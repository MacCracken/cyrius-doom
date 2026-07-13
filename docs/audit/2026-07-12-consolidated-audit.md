# cyrius-doom — Consolidated Audit (2026-07-12, v0.33.3)

> **This document supersedes the per-topic audit reports as the single open-findings ledger.**
> The seven prior audit docs remain as dated artifacts (evidence + repro detail); this file
> carries the *current* status of every finding in them plus the new findings from the
> 2026-07-12 round, and is the authority the roadmap slots against.
>
> **Method**: five parallel review agents over the 0.33.3 tree (toolchain 6.4.55) —
> (1) prior-audit open-items sweep across all 7 docs, (2) setu/Wayland/platform security,
> (3) render + WAD-parse correctness, (4) gameplay/things/collision, (5) memory-safety +
> convention sweep. Every reported finding was traced to a real call path; each carries a
> confidence (CONFIRMED = traced end-to-end / PLAUSIBLE = mechanism verified, in-game trigger
> not reproduced). Spot-verified by hand: the setu present leak (P-1), the BSP node-cycle gap,
> the tagged-special dispatch bug (G-2).

---

## 0. Scope of this cut (v0.33.3)

**Shipped in 0.33.4** (the first fix-slot patch off this audit): **M-1** (Wayland resize-below-320×200
crash), **P-6** (compositor-dim overflow), **M-2** (env-path stack smash), **R-2** (dead death-face),
**R-6/M-3/M-4** (TEXTURE1/STBAR alloc guards), **G-7** (sparse hot-path switches → if/else). See
CHANGELOG `[0.33.4]`. The rows below marked "slotted v0.33.4" are now **FIXED@0.33.4**.

**Shipped in 0.33.8** (pre-PWAD security hardening, the v0.28.11 slot): the latent **HIGH — BSP node
child-cycle gap** in `map_validate` (a hostile cycle would hang/overflow every BSP walk) → new
`map_validate_bsp_acyclic` rejects cycles + shared subtrees at load; **R-3** (zero-seg subsector reject
+ `map_point_sector` bounds); **R-10/M-6** (masked-seg + `render_draw_tex_column` render-loop clamps —
the F17 frame-stall residual; byte-identical A/B); render/sprite BSP descents self-protect (review
defense-in-depth); **fuzz-corpus refresh** (`fuzz/fuzz_texture.cyr`, structured TEXTURE1/PNAMES decoder
fuzzer — rewritten + coverage-verified after the review proved the first version had zero coverage);
**CVE re-walk** (C3/H1 confirmed still-fixed@0.24.0). Deferred: **G-13** sector-0-vs-−1 refinement (0.33.8
returns a safe sector 0); **R-5** patch-dim overflow clamps (LOW); bench formatter (cyrius stdlib). See
CHANGELOG `[0.33.8]`.

**Shipped in 0.33.7** (door/lift fidelity follow-ups from the G-2 review): **G-5** (drop-off escape-rule
zero-band — an on-line cross-product endpoint now counts as crossing so the ML_BLOCKING/one-sided veto
applies), plus the two pre-existing door-fidelity items the G-2 review surfaced — doors open to the
**lowest** neighbor ceiling (vanilla `P_FindLowestCeilingSurrounding`, not the highest) and the
**W1/S1/D1 one-shot latch** (once-only specials fire once per level; keyed D1 doors key-gated, tag-loop
latch restricted to the S1 switch subset per a further adversarial review). Blazing/turbo speed deferred
→ roadmap v0.34.x (registered-WAD-only). See CHANGELOG `[0.33.7]`.

**Shipped in 0.33.6** (+ toolchain 6.4.55→6.4.58): **RC-F2** (bsp `asr()` floor-vs-round-toward-zero)
— fixed upstream in bsp 1.2.1 (floor semantics; doom shares bsp's `asr` engine-wide, positive-case
byte-identical, 9-map PPM A/B byte-identical). doom `[deps.bsp]` 1.2.0→1.2.1 (published, commit-pin
`211b6c41…`); lock regenerated 36/0 on true-pin 6.4.58. See CHANGELOG `[0.33.6]`.

