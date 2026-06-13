# cyrius-doom — Current State

> **Last refresh**: 2026-06-13 (v0.30.1 — **player-feedback rendering patch**. Four live-play bugs reported + fixed, multi-agent-reviewed [9 findings, 1 confirmed-cosmetic, applied]: (1) **weapon psprite mispositioned** + firing animation "totally off" — `sx=253+loff / sy=228+toff` equals the correct DOOM `sx=1−loff / sy=16−toff` ONLY at the pistol ready frame [loff=−126,toff=−106] by coincidence, so every other weapon/frame was off [fist dead-center, gun lurching while firing]; now the real hotspot formula via a shared `render_blit_psprite`. (2) **muzzle-flash overlay added** — the separate `ps_flash` sprite [PISF/SHTF/CHGF/MISF, fullbright] was never drawn [`render_draw_flash`]; closes the 0.30.0-deferred item. (3) **wall texture-U mirror on turn** — `render_seg`'s `sx1>sx2` swap reordered sx/ty but not the U endpoints, mirroring right-to-left segs; now swap-corrected in the wall + masked passes; closes the 0.29.4-deferred U-swap-mirror. (4) **enemies always faced the player** — `sprite_find_frame` only looked up 6-char single-rotation lumps, missing DOOM's combined `TROOA2A8`-style lumps [rot 2/3/4/6/7/8]; now resolves them + returns a flip flag, `sprite_render_all` mirrors columns. Plus the SEE/CHASE walk-frame 35 Hz strobe gated to ~4-tick. No control changes [fire stays `F`; a Space/Enter-fire experiment was reverted]. Binary 608,344→**610,576 B** [+2,232]; `render_frame` **2.957 ms** [render path unchanged, within variance]. Built under cycc **6.2.2** — launcher ignores the 6.1.37 pin, see toolchain row. AGNOS QEMU re-verify of the rendering path: see Gates.) | **Refresh cadence**: every release (ideally bumped by the release post-hook).
>
> CLAUDE.md is preferences / process / procedures (durable). This file is **state** (volatile — binary sizes, version, in-flight slots, dep tags, gates). Anything that rots within a minor lives here. See [first-party-documentation § CLAUDE.md](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#claudemd).

---

## Current version

**[`VERSION`](../../VERSION)** = `0.30.1` (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`).

| Surface | Pin |
|---|---|
| Cyrius toolchain | `cycc 6.1.37` (in `cyrius.cyml`). **Drift warning**: the installed launcher resolves cycc via CYRIUS_HOME/PATH and ignores the pin — even `~/.cyrius/versions/6.1.37/bin/cyrius` ran cycc **6.2.2** at the 0.29.3 cut (PATH-prepend doesn't fix it). 0.29.3 metrics are therefore on 6.2.2; no 6.2.2 `--agnos` fold regression detected (QEMU serial probe `fixed_mul(VIEW_HEIGHT, PROJ_DIST)=429916160` matches Linux + hand-computed). Lockfile unchanged, verifies 37/0. |
| `[deps.bsp]` | `1.1.3` (git tag) |
| `[deps.vani]` | `0.9.4` (git tag, `core` profile — `dist/vani-core.cyr`, 22 `audio_*` symbols) |
| stdlib | `string`, `alloc`, `fmt`, `vec`, `str`, `io`, `fs`, `args`, `syscalls`, `hashmap`, `tagged`, `fnptr`, `freelist`, `process`, `sakshi` |

## Current binary

| Metric | Value |
|---|---|
| `build/doom` | **610,576 B** (cycc 6.2.2 — see toolchain drift note; +2,232 B over 0.30.0 for the muzzle-flash overlay + combined-rotation sprite resolution + U-swap correction). `build/doom_agnos` = **589,664 B** (QEMU re-verified — see Gates). |
| Unreachable fns (NOP-sled today, real shrink under O3) | 996 / 292,784 B |
| Recovery target under Cyrius O3 real DCE | ~260 KB |
| Frame time | `render_frame` **2.957 ms** / `+sprites` 2.952 ms (E1M1, 0.30.1, cycc 6.2.2). Render path **unchanged** from 0.30.0 — the U-swap correction is a couple of ops per seg and the combined-rotation sprite lookups don't register at the E1M1 spawn sprite count; the delta vs 0.30.0's 3.10 ms is run-to-run variance. ~7× headroom on the 22 ms budget. |
| Hot math | `fixed_mul` 7 ns / `asr` 4 ns / `texture_get_column` ~690 ns / `pcache_get_hit` 7 ns |

Frame-time budget: 22 ms per tick @ 35 Hz. Current: ~12× headroom.

## Gates (last green, 2026-06-13)

| Gate | Result |
|---|---|
| `cyrius deps --verify` | **37 verified, 0 failed** (lock unchanged — pin didn't move at 0.30.0; no regen performed under the drifted 6.2.2 launcher, by design). CI runs `cyrius deps` then this gate. |
| `cyrius build src/main.cyr build/doom` | OK, **610,576 B** (cycc **6.2.2** — launcher ignores the 6.1.37 pin, see toolchain row). Clean-from-scratch (`rm -rf build`) build passes. |
| `cyrius build --agnos src/main.cyr build/doom_agnos` | OK, **589,664 B**. **QEMU-verified on the final 0.30.1 binary**: `agnos/scripts/doom-smoke.sh` **PASS** (gnoboot+OVMF+NVMe; serial `cyrius-doom v0.30.1` + `wad loaded`; TITLEPIC fb 240 colors — palette + patch decode intact under the psprite/sprite changes), and `agnos/scripts/doom-ingame-smoke.py` **PASS** (driven into E1M1). The rendering changes (psprite blitter, muzzle flash, U-swap, combined-rotation sprite resolution) are pure ring-3 codegen with no new syscall/timing/alloc surface — no `--agnos` 3-op-multiply risk. |
| `cyrius test tests/doom.tcyr` (WAD-free, CI subset) | **63/63** (+26: a `combat:` group — p_random determinism/range, ammo deduction, damage/state transitions, hitscan select + LOS, splash falloff, rocket projectile). |
| `./build/test_doom wad/DOOM1.WAD` (full) | **101/101** (37 WAD-free combat+math + 64 WAD-gated). |
| `fuzz_wad` / `fuzz_fixed` / `fuzz_weapon` | **2000 / 50000 / 20000 clean**. `fuzz_weapon` (new) drives the real `render_draw_weapon` psprite decoder with malformed one-lump WADs. |
| `./build/doom wad/DOOM1.WAD --ppm` | E1M1 + automap + intermission PPMs at 192,015 B each; map summary `V=467 L=475 SD=648 S=85 SG=732 SS=237 N=236 T=134` (134 = the 138 map things minus 4 player starts). Render unchanged from 0.29.4 (walls/flats resolve, ≤0.1% viewport black). |
| All 9 shareware maps (E1M1–E1M9) | E1M1/E1M3/E1M7/E1M9 PPM-rendered + **visually verified** at the 0.29.4 cut: the black-hole/void family is gone (≤0.1% viewport black). Remaining wall items catalogued on the roadmap (closed-sector-clip-inversion = closed-door-in-play, U-swap mirror, SLADRIP no-op, FLAT_MAX, bsp asr). |
| bsp 1.1.3 standalone (upstream) | 79/79 tests, 13/13 benches sub-μs, 25K fuzz iters |
| Lint / fmt | clean across all 20 src modules + vendored libs |

## Architecture surface

- **20 modules** in `src/*.cyr`:
  `main`, `fixed`, `tables`, `wad`, `framebuf`, `map`, `texture`, `render`, `sprite`, `input`, `player`, `tick`, `things`, `status`, `sound`, `audio`, `doors`, `automap`, `level`, `menu`.
- **2 vendored libs** in `lib/`:
  `bsp.cyr` (1.1.3, spatial geometry primitives) + `vani-core.cyr` (0.9.4 core profile, ALSA audio shim).
- **270 fn signatures** all `: i64`-annotated (v0.27.2 sweep — parse-only, ABI-identical).
- **`Result<T, E>` adoption** at the WAD IO/parse boundary (v0.27.3): `WadError` typed-error enum, `wad_open` returns Result, `wad_read_lump_r` / `wad_read_lump_into_r` parallel forms, `?` + exhaustive `match` at the boot boundary in `doom_main`.

## In-flight slot map

Current arc: **v0.28.x graphics** (review/hardening/parity/performance). The v0.27.x language-adoption arc is complete; the perf micro-pass remains re-targeted to v0.29.x (gated on Cyrius O4 regalloc, v6.4.x).

| Slot | Status | What |
|---|---|---|
| **v0.27.0** | shipped 2026-05-21 | Cyrius 5.7.48 → 6.0.1 lift; vani 0.9.1 → 0.9.3; manifest modernization; CI patra-style installer |
| **v0.27.1** | shipped 2026-05-21 | bsp 1.1.2 → 1.1.3 + vani 0.9.3 → 0.9.4 dep-tag re-pin |
| **v0.27.2** | shipped 2026-05-21 | `: i64` return-type annotation sweep on all 20 modules (270 sigs, ABI-identical) |
| **v0.27.3** | shipped 2026-05-21 | `Result<T, E>` adoption at the WAD IO/parse boundary: `WadError` enum, `wad_open` returns Result, `wad_read_lump_r` parallels, `?` + exhaustive `match` in `doom_main` boot path |
| **v0.27.4** | shipped 2026-06-01 | Framebuffer geometry fix — `framebuf_init` queries real `/dev/fb0` `xres`/`yres`/`bpp`/`line_length` via `FBIOGET_{V,F}SCREENINFO`; `framebuf_flip` integer-scales + center-blits at true pitch/bpp. Fixes top-band tiling on real displays. Dead `rgb_buf` dropped |
| **v0.27.5** | shipped 2026-06-01 | Movement fixes — (1) WASD strafe vectors inverted in `player_tick` (`A`/`D` swapped), (2) cardinal-axis moves dropped by a `&&` guard, now `\|\|`. Plus toolchain pin → 6.0.29 + lockfile cleanup (canonical 27-entry lock, CI guard dropped, known-issue #1 resolved) pulled forward from v0.27.6 |
| **v0.27.6** | gated | yukti `sys_stat` dup-fn cleanup — drop the duplicate-fn warning once yukti re-bundles without `sys_stat`. Did not fire under 6.0.29 or 6.0.83; likely moot. Gated on a yukti rebundle |
| **v0.28.0** | shipped 2026-06-07 | Graphics review/hardening/audit/performance. Patch-decoder bounds propagation (weapon/sprite/HUD+menu — F01/F02/F03 — and TEXTURE1 — F19), visplane heap-OOB-**write** fix + visible E1M1 corruption fix (F17), dead `render_flat_span` delete (F16), flat-fill inline ~15% `render_frame` (F11), weapon-lump cache (F14). Toolchain pin → 6.0.83. 8 of 20 verified findings shipped; rest re-slotted across 0.28.x. Audit: `docs/audit/2026-06-07-v0.28-graphics-hardening.md` |
| **v0.28.1** | shipped 2026-06-08 | **AGNOS target support** — first port. OS interactions branched under `CYRIUS_TARGET_AGNOS`: inlined agnos syscall numbers (collide with Linux), portable timing (`uptime_ms`/`sleep_ms`), fb queries (`fbinfo`#38/`blit`#39), WAD memory-load (no `lseek`), exit/input/sound paths. Linux build byte-identical. |
| **v0.28.2** | shipped 2026-06-08 | **DOOM renders on AGNOS** — the 584 KB ELF ring-3 exec's from disk, loads the 4.2 MB `DOOM1.WAD`, builds the palette, and blits a 240-colour frame to the hardware framebuffer via `fbinfo`#38 / `blit`#39. (Unblocked by two AGNOS kernel fixes: PMM→24 MB, phys-page zeroing ≥16 MB.) |
| **v0.28.3** | shipped 2026-06-09 | **AGNOS keyboard input** via `kbscan`#42 (non-blocking raw Set-1 scancode poll, make/break decode, persistent `key_state`) — DOOM playable past the title screen. WASD/arrows/space/E/F/R/Tab/1–7/Q/Esc. |
| **v0.30.1** | prepared 2026-06-13 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Player-feedback rendering patch.** Four live-play bugs: (1) weapon psprite position — `253+loff/228+toff` matched only the pistol ready frame by coincidence → DOOM hotspot `1−loff/16−toff` via shared `render_blit_psprite` (fist now lower-right, no more lurch while firing); (2) **muzzle-flash overlay** added (`render_draw_flash`, `PISF/SHTF/CHGF/MISF` fullbright — closes 0.30.0-deferred item); (3) **wall texture-U mirror** on turn — `sx1>sx2` swap now reorders U endpoints in wall + masked passes (closes 0.29.4-deferred U-swap-mirror); (4) **enemies always faced player** — `sprite_find_frame` now resolves DOOM combined-rotation lumps (`TROOA2A8`) + returns a flip flag, `sprite_render_all` mirrors columns. Plus SEE/CHASE walk-strobe gated to ~4-tick. Multi-agent diff review (9 findings, 1 confirmed-cosmetic: chaingun/rocket flash_max capped to reachable=1, animated multi-frame flash → roadmap). No control changes (fire stays `F`). Binary 608,344→610,576 B; `render_frame` 2.957 ms (render path unchanged). |
| **v0.30.0** | prepared 2026-06-13 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Shooting-mechanics overhaul.** Multi-agent review of input→hitscan→damage→psprite (27 confirmed). Fixed: unbounded fire cadence (ammo+hitscan every tick → now gated on weapon-ready), shoot-through-walls (LOS via `thing_check_sight`), pain-lock (painchance-gated), corpse re-kill + vanishing corpses, psprite `alloc`/frame leak, weapon-7 silent-fire. Fidelity: rocket→projectile+splash (`thing_spawn_missile`/`thing_explode`), barrels explode + chain, shotgun 7-pellet spread, per-weapon refire cadence, sector-tracked weapon light + muzzle-flash fullbright, `p_random` PRNG. Tests +26 (37→63 WAD-free, 75→101 full) + `fuzz_weapon` 20k. Audit `2026-06-13-shooting-hitscan.md`. Binary 602,032→608,344 B; `render_frame` 3.10 ms (render path unchanged). Deferred (cosmetic): BEXP explosion frames, muzzle-flash overlay sprite, xdeath giblets → roadmap. |
| **v0.29.4** | prepared 2026-06-12 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Wall black-holes + walk-through-walls fixed.** Walls: A/B-render diagnosis pinned the "void/black-hole" family to **texture resolution, not geometry** — (1) PNAMES `strlen` over-read of non-null-terminated 8-byte patch names [161/350 → `patch_lumps=-1` → black; fixed by a null-terminated copy in `texture_init`], (2) patch-cache `PCACHE_DATA_SIZE` 8192→40960 [big patches truncated past byte 8192 → black columns]. All 4 sampled maps ≤0.1% viewport black (E1M9 70.7%→0.1%). Collision: blockmap cell-index double-shift collapsed every query to cell (0,0) → walk-through-walls [latent since 0.13.0] + a new `doom.tcyr` regression group [73→75]. `render_frame` 2.451→2.93 ms (PNAMES fix = real wall draw, A/B-isolated; not the cache). Refuted/deferred: NEAR_CLIP overflow [not a black cause], closed-sector-clip-inversion [HIGH, closed-door-in-play] + U-swap mirror [MED] → roadmap. |
| **v0.29.3** | shipped 2026-06-12 | **Flat rendering fixed** — `render_flat_spans` distance was missing the ×`PROJ_DIST` factor (160× too small → world step ~0 → one texel smeared per row = the "untextured gray floors" bug on AGNOS hardware + Linux; same error pinned zlight fullbright). Follow-ups in the same cut: sky rows no longer registered into `vp_ceil` (F_SKY1 is a real flat — span pass was overdrawing the sky once flats textured), fake contrast no longer leaks into plane lights, per-row `vp_ceil_h` so ceiling spans invert the same height the wall pass projected. Multi-agent review (units/fidelity/refutation + 2 sweeps + 9-map visual + AGNOS QEMU in-game). Review findings → roadmap (visplane slot evidence + new unslotted wall-path bug table). |
| **v0.29.2** | shipped 2026-06-11 | Toolchain pin → **6.1.37** (fixes the `--agnos` 3-op-multiply miscompile; 0.29.1 2-op workarounds reverted to clean chained form in `framebuf.cyr` + `render.cyr`, QEMU-verified fb_buf=256000 / scalelight=6144 / zlight=16384). World-tick **aliveness**: removed the 1000-unit `MONSTER_SIGHT_RANGE` cap (monsters wake on LOS like real DOOM — was keeping all but the nearest asleep), and idle monsters now animate their two standing frames (were pinned to a static frame). Reproduced via a pty harness driving the real-tty input path. |
| **v0.29.1** | shipped 2026-06-11 | World-tick froze without input — two platform-specific causes (Linux: `read(stdin)` blocked for non-tty stdin → `input_enable_raw_mode` now forces `O_NONBLOCK` via `fcntl`; AGNOS: a 255 KB/frame `fb_buf` heap overflow from a cycc `--agnos` 3-op-multiply miscompile stomped the render tables → 2-operand workaround). Both found by reproducing the freeze, not static reading. |
| **v0.29.0** | shipped 2026-06-11 | AGNOS: the kernel scales now — `framebuf_blit_agnos` palette-converts a FIXED 256 KB 32bpp frame and passes the integer scale to `blit`#39 a4[39:32] (agnos 1.44.20); ring 3 writes 64K px/frame instead of scale²·64K, old scale-3 heap cap gone. |
| **v0.28.4** | shipped 2026-06-10 | Gameplay correctness. (1) render+sprite/movement **90° angle-convention unification** — `render_transform_vertex` + sprite transforms used depth `dy·cos−dx·sin` (north@0) while movement/hitscan/floors/map use `(cos,sin)` (east@0); walls/sprites now match. (2) **one-sided-wall collision** — `player_check_linedef` treated flagless one-sided walls as passable. (3) **Linux `termios` VMIN** offset off-by-one (`c_line` byte) left VMIN=1 → blocking `read` → loop froze between keystrokes. (4) **perspective-correct wall + masked-seg depth** (interpolate scale not z) — this is **F22**, pulled forward from 0.29.x; texture-U half (F22b) also landed. (5) **sakshi log routing** for boot diagnostics. Toolchain pin → 6.1.29 (committed `cyrius.lock` regenerated against the new stdlib → 37 entries). |

### Forward 0.28.x slots (re-slotted at the 0.28.4 cut — the AGNOS arc consumed 0.28.1–.3 and gameplay correctness took 0.28.4, so the Black Book parity/perf themes shift to ≥ 0.28.5)

| Slot | Theme |
|---|---|
| **v0.28.5** | Visplane pool rewrite (F08) — keystone Black Book parity; subsumes F13. Rides the `lib/test.cyr` `test_each` refactor (was 0.27.x) |
| **v0.28.6** | Sprite/masked-seg depth-aware clipping (F07 per-drawseg silhouettes → F05b → F05 clip_solid) |
| **v0.28.7** | Sky + wall-mapping parity (F09 horizon anchoring) |
| **v0.28.8** | Structural perf (F12 sidedef/sector index cache, F15 thing-sector cache) — bench-gated |
| **v0.28.9–.11** | The original Black Book sub-audits: BSP+collision (.9), game-state (.10), security-refresh (.11, partly discharged early by F01/F02/F03/F19/F17 + the 0.28.4 collision fix) |

After 0.28.x: **v0.29.x** O4 micro-perf pass + deep renderer fidelity (F06 native-scale midtex). **F22 perspective-correct U/depth shipped early in 0.28.4** (pulled forward off this list). See [`roadmap.md`](roadmap.md).

## Known issues (workarounds in place)

| # | Issue | Workaround |
|---|---|---|
| 2 | `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition wins)` — stdlib defines `sys_stat` and vani's transitively-bundled yukti also defines it (unannotated). | Codegen-identical, warning-only. Did not fire under cycc 6.0.29 or 6.0.83, but kept tracked until yukti drops `sys_stat` from its dist surface. Gated on a yukti rebundle. |
> Issue #3 (cycc `--agnos` 3-operand-chained-constant-multiply miscompile — `alloc(320*200*4)` folded to 800 not 256000 on `--agnos` only, root cause of the 0.29.1 AGNOS world-tick freeze) was **resolved in 0.29.2** by the toolchain pin bump to cycc 6.1.37. The 0.29.1 2-operand workarounds in `framebuf.cyr` + `render.cyr` were reverted to the clean chained form and the fold **verified on the actual `--agnos` binary in QEMU** (serial: fb_buf=256000, scalelight=6144, zlight=16384). Confirmed broken on cycc 6.1.29 + 6.1.35.
>
> Issue #1 (cycc 6.0.1 lockfile-writer regression — empty `cyrius.lock`) was **resolved in 0.27.5**: toolchain pin bumped to 6.0.29, whose `cyrius deps` writes a canonical lock; `cyrius deps --verify` is unconditional again. The 0.28.4 pin bump to 6.1.29 changed the bundled stdlib, so the committed lock was **regenerated** against it (`rm -rf lib && cyrius deps` → **37 entries**, verify 37/0). `./lib/` is a gitignored build artifact, so the lock must always match the pinned toolchain's stdlib — regenerate + commit it whenever the pin moves. (An earlier 0.28.4 attempt mis-diagnosed this as a "writer regression" and added a CI lock-restore guard; that guard verified the *stale* lock against the *new* stdlib and broke CI — reverted.)

## Dependency lineage

`cyrius-doom` **composes**: `bsp` (spatial geometry) + `vani` (audio, transitional — will be replaced by **dhvani** once the Rust→Cyrius port lands; `audio_*` shape is the migration target so `src/audio.cyr` stays ABI-stable across the swap).

Stdlib pulled in by `cyrius.cyml [deps]`; transitive resolution refreshes `yukti` / `patra` / `sakshi` through vani's `[deps.*]` overrides.

## Consumers

- **AGNOS kernel** — initrd demo
- **kiran** — game engine reference
- **vidya** — field notes / language research

## Verification

- `wad/DOOM1.WAD` (shareware, downloaded via `scripts/get-wad.sh`) — not in repo, gitignored.
- Headless: `--ppm` mode (no /dev/fb0 needed).
- Interactive: requires `/dev/fb0` or the GTK3 bridge (`scripts/x11view.py`).

---

*Refresh procedure: bump the per-slot status above when a version ships, update the binary metrics from `bench-history.csv` + `stat -c '%s' build/doom`, and re-anchor "Last refresh" in the header. Historical release narrative lives in [`completed-phases.md`](completed-phases.md), not here.*
