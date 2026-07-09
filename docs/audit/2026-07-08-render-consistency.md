# 2026-07-08 — Render-consistency audit (walls / flats / sprites) + module sweep

**Scope** (user-directed): wall rendering without warpage, floor/ceiling consistency, sprites fully
displaying correctly, plus any issues discovered in passing.
**Tree audited**: v0.31.4 (`main` @ 0f06753, working tree carries only the uncommitted 0.31.5 banner bump).
**Toolchain**: built and rendered under **cycc 6.4.26** (wrapper drift; manifest pins 6.4.2 — recorded per process, committed `cyrius.lock` untouched).
> **Status (2026-07-08, same day)**: **Bite A shipped in 0.32.0** (RC-S3/S4/S5, RC-W1/W2/W5) and
> **Bite B shipped in the same cut** (RC-S1/S2/S9, RC-W6 via drawseg depth clipping — the 0.28.6
> keystone — plus **RC-W9**, a new finding fixed during implementation: seg scale/U endpoints were
> not re-anchored after screen-edge clamping, which was the true cause of the E1M7 right-edge
> stripe band this audit had provisionally attributed to visplane bleed). The **0.28.5 visplane
> pool + global viewz also shipped in 0.32.0** (RC-F1/F4, RC-W8 — elevation renders, flat bleed
> gone, −24% render_frame), and **Bite C shipped in 0.32.0 too** (RC-G1–G5, G7 — door entombment
> reversal, trigger spans, real use-ray, closed-portal sight/hitscan, missile spawn + splash LOS,
> alloc guards). **Bite D also shipped in 0.32.0** (RC-W4 sky V anchor, RC-F3 flat V parity,
> RC-S6/S7/S8 slices, RC-W7, 7 of the RC-G8 LOWs — plus the see-through-gun fix: palette index 0
> is a real color, not the patch transparency key, in the psprite/sprite blitters). Remaining:
> RC-G6 (QEMU-gated), RC-W3 native-scale V (0.29.x), RC-F2 bsp asr (upstream), the F-R6
> texture-path fill-mask, real thing-z, and G8's L2/L5/L8. See `roadmap.md` + CHANGELOG `[0.32.0]`.

**Verdict**: no memory-safety regressions found in the render path (the 0.28.0/0.31.2 patch-decoder
hardening holds; `framebuf_pixel` bounds every write). The findings are **visual-correctness and
gameplay-correctness** bugs. Two architectural keystones already on the roadmap (depth-aware
clipping, visplane pool) are re-confirmed with much stronger evidence than before; eight NEW
self-contained defects were found, five of them cheap to fix.

## Method

1. Line-by-line walk of `render.cyr`, `sprite.cyr`, `texture.cyr`, `fixed.cyr`, `framebuf.cyr`
   primitives, and the vendored `asr()` (`lib/bsp.cyr`).
2. Parallel agent sweep of the 14 non-render modules (map/things/player/doors/level/status/menu/
   automap/input/main/wad/tick/tables/fixed) — findings adjudicated and spot-re-verified.
3. **Staged-viewpoint PPM evidence**: a `/tmp` repo copy patching `view_x/view_y/view_angle` in the
   `--ppm` path (spawn-exact override reproduces the shipping PPM **byte-for-byte**, validating the
   harness), plus WAD-side Python (THINGS type scan, BSP point-to-sector walk, sight-line linedef
   crossing scan) and an instrumented per-sprite trace (`efmt_int` markers).

Repro coordinates for every visual finding are in the appendix. All staging on E1M1, DOOM1.WAD
shareware, skill 3 (96 things).

---

## Findings — sprites (RC-S)

