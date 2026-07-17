# cyrius-doom — Audit Round: Texture World-Lock + Performance + AGNOS Input + E1M1 Fidelity (2026-07-17, v0.34.0)

> **Audit-only round — no code changed.** Four parallel investigation agents over the v0.34.0
> tree, each working in scratchpad repo copies (main tree verified clean before and after).
> Every finding below carries reproduction evidence from instrumented/staged builds, not just
> code reading. This document extends the open-findings ledger
> ([`2026-07-12-consolidated-audit.md`](2026-07-12-consolidated-audit.md) remains the authority
> for pre-0.34.0 findings; §5 below carries its still-open items forward in condensed form).
> The fix slots live in [`roadmap.md`](../development/roadmap.md) § "0.34.x patch band".
>
> **Toolchain caveat**: the local cycc wrapper had drifted to **6.4.66** (pin is 6.4.58) when the
> perf prototypes were measured — recorded per the metrics rule. All perf numbers are relative
> A/Bs under the same compiler, so the deltas stand; absolute times re-baseline at the next
> true-pin bench row.
>
> **Method**: (1) texture-distortion agent — instrumented per-seg/per-column U-pipeline dumps,
> 3 staged viewpoints × 29 view angles on E1M1 linedef 37, bit-exact Python replica of the
> integer pipeline (2,923/2,923 columns identical), fix candidates toggled in the replica then
> implemented live in Cyrius; (2) optimization agent — measured prototype ladder with
> byte-identical PPM gates + full test suite on each step; (3) AGNOS input agent — full QEMU
> reproduction matrix on agnos HEAD and the exact 2026-07-12 kernel; (4) E1M1 fidelity agent —
> THINGS-lump parse + per-skill spawn diff + dynamic tick-1 probe + staged tick-0-vs-tick-1
> renders.

---

## 1. TX — Texture world-lock (the "changing viewing angle still distorts texture" field report)

**User-visible severity: HIGH.** Wall textures must map texels to fixed world positions
regardless of view angle ("texture render locking"). They don't — and the dominant cause is
not any of the previously-shipped U fixes (all re-verified sound).

**World-lock metric**: worst texel slide of a fixed world point on the wall across view
angles. Measurement noise floor ≈ 1.5–2.5 texels (between-column interpolation, established
by a float vanilla-reference run).

| Variant | S1 frontal | S2 wall-extends-behind-viewer | S3 oblique |
|---|---|---|---|
| V0 engine as-is | 1.43 | **48.24** (absolute error up to **110 texels**) | 2.75 |
| V1 + near-clip U fix only | 1.43 | 13.13 | 2.75 |
| V2 + sub-pixel endpoint anchors | 1.53 | 2.49 | 2.16 |
| VW float vanilla reference (= noise floor) | 1.53 | 2.49 | 2.16 |
| **V4 full fix, pure 16.16, live in engine** | **1.53** | **2.49** | **2.16** |

### Findings

