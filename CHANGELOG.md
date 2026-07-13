# Changelog

All notable changes to cyrius-doom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.34.0] - 2026-07-12 — native-scale vertical texture mapping (F06 / RC-W3)

Replaces the engine's stretch-to-section vertical texture mapping with DOOM's vanilla depth-based
mapping: **1 texel = 1 world unit**. Walls taller than their texture now TILE (repeat) it instead of
showing one vertically-squashed copy; walls shorter show a clipped slice; fitted walls (section world
height == texture height) are byte-identical to before. Design + 3-lens adversarial review; AGNOS
in-game 3D verified via direct-map boot (the menu-drive harness is currently blocked by an agnos-side
input regression — see below).

### Changed

- **Native-scale vertical texture mapping (F06 / RC-W3).** All four wall sections — upper, lower,
  one-sided mid, and masked mid — now step the texture-V coordinate by `fixed_div(FIXED_ONE, col_scale)`
  (= vanilla `dc_iscale` = `FRACUNIT / rw_scale`, depth-only) instead of
  `fixed_div(tex_h, section_screen_height)`, which forced exactly one texture copy into each wall
  section regardless of the wall's world height (the "squash"). `col_scale` is screen-pixels-per-world-
  unit (from the projection `screen_y = HALF_HEIGHT - (h - eye) * col_scale`), so the native step
  yields precisely the wall's world-height worth of texels at every depth. `render_draw_tex_column`
  already tiled tall walls via `% th` (with a negative-fixup) and clips via the F-R6 fill mask; the
  masked-mid loop clips (`src_y >= 0 && src_y < th`) since masked textures don't tile. **Verified**:
  9-map Linux PPM A/B — 12-41% of wall bytes differ (exactly the un-fitted walls), fitted walls
  byte-identical; visual A/B (E1M4 far tech-panel wall un-squashed to native proportions; E1M1/E1M8
  coherent, no black holes / smear).

### Fixed

- **`ML_DONTPEGBOTTOM` on one-sided-mid and masked-mid walls (was silently ignored).** The one-sided
  middle-texture path always top-pegged; it now bottom-anchors the texture to the section floor when
  the flag is set (`mid_ystart = (tex_h - (ceil_h - floor_h) + yoff) << 16`, the vanilla bottom-peg).
  The masked-mid path's `dont_peg_bottom` flag — stored in the masked-seg record at `base + 112` — was
  written by the seg collector but **never read**; it now bottom-pegs identically
  (`ty_pos = (tex_h - (open_ceil - open_floor) + yoff) << 16`, using the vanilla min-ceiling/max-floor
  opening). Both formulas use the true world section height and are memory-safe (one-sided tiles via
  `% th`; masked guards `src_y` on both ends, so the negative-start case when the opening exceeds the
  texture height renders transparent, not OOB).

