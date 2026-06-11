# cyrius-doom — Completed Phases

> Chronological record of shipped versions. CHANGELOG holds the per-version detail; this file is the one-line index. Sister to [`state.md`](state.md) (live state) and [`roadmap.md`](roadmap.md) (forward).

Each entry: one row, headline only. For the full changelog see [`CHANGELOG.md`](../../CHANGELOG.md).

## v0.28.x — Graphics arc (in flight, 0.28.0 shipped)

| Version | Shipped | Milestone |
|---------|---------|-----------|
| v0.28.0 | 2026-06-07 | Graphics review/hardening/audit/performance — the new 0.28.x anchor. Multi-agent render-path audit (67 raw → 27 canonical → 20 adversarially verified; 8 shipped, rest re-slotted across 0.28.1–.7). **Hardening**: propagated the v0.24.0 C2 patch-bounds checks from `texture_get_column` to the three other patch decoders — weapon `render_draw_weapon` (F01), `sprite_render_all` (F02), the shared HUD/menu/title `st_draw_patch_shaded` (F03, lump size threaded from every call site in status + menu) — and to the `TEXTURE1` parser (F19); fixed a genuine heap **OOB write** in the visplane row loops where `ceil_screen`/`floor_screen` were only relatively clamped (F17), which also corrected a real 11-px corruption block on E1M1 (x=234–237, y=107–109). **Perf**: inlined the flat fetch + hoisted the COLORMAP row in `render_flat_spans` (F11) — `render_frame` ~2.10 → ~1.78 ms (~15%, same-toolchain), `texture_get_column` unchanged; cached the weapon patch instead of re-reading the lump every frame (F14). **Hygiene**: deleted dead `render_flat_span` (F16). Toolchain pin 6.0.29 → 6.0.83. Binary 590,824 → 592,456 B (+1,632 B bounds checks, net of the dead-fn delete). 37/37 WAD-free + 73/73 full; fuzz 1k/50k clean; 11/12 reference frames byte-identical (E1M1 game = the intended F17 fix). Audit: `docs/audit/2026-06-07-v0.28-graphics-hardening.md`. |
| v0.28.1 | 2026-06-08 | **AGNOS target support** — first port of the engine to the sovereign OS (the "agnsh launches DOOM" arc). OS interactions branched under `CYRIUS_TARGET_AGNOS`: inlined agnos syscall numbers (which collide with Linux — e.g. agnos `0`=exit), portable timing via `uptime_ms`/`sleep_ms`, framebuffer geometry via `fbinfo`#38 + `blit`#39, WAD memory-load (no `lseek`), exit/input/sound paths. Linux build byte-identical; `--agnos` builds + runs. 37/37 + 73/73. |
| v0.28.2 | 2026-06-08 | **DOOM renders on AGNOS.** The 584 KB ELF exec's from disk in ring 3, slurps the 4.2 MB `DOOM1.WAD` into memory, parses it, builds the palette, and blits a 240-colour frame to the hardware framebuffer via `fbinfo`#38 / `blit`#39 — `agnsh` launches a real userland application. A warm-up mmap workaround for a kernel first-syscall-return fault was documented in-place (later removed when the kernel root cause — user stack in the identity-mapped range — was fixed). Unblocked by two AGNOS kernel fixes (PMM → 24 MB, physical-page zeroing ≥ 16 MB). Smoke: `agnos/scripts/doom-smoke.sh`. |
| v0.28.3 | 2026-06-09 | **AGNOS keyboard input — DOOM playable past the title screen.** `input_poll`'s agnos branch drains the kernel's new `kbscan`#42 (a non-blocking raw Set-1 scancode poll), decodes make/break, and keeps `key_state` as persistent held state (closer to real DOOM than the Linux press-then-clear path). Mapping: WASD + arrows + space/E/F/R/Tab/1–7/Q/Esc. Validated in QEMU (`agnos/scripts/doom-input-test.py`, USB-xHCI + HMP sendkey). Requires an AGNOS kernel with `kbscan`#42. |
| v0.28.4 | 2026-06-10 | Gameplay correctness pass (surfaced once the engine was driven interactively rather than via still `--ppm`). (1) **Angle-convention unification** — `render_transform_vertex` + both `sprite.cyr` transforms computed view depth as `dy·cos−dx·sin` (forward = north@BAM0) while movement/hitscan/`render_flat_spans`/map thing-angles use `(cos,sin)` (east@BAM0); walls+sprites rotated 90° off movement and disagreed with floors. Unified to `ty=dx·cos+dy·sin`, `tx=dx·sin−dy·cos` (lateral verified against the floor-span screen-right axis `(sin,−cos)` so left/right isn't mirrored). (2) **One-sided-wall collision** — `player_check_linedef` early-returned passable for any line lacking both `ML_BLOCKING` and `ML_TWOSIDED`, i.e. every ordinary one-sided wall; now solid at the distance test. (3) **Linux `termios` VMIN** — raw-mode set `c_cc` at offsets 22/21 (assumed base 16) but the kernel struct has a `c_line` byte at 16 so the base is 17; VMIN (23) stayed 1 → blocking `read(stdin)` → the 35 Hz loop froze between keystrokes (`things_tick`/`doors_tick` only advanced on input). Corrected to 23/22. (4) **Perspective-correct wall + masked-seg depth** (interpolate scale `PROJ_DIST/z`, not `z`, across columns) + texture-U — **F22**, pulled forward from 0.29.x. (5) **sakshi log routing** for the `map:`/stats/`things:` boot lines. Toolchain pin 6.0.83 → 6.1.29; CI committed-lock restore guard for the 6.1.29 `cyrius deps` writer re-regression. Binary 597,608 B; `render_frame` 2.486 ms; 37/37 + 73/73. |

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