| ID | Sev | Where | Defect |
|----|-----|-------|--------|
| **TX-1** | **HIGH** (primary) | `render.cyr:847-866` (clip) vs `:977-981` (U) vs `:987` (scale) | **Near-plane clipping moves the seg endpoint but not its texture-U or scale anchor.** `tx/ty` are lerped to `NEAR_CLIP` but `u_v1/u_v2` stay the U of the *unclipped* endpoints while `wscale1 = fixed_div(PROJ_DIST, ty1)` uses the *clipped* depth — the (U, 1/z) endpoint pair fed to the F22 perspective-correct interpolation (`:994-995`) corresponds to no point on the wall. U becomes a function of where the near plane crosses the seg = of **view angle**. Any wall extending past the eye plane (the normal case turning in corridors / hugging walls) swims by tens of texels (S2: 48-texel slide). The corrupted endpoint also poisons `col_scale` — measured 13% scale error → 72-row silhouette error at the near column — which corrupts the F06 V-step (`ty_step = 1/col_scale`, `:1266/:1290/:1335`) and lighting: the **vertical** half of the distortion. |
| **TX-2** | **HIGH** (amplifier) | `:847` (NEAR_CLIP=256), `:870-871` (`fixed_to_int` column snap), `:1003-1017` (RC-W9 re-anchor), `:1119-1122` (`frac` from integer `sx1/sx2`) | **Degenerate NEAR_CLIP (1/256 world unit) + integer-column endpoint anchoring + 16.16 re-anchor quantization.** A clipped endpoint projects ~1.9 M columns off-screen; the RC-W9 re-anchor then lerps with 2⁻¹⁶-granular `rt` over that span → ~29 columns of anchor error (the 13-texel residual after TX-1 alone). On ordinary walls the same family costs 1–3 texels of continuous crawl while rotating. The endpoint-lerp scheme is mathematically exact but numerically fragile when one interpolant is 5 orders of magnitude larger than the other. |
| **TX-3** | MED | `render.cyr:716-743` + `:1132-1133` | **V anchored to the truncated wall-section top row, not the view center.** `tex_y` starts at row `y1 = ceil_screen` (floor-truncated projection); when the true projection crosses an integer row during rotation the whole column's texture shifts one V-step. Vanilla anchors `dc_texturemid` at `centery`, immune to top-row snapping. ±1 texel per-column vertical shimmer; worse where TX-1 corrupts the step. |
| **TX-4** | LOW/MED (static, not a swim) | `render.cyr:969` + `fixed.cyr:62-67` | **`seg_len` via `fixed_approx_dist`** (max + min/2, up to ~11.8% error) makes `u_v2` wrong on diagonal segs → static horizontal stretch + a seam at every seg boundary (each seg re-anchors at its exact WAD offset). Angle-independent — not the reported swim, but fix in passing. Same defect as the prior ledger's **R-4** (+6% @45°) — supersedes that row. |

The masked pass inherits TX-1/TX-2 verbatim (stores `uow/scale` endpoints at `:1058-1066`,
consumes at `:1579-1603`).

### Fix design (validated live as V4 — world-lock at noise floor on all three scenarios)

Replace per-column endpoint-lerp U/scale with a **per-column ray↔seg intersection in view
space using the UNCLIPPED endpoints** — vanilla's world-anchored `rw_offset − tan·rw_distance`
math reparametrized (no tangent table needed), pure 16.16 with `asr`, overflow-safe in i64
(worst product ~2⁴⁷):

```
# once per seg (keep raw rtx/rty copies BEFORE near clip mutates tx/ty):
#   u_v1 = sd_xoff + seg_offset ; u_v2 = u_v1 + exact seg texel length
# per column:
rr  = r_table[col]                        # ((col-160)<<16)/160 — 320-entry table at init
den = (rtx2 - rtx1) - fixed_mul(rr, rty2 - rty1)
sp  = (den != 0) ? fixed_div(fixed_mul(rr, rty1) - rtx1, den) : 0
sp  = clamp(sp, 0, FIXED_ONE)
ty  = rty1 + fixed_mul(sp, rty2 - rty1);  if (ty < 256) ty = 256
col_scale = fixed_div(PROJ_DIST, ty);  depth = ty
tex_u = fixed_to_int((u_v1 << 16) + fixed_mul(sp, (u_v2 - u_v1) << 16))
```

- U no longer depends on near clip, swap order, screen clamping, or endpoint snapping — the
  `seg_u_swapped` flag and the RC-W9 **U** re-anchor become dead for the wall pass (keep the
  re-anchored `wscale1/2` only as stored drawseg/masked band endpoints, or store V4 scales at
  `sx1/sx2`). Cost: net ~+2 `fixed_mul` per column — bench gate mandatory.
- **Masked pass**: store `rtx1, rty1, rtx2, rty2, u_v1, u_v2` in the masked entry (replaces
  `uow1/uow2`; +4 fields, `MASKED_ENTRY_SIZE` 120→152) and apply the same per-column form in
  `render_masked_one`.