| # | Sev | Status | Finding |
|---|-----|--------|---------|
| **RC-S1** | HIGH | NEW (root = known F07) | **Near sprites are deleted outright by farther portals.** The sprite pass clips every pixel to the frame-final `clip_top/clip_bottom` (`sprite.cyr:385-418`), which after the BSP walk holds the *narrowest opening along the whole column*, not the opening at the sprite's depth. Proven: barrel at (1312,−3264) viewed from (1312,−3400) — 136 units, dead center, the sight line crosses only line 40 (a floor step; crossing scan) — is collected and projected (trace: `screen_x=160, sy1=111, sprite_h=37`) yet **zero pixels survive**: the window assembly far beyond it narrows those columns to a band above the barrel. In play: monsters/items vanish whenever a window, step edge, or door frame lies anywhere behind them. |
| **RC-S2** | HIGH | NEW (root = known F07) | **Sprites draw on top of nearer one-sided walls (x-ray).** Solid walls set `clip_solid` but never narrow `clip_top/clip_bottom` (`render.cyr:976`), and the sprite pass never reads `clip_solid` — so a sprite behind a solid wall passes the clip test and paints over the wall. Observed: staged view (1312,−3400) ang 256 shows far-NE monsters (~1300 units, several rooms away) as specks pasted on the near east wall. |
| **RC-S3** | HIGH | NEW | **12 shareware thing types are spawned and functional but invisible** — present in `things.cyr` (`TTYPE_*`) but missing from `sprite_build_lookup` (`sprite.cyr:44-85`): **spectre 58 (×63 across E1M3–M9 — invisible attacking monsters)**, shell box 2049 (×35), rocket box 2046 (×22), pool of blood 24 (×23), dead player 15 (×21), backpack 8 (×10), rocket ammo 2010 (×8), candelabra 35 (×8), blur sphere 2024 (×7), radsuit 2025 (×7), computer map 2026 (×4), goggles 2045 (×2). 210 things total. Fix: add lookup entries (spectre → SARG until a fuzz effect exists; 15 → PLAY N-frame; 24 → POL5). |
| **RC-S4** | HIGH | NEW | **`fixed_atan2` compresses each quadrant octant to half range with a 45° jump at the diagonal** (`tables.cyr:106-108`): both branches use coefficient **128** where the diamond-angle form needs **256** — outputs reach only 64 at 45° then jump to 192; 65–191 unreachable; max error 22.5°. Consumers: `sprite_calc_rotation` (wrong 8-view rotation, facing snaps 45° as the viewer crosses a monster's diagonal), monster chase heading (`things.cyr:541`), stereo pan (`audio.cyr:437`). Mechanical fix: `256*ay/(ax+ay)` / `256 − 256*ax/(ax+ay)`. |
| **RC-S5** | HIGH | NEW | **Magnified sprites render as shredded horizontal slices.** The vertical scaler is source-driven — `scr_y = sy1 + src_y * sprite_h / ph` (`sprite.cyr:414`) — so when `sprite_h > ph` (closer than ~160 units for a 1:1 sprite) successive source rows skip screen rows, leaving unfilled gaps. **Visually confirmed**: staged view (2272,−2528) ang 256 — the trooper 96 units ahead is torn into venetian-blind stripes. The horizontal axis is already screen-driven (`src_col = c*pw/sprite_w`, gap-free); make the vertical axis match (iterate screen rows, map back to source; posts become run fills). This is the dominant close-combat sprite artifact. |
| **RC-S6** | MED | NEW | **No thing-z in the sprite pass — everything is floor-anchored** (`sprite.cyr:352-357`, overwriting the top-offset `sy1` computed at :324): rockets in flight render sliding along the floor; any future floater (lost soul, cacodemon) will too. Matches the engine's 2.5D gameplay (missiles also have no z — see roadmap "precise missile trace" row); the render and physics halves should land together. |
| **RC-S7** | LOW | NEW | **128-visible-sprite cap keeps the first 128 by thing index**, not the nearest (`sprite.cyr:234-236`), and drops the rest silently — crowded UV views on big maps pop arbitrary sprites. Log the drop; prefer distance-sorted truncation. |
| **RC-S8** | LOW | NEW | **No fullbright sprite frames** — explosions/fireballs/pickups dim with sector light + a nonstandard `dist_dim` term (`sprite.cyr:360-365`) instead of vanilla scalelight semantics. Cosmetic parity. |
| **RC-S9** | MED | KNOWN (0.28.6 #4) | **Sprites always draw after all masked midtextures** (`main.cyr:323-325` + `render_frame` ordering): a monster behind a grate draws on top of the grate. No depth interleave until the 0.28.6 silhouette work. |

## Findings — walls (RC-W)

| # | Sev | Status | Finding |
|---|-----|--------|---------|
| **RC-W1** | HIGH | NEW | **Sky-to-sky portal upper walls are drawn; vanilla suppresses them.** When front and back ceilings are both F_SKY1, DOOM draws no upper wall (the sky reads as continuous). `render_seg` draws it unconditionally (`render.cyr:917-937`). **Visually confirmed**: staged view (2200,−3400) ang 768 — the E1M1 courtyard's south alcoves (lines 250–252, sector 5 ceil 216 vs sectors 20/22/47 ceil 24/64) show a screen-filling STARTAN3 band where the real game shows open sky. Fix: if `is_sky` and back ceiling is also F_SKY1, skip the upper-wall draw and clip the ceiling boundary at the front projection (vanilla `worldhigh = worldtop`). |
| **RC-W2** | HIGH | KNOWN (wall-path #6) — **evidence upgraded** | **Closed-sector portals are never promoted to solid walls.** Staged view (1420,−2496) ang 0 at the E1M1 spawn-room door (line 151/152, BIGDOOR2, back sector 4 ceil==floor==0): the door face renders but a **see-through seam cuts across it** — with `back_ceil==back_floor`, `clip_top == clip_bottom` leaves a ≥1-row band open through which farther-room geometry (and sprite fragments) bleed. The column also never sets `clip_solid`, so the all-occluded early-out can't fire (perf). Vanilla promotion test: solid if `back_ceil <= back_floor \|\| back_ceil <= front_floor \|\| back_floor >= front_ceil` (also closes the projected floor-above-ceiling inversion case). Fix at `render.cyr:959-960` + mark solid. |
| **RC-W3** | MED | KNOWN (F06/F-R3/F-R4) | **Stretch-to-fit vertical texture mapping is the engine-wide "warpage" source**: every wall section maps `tex_h` over its pixel height (`render.cyr:922,945,967`; masked `:1226`) — textures squash/stretch with wall height, door textures stretch while the door animates, peg flags only approximate. Native-scale V (`rw_scale` path) remains the 0.29.x deep-fidelity slot; F-R3/F-R4 stay entangled with it. Horizontal warpage is fixed (F22 perspective-correct U/depth verified in place, incl. the swap-corrected U endpoints). |
| **RC-W4** | LOW | KNOWN (F09) | **Sky V starts at each column's clip top** (`render_draw_tex_column(col, ct, …, 0, …)` — `render.cyr:866`), not at a horizon/screen anchor, so the sky texture shears where wall tops vary. 0.28.7 #1; F_SKY1 *floors* still not treated as sky (0.28.7 #5). |
| **RC-W5** | MED | NEW | **Masked midtextures render in front-to-back storage order** (`render_masked_segs` iterates `0..masked_count`, `render.cyr:1162`): with two grates in line, the *farther* one draws last and overwrites the nearer. One-line interim fix: iterate in reverse (BSP stored them near-first) until 0.28.6 does it properly. |
| **RC-W6** | MED | KNOWN (F05/F05b) | **The masked pass ignores the clip arrays entirely** (`render.cyr:1195-1242` — only the sector opening bounds the draw): a grate behind a nearer solid wall or below a nearer step edge paints over it. Same keystone as RC-S1/S2. |
| **RC-W7** | LOW | NEW | **`MASKED_MAX = 64` drops overflow silently** (`render.cyr:467`): complex scenes lose grates with no log. Log the drop + measure a real peak before sizing. Also: the entry-layout comment says 13 fields/104 B; the struct is 15 fields/120 B (comment rot). |
| **RC-W8** | MED | KNOWN (0.28.5 #5/#6) | **Per-seg eye model + one-sided portal clip bounds re-confirmed**: `eye_h = front_floor + 41` per seg (`render.cyr:815`) flattens world elevation (all floors project identically at a given depth; no global `viewz`), and portal clip updates take only the back sector's projections (`:959-960`) instead of `max(ceil, back_ceil)`/`min(floor, back_floor)`, letting far geometry leak past near plane edges. Both are 0.28.5 items. |

## Findings — floors/ceilings (RC-F)

| # | Sev | Status | Finding |
|---|-----|--------|---------|
| **RC-F1** | HIGH | KNOWN (F08 keystone) | **Single-row visplane model re-confirmed**: per-row `x1..x2` union + last-seg-wins flat/light/height (`render.cyr:879-903`) — a row shared by two sectors gets one flat painted across both. Fresh evidence: the sky_wall staging shows a foreign flat band wrapped around the courtyard alcove. The 0.28.5 pool rewrite remains the fix; nothing cheaper is honest. |
| **RC-F2** | MED | KNOWN (wall-path #5) | **Vendored `asr()` is round-toward-zero, not floor** (`lib/bsp.cyr:26` — `-((-val) >> bits)`), so `fixed_to_int` truncates negatives: flats show a doubled texel band straddling the world axes (2-unit-wide texel 0 repeat). Fix upstream in bsp, bump the pin. Everything downstream of `fixed_to_int`/`fixed_mul` on negative values carries the same ≤1-ulp toward-zero bias. |
| **RC-F3** | LOW | KNOWN (0.28.7 #3/#4) | Flat V axis uses `+worldY` (vanilla `−worldY`) — all flats vertically mirrored; half-pixel yslope/column-center offsets missing. Cosmetic parity, PPM-diffable. |
| **RC-F4** | LOW | NEW | **Sub-41-unit-tall sectors project ceiling spans at the wrong distance**: the span pass falls back to `VIEW_HEIGHT` when the stored per-row ceiling delta is ≤0 (`render.cyr:1067-1068`), i.e. any ceiling lower than 41 above its floor (crushers, closing doors, crawlspaces) gets texel scale/lighting as if 41 above the eye. Subsumed by the 0.28.5 pool (real per-plane heights); not worth a point fix. |

## Findings — module sweep (RC-G, adjudicated from the parallel agent pass)

| # | Sev | Finding |
|---|-----|---------|
| **RC-G1** | HIGH | **Closing doors never obstruction-check → player can be permanently entombed** (`doors.cyr:225-236` + `player.cyr:283-290`): stand in a remotely-triggered (tag) doorway as it finishes closing — ceil==floor seals every exit crossing, the door's own lines carry no special so E does nothing, no crush damage to die from. Quit-only softlock (vanilla reverses on obstruction). |
| **RC-G2** | MED | **Walk-over triggers fire on the infinite line, not the segment** (`doors.cyr:397-407`): sign-flip test gated only by a 128-unit *midpoint* radius — walking past a short trigger line's endpoint can fire it, including **specials 52/124 = spurious instant level exits**. |
| **RC-G3** | MED | **`doors_use` has no facing/side/LOS test and uses line midpoints** (`doors.cyr:277-306`; the computed use-ray `rx/ry` is dead code): E opens doors behind you and through thin walls; any special line longer than ~128 units is unusable from near its ends. |
| **RC-G4** | MED | **Sight/hitscan skip all two-sided lines with no gap test** (`things.cyr:353-356`): the player shoots monsters through *closed* doors/lifts (it's `player_fire_ray`'s only wall test) and monsters wake through them. Gameplay twin of RC-W2. |
| **RC-G5** | MED | **Rockets materialize 32 units ahead with no spawn-point collision check** (`things.cyr:860-861`) — point-blank shots teleport the rocket through thin walls; `thing_explode` splash is distance-only (no LOS), damaging through solid walls. |
| **RC-G6** | MED | **AGNOS menus lack the F-U3-style edge latch** (`menu.cyr:282-339` + persistent scancode `key_state`): a ~100 ms E press spans ~3 tics → TITLE→MAIN→New Game→instant game start at default skill; ESC held in a submenu quits the program. Linux mostly immune (per-tick clear). QEMU-gated to verify. |
| **RC-G7** | MED | **Allocation leaks on the never-free bump allocator**: `map_alloc` re-allocs ~600 KB per map (re)load with no lazy-init guard (`map.cyr:76-83`, blockmap `:305`, `doors_init`); `status.cyr` allocs 8-byte name bufs per HUD frame (~2 KB/s at 35 Hz). Matters most on AGNOS physical memory. |
| **RC-G8** | LOW | Sweep LOWs, roadmap-tracked as one bundle: blockmap blocklist 256-entry cap (`player.cyr:182`); `map_validate` rejects right-sidedef 0xFFFF instead of degrading (`map.cyr:173-178`); BFG collectible but unfireable (weapon 8 > cap 7); automap plots the static spawn list, not live things (`automap.cyr:158-167`); first-level intermission stats stale after menu skill select (`main.cyr:382`); `door_start` −4 ceiling dip when no higher neighbor; monsters have no thing-vs-thing solidity (blob stacking) and reuse player z in step checks; `fixed_div(a,0)` sign-blind +MAX; hostile-WAD thing angles stored unnormalized. |

Agent verification notes worth keeping: `map.cyr` lump decoding (offsets, int16 sign-extension, MAP_MAX_* caps vs the 64 KB lump buffer) checks out; the Bhaskara sine table is exact at anchors with correct mirroring; no bare `>>` on signed values in the swept files; no `var buf[N]` > 100 B; BSP child-cycle validation is the one `map_validate` gap (hostile-WAD unbounded recursion — bsp-lib territory).

---

## Fix-order recommendation (roadmap detail in `roadmap.md`)

1. **Bite A — self-contained quick wins** (each small, independently PPM-verifiable, no
   architecture): RC-S3 lookup entries, RC-S4 atan2 coefficients, RC-S5 screen-driven vertical
   scaler, RC-W5 masked reverse iteration, RC-W1 sky-vs-sky skip, RC-W2 closed-sector solid
   promotion. Together these remove most of what a player currently notices (invisible spectres/
   pickups, shredded close monsters, wrong facings, door seams, walls in the sky).
2. **Bite B — depth-aware clipping keystone** (0.28.6 content: per-drawseg silhouettes) —
   **recommend pulling ahead of 0.28.5**: it closes RC-S1/S2/S9/W6, and this audit's evidence says
   the sprite failures outrank flat bleed for visible damage. The visplane pool (0.28.5: RC-F1/F4 +
   RC-W8 viewz) follows; the two are architecturally independent.
3. **Bite C — gameplay sweep**: RC-G1/G2/G3 (doors), RC-G4 (sight gap test — also unlocks honest
   monster wake), RC-G5 (missile spawn check + splash LOS), RC-G7 (alloc guards). RC-G6 rides the
   next AGNOS QEMU-gated cut.
4. **Bite D — parity polish**: RC-W3 native-scale V (stays 0.29.x/O4-adjacent), RC-W4/F3 sky anchor
   + flat V mirror (0.28.7), RC-S6/S7/S8, RC-G8 bundle.

## Security notes (P(-1) §5)

No new attack surface: this audit changes nothing; the render-path decoders (weapon/sprite/HUD/
texture/PNAMES/TEXTURE1) retain their 0.28.0/0.31.2 bounds propagation, and all staged findings are
draw-order/projection logic. Hardening candidates confirmed for the 0.28.11 refresh: blockmap
blocklist cap behavior (RC-G8), `map_validate` BSP child-cycle gap (hostile WAD → unbounded
recursion), right-sidedef 0xFFFF handling. Fuzz posture unchanged (`fuzz_wad`/`fuzz_fixed`/
`fuzz_weapon`/`fuzz_mus` all current); a sprite-lookup/patch mutator remains a good 0.28.11 corpus
addition. No `sys_system`, no unchecked writes introduced or found.

---

## Appendix — repro staging (E1M1, skill 3)

Harness: copy repo to /tmp, inject after `view_angle = player_start_angle();` in the `--ppm` block:
`view_x = X << 16; view_y = Y << 16; view_angle = A;` — build, run `--ppm`, convert PPM→PNG.
Sanity: the override `(1056, −3616, 256)` (spawn) reproduces the shipping E1M1 PPM byte-for-byte.

| Finding | X | Y | A (BAM 0–1023) | Expect |
|---|---|---|---|---|
| RC-W1 sky wall | 2200 | −3400 | 768 | STARTAN3 band filling the sky above the south alcoves |
| RC-W2 door seam | 1420 | −2496 | 0 | see-through seam across BIGDOOR2 (line 151) |
| RC-S1 deleted barrel | 1312 | −3400 | 256 | barrel at (1312,−3264) absent; only crossing = line 40 (floor step) |
| RC-S2 x-ray specks | 1312 | −3400 | 256 | far-NE monsters pasted on the near east wall (right of view) |
| RC-S5 shredded trooper | 2272 | −2528 | 256 | close monster torn into horizontal stripes |

WAD-side tooling (session scratch, rewrite as needed): THINGS doomednum scan vs `sprite_build_lookup`;
BSP point→sector walk; sight-line linedef crossing scan. All ~40-line stdlib Python against DOOM1.WAD.
