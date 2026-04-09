# Changelog

All notable changes to cyrius-doom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