- **TX-4**: exact per-seg texel length via one-time integer sqrt at map load — zero per-frame cost.
- **TX-3**: anchor V at view center, vanilla-style:
  `v_mid = ((anchor_top_h << 16) - view_z) + (sd_yoff << 16)` with per-section/peg
  `anchor_top_h` — upper: `ceil_h` (DONTPEGTOP) else `back_ceil_h + tex_h`; mid: `ceil_h` else
  `floor_h + tex_h` (DONTPEGBOTTOM); lower: `back_floor_h` else `ceil_h`. Call sites pass
  `tex_y_start = v_mid + (y1 - HALF_HEIGHT) * ty_step`; the `:1298` closed-gap V re-anchor
  hack falls out for free.
- **Verify**: (1) the staged world-lock harness (preserved in the session scratchpad:
  `run_staged.sh` / `analyze.py` / `replicate.py`) — slide ≤ noise floor on S1/S2/S3;
  (2) spawn-view A/B — expect diffs confined to wall texel boundaries (~5–8% of pixels;
  measured 7.26%, all in wall rows, floors/HUD byte-identical), no structural change;
  (3) full tests + bench row + AGNOS QEMU 4×-block pixel-diff. **No** byte-identical
  expectation for wall pixels — sub-texel corrections everywhere.

### Refuted (TX)

