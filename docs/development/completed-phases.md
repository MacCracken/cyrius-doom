# cyrius-doom — Completed Phases

> Chronological record of shipped versions. CHANGELOG holds the per-version detail; this file is the one-line index. Sister to [`state.md`](state.md) (live state) and [`roadmap.md`](roadmap.md) (forward).

Each entry: one row, headline only. For the full changelog see [`CHANGELOG.md`](../../CHANGELOG.md).

## v0.33.x — Desktop rendering (native Wayland window) + field patch

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.33.4 | 2026-07-12 | **Security + safety quick-wins — the first patch off the [2026-07-12 consolidated audit](../audit/2026-07-12-consolidated-audit.md).** Six small fixes, no render/gameplay-logic change. **M-1** (HIGH): Wayland window crash when dragged below 320×200 — the fixed 320×200 blit overran a smaller shm buffer → SIGSEGV; now `win__clamp_size` floors the adopted size + `xdg_toplevel.set_min_size`. **P-6**: compositor-dimension integer-overflow cap (16384) + a `shm_create` overflow guard. **M-2**: unbounded `WAYLAND_DISPLAY`/`XDG_RUNTIME_DIR` copy → stack smash, now bounded to the 107-char `sun_path` (fails closed → fb0). **R-2**: dead death-face — the 8-char "STFDEAD0" in an `alloc(8)` scratch had no NUL, so `strlen` over-read → every lump rejected → blank face; now `alloc(9)`+NUL (same for STYSNUM). **R-6/M-3/M-4**: TEXTURE1/STBAR/STARMS lump allocs null-guarded + capped (malformed-WAD boot DoS). **G-7**: sparse `doors_walk_trigger`/`things_check_pickups` switches → if/else (defensive vs the cycc return-smash class). Tests **155/227** (+6 WAD-free clamp, +3 WAD-gated R-2); binary 439,192→439,208 B (agnos 425,640→425,608 B); AGNOS QEMU doom-smoke + in-game + aethersafha-present PASS. Pin unchanged 6.4.55. |
| v0.33.3 | 2026-07-12 | **Audit round — toolchain/dep refresh + setu present-leak fix + roadmap reorg.** Toolchain 6.4.43→**6.4.55**, vani vendor 1.1.0→**1.1.1** (header-only), setu vendor 0.5.0→**0.5.1**; lock 36/0. Ran a five-agent audit over the whole tree and **consolidated all seven prior audit docs** into [`2026-07-12-consolidated-audit.md`](../audit/2026-07-12-consolidated-audit.md). Fixed a live HIGH (**P-1**): the setu present path created a new kernel shm buffer every frame and never freed it → agnos exhausted its 16 shm slots in <0.5 s of play (system-wide present DoS) → **patched upstream in setu 0.5.1** (cache/reuse + close), re-vendored + QEMU-verified. Plus doom-side setu input hardening (focus-loss latch clear, stream reassembly, persistent poll scratch). Tests 149/218 unchanged; binary 426,496→439,192 B (agnos 395,968→425,640 B). Codegen gate corrected (perf/regalloc arc is cyrius v6.5.x, not v6.4.x). |
| v0.33.2 | 2026-07-10 | **DOOM on the sovereign desktop — a `PM_SETU` display + input backend.** doom runs as a window on the aethersafha compositor over the setu display protocol on AGNOS (the OS-agnostic twin of the Wayland window backend: agnos→setu, Linux→Wayland). New `src/setu_present.cyr` (setu client shell) + `vendor/setu.cyr` (setu 0.5.0); a `PM_SETU` runtime branch threaded through `framebuf_init`/`framebuf_flip`/`framebuf_shutdown`/`input_poll`. Reuses doom's existing `fb_buf` (320×200 XRGB8888/BGRA) — no new rasterizer — presented over setu's shared-buffer path (sidesteps the 2 KB loopback-TCP window). agnos defaults to `PM_SETU`; `framebuf_init` auto-downgrades to `PM_FB0` (fullscreen blit#39) when no compositor listens; `--fb0` forces fullscreen. **Held-key make/break** via setu 0.5.0 FULL key events (`SETU_SURF_FULL_KEYS`) — `input_poll_setu` tracks persistent held state (hold W to keep moving). Added `net`/`result`/`assert` to the stdlib. **QEMU-validated**: `aethersafha-doom-smoke.sh` (doom composited as a window next to crab) + `aethersafha-doom-input-smoke.sh` (balanced 10 press / 10 release over setu). *(state.md captured this release retroactively at the 0.33.3 cut — 0.33.2 shipped without a state refresh.)* |
| v0.33.1 | 2026-07-10 | **Field-report combat/sky/movement patch** — the four bugs from the first real 0.33.0 desktop play session, each reproduced headlessly against real E1M1 geometry before fixing. **Sky**: V drawn 1:1 (was squeezed 128→100 rows — mountains ~28% high) + U tan-distributed per column via `x_to_viewangle` (was linear — the sky slid against the walls on turns). **Aim**: `fixed_atan2` diamond→minimax quadratic (~3.9° mid-octant error → ≤0.25°; exact-aim rays whiffed 20u targets past ~350u). **Movement**: drop-off wedge cured (player-only same-side escape rule — the post-drop z-snap inside a ledge line's radius used to block all 8 directions); monster moves step-checked against the mover's OWN floor (was player_z — chases froze near ledges) + vanilla MF_DROPOFF pin. **Aliveness**: noise alert (P_NoiseAlert sector flood; closed doors stop sound) + monster ranged attacks (zombie/sergeant hitscan, imp/caco BAL1/BAL2 fireballs, owner-immune, distance-rolled arm + cooldown). Toolchain 6.4.30→**6.4.43**; vani vendor 0.9.9→**1.0.0** (surface-identical). Tests **149/218** (+16/+25); binary 426,496 B (agnos 395,968 B); `render_frame` 2.349 ms; **AGNOS QEMU doom-smoke + in-game sendkey harness PASS on the final binary**. |
| v0.33.0 | 2026-07-09 | **Native Wayland window backend — DOOM as a real, resizable desktop window.** Sovereign wl protocol over the AF_UNIX socket via syscalls (no libwayland, no new deps), lifted+adapted from [puka](https://github.com/MacCracken/puka). Four `src/platform/` files (`wayland/{wire,client,shm}.cyr` + `window.cyr`, all `#ifndef CYRIUS_TARGET_AGNOS`) behind a runtime `present_mode`; `framebuf_flip`/`input_poll` branch to Wayland, fb0/AGNOS/`--ppm` byte-identical. Double-buffered ping-pong present (no tearing), full keyboard (evdev→key_state, arrows-turn, poll(7)-gated), xdg_shell lifecycle + ping/pong + drag-resize + close, wire-parser security hardening ([audit](../audit/2026-07-09-wayland-backend.md)). Selection via `--wayland`/`--fb0`/`--wayland-probe`/`WAYLAND_DISPLAY`. Built through 4 adversarially-reviewed bites (reviews caught+fixed a `var x[N]`-is-BYTES stack overflow, a menu lock, a resize-OOM crash). **25 modules** now. Tests **133/193** (+15); binary 418,224 B (agnos 387,592 B, QEMU PASS); `render_frame` 2.469 ms (present off the render path). Window user-verified on Hyprland. Design: [proposal](../proposals/wayland-backend.md). |

## v0.32.x — The July render-consistency mega-cut + patch

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.32.1 | 2026-07-08 | **Patch — `--audio-test` / `--music-test` cleanly separated.** `--audio-test` was also playing music (`load_map()` runs `music_start()`, `music_volume` defaults to 8, so `D_E1M1` mixed into the SFX test's every `audio_tick`): it now `music_stop()`s first (SFX-only), and `--music-test` `music_start()`s to re-arm from bar 1 (music-only). Audio-path-only — render gates byte-identical. +3 WAD-free regression asserts (a playing voice renders sound; `music_stop()` → pure silence). AGNOS QEMU smoke PASS on the final 0.32.1 binary. Tests **118/178**; binary 392,304 B (agnos 387,528 B). |
| v0.32.0 | 2026-07-08 | **Render-consistency audit (Bites A–D) + both render keystones + vani vendoring + toolchain 6.4.30.** One-day arc off the [2026-07-08 audit](../audit/2026-07-08-render-consistency.md) (21 findings, staged-viewpoint PPM evidence). **A**: 12 invisible thing types (63 spectres!), `fixed_atan2` octant compression, shredded magnified sprites, sky-to-sky walls, closed-door see-through seam, masked order. **B (0.28.6)**: drawseg depth clipping — near sprites no longer deleted by far portals, sprite x-ray gone, grate/sprite depth merge; +RC-W9 screen-edge endpoint re-anchor (the E1M7 stripe band). **0.28.5**: global `view_z` + real visplane pool — **world elevation renders**, flat bleed gone, `render_frame` **−24%** (2.35 ms). **C**: door-entombment reversal, trigger segment-spans, real use-ray, closed-portal sight/hitscan, missile spawn check + splash LOS, alloc-leak guards. **D**: the see-through gun (palette-0 ≠ transparent in post pixels), sky V screen-anchoring, flat V parity, projectile height/fullbright, 7 LOW leftovers. **Release cleanup**: RC-G6 AGNOS menu edge-latch, F-R6 fully retired (texture fill-mask — true grate transparency), L8-lite monster solidity; **AGNOS QEMU smoke PASS on the final binary** (v0.32.0 banner + WAD + 240-color TITLEPIC). vani-core vendored (`vendor/vani-core.cyr` 0.9.9, lock 100→34); pin 6.4.2→**6.4.30**. Tests **115/175** (+35 regression asserts this cut); binary 392,280 B (agnos 387,504 B). |

## v0.31.x — Playability, fidelity, sound-on-AGNOS, music

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.31.0–v0.31.4 | 2026-07-04 | **Sound on AGNOS (`sys_snd_*`, 0.31.0) → audio iron-validation (0.31.1) → July Fable audit playability pass (0.31.2: 13 fixes — melee clobber, door thinker lifecycle, wall-phasing, skill filter, texture-height clamp) → vanilla-fidelity gameplay + sky-pan (0.31.3) → MUS music wired in (0.31.4: parser + 140 Hz sequencer + 16-voice synth into the shared mixer).** Toolchain 6.3.5→6.4.2 across the band (lock 37→100). See CHANGELOG for the per-version detail. |

## v0.30.x — Shooting overhaul + player-feedback + toolchain rollups

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.30.4 | 2026-06-29 | **Toolchain + dependency bump.** cyrius pin 6.2.44→6.3.5 (closes the launcher drift — cycc already ran 6.3.5), vani 0.9.4→0.9.5, bsp 1.1.3→1.1.5; `cyrius.lock` regenerated (37/0, transitive yukti/patra/sakshi unmoved). No application logic changes (only the version banner). Picks up cyrius **CVE-32** resolver path-traversal fix (6.2.45, in-band). The 6.2.44→6.3.5 band carries 6.3.5 CO-01 (forward-call ABI fix) + 6.3.0 (per-var `_base` indirection), both re-verified green on Linux. Binary 612,672→613,720 B (+1,048 codegen growth-tax); `render_frame` 2.971 ms (variance); 63/63 + 101/101; fuzz 50000/1000/2000 clean. |
| v0.30.3 | 2026-06-26 | **Sprite draw-loop OOB read → ring-3 #PF on AGNOS during sustained close-range combat.** A point-blank muzzle-flash/projectile sprite blew up `sprite_w`, so the column draw loop read `clip_top`/`clip_bottom` ~734 KB off the end (clean #PF on AGNOS guard pages; silent heap corruption on stock HW). The in-source bounds guards were dead no-ops under the old 6.1.37 `continue`-in-large-fn miscompile. Fixed by range-clamping the draw loop so `scr_x ∈ [0, SCREEN_WIDTH)` by construction. Toolchain pin 6.1.37→6.2.44. |
| v0.30.2 | 2026-06-14 | **Player-feedback + controls patch.** Combat coredump fixed (`thing_animate` `switch`→`if/else`, cycc return-smash); dead main-menu Options item → navigable `MENU_OPTIONS` screen; fist thumb raised to clear the status bar; controls reworked — AGNOS gains DOOM-faithful Ctrl-fire + Shift-to-turn, Linux keeps the Caps-Lock-immune arrows-turn/A-D-strafe/F-fire scheme. |
| v0.30.1 | 2026-06-13 | **Player-feedback rendering patch.** Weapon psprite hotspot fix (`1−loff/16−toff`, was pistol-only by coincidence); muzzle-flash overlay (`ps_flash` PISF/SHTF/CHGF/MISF fullbright); wall texture-U mirror on turn corrected; enemies resolve combined-rotation lumps (`TROOA2A8`) + flip so they face correctly; walk-strobe gated to ~4-tick. |
| v0.30.0 | 2026-06-13 | **Shooting-mechanics overhaul.** Multi-agent review of input→hitscan→damage→psprite (27 findings). Fixed unbounded fire cadence, shoot-through-walls (LOS), pain-lock, corpse re-kill, psprite leak. Fidelity: rocket→projectile+splash, barrel chain-explosions, shotgun 7-pellet spread, per-weapon refire cadence, `p_random` PRNG. Tests 37→63 WAD-free / 75→101 full + `fuzz_weapon` 20k. |

## v0.29.x — AGNOS scaling + world-tick correctness + flat rendering

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.29.0 | 2026-06-11 | **AGNOS: the kernel scales.** `framebuf_blit_agnos` stops expanding scale² pixels in ring 3 — it palette-converts the raw 320×200 frame into a FIXED 256 KB 32bpp buffer and passes the integer scale to `blit`#39 a4[39:32] (agnos 1.44.20). Ring 3 writes 64 K px/frame instead of scale²·64 K; the old scale-3 heap cap is gone (panel's natural integer scale, e.g. 7 on 2560×1440, capped at the kernel's 16). Ship with agnos ≥ 1.44.20 (older kernels ignore the scale bits — unscaled centred, degraded but harmless). |
| v0.29.1 | 2026-06-11 | **World tick froze without input — two platform-specific causes, both reproduced (not static-read).** Linux: `read(stdin)` blocked the loop for any non-tty stdin (pipe/FIFO/redirect/x11view bridge/failed `ioctl`) where `VMIN=0` is ignored — `input_enable_raw_mode` now also forces `O_NONBLOCK` on fd 0 via `fcntl`, restored on exit. AGNOS: `framebuf_init` sized `fb_buf` via `alloc(SCREEN_WIDTH*SCREEN_HEIGHT*4)`, a 3-operand chained constant multiply cycc's `--agnos` backend folded to 800 (not 256000) → a 255 KB/frame heap overflow that stomped `colormap`/`zlight`/`flat_cache` → frame-2 `render_flat_spans` page fault. Worked around with 2-operand forms (`SCREEN_SIZE*4`, split light-table allocs). |
| v0.29.2 | 2026-06-11 | **Toolchain → cycc 6.1.37 + world-tick aliveness.** 6.1.37 fixes the `--agnos` 3-op-multiply miscompile (retires known-issue #3), so the 0.29.1 2-operand workarounds in `framebuf.cyr` + `render.cyr` revert to the clean chained form — **verified on the real `--agnos` binary in QEMU** (serial probe: fb_buf=256000, scalelight=6144, zlight=16384; `doom-smoke.sh` PASS). Aliveness (the loop already ticked at 35 Hz post-0.29.1; the *world* just wasn't visibly changing): removed the 1000-unit `MONSTER_SIGHT_RANGE` cap — monsters now wake on line-of-sight like real DOOM (the cap kept all but the nearest 936-unit monster asleep at the E1M1 spawn) — and idle monsters now animate their two standing frames (A↔B, ~8-tick, staggered by index) instead of a static frame. Reproduced via a pty harness driving the real-tty input path. `cyrius.lock` regenerated (37 entries). Binary 601,568 B (agnos 580,592 B); `render_frame` 2.557 ms; 37/37 + 73/73. |
| v0.29.3 | 2026-06-12 | **Flat rendering fixed — floors/ceilings finally textured.** `render_flat_spans` computed per-row plane distance as `41/dy`, missing the ×`PROJ_DIST` factor (true: `41·160/dy`, DOOM's `planeheight·yslope[y]`); 160× too small collapsed the per-pixel world step to ~0 — **one texel smeared per row** (the user-reported "untextured gray floors", photo'd on AGNOS hardware, identical on Linux) — and pinned zlight ~0 (flats fullbright, no distance fade). Root cause isolated by pixel-probing the PPM against PLAYPAL/COLORMAP (the "gray" decoded to exactly FLOOR4_8's five most-common texels). Same cut: sky rows no longer registered into `vp_ceil` (F_SKY1 is a real flat — the span pass overdrew the wall-pass sky once flats textured), fake contrast no longer leaks into plane lights (DOOM: walls only), per-row `vp_ceil_h` so ceiling spans invert the same `ceil−floor−41` height the wall pass projected (was constant 41 → ~2× mis-scale in 128-tall rooms). Multi-agent review: units/overflow + DOOM-fidelity + refutation (failed on all vectors — span mapping is the exact inverse of the wall projection) + 2 pipeline sweeps + E1M1–E1M9 visual verification (16–33 distinct colors/floor row vs 1–3 pre-fix) + AGNOS QEMU in-game screendump (textured floors with depth lighting; serial probe = Linux fold). Review findings → roadmap (visplane-slot evidence; new unslotted wall-path bug table: closed-door black holes E1M3/4/7, E1M9 parallel-wall drop, SLADRIP no-op, FLAT_MAX, bsp `asr()` trunc). Binary 601,936 B (agnos 580,960 B); `render_frame` 2.451 ms; 37/37 + 73/73. Built under cycc 6.2.2 (launcher ignores the 6.1.37 pin — resolves via CYRIUS_HOME/PATH). |

## v0.28.x — Graphics arc (in flight, 0.28.0 shipped)

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.28.0 | 2026-06-07 | Graphics review/hardening/audit/performance — the new 0.28.x anchor. Multi-agent render-path audit (67 raw → 27 canonical → 20 adversarially verified; 8 shipped, rest re-slotted across 0.28.1–.7). **Hardening**: propagated the v0.24.0 C2 patch-bounds checks from `texture_get_column` to the three other patch decoders — weapon `render_draw_weapon` (F01), `sprite_render_all` (F02), the shared HUD/menu/title `st_draw_patch_shaded` (F03, lump size threaded from every call site in status + menu) — and to the `TEXTURE1` parser (F19); fixed a genuine heap **OOB write** in the visplane row loops where `ceil_screen`/`floor_screen` were only relatively clamped (F17), which also corrected a real 11-px corruption block on E1M1 (x=234–237, y=107–109). **Perf**: inlined the flat fetch + hoisted the COLORMAP row in `render_flat_spans` (F11) — `render_frame` ~2.10 → ~1.78 ms (~15%, same-toolchain), `texture_get_column` unchanged; cached the weapon patch instead of re-reading the lump every frame (F14). **Hygiene**: deleted dead `render_flat_span` (F16). Toolchain pin 6.0.29 → 6.0.83. Binary 590,824 → 592,456 B (+1,632 B bounds checks, net of the dead-fn delete). 37/37 WAD-free + 73/73 full; fuzz 1k/50k clean; 11/12 reference frames byte-identical (E1M1 game = the intended F17 fix). Audit: `docs/audit/2026-06-07-v0.28-graphics-hardening.md`. |
| v0.28.1 | 2026-06-08 | **AGNOS target support** — first port of the engine to the sovereign OS (the "agnsh launches DOOM" arc). OS interactions branched under `CYRIUS_TARGET_AGNOS`: inlined agnos syscall numbers (which collide with Linux — e.g. agnos `0`=exit), portable timing via `uptime_ms`/`sleep_ms`, framebuffer geometry via `fbinfo`#38 + `blit`#39, WAD memory-load (no `lseek`), exit/input/sound paths. Linux build byte-identical; `--agnos` builds + runs. 37/37 + 73/73. |
| v0.28.2 | 2026-06-08 | **DOOM renders on AGNOS.** The 584 KB ELF exec's from disk in ring 3, slurps the 4.2 MB `DOOM1.WAD` into memory, parses it, builds the palette, and blits a 240-colour frame to the hardware framebuffer via `fbinfo`#38 / `blit`#39 — `agnsh` launches a real userland application. A warm-up mmap workaround for a kernel first-syscall-return fault was documented in-place (later removed when the kernel root cause — user stack in the identity-mapped range — was fixed). Unblocked by two AGNOS kernel fixes (PMM → 24 MB, physical-page zeroing ≥ 16 MB). Smoke: `agnos/scripts/doom-smoke.sh`. |
| v0.28.3 | 2026-06-09 | **AGNOS keyboard input — DOOM playable past the title screen.** `input_poll`'s agnos branch drains the kernel's new `kbscan`#42 (a non-blocking raw Set-1 scancode poll), decodes make/break, and keeps `key_state` as persistent held state (closer to real DOOM than the Linux press-then-clear path). Mapping: WASD + arrows + space/E/F/R/Tab/1–7/Q/Esc. Validated in QEMU (`agnos/scripts/doom-input-test.py`, USB-xHCI + HMP sendkey). Requires an AGNOS kernel with `kbscan`#42. |
| v0.28.4 | 2026-06-10 | Gameplay correctness pass (surfaced once the engine was driven interactively rather than via still `--ppm`). (1) **Angle-convention unification** — `render_transform_vertex` + both `sprite.cyr` transforms computed view depth as `dy·cos−dx·sin` (forward = north@BAM0) while movement/hitscan/`render_flat_spans`/map thing-angles use `(cos,sin)` (east@BAM0); walls+sprites rotated 90° off movement and disagreed with floors. Unified to `ty=dx·cos+dy·sin`, `tx=dx·sin−dy·cos` (lateral verified against the floor-span screen-right axis `(sin,−cos)` so left/right isn't mirrored). (2) **One-sided-wall collision** — `player_check_linedef` early-returned passable for any line lacking both `ML_BLOCKING` and `ML_TWOSIDED`, i.e. every ordinary one-sided wall; now solid at the distance test. (3) **Linux `termios` VMIN** — raw-mode set `c_cc` at offsets 22/21 (assumed base 16) but the kernel struct has a `c_line` byte at 16 so the base is 17; VMIN (23) stayed 1 → blocking `read(stdin)` → the 35 Hz loop froze between keystrokes (`things_tick`/`doors_tick` only advanced on input). Corrected to 23/22. (4) **Perspective-correct wall + masked-seg depth** (interpolate scale `PROJ_DIST/z`, not `z`, across columns) + texture-U — **F22**, pulled forward from 0.29.x. (5) **sakshi log routing** for the `map:`/stats/`things:` boot lines. Toolchain pin 6.0.83 → 6.1.29 (the committed `cyrius.lock` regenerated against the new bundled stdlib — `./lib/` is a gitignored build artifact — to 37 entries, `cyrius deps --verify` 37/0). Binary 600,848 B; `render_frame` 2.520 ms; 37/37 + 73/73. |

## v0.27.x — Language-adoption arc (complete, 0.27.0–0.27.5 shipped)

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.27.5 | 2026-06-01 | Post-playtest movement fixes + toolchain/lockfile cleanup. (1) WASD strafe inverted — `player_tick` strafe-left/right vectors swapped, `A` strafed right / `D` left; corrected to strafe-left = facing+90° = `(-sin,+cos)`, strafe-right = `(+sin,-cos)`. (2) Cardinal-axis moves dropped — the apply block was gated on `move_x != 0 && move_y != 0`, so pure forward/back or strafe while facing due N/S/E/W never updated position; regated on `\|\|`. (3) Toolchain pin 6.0.1 → 6.0.29 (clears pin-drift warning); `cyrius.lock` now the resolver's canonical 27-entry output, `sha256sum` hand-population + CI empty-lock guard dropped, `cyrius deps --verify` unconditional (resolves known-issue #1, pulled forward from v0.27.6). Binary 590,696 → 590,824 B (+128 B move restructure). |
| v0.27.4 | 2026-06-01 | Framebuffer geometry fix. The live `/dev/fb0` path assumed a 320×200×32 panel with a 1280-byte pitch and dumped a packed RGBA block at offset 0 — on real displays it tiled horizontally and collapsed into the top ~20–33 px band (`--ppm` path self-describing, so headless smoke never caught it). `framebuf_init` now reads real `xres`/`yres`/`bits_per_pixel`/`line_length` via `FBIOGET_VSCREENINFO` (0x4600) + `FBIOGET_FSCREENINFO` (0x4602); `framebuf_flip` integer-scales + center-blits at the true pitch/bpp (32bpp `store32` fast path, 16bpp RGB565 fallback), writing one active band per frame. Dead `rgb_buf` (256 KB) dropped. Binary 587,752 → 590,696 B (+2,944 B). Render path untouched. |
| v0.27.3 | 2026-05-21 | `Result<T, E>` adoption at the WAD IO/parse boundary: `WadError` typed-error enum, `wad_open` returns Result in-place, `wad_read_lump_r` / `wad_read_lump_into_r` parallels, `?` + exhaustive `match` in `doom_main` boot path. Binary 585,224 → 587,752 B (+2,528 B Result/match codegen tax). `render_frame` 2.132 ms (variance-level). First use of v5.8.x sum types in doom's own code. |
| v0.27.2 | 2026-05-21 | `: i64` return-type annotation sweep across all 20 modules (270 fn sigs). Parse-only, ABI-identical binary (585,224 B). `render_frame` 2.114 ms. |
| v0.27.1 | 2026-05-21 | Dep-tag re-pin to upstream-published bsp 1.1.3 + vani 0.9.4. Bundle content byte-identical save for `Version:` header. Binary 585,320 → 585,224 B (−96 B). |
| v0.27.0 | 2026-05-21 | Cyrius 5.7.48 → 6.0.1 lift (sum-types / `Result<T,E>` / `?` / exhaustive-match infrastructure landed; cybs/cycc rename); vani 0.9.1 → 0.9.3 annotation pass; `cyrius.toml` + `cyrb.toml` retired (single `cyrius.cyml` + `${file:VERSION}` template); CI lifted to patra-style installer + pre-flight HTTP gate + lockfile-guarded verify. Binary 565,856 → 585,320 B (+19,464 B annotation rt-table + sum-type-emit growth-tax). |

## v0.26.x — bsp as a real dep

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.26.2 | 2026-05-01 | Cyrius 5.7.48 lift + vani 0.3.0 → 0.9.1 `core` profile (29 KB vs 76 KB full bundle). Manifest hygiene: lib/ gitignored, patra dropped from stdlib, `.cyrius-toolchain` deleted. Binary 259,920 → 565,856 B (+305 KB — recovery gated on O3). |
| v0.26.1 | 2026-04-20 | Cyrius 5.5.0 → 5.5.2 (enum-constant fold). −7,296 B / −2.7 %. No source changes. |
| v0.26.0 | 2026-04-20 | Migrated manifest to `cyrius.cyml`; `[deps.bsp] @ 1.1.1`. `render_bsp_node` uses bsp primitives. Release CI runs `CYRIUS_DCE=1`; CI gains WAD-free test job. |

## v0.24.x — Security hardening + toolchain rollups

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.24.6 | 2026-04-20 | Cyrius 5.5.0 bump; E1M6 map-cap fix (MAP_MAX_SSECTORS 512 → 1024); test suite WAD-include chain repaired. |
| v0.24.2–0.24.5 | 2026-04-13–14 | bsp 1.0.0 → 1.0.1 dep bump; Cyrius 4.6.2 / 4.8.2 / 4.8.5-1 toolchain rollups; switch jump-table tuning (4-case weapon/ammo conversions). |
| v0.24.1 | 2026-04-13 | Short-circuit cleanup (15+ nested-if → `&&` chains); Cyrius 4.4.3 verified. |
| v0.24.0 | 2026-04-13 | **CVE audit + fixes**: map index bounds, texture column bounds, BLOCKMAP offset validation, WAD lump read zero-fill, sprite minimum lump size (3 CRITICAL + 2 HIGH, all fixed). |

## v0.23.x — Polish + Cyrius 4.0 modernization

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.23.2 | 2026-04-13 | P(-1) hardening — termios iflag bitmask fix (pre-existing bug since 0.5.0). |
| v0.23.1 | 2026-04-13 | Cyrius 4.0.0 modernization (~300 changes: compound assignments, negative literals, unary minus). |
| v0.23.0 | 2026-04-13 | Weapon bob, sound triggers, HUD ammo display, armor absorption. |

## v0.22.x — Gameplay completeness

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.22.0 | 2026-04-13 | Ammo consumption, hitscan shooting, death/respawn, key cards, locked doors. |

## v0.21.x — Rendering accuracy

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.21.0 | 2026-04-13 | DOOM-accurate `scalelight`/`zlight` tables, animated wall textures, masked midtextures, intermission screen, level stat tracking. |

## v0.20.x — Dep management + menus + animation

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.20.0 | 2026-04-13 | `[deps]` auto-resolve; sakshi 0.5.0 → 0.9.0; WAD-native menus (TITLEPIC, M_DOOM, M_SKULL cursor); weapon switching + firing; sprite frame animation; animated flats. |

## v0.19.x — Audio + display bridge

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.19.1 | 2026-04-11 | `audio.cyr` (WAD SFX + ALSA), shravan 2.0.0 dep, GTK3 display bridge. |
| v0.19.0 | 2026-04-11 | ALSA audio via stdlib, shravan 2.0.0, 12 WAD sounds cached. |

## v0.18.x — WAD-native status bar + CI polish

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.18.2 | 2026-04-10 | Weapon hand positioning, CI lint/format, cc3 3.3.13 verified. |
| v0.18.1 | 2026-04-10 | Ammo totals polish, softened yellow STYSNUM, regression test suites, batch-mode benches. |
| v0.18.0 | 2026-04-10 | STBAR background, STTNUM red / STYSNUM yellow numbers, ARMS box, weapon ownership tracking. |

## v0.17.x — Level progression

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.17.0 | 2026-04-09 | Level progression (E1M1 → E1M9 + secret exits), `load_map()`, all 9 shareware maps verified. |

## v0.16.x — HUD polish + extended specials

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.16.0 | 2026-04-09 | Doomguy face (STFST + health frames), HUD layout match, walk-over triggers, tagged sectors, extended door/lift specials. |

## v0.15.x — Automap

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.15.0 | 2026-04-09 | `automap.cyr` (TAB toggle, Bresenham, color-coded linedefs, player arrow). |

## v0.14.x — Doors + lifts

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.14.0 | 2026-04-09 | `doors.cyr` — door open/wait/close + lift lower/wait/raise; tagged sectors; 32-slot thinker array. |

## v0.13.x — Weapon overlay + BLOCKMAP collision

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.13.0 | 2026-04-09 | Weapon sprite overlay; BLOCKMAP O(1) collision; `asr()` applied to collision math. |

## v0.12.x — Audit quick wins

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.12.0 | 2026-04-09 | Fake contrast (reversed to match original), light scale `>> 4`, texture pegging flags, sprite rotation 1–8 by viewer angle. |

## v0.11.x — Tests + benches + docs

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.11.0 | 2026-04-08 | 73 assertions across 13 groups; 14 benchmarks; `bench-history.sh`; full module dependency graph in `docs/architecture/overview.md`. |

## v0.10.x — Full game loop

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.10.0 | 2026-04-08 | All 13 modules in loop; span-based floor/ceiling; **patch cache (200× speedup)**; sky rendering; frame time 5 s → 22 ms. |

## v0.5.0–0.9.0 — Foundations

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.9.0 | 2026-04-08 | `sprite.cyr` — thing sprites, distance sort, scale, COLORMAP shading. |
| v0.8.0 | 2026-04-08 | Floor/ceiling flat textures + perspective. |
| v0.7.0 | 2026-04-08 | `texture.cyr` — wall texture compositing, COLORMAP lighting, distance shading. **Critical fix**: `asr()` for sign-preserving right shift (Cyrius `>>` is logical). |
| v0.6.0 | 2026-04-08 | Sakshi tracing, `--ppm` headless mode. |
| v0.5.2 | 2026-04-08 | Palette lazy-init segfault fix; `scripts/get-wad.sh`; fuzz harnesses (50K + 1K iters). |
| v0.5.1 | 2026-04-08 | CI via `cyrb build`; BSP git dep. |
| v0.5.0 | 2026-04-08 | First end-to-end build: 14 source files (3,094 LoC), 56 KB binary, full module set scaffolded. |

## v0.1.0 — Scaffold

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.1.0 | 2026-04-08 | Project scaffolded; architecture defined; clean-room implementation plan from DOOM specs. |