**Shipped in 0.33.5** (the second fix-slot patch): **G-2** (switch doors/lifts → tagged sectors; the
progression blocker — plus the one-sided-switch-line inert case, the newly-added D1 keyed open-stay
doors 32/33/34, the walk-special relocation, and a one-way `DS_FLOOR_LOWER` motion for 23/38/70/71/102),
**R-1** (both-end render-clip clamp — A/B PPM byte-identical, review-confirmed), **G-1** (weapon-switch
refire-cadence gate), **G-3** (intermission/death min-display + sustained-release), **G-4** (armor
class), **G-6** (melee sight re-check), **G-8** (open-stay door sound spam), **G-12** (sergeant SFX). See
CHANGELOG `[0.33.5]`. **G-5** (escape-rule zero-band) and pre-existing door/lift fidelity items surfaced
by the G-2 review (door-opens-to-highest-ceiling, blazing/turbo speed, W1 one-shot latch) deferred → roadmap 0.33.7.

**Shipped in 0.33.3** (this document's release):
- **Toolchain pin `6.4.43 → 6.4.55`** (latest; true-pin build via `~/.cyrius/versions/6.4.55/bin/cyrius`).
- **vani vendor `1.1.0 → 1.1.1`** (dist byte-identical except the version header — provenance refresh).
- **setu vendor `0.5.0 → 0.5.1`** carrying the **P-1 fix** (present-buffer reuse) + **P-3/P-5** input
  stream reassembly, plus the doom-side **P-2/P-4** setu input hardening (focus-loss latch clear,
  persistent poll scratch). bsp stays `1.2.0`, setu proto wire unchanged.
- Lock regenerated clean: **36 verified / 0 failed** (was 34 on 6.4.43 — the 6.4.55 stdlib snapshot).

Everything else below is **classified and slotted onto the roadmap**, not fixed in this cut.

---

## 1. New findings — 2026-07-12 round

Severity key: **HIGH** = crash / DoS / memory-unsafety reachable on a path that runs; **MED** =
conformant-input correctness bug or a security hole reachable only via hostile assets;
**LOW/INFO** = cosmetic, latent, or convention.

### 1a. Platform / security (agent 2 + memory sweep agent 5)

| ID | Sev | Where | Defect | Status |
|----|-----|-------|--------|--------|
| **P-1** | **HIGH** | `setu client (upstream)` → present path | `setu_client_present` created a **new** kernel shm buffer every frame and never freed any; agnos has 16 system-wide shm slots → exhausted in <0.5 s of 35 Hz play → every present (all setu apps') drops to the 2 KB-window TCP fallback = system-wide present DoS until reboot; Linux leaked one `/dev/shm` file per frame. | **FIXED 0.33.3** — patched **upstream in setu 0.5.1** (cache one buffer id in `SetuClient`, rewrite in place, recreate on resize, free at close), re-vendored, QEMU compositor-present + input smokes PASS. |
| **P-2** | MED | `input.cyr` setu path / `setu_present.cyr` | Held keys never cleared on focus loss (setu ignored `SETU_INPUT_FOCUS`); the Wayland path already clears on `wl_focus==0`. Alt-tab while holding W → player walks forever. | **FIXED 0.33.3** — `doom_setu_focus` tracked from `SETU_INPUT_FOCUS`, `input_poll_setu` clears all latches on focus 0. |
| **P-3** | MED | `setu_present.cyr` drain | A non-key setu message (focus/pointer/configure) returned "nothing pending" and ended the frame's input drain early → key latency under mixed-event bursts. | **FIXED 0.33.3** — `doom_setu_next_key` returns a distinct "consumed non-key, keep draining" code. |
| **P-4 / M-5** | MED→HIGH | `setu_present.cyr` + setu poll | Per-poll `setu_msg_new()` (80 B) + `setu_poll_input` scratch (256 B) on a never-free bump allocator, ≥35×/s → ~12 KB/s idle, ~1.5 MB/s under input → unbounded agnos heap growth. | **FIXED 0.33.3** — persistent lazily-alloc'd `doom_setu_msg`; setu 0.5.1's `setu_client_poll_input` owns a reused 512 B reassembly buffer (no per-poll alloc). |
| **P-5** | MED | `setu client (upstream)` | `setu_poll_input` decoded only the first frame of each recv; coalesced/split TCP frames dropped — a dropped key-RELEASE is a stuck key. | **FIXED 0.33.3** — new `setu_client_poll_input` reassembles the stream (setu 0.5.1); RUN-tested (coalesced + split frames). |
| **M-1** | **HIGH** | `framebuf.cyr` `framebuf_present_wayland` + `window.cyr` resize | Wayland present blits a fixed 320·scale × 200·scale frame into a `win_w×win_h` shm buffer with **no minimum-size clamp**. Drag-resize below 320×200 is live (bite-4 adopts any `cfg>0`); a 300×150 window overruns the pitch → corrupts the sibling pool buffer, and past the mmap end on the far buffer → SIGSEGV. | **OPEN — slotted v0.33.4** (HIGH; user-reachable crash on the resize feature). Fix: `xdg_toplevel.set_min_size(320,200)` + floor-clamp in `framebuf_wl_recompute`/`win_resize_apply`. |
| **M-2** | MED | `platform/wayland/client.cyr` `wl__sock_path` | `WAYLAND_DISPLAY`/`XDG_RUNTIME_DIR` copied unbounded into a 128 B stack buffer then a 120 B `sockaddr_un` — no length check (the "<120 chars" comment is an assumption). Over-long env → stack smash on the default Linux startup path. | **OPEN — slotted v0.33.4** (MED). Fix: cap to 107 B (`sun_path`), fail `wl_connect` → fb0 fallback when it doesn't fit. |
| **P-6** | LOW | `platform/wayland/shm.cyr` | No upper bound on compositor-supplied window dims; `bsize=w*4*h`, `psize=bsize*2` can integer-overflow to a small positive → undersized mmap vs a larger blit. Semi-trusted compositor. | **OPEN — v0.33.4** with M-1 (same clamp site). |
| **P-7 / P-8** | INFO | wayland client / framebuf | WF-6 residual (fixed-offset event fields under the size≥8 gate + 64 B slack — wrong value, not OOB); `PM_PPM` opens an unused `/dev/fb0` fd. | **OPEN — WF-6 (accepted, local-compositor threat model)** / trivial. |

### 1b. Render + WAD parse (agent 3)

| ID | Sev | Where | Defect | Status |
|----|-----|-------|--------|--------|
| **R-1** | MED | `render.cyr` seg loop | Wall/plane/sky sections clamp to the clip window on **one end only** (`ceil_screen` up to `ct` but not down to `cb+1`; back-sector `upper_y2`/`lower_y1` unclamped). Vanilla `R_RenderSegLoop` clamps both. Through a raised-sill portal a far ceiling projects below `cb`, gets marked into the visplane past `cb`, and the plane pass overpaints the near wall. Visual only (all writes bounded). | **OPEN — slotted v0.33.5** (MED; the only conformant-map render defect found). Fix: clamp both ends + re-anchor texture-V (the closed-gap path already shows the pattern). |
| **R-2** | MED | `status.cyr:30,224` + `wad.cyr` `wad_name_eq`→`strlen` | Face-name scratch is `alloc(8)` with **no NUL**; `strlen` reads the adjacent 4096 B face-patch buffer (bump-adjacent). After the first face draw `strlen>8` → `wad_name_eq` rejects every lump → `STFDEAD0` never resolves → **death face is a blank cutout**. Same over-read class as the 0.29.4 PNAMES bug; deterministic. | **OPEN — slotted v0.33.4** (MED but a ~2-line fix: `alloc(9)` + `store8(buf+8,0)`, same for `STYSNUM`). |
| **R-3** | LOW | `map.cyr` `map_validate`/`map_point_sector` | Zero-seg subsector (`count==0`) admitted; `map_point_sector` lacks the `first_seg<num_segs` guard the other two BSP walkers have → one seg entry past range on a crafted WAD. | **OPEN — v0.28.11** (with the node-cycle gap). |
| **R-4** | LOW | `render.cyr:956,965` | Texture-U seg length uses `fixed_approx_dist` (+6% @45°) while the next seg anchors from the exact WAD offset → texture discontinuity at every diagonal seg join (~7 texels/128u). | **OPEN — slotted v0.28.7** (sky/wall-mapping parity). Fix: exact integer hypot, or derive `u_v2` from the next seg's offset. |
| **R-5** | LOW | sprite/render/fixed | i64 overflow cluster at WAD-controlled extremes (giant patch width × point-blank scale; ±32k sector-height delta × near-clip scale). Garbage visuals, not memory-unsafe. | **OPEN — v0.28.11** (clamp patch dims + height deltas). |
| **R-6 / M-3 / M-4** | MED | `texture.cyr:112`, `status.cyr:41-52` | Lump-sized `alloc()` with no null guard + no size cap (TEXTURE1, STBAR bg/arms) — sibling PNAMES path has the guard. Multi-GB lump → `alloc`→0 → `memset(0,0,sz)` null-write crash at load. Malicious-WAD boot DoS. | **OPEN — slotted v0.33.4** (cheap: mirror the `pn_data==0` guard + cap). |
| **R-7** | INFO | `wad.cyr:16` `WAD_MAX_LUMPS=2048` | Full IWAD (~2306 lumps) silently truncates the directory → 0 flats load + maps exceed MAP_MAX. Companion to FLAT_MAX=64. | **OPEN — full-IWAD theme** (with FLAT_MAX; warn-on-clamp). |
| **R-8** | INFO | `render.cyr:598/1492` | Masked-seg stores `dont_peg_bottom`/`sd_xoff` never read — load-bearing the day F06 native-scale lands. | **CLOSED v0.34.0** (with F06 = F-R4): the masked-mid path now reads `dont_peg_bottom` at `base+112` and bottom-pegs. (`sd_xoff` — verify it's applied; drop if so.) |
| **R-9** | INFO | `status.cyr:106` vs others | Post-walk caps inconsistent (64 HUD/menu vs 128 weapon/sprite vs 256 texture). | **OPEN — trivial** (unify on 256). |
| **R-10 / M-6** | LOW | `render.cyr` back-sector projections | Bare logical `>>` on sector light (safe today — light stored unsigned) + F17's absolute clamp covers the **front** projection only; back-sector + masked `open_top/open_bot` unclamped → a crafted extreme-height sector stalls a frame for minutes (`continue` per row from −2³⁰). No OOB. | **OPEN — v0.28.11** (finish F17: clamp back-sector + masked loop entry; add `asr()`/invariant comment). |

### 1c. Gameplay / things / collision (agent 4)

| ID | Sev | Where | Defect | Status |
|----|-----|-------|--------|--------|
| **G-2** | MED | `doors.cyr:387-404` | Use-activated **tagged** door/lift specials (29, 63, 10, 21, 62, 88, 121, 122) dispatch on the switch line's **back-side sector** instead of the tagged sector. Works only when the switch borders the platform (E1M1's lift does); a **remote** switch animates the wrong sector and the real platform never moves — a progression blocker. | **OPEN — slotted v0.33.5** (MED, most user-visible gameplay bug). Fix: route the tag-activated types through the tag loop; keep 1/26/27/28/31/117 (manual, back-sector-correct) direct. |
| **G-1** | MED | `player.cyr:626` + `render.cyr` | Weapon switch resets `weapon_fire_frame=0` with no gate on an in-flight fire; the fire gate is `==0`. Fire rocket → tap 4 → tap 5 → fire: refire collapses from 20 ticks to ~3 (multi-× DPS on slow weapons). | **OPEN — slotted v0.33.5** (MED). Fix: ignore weapon-switch while `weapon_fire_frame!=0`, or preserve the cadence timer across switch. |
| **G-3** | MED | `level.cyr:280`, `main.cyr:505`, `input.cyr:545` | The "fresh press" release gate on intermission/death screens is defeated on the **Linux tty** path — `key_state` is cleared each poll, so `input_flags` pulses 0 between autorepeat bytes and the next byte counts as a fresh press → screens self-dismiss in <1 s. (Wayland/AGNOS persistent paths fine.) | **OPEN — slotted v0.33.5** (MED). Fix: require N consecutive all-released ticks, or edge-detect a confirm key. |
| **G-13** | INFO→MED | `map.cyr:457` | `map_point_sector` returns sector **0** (not error) for degenerate leaves / outside-map points → wrong mover-floor / misdirected noise flood on a malformed WAD. | **OPEN — v0.28.11** (return −1; callers treat as no-context). Overlaps R-3. |
| **G-6** | LOW | `things.cyr:695` | Melee release has no sight re-check (only ranged does) → melee through a thin wall if the player ducks during the 15-tick wind-up. | **OPEN — v0.33.5** (gate melee on `thing_check_sight`). |
| **G-4** | LOW | `player.cyr:375` | Armor class inferred from current count (`>100`=blue) not pickup type → blue armor degrades to green absorption below 100. | **OPEN — v0.33.5** (track `player_armor_class`). |
| **G-5** | LOW | `player.cyr:265` | Same-side escape rule's cross-product quantizes to 0 within ~0.01–0.13 u of a line (reduced-precision `asr(...,8)`) → `crossing==0` skips the veto → possible 2-step tunnel at ledge/vertex corners. | **OPEN — v0.33.5** (treat `side==0` as crossing, or full-precision sides). |
| **G-8** | LOW | `doors.cyr:138` | Open-stay door replays DSDOROPN + spawns a 1-tick thinker on every use pulse (~15–30 Hz tty autorepeat) → audio spam + voice stealing. | **OPEN — v0.33.5** (early-return when already open). |
| **G-9** | LOW | `input.cyr:341` | (Same root as P-2, now fixed for focus events.) Residual: no focus-loss clear if the compositor never signals focus. | **Mostly FIXED 0.33.3** via P-2; residual gated on aethersafha focus semantics. |
| **G-7** | LOW | `doors.cyr:437/490`, `things.cyr:775` | Sparse/out-of-order `switch` in hot tick paths (`doors_walk_trigger`, `things_check_pickups`) — the cycc return-smash class that hit `thing_animate`/`doors_use` twice. Currently stable; latent to any local-layout change. | **OPEN — slotted v0.33.4** (defensive: rewrite as if/else per the established pattern). |
| **G-10/G-11/G-12** | INFO | player/things | Diagonal double `doors_walk_trigger` call; BFG collectible-but-unfireable (registered-only, dormant); sergeant plays DSPISTOL not DSSHOTGN. | **OPEN — LOW/INFO batch** (G-12 trivial polish; G-11 = RC-G8/L5). |

**Verified clean by agent 4** (worth recording): aux-field lifecycle (kill/respawn/level-change), fireball owner-immunity (no dangling pointer — slots never freed, corpse loses TF_SHOOTABLE), noise-alert termination (per-sector visit bits + caps), door/lift thinker slots (no leak/double-free), level-transition resets, damage/health/ammo bounds, audio voice assignment, MUS sequencer bounds.

**Verified clean by agent 5** (mechanical sweep): no bare `>>` on a signed value anywhere (all 11 hits are unsigned-by-construction); no `load64/store64` offset reaches its record stride (THING_SIZE=128 max-offset 120, etc.); zero raw `file_write(2,...)` bypassing sakshi; the WAD-input decoders (8 map loaders, 4 patch decoders, MUS, blockmap, setu decode, wl__parse) all bound every read.

---

## 2. Prior-audit findings — current status (all 7 docs)

Full evidence lives in each dated doc; this is the *current* disposition. `FIXED@v` = shipped
and code-verified this round; `OPEN` = still present (with the slot it's now assigned);
`REFUTED` = investigated and not a defect; `N/A` = feature not present (no savegame/net/demo/DEH).

### 2.1 `2026-04-13-security-cve-audit.md` (15 findings)
- **FIXED@0.24.0** (code-verified): C1 map-index bounds (`map_validate`), C2 texture-column bounds
  (propagated to all decoders @0.28.0), C3 BLOCKMAP offsets (`player.cyr`, cap raised 256→1024 @0.32.0),
  H1 WAD short-read zero-fill (`wad.cyr`), H2 sprite min-size, #6 flat-size, #8 Medusa loop caps,
  #9 tutti-frutti wrap, #10 lump-name iteration. *(Note: the 0.28.0 audit's "C3/H1 unchanged" rows
  were themselves stale — both were fixed at 0.24.0.)*
- **SUPERSEDED**: #4 visplane "mitigation" (was actually the F17 OOB write; path replaced by the
  0.32.0 plane pool). Rec-#4 `wad_validate_lump` (H1 zero-fill covers the failure mode).
- **N/A**: #11 savegame, #12 network, #13 demo, #14 DEHACKED, #15 REJECT (none implemented).

### 2.2 `2026-04-15-black-book-handoff.md` (5 priorities + perf note)
- **FIXED**: P1 psprite coords (@0.30.1), P3 visplane correctness (@0.32.0).
- **OPEN**: P2 brightness A/B (verification task, F25 refuted the correctness worry) → v0.28.7 #2;
  P4 episode-complete screen (`level.cyr:127` wraps E1M8→E1M1) → **v0.34.x**; P5 remaining Black
  Book sub-audits → v0.28.9–.11; perf `wad_find_lump` 30 µs linear scan (accepted, init-only).

### 2.3 `2026-06-07-v0.28-graphics-hardening.md` (F01–F27)
- **FIXED@0.28.0**: F01/F02/F03/F19 patch-decode bounds, F16 dead-code, F11 flat-span, F14 weapon
  cache, F17 OOB write. **FIXED@0.32.0**: F05/F05b/F07/F08/F13 (depth clipping + plane pool),
  F09 sky (V @0.32.0, U @0.33.1). **FIXED@0.28.4**: F22 perspective-correct U/depth.
- **REFUTED**: F04, F10, F18, F21, F23, F24, F25, F27 (each investigated; not defects).
- **OPEN**: F06 native-scale midtexture (→ v0.29.x/**v0.34.x**), F12 sidedef/flat index cache +
  F15 thing-sector cache (→ v0.28.8, bench-gated), F26 automap pre-clip (→ v0.28.8), bench
  formatter (→ v0.28.11 #3), fuzz-corpus TEXTURE1/sprite/flat mutators (→ v0.28.11 #2).

### 2.4 `2026-06-13-shooting-hitscan.md`
- **VERIFIED/held**: §1 psprite fuzz (20k clean), §2 hitscan LOS, §3 projectile DoS bound,
  §4 splash recursion bound, §5 asr on all new shifts.
- **OPEN**: res-1 precise missile-vs-wall trace (partial @0.32.0 RC-G5; precise trace → **v0.34.x**,
  pairs with real thing-z); res-2 decoder fuzz targets → v0.28.11 (gated on PWAD).

### 2.5 `2026-07-04-mus-music.md`
- **FIXED@0.31.4** (code-verified §-by-§): all 7 hardening requirements + `fuzz_mus`.
- **OPEN (deferred by design)**: OPL2/GENMIDI FM, percussion ch-15, pitch bend, `D_INTER`/`D_VICTOR`
  → Music roadmap #1–4.

### 2.6 `2026-07-08-render-consistency.md` (RC-*)
- **FIXED@0.32.0**: RC-S1/S2/S3/S5/S7/S9, RC-W1/W2/W5/W6/W7/W8/W9, RC-F1/F4, RC-G1(player)/G2/G3/
  G4/G5/G6/G7, RC-G8 bundle (L1/L3/L4 + automap/intermission/door-dip/fixed_div). **RC-S4 re-fixed@0.33.1**
  (atan2 minimax).
- **OPEN residuals**: RC-S6 real thing-z (**v0.34.x**), RC-S8 `dist_dim`/fullbright (LOW), RC-W3
  native-scale V = F06, RC-W4 F_SKY1 *floors* (v0.28.7 #5), RC-F2 bsp `asr()` floor-vs-trunc
  (**upstream bsp** + pin bump), RC-F3 half-pixel yslope (v0.28.7 #4), **RC-G1 monster obstruction**
  by closing doors (rides F15 thing-sector cache → v0.28.8), RC-G8/L2 (speculative, no repro),
  RC-G8/L5 BFG (dormant), RC-G8/L6b WILV (registered-only).

### 2.7 `2026-07-09-wayland-backend.md` (W-1…W-5)
- **FIXED@0.33.0** (code-verified): W-1 registry OOB, W-2 fixed-offset key/mods, W-3 cmsg slack,
  W-4 `var[N]`-bytes stack overflow, W-5 resize-OOM dangling shm.
- **OPEN**: WF-6 per-event size table (accepted, local-compositor model). **NEW this round**: M-1
  (resize below 320×200 crash) + M-2 (env-path stack smash) + P-6 (dim overflow) extend this surface.

---

## 3. Still-open master list — ranked

**HIGH (reachable on a path that runs)**
1. **M-1** — Wayland present crash when the window is dragged below 320×200 (`framebuf.cyr`). → **v0.33.4**
2. **BSP node child-cycle gap** — `map_validate` (`map.cyr:383`) range-checks node children but never
   detects a cycle → unbounded recursion in every BSP walk on a hostile WAD. Latent (no PWAD load yet)
   but must land before PWAD support. → **v0.28.11**

**MED — conformant-input correctness**
3. **G-2** tagged use-special dispatches on the wrong sector (remote switches dead) → **v0.33.5**
4. **R-1** one-end clip clamp → far flats/textures overpaint near geometry → **v0.33.5**
5. **R-2** dead death-face (`strlen` over-read of the 8 B name scratch) → **v0.33.4**
6. **G-1** weapon-switch collapses rocket/shotgun refire cadence → **v0.33.5**
7. **G-3** intermission/death screens self-dismiss on tty autorepeat → **v0.33.5**

**MED — hostile-asset only (pre-PWAD hardening)**
8. **M-2** unbounded env-path copy → stack smash (`wl__sock_path`) → **v0.33.4**
9. **R-6/M-3/M-4** unguarded/uncapped lump allocs (TEXTURE1, STBAR) → null-write boot DoS → **v0.33.4**
10. **R-3 / G-13 / R-5 / M-6** zero-seg subsector, sector-0 fallback, dim-overflow, back-sector
    clamp / frame-stall → **v0.28.11**

**MED — engine-fidelity (larger)**
11. ~~**F06 / RC-W3 native-scale vertical texture mapping** (unblocks F-R3/F-R4/R-8)~~ → **SHIPPED v0.34.0** — native V-step `fixed_div(FIXED_ONE, col_scale)` = `dc_iscale` on all four wall sections; **F-R3/F-R4 resolved** (`ML_DONTPEGBOTTOM` wired on one-sided-mid + the masked-mid `base+112` flag); **R-8 closed** (the masked dead-store is now read). 9-map A/B (fitted byte-identical), 3-lens adversarial review, AGNOS direct-map 99.4% pixel-diff. **New LOW residual (F06-1)**: a crafted texture with declared height > 256 (`TEX_COL_MAX`) diverges the peg's `tex_h` from the clamped column data `th` on a floor-pegged column → cosmetic blank column, no crash (real DOOM textures ≤128); a one-line `tex_h` clamp closes it, byte-identical for legit content.
12. **RC-S6 real thing-z** (render + physics together; unblocks precise missile trace res-1) → **v0.34.x**
13. **RC-G1 monster-vs-closing-door obstruction** (rides F15 thing-sector cache) → **v0.28.8**
14. **P4 episode-complete screen** (E1M8→text/bunny, + `D_VICTOR`) → **v0.34.x**

**MED — upstream**
15. **RC-F2** vendored bsp `asr()` round-toward-zero not floor → fix in bsp, bump pin → **v0.33.6**

**LOW / INFO** (batched): F12/F15/F26 structural perf (v0.28.8, bench-gated); G-4/G-5/G-6/G-8/G-12
gameplay polish (v0.33.5); R-4 seg-U exact length (v0.28.7); R-7 full-IWAD lump cap; R-8/F-R3/F-R4
peg anchoring (with F06); R-9 post-cap unify; RC-S8/RC-F3/RC-W4 render residuals (v0.28.7); WF-6
wire size table; bench formatter (v0.28.11); MUS fidelity #1–4; RC-G8/L2/L5/L6b (dormant/gated).

---

## 4. Toolchain & codegen posture

- **Pin 6.4.55** (this cut). The cyrius **6.4.x minor is ABI/Language-Features**, not perf. The
  regalloc/IR performance work (the old "O4" equivalent) is **v6.5.x — Performance-Quality**. doom's
  roadmap previously gated its v0.29.x perf pass on "Cyrius O4 regalloc (v6.4.x)" — **that reference
  is stale**; the gate is re-pointed to **v6.5.x** in `roadmap.md`.
- **`>>>` native arithmetic right-shift shipped in cyrius 6.4.46** (the drishti fix). doom's `asr()`
  convention (~95 call sites) now has a native-operator migration path on the current pin. This is a
  large mechanical change with its own gate risk — **slotted v0.34.x** as an opt-in modernization,
  not rushed. Until then `asr()` remains the rule (do not introduce bare `>>` on signed values).

---

## 5. Prior audit docs (pointer index)

| Doc | Covers | Disposition |
|-----|--------|-------------|
| `2026-04-13-security-cve-audit.md` | CVE checklist, WAD parse | superseded here; all live items FIXED or N/A |
| `2026-04-15-black-book-handoff.md` | Black Book verification priorities | P1/P3 fixed; P2/P4/P5 → §2.2 slots |
| `2026-06-07-v0.28-graphics-hardening.md` | F01–F27 render hardening | 8 fixed 0.28.0, rest across 0.32.0/0.33.1; open → §2.3 |
| `2026-06-13-shooting-hitscan.md` | input→hitscan→damage posture | verified; res-1/res-2 open → §2.4 |
| `2026-07-04-mus-music.md` | MUS parser P(-1) research | all 7 hardening fixed 0.31.4; fidelity deferred |
| `2026-07-08-render-consistency.md` | walls/flats/sprites RC-* | shipped 0.32.0; residuals → §2.6 |
| `2026-07-09-wayland-backend.md` | Wayland wire security W-* | fixed 0.33.0; extended by M-1/M-2/P-6 this round |

*Next refresh: fold this document forward at the next audit round; move FIXED rows out as their
slots ship.*