RC-W9 logic itself (projectively exact; only its quantization over near-clip-inflated spans is
at fault — TX-2); the 0.30.1 swap-mirror residual (`swapped=0` across all 29 staged runs;
V4 removes swap sensitivity anyway — keep it in the fix's test matrix); missing `sd_xoff` /
seg-offset application (both applied at `:977`); the F22 perspective-correct scheme (sound —
its endpoint *inputs* are the bug); sky/wall inconsistency, Bhaskara trig error, `fixed_lerp`
precision on normal spans (all sub-texel); `fixed_approx_dist` as a swim cause (static only).

---

## 2. OP — Performance (algorithmic wins only; the v6.5.x regalloc arc is not fought)

**Headline: the bench has a blind spot.** `benches/doom.bcyr` never calls
`things_spawn_from_map()`, so every `render_frame+sprites` row in `bench-history.csv` measured
an **empty world** (sprite pass ≈ 2 µs). With things spawned, the true E1M1 spawn frame is
**4.09 ms, not 2.35 ms** — ~1.7 ms/frame was invisible to every bench row ever recorded.

**Measured prototype ladder** (E1M1, things spawned, Linux, cycc 6.4.66; byte-identical
`--ppm` on E1M1/E1M2/E1M3/E1M5/E1M7/E1M9 + 168/168 WAD-free + 264/264 full tests at each step):

| Step | spawn frame | turned-180 view |
|---|---|---|
| Baseline (true) | 4.086 ms | 2.736 ms |
| + OP-1 sprite lump memo | 2.564 ms | 1.885 ms |
| + OP-2 composited-texture cache | 2.160 ms | 1.401 ms |
| + OP-3 plane/texcol loop hoists | **1.278 ms** | **0.631 ms** |

**−69% total.** All three are algorithmic (fewer operations), so they carry to AGNOS/QEMU
proportionally or better.

| ID | Impact | Where | Finding / fix |
|----|--------|-------|---------------|
| **OP-0** | gate integrity | `benches/doom.bcyr` | Bench never spawns things → sprite pass + things-adjacent costs invisible. Add a spawned-things frame row + `things_tick` + `status_render` rows. **Do first** so every later gain is measured honestly. |
| **OP-1** | **−1.52 ms/frame (−37%), measured** | `sprite.cyr:183` `sprite_find_frame` | Up to ~5 `wad_find_lump` calls per visible sprite **per frame**; each a linear scan of ~1,260 directory entries through `strlen`-based `wad_name_eq` — measured 33.7 µs/scan, 65 scans/frame at spawn with ~12 visible sprites; crowd views scale to 4–6 ms. Fix: permanent memo `(type, frame, rotation) → (lump, flip)` — WAD immutable, no invalidation, ~25 lines. Near-zero risk. |
| **OP-2** | **−0.40 ms/frame measured + kills a scaling cliff** | `texture.cyr:252` `texture_get_column` | Re-decodes patch posts from scratch **every call** (this is the entire "mysterious" 849 ns: clear 2×th bytes, walk patch refs, `pcache_get`, decode posts — 729 calls/frame ≈ 612 µs at spawn). Lazily composite each texture once (columns + fill masks) on first use; serve as two `th`-byte copies (~30 ns). Also removes the hidden cliff: a scene whose per-frame patch working set exceeds the 8-slot pcache degrades to WAD syscalls per column per frame. ~1–2 MB heap for shareware. Integration requirement: `anim_rotate_tex_3` must rotate/invalidate composite pointers (intersects the SLADRIP-anim no-op bug). |
| **OP-3** | **−0.92 ms/frame, measured** | `render.cyr:1444-1451` (`render_plane_row`), `:731-741` (`render_draw_tex_column`) | Per-pixel call/div elimination a register allocator can never do. Plane row: 2 nested `fixed_to_int→asr` fn calls + `framebuf_pixel` (bounds + y×320 mul) per pixel × 51k flat px/frame → hoist row pointer, bias U/V accumulators by a positive multiple of 64<<16 so logical `>>16 & 63` is exact (**19.8 → 4.6 ns/px**). Subtlety: negated-V needs `+0xFFFF` in the bias to match negate-after-`asr` floor semantics — without it output shifts one texel. Tex column: per-pixel `% th` (div), 2-call `fixed_to_int`, `render_shade` + `framebuf_pixel` calls → hoist colormap row, wrapped-V accumulator (compare+subtract), pointer stepped by `SCREEN_WIDTH`. |
| **OP-4** | −~170 µs/frame (measured 202 µs → est. <30) | `status.cyr:189,250,293,307-309` | `status_render` does ~7 `wad_find_lump` scans + ~20 `wad_read_lump_into` (lseek+read syscall pairs) **every frame** (grey STGNUM digits, face, keys). Resolve lumps at `status_init_font` + keep decoded patches, like `st_nums` already does. Trivial risk. |
| **OP-5** | scaling insurance (**the AGNOS budget-killer on dense maps**) | `things.cyr:374-429` (`thing_check_sight`), `:598` (idle wake), `:617` (chase) | 41 µs/call (full linedef scan) × every idle monster every tick: E1M1-easy ≈ 1.1 ms/tick hidden in `things_tick`; an E1M7-class map (100+ monsters, ~2× linedefs) extrapolates to **8–15 ms/tick on Linux** — game over on QEMU/AGNOS. Fixes, cheapest first: (a) per-linedef bboxes at map load, reject vs the sight segment's bbox; (b) load the WAD's **REJECT lump** (marker+9, currently never read) as a free (sector,sector) LOS pre-test — this is what F15's per-thing sector cache should exist to enable; (c) stagger idle wake checks (vanilla-style). |
| **OP-6** | est. 33.7 → 2–4 µs/scan | `wad.cyr:150` `wad_name_eq` | `strlen` + byte loop per directory entry. Pack the query once into an uppercase null-padded 8-byte word, compare `load64` vs `entry+16`. Benefits every caller the memos miss (menu, `audio_play_name`, level load). |
| **OP-7** | ~50 µs/frame (smaller than roadmapped) | F12 (per-sidedef tex idx / per-sector flat idx) | Still valid, but measured small: 273 `texture_find` (126 ns each) + 182 `flat_find` per frame. Do anyway — cheap, helps AGNOS more, and is the prerequisite for fixing the SLADRIP animation no-op properly. |
| **OP-8** | est. −100–300 µs, moderate risk | `render_seg` column loop + masked pass | ~6 `fixed_div`/column × 2,637 columns (frac, depth, projections) → vanilla-style per-seg incremental stepping (`rw_scalestep`). PPM A/B gate mandatory. **Sequencing note: do AFTER the TX world-lock fix** — V4 changes the per-column math this would restructure. |
| **OP-9** | crowd-scene insurance | `render.cyr:688-694` `render_clip_band_build` | 2 `fixed_div` + 2 lerps per column per overlapping drawseg, rebuilt per sprite/masked entry — O(sprites × drawsegs × columns) worst case. Precompute per-drawseg scale steps at store time; step incrementally. Small at spawn. |
| **OP-10** | every presented frame (off the render bench) | `framebuf_blit` / `framebuf_present_wayland` / `framebuf_blit_agnos` | Palette→XRGB 256-entry u32 LUT rebuilt on `framebuf_set_palette` replaces 3 loads + 3 shifts per source pixel per frame. |

**Wait for the cyrius v6.5.x regalloc arc** (don't hand-fight codegen): `fixed_mul`/`asr`/
`fixed_div` call overhead (6/5/4 ns), `colormap_shade`/`point_on_side` micro-costs, register
shuffling in loops the hoists above don't already restructure.

**Refuted / not worth it**: F26 automap pre-clip (confirmed negligible); pcache LRU thrash as a
standalone fix (22 first-frame misses, 0 after; OP-2 removes pcache from the hot path anyway);
F15 as a *perf* item (~0.3 µs/thing BSP descent, ~5–10 µs/frame total — its real value is as
the sector resolver for OP-5's REJECT test); audio/music mixer (tens of µs/tick, bounded);
sprite/masked insertion sorts (O(n²) on tens of items ≈ µs).

---

## 3. AG — AGNOS "keyboard-into-menu delivery stuck" (the 0.34.0 noted issue)

**RESOLVED BY DIAGNOSIS — there is no kernel keyboard regression, and the 0.34.0 state.md
framing ("cause unidentified, agnos-side") was wrong.** Corrected in state.md this round.

Full QEMU reproduction matrix with the existing prebuilt `build/doom_agnos` (v0.34.0), robust
gates (title-diff + [8..45] flat-band + visual PNG):

| Kernel | Key cadence | Result |
|---|---|---|
| agnos HEAD `7445739` | held 500 ms | **PASS** — real E1M1 3D (HUD/weapon/monster visually verified) |
| HEAD | explicit 100 ms | **PASS** |
| HEAD | bare `sendkey` | **FAIL** — byte-identical to TITLEPIC, no edge seen |
| 2026-07-12 kernel `3335469` | held 500 ms | **PASS** (identical floor signature) |
| `3335469` | bare `sendkey` | **PARTIAL** — menu appeared, game never started |

**Mechanism (AG-1)**: doom runs ring-3 IF=0; `input.cyr:413-428` (AGNOS path) drains **all**
buffered scancodes per `kbscan#42` call and keeps only final `key_state` — a make+break pair
landing in one drain nets to zero and no edge is ever seen. Under QEMU TCG the effective poll
period inflated over the month (doom 0.34.0 render-cost growth + kernel per-frame additions:
iron_lock spinlocks 06-26, timer-tick `hid_poll`+xHCI MSI 07-08, per-`hid_poll` IMAN MMIO
re-arm 07-10), pushing QEMU's ~100 ms bare-`sendkey` tap onto the margin — hence flaky.

**The month of false passes**: the last *genuinely verified* bare-tap pass was **agnos 1.43.8,
2026-06-09** (framebuffer-*change* gate). Every "in-game PASS" from 06-12 to 07-12 gated on
"map: V=" — which doom prints at **boot** (`main.cyr:320` `load_map(1)` runs before
`menu_run()` at `:438`) — and on ≥8-colors/row, which TITLEPIC art also passes. There was no
discrete break; the tap margin eroded invisibly. This also **reconciles the disputed held-key
harness episode**: the prior agent's mechanism was right, AND input genuinely "worked fine
previously" (the 06-09 era) — a month of false passes hid the erosion.

**Refuted**: kernel keyboard-path breakage (held-key passes on both bracketing kernels; input
path diff is version strings only); setu/aethersafha routing (harness launches doom directly,
no compositor in image; setu delivery separately proven working 07-12); GPU blit blocking under
QEMU (DCN-only paths); the `8657e9e` probe fallout (DBG-only, removed 21 min later; post-cleanup
kernel reproduces); klug (log ring only).

**Repair plan**:
- **agnos (no kernel fix needed)**: keep the held-key harness (`DOOM_KEY_HOLD=500`) + the
  robust title-diff/flat-band gates; add an intermediate screendump after the first key
  (distinguishes "still title" vs "menu appeared, game didn't start"); keep "map: V=" demoted
  to info; **promote `doom-directmap-smoke.sh` as the canonical AGNOS render gate** (zero
  keyboard dependency — exactly what state.md proposed).
- **doom (AG-2, optional robustness — the only change that makes real short taps reliable)**:
  in the `input.cyr` AGNOS drain (~`:413-428`), latch a per-key "make-seen-since-last-poll"
  edge flag for menu consumption instead of relying solely on final `key_state`. Enhancement,
  not a regression fix. Slotted 0.34.x.
- Watch item (real hardware, not QEMU): blit#39 now vsync-blocks when a DCN pipe is owned — a
  deliberate agnos pacing change to re-check on iron.

---

## 4. EF — E1M1 fidelity (field reports: "greenshirts alive that should be dead", "missing three zombies at the armor staircase")

| ID | Sev | Where | Finding |
|----|-----|-------|---------|
| **EF-1** | **HIGH** (user-visible on every map, every session) | `things.cyr:467-477` vs `:359-360` | **Corpse-decor spawn frames are clobbered to the standing frame on the very first game tick.** `things_spawn_from_map` correctly spawns dead-player decor (type 15) on PLAY `N` (frame 13) and gibs (10/12) on PLAY `W` (frame 22) — the RC-S3 fix. But `thing_animate` (every thing, every tick) executes `thing_set_frame(idx, 0)` for STATE_SPAWN + non-CAT_MONSTER → tick 1 resets 13/22 → 0 = PLAY `A`, an upright green-armored marine. It then stands there all level, unshootable and non-solid ("won't die when shot" — they're decor). E1M1 has **8** such phantoms (lump idx 114/115 spawn room, 117 secret courtyard, 118, 119 — right beside the real zombiemen 87/88, maximum confusion —, 123, 124, 125). "Greenshirt" = the PLAY sprite's green armor: these are dead-**player** decorations, not zombiemen. **Why every prior verification missed it**: `--ppm` renders at tick 0, before any `things_tick()` (`main.cyr:392-400` vs the interactive loop's `:540`) — RC-S3's staged screenshots genuinely showed corpses; live play never does. Dynamic proof: probe build shows all type-15 `frame 13→0`, all 10/12 `frame 22→0` after one tick; staged tick-0 vs tick-1 renders show corpse → standing marine (824-px diff, exactly the sprite box). **Fix**: delete the `thing_set_frame(idx, 0)` else-arm (spawn frame is authoritative for decor; barrels/items already sit at frame 0). Regression: WAD-gated assert — after spawn + one `things_tick`, type-15 frame==13, type-10/12 frame==22. |
| **EF-2** | MED (fidelity; also the UV half of the missing-zombies report) | `map.cyr:130-131` (documented, never consumed), `things.cyr:1345-1357` (`things_noise_alert`), `:598` (sight wake) | **The deaf/ambush flag (THINGS options bit 8) is parsed and never honored — and 28 of E1M1's 29 monsters are ambush-flagged.** Vanilla: a deaf monster ignores the sound flood unless it also *sees* the player — E1M1's opening monsters famously hold their posts through pistol fire. Ours: the first shot's noise flood wakes everything through the window portals, and with no P_NewChaseDir wander they beeline into walls/ledges — by the time the player climbs to the armor, the vanilla posts are empty. (The 0.33.1 "5-of-6 wake parity" check verified flood *reach* only; with MF_AMBUSH honored vanilla wakes ~0 of them.) The reported "three zombies at the armor staircase" are lump idx 10/11/12 (courtyard trio): **all three exist only on skill 4-5** (HMP has two, ITYTD one) — so if the session was HMP, two-not-three is vanilla-correct (skill confirm outstanding); if UV, all three spawn but wander off-post per this finding. **Fix**: store bit 8 as a `TF_AMBUSH` flag at spawn; in the noise-alert wake loop skip TF_AMBUSH monsters unless `thing_check_sight` passes; optionally add vanilla's front-180° FOV gate to the SPAWN-state sight wake. Verify via pty harness: pistol shot at spawn wakes ~0 E1M1 monsters. |
| **EF-3** | LOW | `things.cyr:286` | Deathmatch starts (type 11) spawn as invisible inert decor (only types 1-4 are skipped) — 5 wasted slots/level and the reason our HMP count is 96 vs vanilla's 91. Skip type 11 (and keep 1-4) in single-player spawn. |
| **EF-4** | LOW (latent null-deref) | `tick.cyr:73-75` + `main.cyr:433` | `tick_get_count()` does `load64(tick_state)` with `tick_state=0` until `tick_init()`, and `--ppm` mode never calls `tick_init` — any future "tick then screenshot" probe SIGSEGVs (bit this audit's first A/B: exit 139, silently-stale PPM). Add the standard lazy-init guard. **Process fix**: the PPM gate cannot see first-tick regressions (EF-1's whole camouflage) — consider a `--ppm-tick N` mode (which must call `tick_init` first). |

**Spawn filter verified vanilla-exact** (refutes the filter as the missing-zombie cause):
per-skill spawn sets computed from the lump vs `things_spawn_from_map` (`things.cyr:292-297`)
are identical at every skill — skills 1-2: 4 monsters (2 imp, 2 zombie); skill 3: 6 (2 imp,
4 zombie — state.md's "6 monsters HMP" is vanilla-correct); skills 4-5: 29 (16 sergeant, 4 imp,
9 zombie). Multiplayer bit 16 handled correctly (E1M1's 14 mp-only things are all items — no
monster leak). Also refuted: monsters failing to die or resurrecting (`thing_damage` guards
STATE_DIE/DEAD; DIE→DEAD keeps the POSS corpse frame 11; no transition out of STATE_DEAD);
types 18/19 dead-trooper decor (zero exist in any DOOM1.WAD map — E1 uses only 10/12/15/24);
thing-type table gaps; spawn caps.

---

## 5. Carried forward from the 2026-07-12 ledger (condensed; evidence in that doc)

Still open post-0.34.0, unchanged by this round except where noted:

- **Pre-PWAD residuals**: G-13 sector-0 degenerate-leaf refinement; R-5 patch-dim overflow
  clamps (LOW); R-7 `WAD_MAX_LUMPS`/`FLAT_MAX` full-IWAD truncation; R-9 post-walk cap unify.
- **R-4 seg-U approximate length** — **superseded by TX-4** (same defect, now with the exact
  fix path: integer sqrt at map load).
- **Fidelity (0.34.x band)**: RC-S6 real thing-z (+ res-1 precise missile trace); P4
  episode-complete screen (E1M8 → text/bunny + `D_VICTOR`); F06-1 LOW `tex_h>256` peg clamp;
  blazing/turbo speeds (registered-WAD-gated).
- **Perf slots**: F12 → absorbed into OP-7; F15 → reframed as OP-5's sector resolver; F26 →
  refuted (drop).
- **0.33.1 follow-ups**: baron BAL7 (registered-gated), vanilla ledge-glide z, sight z-slope,
  P_NewChaseDir wander (note: wander now *also* matters for EF-2's post-wake behavior).
- **`asr()` → `>>>` migration** (~95 sites, own gate); **Wayland follow-ups** WF-1…WF-8;
  **music fidelity** #1–4; F-R5 24-bpp fb blit (hardware-gated); F-U6 AGNOS scancode prefix
  (QEMU-gated — note AG-2 touches the same drain loop; do together).
- **SLADRIP anim no-op + FLAT_MAX** (wall-path items 3–4) — OP-2's composite invalidation and
  OP-7's index cache are the natural vehicles.

---

## 6. Evidence preservation

All instrumented copies, staged PPM/PNG pairs, dump logs, the bit-exact Python pipeline
replica, the QEMU pass/fail screendumps, and the THINGS parser live under the session
scratchpad (`/tmp/claude-1000/-home-macro-Repos-cyrius-doom/f5b14154-c73d-491e-ae17-8ce4e89e7b09/scratchpad/`)
— ephemeral; the numbers and file:line citations above are the durable record. The main repo
was verified untouched (clean `git status`) after every agent.

*Next refresh: fold forward at the next audit round; move fixed rows out as the 0.34.x slots ship.*