Verification: 3-lens adversarial review (native-scale math / pegging formulas / edge-crash) confirmed
correct + safe — the native step equals `dc_iscale` with no i64 overflow and no zero-underflow
(`NEAR_CLIP` bounds `col_scale` so the step floor is 1), both pegging formulas match vanilla and are
sign-correct, and `base + 112` is a valid in-bounds field of the 120-byte masked-seg record with no
OOB / div-by-zero / DoS. **AGNOS in-game 3D render** (via direct-map boot — see the AGNOS note) is
**99.4% byte-identical** to the Linux `--ppm` E1M1 spawn (HUD 100%, weapon 100%, scene 99.2% — the
~0.8% scene delta is the animated former-human sprite at a different tick than Linux's tick-0 render),
proving F06 is target-agnostic with no AGNOS codegen divergence.

Bench: `render_frame` **2.391 ms** (E1M1, cycc 6.4.58 — variance-neutral vs 0.33.8's 2.492 ms; the
native step drops two shifts). Binary **447,456 B** (unchanged); `doom_agnos` **433,872 B** (unchanged).
Tests **168/264** (unchanged — a render-path change is verified by the byte-identical A/B + the AGNOS
pixel-diff, not a unit assert). Fuzz ×5 clean. Built on true-pin **6.4.58** (symlink-swapped from the
drifted local 6.4.60 for the gates).

**AGNOS harness note (agnos-side, orthogonal to F06):** the `doom-ingame-smoke.py` HMP-sendkey menu
drive no longer advances past TITLEPIC on current agnos HEAD — the screendump captures the title screen,
and the flat-gate's `>= 8 colors/row` cannot distinguish title art (51-59) from a real floor (11-30), so
it false-passes. doom's `input.cyr`/`menu.cyr` are byte-identical since v0.33.0; the changed variable is
agnos's in-flight klug/klub input-ring + GPU-ring boot work. Worked around here with a direct-map boot
(one-line SELFTEST-only kernel edit, reverted) that renders E1M1 without keyboard input; the 99.4%
pixel-diff above is the decisive render check. Flagged for a separate agnos-side look.

Known low-severity (deferred → consolidated audit): a crafted texture declaring a height > 256
(`TEX_COL_MAX`) makes the peg's `tex_h` diverge from the clamped column data `th` on a floor-pegged
column → a cosmetic blank column, no crash (real DOOM textures are ≤ 128 tall).

## [0.33.8] - 2026-07-12 — pre-PWAD security hardening (BSP cycle, subsector/render bounds, decoder fuzzer)

Hardens the WAD/map parse + BSP walk surface against hostile/malformed WADs — the groundwork that
must land before PWAD (custom-WAD) support, since untrusted WADs then become loadable. Design +
adversarial review (which proved the first decoder fuzzer had zero coverage and caught it before cutting).

### Fixed

- **HIGH — hostile BSP node cycle → unbounded walk (hang / stack overflow).** `map_validate`
  range-checked node child *indices* but not the tree *structure*: a WAD whose BSP nodes form a cycle
  passed, then every BSP walk looped forever — `map_point_sector`'s descent never reached a leaf and the
  recursive render/collision walks overflowed. New `map_validate_bsp_acyclic()` does an iterative DFS
  from the root, marking each node the first time it is referenced and rejecting a second reference
  (cycle *or* shared subtree — both invalid in a DOOM binary tree); marking on push bounds the scratch
  stack to the node count. Rejected at load, so no walk ever runs on a cyclic map. All 9 shareware maps
  still validate + render.
- **Zero-seg subsector over-read (R-3).** `map_validate` admitted a `count==0` subsector, leaving
  `map_point_sector` to read `first_seg == map_num_segs` (one past the segs array). Now rejected at load
  (vanilla requires ≥1 seg); `map_point_sector` also gained a descent iteration cap and `ss_idx`/
  `first_seg`/`line_idx` bounds as defense-in-depth (returns sector 0 — a valid sector — for any leaf
  that slips through, so every caller's `map_sector_floorh` stays in bounds).
- **Render-loop frame-stall DoS (R-10).** A crafted extreme-height sector projected a masked-seg /
  wall-column span from `≈ -2³⁰`, and the row loop did ~10⁹ `continue`s before reaching row 0 (a
  minutes-long frozen frame; no OOB). R-1 (0.33.5) clamped the main seg loop; the masked-seg pass and
  the shared `render_draw_tex_column` were the residual — both now skip to the first drawable row up
  front (advancing the texture-V by the same per-row step). **Byte-identical output on all 9 maps
  (A/B PPM diff)** — bounded work, same pixels.
- **Render/sprite BSP descents self-protect** against a cycle (defense-in-depth from the review):
  `render_update_view_z` and the sprite floor-height walk gained the same iteration cap as
  `map_point_sector`, so the render path no longer depends solely on load-time validation.

### Added

- **`fuzz/fuzz_texture.cyr`** — a structured-fuzz harness for the TEXTURE1/PNAMES composite decoder
  (F19 patch-ref bound, F-S1 height clamp, F-S5 post loop, the 0.29.4 PNAMES strlen-safe copy). Emits a
  walkable PWAD (valid PNAMES + TEXTURE1 + patch structure) with fuzzed leaf fields, so the parse
  reaches the texture-definition body + patch/post decoder rather than being rejected at the
  offset-directory guard. **Coverage-verified** (instrumented probe: the post decoder is reached ~146×
  per 1000 iters — the initial version was rewritten after the review proved it had *zero* decoder
  coverage). The fuzz suite is now **×5** (wad/fixed/weapon/mus/texture).

### Deferred → roadmap

- **CVE re-walk** confirmed C3 (BLOCKMAP bounds) + H1 (WAD short-read zero-fill) remain fixed@0.24.0
  (per the consolidated audit's still-open sweep). **Bench formatter** (min > max on sub-ms averages)
  is in the cyrius **stdlib** `lib/bench.cyr`, not doom source — deferred as a cyrius-stdlib item.

### Verification

- Tests **168/264** (+4 WAD-free: BSP cycle-reject — valid tree accepted, cycle/self-loop/out-of-range
  rejected). fuzz **1000/50000/2000/1000/1000 clean** (incl. the new `fuzz_texture`); 9 maps + 5 menus at
  192,015 B; **R-10 A/B PPM byte-identical on all 9 maps**; clean-from-scratch resolve + `CYRIUS_DCE=1`
  build (530 fns / 99,379 B NOPed); deps 36/0; `render_frame` **2.492 ms** (variance — the validation is
  load-time, the render clamps are byte-identical). Binary 447,440 → **447,456 B** (`doom_agnos` 429,760
  → **433,872 B** — a 6.4.58 target-codegen delta on the added validation). **AGNOS QEMU doom-smoke PASS**
  (deterministic); **in-game PASS on a clean-frame capture** (healthy 51-59 flat signature) — the
  harness's known screendump-timing flake intermittently caught a wall-facing frame; the render
  correctness is established by the byte-identical Linux A/B + 264/264 tests (all 0.33.8 changes are
  target-agnostic). Built on true-pin **6.4.58** (symlink-swapped from the drifted local 6.4.60).

## [0.33.7] - 2026-07-12 — door/lift fidelity follow-ups

Three vanilla-fidelity fixes surfaced by the 0.33.5 G-2 adversarial review, each pre-existing.
Design + an adversarial diff review (which caught one malformed-WAD progression-blocker edge in the
new latch, fixed before cutting). No render-path change — the 9-map spawn renders are unchanged.

### Fixed

- **Doors opened to the *highest* neighbor ceiling instead of the lowest** (item 1). `door_start`
  used `find_highest_neighbor_ceil`; vanilla `P_FindLowestCeilingSurrounding` opens a door to the
  **lowest** surrounding ceiling − 4 (a door bordering rooms of different ceiling heights rises only
  as high as its lowest neighbor). Added `find_lowest_neighbor_ceil` (excludes self, min over
  two-sided neighbors) and switched the target; removed the now-dead `find_highest_neighbor_ceil`.
  Single-neighbor doors are unchanged (highest == lowest).
- **W1/S1/D1 "once" specials re-fired on re-cross / re-use** (item 3). Vanilla fires a once-only
  linedef exactly once per level (the engine zeroes `line->special`); doom re-read the special every
  time, so re-crossing a W1 line or re-pressing an S1/D1 switch re-triggered it (a W1 lift re-riding,
  etc.). Added a per-linedef `linedef_used` latch (allocated `MAP_MAX_LINEDEFS`, cleared each map in
  `doors_init`) + a `special_is_once` classifier; the once-types (D1 31/32/33/34/118, W1 2/4/10/38/121,
  S1 29/103/21/122/23/71/102) latch after firing, the repeatable DR/SR/WR forms never do. **Keyed D1
  doors (32/33/34) latch only when the key is present** so a keyless attempt stays retriable, and the
  tag-loop latch is restricted to the S1 switch subset (`special_is_switch_once`) — a malformed WAD
  that tags a keyed D1 door can't latch it keyless and lock the player out (adversarial-review fix).
- **Collision escape-rule zero-band let a move tunnel a line near its endpoints** (audit G-5). The
  drop-off same-side escape rule (0.33.1) set `crossing` only on a strict cross-product sign flip;
  the `asr(,8)`+`fixed_mul` truncation quantizes the side value to exactly 0 within ~0.01–0.13 map
  units of a line, and a 0 read as "same side" → the move escaped the ML_BLOCKING/one-sided veto.
  Now an on-line (`side==0`) endpoint counts as crossing, so the veto applies. Player-only; the
  sub-pixel band matches vanilla's tall-step/one-sided blocking (review-confirmed no re-wedge).

### Deferred → roadmap

- **Blazing/turbo door-lift speed** (117/118 doors, 122 lift, 70/71 turbo floor run at base
  DOOR_SPEED/LIFT_SPEED). Registered-WAD-only fidelity (none appear in shareware; type 70 already
  runs at ~turbo speed) and needs an invasive thinker-layout change to carry a per-thinker speed —
  deferred to a registered-WAD slot where it can be play-verified.

### Verification

- Tests **164/260** (+16 WAD-gated: door-target = lowest neighbor ceiling; `special_is_once` /
  `special_is_switch_once` classification; the `linedef_used` latch mark/check/clear). fuzz
  `fuzz_wad`/`fuzz_fixed`/`fuzz_weapon`/`fuzz_mus` = **1000/50000/2000/1000 clean**; 9 maps + 5 menus
  render at 192,015 B (no render-path change); clean-from-scratch resolve + `CYRIUS_DCE=1` build
  (530 fns / 99,379 B NOPed); deps 36/0; `render_frame` **2.556 ms** (variance — doors/collision are
  off the render path). Binary 443,336 → **447,440 B** (+4,104 for the latch infrastructure +
  helpers; `doom_agnos` 429,752 → **429,760 B**). **AGNOS QEMU doom-smoke + in-game — PASS on the
  final 0.33.7 binary** (serial `cyrius-doom v0.33.7`; one flaky in-game screendump race re-ran
  clean with correct E1M1 map stats + textured flats). Built on true-pin **6.4.58** (symlink-swapped
  from the drifted local 6.4.59). Adversarial review: item 1 + G-5 verdicts clean (INFO-only, all
  confirmed vanilla-matching); the item-3 latch's malformed-WAD edge was hardened before cutting.

## [0.33.6] - 2026-07-12 — bsp `asr()` floor fix (RC-F2) + toolchain 6.4.55 → 6.4.58

The third patch off the [2026-07-12 consolidated audit](docs/audit/2026-07-12-consolidated-audit.md):
a one-function correctness fix in the `bsp` dependency, plus the toolchain refresh to the latest cyrius.
**doom shares bsp's `asr()`** (included first from `lib/bsp.cyr`, used at all 95 signed-shift sites), so
the fix is an engine-wide fixed-point change — verified to be a strict correction with no regression.
bsp 1.2.1 is now published; doom's `[deps.bsp]` resolves it and the lock is regenerated (**36 verified,
0 failed**, bsp commit-pin `211b6c41…`).

### Fixed

- **`asr()` rounded negatives toward zero instead of flooring** (audit RC-F2). bsp's `asr(val, bits)`
  negative path returned `-((-val) >> bits)` — round-toward-**zero** (e.g. `asr(-3, 1)` → `-1`) rather
  than the arithmetic (sign-preserving) shift C's signed `>>` performs and DOOM's fixed-point + coord
  math assume (`-2`). Every `fx_to_int` / `fx_mul` on a negative operand inherited the truncation, which
  mis-wrapped flats by one texel over **negative world coordinates** and doubled the texel band
  straddling a world axis. Fixed upstream in **bsp 1.2.1** to floor: negative `val` →
  `-((|val| + 2^bits - 1) >> bits)`. Positive values are unchanged, so the all-positive call sites (the
  common case) are byte-identical — which is why the **9-map PPM A/B is byte-identical at spawn views**
  (the mis-wrap is a subtle negative-coord effect the spawn viewpoints don't exercise; the audit's
  evidence came from staged viewpoints). bsp suite **94 → 103** (+9 `asr`/`fx_to_int` floor asserts);
  its geometry tests (point-side, blockmap, frustum, traverse) unchanged and green.

### Changed

- **`[deps.bsp]` tag 1.2.0 → 1.2.1** (`cyrius.cyml`) — carries the RC-F2 asr fix.
- **Toolchain pin `cyrius 6.4.55 → 6.4.58`** (latest release). Lock regenerated from scratch
  (`rm -rf lib && cyrius deps`) — **36 deps, 1 commit-pinned (bsp 1.2.1), verifies 36/0**. Builds ran
  the true-pin toolchain (local cycc == pin == 6.4.58, no drift). 6.4.58 codegen differs from 6.4.55:
  the plain binary grows +16 B and the AGNOS binary +4,128 B (codegen tax, not a source change).

### Verification

- doom tests **164/244** (unchanged — asr floor is logic-equivalent for the positive-only assertions;
  the negative-shift call paths in collision/combat/atan2 stay green); fuzz `fuzz_wad`/`fuzz_fixed`/
  `fuzz_weapon`/`fuzz_mus` = **1000/50000/2000/1000 clean** (fuzz_fixed exercises asr heavily); all 9
  maps **byte-identical** old-trunc vs new-floor asr (the asr A/B, isolating the fix under one
  compiler), + 5 menus at 192,015 B; clean-from-scratch resolve + `CYRIUS_DCE=1` build (530 fns /
  99,379 B NOPed); deps **36/0**; `render_frame` **2.457 ms** (variance). Binary 443,320 →
  **443,336 B** (`doom_agnos` 425,624 → **429,752 B** — the 6.4.58 codegen delta). **AGNOS QEMU
  doom-smoke + in-game sendkey + aethersafha compositor-present — all PASS on the final 6.4.58 0.33.6
  binary** (serial `cyrius-doom v0.33.6`, 258-colour composited window).

## [0.33.5] - 2026-07-12 — gameplay-fidelity patch (switch/lift dispatch + render clamp + polish)

The second patch off the [2026-07-12 consolidated audit](docs/audit/2026-07-12-consolidated-audit.md),
driven by a design pass (authoritative DOOM linedef-type semantics + vanilla R_RenderSegLoop clamp
spec) and an adversarial diff review. The headline is a progression-blocker: **switch-operated doors
and lifts acted on the wrong sector** (or none), so remote switches did nothing.

### Fixed

- **Switch-operated doors/lifts dispatched on the wrong sector — a progression blocker** (audit G-2,
  the largest fix). `doors_use` routed the S1/SR switch specials (29/63 doors, 21/62/122 lifts) to the
  **back sector of the switch line** instead of the **tagged** sectors. Worse, many switch lines are
  one-sided (a switch texture on a solid wall), so `door_sec = -1` and the whole block was skipped —
  the switch was **completely inert** (verified: E1M2 line with special 62 tag 10, `back_sec = -1`, did
  nothing; type 62 is used 35× across the shareware episode). Now every S1/SR switch acts on its tagged
  sectors. The back-sector block keeps only the manual DR/D1 doors (which correctly ignore the tag), and
  **gained the D1 keyed open-stay doors 32/33/34** (blue/red/yellow), which the shareware maps use 13×
  but doom didn't handle at all — those doors were stuck closed. The walk specials (90/10/88/121) that
  were wrongly use-activatable moved out of `doors_use`; **90 (WR door) + 121 (W1 lift) were added to
  `doors_walk_trigger`** — 90 (used 20× in E1M3/4/5/7/9) had no working path before.
- **Floor-lower specials re-sealed the path** (audit G-2, motion fix). Specials 23/38/70/71/102 ("lower
  floor to …") were routed to `lift_activate` = lower-**wait-raise**, so a floor that should permanently
  drop to open a route rose back up after ~3 s (or could crush). New one-way `DS_FLOOR_LOWER` thinker
  (+ `find_highest_neighbor_floor` + `floor_lower_to_{lowest,highest,highest8}`) lowers and **latches**.
  Present in E1M5/E1M7.
- **Far flats/textures overpainting nearer geometry through a portal** (audit R-1). The seg loop clamped
  wall/plane/sky sections to the clip window on only one end; vanilla R_RenderSegLoop bounds every section
  by **both** `ceilingclip` and `floorclip`. A raised-sill or low portal let a far low ceiling / far high
  floor project past the window and, since the plane pass runs after all walls, overpaint. Added the
  missing far-end clamps (`ceil_screen ≤ cb+1`, `floor_screen ≥ ct-1`, `upper_y2 ≤ cb`, `lower_y1 ≥ ct`).
  **A/B PPM diff: all 9 shareware maps byte-identical** (the clamps are dormant at spawn views —
  adversarial review confirmed they're correct AND safe, never producing an OOB or inverted draw).
- **Weapon-switch collapsed the refire cadence** (audit G-1). Switching weapons ran `render_set_weapon`,
  which resets `weapon_fire_frame`/`weapon_fire_timer` to 0 — re-opening the fire gate. Tapping a weapon
  key mid-refire fired the rocket/shotgun every ~3 ticks instead of every 20/18 (a multi-× DPS exploit,
  the class 0.30.0 closed for the fire key). Weapon switching is now deferred while a fire animation is
  in flight (`weapon_fire_frame != 0`).
- **Intermission / death screen self-dismissed on a held key** (audit G-3). The single-poll release gate
  armed on the tty-autorepeat gap (`input_flags` pulses 0 between bytes) and the next byte dismissed the
  screen in ~28 ms. Replaced with a **minimum display time (~1 s) + sustained-release counter**: the
  minimum lets any fresh-press key-repeat *initial delay* pass before arming, so a held key (in steady
  autorepeat by then) can't false-arm regardless of the OS repeat-delay setting — hardened past a naive
  N-tick threshold after the adversarial review flagged its dependence on that uncontrolled parameter.
- **Blue armor degraded to green absorption below 100** (audit G-4). Absorption was inferred from the live
  count (`> 100` = ½) rather than the pickup type, so a depleting blue set silently dropped to ⅓ once it
  fell below 100. Now a persistent `player_armor_class` (green 1, blue 2), set at pickup and cleared at 0.
- **Melee monsters hit through thin walls** (audit G-6). The melee-release branch had no sight re-check
  (only the ranged branch did), so a player ducking behind a wall during the wind-up still took the hit.
  Gated on `thing_check_sight` like the ranged branch (vanilla P_CheckMeleeRange includes P_CheckSight).
- **Repeated use on an already-open stay-door replayed the sound + spawned a dead thinker** (audit G-8).
  `door_start` now early-returns (before allocating a slot — no leak) when the sector is already at/above
  the open target, so held use on an open door no longer spams `DSDOROPN` / steals mixer voices.
- **Sergeants used the pistol sound** (audit G-12). Shotgun sergeants (`TTYPE_SHOTGUY`) now play `DSSHOTGN`.

### Verification

- Tests **164/244** (+9 WAD-free: armor-class absorption — G-4; +8 WAD-gated: one-way floor-lower motion +
  already-open-door no-op — G-2/G-8). fuzz `fuzz_wad`/`fuzz_fixed`/`fuzz_weapon`/`fuzz_mus` =
  **1000/50000/2000/1000 clean**; all 9 maps + 5 menus render at 192,015 B; **R-1 A/B PPM diff byte-identical
  on all 9 maps**; clean-from-scratch resolve + `CYRIUS_DCE=1` build (523 fns / 98,164 B NOPed); deps 36/0;
  `render_frame` **2.347 ms** (variance — R-1's per-column branches are negligible). Binary 439,208 →
  **443,320 B** (+4,112 for the floor-motion infrastructure + dispatch; `doom_agnos` 425,608 →
  **425,624 B**). **AGNOS QEMU doom-smoke + in-game sendkey + aethersafha compositor-present — all PASS on
  the final 0.33.5 binary.** Built on the **true pinned 6.4.55** (toolchain symlink-swapped from the
  drifted local 6.4.58; pin unchanged — a fix-only patch). Adversarial diff review: doors + render verdicts
  clean (pre-existing INFO items → roadmap); the one MED it surfaced (G-3 threshold) was hardened before
  cutting.
- **Deferred → roadmap** (pre-existing, surfaced by the G-2 review): doors open to the *highest* neighbor
  ceiling (vanilla: lowest); blazing/turbo specials run at base speed (no fast variant); W1/S1 one-shot
  specials lack a per-linedef used-latch (re-fire on re-cross).

## [0.33.4] - 2026-07-12 — security + safety quick-wins (first audit-slot patch)

The first patch off the [2026-07-12 consolidated audit](docs/audit/2026-07-12-consolidated-audit.md) —
six small, high-confidence fixes. No render-path or gameplay-logic changes; the two HIGH items
are user-reachable crashes on the desktop-window backend, the rest are malicious-WAD hardening
and a deterministic HUD bug.

### Fixed

- **Wayland window crash when resized below 320×200** (audit M-1, HIGH). `framebuf_present_wayland`
  blits a fixed 320×200 frame, but drag-resize (bite-4, live since 0.33.0) adopted any compositor
  configure `> 0`, so a sub-320×200 window overran the shm pitch and — on the far double-buffer —
  ran past the mmap end → SIGSEGV. Now `win_open`/`win_resize_apply` clamp the adopted size through
  a shared `win__clamp_size` (floor 320×200), and `win_open` sends `xdg_toplevel.set_min_size(320,200)`
  so compliant compositors don't try. `win_poll_events` compares the *clamped* target, so a
  compositor that keeps sending a sub-min size no longer churns shm rebuilds.
- **Compositor-dimension integer overflow** (audit P-6). The shm buffer size is `w*4*h*2`; a hostile
  or buggy compositor dimension near 2³¹ wraps to a small positive → undersized mmap vs a larger
  blit. `win__clamp_size` caps both axes to 16384, and `shm_create` gained an explicit overflow
  guard (`bsize/h == stride`, `psize >= bsize`).
- **Unbounded env-path copy → stack smash** (audit M-2). `wl__sock_path` copied `WAYLAND_DISPLAY` /
  `XDG_RUNTIME_DIR` (arbitrary length) into a 128-byte stack buffer and then a 120-byte `sockaddr_un`
  with no bound. `wl__copy_cstr` now takes a capacity and refuses to write past it; an over-long env
  fails closed (`wl_connect` → −1 → the fb0/ppm fallback), capped at the 107-char `sun_path` limit.
- **Dead death-face** (audit R-2). The face-name scratch was `alloc(8)`, but the face lumps
  ("STFDEAD0" etc.) are exactly 8 chars — so no NUL fit, and `wad_name_eq`'s `strlen` over-read the
  adjacent `face_patch_buf` (nonzero after the first draw) → every lump rejected → `STFDEAD0` never
  resolved → the death face rendered as a blank cutout (same over-read class as the 0.29.4 PNAMES
  bug). Now `alloc(9)` + an explicit NUL; the sibling `STYSNUM` HUD-digit names (also 8 chars) got
  the same fix in `status_init_font`.
- **Unguarded/uncapped lump allocations** (audit R-6/M-3/M-4). `texture_init`'s `TEXTURE1` alloc and
  `status_init_font`'s `STBAR`/`STARMS` allocs took a WAD-controlled size (up to ~4.29 GB via a
  `read_le32` directory field) with no null guard and no cap — a malformed lump → `alloc`→0 →
  `wad_read_lump_into`'s `memset(0,0,sz)` null-write crash at load. Now capped (TEXTURE1 ≤ 16 MB,
  STBAR/STARMS ≤ 64 KB — far above real IWADs) and null-guarded, mirroring the existing PNAMES guard.

### Changed

- **Defensive rewrite of the remaining sparse hot-path `switch`es as if/else** (audit G-7). The
  `doors_walk_trigger` walk-type / exit / tag-dispatch switches and the `things_check_pickups`
  pickup dispatch had sparse/out-of-order labels (2..2049) in per-tick functions with post-switch
  work — the exact cycc codegen shape that smashed the enclosing return address in `thing_animate`
  and `doors_use` (both previously rewritten). Converted to if/else ladders per the established
  pattern. Behavior is identical; the dense `thing_category` switches (2001-2006 etc., each case
  returns) are left as intentional jump-table candidates.

### Verification

- Tests **155/155** WAD-free (+6: `win__clamp_size` floor/cap) + **227/227** full (+3 WAD-gated:
  `STFDEAD0` + `STYSNUM0/9` resolution — R-2; `status.cyr` added to the harness). fuzz
  `fuzz_wad`/`fuzz_fixed`/`fuzz_weapon`/`fuzz_mus` = **1000/50000/2000/1000 clean**; all 9 maps + 5
  menus render at 192,015 B; clean-from-scratch resolve + `CYRIUS_DCE=1` build (523 fns / 98,164 B
  NOPed); `render_frame` **2.425 ms** (variance); deps 36/0. Binary 439,192 → **439,208 B** (+16;
  `doom_agnos` 425,640 → **425,608 B**). **AGNOS QEMU on the final 0.33.4 binary: doom-smoke +
  in-game sendkey + aethersafha compositor-present — all PASS** (the M-1/P-6/M-2 Wayland fixes are
  Linux-only `#ifndef CYRIUS_TARGET_AGNOS`; the R-2/R-6/G-7 fixes are on the shared path and covered
  by the agnos harnesses). Built with the versioned `~/.cyrius/versions/6.4.55/bin/cyrius` (pin
  unchanged from 0.33.3 — a fix-only patch).

## [0.33.3] - 2026-07-12 — audit round: toolchain/dep refresh + setu present-leak fix + roadmap reorg

A consolidation cut. Bumped the toolchain and dependencies to latest, ran a five-agent audit
over the whole tree, consolidated all seven prior audit docs into one open-findings ledger, and
re-organized the findings onto the roadmap as new patch/minor slots. One live security defect —
found by the audit and fixed **upstream in setu** this cut — plus the doom-side setu input
hardening it enabled.

### Fixed

- **setu present-buffer leak (audit P-1, HIGH) — a system-wide present DoS on AGNOS.**
  `setu_client_present` created a NEW kernel shared-memory buffer on **every** frame and never
  freed any (`setu_buf_close` had zero callers; `SetuClient` had no field to cache an id). agnos
  has only **16 system-wide shm slots**, so within ~0.5 s of 35 Hz play doom exhausted them —
  every later present (doom's *and every other setu client's*) fell back to the inline-TCP path,
  which is exactly the 2 KB-loopback-window stall the shared buffer exists to avoid, and the slots
  were unreclaimable until reboot. On Linux it leaked one `/dev/shm/setu-buf-*` file per frame.
  **Fixed at the source in setu 0.5.1** (cache one buffer id, rewrite it in place each present,
  recreate on resize, free it in `setu_client_close`) and re-vendored here. QEMU-verified: the
  aethersafha compositor-present smoke composites doom as a live window (258 colours, 923 K
  non-black px) and the in-game harness runs clean.
- **setu input state-machine hardening (audit P-2/P-3/P-4/P-5)** — the setu input path had not
  caught up to the hardening the Wayland path already had. Now: **P-2** focus-loss clears every
  key latch (`doom_setu_focus` from `SETU_INPUT_FOCUS`; else a held key whose release went to the
  newly-focused window walked the player forever); **P-3** a non-key message no longer ends the
  frame's input drain early; **P-4** the per-poll `setu_msg_new()` allocation (a continuous leak
  on agnos's never-free allocator, ~12 KB/s idle) is now a persistent lazily-alloc'd scratch;
  **P-5** setu 0.5.1's new `setu_client_poll_input` reassembles the TCP stream, so coalesced or
  split frames no longer drop key releases (a dropped release = a stuck key). QEMU input smoke:
  balanced 10 press / 10 release over setu.

### Changed

- **Toolchain pin `cyrius 6.4.43 → 6.4.55`** (latest release). Lock regenerated from scratch
  (`rm -rf lib && cyrius deps`) — **36 entries, verifies 36/0** (was 34 on 6.4.43; the count
  tracks the 6.4.55 stdlib snapshot). Builds ran the versioned `~/.cyrius/versions/6.4.55/bin/cyrius`
  (true pin match). No source changes for the bump — codegen-clean across all 21 src modules.
- **vani vendor `1.1.0 → 1.1.1`** (`vendor/vani-core.cyr` from vani 1.1.1's dist; byte-identical to
  1.1.0 except the version header — a provenance refresh).
- **setu vendor `0.5.0 → 0.5.1`** (`vendor/setu.cyr`) carrying the P-1 fix + `setu_client_poll_input`
  (stream reassembly). The setu wire protocol is unchanged; `SetuClient` grew 24→56 bytes but is
  opaque, so doom recompiles with only the call-site changes above.

### Docs

- **New consolidated audit** — [`docs/audit/2026-07-12-consolidated-audit.md`](docs/audit/2026-07-12-consolidated-audit.md):
  the single open-findings ledger. Classifies every finding in all seven prior audit docs
  (FIXED@version / OPEN+slot / REFUTED / N/A) and adds the 2026-07-12 round's findings
  (P-1…P-8, R-1…R-10, G-1…G-13, M-1…M-10), each traced to a real call path with a confidence
  mark. Ranked still-open master list at §3.
- **Roadmap reorg** — new near-term patch band **v0.33.4** (security/safety quick-wins: M-1 resize
  crash, M-2 env-path smash, R-2 dead death-face, R-6/M-3/M-4 lump-alloc guards, G-7 sparse-switch
  defensive rewrite), **v0.33.5** (gameplay-fidelity: G-2 tagged-special dispatch, R-1 clip clamp,
  G-1 refire cadence, G-3 screen self-dismiss + LOW polish), **v0.33.6** (bsp `asr()` floor fix +
  pin bump). v0.28.11 gains the BSP node-cycle gap + pre-PWAD hardening; **v0.34.x** gains F06
  native-scale V, real thing-z, the episode-complete screen, and the opt-in `asr()`→`>>>` migration.
  **Codegen gate corrected**: the cyrius perf/regalloc arc ("O4") is **v6.5.x**, not v6.4.x — the
  v0.29.x perf-pass gate is re-pointed. cyrius 6.4.46's native `>>>` noted as the `asr()` path.

### Verification

- Tests **149/149** WAD-free + **218/218** full (unchanged — no gameplay logic changed this cut);
  fuzz `fuzz_wad`/`fuzz_fixed`/`fuzz_weapon`/`fuzz_mus` = **1000/50000/2000/1000 clean** on 6.4.55;
  all 9 shareware maps + 5 menu PPMs render at **192,015 B**; clean-from-scratch resolve + `CYRIUS_DCE=1`
  build passes (523 fns / 98,164 B NOPed; agnos 553 / 94,884 B); `render_frame` **2.306 ms** (variance
  vs 0.33.1's 2.349; cycc 6.4.55). Binary 426,496 → **439,192 B** (`doom_agnos` 395,968 → **425,640 B** —
  the agnos growth is the 0.33.2 setu backend + the 6.4.55 codegen tax; both were first captured in
  state.md at this cut, since 0.33.2 shipped without a state refresh). **AGNOS QEMU on the final 0.33.3
  binary: doom-smoke + in-game sendkey + aethersafha compositor-present + aethersafha input smoke — all
  PASS.**

## [0.33.2] - 2026-07-10 — DOOM on the sovereign desktop (setu backend + held keys)

### Added

- **DOOM on the sovereign desktop — a `PM_SETU` display + input backend.** doom can now
  run as a **window on the aethersafha compositor** (over the setu display protocol) on
  AGNOS, instead of only owning the raw framebuffer via blit#39 — the OS-agnostic twin
  of the Wayland window backend (agnos → setu, Linux → Wayland; the same split jalwa,
  crab and puka use). New `src/setu_present.cyr` (the setu client shell, mirroring
  jalwa's) + a `PM_SETU` runtime branch threaded through `framebuf_init` / `framebuf_flip`
  / `framebuf_shutdown` and `input_poll`. doom's existing `fb_buf` (320×200 XRGB8888 /
  BGRA, from `framebuf_blit_agnos`) is exactly what `setu_client_present` wants, so there
  is **no new rasterizer** — the frame is presented over setu's shared-buffer path
  (sidesteps the 2 KB loopback-TCP window). agnos defaults to `PM_SETU`; `framebuf_init`
  auto-downgrades to `PM_FB0` (fullscreen blit#39) when no compositor is listening, and
  `--fb0` forces fullscreen. Vendors `vendor/setu.cyr` (setu 0.5.0) + adds `net`/`result`/
  `assert` to the stdlib. Builds clean `--agnos` and host (Linux Wayland path untouched).
  **QEMU-validated** (`agnos scripts/aethersafha-doom-smoke.sh`, reusing the
  `AETHERSAFHA_SETU_SELFTEST` hook with doom seeded as the first-resident setu client): the
  compositor spawns doom, doom loads `/DOOM1.WAD`, connects over setu, and presents — the
  screendump shows the DOOM title screen composited as a window on the desktop next to crab,
  with the game loop live (map/things stats printing).
  - **Held-key input — real make/break.** doom opts into setu 0.5.0 FULL key events
    (`setu_client_request_keys` / `SETU_SURF_FULL_KEYS`), so aethersafha delivers key
    **press AND release**; `input_poll_setu` tracks persistent held state exactly like
    doom's raw-scancode path — **hold W to keep moving**, no reliance on key-repeat.
    QEMU-validated (`agnos scripts/aethersafha-doom-input-smoke.sh`, USB-xHCI keyboard +
    HMP `sendkey`): doom receives a balanced **10 press / 10 release** over setu. Requires
    setu ≥ 0.5.0 + aethersafha (which honours the flag per-surface); press-only nav clients
    (crab) are unaffected.

## [0.33.1] - 2026-07-10

Field-report patch: four live-play bugs from the first real 0.33.0 Wayland-window session
("enemies not alive/reactionary", "shots don't register damage/die", "mountains too high and
moving with the view", "locked in place after dropping off the armor platform"), all reproduced
headlessly before fixing, plus the toolchain/dep refresh. Every fix is anchored to a staged
reproduction against real E1M1 geometry (the sims live in the session scratchpad; the durable
regressions are in `tests/doom.tcyr`).

### Fixed

- **Sky: mountains sat ~28% too high and slid against the world on turns** (the render half of the
  field report). Two independent causes in `render_draw_sky_column`:
  - **V**: the sky stepped `sky_h/HALF_HEIGHT` (1.28 texels/row), squeezing all 128 SKY1 rows into
    the top 100 screen rows. Vanilla is 1:1 (skytexturemid=100 at centery=100 ⇒ texture row ==
    screen row at 320×200); now drawn 1:1 with wrap.
  - **U**: the per-column term was LINEAR in screen col while walls project tan-style — near the
    screen edges a turn sweeps wall columns up to ~2× faster than the sky, so sky features slid
    against the geometry ("moves with the view instead of locked"). Now vanilla's
    `viewangle + xtoviewangle[x]`: a projection-matched atan offset per column
    (`x_to_viewangle`, filled in `tables_init` — the table had been alloc'd since early days but
    never populated). Verified: A/B renders at Δangle=16 show sky and wall features shifting the
    same direction and magnitude (+17 vs +15 columns; the old formula moved the sky ~20 columns the
    OPPOSITE way), sky region byte-stable under player translation, wrap-exact at +90°.
    New `render_sky_u()` helper + 8 WAD-free asserts.
- **`fixed_atan2` was off by up to ~11 angle units (~3.9°) mid-octant** — the diamond-angle
  interpolation's documented error. Chase headings wobbled and **exact-aim hitscan rays whiffed
  20-unit-radius monsters beyond ~350 units** (lateral error 27 units at 457 — the reproducible
  half of "shots don't register"). Replaced with the quadratic minimax octant form
  (atan(r) ≈ (π/4)r + 0.273·r(1−r), ≤ ~0.7 unit error): the staged shot at 457 units now lands
  with lateral error 1 unit and a symmetric ±8-unit hit window. 6 accuracy asserts.
- **Drop-off wedge: dropping off a >24-unit ledge locked the player in place** (field report:
  the armor platform). The per-tick z-snap lands the player at the low floor still inside the
  ledge line's 16-unit collision radius; every subsequent move then re-failed the step-up check —
  0 of 8 directions legal, permanently. Vanilla never wedges because tmfloorz keeps the mover at
  the high floor until its bounding box clears the line. Fix: a PLAYER-ONLY escape rule in the
  collision core — when the current position already violates a line's radius, that line may only
  veto moves that actually CROSS it. Reproduced at the real E1M1 armor-walkway ledge (112-unit
  drop at (72,−3083)): was 0/8 directions free, now 7/8 with only the crossing back up vetoed.
- **Monster chase moves were step-checked against the PLAYER's floor height** —
  `thing_move_clear` routed through the player collision wrapper, so `player_z` decided every
  mover's ledge verdicts: monsters near any floor-height change froze solid whenever the player
  stood on different ground (the movement half of "enemies not alive"), and worse, a player on
  HIGH ground made cliff-edge monsters free to walk off. The collision core now takes the mover's
  own position + floor (`move_check_position`/`move_check_linedef`, resolved via the new
  `map_point_sector`), with vanilla's MF_DROPOFF rule for monsters (never step off a >24-unit
  ledge; players may). Verdicts asserted invariant under `player_z`.

### Added

- **Noise alert (vanilla `P_NoiseAlert`)** — weapon fire floods sound from the firing sector
  through open two-sided portals (closed doors stop it; `ML_SOUNDBLOCK` lines pass it once,
  vanilla's two-level rule); idle monsters in flooded sectors wake and hunt. This is how vanilla
  wakes monsters the player can't see — E1M1's computer-room zombiemen behind the barred window
  are legitimately 2D-sight-blocked (the bars are one-sided segs), so before this they dozed
  through any amount of point-blank gunfire: the "enemies not alive + shots don't register"
  combination in one scenario. WAD-gated regression: one shot at the E1M1 spawn wakes exactly the
  5 door-free HMP monsters; the southern-room imp behind the closed staircase door correctly
  sleeps through it (python BFS over the WAD's open portals confirms sector 74 unreachable).
- **Monster ranged attacks** — monsters could previously ONLY melee (attack armed under 64
  units), so anything that couldn't path to the player — ledge imps, monsters across a pit —
  stood inert forever, and nothing ever shot back ("not reactionary"). Now vanilla-style:
  zombiemen hitscan (1 bullet, (P%5+1)×3, distance-scaled hit odds), sergeants 3 pellets, imps
  and cacodemons throw fireballs (`BAL1`/`BAL2` sprites, 10 units/tic, direct damage, owner-immune,
  no splash; fireballs fly by the sight-crossing rule — through open portals over any floor step,
  stopped by solid walls/closed portals, so a ledge imp's ball no longer detonates on its own
  platform lip). Arming is distance-rolled per vanilla `P_CheckMissileRange` with a paced re-roll
  and a randomized ~1–2 s cooldown (new per-thing `aux` field; `THING_SIZE` 120→128). LOS is
  re-checked at release so shots don't cross walls the player ducked behind during the wind-up.
  Barons stay melee — their BAL7 sprites aren't in the shareware WAD (roadmap). In the staged
  E1M1 fight, monsters at 376–678 units now deal steady ranged damage (player 100→40 hp over 6 s)
  where before they were statues. 5 WAD-free asserts (zombie range damage, imp ball spawn+hit,
  melee-only demon unchanged).

### Changed

- **Toolchain pin `cyrius 6.4.30 → 6.4.43`** (latest release, published 2026-07-10); lock
  regenerated from scratch (`rm -rf lib && cyrius deps`) — **34 entries, verifies 34/0**,
  count unchanged. Builds in this cut ran the versioned `~/.cyrius/versions/6.4.43/bin/cyrius`
  (true pin match; note the versioned wrapper resolves cycc through CYRIUS_HOME, so it reported
  drift until the pin caught up — final gates all ran true 6.4.43).
- **vani vendor refresh 0.9.9 → 1.0.0** (`vendor/vani-core.cyr` from vani 1.0.0's dist; the
  `audio_*` surface is byte-for-byte identical fn-for-fn, zero code changes downstream).
- `player_find_sector` now delegates to the new general `map_point_sector(x, y)`.

Verification: tests **149/149** WAD-free (was 133; +16) and **218/218** full (was 193; +25);
fuzz `fuzz_wad`/`fuzz_fixed`/`fuzz_weapon`/`fuzz_mus` = 1000/50000/2000/1000 clean; all 9
shareware maps + 5 menu PPMs render at 192,015 B; clean-from-scratch resolve + `CYRIUS_DCE=1`
build (478 fns / 89,664 B NOPed); `render_frame` **2.349 ms** / +sprites **2.345 ms** (E1M1,
cycc 6.4.43 — prior row 2.469/2.466 on 6.4.30; the sky U map is a table lookup replacing a
division, everything else is off the render path); binary 418,224 → **426,496 B**
(`doom_agnos` 387,592 → **395,968 B**). **AGNOS QEMU doom-smoke PASS on the final 0.33.1
binary** (serial `cyrius-doom v0.33.1` + `wad loaded`, 240-color TITLEPIC screendump) plus the
in-game sendkey harness. Desktop window play re-verify on Hyprland remains the user's run
(no live compositor in the dev shell).

## [0.33.0] - 2026-07-09

### Added

**Native Wayland window backend — DOOM as a real, resizable desktop window.** doom now opens a sovereign
Wayland window on Hyprland/wlroots — raw wl protocol over the AF_UNIX socket via syscalls, **no libwayland,
no new deps** — that blits the 320×200 palette-indexed frame and takes keyboard input, replacing the
`/dev/fb0`-or-GTK-PPM-bridge (`scripts/x11view.py`) desktop story. Pulls the v1.0.0 "Wayland display backend"
item forward; the working example is [puka](https://github.com/MacCracken/puka), whose sovereign Wayland
client (`wire`/`shm`/`client` + a `win_*` seam) doom lifts and adapts. Design + phasing:
[`docs/proposals/wayland-backend.md`](docs/proposals/wayland-backend.md); security: [`docs/audit/2026-07-09-wayland-backend.md`](docs/audit/2026-07-09-wayland-backend.md).

- **The seam** — four new files under `src/platform/` (`wayland/{wire,client,shm}.cyr` + `window.cyr`), all
  `#ifndef CYRIUS_TARGET_AGNOS`, behind a runtime `present_mode` (`PM_FB0` / `PM_WAYLAND` / `PM_PPM`). One
  prepended branch in `framebuf_flip` (→ `framebuf_present_wayland`) and `input_poll` (→ `input_poll_wayland`);
  the existing fb0/AGNOS/`--ppm` bodies are untouched and stay **byte-identical**.
- **Backend selection** — `--wayland` / `--fb0` force it; `--wayland-probe` lists the compositor's globals and
  exits; else `WAYLAND_DISPLAY` present → Wayland; `--ppm`/`--ppm-menu` always force PPM (a window never pops
  during screenshot runs). Resolved **before** `framebuf_init` so init opens the right surface.
- **Pixel path** — the palette→XRGB8888 integer-scale-center blit (reused from the fb0 path; byte order
  B,G,R,X on LE — no R/B swap) into a wl_shm buffer, letterboxed. **Double-buffered**: two wl_buffers
  ping-ponged over one 2×-sized pool (`shm_pick`/`shm_cur_oid`, per-buffer release tracking) so doom writes
  the back buffer while the compositor samples the front — no tearing.
- **Keyboard** — a raw-evdev-keycode → doom `key_state` table with the Linux desktop scheme (arrows turn, A/D
  strafe, F/Ctrl fire, Space/E use, R run, Tab map, 1–7 weapons, Esc/Q quit); `poll(7)`-gated non-blocking
  drain so the compositor read never stalls the 35 Hz tick; `wl_keyboard.leave` clears latches on focus loss.
- **Window lifecycle** — xdg_shell toplevel + configure/ack, `xdg_wm_base.ping`→`pong`, close-button →
  quit, and **drag-resize** (adopt the new size, rebuild buffers, recompute scale/letterbox, repaint).
- **Security (P(-1))** — the wire parser is bounds-checked against malformed compositor messages (the
  `wl_registry.global` string length can no longer OOB-read past `wl_rbuf`; key events are size-guarded; the
  recv buffer has read-slack). SCM_RIGHTS fd-passing zeroes its ancillary scratch. See the audit doc.

Built through four reviewed "bites" (seam+window → double-buffer → keyboard [folded into bite 1] → resize),
each adversarially reviewed — the reviews caught + fixed a `var x[N]`-is-BYTES stack-overflow (I'd divided
puka's buffer sizes by 8), a menu-lock (`input_flags` hardcoded 0), and a resize-OOM dangling-pointer crash.

**No `cyrius.cyml` dep change** (pure syscalls + existing stdlib). +4 source files (25 modules now).
`VERSION` 0.32.1 → **0.33.0**; banner + CHANGELOG synced.

Verification: `--ppm`/`--ppm-menu` **byte-identical** to pre-change; tests **129 → 133** WAD-free / **189 →
193** full (+4 Wayland: pure wire codec + `wl__parse` untrusted-registry bounds); fuzz 1000/50000/2000/1000
clean; 9-map PPM + 5 menus; clean-from-scratch resolve+DCE (34/0 lock unchanged, 477 fns / 89,580 B NOPed);
**AGNOS QEMU smoke PASS on the final 0.33.0 binary** (the backend is fully `#ifndef`'d out — agnos codegen
unregressed). `render_frame` **2.469 ms** (variance — the Wayland present is off the render path). Binary
392,304 → **418,224 B** (+25,920 B: the four platform files). **The window itself is user-verified on
Hyprland** — the dev shell has no live compositor, same build-here/confirm-on-hardware split as the audio and
AGNOS paths.

## [0.32.1] - 2026-07-08

### Fixed

**`--audio-test` was also playing music.** `load_map()` (which the self-tests run to
prime the device + WAD caches) calls `music_start()`, and `music_volume` defaults to
8, so E1M1's `D_E1M1` MUS track mixed into every `audio_tick()` of the SFX test
(`audio_mix_chunk` sums `music_render_sample()` into each source sample). The two
self-tests are now cleanly separated: **`--audio-test` calls `music_stop()` first**
(clears `music_playing`, so `music_render_sample()` returns 0 → the six SFX + L/R pan
pings play with no music underneath), and **`--music-test` calls `music_start()`** to
re-arm the track from bar 1 and triggers no SFX in its loop — it is the music-focused
counterpart. Log lines now say "(sfx only)" / "(music only)". Audio-path-only change:
render/collision/boot untouched, so all render gates are byte-identical.

Verified: new WAD-free regression group asserts the mechanism — a playing voice renders
non-silent output (it *would* mix in), and after `music_stop()` every sample is pure
silence. Tests **115→118** WAD-free / **175→178** full. `render_frame` 2.429 ms
(variance — off the audio path); binary 392,280→**392,304 B** (agnos 387,504→387,528 B).
Gates re-run under the pinned cyrius **6.4.30** (versioned binary; the local wrapper has
drifted to 6.4.31): clean-from-scratch resolve+DCE, 4 fuzzers clean, 9-map PPM + 5
menus, **AGNOS QEMU doom-smoke PASS on the final binary** (serial `cyrius-doom v0.32.1`
+ `wad loaded`, 240-color TITLEPIC). Audible confirmation on the jack is the user's run
(the agent context can't open `/dev/snd`).

## [0.32.0] - 2026-07-08

### Fixed

**Bite A of the [2026-07-08 render-consistency audit](docs/audit/2026-07-08-render-consistency.md)**
(2026-07-08) — the six self-contained quick wins, each verified against staged-viewpoint PPMs
(repro coordinates in the audit appendix):

- **RC-S3 — 12 shareware thing types were invisible.** They spawned and functioned
  (`things.cyr` knows them) but had no `sprite_build_lookup` entry: spectre 58 (**63
  invisible attacking monsters** across E1M3–M9; renders as a plain demon until a fuzz
  effect exists), shell box 2049, rocket box 2046, rocket ammo 2010, backpack 8,
  dead marine 15, blood pool 24, candelabra 35, blur sphere 2024, radsuit 2025,
  computer map 2026, goggles 2045. Corpse decor now spawns on its corpse frame
  (15 → PLAY N; gibs 10/12 → PLAY W — these two previously rendered as **standing
  marines**). Verified: staged item/corpse views + spectre lump trace (SARG resolves;
  its remaining crop is the known 0.28.6 clip keystone).
- **RC-S4 — `fixed_atan2` compressed every octant to half range** (coefficient 128
  where the diamond-angle form needs 256): outputs 65–191 were unreachable and the
  result jumped 64→192 crossing the diagonal — wrong sprite rotation bands, monsters
  chasing up to 22.5° off-course, stereo pan snapping 45°. Now full-range and continuous
  to ≤2 angle units at the octant seam.
- **RC-S5 — magnified sprites drew as shredded horizontal stripes.** The vertical
  scaler iterated source rows (`scr_y = sy1 + src_y*sprite_h/ph`), skipping screen rows
  whenever a sprite was closer than ~160 units. Columns now decode into a dense buffer
  and the draw loop iterates screen rows sampling the source — same scheme the
  horizontal axis already used. Verified: the close-range trooper staging shot.
- **RC-W1 — sky-to-sky portal upper walls were drawn** where vanilla suppresses them
  (`worldhigh = worldtop`): the E1M1 courtyard showed a screen-filling STARTAN3 band
  instead of open sky. Both-ceilings-sky portals now draw the band as sky, V-anchored
  with the ceiling sky above it (new shared `render_draw_sky_column`; F09 horizon
  anchoring unchanged, still 0.28.7).
- **RC-W2 — closed-sector portals are now promoted to solid walls** (vanilla
  `R_AddLine`: back ceil ≤ back floor, back ceil ≤ front floor, or back floor ≥ front
  ceil). Closed doors had `clip_top == clip_bottom` — a see-through seam of
  farther-room pixels across the door face — and never occluded, so segs and sprites
  kept rendering behind them. The upper/lower sections now also meet across the old
  seam row (gap coverage), closed portals collapse the column clip (occludes the
  sprite pass too), and no longer burn a masked-seg slot.
- **RC-W5 — masked midtextures drew far-over-near** (forward iteration over the
  front-to-back store): a farther grate overpainted a nearer one. Drawn in reverse
  (painter's order) until 0.28.6 lands true depth clipping.

Perf: `render_frame` **3.049 ms** vs **3.048 ms** for the pre-change tree rebuilt under
the same compiler (A/B) — variance-level, no regression. Absolute numbers moved vs the
0.31.4 row (2.870 ms) because the local toolchain drifted to **cycc 6.4.29**, which also
shrinks the plain binary to **379,664 B** (untouched `texture_get_column` moved 678→727 ns
in the same run — codegen drift, not this change; the 6.4.2 pin is unchanged). E1M1 spawn
PPM differs from 0.31.4 only in sprite rows 94–121 (394 px: resampling + newly visible
items); walls/flats byte-identical. All 9 shareware maps render clean (192,015 B PPMs).

**Bite B of the same audit — depth-aware sprite + masked clipping (the 0.28.6 keystone)**
(2026-07-08). New drawseg infrastructure: the wall pass records one occlusion record per
rendered seg (screen range, endpoint scales, solid flag, eye-relative opening heights;
`DS_MAX = 512` with a one-shot `sakshi_warn` on overflow), and `render_clip_band_build`
reconstructs per-column visibility for a subject at ANY depth — only drawsegs *nearer*
than the subject occlude it. This replaces the frame-final collapsed `clip_top`/
`clip_bottom` the sprite pass used, which held the narrowest opening per column
regardless of depth:

- **RC-S1 — near sprites were deleted by farther portals.** The audit's staged barrel
  (136 units dead ahead, provably clear sight line) now renders; the E1M5 spectre that
  survived as 5 cropped rows renders whole (along with a sergeant that was also being
  swallowed). Regression assert added (render → snapshot barrel region → sprite pass →
  region must change).
- **RC-S2 — sprites x-rayed over nearer one-sided walls.** Solid drawsegs fully occlude
  anything behind them; the far-room monster specks pasted on near walls (E1M1 staging,
  E1M7 spawn) are gone.
- **RC-S9 — sprites always drew over masked midtextures.** Masked segs moved out of
  `render_frame` into a merged painter's walk inside `sprite_render_all`: masked entries
  sort far→near by midpoint depth and drain between sprite draws, so a monster behind a
  grate is overdrawn by it and one in front overdraws it. (The death-flash path in
  `main.cyr` now pairs `render_frame` with `sprite_render_all` — grates persist and your
  killer is visible.) Supersedes Bite A's reverse-iteration stopgap (RC-W5).
- **RC-W6 — masked midtextures ignored occlusion entirely.** Each masked entry now clips
  per column against the drawseg bands (its own scale lerps across the span, so
  obliquely-crossing segs resolve per-column) — a grate behind a wall or step edge no
  longer paints over it.
- **RC-W9 — NEW, found and fixed during the drawseg work: seg interpolation endpoints
  were not re-anchored after screen-edge clamping.** The column loop lerps scale and
  texture-U/z over the *clamped* `[sx1, sx2]`, but the endpoint values belonged to the
  unclamped projection — every seg crossing a screen edge had its depth, lighting, and
  texture-U compressed into the visible span (texture swim at the edges while turning,
  and the **E1M7 spawn right-edge stripe band**, previously misattributed to visplane
  bleed — now gone). Masked entries store the re-anchored endpoint scales/U-over-z
  directly (entry fields 32–56 repurposed), so the deferred pass lerps the exact lines
  the wall pass drew.

Perf: `render_frame` 3.075 ms / `+sprites` 3.050 ms (cycc **6.4.30**) vs 3.049/3.045 ms
(Bite A, cycc 6.4.29) — variance-level; the masked pass moved from `render_frame` into
the sprite phase, and the drawseg band building costs less than run-to-run noise.
Binary 379,664 → **383,896 B** (+4,232 B: drawseg machinery). All 9 maps PPM-clean;
staged re-verification of every Bite A view passed (sky courtyard, door seam,
close-range sprites, item/corpse visibility).

**Visplane pool rewrite + global viewz (the 0.28.5 keystone — world elevation is now
real)** (2026-07-08). The renderer had no view height at all: every seg projected
against its own front floor + 41 ("per-seg eye"), so all floors landed on identical
screen rows regardless of world height — stairs read as flat, ledges as paint. And
floor/ceiling flats lived in a per-screen-row model (ONE flat/light/x-range per row,
last seg wins) that bled a far sector's flat across interposed walls and sky (RC-F1,
the courtyard's white alcove band).

- **Global `view_z`** — BSP-resolved once per frame from the view coordinates (floor
  of the sector under the viewpoint + 41, DOOM viewz). Walls, masked segs, drawseg
  occlusion deltas, and **sprites** all project against it: looking into E1M1's
  blue-carpet strip now shows a genuine step down, items/monsters stand at their true
  floor heights, E1M3's recessed ceiling lights render as fixtures, and an E1M5 "black
  rectangle" artifact resolved into the window it always was.
- **Real visplane pool** (DOOM R_FindPlane/R_CheckPlane/R_MakeSpans): planes keyed by
  (height, flat, lightnum), each with per-column top/bottom spans; same-key planes
  split on column overlap; per-column spans convert to horizontal spans via the
  spanstart walk. Kills the row-union bleed (RC-F1) and gives every plane its true
  height for texel scale + zlight distance (RC-F4 — sub-41-unit ceilings were
  projected as if 41 above the eye). `PLANE_MAX = 128` with a one-shot warn; planes
  are only created on the visible side of the eye (vanilla markfloor/markceiling).
- **Portal clip bounded by BOTH sectors** (0.28.5 item 6): the opening top/bottom now
  take the lower ceiling / higher floor of the pair — far geometry no longer leaks
  past near plane edges.

Perf: `render_frame` **2.351 ms** / `+sprites` **2.346 ms** — **~24% faster** than the
old per-row double pass (3.075/3.050 ms, same compiler): spans draw once per plane
instead of re-scanning all 200 rows twice with per-row union re-stores. Binary
383,896 → **383,968 B** (+72 B net — the pool roughly pays for the deleted row-union
code). Tests 115/115 + 167/167 (the RC-S1 barrel assert re-verified against the new
elevation-true projection); fuzz clean; all 9 maps PPM-clean; staged re-verification
of every Bite A/B view passed.

**Bite C — gameplay sweep (same audit)** (2026-07-08). The module-sweep findings that
break play:

- **RC-G1 — a closing door could permanently entomb the player.** `DS_CLOSING` now
  obstruction-checks (vanilla T_VerticalDoor): if the player stands in the doorway
  and the next step would squeeze below player height, the door REVERSES to opening.
  Remotely-triggered tag doors have no special on their own lines, so being caught
  was a quit-only softlock (no inside "use", no crush damage to die from). Regression
  test rides the full open-wait-close cycle with the player in the doorway (clearance
  floor = exactly 56) and confirms the door completes its close once they step out.
  (Monsters in doorways can still be pinned — thing-side obstruction rides the F15
  thing-sector cache; roadmap.)
- **RC-G2 — walk-over triggers fired on the INFINITE line.** The crossing test was a
  sign flip gated only by a 128-unit midpoint radius, so walking past a short trigger
  line's endpoint fired it — specials 52/124 made that a spurious instant level exit.
  The crossing point is now projected onto the line and must lie within the segment.
- **RC-G3 — E (use) ignored facing entirely.** Selection was "nearest special line
  whose MIDPOINT is within 64 units in any direction": doors opened from behind,
  through thin walls, and long special lines were unusable from their ends. Now a
  real use ray (64 units along the facing, vanilla P_UseLines): nearest ray/segment
  crossing wins, and a nearer blocking line (one-sided wall or closed portal) vetoes
  a special behind it. The dispatch switches were rewritten as if/else ladders while
  in there — the sparse-label `switch` return-smash class that hit `thing_animate`
  (0.30.2).
- **RC-G4 — sight and hitscan passed through CLOSED doors.** `thing_check_sight`
  (also `player_fire_ray`'s only wall test) skipped every two-sided line; it now
  blocks when the portal is closed (lower ceiling ≤ higher floor) — no more shooting
  monsters through shut doors, and no more monsters waking through them.
- **RC-G5 — point-blank rockets teleported through thin walls.** The missile
  materialized 32 units ahead with no spawn-point check; a blocked muzzle point now
  spawns at the shooter (first tick detonates it against the wall, splashing the
  shooter — vanilla point-blank behavior). Splash damage (barrels + rockets) is now
  line-of-sight gated (vanilla P_RadiusAttack) — no more blast damage through walls
  and closed doors.
- **RC-G7 — allocation leaks on the never-free bump allocator.** `map_alloc`
  re-alloc'd ~600 KB of fixed-size arrays on every map (re)load — now lazy-init;
  BLOCKMAP gets a single fixed 64 KB buffer (+ a hard size bound — the vanilla
  format cannot exceed it); `doors_init` guards its thinker array; the HUD face/ARMS/
  grey-number and intermission name buffers (8 B per draw, per frame, ~2 KB/s) now
  use shared lazily-allocated scratches.

**Bite D — polish + the LOW leftovers (same audit)** (2026-07-08):

- **The see-through gun fixed.** DOOM patch transparency is only the gaps BETWEEN
  posts — every in-post pixel is opaque, including palette index 0, a real near-black
  color the weapon art uses heavily. The psprite blitter skipped index 0, so the gun's
  dark parts showed the scene through them; sprites had the same hole via their dense
  column buffer (index 0 doubled as the "unfilled row" sentinel — now a separate fill
  mask). Walls/masked keep the index-0 key for now (the proper fill-mask through
  `texture_get_column` is the F-R6 remainder, roadmapped with the masked rewrite).
- **RC-W4 (F09 core) — sky V anchored to absolute screen row 0**: the sky is glued to
  the screen and walls slide over it. Anchoring at each column's clip top sheared the
  sky wherever wall tops varied — the "white strips" along the E1M1 courtyard wall
  tops were the sky's bright top rows re-anchoring at every wall top; the mountain
  skyline is now continuous. (Remaining F09 nuance: the per-column horizontal term is
  linear, not tan-distributed.)
- **RC-F3 — flat V uses negated world-Y** (vanilla `ds_yfrac`): every floor/ceiling
  flat was vertically mirrored against the reference renderer.
- **RC-S6/S8 (cheap honest slice)** — in-flight rockets render at ~32 units and
  fullbright (vanilla MISL frames) instead of dragging along the floor dimly lit; real
  thing-z (render + physics together) stays roadmapped.
- **RC-S7** — sprite collection sized to `THING_MAX` (the 128-entry cap kept the first
  128 by index, silently popping arbitrary sprites in crowded views).
- **RC-W7** — `MASKED_MAX` overflow now counts + warns once (no-silent-caps), matching
  the drawseg/plane caps.
- **RC-G8 LOW bundle**: blockmap blocklist cap 256 → 1024 (silent drop = walk-through
  -wall on dense/hostile cells); right-sidedef `0xFFFF` now degrades to a skipped line
  instead of rejecting the whole map (all consumers already guard `< 0`); intermission
  stats re-derived after the menu skill re-spawn; doors with no higher neighbor no
  longer dip their ceiling −4 for the wait period; the automap plots LIVE things
  (collected items and corpses no longer haunt their spawn spots); `fixed_div(a, 0)`
  saturates sign-aware; thing/player-start angles normalized against hostile-WAD
  degrees.

**Release leftovers — the final cleanup** (2026-07-08):

- **RC-G6 — AGNOS menu edge-latching.** Every discrete menu action (any-key on the
  title, select, back, up/down navigation) now requires a FRESH press (the F-U3/F-U4
  latch pattern): on AGNOS the raw scancode `key_state` persists until the break code,
  so one held press used to blow through TITLE → MAIN → New Game → instant start, and
  a held ESC backed out of a submenu then quit the program a tick later (a non-fresh
  ESC is now consumed outright). `menu_init` swallows keys carried in from gameplay.
  The Sound sliders keep their level-triggered repeat (own debounce). Linux behavior
  preserved; menu navigation is now per-press like vanilla.
- **F-R6 CLOSED — the texture path got its fill mask** (`tex_col_mask` alongside
  `texture_get_column`, same shape as the sprite fix): masked midtextures get true
  post-gap transparency while in-post index-0 texels draw; solid walls no longer punch
  pinholes at dark texels. The palette-index-0-as-transparency conflation is now fully
  retired across psprite, sprites, HUD, walls, and grates.
- **L8-lite — monster thing-solidity** (`thing_move_clear`): chasing monsters now
  AABB-test solid things and the player before stepping (vanilla P_CheckPosition's
  thing pass) — no more stacking into one blob or melee-ing from inside your face.
  Blocking engages at radius-sum (~36 units), inside melee range (64), so combat feel
  is unchanged. (Full monster z/step parity stays roadmapped.)
- **AGNOS QEMU smoke: PASS on the final binary** — `doom-smoke.sh` boots
  gnoboot+OVMF+NVMe, execs `/bin/doom` ring-3 from the ext2 root: serial shows
  `cyrius-doom v0.32.0` + `wad loaded`, and the framebuffer screendump is the
  clean 240-color TITLEPIC. The release QEMU gate is green (audible
  `--audio-test`/`--music-test` on the jack remain user-run checks).

Final release numbers: binary **392,280 B** / `doom_agnos` **387,504 B**;
`render_frame` **2.455 ms** / `+sprites` 2.440 ms (the wall fill-mask costs one byte
load per pixel, ~+4% — net still ~20% faster than pre-visplane, ~9× headroom); tests
**115/115 + 175/175**; fuzz 1000/50000/2000/1000 clean; all 9 maps + 5 menu screens
render.

Remaining on the roadmap from this audit: RC-W3 native-scale V (0.29.x), RC-F2 bsp
`asr` floor semantics (upstream), F-U6 AGNOS scancode-prefix locals, real thing-z,
BFG mechanics (unreachable in shareware), registered-WAD WILV names. Tests 115/115 + **175/175** (+8: sight blocked/clear
pairs, missile-through-door, use-ray facing both ways, door-reversal cycle + completed
close; `doors.cyr` now included in the test harness with sound/level stubs); fuzz
2000/1000 clean on the changed paths; all 9 maps PPM-clean; `render_frame` 2.382 ms
(variance-level — gameplay is off the render path). Binary 383,968 → **388,056 B**.

### Added

- **+21 regression asserts (Bite A)** — `fixed_atan2` full-range octants (10, WAD-free:
  axis anchors, four diagonals at 128/384/640/896, monotone + continuous seam) and sprite
  lookup coverage for all 12 RC-S3 types (11, WAD-gated). **+3 (Bite B)** — drawsegs
  recorded/under-cap + the RC-S1 barrel-visibility assert (which also exposed that the
  test flow never spawned real map things — it does now). Tests **105 → 115** WAD-free,
  **143 → 167** full.

### Changed

- **Toolchain pin `cyrius = "6.4.2"` → `"6.4.30"`** (user-directed; 6.4.30 released).
  `cyrius.lock` regenerated on a clean resolve per process (`rm -rf lib && cyrius deps`):
  still 34 entries, 4 stdlib hashes moved, verifies 34/0. Builds this cut ran the
  versioned `~/.cyrius/versions/6.4.30/bin/cyrius` (reports 6.4.30, no drift) — the
  6.4.x compilers do real default dead-code elimination, so binary sizes are not
  comparable to the ≤6.4.3 rows (567 KB → ~380 KB for the same tree).

- **`vani-core` 0.9.5 → 0.9.9, and converted from a git `[deps.vani]` dep to a
  committed `vendor/vani-core.cyr`** (mirroring cyrius-polyomino / cyrius-bb).
  Since vani's 0.9.9 all-stdlib cut, resolving vani as a git dep dragged in its
  whole `[deps].stdlib` (yukti/patra/chrono/…) — `cyrius deps` failed with
  "dep vani requires 'yukti'". Vendoring the single-file shim compiles only what
  doom uses against doom's own stdlib list. vani-core 0.9.9 carries the agnos
  `audio_*` backend; doom's hand-rolled `sys_snd_*` agnos path is unchanged, so
  this is a version-currency bump. No release-ordering dependency (vendored copy,
  refresh from vani's `dist/vani-core.cyr` on a vani release).

## [0.31.4] - 2026-07-04

**Music — DOOM MUS playback wired in alongside the SFX.** The engine had a PCM SFX mixer
but no music at all. This adds a `music.cyr` module that parses the map's MUS lump
(`D_<map>`, Paul Radek's DMX format), sequences it at the 140 Hz MUS tick rate, and
synthesises the notes into the existing audio output — so the real DOOM soundtrack plays
through the same ALSA (Linux) / `sys_snd_*` (agnos) path as the SFX. Verified structurally
(the synth reproduces E1M1's actual pitches — E2/D2/C3/D3, the "At Doom's Gate" bass riff —
non-clipping) and fuzzed against malicious scores; **audible confirmation on the jack is a
user `--music-test`** (the agent context can't open `/dev/snd`). Research + the
malicious-MUS security surface: [`docs/audit/2026-07-04-mus-music.md`](docs/audit/2026-07-04-mus-music.md).

### Added

- **`src/music.cyr` — MUS sequencer + polyphonic wavetable synth.** Parses the MUS header
  (bounds-checked: magic, `scoreStart`/`scoreLen` clamped to the lump), sequences the score
  (play/release/controller/system/pitch-bend/end events + variable-length delays, every
  read bounded to the score end with iteration guards), and synthesises up to 16 voices
  from the shared 1024-entry sine table with a click-free linear envelope and a note→phase
  table (equal-temperament, built at init). Channel volume (controller 3) and all-notes-off
  (system 11) are honoured; percussion (channel 15) is skipped in v1.
- **Mixer integration** — `music_render_sample()` is summed into `audio_mix_chunk`'s output
  stage at its own `music_volume` (0–15), riding the same 11025→`audio_out_rate` upsampler
  as the SFX. When no music plays it returns 0, so the SFX-only mix is byte-identical.
- **Wiring** — `load_map` loads + starts the map's `D_<map>` track; the title/menu plays
  `D_INTRO`; `music_shutdown` at exit. Music loops on score-end (like DOOM).
- **Menu music-volume slider** — the Options→Sound screen now shows **both** an Sfx Volume
  and a Music Volume thermometer (cursor-selectable, live preview); the volume comment in
  `menu.cyr` about "no music subsystem yet" is resolved.
- **`--music-test`** — plays the current map's track through the mixer for ~15 s (headless
  audible check, mirroring `--audio-test`).
- **`fuzz/fuzz_mus.cyr`** — fuzzes the sequencer on random/corrupt score data (1000 iters
  clean); the parse bounds + guards never OOB-read or hang.
- Regression test `music: MUS synth voice` (note-on → one tonal, non-clipping voice;
  note-off releases; percussion skipped). WAD-free suite 99 → **105**, full 137 → **143**.

### Notes

- **Not FM-accurate yet.** Real DOOM used OPL2 FM synthesis driven by the `GENMIDI` lump;
  v1 is a simple sine+envelope synth (correct notes/timing, different timbre). OPL2/GENMIDI
  FM + MUS percussion are documented follow-ups on the roadmap.
- **Toolchain drift** — the local `cycc` auto-updated to **6.4.3** while `cyrius.cyml` pins
  6.4.2; 0.31.4 was built/tested/fuzzed on 6.4.3 (deps still verify 100/0, so the lock is
  unaffected). Bumping the pin is a separate toolchain decision (its own QEMU re-verify).

## [0.31.3] - 2026-07-04

**Vanilla-fidelity gameplay pass + sky-pan fix.** Follow-on to the 0.31.2 July Fable
audit playability pass: closes the batch of MED vanilla-fidelity gaps the audit's
gameplay review surfaced but that were scoped out of the play-breaking Tier-1 cut —
combat damage rolls, item/ammo pickup rules, player-vs-thing collision, secret sectors —
plus the one cleanly-doable deferred render item (sky pan rate). All Linux-verifiable;
the other deferred audit items stay blocked (AGNOS QEMU: F-U6; hardware this box lacks:
F-R5 non-32bpp fb, F-U8 audio jack; entangled with bigger render rewrites: F-R3
native-scale-V pegging, F-R6 masked-transparency).

### Fixed

- **Monster melee damage no longer time-correlated (audit follow-up to F-G1).** The melee
  roll was `3 + (tick_get_count() % 22)` — a deterministic function of the game clock, the
  same time-correlation class purged from player weapons in 0.30.0. Now `(p_random() % 8
  + 1) * 3` (3–24, DOOM's imp/demon melee formula). ([`src/things.cyr`](src/things.cyr))
- **Linux audio output rate is now negotiated, not hardcoded (audit F-U8).** 0.31.0 set
  `OUT_RATE` 48000 (the ALC897/HDA native rate, matching the agnos stream) but the header
  comment + state.md still claimed "the jack takes ONLY 44100" — a contradiction that, if
  literal, meant Linux audio could go silently dead. `audio_try_configure` now requests
  48000 first and **falls back to 44100** if a raw hw node rejects it, recording the winner
  in a new `audio_out_rate` that the Bresenham upsampler reads — so pitch stays correct at
  whichever rate the device accepts. The 48000 path is byte-identical (`audio_out_rate ==
  OUT_RATE`), and the agnos `sys_snd_*` path is untouched (hard-armed 48000, never runs the
  fallback). Upsampler verified drift-free at both rates (11025 src samples → exactly
  48000 / 44100 output frames; worst chunk 1372 / 1260 frames ≤ the 6400 B buffer). Stale
  "44100-only" comments reconciled. **Audible confirmation on the jack is pending a user
  `--audio-test`** — the agent's execution context can't open `/dev/snd` (not in the
  `audio` group / no login-session ACL), so it can't verify sound end-to-end here.
  ([`src/audio.cyr`](src/audio.cyr))
- **Item/ammo pickup rules match DOOM (audit gameplay-review gap).** Stimpacks and
  medikits healed into the shared 200 clamp and were consumed even at full health; ammo
  had no maximum at all. Now stimpack/medikit cap at 100 (maxhealth) and are *not* picked
  up at full health (soulsphere/potion/bonus still go to 200), and ammo clamps to DOOM
  maxammo (bullets 200, shells 50, rockets 50, cells 300). Regression test covers the
  no-over-heal, no-pickup-at-full, and ammo-cap cases. (A pure-ammo box walked over while
  already at max still vanishes — a smaller follow-up.) ([`src/things.cyr`](src/things.cyr))
- **Player-vs-thing collision (audit gameplay-review gap).** `TF_SOLID` was defined but
  never tested, so the player walked straight through monsters and barrels. Added
  `player_check_things` (a radius test against every `TF_SOLID` active thing) and gated the
  player's move + slide on a combined `player_move_ok` (walls AND solid things). Corpses
  (`TF_CORPSE`), items (`TF_PICKUP`), and missiles (`TF_MISSILE`) are non-solid and stay
  passable. Regression test covers the blocked/clear/corpse cases. (Monster-into-player is
  a separate gap — chase movement still uses the wall-only `player_check_position`.)
  ([`src/player.cyr`](src/player.cyr))
- **Secret sectors count and credit correctly (audit gameplay-review gap).** The
  max-secret scan read the sector *tag* (offset +48) == 9, but a DOOM secret is the sector
  *special* (offset +40) == 9 — so `level_max_secrets` was almost always 0, and
  `level_add_secret` had zero callers so nothing was ever credited. Now the scan reads the
  special, and a new per-tick `level_check_secret(player_find_sector())` credits a secret
  once when the player enters it (clearing the special to mark it found, matching DOOM's
  `P_PlayerInSpecialSector`). Verified: E1M1 now reports `max_secrets=3` (was 0).
  ([`src/level.cyr`](src/level.cyr), [`src/main.cyr`](src/main.cyr))
- **Sky pans at the DOOM rate instead of looking glued to the view (audit F-R2, the one
  cleanly-doable deferred render item).** The sky column mapped a full 360° turn to a
  single texture wrap (~0.25 texel/angle-unit), ~5× slower than the geometry, so the sky
  appeared stuck to the viewport. Now it maps the turn to FOUR wraps (DOOM's
  ANGLETOSKYSHIFT, ~1 texel/angle-unit) and one screen-width to one wrap
  (`view_angle*sky_w*4/ANG360 + col*sky_w/SCREEN_WIDTH`). `render_frame` **2.952 ms**
  (indoor spawn byte-identical — the sky path isn't hit there). Visually verified on
  E1M1's outdoor courtyard: the SKY1 mountain backdrop renders cleanly and scrolls with
  the view as it turns. ([`src/render.cyr`](src/render.cyr))


**Playability pass — acting on the July Fable full-project audit
([`docs/development/july-fable-audit.md`](docs/development/july-fable-audit.md)).** Works
down the audit's recommended fix order, each item a self-contained change. Gameplay
state-machine correctness first (the bugs that made a level unwinnable or instantly
lethal), then the one HIGH memory-safety hole and the per-frame allocator leak, then
UI/input polish. No render-path perf regression — the mixer/AI fixes are off the hot path.

### Security

- **Texture-height buffer overflow closed (audit F-S1 — HIGH).** `texture_get_column`
  bounded its column clear + patch composite by the texture's height, read straight from
  the WAD's `TEXTURE1` header (`read_le16`, 0–65535) and never clamped — but both callers
  pass a fixed 256-byte `tex_col_buf`. A WAD (any WAD accepted on the command line)
  declaring a texture height > 256 that is referenced by an on-screen wall overflowed
  that heap buffer by up to ~64 KB (zeros plus attacker-positioned patch pixels) the
  first frame it drew. Now the height is clamped to a shared `TEX_COL_MAX = 256` before
  it bounds any write, and both allocation sites reference the same constant so they
  can't drift. Latent on DOOM1.WAD (max height 128); E1M1 render is byte-identical.
  Verified with a canary test (height 4096 → zero bytes past the buffer).
  ([`src/texture.cyr`](src/texture.cyr), [`src/render.cyr`](src/render.cyr))
- **PNAMES / patch-post / PPM hardening (audit F-S3 / F-S5 / F-S6).**
  (1) `texture_init` now guards `PNAMES` with `pn_size >= 4` before reading the count and
  bounds the count by `(pn_size - 4) / 8`, so a truncated lump can't over-read past the
  allocation (F-S3). (2) The patch post-walk in `texture_get_column` now breaks on
  `post_ptr + 1 >= pdata_end`, matching the other decoders, so the length byte read stays
  in-bounds (F-S5). (3) PPM files open with `O_TRUNC | O_NOFOLLOW` added — no stale
  trailing bytes from a larger pre-existing file, and no following a symlink at the fixed
  `/tmp` paths (F-S6). ([`src/texture.cyr`](src/texture.cyr), [`src/framebuf.cyr`](src/framebuf.cyr))

### Fixed

- **Melee monsters no longer deal instant-death contact damage (audit F-G1).** In
  `thing_ai_tick`'s `STATE_CHASE` block, the "lost sight?" branch ran as a *separate*
  `if` on the same tick the monster armed its 15-tick attack wind-up, and its `else`
  (still-in-sight) path unconditionally reset `tics` to 0 — wiping the wind-up, so the
  next tick's `STATE_ATTACK` saw `tics==0` and hit immediately, looping every ~2 ticks
  (~245 DPS, sub-second death on any melee touch). Restructured to compute
  `thing_check_sight` once per tick and gate the attack-transition vs. give-up-timer
  reset through a single `if/else` so the wind-up survives. Also removes two redundant
  `thing_check_sight` calls per chasing monster per tick. ([`src/things.cyr`](src/things.cyr))
  Regression test added (`combat: melee wind-up`) — WAD-free suite 63 → 69 asserts,
  full 101 → 107.
- **Sprite renderer no longer leaks 16 KB per frame (audit F-S2).** `sprite_render_all`
  called `alloc(16384)` for its patch buffer every frame — ~560 KB/s at 35 Hz on the
  never-free bump allocator, unbounded RSS growth over a long session. Hoisted to a
  file-scope `spr_patch_buf` with the standard lazy-init guard (matching
  `weapon_patch_buf` / `_spr_prefix`); allocated once, reused thereafter. Render output
  is byte-identical. ([`src/sprite.cyr`](src/sprite.cyr))
- **PPM writer no longer leaks a row buffer per frame (audit F-S4).** `framebuf_write_ppm`
  allocated its 960-byte row buffer on every call — a steady leak in the GTK-bridge path
  that writes a PPM each frame. Hoisted to a lazily-initialised `ppm_row_buf`.
  ([`src/framebuf.cyr`](src/framebuf.cyr))
- **Doors and lifts are repeatable again — one-shot-per-map soft-lock fixed (audit
  F-G2).** `doors_tick` had no handler for the terminal `DS_CLOSED` state and never
  released a completed thinker, so a finished door/lift sat in the array forever bound
  to its sector; `door_open`/`lift_activate` then bailed on `door_find_sector`, so the
  door could never reopen and the lift could never be re-ridden (and the array capped at
  `DOOR_MAX = 32` lifetime activations). Now terminal states call `door_free` (sector :=
  -1) and a new `door_alloc_slot` reclaims freed slots, so doors/lifts re-trigger
  normally and the pool no longer exhausts. `doors_tick`'s `switch` — flagged by the
  audit as latent cycc return-smash risk — is rewritten as the codebase's standard flat
  `if (state == …)` ladder over a state snapshot. ([`src/doors.cyr`](src/doors.cyr))
- **"Open and stay open" doors latch instead of auto-closing (audit F-G3).** D1/W1/S1
  specials (2, 31, 103) funnelled through the generic open-wait-close path, so a door
  meant to stay open (and be unreopenable) instead shut after ~3 s and — with F-G2 —
  sealed permanently, potentially trapping the player. Added a `DS_OPENING_STAY` state
  and `door_open_stay`; those specials now raise once and latch (releasing their slot at
  the top). ([`src/doors.cyr`](src/doors.cyr))
- **Chasing monsters no longer phase through walls (audit F-G4).** `STATE_CHASE` set the
  monster's x/y directly with zero collision — monsters walked through one-sided walls,
  closed doors, and ledges into other rooms (worst during the lost-sight grace window).
  Movement now goes through the player's collision core (`player_check_position`, which
  blocks solid walls and closed doors z-independently): the monster tries the diagonal
  step, then slides along a single axis to round a corner, else holds. (Step-height still
  references the player's elevation — a small known inaccuracy, far better than none.)
  Regression coverage: a chaser still closes distance on open ground (`72` WAD-free
  asserts). ([`src/things.cyr`](src/things.cyr))
- **Spent barrels stop shielding the monster behind them (audit F-G5).** A detonated
  barrel kept `TF_SHOOTABLE` forever — its `STATE_DIE → STATE_DEAD` transition lived only
  in the monster-only AI path (`thing_ai_tick` early-returned for decorations), so it
  froze on a death frame as a permanent bullet-shield that silently absorbed every shot
  fired across it. Now `thing_damage` drops shootable/solid the instant a barrel blows,
  and `thing_ai_tick` advances a dying decoration to an inert `TF_CORPSE`. Regression
  test fires through a spent barrel into the monster behind it. ([`src/things.cyr`](src/things.cyr))
- **Inventory carries across level transitions (audit F-G6).** `load_map` unconditionally
  called `player_init`, which reset health/armor/weapons/ammo to pistol start — so the
  shotgun found in E1M1 was gone at the start of E1M2. Split off `player_spawn_at_start`
  (reposition only) from `player_init` (full reset); `load_map` now takes a `reset_player`
  flag — `1` for a new game / death-respawn (full reset, unchanged), `0` for a level
  advance (keep health/armor/weapons/ammo, reposition, clear the per-level keys).
  ([`src/player.cyr`](src/player.cyr), [`src/main.cyr`](src/main.cyr))
- **Intermission and death screens no longer self-dismiss; TAB no longer flickers the
  automap (audit F-U3 / F-U4).** All three read `input_flags`, which is level-triggered
  (held keys, tty autorepeat, AGNOS persistent key-state) — so a level exited or a death
  taken with a movement key held flashed the screen for ~28 ms, and holding TAB toggled
  the automap at 35 Hz. The two wait loops now edge-detect a *fresh* press (wait for all
  keys to release, then a new press), and the automap toggle latches on a 0→1 TAB
  transition. Runtime-verified: one TAB press = exactly one toggle.
  ([`src/main.cyr`](src/main.cyr), [`src/level.cyr`](src/level.cyr))
- **"New Game" reaches the skill screen instead of instant-starting (audit F-U1).** The
  menu's use handler ran sequential `if (menu_screen == …)` branches, so selecting New
  Game (which sets `menu_screen = MENU_SKILL`) fell straight through the MENU_SKILL branch
  in the same call and started the game at the default skill — the skill screen was
  unreachable. The handler now snapshots the screen before dispatching. Runtime-verified:
  New Game now lands on the skill screen (no game start). ([`src/menu.cyr`](src/menu.cyr))
- **Skill selection actually changes the monster set (audit F-U2).** The THINGS options
  word (skill bits + multiplayer flag) was stored but never read, so every skill spawned
  the Ultra-Violence set and multiplayer-only things leaked into single-player.
  `things_spawn_from_map` now filters on the selected `game_skill` (skill 1&2 → bit 0x01,
  3 → 0x02, 4&5 → 0x04) and drops multiplayer-only things (0x10), matching vanilla
  `P_SpawnMapThing`. The chosen skill is recorded from the menu (default HMP when the menu
  is skipped, e.g. direct-map CLI). Because the initial `load_map` runs before `menu_run`,
  the interactive path re-spawns the first level's things after the menu returns so the
  selected difficulty applies to E1M1 too (not just from the first level-advance onward).
  Verified on E1M1: skill 1 → 4, skill 3 → 6, skill 5 → 29 monsters (previously a flat 29
  on every skill; and menu-selecting Nightmare now re-spawns E1M1 at 29). ([`src/things.cyr`](src/things.cyr),
  [`src/map.cyr`](src/map.cyr), [`src/menu.cyr`](src/menu.cyr), [`src/main.cyr`](src/main.cyr))
- **Sprite rotation was 180° off — monsters showed their backs while approaching (audit
  F-R1).** `sprite_calc_rotation` omitted the ANG180 term, so `rel` (view→thing minus the
  thing's facing) picked the opposite of the correct sprite view: a monster facing you
  resolved to rotation 5 (its back). Added the ANG180 term. Regression test pins
  facing-viewer → front (rot 1), facing-away → back (rot 5), left-side → rot 3.
  `render_frame` **2.858 ms** (variance-level; the rotation calc is off the pixel loop).
  ([`src/sprite.cyr`](src/sprite.cyr))
- **Linux input hardening (audit F-U5 / F-U9 / F-U10).** (F-U5) The tty decoder now
  handles a CSI escape sequence as a unit: it scans `ESC [ … <final>` to the final byte
  and acts only on that, so a modified arrow (`ESC [ 1 ; 2 C`) no longer leaks its `1`/`2`
  into the weapon-select scan, and a sequence split across a full 32-byte read is consumed
  rather than mis-read as a quit (a bare arrow and Shift+arrow both resolve to the arrow;
  a lone ESC still quits). Runtime-verified: arrows still turn, no spurious quit/weapon
  swap. (F-U9) Uppercase `E`/`F`/`Q` are now aliased to use/fire/quit, so Caps Lock no
  longer disables them. (F-U10) The direct-map arg is validated (`strlen >= 4` and `'M'` at
  index 2) before indexing, closing the OOB read on a short arg and rejecting malformed
  forms like `E1X3`; two `sakshi_info` length arguments were off by one (banner 43→42,
  audio-test 31→32). ([`src/input.cyr`](src/input.cyr), [`src/main.cyr`](src/main.cyr))
- **PC-speaker tone lifecycle + audio pumping in wait loops (audit F-U7).** `sound_tick`
  started a queued tone and counted it down in the *same* call, so every 1-tick tone (the
  dry-fire click, plasma, menu-move) was turned on and off within microseconds and never
  played — fixed with a `just_started` guard. The death-wait loop pumped `audio_tick` but
  not `sound_tick` (a tone mid-playback at death left the speaker beeping); the
  intermission loop pumped neither (AGNOS ring underrun → stale-content echo). Both wait
  loops (and the menu loop) now pump `sound_tick` — and the intermission also pumps
  `audio_tick`. ([`src/sound.cyr`](src/sound.cyr), [`src/main.cyr`](src/main.cyr),
  [`src/level.cyr`](src/level.cyr), [`src/menu.cyr`](src/menu.cyr))


**DOOM audio IRON-VALIDATED on archaemenid — "ALL DOOM SOUNDS PERFECT."** The 0.31.0 audio
retarget shipped, but the first iron burns had a residual echo/dropout that a long chase
(deeper adaptive buffer, log removal, DMX-pad skip, an LPIB-rate experiment) only mitigated
— because **the real root cause was in agnos, not doom**: the kernel's LAPIC timer was
uncalibrated and ran ~12× slow on real Zen (a hardcoded QEMU-tuned reload count), so the
100 Hz HDA servicer couldn't keep the 48 kHz ring fed. **Fixed kernel-side in agnos 1.52.8**
(boot-time LAPIC calibration). With a correct system clock, doom's audio is clean on iron.

### Changed
- **Restored the per-SFX `sakshi_info` logs in `--audio-test`** (`main.cyr`). They were removed
  mid-chase on a wrong theory that the console-render stall caused the glitch; with the timer
  fixed they cost nothing (Linux plays fine with the same logs — so agnos does too). The 8
  `sfx: pistol` / `shotgun` / … lines are back, marking each SFX as it fires.
- **Skip the DMX 16-sample lead/tail pad in `audio_load`** (Chocolate/PrBoom parity) — removes
  ~1.5 ms of "empty air" before each SFX. Harmless correctness win.

### Removed
- The temporary FB fill-vs-tick **graph telemetry + 12 s hold** from `--audio-test`, and the
  `audio_fill_hist`/`audio_fill_idx` DBG state from `audio.cyr`. They were the diagnostic that
  helped localize the timer bug; no longer needed.

### Notes
- The agnos-side adaptive producer (`audio_tick` reads `sys_snd_avail` and fills to
  `AUDIO_AGNOS_TARGET`) stays — proper flow control. The target is currently **12288 frames
  (~256 ms)**, deepened during the chase to mask the slow clock; now that the clock is fixed it
  is conservative and **can be trimmed toward ~60–90 ms for snappier in-game SFX latency** (a
  follow-up, gated on an iron listen). Kept deep here because it is the known-good state.

## [0.31.0] - 2026-07-04

**Sound on agnos — DOOM SFX out the sovereign HDA output (the audio arc's Gate 4).**
Retargets the digital-SFX output stage onto the agnos `sys_snd_*` syscall band (`#64–#69`,
frozen in agnos 1.52.7 + shipped in the cyrius v6.4.2 stdlib), so DOOM's WAD sound effects
reach the ALC897 codec on agnos — the `cyrius-doom audio.cyr → sys_snd_* → agnos #64–#69 →
HDA ring → ALC897` path is now live.

### Changed
- **Closed-loop adaptive-`avail` producer on agnos (the echo/underrun fix).** The first iron
  burn played every SFX with a **heavy echo/repeat** + slight slowness. Root cause (measured):
  the agnos HDA ring is drained by a **free-running 48 kHz DAC** independent of the 35 Hz /
  10 ms-quantized game clock, so pushing a **fixed ~1371 frames per tick** left the ring only
  ~1 tick deep; the 100 Hz `sleep_ms` jitter (20/30 ms) then tipped it into **underrun**, where
  the cyclic BDL **replays ~28 ms of stale ring content** = the echo. (Linux is clean because
  vani→ALSA buffers ~186 ms and absorbs the jitter; the raw agnos ring has no such cushion.)
  Fix (`audio.cyr`, agnos-gated): `audio_tick` now reads **`sys_snd_avail`#69** (ground truth of
  what actually drained) and mixes+pushes chunks in a loop until the ring fill reaches a deep,
  jitter-tolerant **`AUDIO_AGNOS_TARGET` = 8192 frames (~171 ms)** (capped at 7 chunks/tick). The
  mix body is factored into `audio_mix_chunk()`; each chunk still renders exactly `MIX_SRC_SAMPLES`
  (315) so `audio_up_acc` + per-voice `cpos` advance identically — pitch/timing stay drift-free,
  and 315 samples emit ≤5488 B < `OUT_BUF_BYTES` (no overflow). The **Linux/ALSA path is byte-
  identical** (one chunk per tick behind `#ifndef`). QEMU-verified: ring fill held at the target (was
  ~1 tick, near-empty), SFX bursts **23 → 8** (echo clusters gone), no slowdown. (First iron burn:
  the rate/speed fix landed but a residual echo remained at the initial 3072/~64ms target — real
  ALC897 service stalls exceed what QEMU models — so `AUDIO_AGNOS_TARGET` was deepened to
  8192/~171ms; to be tuned down to the min-clean depth for in-game SFX latency once iron confirms.)
  No kernel change
  (a kernel silence-net was rejected — it would make the timer ISR a second `snd_appl` writer,
  breaking the lock-free single-writer band ABI).
- **`OUT_RATE` 44100 → 48000** to match the agnos HDA stream's hard-armed 48k/16/2 format
- **`OUT_RATE` 44100 → 48000** to match the agnos HDA stream's hard-armed 48k/16/2 format
  (a valid raw ALSA rate too, so the Linux path is unaffected in kind). The output stage's
  fixed ×4 integer upsample (44100/11025) becomes a **drift-free Bresenham nearest-neighbour
  upsampler** (`audio_up_acc`, `audio_tick`): each 11025 mono source sample emits
  `floor((acc+48000)/11025)` output frames (4 or 5, averaging 4.354), the accumulator carried
  across ticks so the long-run count is exactly 48000/11025 — no pitch drift. Per-tick output
  is now a variable ~1371/1372 frames (`OUT_BUF_BYTES` grown 5040 → 6400 to hold it); the push
  uses the actual produced count (`oi/4`), not a fixed constant.
- **`audio_init` / `audio_preload` / `audio_tick` agnos branches** (`#ifdef CYRIUS_TARGET_AGNOS`):
  `audio_init` opens the output via `sys_snd_open()` + `sys_snd_config(slot, 48000, 0x1002)`
  (S16/stereo) instead of ALSA (storing `slot+1` in `audio_dev` so 0 stays "no device"); the
  per-tick push uses `sys_snd_write_nb`; `audio_preload` now loads the WAD SFX on agnos (was a
  no-op). The vani/ALSA path (`audio_open_best`/`audio_write`/EPIPE recovery) is unchanged on
  non-agnos targets. `sound.cyr`'s PC-speaker guard stays agnos-disabled (no PC speaker there).
- **Toolchain pin → cyrius 6.4.2** (`cyrius.cyml`) — the release carrying the `sys_snd_*` peer;
  the vendored `lib/` was `cyrius lib sync --full`'d to the 6.4.2 snapshot (the stale wrappers
  lacked `sys_snd_*`). Builds clean for agnos.

### Fixed
- **`audio_init` / `audio_shutdown` agnos branches fell through to the ALSA-only tail on a fake
  handle → `#PF` inside `load_map`.** With `audio_dev = slot + 1` (a small integer, not an fd), the
  post-branch common code (`audio_set_sw_params`/`audio_prepare`/`audio_fd`/`SYS_FCNTL` in `audio_init`;
  `audio_drain`/`audio_close` in `audio_shutdown`) operated on that fake handle and faulted on agnos.
  Both agnos branches now `return` before the Linux-only tail (and `audio_shutdown` calls
  `sys_snd_drain`/`sys_snd_close` on the slot). Surfaced by the agnos `--audio-test` bring-up, where
  it masked the actual audio path; caught via serial bisection.
- **Validated end-to-end on agnos in QEMU** (agnos `scripts/doom-audio-smoke.sh`): `--audio-test`
  plays all 8 SFX out the emulated `intel-hda` and the captured wav is non-silent (PEAK=24287) — first
  cyrius-doom sound on AGNOS. (The exercise also caught + fixed an agnos kernel bug where the HDA PCM
  ring's CPU-access VA wasn't in the per-process CR3; fixed kernel-side in agnos 1.52.7.)

## [0.30.7] - 2026-06-29

**Positional/stereo SFX + Sound-menu live preview.** Builds on the 0.30.5/0.30.6
audio work: monster and explosion sounds now attenuate with distance and pan
across the stereo field, and the volume slider previews live. Binary **621,080 →
623,520 B** (+2,440; `doom_agnos` 607,680 → 610,152 B). `render_frame` **2.956 ms**
(E1M1, cycc 6.3.5 — variance-level; the mixer is off the render path). Tests
**63/63** WAD-free + **101/101** full; `fuzz_wad`/`fuzz_fixed` 1000/50000 clean;
`cyrius deps --verify` **37/0**; DCE 1001 / 294,063 B. Vetted by a 27-agent
pre-cut adversarial review (17/17 confirmed as correctness verifications — zero
defects; L/R pan direction confirmed correct, centered playback bit-identical to
0.30.6).

### Added

- **Positional SFX — distance attenuation + stereo pan** — `audio_play_at(name,
  sx, sy)` attenuates by the player→source distance (full within 160 u, linear
  to silence at 1200 u; beyond that no voice is taken) and pans by the source
  angle relative to the player's facing, using the original engine's
  approximate-distance + stereo-swing (96) panning law. The mixer is now truly
  stereo (per-voice `lvol`/`rvol`, separate L/R accumulators). Wired at the
  monster **death**/**pain** and **explosion** sites (`things.cyr`); player-,
  pickup- and door-sourced sounds stay centered. **A centered, full-volume voice
  is bit-identical to the 0.30.6 mono mix.**
- **Sound-menu live preview** — adjusting the SFX slider plays a pistol shot at
  the new level (the device is already open before the menu), so you can hear the
  volume as you set it. `audio_tick` is pumped in the `menu_run` loop.
- **`--audio-test` LEFT/RIGHT pan pings** — two positional pistol shots 400 u to
  the player's left and right, so the stereo pan can be verified headless without
  launching gameplay (now 8 sounds over ~8 s).

### Changed

- **Sound-menu polish** (0.30.6 review nice-to-haves) — defensive `[0, 15]` clamp
  inside `menu_draw_thermo`; the slider's increment is `else`-gated so a held key
  steps cleanly.

**SFX volume control + Options→Sound menu, plus ALSA hardening and a bsp bump.**
Builds on the 0.30.5 audio revive: the previously display-only "Sound Volume"
option is now a live menu, and two robustness gaps from the 0.30.5 pre-cut review
are closed. Binary **619,224 → 621,080 B** (+1,856; `doom_agnos` 605,808 →
607,680 B). `render_frame` **2.950 ms** (E1M1, cycc 6.3.5 — variance-level; none
of this touches the render path). Tests **63/63** WAD-free + **101/101** full;
`fuzz_wad`/`fuzz_fixed` 1000/50000 clean; `cyrius deps --verify` **37/0**. Vetted
by a 29-agent pre-cut adversarial review (20/20 findings confirmed as correctness
verifications — zero defects).

### Added

- **Master SFX volume + Options→Sound menu** — selecting "Sound Volume" on the
  Options screen now opens a real Sound sub-menu (`MENU_SOUND`) with a DOOM-style
  thermometer slider (`M_THERML`/`M_THERMM`/`M_THERMR` track + `M_THERMO` knob).
  Left/right (arrows or A/D, debounced) adjust `sfx_volume` (0–15), applied as a
  gain in the `audio_tick` mix stage: `asr((sample<<8)*(vol+1), 4)` — so **v=15
  is bit-identical full scale** (default, unchanged from 0.30.5) and **v=0 mutes**.
  `--ppm-menu` gained a Sound-screen render.

### Changed

- **`[deps.bsp]` `1.1.5` → `1.2.0`** — source-module bump (no ABI surface change);
  `cyrius.lock` regenerated (`rm -rf lib && cyrius deps`), verifies **37/0** with
  only the bsp row moved (transitive trio + stdlib leaves unchanged). Both Linux
  and `--agnos` link clean; 63/63 + 101/101 hold.

### Fixed

- **ALSA suspend/resume recovery** — `audio_tick` now also recovers from
  `-ESTRPIPE` (PCM suspended on system sleep) via `audio_resume` + `audio_prepare`,
  alongside the existing `-EPIPE` underrun path. `-EAGAIN`/short writes still fall
  through untouched (the never-stall design).
- **HW_PARAMS-fallback start-threshold** — `audio_set_sw_params(MIX_START, …)` is
  now applied **only** when the explicit period/buffer were accepted
  (`audio_explicit_params`). On the kernel-chosen-buffer fallback a fixed
  `start_threshold` could exceed a smaller negotiated buffer and never auto-start
  (total silence); the fallback now leaves the kernel default (`start_threshold=1`).

**Audio revive — DOOM SFX actually play through ALSA now.** The `audio.cyr` +
vani path was wired but **dead**: `audio_play` had zero callers, so not one `DS*`
sample ever reached the card — all in-game sound came from the PC-speaker beep
fallback (`sound.cyr`), inaudible on hardware without a `pcspkr`. This cut makes
the real WAD sounds play, fixing every blocker found by reproducing on metal.
Binary **613,720 → 619,224 B** (+5,504, the software mixer + device pick + the
`--audio-test` harness; `doom_agnos` 600,272 → 605,808 B). `render_frame`
**3.082 ms** (E1M1, cycc 6.3.5 — variance-level; the mixer is not on the render
path and no-ops when no card is present). Tests **63/63** WAD-free + **101/101**
full; `fuzz_wad`/`fuzz_fixed` 1000/50000 clean; DCE **998 unreachable / 295,193 B**;
`cyrius deps --verify` **37/0**. Vetted by a 29-agent pre-cut adversarial review
(18 findings confirmed; the one HIGH — an AGNOS null-page write — fixed below;
MED/LOW deferred to the roadmap audio-hardening item).

### Added

- **Software SFX mixer** (`src/audio.cyr`) — 8-voice, non-blocking. Voices are
  cached + mixed at DOOM-native 11025 mono (U8); `audio_tick()` (driven once per
  35 Hz tick from the game loop + dead-wait loop) renders one tick of audio and
  pushes it with a non-blocking `WRITEI` so it can never stall the frame loop.
  Underruns (`-EPIPE`) self-heal via re-`prepare`. Voice allocation prefers a
  free slot, else steals the one with the least audio remaining.
- **`--audio-test` mode** (`src/main.cyr`) — plays six real DOOM SFX paced at
  35 Hz, no framebuffer required, so the output chain (device pick, format
  conversion, non-blocking writes) can be verified directly on the speaker/jack.
- **Real WAD sounds wired to game events** (`player`/`things`/`doors.cyr`,
  alongside the kept PC-speaker fallback): weapon fire (`DSPISTOL`/`DSSHOTGN`/
  `DSRLAUNC`/`DSPLASMA`), player + monster pain/death, item pickup, door,
  explosion. All pre-cached by `audio_preload` so the first hit does no
  mid-frame WAD I/O.

### Fixed

- **Audio output was entirely dead** — `audio_play`/`audio_play_name` had no
  callers; now driven from the `sound_*` event sites.
- **Wrong sound card** — the hardcoded `audio_open_playback(0, 0)` opened card 0
  device 0, which on a box with a GPU is the HDMI codec (and often has no D0
  node at all → "no device"). New `audio_open_best()` prefers the **analog**
  card (its device 0 has a capture sibling; HDMI is playback-only), falling back
  to the first playback node that accepts the format.
- **Impossible format** — requested S8/mono/11025, which real HDA codecs reject
  outright (the analog jack accepts **only S16_LE/stereo/44100·48000**). The raw
  hw node does no conversion, so the mixer's output stage now converts: U8→S16
  (`(s<<8)`), mono→L/R, and a clean **4× upsample** (44100/11025 = 4 exactly).
  315 mono samples in → 1260 stereo frames out per tick, exact (no drift). Honest
  logging: only `audio: ALSA playback` on a config the device actually accepted.
- **Audio died after the first level transition** — `audio_init()` runs in
  `load_map()` (every map); the old code re-opened the **exclusive** PCM node
  while the prior fd was held → `-EBUSY`. Now idempotent via a one-shot
  `audio_inited` flag; `audio_shutdown()` wired at exit.
- **AGNOS null-page write** (pre-cut review, HIGH) — on AGNOS `audio_init`
  early-returns before allocating the caches, but the event sites still call
  `audio_load`; the first SFX did `store64(0 + idx*8, …)`. `audio_load` now
  no-ops when `snd_cache_lumps == 0`. Plus an AGNOS `#ifdef` guard on
  `audio_init`/`audio_preload` (mirrors `sound.cyr`).
- **Malformed `DS*` lumps** — validate the DMX format word (== 3) and reject
  `nsamples <= 0` (and the post-decimation 1-sample-22050 `alloc(0)` case);
  decimate the one 22050 Hz shareware lump (`DSITMBK`) 2:1 to the device rate.

### Known limitations (→ roadmap audio-hardening item)

- Output is hardcoded **S16/stereo/44100**; cards that reject 44100 (need 48000)
  aren't handled yet (fractional resample). HW_PARAMS-fallback path keeps the
  fixed start-threshold (could mis-start on an unusually small negotiated
  buffer). Only `-EPIPE` is recovered (not suspend/resume). SFX play at the
  lump's native loudness (no normalization/volume) — soft lumps like `DSITEMUP`
  (±19 vs gunfire's ±128) are faithfully quiet. PC-speaker + ALSA both fire per
  event. Device heuristic can't tell a virtual card (snd-aloop) from the codec.

## [0.30.4] - 2026-06-29

Toolchain + dependency bump to the cyrius 6.3.x line. No application logic
changes — the only `src/` edit is the version banner. Binary **612,672 →
613,720 B** (+1,048, 6.3.0/6.3.5 codegen growth-tax; `doom_agnos` 592,448 →
600,272 B). `render_frame` **2.971 ms** (E1M1, cycc 6.3.5 — variance-level vs
0.30.1's 2.957 ms). Tests **63/63** WAD-free + **101/101** full;
`fuzz_fixed`/`fuzz_wad`/`fuzz_weapon` 50000/1000/2000 clean.

### Changed

- **`cyrius` pin `6.2.44` → `6.3.5`** (`cyrius.cyml`) — closes the launcher
  drift (cycc already ran 6.3.5; the manifest now matches). The band carries two
  default-codegen deltas, both re-verified green: 6.3.5 CO-01 (forward-call ABI
  fix, exercises the `Result<T,E>` WAD path) and 6.3.0 (per-var `_base`
  indirection; `fuzz_fixed` + render bench confirm no hot-path regression).
- **`[deps.vani]` `0.9.4` → `0.9.5`** — pure upstream pin sweep; `vani-core`
  code byte-identical, the `audio_*` ABI `src/audio.cyr` uses is unchanged.
- **`[deps.bsp]` `1.1.3` → `1.1.5`** — bsp's own 6.3.5 pin release; `dist/bsp.cyr`
  bundle byte-identical, the `bsp_*` geometry ABI is unchanged.
- **Regenerated `cyrius.lock`** (`rm -rf lib && cyrius deps`): 37 leaves, 5
  commit-pinned, `cyrius deps --verify` **37/0**. Transitive trio unmoved (vani
  0.9.5 still pins yukti 2.2.4 / patra 1.9.5; sakshi 2.2.5 via stdlib); only the
  vani/bsp git rows + the 6.3.5 stdlib leaves re-hash.

### Security

- Picks up cyrius **CVE-32 (P1)** fix (6.2.45, in the 6.3.5 band) — a
  path-traversal in the modular dep resolver. doom doesn't use `modular=` so its
  surface was nil, but the resolver itself is now hardened.

## [0.30.3] - 2026-06-26

### Fixed
- **Sprite draw-loop out-of-bounds read → ring-3 #PF on AGNOS during sustained close-range combat (`src/sprite.cyr`).** A point-blank sprite — the muzzle-flash / projectile sprites added in the 0.30.x shooting work — has a tiny view-space `vy`, so `scale = PROJ_DIST/vy` and the unclamped `sprite_w` (sprite.cyr:307) blow up to tens of thousands. The sprite-column draw loop then computed `scr_x = sx1 + c` up to ~91,880 and read `clip_top[scr_x]`/`clip_bottom[scr_x]` — 320-entry per-screen-column arrays — walking ~734 KB off the end. On AGNOS (guard-unmapped pages) that is a clean ring-3 page fault (CR2 ≈ `0x12xxxxxx`, the `clip_top` heap chunk → DOOM locks up after ~1–2 min of play); on stock hardware it would silently corrupt adjacent heap. The two `if (scr_x < 0 / >= SCREEN_WIDTH) continue;` guards that should have caught it were **dead no-ops** under the former `cyrius = "6.1.37"` pin, which miscompiled `continue` inside this large function to a jump-to-loop-body (fixed in cyrius 6.2.x). **Fix:** range-clamp the draw loop — `c ∈ [max(0,-sx1), min(sprite_w, SCREEN_WIDTH-sx1))` — so `scr_x` is provably in `[0, SCREEN_WIDTH)` by construction, independent of `continue` codegen, and the loop no longer iterates the huge off-screen column excess (a per-frame perf cliff). Diagnosed from the AGNOS iron #PF (CR2=0x120b3740, RIP=0x45ff1d) + objdump of the stripped binary. Validated: `doom-smoke` (title render) + `doom-ingame-smoke` (E1M1 3D) PASS; both `doom` + `doom_agnos` rebuilt clean.

### Changed
- **Bumped the `cyrius` toolchain pin `6.1.37` → `6.2.44`** (`cyrius.cyml`). 6.2.x fixes the `continue`-in-large-function miscompile that masked the sprite OOB above (so the in-source bounds guards work again as defense-in-depth), and aligns with the current ecosystem toolchain.

## [0.30.2] - 2026-06-14

Player-feedback patch — live-play fixes plus control fidelity. Fixed a combat
coredump (shooting a monster) and the dead main-menu "Options" item; raised the
fist so its thumb clears the status bar; and reworked the controls so AGNOS gains
DOOM-faithful Ctrl-fire and Shift-to-turn while Linux keeps a simple,
Caps-Lock-immune keyboard scheme. Binary **612,576 B** (+2,000 over 0.30.1).
Tests **63/63** WAD-free, **101/101** full.

### Added

- **Options menu screen** — selecting "Options" on the main menu opened nothing
  (the case was unhandled, a silent no-op). Added a navigable `MENU_OPTIONS`
  screen (`M_OPTTTL` heading + End Game / Messages / Graphic Detail / Screen Size
  / Mouse Sensitivity / Sound Volume, original DOOM `OptionsDef` layout, skull
  cursor). The individual settings are display-only stubs for now; `ESC` / `Q`
  returns to the main menu. Also added the screen to `--ppm-menu`
  (`/tmp/doom_options.ppm`). (`src/menu.cyr`, `src/main.cyr`)

### Changed

- **Controls: AGNOS gains Shift-to-turn; Linux keeps arrows-to-turn** — the
  intended scheme (arrows strafe, **Shift**+A/D or **Shift**+arrows turn) is
  carried on the **AGNOS** path, which reads raw PS/2 scancodes: Shift is a real
  key (`0x2A`/`0x36`) tracked in `key_state`, so A/D and the arrows branch
  strafe↔turn on it, and Caps Lock is inherently ignored (letters always decode
  lowercase). On **Linux** a raw tty can't report a bare Shift (modifier, no
  byte) and reading it from uppercase letters is ambiguous with Caps Lock, so the
  Linux build keeps the simple, robust scheme — **arrows turn, A/D strafe** —
  until mouse input lands. Movement is Caps-Lock-immune there: uppercase
  `W`/`A`/`S`/`D`/`R` alias their lowercase movement actions, so Caps Lock can't
  blow out movement. (`src/input.cyr`, `README.md`)
- **Fire mapped to Ctrl (DOOM-faithful)** — original DOOM fires with Ctrl. Added
  left/right Ctrl → fire on the AGNOS input path (raw PS/2 scancode `0x1D`, plus
  the `E0 1D` right-Ctrl extended form), wired through a new `KEY_CTRL` (132)
  entry in the fire-flag builder of both poll paths. A raw Linux tty can't report
  a bare Ctrl (it's a modifier — only Ctrl+key yields a byte), so on Linux the
  `KEY_CTRL` slot is never set and **F stays the working fire key everywhere**.
  Net effect: Ctrl fires on AGNOS/real-keyboard; F fires on Linux/tty.
  (`src/input.cyr`, `README.md`)

### Fixed

- **Combat coredump (`thing_animate` switch miscompile)** — shooting a monster
  crashed the game with a corrupted return (`SIGSEGV` @ `RIP=0x1`, sometimes
  `SIGILL`). Root cause: cycc's jump-table codegen for `thing_animate`'s
  `switch (state)` emitted a frame that smashed the function's own return
  address. The switch had sparse/out-of-order case labels (`case 8` sat between
  `1` and `2`) and `var` declarations inside case bodies; the smash detonated at
  a later `ret` (e.g. a `STATE_PAIN` thing's `thing_set_frame`), which is why it
  presented as a "death" crash. Reproduced deterministically (force-damage
  monsters → pain/die animation) and isolated by bisection — removing the switch
  eliminated the crash. **Fix:** rewrote the state→frame mapping as an
  equivalent `if/else` ladder (cycc's if-codegen is solid); clean under sustained
  combat. Not toolchain-specific — identical miscompiled binary under both the
  pinned cycc 6.1.37 and 6.2.2. (`src/things.cyr`)
- **Fist thumb hidden behind the status bar** — the first weapon (fists, `PUNG`)
  sat too low: its thumb lives in the bottom-left of the sprite (rows 32-41),
  which the shared psprite anchor maps to screen rows 174-183 — entirely behind
  the status bar (top at 168), so the thumb never showed. (DOOM clips it the same
  way in status-bar mode; the reference fist animation shows the standalone
  sprite.) Added a per-weapon vertical lift (`weapon_y_lift`, zero for every gun)
  and set the fist to **14 px** so the thumb clears the bar while the wrist stays
  tucked behind it. Verified against a real-binary `--ppm` render. (`src/render.cyr`)

## [0.30.1] - 2026-06-13

Player-feedback patch — four rendering/animation bugs reported from live play:
the weapon stuck dead-center with its firing animation "totally off" and no
muzzle flash, walls warping/mirroring when turning, and enemies appearing to
always face the player. Closes the **U-swap-mirror** and **muzzle-flash-overlay**
items deferred from 0.29.4 / 0.30.0. Binary **610,576 B** (+2,232 over 0.30.0).
`render_frame` **2.957 ms** / `+sprites` **2.952 ms** (E1M1, cycc 6.2.2) — render
path effectively unchanged from 0.30.0 (within run-to-run variance); the extra
combined-rotation lump lookups don't register at the E1M1 spawn sprite count.
~7× headroom on the 22 ms budget.

### Added

- **Muzzle flash overlay** — firing now draws DOOM's separate `ps_flash` psprite
  (`PISF` / `SHTF` / `CHGF` / `MISF`) fullbright over the gun
  (`render_draw_flash`; per-weapon flash family + frame count set in
  `render_set_weapon`). 0.30.0 only lit the *gun* fullbright on fire — the actual
  flash sprite was never drawn. Melee weapons (fist/chainsaw) have no flash;
  plasma's `PLSF` is absent in the shareware WAD (guarded by `wad_find_lump < 0`).
  Closes the 0.30.0-deferred "separate muzzle-flash overlay sprite" roadmap item.

### Fixed

- **Weapon psprite position + firing animation.** The gun was placed at
  `sx = 253 + leftoffset`, `sy = 228 + topoffset`, which equals the correct
  DOOM `sx = 1 − leftoffset`, `sy = 16 − topoffset` **only when
  leftoffset == −126 and topoffset == −106** — i.e. exactly the pistol ready
  frame (`PISGA0`), by coincidence. Every other weapon and every other animation
  frame (each lump has its own offsets) was mispositioned, so the fist sat
  dead-center (should be lower-right) and the gun lurched across the screen as it
  fired. Replaced with the DOOM-accurate hotspot formula via a shared
  `render_blit_psprite` blitter. (roadmap reference-parity #1, `R_DrawPSprite`)
- **Wall texture mirrored when turning.** `render_seg`'s `sx1 > sx2` swap
  reordered the screen-X / depth endpoints but **not** the texture-U endpoints,
  so any seg projecting right-to-left rendered its texture mirrored — and flipped
  the instant a turn crossed that screen-order threshold ("walls warp when
  turning"). The U endpoints now swap with screen order, in both the wall pass
  and the deferred masked-midtexture pass (`render_masked_segs`). (roadmap
  wall-path #7, MED)
- **Enemies always faced the player.** `sprite_find_frame` only looked up the
  6-char single-rotation lump (`TROOA1`); DOOM packs rotations 2/3/4/6/7/8 into
  combined 8-char lumps (`TROOA2A8` = rotation 2, and rotation 8 mirrored), so
  every rotation but 1 and 5 missed and fell back to the front view. It now
  resolves the combined lumps and returns a flip flag; `sprite_render_all`
  mirrors the patch columns when set. Verified against the WAD: 1→`TROOA1`,
  2→`TROOA2A8`, 3→`TROOA3A7`, 4→`TROOA4A6`, 5→`TROOA5`, 6→`TROOA4A6`(flip),
  7→`TROOA3A7`(flip), 8→`TROOA2A8`(flip). `_spr_prefix` scratch grown 8 → 16 B
  to hold the 8-char names.
- **Monster walk strobe.** SEE/CHASE flipped the two walk frames every 35 Hz
  tick (`thing_animate` runs each tick), ~10× too fast. Now gated to a ~4-tick
  cadence, staggered by thing index (matches DOOM `*_RUN` ≈3-tic frames).

### Notes

- No control changes: fire stays on **F**; **Space** = use and **Enter** keep
  their roles (a brief experiment binding fire to Space/Enter was reverted at the
  user's request — those keys are meant to be other buttons).

## [0.30.0] - 2026-06-13

Shooting-mechanics overhaul — a multi-agent review of the full path (input →
hitscan → damage → psprite render) surfaced 27 confirmed findings; this cut
fixes the correctness bugs and closes the biggest DOOM-fidelity gaps. Binary
**602,032 → 608,344 B** (+6,312). `render_frame` **3.10 ms** (E1M1, cycc 6.2.2)
— render path unchanged; the only per-frame addition is the weapon's
sector-light lookup, which is not on the measured path. ~7× headroom on the
22 ms budget.

### Added

- **Deterministic combat RNG** — `p_random` / `p_random_range` (LCG, fixed seed
  in `tables_init`) in `tables.cyr`. Replaces `tick_get_count() % N` damage
  rolls, which tied damage to the frame counter. Drives damage spread,
  painchance, pellet scatter, and splash falloff; reproducible for tests/demos.
- **Rocket projectile + radius damage** — the launcher now spawns a travelling
  `CAT_PROJECTILE` thing (`thing_spawn_missile`) that flies, renders its MISL
  sprite, and detonates on a wall / thing / lifetime via `thing_explode`
  (linear-falloff splash to things **and** the player). Spent slots are reused.
- **Barrel explosions + chain reactions** — shooting a barrel to death now
  detonates it (`thing_explode`, 128-unit / 128-dmg), which can pop adjacent
  barrels; the corpse-guard bounds the recursion.
- **Shotgun spread** — 7 independent pellets (±~2.8° scatter), 5–15 dmg each,
  instead of a single hitscan ×3.
- **Per-weapon refire cadence** — `weapon_fire_ticks` set per weapon in
  `render_set_weapon` (chaingun fast, shotgun/rocket slow) instead of one
  global `FIRE_TICKS`. Weapon 7 (plasma, `PLSG`) added to the sprite/cadence map.
- **Dry-fire feedback** — `sound_weapon_dry` click when firing empty (edge-latched,
  once per trigger pull); `sound_plasma` for weapon 7.
- **Per-monster painchance** (`thing_painchance`) — DOOM-matched flinch odds.
- **Combat unit tests** (`tests/doom.tcyr`, +26 asserts: WAD-free **37 → 63**,
  full **75 → 101**) covering p_random, ammo deduction, damage/state transitions,
  hitscan selection + LOS, splash falloff, and the rocket projectile — plus a
  hermetic-stub block so the WAD-free subset can exercise the combat path.
- **`fuzz/fuzz_weapon.cyr`** — drives the real `render_draw_weapon` decoder with
  malformed one-lump WADs (20k iters clean).
- Security research: `docs/audit/2026-06-13-shooting-hitscan.md` (P(-1)).

### Fixed

- **Unbounded fire cadence** (review #1). The fire block deducted ammo and ran
  `player_hitscan` *every 35 Hz tick* the fire key was held — 35 shots/sec, a
  magazine gone in ~1.4 s, 35× intended DPS — because only the sprite animation
  was gated, not the shot. The shot is now gated on the weapon being ready
  (`weapon_fire_frame == 0`), i.e. once per refire period.
- **Shoot-through-walls** (review #2). `player_hitscan` had no line-of-sight
  check; bullets passed through solid walls into adjacent rooms. Now reuses
  `thing_check_sight` (the monster-AI sight primitive) to reject blocked targets.
- **Pain-lock / stun-lock** (review #3). Every hit forced `STATE_PAIN`/tics=5
  unconditionally, so sustained fire froze any monster forever and spammed the
  pain sound each tick. Pain is now painchance-gated and not re-entered while
  already flinching.
- **Corpse re-kill** (review #4). Shooting a dying thing reset `STATE_DIE`/tics
  and replayed the death sound, so the animation never finished. `thing_damage`
  now early-returns on `STATE_DIE`/`STATE_DEAD`.
- **Vanishing corpses** (review #5). The death→corpse transition cleared
  `TF_ACTIVE`, and `sprite_render_all` skips inactive things, so bodies popped
  out of existence. Corpses keep `TF_ACTIVE | TF_CORPSE` (visible, inert,
  un-shootable).
- **psprite memory leak** (review #6). `render_update_weapon_lump` `alloc(8)`'d a
  lump-name buffer on every firing frame and weapon switch, never freeing it.
  Now a single lazy-init-guarded buffer.
- **Weapon 7 (plasma) fired silently with fall-through damage** (review #7) —
  now has an explicit damage and sound case.
- **No-map robustness** — `render_draw_weapon`'s new sector-light path is guarded
  on `map_num_sectors > 0`, so it can't deref a null sector table off the map.

### Changed (DOOM fidelity)

- **Rocket** is a projectile with splash, not an instant single-target hitscan
  (review #9). **Shotgun** is a 7-pellet spread, not hitscan ×3 (review #8).
  **Chaingun** has its own (fast) cadence rather than being a re-skinned pistol
  (review #10).
- **Weapon brightness** tracks the player's sector and goes full-bright during
  the fire animation (muzzle-flash glow), replacing the hardcoded `light_level 4`
  (review #11).
- **Damage variety** comes from `p_random`, decorrelated from game time (#15).
- **Idle monsters wake when shot** even without prior line of sight.
- **Overkill** (hp below the negative of spawn health) resolves the death faster
  (a lightweight gib; full xdeath giblet sprites are a follow-up).

### Notes

- The weapon **bob** was reviewed and left unchanged: DOOM's `psp->sy` bob uses a
  half-angle sine (a one-directional dip), which the existing `fixed_abs(cos)`
  already matches — the review's "make it symmetric" was a misread.
- Deferred (cosmetic): BEXP rocket-explosion frames, separate muzzle-flash
  overlay sprite, full xdeath giblet animation. Missile-vs-wall reuses
  `player_check_position`, so a rocket can clip on tall steps in this 2.5D engine.

## [0.29.4] - 2026-06-12

### Fixed

- **Player walked through every wall** (user-reported from interactive play).
  Root cause: `player_check_position` computed each BLOCKMAP cell index as
  `fixed_to_int(asr(nx - radius - map_bm_originx, 16)) / 128`. The world-space
  offset is already 16.16 fixed-point (both `player_x` and `map_bm_originx`
  carry `<<16`), so `fixed_to_int` (= `asr 16`) is the *only* shift needed —
  the extra inner `asr(…, 16)` made it `asr 32`, collapsing every real map
  offset (< 65536 units) to **0**. Every collision query therefore scanned only
  blockmap cell **(0,0)** (the SW corner), so the player collided with nothing
  outside it. Latent since **0.13.0** (when the BLOCKMAP path + the `<<16` on
  `map_bm_originx` were added together); only exposed once interactive movement
  landed (0.28.3 AGNOS keyboard + 0.29.x world-tick aliveness). Fixed to a
  single `fixed_to_int` shift. Reproduced + verified with a probe on E1M1:
  spawn cell `(0,0)→(14,9)`, and a ±2048-unit collision sweep through spawn
  went from **0/65 blocked → 5/65 (X) + 1/65 (Y) blocked**. Added a permanent
  collision regression assertion to `tests/doom.tcyr` (full suite 73 → 75) —
  the bug survived 16 minors precisely because nothing exercised it.

- **Wall "black holes" / dropped-wall void** (user-reported; E1M9 ~70% of the
  view black with monster sprites floating through where solid walls belong,
  E1M3 central black rectangle, E1M7 left rectangle, E1M1 far doorways). A
  multi-agent A/B-render diagnosis (4 diagnosers + adversarial verification)
  **empirically refuted** every geometry/clip/overflow hypothesis (NEAR_CLIP
  degenerate depth, `fixed_mul(tx,PROJ_DIST)` 64-bit overflow, one-sided-wall
  clip-drop, U/scale swap mispairing) — none move the black. The entire family
  is **two independent texture-resolution bugs**:
  - **PNAMES 8-char patch names never resolved.** `wad_name_eq` runs
    `strlen(name)` on the raw 8-byte PNAMES field; WAD names are null-padded
    *only* when shorter than 8 chars, so the 161/350 entries that are exactly 8
    chars have no terminator and the word-at-a-time `strlen` over-reads past
    byte 8, returns `>8`, and rejects the name → `patch_lumps[i] = -1` →
    `texture_get_column` composites nothing → framebuffer-black. `texture_init`
    now copies each field into a null-terminated 9-byte buffer before the
    lookup. **Alone:** E1M9 70.7% → 1.0% viewport black, E1M1 7.6% → 0.6%.
  - **Patch cache truncated patches > 8192 B.** `PCACHE_DATA_SIZE = 8192` kept
    only the first 8192 bytes of large patches; the `col_off >= pdata_size`
    bound in `texture_get_column` then dropped every column whose directory
    offset landed past the truncation → all-zero (black) column. BIGDOOR2
    (`DOOR2_4`, 17544 B) lost columns 58–127. Raised to **40960** (covers
    DOOM1.WAD's largest PNAMES-referenced patch, `WALL24_1` at 36960 B; heap
    cache grows 64 KB → 320 KB via `alloc`, binary unaffected). **On top of the
    PNAMES fix:** E1M3 10.5% → 0.0% (111 distinct viewport colors), E1M7
    17.8% → 0.1%.

  Combined, all four maps end at **≤ 0.1%** viewport black (rows 0–167),
  visually whole. Verification: 37/37 WAD-free, 75/75 full,
  `fuzz_wad` 1000/1000, `fuzz_fixed` 50000/50000; nine-map PPMs at 192,015 B.
  Bench: `render_frame` 2.451 → **2.93 ms** — A/B-isolated to the PNAMES fix
  (the renderer now actually composites and draws the wall textures that were
  previously unresolved black no-ops), **not** the cache bump (PCACHE 8192 vs
  40960 = 0.011 ms = variance). ~7.5× headroom on the 22 ms budget. Linux
  601,936 → **602,032 B** (+96 B); `--agnos` 580,960 → **581,072 B** (+112 B).
  Built under cycc **6.2.2** (launcher ignores the 6.1.37 pin — see state.md
  toolchain row). **AGNOS QEMU verified on the final binary** (581,072 B):
  `doom-smoke.sh` PASS (serial `cyrius-doom v0.29.4` + `wad loaded`, framebuffer
  240 colors), and the in-game sendkey harness (`doom-ingame-smoke.py`) drove
  into E1M1 and rendered **textured walls + floors + ceilings with no void** —
  viewport-black **0.06%** and **104** distinct colors, identical to the Linux
  render's 0.06% / 104 (the menu-drive viewpoint differs only slightly, so this
  is rendering-equivalence, not a literal same-pixel diff). No `--agnos` codegen
  hazard (constant/alloc/cold-path changes only; the 6.1.37 fold fix holds).

### Notes

- The diagnosis re-attributed two roadmap "Wall-path correctness" items: the
  closed-door black holes (E1M3/4/7) and the near-parallel one-sided wall drop
  (E1M9) were **not** the geometry/clip defects originally hypothesized — both
  were the texture-resolution bugs above. Two findings that *survived*
  refutation but were **not** exercised by the spawn-view A/B remain open (now
  on the roadmap): `closed-sector-clip-inversion` (HIGH — a two-sided line
  backing a closed/zero-height sector inverts the column clip; reproduces only
  facing a closed door *during play*) and `wall-u-swap-mirror` (MED — the
  `sx1>sx2` swap reorders sx/ty but not the texture-U endpoints, mirroring
  right-to-left segs). NEAR_CLIP=256 was A/B-proven **not** a black-hole cause
  and is intentionally out of scope.

## [0.29.3] - 2026-06-12

### Fixed

- **Floor/ceiling flats rendered as untextured gray smears** (user-reported from
  AGNOS hardware; reproduced identically on Linux `--ppm` — the smear color just
  lands on different texels per viewpoint). Root cause: `render_flat_spans`
  computed the per-row plane distance as `fixed_div(VIEW_HEIGHT, dy<<16)` =
  `41/dy`, omitting the `PROJ_DIST` projection factor (true distance =
  `41·160/dy`, DOOM's `planeheight·yslope[y]`). The distance being 160× too
  small collapsed the per-pixel world step to ~0 — **one texel smeared across
  each row**, so flats showed no texture — and pinned the zlight index to ~0,
  so flats never light-faded with distance. Fixed:
  `dist = fixed_div(fixed_mul(plane_h, PROJ_DIST), dy << 16)`. Adversarially
  verified (units/overflow audit, DOOM-fidelity audit, refutation attempt
  failed on all vectors): the span mapping is now the exact algebraic inverse
  of the wall projection, and zlight indexing matches the documented
  `r_main.c` scheme. Three follow-up defects from the same multi-agent review,
  fixed in the same cut:
  - **Sky overdrawn by the span pass (regression-by-unmasking)**: `F_SKY1` is a
    real 4096-byte flat lump (shareware flat index 53), and sky-ceiling rows
    were still registered into `vp_ceil_*` — so once flats actually textured,
    the span pass overdrew the wall-pass sky with F_SKY1's noise content. Sky
    rows no longer register. (Full sky correctness still pends the visplane
    pool rewrite: a non-sky ceiling sharing a row can still bridge its x-union
    across sky columns.)
  - **Wall fake-contrast leaked into plane lighting**: the ±1 axis-orientation
    lightnum adjustment was applied *before* the `vp_*_light` stores, so a
    flat's brightness inherited the orientation of whichever seg last marked
    the row (DOOM applies fake contrast to walls only). Planes now store the
    pre-contrast sector lightnum.
  - **Ceiling spans mapped/lit at constant plane height 41**: the wall pass
    projects ceiling rows with the true `ceil−floor−41` delta, but the span
    pass inverted with `41` — ceilings in any room not exactly 82 tall were
    radially mis-scaled (≈2.1× in a 128-tall room) and mis-lit. New per-row
    `vp_ceil_h` stores the wall-pass delta for the span pass to invert with
    (floors need no equivalent: their delta is always exactly `VIEW_HEIGHT`
    under the per-seg eye model). Below-eye degenerate deltas fall back to
    `VIEW_HEIGHT`, preserving prior behavior.
  - Dead `plane_eye_h` removed.

  Verification: 37/37 WAD-free + 73/73 full suite; all nine shareware maps
  PPM-rendered (192,015 B each) and visually verified — floor rows now carry
  16–33 distinct colors vs 1–3 pre-fix, with correct perspective convergence
  and distance fade. `--agnos` QEMU-verified **on the final 0.29.3 release
  binary** (580,960 B): `doom-smoke.sh` PASS (serial `cyrius-doom v0.29.3` +
  `wad loaded`, fb 240 colors), in-game E1M1 sendkey harness screendump shows
  textured tiled floors with depth lighting, and the AGNOS framebuffer is
  **99.99% pixel-identical to the Linux render** at 4× block scale (7/64,000
  px — idle-monster anim tick skew). A serial probe earlier in the cut
  confirmed `fixed_mul(VIEW_HEIGHT, PROJ_DIST) = 429916160` identical to
  Linux (no backend fold regression). Final binaries: Linux 601,936 B,
  `--agnos` 580,960 B (+320 B each for the `vp_ceil_h` plumbing). Bench:
  `render_frame` **2.451 ms** (0.29.2 row 2.492 ms — variance-level). NOTE:
  built under cycc **6.2.2** (the installed launcher resolves cycc via
  CYRIUS_HOME/PATH and ignores the 6.1.37 pin — even the
  `versions/6.1.37/bin` path; lockfile unchanged, verifies 37/0).

### Notes

- The review confirmed the **per-row single-visplane model** as the largest
  remaining flat defect (farthest-seg-wins flat/light per row; `x1..x2` union
  bridges interposed walls and sky columns) — already slotted as the visplane
  pool rewrite. The review adds to that slot's motivation: no global `viewz`
  (eye is per-seg `front_floor+41`, flattening elevation), the E1M5 step-down
  back-floor bleed, and portal clip updates ignoring front-sector plane bounds.
- New wall-path bugs surfaced (separate from flats, now on the roadmap):
  closed-door faces render as black holes (BIGDOOR2/4 — E1M3/E1M4/E1M7);
  near-view-parallel one-sided walls dropped entirely (E1M9 spawn corridor,
  ~70% of the view black); SLADRIP wall animation is a no-op (rotates the name
  hash together with the entry, so by-name lookup follows the rotation);
  `FLAT_MAX=64` silently truncates full-IWAD flats (shareware's 54 fit); flat V
  axis mirrored vs vanilla (`+worldY` instead of `−worldY`); vendored bsp
  `asr()` is round-toward-zero rather than floor (one-texel flat mis-wrap in
  negative-coordinate map regions).

## [0.29.2] - 2026-06-11

### Changed

- **Toolchain pin `6.1.29` → `6.1.37`** (`cyrius.cyml`). cycc 6.1.37 fixes the
  `--agnos` 3-operand-chained-constant-multiply miscompile (known issue #3), so
  the 0.29.1 2-operand workarounds are reverted to the clean chained form:
  `framebuf.cyr` `fb_buf = alloc(SCREEN_WIDTH * SCREEN_HEIGHT * 4)` and
  `render.cyr` `scalelight`/`zlight = alloc(LIGHTLEVELS * MAXLIGHT* * 8)`.
  **Verified the fold on the actual `--agnos` binary in QEMU** (serial probe):
  `fb_buf=256000`, `scalelight=6144`, `zlight=16384` — all correct (would be 800
  / undersized under cycc ≤ 6.1.35). `doom-smoke.sh` PASS — DOOM renders on AGNOS,
  240-colour framebuffer, no heap overflow. `cyrius.lock` regenerated for the new
  pin (clean `rm -rf lib && cyrius deps` → **37 entries**, verify 37/0). Linux
  build 601,568 B; 37/37 + 73/73; `render_frame` 2.557 ms (perf-neutral; codegen
  changed with the pin so cross-version comparison is not valid).

### Fixed

- **Standing still showed a dead world — monsters never woke and idle monsters
  never animated.** Two root causes, both reproduced via a pseudo-terminal
  harness driving the real-tty input path (the 35 Hz loop itself was already live
  at a verified 35.3 Hz after 0.29.1 — the *world* just wasn't visibly changing):
  - **Monster sight was capped at 1000 units.** `thing_ai_tick`'s SPAWN→SEE gate
    required `dist < MONSTER_SIGHT_RANGE` (1000 units), so all but the nearest
    monsters stayed permanently asleep — a probe at the E1M1 spawn found the
    nearest monster 936 units away and only 1 of 29 inside the cap. Real DOOM
    gates wake-up on line-of-sight (P_CheckSight) with **no distance cap**; the
    cap and the `MONSTER_SIGHT_RANGE` constant are removed. Monsters now wake on
    LOS as the player advances (verified: holding forward, `chase` count climbs
    0→1→2 and `see`→2 as line-of-sight opens). `thing_check_sight` already culls
    monsters with a one-sided wall between them and the player.
  - **Idle monsters rendered a single static frame.** `thing_animate`'s SPAWN
    case pinned monsters to frame 0; real DOOM's `*_STND` states alternate the
    two standing frames. Idle monsters now loop frames A↔B at an ~8-tick cadence,
    staggered by thing index (verified: idle frame-sum oscillates with zero
    input). Non-monster idle things (single-frame decor, items) stay on frame 0 —
    alternating them would request a B sprite many decorations don't have.

### Notes

- The E1M1 *spawn point itself* stays quiet with zero input even after these
  fixes — no monster anywhere has line-of-sight into the spawn alcove (faithful
  to DOOM). Visible ambient life now comes from idle-monster animation of any
  monster in view, and from monsters waking as the player moves. Sector light
  specials (flicker/strobe/glow) remain unimplemented — a future ambient-life
  item, not in this cut.

## [0.29.1] - 2026-06-11

### Fixed

- **Game world tick froze without player input — two distinct, platform-specific
  root causes, both found by *reproducing* the freeze (Linux locally, AGNOS in
  QEMU via `agnos/scripts/doom-smoke.sh`), not by static reading.** The world-tick
  calls (`player_tick`/`doors_tick`/`things_tick`/`texture_animate`) are
  unconditional in the loop, so both bugs sat upstream of them and stalled the
  whole 35 Hz loop.
  - **Linux: `read(stdin)` blocked the loop.** `input_poll`'s `read(0)` only polls
    non-blocking when stdin is a real tty whose raw-mode `TCSETS` honored `VMIN=0`
    (the 0.28.4 fix). For any *other* stdin — pipe, FIFO, redirect, the `x11view`
    GTK bridge, or when the `ioctl` silently failed because stdin is not a tty —
    `VMIN`/`VTIME` are ignored and `read(0)` BLOCKS until a byte arrives, freezing
    the loop in `input_poll` before any world tick. Fix: `input_enable_raw_mode`
    now also forces `O_NONBLOCK` on fd 0 via `fcntl` (a non-blocking guarantee
    independent of tty/`VMIN` state); `input_poll`'s existing `if (n > 0)` guard
    already treats `EAGAIN`/`n<=0` as "no input this frame". `input_disable_raw_mode`
    restores the saved flags on exit so the parent shell's stdin is not left
    non-blocking. Reproduced: a no-data stdin froze the game on its first frame
    (0 iterations); after the fix the world advances at ~33 Hz with zero input
    (103 frames / 3 s).
  - **AGNOS: a 255 KB per-frame heap overflow corrupted the render tables.**
    `framebuf_init` sized the blit conversion buffer as
    `alloc(SCREEN_WIDTH * SCREEN_HEIGHT * 4)` — a compile-time-constant **3-operand
    chained multiply that cycc's `--agnos` backend miscompiles** (`320*200*4` folds
    to **800**, not 256000; the 2-operand `320*200=64000` and runtime 3-operand
    multiplies are correct, and the Linux target folds it correctly). The resulting
    800-byte `fb_buf` vs the 256000 bytes `framebuf_blit_agnos` writes every frame
    stomped `colormap` / `zlight` / `flat_cache` (allocated just above `fb_buf`).
    Frame 1 rendered with intact tables; frame 1's `framebuf_flip` corrupted them;
    frame 2's `render_flat_spans` read a corrupted `zlight` → wild `colormap`
    pointer → ring-3 page fault → "frozen after one frame". Fix: size `fb_buf` as
    `SCREEN_SIZE * 4` (2-operand), and split the two light-table allocations
    (`scalelight` / `zlight` in `render_init_light_tables`) into a 2-operand entry
    count × 8 — all avoiding the miscompiled pattern. Reproduced + fixed in QEMU:
    idle world-advance went from 1 frame to continuous (105+ frames, no input).
    **Iron burn on archaemenid still pending.**

### Notes

- **cycc `--agnos` toolchain bug (report upstream):** compile-time-constant
  3-operand chained integer multiplies (`A * B * C`, all constant-folded)
  miscompile on the `--agnos` target only (confirmed cycc 6.1.29 + 6.1.35).
  Worked around in `framebuf.cyr` + `render.cyr`; audit any new all-constant
  `alloc(X * Y * Z)` site for the same trap.
- `--ppm` screenshot mode renders a single static frame and never enters the
  world-tick loop, so neither freeze was reachable through any PPM/CI gate — the
  reproductions had to drive the interactive loop.

## [0.29.0] - 2026-06-11

### Changed

- **agnos: the kernel scales now** — `framebuf_blit_agnos` no longer expands scale² pixels in
  ring 3; it palette-converts the raw 320×200 frame into a FIXED 256 KB 32bpp buffer and passes
  the integer scale to the kernel via `blit`(#39) a4 bits [39:32] (agnos 1.44.20). Per frame,
  ring 3 writes **64 K pixels instead of scale²·64 K**, and the old heap-budget scale cap (3)
  is gone — the panel's natural integer scale applies (e.g. **7 on 2560×1440**, capped at the
  kernel's 16). On an older kernel the scale bits are ignored (unscaled centered placement —
  degraded but harmless); ship with agnos ≥ 1.44.20.

## [0.28.4] - 2026-06-10

### Fixed

- **Player movement was 90° out of phase with the rendered view.**
  `render_transform_vertex` and the two `sprite.cyr` transforms computed
  view-space depth as `dy·cos − dx·sin`, orienting "forward / into-screen"
  toward north (BAM 256), while player movement, hitscan, the floor-span pass
  (`render_flat_spans`), and the map's thing-angle convention all use
  `(cos, sin)` = east (BAM 0, `degrees·1024/360`). Pressing forward therefore
  slid the player sideways relative to what was on screen, and walls disagreed
  with floors by 90°. Walls + sprites now use the same `(cos, sin)` convention:
  `ty = dx·cos + dy·sin` (depth), `tx = dx·sin − dy·cos` (lateral — the
  screen-right axis `(sin, −cos)` that `render_flat_spans` already used, verified
  against it so left/right is not mirrored). The `--ppm` view now faces the
  map-intended direction (the canonical E1M1 opening). Latent since the renderer
  was validated only via still `--ppm` screenshots; surfaced once the engine was
  driven interactively.
- **Player walked straight through solid walls.** `player_check_linedef`
  early-returned "passable" for any line that was neither `ML_BLOCKING` nor
  `ML_TWOSIDED` — i.e. every ordinary one-sided wall, which carries no
  `ML_BLOCKING` flag in the WAD (it is implicitly solid by having no back
  sidedef). One-sided lines (`!ML_TWOSIDED` / `side_left < 0`) are now solid at
  the distance test; two-sided step-up (≤24) / ceiling-fit logic unchanged.
- **35 Hz loop stalled between keystrokes on the Linux `/dev/fb0` path.** The
  raw-mode termios setup wrote `VMIN`/`VTIME` at byte offsets 22/21, assuming
  `c_cc` began at offset 16 — but the kernel `struct termios` carries a `c_line`
  byte at 16, so `c_cc` starts at 17 (`VTIME`=22, `VMIN`=23). `VMIN` was never
  zeroed and kept the terminal's inherited value of 1, making `read(stdin)`
  blocking; the game loop — and therefore `things_tick` / `doors_tick` — only
  advanced when a key arrived (monsters/doors froze when standing still).
  Corrected to offsets 23/22. (Linux path only; the AGNOS path uses `kbscan#42`
  and is unaffected.)
- **Oblique walls bowed (perspective distortion).** `render_seg` and
  `render_masked_segs` interpolated depth (`z`) linearly across screen columns,
  but for a flat wall it is the scale (`PROJ_DIST / z`), not `z`, that is linear
  in screen-x. Both loops now interpolate scale and derive per-column depth,
  straightening wall top/bottom edges and texture-height scaling on angled walls.
  `render_frame` 2.520 ms (perf-neutral; 22 ms budget).
- **Boot diagnostics bypassed sakshi.** The `loading map` / `map: <name>`,
  `map: V=… L=…` stats, and `things: N total (…)` lines were bare
  `syscall(1, …)` writes, rendering as un-prefixed bare lines interleaved with
  the structured `[ts] [INFO]` log. All three now route through `sakshi_info`
  (the two stat lines via `fmt_sprintf`), so they carry the standard prefix.

### Changed

- **Toolchain pin → `cycc 6.1.29`** (`cyrius.cyml`, was 6.0.83). The local
  toolchain launchers resolve the newest installed `cycc` regardless of the
  versioned path, so the pin now matches the only compiler that actually runs
  and the build is no longer "drift"-warned. Build 600,848 B; 37/37 + 73/73;
  `render_frame` 2.520 ms (cross-version perf vs 0.28.0 is not comparable — the
  codegen + bundled stdlib changed with the pin).
- **`cyrius.lock` regenerated for the new pin.** `./lib/` is a gitignored build
  artifact that `cyrius deps` populates from the pinned toolchain's stdlib, so
  bumping the pin changes the lock's contents. Regenerated via a clean resolve
  (`rm -rf lib && cyrius deps`) → **37 entries**; `cyrius deps --verify` 37/0.
  CI keeps the unchanged `cyrius deps` → `cyrius deps --verify` flow — a clean
  checkout resolves `./lib/` from the pinned stdlib and verifies 37/0.

## [0.28.3] - 2026-06-09

### Added

- **Keyboard input on AGNOS — DOOM is now playable past the title screen.** The
  `--agnos` build rendered its title but took no input (the loop sat on TITLEPIC
  forever): the old `input_poll` agnos branch returned no keys, because AGNOS's only
  stdin path (`read`#5) is blocking + line-disciplined + cooked-to-ASCII — fatal in
  the frame loop and dropping key-up. It now drains the kernel's new **`kbscan`#42**
  (a non-blocking raw Set-1 scancode poll), decodes make/break, and keeps `key_state`
  as **persistent held state** (a key stays down until its break code arrives —
  closer to real DOOM than the Linux press-then-clear path). Mapping: WASD move/strafe,
  arrows turn (`0xE0` extended), Space/E use, F fire, R run, Tab automap, 1–7 weapons,
  Q/Esc quit. `src/input.cyr`. Validated in QEMU via `agnos/scripts/doom-input-test.py`
  (USB-xHCI keyboard + HMP `sendkey`): `w` advances title→menu, `q` quits.
  Iron burn pending. Requires AGNOS kernel with `kbscan`#42.

## [0.28.2] - 2026-06-08

**DOOM renders on AGNOS.** The `--agnos` build now boots to the title screen
under the sovereign OS: the 584 KB ELF exec's from disk in ring 3, slurps the
4.2 MB `DOOM1.WAD` into memory, parses it, builds the palette, and blits a
240-colour frame to the hardware framebuffer via `fbinfo`#38 / `blit`#39. This is
the "agnsh launches DOOM" milestone — the first real userland application on
AGNOS. (Validated by `agnos/scripts/doom-smoke.sh`: gnoboot+OVMF+NVMe, ring-3
exec, WAD load, non-blank framebuffer screendump.)

Two AGNOS *kernel* fixes (in the `agnos` repo) unblocked the render — the WAD
needs ~24 MB and the old PMM only managed 16 MB; and the kernel could not reach
physical pages ≥16 MB to zero a freshly-`mmap`'d region. Neither is a port issue.

### Added / Changed

- **Warm-up `mmap`** (`main.cyr`, agnos only) — the FIRST `mmap` syscall from a
  freshly-exec'd ring-3 process corrupts the ring-3 return state on AGNOS (a
  kernel first-syscall-return bug, doom-specific; agnsh is unaffected). A
  throwaway `mmap` before `alloc_init` makes the real heap `mmap` the second
  syscall, which returns cleanly. Documented in-place; removed once the kernel
  bug is fixed. The Linux build is unchanged.

### Fixed

- Stripped the boot-bisect debug markers added during agnos bring-up.

## [0.28.1] - 2026-06-08

**AGNOS target support — cyrius-doom builds and runs `--agnos`.** The first
port of the engine to the sovereign OS (the "agnsh launches DOOM" arc). The
engine's OS interactions are branched under `CYRIUS_TARGET_AGNOS`, inlining the
agnos syscall numbers (which collide with Linux ones — e.g. agnos `0`=exit not
read, `2`=getpid not open, `16`=kill not ioctl), so the Linux build is byte-for-
byte unchanged.

### Added

- **Timing** (`tick.cyr`) — `tick_get_time_ns`/`tick_begin`/`tick_wait` use agnos
  `uptime_ms`(#40) + `sleep_ms`(#41) instead of `CLOCK_GETTIME`/`NANOSLEEP`.
- **Framebuffer** (`framebuf.cyr`) — `framebuf_init` queries geometry via
  `fbinfo`(#38); `framebuf_flip` builds a tightly-packed integer-scaled 32bpp
  frame and presents it via `blit`(#39) (the kernel handles the FB pitch), instead
  of `/dev/fb0` ioctls + `lseek`+`write`.
- **WAD** (`wad.cyr`) — agnos has no `lseek` (its syscall 8 is `dup`), so the WAD
  is slurped into memory at `wad_open` and the 5 seek sites route through a
  `wad_pread` offset reader. (Linux keeps the live-fd `lseek`+`read` path.)
- **Input** (`input.cyr`) — stubbed on agnos (no termios; key up/down events need
  a kernel raw-scancode mode — a follow-on). The title/menu renders without input.
- **Sound** (`sound.cyr`) — disabled on agnos (no PC-speaker `/dev/console`).
- **Process exit / WAD path** (`main.cyr`) — portable `doom_exit` (agnos exit is
  syscall 0); defaults the WAD path to `/DOOM1.WAD` when run with no argv.

### Notes

- Validated on the agnos kernel under QEMU: the 584 KB ELF execs from disk in
  ring 3, the heap/`mmap`, timing, and sakshi all initialize. WAD loading is
  currently gated on a kernel-side memory limit (the agnos 2 MB-page pool) — a
  kernel bite, not a port issue. The Linux build is unaffected (still renders).

## [0.28.0] - 2026-06-07

Graphics review / hardening / audit / performance pass — the new
anchor for the 0.28.x arc. A multi-agent audit of the entire render
path (render / framebuf / texture / sprite / status / menu + the
fixed-point math feeding them) surfaced 67 raw findings, triaged to
27 canonical and adversarially verified down to 20 real ones; 8
shipped here, the rest re-slotted across 0.28.x (see
`docs/development/roadmap.md`). Audit artifact:
`docs/audit/2026-06-07-v0.28-graphics-hardening.md`.

The headline is **memory-safety hardening of the patch decoders**:
the C2-class bounds checks that have lived in `texture_get_column`
since v0.24.0 were never propagated to the other three patch
decoders (weapon, sprite, HUD/menu/title) or to the `TEXTURE1`
parser, and the visplane row loops could write out of bounds on
crafted geometry. All four decode paths now mirror
`texture_get_column`, and the visplane projection is absolutely
clamped to its row-loop bounds. Latent on the trusted shareware
IWAD, reachable under the planned PWAD support — except F17, which
also fixed a real visible artifact on E1M1.

### Security

- **`render.cyr` — heap OOB *write* in the visplane loops (F17).**
  `ceil_screen` / `floor_screen` were only *relatively* clamped
  (`>= ct`, `<= cb`); the `vp_ceil_*` / `vp_floor_*` row loops
  (each `alloc(200*8)`) used the un-capped side, so a sector with
  extreme heights at minimum depth drove the projection past the
  array and `store64` ran off the end (the arrays are alloc'd
  consecutively, so the overflow corrupted the neighbouring
  visplane bounds). Now absolutely clamped to exactly the loop
  bounds — `ceil_screen <= SCREEN_HEIGHT` (the ceiling loop is
  half-open `[ct, ceil_screen)`) and `floor_screen >= -1` (the
  floor loop is `[floor_screen+1, cb]`) — which leaves every in-band
  row write identical on conformant maps. `map_validate()` bounds
  *indices*, not coordinates, so this was the real memory-safety
  boundary.
- **`render.cyr` / `sprite.cyr` / `status.cyr` — bound the patch
  column decoders (F01 / F02 / F03).** `render_draw_weapon`,
  `sprite_render_all`, and the shared HUD/menu/title decoder
  `st_draw_patch_shaded` read `read_le32(buf + 8 + col*4)` and
  walked post lists with only an iteration-count `safety` guard and
  no address bounds. Each now mirrors `texture_get_column`: column
  directory bounds (`8 + col*4 + 4 > size`), `col_off >= size`, and
  per-post `post + 1 >= end` / `post + 4 + length > end` checks,
  plus a `psz < 8` header floor. `st_draw_patch_from_buf` /
  `st_draw_patch_shaded` now take the backing lump size (threaded
  from every call site in `status.cyr` + `menu.cyr`).
- **`texture.cyr` — validate `TEXTURE1` offsets + patch refs (F19).**
  `texture_init` now bounds the offset directory and each
  texture's 22-byte header against the lump (`off + 22 > t1_size`
  skips a malformed entry — the zeroed `tex_table` slot is guarded
  by the existing `tw == 0` early-out), and `texture_get_column`
  bounds every 10-byte patch reference to the lump extent
  (`tex_def_end`). Completes the patch-decode attack surface.

### Fixed

- **`render.cyr` — visible corruption on E1M1 (F17).** As a direct
  consequence of the OOB-write fix above, an 11-pixel block at
  x=234–237, y=107–109 that previously rendered as stray near-black
  speckle (from the corrupted visplane bounds) now renders the
  correct floor texture. This is the only intended pixel change in
  0.28.0; all other frames (E1M1/E1M3/E1M5 game + automap +
  intermission, title, menu, skill) are byte-identical to 0.27.5.

### Removed

- **`render.cyr` — dead `render_flat_span` (singular) deleted (F16).**
  43-line per-pixel span routine with zero call sites (superseded
  by the deferred row-based `render_flat_spans`). Output unchanged.

### Performance

- **`render.cyr` — inline the flat fill + hoist the COLORMAP row
  (F11).** `render_flat_spans` called `flat_get_pixel` (re-masking
  `& 63`) and `render_shade` (re-clamping the light level, already
  `0..31` here) for *every* floor/ceiling pixel — two calls plus
  redundant work on the dominant fill path. The fetch is now
  inlined and the COLORMAP row pointer (`colormap + light*256`) is
  hoisted per span. Byte-identical output. **`render_frame`
  ≈2.10 ms → ≈1.78 ms (~15%)**, `render_frame+sprites` ≈2.12 ms →
  ≈1.78 ms, measured same-toolchain (cycc 6.0.83) before/after
  against the 22 ms @ 35 Hz budget (now ~12× headroom).
  `texture_get_column` unchanged (~685 ns).
- **`render.cyr` — cache the weapon patch (F14).**
  `render_draw_weapon` re-read the weapon lump from the WAD via
  `wad_read_lump_into` *every frame*; now re-read only when the
  firing frame actually changes the lump (guarded after the size
  check so a rejected lump is never cached).

### Changed

- **Toolchain pin `6.0.29` → `6.0.83`** in `cyrius.cyml`. Lock
  re-resolved (canonical 27 entries, `cyrius deps --verify` 27/0).
  Codegen-identical to 6.0.29 for the unchanged sources.

Binary `590,824 → 592,456 B` (+1,632 B: the patch-decode bounds
checks, net of the `render_flat_span` deletion). DCE NOP-sled
985 fns / 293,833 B. Tests 37/37 WAD-free + 73/73 full; fuzz
`fuzz_wad` 1k + `fuzz_fixed` 50k clean.

## [0.27.5] - 2026-06-01

Post-playtest movement fixes plus the toolchain/lockfile cleanup
(pulled forward from the v0.27.6 gated slot, now that cycc's
lockfile-writer regression is fixed upstream). Two real movement
bugs: inverted strafe, and a guard that silently dropped any
cardinal-axis move.

### Fixed

- **`player.cyr` — strafe direction inverted.** With forward =
  `(cos θ, sin θ)` and turn-left incrementing the angle (CCW),
  strafe-left is facing rotated +90° = `(-sin, +cos)` and
  strafe-right is −90° = `(+sin, -cos)`. The two blocks had the
  signs reversed, so `A` strafed right and `D` left. Swapped to
  match. `W`/`S` and arrow turning were already correct.
- **`player.cyr` — cardinal-axis moves dropped.** The movement
  apply block was gated on `move_x != 0 && move_y != 0` (nested
  ifs), so any move landing on an axis — pure forward/back or
  strafe while facing due N/S/E/W — never updated position. Now
  gated on `move_x != 0 || move_y != 0`; the full diagonal move is
  tried first, then X-only / Y-only wall slide.

### Changed

- **Toolchain pin `6.0.1` → `6.0.29`** in `cyrius.cyml`. Clears
  the per-build pin-drift warning and gives CI a toolchain whose
  `cyrius deps` lockfile writer works.
- **`cyrius.lock` now canonical (27 entries)** written by
  `cyrius deps`, replacing the hand-populated 5-entry `sha256sum`
  workaround. CI's empty-lock guard is dropped — `cyrius deps
  --verify` is an unconditional gate again. Resolves known-issue
  #1. (yukti `sys_stat` dup-fn, #2, stays — gated on a yukti
  rebundle; did not fire under 6.0.29 but left tracked.)

Binary 590,696 → 590,824 B (+128 B, the cardinal-axis move
restructure; strafe swap was size-neutral).

## [0.27.4] - 2026-06-01

Framebuffer geometry fix. The live `/dev/fb0` output path assumed
the panel was exactly 320×200×32 with a 1280-byte scanline pitch
and dumped a tightly-packed RGBA block at offset 0. On any real
display this tiled the frame horizontally and collapsed it into
the top ~20–33 px band. The `--ppm` path (self-describing) was
unaffected, so headless smoke never caught it. `framebuf_init`
now queries the real geometry and `framebuf_flip` integer-scales,
centers, and blits at the true pitch/bpp.

### Fixed

- **`framebuf.cyr` — real panel geometry.** `framebuf_init` now
  issues `FBIOGET_VSCREENINFO` (0x4600) + `FBIOGET_FSCREENINFO`
  (0x4602) ioctls to read `xres` / `yres` / `bits_per_pixel` /
  `line_length`, with defensive fallbacks if the driver reports
  nothing. Computes the largest integer scale that fits both axes
  and the centering letterbox offsets once at init.
- **`framebuf_flip` — correct blit.** New `framebuf_blit` helper
  integer-scales the 320×200 indexed frame into a full-screen
  scratch buffer honoring the physical pitch and bpp (32bpp
  XRGB8888 fast path via `store32`; 16bpp RGB565 fallback), then
  writes just the active band in one `write()`. Letterbox bars are
  blacked once at init and never rewritten.

### Removed

- **Dead `rgb_buf`** (256 KB) — the old flip's intermediate RGBA
  buffer. The PPM path reads `screen_buf` + `palette` directly and
  the new blit reads from `screen_buf`, so the intermediate is gone.

## [0.27.3] - 2026-05-21

`Result<T, E>` adoption at the WAD IO/parse boundary. Doom's
public-fn surface has been `: i64`-annotated since 0.27.2;
0.27.3 builds on that to retrofit typed-error returns where the
boot path needed them most. Replaces hand-coded `-1` / `0`
sentinels at the `wad_open` boundary with typed `WadError`
variants. Introduces the `?` propagation operator + exhaustive
`match` at the main-loop boundary — the first use of v5.8.x sum
types in doom's own code.

### Added

- **`enum WadError`** in `wad.cyr` — six variants
  (`WadOpenFailed` / `WadBadMagic` / `WadIoFailed` /
  `WadLumpNotFound` / `WadLumpTooBig` / `WadOther`).
  Wad-prefixed to coexist in the global enum-variant namespace
  per stdlib convention (matches `IoNotFound` / `JsonParseErr`
  / etc.).
- **`wad_read_lump_r(idx)`** — Result-returning parallel to
  `wad_read_lump`. Returns `Ok(buf_ptr)` on success;
  `Err(WadLumpNotFound)` for a bad index;
  `Err(WadIoFailed)` for a short read.
- **`wad_read_lump_into_r(idx, buf, max)`** — Result-returning
  parallel to `wad_read_lump_into`. Returns `Ok(bytes_read)`
  on success; same `Err` set as above.
- **`boot_init(wad_path)`** in `main.cyr` — Result-returning
  helper that cascades the boot-path WAD open + PLAYPAL lookup
  + PLAYPAL read via the `?` propagation operator. Replaces
  the prior inline `if (... != 0) { sakshi_error(...);
  syscall(60, 1); }` boilerplate.

### Changed

- **`wad_open(path)`** — in-place migration to
  `Result<i64, WadError>` (3 call sites total: `main.cyr`,
  `tests/doom.tcyr`, `benches/doom.bcyr`). Returns `Ok(0)` on
  success; `Err(WadOpenFailed)` if `file_open` fails;
  `Err(WadBadMagic)` if the header magic is neither `IWAD`
  nor `PWAD`; `Err(WadIoFailed)` if the header read is short.
  Removed inline `sakshi_error` calls — the typed `Err` lets
  the caller log a more informative message at the boundary
  via `match`.
- **`doom_main()`** boot path — `wad_open(argv(1)) != 0`
  inline check replaced with `var br = boot_init(argv(1)); if
  (is_err_result(br) == 1) { match load64(br + 8) { ... } }`.
  The match arm logs the typed cause (`cannot open WAD file`
  / `not a WAD file` / `WAD I/O failure` / `missing PLAYPAL
  lump` / `boot init failed`) before exiting with status 1.
  Compiler-enforced exhaustiveness via the explicit `_ =>`
  catch-all.
- **`tests/doom.tcyr`** — `wad_open` check uses `is_ok(...) ==
  1` rather than the legacy `== 0` int comparison. `alloc_init()`
  was already on the test entry path before `wad_open`, so the
  Result allocation runs safely.
- **`src/main.cyr`** banner bumped 0.27.2 → 0.27.3.

### Deferred

- **`texture.cyr` Result adoption** (roadmap item #3) —
  deferred to a follow-up cut. The wad-side adoption already
  demonstrates the full pattern (typed enum + `?` + `match`);
  texture's call sites in `render.cyr` (`texture_get_column`)
  are inside the hot render path and the existing `0`-on-fail
  sentinel is handled gracefully by the renderer, so the
  migration value is lower than wad-open's. Will revisit
  alongside the v0.28.x Black Book audit's column-rendering
  pass.

### Verified

- `cyrius build src/main.cyr build/doom`: 587,752 B (+2,528 B
  vs 0.27.2's 585,224 B — Result codegen + match jump tables +
  ?-operator emit. 985 unreachable fns / 291,438 B NOPed).
- `cyrius deps --verify`: 5 verified, 0 failed.
- `cyrius test tests/doom.tcyr` (WAD-free): 37/37 passed.
- `./build/test_doom wad/DOOM1.WAD` (full): 73/73 passed.
- `./build/doom wad/DOOM1.WAD --ppm`: E1M1 + automap +
  intermission PPMs at 192,015 B each; map summary unchanged.
- **Typed-error paths verified** by injecting bad inputs:
  - `./build/doom /nonexistent.wad` → `[ERROR] cannot open
    WAD file` (matches `WadOpenFailed` arm).
  - `./build/doom /etc/hostname` → `[ERROR] not a WAD file`
    (matches `WadBadMagic` arm — the file opens but has no
    IWAD/PWAD magic).
- Bench (`scripts/bench-history.sh`): `render_frame` 2.132 ms /
  `+sprites` 2.136 ms / `fixed_mul` 6 ns / `texture_get_column`
  749 ns / `pcache_get_hit` 8 ns — variance-level vs 0.27.2
  (2.114 / 2.127 / 6 / 730 / 7). Result allocations land at
  boot only (boot_init's `Ok(0)` + `Ok(pd)`), not on the hot
  render path — no per-frame allocation pressure.

### Known issues (unchanged from 0.27.0–0.27.2)

Both upstream-cycc workarounds still apply. Tracked under
v0.27.5 upstream-fix cleanup.

## [0.27.2] - 2026-05-21

Type-annotation sweep across doom's full public-fn surface —
adopts the v5.11.x annotation arc (parse-only `: i64` return-type
annotation, zero codegen change) on every fn in `src/*.cyr`,
matching the shape of vani's 0.9.3 internal sweep and bsp's
1.2.x planned cut. 269 single-line fn signatures + 1 multi-line
(`render_store_masked`) bumped to carry an explicit `: i64`
return tag. Documents return contracts inline; sets up
0.27.3's `Result<T, E>` adoption to retrofit error-bearing
returns without further signature churn at the call sites.

### Changed

- **`: i64` return annotations across all 20 modules in
  `src/*.cyr`** — 270 fn signatures total. Includes
  `render_transform_vertex` (multi-return tuple), which the
  annotation accepts as parse-only metadata since cycc 6.0.1
  treats `: i64` as a documentation hint without enforcing it
  against tuple-shaped returns. Highest-value boundaries
  (`wad` / `map` / `render` / `texture`) carry annotations
  same as every other module — no tiered rollout was needed
  because the sweep is mechanical and parse-only.
- **`src/main.cyr`** — banner string `cyrius-doom v0.27.1` →
  `cyrius-doom v0.27.2`. `load_map()` and `doom_main()` both
  annotated as `: i64` (the actual return values: 0 / -1 for
  load_map; doom_main exits via `syscall(60, …)` so its return
  is conventionally i64).

### Verified

- **Binary byte-identical**: 585,224 → 585,224 B. Confirms the
  annotation pass produces zero codegen delta. Matches vani
  0.9.3's "ABI-identical" claim under the same v5.11.x arc.
- `cyrius build src/main.cyr build/doom`: 585,224 B (982
  unreachable fns / 292,798 B NOPed — same as 0.27.1).
- `cyrius deps --verify`: 5 verified, 0 failed.
- `cyrius test tests/doom.tcyr` (WAD-free): 37/37 passed.
- `./build/test_doom wad/DOOM1.WAD` (full): 73/73 passed.
- `./build/doom wad/DOOM1.WAD --ppm`: E1M1 + automap +
  intermission PPMs 192,015 B each; map summary unchanged.
- Bench (`scripts/bench-history.sh`): `render_frame` 2.114 ms
  / `+sprites` 2.127 ms / `fixed_mul` 6 ns / `texture_get_column`
  730 ns / `pcache_get_hit` 7 ns — all within run-to-run
  variance of the 0.27.1 row (2.146 / 2.141 / 7 / 761 / 8).
  Annotations do not move frame time, as predicted.

### Known issues (unchanged from 0.27.0 / 0.27.1)

Both upstream-cycc workarounds still apply. Tracked under
v0.27.5 upstream-fix cleanup:

- `cyrius.lock` written empty by `cyrius deps` — hand-populated
  via `sha256sum`.
- `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition
  wins)` — codegen-identical.

## [0.27.1] - 2026-05-21

bsp 1.1.3 + vani 0.9.4 dep-tag re-pin — the half of the 0.27.0
cut that was held against upstream-publish. No source changes
in `src/*.cyr` beyond the version comments in `src/main.cyr`'s
header and the banner string; both upstream tags ship bundle
content byte-identical to their predecessor save for the
`Version:` header line. Same shape as v0.26.1's Cyrius pin-only
patch.

### Changed

- **`[deps.bsp]` 1.1.2 → 1.1.3** — picks up bsp's cyrius
  toolchain pin bump (5.5.2 → 6.0.1), `${file:VERSION}`
  template, `cyrius.toml` + `.cyrius-toolchain` retirement,
  and CI lift to the patra-style installer. `dist/bsp.cyr`
  bundle content is byte-identical save for the `Version:`
  header (1.1.2 → 1.1.3).
- **`[deps.vani]` 0.9.3 → 0.9.4** — picks up vani's cyrius
  pin bump (5.11.4 → 6.0.1), yukti 2.2.2 → 2.2.4, patra
  1.9.3 → 1.9.5, and `cc5_aarch64 → cycc_aarch64` CI rename.
  `dist/vani-core.cyr` bundle content is byte-identical save
  for the `Version:` header.
- **`src/main.cyr`** — vendored-dep version comments bumped
  (`bsp @ 1.1.1` → `bsp @ 1.1.3`, `vani @ 0.9.1` → `vani @
  0.9.4`); these two comments had lagged through 0.27.0).
  Banner string `cyrius-doom v0.27.0` → `cyrius-doom v0.27.1`.
- **`cyrius.lock`** — re-anchored to the new bundle hashes:
  `lib/vani-core.cyr` `9891f720… → 74000d17…`, `lib/bsp.cyr`
  `… → 8ae89a9e…`. Yukti / patra / sakshi hashes also rotate
  as vani's transitive dep tree resolved fresh.
- **Binary size**: 585,320 → **585,224 B (−96 B)**. The delta
  is the `Version:` header swap in the two bundles
  (`# Version: 0.9.3` → `# Version: 0.9.4`, `# Version: 1.1.2`
  → `# Version: 1.1.3`). Variance-level, not a real shrink —
  recovery to ~260 KB remains gated on Cyrius O3 real DCE.

### Verified

- `cyrius deps`: 5 resolved (after hand-populating `cyrius.lock`
  via `sha256sum`, same cycc 6.0.1 lockfile-writer workaround
  documented under 0.27.0 Known issues).
- `cyrius deps --verify`: 5 verified, 0 failed.
- `cyrius build src/main.cyr build/doom`: 585,224 B (982
  unreachable fns / 292,798 B NOPed).
- `cyrius test tests/doom.tcyr` (WAD-free): 37/37 passed.
- `./build/test_doom wad/DOOM1.WAD` (full): 73/73 passed.
- `./build/doom wad/DOOM1.WAD --ppm`: E1M1 + automap +
  intermission PPMs all written at the expected 192,015 B
  each; map summary `V=467 L=475 SD=648 S=85 SG=732 SS=237
  N=236 T=138` matches 0.27.0 / 0.26.2.
- Bench (`scripts/bench-history.sh`): `render_frame` 2.146 ms,
  `render_frame+sprites` 2.141 ms, `fixed_mul` 7 ns,
  `texture_get_column` 761 ns, `pcache_get_hit` 8 ns — all
  within run-to-run variance of 0.27.0's pre-publish numbers.

### Known issues (carried over from 0.27.0)

Both upstream-cycc workarounds documented under 0.27.0 still
apply unchanged in 0.27.1:

- `cyrius.lock` written empty by `cyrius deps` — workaround:
  hand-populate via `sha256sum lib/{vani-core,bsp,yukti,patra,
  sakshi}.cyr > cyrius.lock`. CI's `--verify` step stays
  gated on a populated lockfile.
- `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition
  wins)` — codegen-identical, drops when yukti drops the
  duplicate from its dist. Pending tracked under 0.27.5
  upstream-fix cleanup.

## [0.27.0] - 2026-05-21

Cyrius 6.0.1 lift + manifest modernization. Opens the 0.27.x
patch arc — held against the Cyrius O4 linear-scan regalloc
landing for the "performance pass" was the original 0.27.0 thesis,
but the v6.0.0 cycle-open (cybs/cycc rename) + the v5.8.x sum-type
/ `Result<T,E>` / `?` / exhaustive-match infrastructure that's
now landed in stdlib makes a `language-adoption` arc the higher-
value 0.27.x sequence. O4 perf-pass re-targets to 0.28.x once
the upstream regalloc ships. The 0.27.x patches now sequence as:
0.27.0 cyrius lift + manifest, 0.27.1 bsp/vani dep-tag re-pin
(post-publish), 0.27.2 type annotations on public surface, 0.27.3
`Result<T,E>` adoption in `wad.cyr` / `render.cyr` error paths,
0.27.4 `lib/test.cyr` table-driven test refactor.

### Changed

- **Cyrius 5.7.48 → 6.0.1**. Covers the v5.8.x language arc
  (`Result<T,E>` carve-out into `lib/result.cyr` at v5.8.28,
  sum-type syntax / `enum Foo { Bar(T); }` at v5.8.21,
  `?` operator + exhaustive-match warnings at v5.8.21-25), the
  v5.9.x stdlib enrichment, the v5.11.x annotation arc
  (`fn foo(): i64` return types — parse-only, zero-codegen-change),
  v5.11.59 DCE-aware undef-fn reachability filter (cleaner
  compiler warnings), v5.11.60 `_exec3` argv/envp byte-contract
  fix in `lib/process.cyr`, v5.11.65 CVE-05 tok_names mangle-path
  overflow fix in the compiler itself, v6.0.0 two-binary rename
  ceremony (`cyrc → cybs`, `cc5 → cycc`; ~2,100 occurrences
  across cyrius repo), and v6.0.1 stdlib-resolution path hotfixes
  (the rename-skip off-by-one that shipped `ud2/ud2/nop` sentinels
  to UEFI consumers — fixed same-day).
- **Binary growth**: 565,856 → 585,320 B (**+19,464 B, +3.4 %**)
  on cycc 6.0.1. Honest growth-tax from the v5.11.x annotation
  rt-table widening + v5.8.x sum-type emit. Cyrius's own
  v6.0.x byte-array-literal-peephole + dead-code careful sweep
  are expected to recover a portion; the long-deferred O3 real
  DCE recovery to ~260 KB still gates on upstream. Frame time
  unchanged (~3.9 ms/frame on E1M1).
- **Manifest hygiene** (matches patra/vani/sakshi/mihi
  convention):
  - **`cyrius.toml` + `cyrb.toml` deleted.** `cyrius.cyml` is
    now the single manifest, matching every other modern
    first-party lib. The legacy `.toml` shims existed during
    the 5.x cyml transition; v6.0.0 closed that transition.
  - **`version = "${file:VERSION}"` template** in `cyrius.cyml`
    — version single-source-of-truth at `VERSION`. CI's
    consistency check now resolves the template (same pattern
    patra/vani CI use).
- **`[deps.vani]` 0.9.1 → 0.9.3** — picks up vani's stdlib
  annotation pass (`: i64` return-type annotations on every
  public fn in vani's `src/*.cyr` — parse-only, ABI-identical).
  Vendored `dist/vani-core.cyr` still 800 lines, same 22
  `audio_*` symbols, header bumped 0.9.1 → 0.9.3.
- **CI workflows refreshed**:
  - Adopted patra's pre-flight HTTP check on the Cyrius release
    asset — surfaces a clear error when the cyml pin is bumped
    ahead of the published release (catches the failure pattern
    documented in patra v1.9.0 CI fix).
  - Version-pinned toolchain install layout
    (`~/.cyrius/versions/$V/{bin,lib}/`) — required by cycc
    6.0.1's stdlib resolver, matches every other modern repo.
  - `${file:VERSION}` template resolution in the
    version-consistency check.
  - `cyrius deps --verify` gated on a populated lockfile
    (cycc 6.0.1 has a known regression where `cyrius deps`
    writes an empty `cyrius.lock` for some manifest shapes
    incl. ours — workaround documented inline, drops when the
    upstream fix lands).
  - `cyrius.toml` removed from the required-docs check.
- **`cyrius.lock` re-anchored** for the new vani 0.9.3 dist
  hash (`9891f720…` vs prior `aaa8fba9…`). bsp 1.1.2 dist
  hash unchanged.
- **`src/main.cyr` banner** bumped 0.26.2 → 0.27.0.

### Known issues (downstream)

- `warning:lib/yukti.cyr:39: duplicate fn 'sys_stat' (last
  definition wins)` — cycc 6.0.1's bundled
  `lib/syscalls_x86_64_linux.cyr` defines `sys_stat(path, buf):
  i64`; vani's transitively-bundled yukti 2.2.4 dist defines
  `sys_stat(path, buf)` without the annotation. The two
  implementations are byte-identical at the codegen layer
  (yukti's wins). Drops when yukti re-bundles with the cyrius
  stdlib sys_stat dropped from its own surface — out of scope
  for cyrius-doom.
- `warning: cyrius.lock: 0 deps locked` — cycc 6.0.1
  lockfile-writer regression (acknowledged upstream, fix
  pending). Workaround: this repo's `cyrius.lock` is populated
  by hand (`sha256sum lib/{vani-core,bsp,yukti,patra,sakshi}.cyr`)
  so `cyrius deps --verify` still succeeds locally; CI gates
  the verify step on a populated lock so it doesn't trivially
  pass against a freshly-empty resolver write.

### Verified

- `cyrius deps --verify`: 5 verified, 0 failed.
- `cyrius build src/main.cyr build/doom`: 585,320 B (CYRIUS_DCE=1
  identical, 987 unreachable fns / 290,955 B NOPed).
- `cyrius test tests/doom.tcyr`: 37/37 passed (WAD-free subset).
- `./build/doom wad/DOOM1.WAD --ppm`: E1M1 + automap + intermission
  PPMs all written; map summary `V=467 L=475 SD=648 S=85 SG=732
  SS=237 N=236 T=138` matches 0.26.2.
- `bsp 1.1.3` (pinned in `[deps.bsp]` once published): 79/79
  tests, 13/13 benches sub-μs, 25K fuzz iters across 3 harnesses
  — same gates, growth-tax of +18,144 B in standalone bsp binary
  (76,496 → 94,640 B) from cyrius 6.0.1.

### Pending (queued for 0.27.1)

- **`[deps.bsp]` 1.1.2 → 1.1.3** + **`[deps.vani]` 0.9.3 → 0.9.4**
  — both upstream tags carry only the cyrius pin bump (5.5.2 →
  6.0.1 for bsp; 5.11.4 → 6.0.1 for vani) and CI-yml rename
  (`cc5_aarch64` → `cycc_aarch64`). The bundle content for
  `dist/bsp.cyr` and `dist/vani-core.cyr` is byte-identical to
  the current 1.1.2 / 0.9.3 pin (only the `Version:` header
  differs). 0.27.1 rolls forward once the user tags + publishes.

## [0.26.2] - 2026-05-01

Toolchain + audio-stack hygiene cut. Unblocks CI (vani 0.9.x
requires Cyrius 5.7.48 stdlib surface, but `.cyrius-toolchain`
was still pinned at 5.5.2), opts cyrius-doom into vani's new
`audio-core` distribution profile (29 KB single-module bundle
vs the 76 KB full bundle, 22 `audio_*` symbols vs 106), and
collapses the manifest drift between `cyrius.cyml` /
`cyrius.toml` / `cyrb.toml`. No source behavior changes — the
`audio_*` ABI is byte-identical between vani profiles, and
`src/audio.cyr` calls exactly six of the 22 core-profile
symbols.

### Changed

- **Cyrius 5.5.2 → 5.7.48** — `cyrius.cyml` and `cyrius.toml`
  pinned to 5.7.48. The CI break was caused by `cyrius.cyml`
  declaring `cyrius = "5.7.48"` (required by vani 0.9.x's
  manifest, which references stdlib modules `fs` / `hashmap` /
  `tagged` / `fnptr` / `freelist` / `process` / `patra` that
  didn't ship in the 5.5.2 stdlib bundle) while the toolchain
  installer file CI was reading (`.cyrius-toolchain`) was
  still 5.5.2.
- **`.cyrius-toolchain` deleted.** CI now reads the pinned
  toolchain from `cyrius.cyml`'s `cyrius = "..."` line via
  `grep -oP '(?<=^cyrius = ")[^"]+' cyrius.cyml` — the same
  pattern vani / yukti CI uses. Single source of truth
  eliminates the drift vector that caused this CI break.
- **vani 0.3.0 → 0.9.1 (`core` profile)** — `[deps.vani]` now
  pins `tag = "0.9.1"` with `modules = ["dist/vani-core.cyr"]`
  (was `"dist/vani.cyr"`). The core profile is a strict subset
  of the full bundle: only `src/alsa.cyr`'s `audio_*` shim,
  29,015 B / 800 lines / 22 public symbols. cyrius-doom's
  `src/audio.cyr` calls 6 of those 22 — every other vani
  module (`buffer` / `capture` / `device` / `error` /
  `format` / `mixer` / `playback`) is dropped at the bundle
  level, not just at the dead-code level. The `audio_*` ABI
  is byte-identical between profiles, so `src/audio.cyr` is
  unchanged.
- **`src/main.cyr` include** swapped `lib/vani.cyr` →
  `lib/vani-core.cyr` to match the new manifest path. Header
  comment refreshed to point at vani 0.9.1 and to call out
  that the full `vani_*` higher-level helpers are still one
  manifest line away if a later sound rework wants them.
- **Manifest hygiene**:
  - `cyrius.toml` and `cyrb.toml` synced to `cyrius.cyml`'s
    canonical `[deps]` shape: stdlib list drops the retired
    `audio` (5.8.0) and adds `fs` / `hashmap` / `tagged` /
    `fnptr` / `freelist` / `process` / `sakshi` to cover
    vani's transitive needs.
  - **`patra` dropped from stdlib** — vani's `[deps.patra] @
    1.9.2` git override provides it transitively, and listing
    it in both places triggered double-resolution (the cc5
    deps writer can't reconcile a stdlib copy + a git symlink
    for the same `lib/` path). Mirrors what vani did
    internally to its own stdlib list at 0.9.0. CI surfaced
    this as `error: cannot write lib/patra.cyr`.
  - `cyrb.toml`'s stale `[deps.shravan]` (2.0.0, never used
    in this branch) replaced by `[deps.vani] @ 0.9.1`.
  - **`lib/` no longer committed.** Was tracked as a mix of
    real stdlib copies (mode 100644) and symlinks to the
    local developer's `/home/<user>/.cyrius/...` (mode 120000)
    — the symlinks were dangling on every CI runner. Now
    fully gitignored (`/lib/` in `.gitignore`, matching vani
    / yukti); `cyrius deps` populates it fresh on every
    checkout. 18 previously-tracked files dropped from the
    index.

### CI alignment with vani / yukti

- **Toolchain version sourced from `cyrius.cyml`** instead of
  the now-deleted `.cyrius-toolchain` file. Same `grep -oP`
  pattern vani uses. Applies to both `ci.yml` and
  `release.yml`.
- **`Lock file present` step** added before `cyrius deps` —
  guards against accidental `.gitignore` changes that would
  let `cyrius.lock` slip out of git, defeating the
  supply-chain integrity check.
- **`cyrius deps --verify` step** added after `cyrius deps`
  in both `build` and `test` jobs. Verifies the lockfile
  hashes match the just-resolved `lib/` contents — catches
  upstream tag rewrites and dep tampering.
- **Version-consistency check** in the `docs` job now
  cross-checks `VERSION` against `cyrius.cyml`,
  `cyrius.toml`, and `CHANGELOG.md`. Stops a release from
  shipping with version drift.

### Binary size — honest read

| Build | `build/doom` | Δ |
|---|---|---|
| 0.26.1 (vani 0.3.0, full) | 259,920 B | baseline |
| 0.26.2 mid-bump (vani 0.9.0, full) | 600,608 B | +340,688 B |
| **0.26.2 final (vani 0.9.1, core)** | **565,856 B** | **+305,936 B vs 0.26.1, −34,752 B vs full** |

Trimming vani's bundled source from 76 KB → 29 KB (47 KB
delta) translates to a ~35 KB binary savings — about 5.8 % off
the full-bundle build. The remaining ~306 KB of regression vs.
0.26.1 is unreachable today: every public symbol vani exports
gets a NOPped function body in the cyrius-doom output under
the current cc5 NOP-sled DCE. Real recovery to ~260 KB lands
when **Cyrius phase O3 (real DCE replaces NOP-sled)** ships,
at which point the core profile's smaller surface compounds
with O3 to drop the unused `audio_*` getters and the
capture-side path entirely.

The proposal that drove the audio-core profile predicted
"~340 KB recovered"; that prediction was overstated for the
same DCE reason. The mechanism works as designed; the size
win is bottlenecked on Cyrius, not on vani. See
`docs/proposals/archive/vani-audio-core-profile.md` for the
full closing-loop analysis.

### Audio dep — transitional shape

`vani` is **not** the long-term audio dep for cyrius-doom.
The current trajectory:

1. **vani** (today, 0.9.1 core) — covers the gap left by the
   cyrius stdlib `audio` retirement (5.8.0 fold-in). Stable
   `audio_*` shim, byte-stable ABI, single-module 29 KB
   bundle. Good enough until dhvani lands.
2. **dhvani** (planned) — Rust-to-Cyrius port. Will replace
   vani in `[deps.*]` once the port hits feature parity for
   the playback path cyrius-doom uses. Same `audio_*` shape
   is the migration target so `src/audio.cyr` stays
   ABI-stable across the swap.

Treat vani's surface in cyrius-doom as a temporary pin, not a
long-term commitment. The audio-core profile choice was made
specifically with this swap in mind: the smaller the vani
surface, the smaller the dhvani port's day-one feature target.

### Documentation

- **Audio-core proposal**, drafted, accepted, and archived at
  `docs/proposals/archive/vani-audio-core-profile.md`. Includes
  the original three-cut patch-series proposal (0.9.1 → 0.9.2 →
  0.9.3) that vani collapsed into a single 0.9.1 cut, the
  resolution section, and the closing-loop measurement
  (565,856 B post-flip). First entry under
  `docs/proposals/archive/`; future settled proposals will
  land alongside it.

### Gates

- `cyrius deps`: 5/5 resolved, `cyrius.lock` rewritten clean.
- `cyrius build src/main.cyr build/doom`: OK (565,856 B).
- `cyrius test tests/doom.tcyr`: 37/37 WAD-free assertions
  pass (CI's headless subset). Full 73-assertion suite needs a
  WAD path; not exercised in CI by design.
- `./build/doom wad/DOOM1.WAD --ppm`: E1M1, automap, and
  intermission render cleanly. ALSA path emits the expected
  `[WARN] audio: no device` on the headless CI runner, no
  device under `/dev/snd/`.

### Tracking the upstream optimizer track

Unchanged from 0.26.1 — cyrius-doom still holds v0.27.0
"performance pass" against Cyrius O4 linear-scan regalloc
landing. The 0.26.2 toolchain bump (5.5.2 → 5.7.48) does not
include any of O2 / O3 / O4 — those are scheduled in the
parallel cyrius optimizer queue, not in the 5.7.x stabilization
line.

The honest-read above on binary size is the most concrete
demonstration to date of why O3 matters: a clean 47 KB
source-bundle trim recovered only ~35 KB of binary, because
~306 KB of `0x90` filler is structurally trapped behind the
NOP-sled DCE. O3 unlocks it as a free win.

## [0.26.1] - 2026-04-20

### Changed

- **Cyrius 5.5.0 → 5.5.2** — picks up the enum-constant `sc_num`
  fold that shipped in 5.5.1 (PE syscall reroutes) + 5.5.2 (the
  actual fold). Every enum variant read now emits `mov rax, imm32`
  (5 B) instead of `mov rcx, gvaddr; mov rax, [rcx]` (~10 B).
  cyrius-doom is enum-dense (`MapMax`, `MapSize`, `MapLineFlag`,
  `MapMisc`, `Fixed`, `Angle`, `ViewConst`, `WeaponConst`,
  `BspFixed`, `BspNode`, `BBox`, `BlockmapConst`, …), so the win
  compounds across the codebase.
- **BSP 1.1.1 → 1.1.2** — bsp's own toolchain pin bumped, same
  enum-fold benefit on its standalone build.
- **Binary shrink**: 267,216 B (on 5.5.0) → **259,920 B (on 5.5.2)** —
  **−7,296 B (−2.7 %)** purely from the 5.5.2 enum fold, no code
  changes in cyrius-doom. bsp standalone: 77,944 → 76,496 B
  (−1,448 B, −1.86 %).
- **Benches on 5.5.2**: `fixed_mul` 4 ns, `pcache_get_hit` 9 ns,
  `atan2` 13 ns, `point_on_side` 29 ns, `render_frame` 2.53 ms —
  within run-to-run variance of 0.26.0 numbers (the enum fold is
  a codegen-size win, not a runtime-hot-path win).

### Gates

- 9/9 shareware maps render (via bsp library traversal).
- 73/73 tests pass; 50K + 1K fuzz iters clean.
- fmt + lint clean across all 20 cyrius-doom modules and vendored
  lib/bsp.cyr.

### Tracking the upstream optimizer track

Cyrius's parallel O1–O6 compiler-optimization queue (see
`cyrius/docs/development/roadmap.md` §"v5.4.x Queue"). The 5.5.2
fold is a narrow peephole-class win that doesn't touch the hot
runtime path; the larger wins for cyrius-doom arrive with:

- **Phase O2** (peephole: strength reduction, flag reuse, LEA
  combining, aarch64 `madd`/`msub`): small runtime wins on hot
  loops. Incrementally.
- **Phase O3** (IR-driven DCE + const prop + dead-store elim):
  **real** DCE replaces today's NOP-sled — binary actually
  shrinks instead of staying 260 KB with 49 KB of `0x90` filler.
- **Phase O4** (linear-scan register allocator): the one that
  matters. 2–3× on hot inner loops per Poletto-Sarkar; will
  unlock a v0.27.0 "performance pass" release targeting sub-
  millisecond `render_frame`.

No hand-optimization of `fx_mul` / `asr` / column loops until
O2–O4 land — the compiler will do it uniformly and avoid
fighting the codegen.

## [0.26.0] - 2026-04-20

### Added — bsp is a real dep

Turned the "Composes: bsp" line from aspirational into mechanical truth.
Prior versions rolled their own BSP traversal in `render.cyr` +
`src/map.cyr`; 0.26.0 vendors bsp 1.1.1's single-file distribution and
calls into the library.

- **Manifest migrated to `cyrius.cyml`** (5.x convention, modelled on
  `libro/cyrius.cyml`). `cyrius.toml` kept alongside as a build-tool
  compatibility shim during the transition.
- **`[deps.bsp]`** pinned to `tag = "1.1.1"`, `modules = ["dist/bsp.cyr"]`.
  The Cyrius build tool symlinks `lib/bsp.cyr` →
  `~/.cyrius/deps/bsp/1.1.1/dist/bsp.cyr`, so the vendored copy stays in
  sync with upstream.
- **`lib/bsp.cyr` included first** in `main.cyr`, `tests/doom.tcyr`, and
  `benches/doom.bcyr` — before `src/fixed.cyr`, which now shares bsp's
  `asr()` (stripped the duplicate definition; they were identical).

### Changed — ad-hoc BSP primitives → bsp library calls

- **`src/render.cyr`** — `render_bsp_node` now calls `bsp_is_subsector` /
  `bsp_subsector_idx` / `bsp_point_on_side(map_nodes, ...)` /
  `bsp_node_child_r(map_nodes, ...)` / `bsp_node_child_l(map_nodes, ...)`.
  Layout-compatible: cyrius-doom's 112-byte node block has identical
  field offsets to bsp's.
- **`src/player.cyr`** — `player_find_sector`'s BSP walk likewise.
- **`src/sprite.cyr`** — sprite's floor-lookup BSP walk likewise.
- **`src/map.cyr`** — deleted `map_point_on_side`, `map_is_subsector`,
  `map_subsector_idx`, and the `map_node_{x,y,dx,dy,child_r,child_l}`
  accessors. Kept `MAP_NODE_SIZE = 112` for the loader's alloc sizing;
  noted the layout-match with `BSP_NODE_SIZE` in a comment.
- **`benches/doom.bcyr`** `point_on_side` bench switched to
  `bsp_point_on_side`.

### Benchmarks (on Cyrius 5.5.0, bsp 1.1.1)

| Metric | 0.24.6 | 0.26.0 | Delta |
|---|---|---|---|
| `render_frame` avg | 2.73 ms | 2.50 ms | **−8.4%** |
| `render_frame+sprites` avg | 2.113 ms | 2.53 ms | ~flat |
| `point_on_side` | 23 ns | 30 ns | +7 ns (explicit `nodes` arg) |
| `fixed_mul` / `asr` / `pcache_hit` | 4 / 4 / 9 ns | 4 / 4 / 9 ns | unchanged |

The render_frame win is cache/layout: one shared `asr()` definition
instead of two, and consolidated node-access through bsp's accessor
pattern. The +7 ns on `point_on_side` is the cost of passing `map_nodes`
explicitly — trivially compensated for by the render_frame win since the
BSP walk hits it ~N_nodes times per frame but other path code benefits
from the uniformity.

### Gates

- Build: OK, binary 259,920 bytes.
- 9/9 shareware maps render (E1M1–E1M9) via the bsp traversal.
- Tests: 73/73 (`build/test_doom wad/DOOM1.WAD`).
- Fuzz: `fuzz_fixed` 50K iters + `fuzz_wad` 1K iters pass.
- Lint: clean across all 20 cyrius-doom modules.
- Fmt: `src/render.cyr` formatted-in-place (pre-existing multi-line arg
  indentation nits cc5's formatter wanted normalized).

## [0.24.6] - 2026-04-20

### Fixed

- **E1M6 map load** — `MAP_MAX_SSECTORS` raised 512 → 1024. E1M6 ("Central Processing") has 606 subsectors; prior cap truncated loading and left node child indices dangling, so `map_validate()` correctly rejected the map. Latent since the v0.24.0 validator shipped — the "all 9 maps render" claim in 0.24.x was inaccurate (test suite only exercised E1M1). All 9 shareware maps now render.
- **tests/doom.tcyr missing includes** — `input.cyr`, `player.cyr`, and `things.cyr` added. Cyrius 5.5.0 hardens undefined-variable references into compile errors (previously soft-warn), so the incomplete include chain now fails loudly at `cyrius test`. `./build/test_doom wad/DOOM1.WAD` → 73/73 pass.

### Changed

- **Cyrius 5.5.0** — toolchain bump from 4.8.5-1. No source changes required for language compatibility. cyrius.toml + .cyrius-toolchain + main.cyr banner updated.
- **BSP 1.1.0** — sibling dep upgraded on 5.5.0. Signed-shift correctness audit: `asr()` replaces bare `>>` on signed values across `aabb_center_*`, `bsp_point_seg_dist`, and both `frustum_test_*` functions. DOOM wasn't biting these because integer-fx coords aligned the low bits; non-DOOM consumers would have. 79/79 tests (+5 regression asserts), 25K fuzz iters still pass, benches unchanged. cyrius-doom references bumped to 1.1.0 in CLAUDE.md + cyrb.toml.
- **Binary size**: 248976 bytes (~243 KB). Essentially flat vs 0.24.5.
- **Benchmarks on 5.5.0** (100 iters render_frame):
  - `fixed_mul` 4ns, `fixed_div` 3ns, `asr` 4ns, `sin_lookup` 4ns (unchanged)
  - `atan2` 13ns, `pcache_get_hit` 9ns (was 10ns), `colormap_shade` 4ns
  - `render_frame` avg 2.73ms, `render_frame+sprites` avg 2.113ms (well under 22ms budget)
- **Fuzz**: `fuzz_fixed` 50000 iterations OK, `fuzz_wad` 1000 iterations OK.

## [0.24.5] - 2026-04-14

### Changed

- **Cyrius 4.8.5-1** — pinned cyrius.toml minimum. All 9 maps render, 51K fuzz iterations pass, BSP 74/74 tests green. Note: `render_frame` showed 2.59 → 2.92ms on this run (run-to-run variance, not a regression — hot math path unchanged at 4ns fixed_mul, pcache_hit improved 12 → 10ns).

## [0.24.4] - 2026-04-14

### Changed

- **Cyrius 4.8.2** — cyrius.toml pinned to 4.8.2 minimum. Switch jump-table tuning (density 33%, range cap 1024) makes more cases eligible for O(1) dispatch.
- **Switch conversions for hot paths** — converted 4 if-chains to switch statements. Compiler decides jump-table vs chain per cluster:
  - `player_current_ammo()` — 7-case weapon → ammo-type lookup (range 1-7, dense, jump-table qualifies)
  - `player_try_fire()` — 7-case weapon → fire+deduct (same structure)
  - `thing_classify()` — weapon type (2001-2006, dense 6-case)
  - `things_check_pickups()` — unified 21-case pickup dispatch with keys (5-13), weapons (2001-2006), items (2007-2019), ammo boxes (2046-2049). Armor stays in if-chain (has conditional logic).

### Performance

- **render_frame: 2.66ms → 2.59ms** (2.6% faster)
- **render_frame+sprites: 2.76ms → 2.63ms** (4.7% faster)
- Hot-path dispatch is now measurably cheaper on per-tick item pickup checks

## [0.24.3] - 2026-04-14

### Changed

- **Cyrius 4.6.2** — rebuilt and verified on the new toolchain. Added `cyrius = "4.6.2"` pin + `language = "cyrius"` to cyrius.toml. No code changes. All 9 maps render, 51K fuzz iterations pass.
- **BSP 1.0.1** — dep tag bumped (also rebuilt on 4.6.2, no code changes). 74/74 tests pass.
- Minor benchmark improvements: `atan2` 17ns → 13ns, `colormap_shade` 6ns → 4ns, `pcache_get_hit` 13ns → 12ns. DCE report smaller (32KB → 26KB of dead stdlib — compiler got smarter about reachability).

## [0.24.2] - 2026-04-13

### Changed

- **BSP 1.0.0** — bsp dependency stable release. API unchanged from 0.9.0. Indicates production-ready status.

## [0.24.1] - 2026-04-13

### Changed

- **`&&` / `||` short-circuit cleanup** — now that Cyrius 4.4.1 fixed short-circuit semantics, converted nested `if (a) { if (b) { ... } }` patterns to `if (a && b) { ... }` across 9 files. 15+ sites cleaned: WAD magic check (4-level nest → 1 line), sky name check, near-plane clip, walk-over crossing, player collision ceiling/floor checks, screen bounds, armor pickup conditions, level coord parsing. Same semantics, half the lines.
- **Cyrius 4.4.3 verified** — cc3 reports 196 unreachable fns (32KB dead stdlib). `CYRIUS_DCE=1` NOPs 17KB. Clean `cyrlint` across all 20 files.

## [0.24.0] - 2026-04-13

### Security (CVE Audit Hardening)

- **C1: Map index bounds validation** — added `map_validate()` that runs after `map_load()`. Checks all cross-references: seg v1/v2 < num_vertexes, seg linedef < num_linedefs, linedef v1/v2 < num_vertexes, sidedef sector < num_sectors, subsector firstseg+numsegs <= num_segs, node child indices in range (with subsector flag handling). Returns -1 on any invalid index.
- **C2: Texture column bounds** — patch cache now stores per-slot lump size (`PCACHE_SLOT_SIZE` 8200→8208). `texture_get_column()` validates column header offset and column data offset within lump bounds. Post iteration loop checks `post_ptr < pdata_end` and `post_ptr + 4 + length <= pdata_end` before reading.
- **C3: BLOCKMAP offset validation** — stores `map_bm_size` at load time. Collision code validates cell offset index and list offset within blockmap lump before dereferencing. `ptr + 2 <= bm_end` checked per linedef read.
- **H1: WAD lump read zero-fill** — `wad_read_lump()` and `wad_read_lump_into()` now `memset(buf, 0, size)` before `file_read()`. Partial reads leave zeroed data instead of uninitialized memory. Warns on size mismatch.
- **H2: Sprite minimum lump size** — `sprite_render_all()` rejects sprite lumps < 8 bytes (minimum patch header size) before reading dimensions.

### Added

- `map_validate()` — post-load cross-reference validator for all map data structures
- `pcache_data_size()` — returns cached patch lump size for bounds checking
- `map_bm_size` global — blockmap lump size for runtime bounds checking
- `docs/audit/2026-04-13-security-cve-audit.md` — full CVE audit report with 15 findings

### Changed

- Binary size: 194KB (validation code adds ~3KB)
- Audit status: 3 CRITICAL + 2 HIGH → all fixed. 5 MITIGATED unchanged. 5 N/A.

## [0.23.2] - 2026-04-13

### Fixed

- **Terminal iflag bitmask** — `input_enable_raw_mode()` used wrong mask (-1043) to clear termios c_iflag bits. Corrected to -1331 which properly clears IXON(0x400), ICRNL(0x100), BRKINT(0x002), INPCK(0x010), ISTRIP(0x020). Pre-existing bug since v0.5.0, found during P(-1) hardening audit.

### Changed

- P(-1) hardening audit: all 20 source files verified clean. No malformed compound assignments, no broken unary minus, no buffer overflows, no unguarded divisions. One pre-existing termios bug found and fixed.

## [0.23.1] - 2026-04-13

### Changed

- **Cyrius 4.0.0 modernization** — ~300 line changes across 19 source files. All `i = i + 1` → `i += 1` compound assignments (`+=`, `-=`, `|=`, `&=`). All `0 - N` → `-N` negative literals. All `0 - var` → `-var` unary minus. Minimum compiler: cc3 4.0.0.
- Binary size: 191KB (slightly smaller — negative literals generate tighter code)

## [0.23.0] - 2026-04-13

### Added

- **Weapon bob** — sine-based weapon oscillation during player movement. X sways left-right, Y bounces vertically. 15-unit angular step per tick through 1024-entry sine table. Settles to center when stationary. BOB_RANGE = 4 pixels.
- **Sound effect triggers** — all PC speaker sounds now wired to gameplay: pistol/shotgun/chaingun fire, door open, item pickup, player pain, monster pain/death, rocket explosion. Sound plays through existing tone queue system.
- **Armor damage absorption** — `player_take_damage()` splits damage between armor and health. Green armor (≤100) absorbs 1/3, blue armor (>100) absorbs 1/2. Armor depletes before health takes full damage.
- **HUD current weapon ammo** — big AMMO number now shows current weapon's ammo type via `player_current_ammo()`. Fist/chainsaw display 0. Shotgun shows shells, rocket shows rockets, etc.

### Changed

- Binary size: 191KB (weapon bob + sound wiring + armor system)
- Monster damage now routes through `player_take_damage()` instead of directly modifying `player_health`

## [0.22.0] - 2026-04-13

### Added

- **Ammo consumption** — firing deducts ammo for current weapon. Pistol/chaingun use bullets (1), shotgun uses shells (1), rocket uses rockets (1), plasma uses cells (1). Fist and chainsaw are free. Empty weapon refuses to fire.
- **Hitscan shooting** — fire key traces ray from player in facing direction. Finds nearest shootable thing within weapon range (2048 units, 64 for melee). Damage: pistol 5-15, shotgun 3x(5-15), rocket 20-120, fist/chainsaw 2-20. Calls `thing_damage()` on hit → pain/death states.
- **Death and respawn** — when `player_health <= 0`: render scene with dark red tint (COLORMAP level 24), display HUD showing 0% health, wait for any key, then restart current map via `load_map()`.
- **Key cards** — `player_keys` bitmask tracks blue/yellow/red key pickups. Door specials 26/27/28 check for matching key before opening. Keys displayed in HUD status bar (STKEYS0/1/2 patches at x=239). Key pickup tracked via `things_check_pickups()`.
- **`framebuf_get_pixel()`** — read pixel from framebuffer for post-processing (death screen tint).
- **`player_try_fire()`** — ammo check + deduction, returns 1 if fire allowed.
- **`player_hitscan()`** — ray trace against all active shootable things with dot/cross product aiming.
- **`thing_radius()` accessor** — reads thing radius from runtime struct for hitscan hit detection.

### Changed

- Binary size: 190KB (gameplay mechanics + hitscan + death screen)
- Monster damage to player was already wired in v0.21.0; now has death consequence

## [0.21.0] - 2026-04-13

### Added

- **DOOM-accurate lighting** — replaced linear distance dimming with proper `scalelight[16][48]` wall lighting table and `zlight[16][128]` floor/ceiling lighting table, matching R_InitLightTables() from the DOOM source. Non-linear brightness curve based on inverse distance (scale). Fake contrast verified correct (horizontal walls lightnum--, vertical lightnum++).
- **Animated wall textures** — SLADRIP1/2/3 wall texture sequence cycles every 8 ticks (same mechanism as flat animation). Extensible to full registered/commercial texture sequences.
- **Masked midtextures** — transparent middle textures on two-sided linedefs rendered as deferred drawsegs after walls/flats, before sprites. Clipped to opening between front and back sector heights. Palette index 0 treated as transparent.
- **Intermission screen** — shown after level exit with kill%, item%, secret%, time. Uses WAD patches: WIMAP0 episode background, WINUM0-9 digits, WIPCNT percent sign, WICOLON, WITIME, WIOSTK/WIOSTI/WIOSTS labels, WIF "Finished", WIENTER "Entering". Stats tracked during gameplay via `level_add_kill/item/secret/tick_time`.
- **Level stat tracking** — `level_kills`, `level_items`, `level_secrets`, `level_time` counters. Max counts derived from thing categories and sector type 9 (secret sectors).

### Changed

- Stdlib deps expanded: vec, str, syscalls added to cyrius.toml [deps]
- Binary size: 185KB (lighting tables + masked seg system + intermission)
- Seg offset sign-extended at load time (map.cyr) for correct texture mapping

## [0.20.0] - 2026-04-13

### Changed

- **Dependency management** — added `[deps]` section to `cyrius.toml` for auto-resolve via `cyrius deps`. Stdlib modules (string, alloc, fmt, io, args, sakshi, audio) are now declared and auto-included by the build tool. Removed 24 unused vendored stdlib modules from `lib/`.
- **sakshi upgraded** — 0.5.0 to 0.9.0 (constants migrated from var to enum, expanded error handling)
- **stdlib refreshed** — string.cyr gains `atoi()`, `strstr()`; io.cyr gains file locking; all modules synced to Cyrius 3.10.1
- **Manual includes removed** — `include "lib/..."` lines in `main.cyr` replaced by auto-include from `cyrius.toml` deps declaration
- **60+ constants migrated var to enum** — ThingType, ThingState, ThingCat, ThingLayout, ThingFlags, MonsterConst, MenuScreen, SoundConst, plus removal of 5 unused FIXED_* vars. Saves ~60 gvar_toks slots.
- **Multi-return** — `render_transform_vertex()` now uses native `return (tx, ty)` with destructuring at call sites, eliminating output pointer parameters (v3.7.2 feature)
- **Switch/case blocks** — door state machine (`doors_tick`), linedef special dispatch (`doors_use`, `doors_walk_trigger`) refactored from if-chains to switch/case blocks (v3.7.4 feature). Note: case labels require literal integers, not enum identifiers.
- Minimum Cyrius version: 3.10.1 (auto-include, undefined function diagnostic)
- Binary size: 154KB (weapon/sprite animation + animated flats)

### Added

- **WAD-native menu system** — title screen (TITLEPIC fullscreen), main menu (M_DOOM logo, M_NGAME/M_OPTION/M_LOADG/M_SAVEG/M_QUITG items), skill select (M_NEWG/M_SKILL headings, M_JKILL/M_ROUGH/M_HURT/M_ULTRA/M_NMARE items), animated M_SKULL1/M_SKULL2 cursor. Replaces procedural block-letter text rendering.
- **Menu integration in game loop** — interactive mode shows title -> main menu -> skill select before game. Direct map argument (`E1M3`) skips menu. `--ppm-menu` flag renders title/menu/skill as PPM screenshots.
- **`menu_draw_lump()`** — generic WAD patch drawer for menu graphics, supports up to 128KB patches (for TITLEPIC at 68KB)
- **Weapon switching** — number keys 1-7 switch weapons (fist, pistol, shotgun, chaingun, rocket, chainsaw, plasma). Checks `player_weapons` bitmask for ownership. Fixed weapon pickup bitmask to use `1<<N` consistently.
- **Firing animation** — fire key (F) cycles weapon through sprite frames (B0, C0, D0... back to A0). 2-tick frame rate. Each weapon has correct frame count (pistol=5, shotgun=4, chaingun=2, etc.).
- **Sprite frame animation** — things cycle sprite frames based on AI state. Walk cycle (A-B), attack (C-D), pain (E-F), death (H-K), corpse (L). Sprite renderer reads frame from runtime thing struct. `sprite_find_frame()` resolves type+rotation+frame to WAD lump.
- **Runtime thing rendering** — sprite renderer now iterates runtime `things[]` array instead of raw map data, enabling animated frames and proper active/inactive state tracking.
- **Animated flats** — NUKAGE1/2/3 flat textures cycle every 8 game ticks (rotating pixel data in cache). Extensible to FWATER/BLOOD/LAVA when full WAD is available.

### Fixed

- **Sight check arithmetic shift bug** — `thing_check_sight()` used bare `>>` on signed coordinates (dx, dy, differences). Replaced with `asr()` for correct sign-preserving shifts. Previously caused incorrect line-of-sight calculations at negative coordinates.
- **Missing function `status_draw_digit`** — `menu_draw_char()` called undefined `status_draw_digit()`; replaced with existing `st_draw_small_num()`. Caught by Cyrius 3.10.0 undefined function diagnostic.

## [0.19.1] - 2026-04-11

### Added

- **audio.cyr** — WAD sound effect loading and ALSA playback via stdlib `lib/audio.cyr`
- shravan 2.0.0 pinned as git dependency for PCM codec support
- 12 DOOM sound effects preloaded from WAD (pistol, shotgun, doors, items, pain, death)
- GTK3 display bridge viewer (`scripts/x11view.py`) for desktops without /dev/fb0
- PPM fallback output in `framebuf_flip()` when no framebuffer device available
- Wolfenstein Black Book audit notes (raycasting, compiled scalers, deferred rendering)

### Fixed

- Health/armor numbers shifted 1px left for better alignment
- Weapon hand shifted 2px down for final positioning (sx=253+loff, sy=228+toff)

### Changed

- Binary size: 137KB (audio module adds 5KB)
- Minimum Cyrius version: 3.4.5 (audio stdlib required)
- Roadmap consolidated: removed duplicate v1.0.0 sections, added v0.20.0-v0.21.0 milestones

## [0.18.2] - 2026-04-10

### Fixed

- **Weapon sprite positioning** — pistol hand center-right at (sx=253+loff, sy=226+toff), matching original DOOM placement. Barrel centered, hand from lower-right.
- Iterated through DOOM psprite coordinate system using Wolfenstein Black Book insights (weapon = sprite with clipping disabled)

### Added

- 4-frame 360° spin animated GIF rendered from player start position
- `st_draw_patch_shaded()` for COLORMAP-shaded HUD elements

## [0.18.1] - 2026-04-10

### Fixed

- Ammo totals: current/max pairs with proper spacing (cur_x=276, gap=14px, row_h=6px, ammo_y=STBAR_Y+5)
- Ammo totals use softened yellow STYSNUM (shade 2 via COLORMAP, matching original DOOM warmth)
- Weapon numbers use same softened yellow treatment
- Grey STGNUM for unowned weapons in ARMS box (correct contrast vs owned yellow)
- cyrb.toml version synced to 0.18.1

### Added

- `st_draw_patch_shaded()` — draw WAD patches with COLORMAP shade level
- `st_draw_grey_num()` / `st_draw_grey_number()` — grey number rendering for unowned weapons
- Regression test suites: `regression_stack_args.tcyr` (12 tests), `regression_asr.tcyr` (15 tests)
- CI: format check (`cyrfmt`), lint check (`cyrlint`), all .tcyr test suites, pinned to Cyrius 3.3.13
- Benchmarks switched to batch mode (`bench_batch_start/stop`) for accurate sub-10ns measurements

### Changed

- cc3 compiler reference (cc2 → cc3) in bench-history.sh and CI
- Verified on Cyrius 3.3.13: 73/73 DOOM tests, 74/74 BSP tests, 100 total assertions

## [0.18.0] - 2026-04-10

### Added

- **WAD-native status bar** — STBAR background texture, STTNUM red numbers, STYSNUM yellow numbers, STTPRCNT percent sign, all loaded from WAD
- **Weapon ownership tracking** — `player_weapons` bitmask, yellow/grey arms display
- **Face background layering** — black rect behind STBAR cutout, Doomguy face on top
- **Weapon sprite at 1:1** — correct scale, positioned by patch offsets
- Wolfenstein Black Book audit started — raycasting fundamentals, compiled scalers, deferred rendering documented

### Fixed

- Status bar number positioning — AMMO and ARMOR shifted to match original DOOM layout
- ARMS display — grey (STGNUM) for unowned weapons, yellow (STYSNUM) for owned
- Row spacing for weapons 5-6-7 tightened from 12px to 10px
- Weapon pickup now sets `player_weapons` bitmask (shotgun=bit3, chaingun=bit4, etc.)
- `STBAR_BG_COLOR` removed — was undefined after status bar rewrite

### Changed

- Binary size: 129KB
- Status bar rendered from WAD graphics instead of procedural drawing
- Minimum Cyrius version: 3.3.11+ (stack args fix required)
- Benchmarks updated to batch mode (`bench_batch_start/stop`) for accurate timing
- cc3 3.3.13 verified: 73/73 DOOM tests, 74/74 BSP tests

### Performance (cc3 3.3.13, batch benchmarks)

- fixed_mul: 6ns
- asr: 5ns  
- render_frame: 3.9ms
- render+sprites: 4.8ms

### Known Issues (polish for 0.19.0)

- Weapon sprite X position slightly left of original DOOM
- Ammo totals right-side numbers could be better aligned
- Key indicators not yet drawn
- Weapon switching (1-7 keys) not implemented

## [0.17.2] - 2026-04-09

### Changed
- Cyrius toolchain pinned to v3.2.5 (cc3 compiler, minimum version)

## [0.17.1] - 2026-04-09

### Changed

- BSP dependency bumped to 0.7.0 (asr() fix for logical shift bug)

## [0.17.0] - 2026-04-09

### Added

- **level.cyr** — Level progression system (episode/map tracking, advance, secret exits)
- Exit switch support: linedef special 11 (normal exit), 51 (secret exit)
- Walk-over exit lines: special 52 (normal), 124 (secret)
- Level advance logic: E1M1→E1M2→...→E1M8, E1M3→E1M9 (secret), E1M9→E1M4 (return)
- `load_map()` function — reload all map state (geometry, things, doors, player) for transitions
- Map name from command line: `./doom DOOM1.WAD E1M3` loads E1M3 directly
- Verified all 9 maps of Episode 1 load and render (E1M1-E1M9)

### Changed

- Binary size: 129KB
- main.cyr restructured with `load_map()` for level transitions
- Game loop checks `next_level_flag` each tick for seamless map changes
- Source: 19 .cyr files

## [0.16.0] - 2026-04-09

### Fixed

- **Weapon sprite position** — proper offset math using signed patch offsets
- **HUD layout** — repositioned all elements to match original DOOM proportions (ammo, health, arms, face, armor, keys, totals)
- **Status bar background** — dark grey (palette 104) instead of black
- **Doomguy face** — loads actual STFST sprite from WAD with health-based frame selection (5 damage levels + dead)

### Added

- Walk-over linedef triggers — doors/lifts activate when player crosses trigger lines
- Tagged sector support — switches and triggers find sectors by tag number
- Additional door specials: 63, 29, 90
- Additional lift specials: 10, 21, 121, 122
- Switch-to-tagged-sector specials: 103, 23, 102, 38, 70, 71
- Walk-over types: 2, 4, 88, 10, 38, 70

### Changed

- Binary size: 127KB
- Source: 18 .cyr files
- doors.cyr expanded with tagged sectors and walk triggers

## [0.15.0] - 2026-04-09

### Added

- **automap.cyr** — 2D overhead map display (TAB toggle)
- Bresenham line drawing for all linedefs
- Color-coded lines: red (solid walls), yellow (height changes), grey (portals)
- Blue dots for things (monsters, items, decorations)
- Green player arrow showing position and facing direction
- Map centered on player, auto-scrolls with movement
- TAB input flag added to input bitmask (INP_TAB = 512)
- `--ppm` mode now outputs both 3D view and automap screenshots

### Changed

- Binary size: 123KB
- Source: 17 .cyr files
- Game loop: TAB toggles between 3D view and automap

## [0.14.0] - 2026-04-09

### Added

- **doors.cyr** — Door and lift sector animation system
- Door open/wait/close cycle: ceiling raises to highest neighbor, waits 3s, closes
- Lift lower/wait/raise cycle: floor drops to lowest neighbor, waits 3s, raises
- "Use" action (E/Space): ray cast from player to find nearest special linedef
- Supports door specials: 1 (normal), 26-28 (keyed), 31 (open stay), 117 (fast)
- Supports lift specials: 62 (lower wait raise), 88 (fast)
- Neighbor sector height search for door targets (`find_highest_neighbor_ceil`, `find_lowest_neighbor_floor`)
- 32-slot thinker array for concurrent door/lift animations
- Sector heights modified in-place — renderer automatically reflects changes

### Changed

- Binary size: 119KB
- Game loop: input → use → doors → player → things → sound → render → sprites → weapon → HUD → flip

## [0.13.0] - 2026-04-09

### Added

- **Weapon sprite overlay** — pistol rendered as screen overlay above status bar, COLORMAP shaded
- `render_set_weapon()` / `render_draw_weapon()` — weapon sprite system with dedicated patch buffer
- **BLOCKMAP collision** — loads WAD BLOCKMAP lump for O(1) cell-based collision detection
- `player_check_linedef()` — extracted single-linedef collision check for blockmap + brute-force paths
- `texture_animate()` stub — animation framework for cycling flat/texture names
- `asr()` applied to collision math — fixed signed shift bugs in point-to-line distance

### Changed

- Binary size: 113KB
- Collision detection: BLOCKMAP path when available, brute-force fallback
- Player collision uses `asr()` for all signed shifts in distance calculations

## [0.12.0] - 2026-04-09

### Fixed (Audit Quick Wins)

- **Fake contrast** — reversed to match original DOOM: E-W walls (same Y) darkened, N-S walls (same X) brightened. ±1 COLORMAP level = ±16 light units
- **Light level scale** — changed from `>> 3` to `>> 4` for correct 16 distinct sector light levels (×2 for even colormap indexing, matching DOOM quirk)
- **Texture pegging** — `ML_DONTPEGTOP` and `ML_DONTPEGBOTTOM` flags now applied to upper/lower texture Y offsets. Door frames and window sills align correctly
- **Sprite rotation** — sprites now select rotation 1-8 based on angle between viewer and thing. Monsters show correct facing direction (front, side, back)

### Added

- `sprite_find_rotated()` — rotation-aware sprite lump lookup
- `sprite_calc_rotation()` — computes rotation from viewer-thing angle delta
- `docs/audit.md` — full gap analysis vs original DOOM engine (from doomwiki.org + Sanglard analysis)

### Changed

- Binary size: 109KB

## [0.11.0] - 2026-04-08

### Added

- **tests/doom.tcyr** — 73 assertions across 13 test groups (asr, fixed-point, trig, WAD, map, textures, COLORMAP, rendering)
- **benches/doom.bcyr** — 14 benchmarks (fixed_mul through render_frame+sprites)
- **scripts/bench-history.sh** — CSV benchmark tracking with version/date/binary size
- **docs/architecture/overview.md** — full module dependency graph, memory layout, performance table, game loop diagram
- **docs/sources.md** — DOOM Black Book chapter references, WAD spec, mathematical sources, internal vidya refs
- **CLAUDE.md** rewritten — ecosystem-aligned with P(-1) research steps, references section, key principles, build commands

### Performance (baseline recorded)

- render_frame: 2.2ms avg
- render_frame+sprites: 2.9ms avg (10x headroom vs 28ms budget)
- fixed_mul: 410ns
- pcache_get (hit): 462ns
- texture_get_column: 1μs

## [0.10.0] - 2026-04-08

### Added

- **All 13 modules compiled** — things, status, menu, sound now included in game loop
- Span-based floor/ceiling rendering (row-by-row with horizontal stepping)
- Deferred visplane system: walls collect span bounds, flats drawn in second pass
- **Patch data cache** — 8-slot LRU cache eliminates WAD I/O during rendering (**200x speedup**)
- **Sky texture rendering** — F_SKY1 ceiling replaced with SKY1 wall texture mapped to view angle
- Dead code elimination: removed 40 unused functions
- Switched to `lib/io.cyr` (no more inline file_* functions)
- Full game loop: input → AI → sound → render → sprites → HUD → flip
- Things: 29 monsters, 67 items, 38 decorations
- Status bar HUD, sound system, menu system

### Changed

- Binary size: 107KB (down from 108KB despite adding features — dead code removal)
- Frame render time: **22ms** (was ~5 seconds — patch cache + span optimization)
- Runs at full 35Hz framerate within tick budget (28ms)
- Requires cyrius 2.4.0+ (expanded gvar_toks to 1024)
- Compile time: 79ms
- Source: 3,905 lines across 16 files

### Fixed

- `tick_count` → `tick_get_count()` (packed state)
- Menu input refs → function accessors
- Cleaned up main.cyr (removed debug prints, tightened structure)

## [0.9.0] - 2026-04-08

### Added

- **sprite.cyr** — Thing sprite rendering (monsters, items, decorations)
- Sprite lookup table: 35 DoomEd thing types mapped to sprite prefixes
- Back-to-front distance sorting (insertion sort) for correct overdraw
- Sprite scaling by distance using projection math
- Sprite clipping to wall column boundaries (clip_top/clip_bottom)
- BSP sector lookup for per-sprite floor height and light level
- Dedicated 16KB sprite patch buffer (avoids shared WAD lump buffer corruption)
- COLORMAP shading on sprites with distance falloff

### Fixed

- Shared WAD lump buffer crash: sprites calling `wad_read_lump` in a loop overwrote previous patch data — now uses `wad_read_lump_into` with dedicated buffer
- Removed `elif` usage (not supported by all cc2 versions) — replaced with data-driven lookup table

### Changed

- Binary size: 81KB (was 74KB — sprite system adds 7KB)
- E1M1 renders with zombiemen, barrels, items, armor bonuses visible

## [0.8.0] - 2026-04-08

### Added

- Floor/ceiling flat texture rendering with perspective mapping
- Flat textures loaded from WAD (F_START..F_END, 64x64 raw palette indices)
- Per-pixel world coordinate calculation for floor/ceiling spans
- Sector floor/ceiling texture name accessors (`map_sector_floor_tex`, `map_sector_ceil_tex`)
- Flat texture lookup via name hash (`flat_find`, `flat_get_pixel`)
- Distance-based light dimming on floor/ceiling planes

### Changed

- Binary size: 74KB (was 70KB — floor/ceiling rendering adds 4KB)
- Floor/ceiling now show actual DOOM flat textures (FLOOR4_8, etc.) instead of solid colors
- Rendering time increased (per-pixel flat calculation) but produces correct perspective

## [0.7.0] - 2026-04-08

### Added

- **texture.cyr** — Wall texture loading from WAD (PNAMES, TEXTURE1, patch compositing)
- Patch-based column rendering: reads DOOM's column-major patch format (posts with transparency)
- Texture name lookup via hash table for fast sidedef → texture resolution
- Flat (floor/ceiling) texture cache: loads 64x64 raw images from F_START..F_END
- DOOM COLORMAP integration: 34-level light-to-palette mapping from WAD
- Distance-based COLORMAP shading: walls darken with depth using id Software's light curves
- Directional wall dimming: N/S walls dimmed by 2 COLORMAP levels (matches original DOOM)
- Per-sector ceiling colors: blue for tall/outdoor sectors, dark grey for indoor
- Per-sector floor colors: beige/brown from palette ramp
- `--ppm` screenshot mode for headless rendering and testing
- `render_load_colormap()` and `render_shade()` for proper palette-based lighting
- `texture_get_column()` composites multiple patches into a single texture column
- `render_draw_tex_column()` draws textured wall columns with COLORMAP shading

### Fixed

- **Critical: Cyrius >> is logical, not arithmetic** — all fixed-point math with negative values was broken (black screen). Added `asr()` helper for sign-preserving right shift
- Palette double-allocation: `framebuf_set_palette` and `framebuf_init` both allocated palette buffer, second one overwrote loaded data with zeros
- `sign_extend_16` rewritten to use subtraction (`lo - 0x10000`) instead of OR with bitmask

### Changed

- Binary size: 70KB (was 63KB — texture system adds 7KB)
- Wall rendering: textured columns (STARTAN3, LITE3, DOOR3, etc.) instead of solid colors
- E1M1 renders with actual DOOM wall textures, COLORMAP lighting, distance shading

## [0.6.0] - 2026-04-08

### Added

- Sakshi 0.7.0 integration — structured logging with timestamps to stderr
- All startup, WAD loading, map loading, and error paths emit `[INFO]`/`[WARN]`/`[ERROR]` traces
- `--ppm` flag for headless screenshot mode (`./doom DOOM1.WAD --ppm`)
- Debug-level tracing for subsystem init (tables, palette, player)
- cc2 gvar_toks limit confirmed at 256 (not 64 as previously assumed)

### Changed

- Error messages use `sakshi_error()` instead of raw `file_write(2, ...)`
- Binary size: 62KB (was 57KB — sakshi adds ~5KB)
- Log output format: `[timestamp_ns] [LEVEL] message`

## [0.5.2] - 2026-04-08

### Fixed

- Segfault on startup: `framebuf_set_palette()` called before palette buffer allocated — added lazy init guard
- Verified against real DOOM1.WAD shareware (1264 lumps, E1M1 loads correctly)

### Added

- `scripts/get-wad.sh` — downloads DOOM1.WAD shareware from nneonneo/universal-doom
- `scripts/run.sh` — one-shot download + build + run
- `fuzz/fuzz_wad.cyr` — WAD parser fuzz harness (1000 random inputs, zero crashes)
- `fuzz/fuzz_fixed.cyr` — fixed-point math fuzz harness (50000 iterations, extreme values)
- CI smoke test with real DOOM1.WAD
- E1M1 stats: 467 vertices, 475 linedefs, 648 sidedefs, 85 sectors, 732 segs, 237 subsectors, 236 nodes, 138 things

## [0.5.1] - 2026-04-08

### Changed

- CI uses `cyrb build` via install script instead of raw cc2
- Added `cyrb.toml` with BSP as git dependency (`tag = "0.5.1"`)
- Release workflow bootstraps Cyrius from upstream install script

## [0.5.0] - 2026-04-08

### Added

- **fixed.cyr** — 16.16 fixed-point math (mul, div, abs, clamp, lerp, approx_dist)
- **tables.cyr** — 1024-entry sine table via Bhaskara I approximation, atan2, trig wrappers
- **wad.cyr** — WAD file parser (IWAD/PWAD magic, directory, lump read, name lookup)
- **framebuf.cyr** — 320x200 palette-indexed framebuffer, vline/hline, palette-to-BGRA flip, PPM output
- **map.cyr** — Full geometry loader: vertices, linedefs, sidedefs, sectors, segs, subsectors, BSP nodes, things
- **render.cyr** — BSP traversal, view transform, near-plane clipping, column-by-column wall rendering, two-sided portals, per-column occlusion
- **input.cyr** — Terminal raw mode, ESC sequence decoder, WASD + arrow keys, bitmask action flags
- **player.cyr** — Movement (walk/run/strafe), wall sliding collision, step height + ceiling clearance checks, sector tracking
- **tick.cyr** — 35Hz game timer via clock_gettime + nanosleep
- **things.cyr** — Monster/item/decoration types, AI state machine (spawn/see/chase/attack/pain/die), item pickups, damage
- **status.cyr** — HUD with 3x5 bitmap font, health/armor/ammo display, face, weapon slots, keys
- **menu.cyr** — Title screen, main menu, skill select, cursor navigation
- **sound.cyr** — PC speaker via ioctl (KIOCSOUND), tone queue, predefined effects
- **main.cyr** — Full game loop: menu → load → input → AI → render → HUD → flip → wait
- All data arrays heap-allocated to stay under cc2's 256KB output limit
- Constants packed into enums to stay within 64 gvar_toks limit
- Reads real DOOM1.WAD shareware files
- All math is 16.16 fixed-point, no FPU

### Build

- Compiles with cc2 2.2.2+ (requires improved error reporting)
- 9-module game loop binary: **56KB** (core without things/status/menu/sound: 45KB)
- 3,094 lines of Cyrius across 14 source files
- 64 initialized globals (at cc2 limit)

### Known Limitations

- things.cyr, status.cyr, menu.cyr, sound.cyr not yet included in game loop (need >64 gvar_toks)
- No texture mapping (solid colors from sector light level)
- No sprite rendering
- No automap
- Binary size 56KB exceeds 50KB target by 6KB

## [0.1.0] - 2026-04-08

### Added

- Project scaffolded
- Architecture defined: 14 modules, 30-50KB target
- Clean-room implementation plan from DOOM specs
