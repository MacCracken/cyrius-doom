# Changelog

All notable changes to cyrius-doom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.20.0] - 2026-04-13

### Changed

- **Dependency management** — added `[deps]` section to `cyrius.toml` for auto-resolve via `cyrius deps`. Stdlib modules (string, alloc, fmt, io, args, sakshi, audio) are now declared and auto-included by the build tool. Removed 24 unused vendored stdlib modules from `lib/`.
- **sakshi upgraded** — 0.5.0 to 0.9.0 (constants migrated from var to enum, expanded error handling)
- **stdlib refreshed** — string.cyr gains `atoi()`, `strstr()`; io.cyr gains file locking; all modules synced to Cyrius 3.10.1
- **Manual includes removed** — `include "lib/..."` lines in `main.cyr` replaced by auto-include from `cyrius.toml` deps declaration
- **60+ constants migrated var to enum** — ThingType, ThingState, ThingCat, ThingLayout, ThingFlags, MonsterConst, MenuScreen, SoundConst, plus removal of 5 unused FIXED_* vars. Saves ~60 gvar_toks slots.
- Minimum Cyrius version: 3.10.1 (auto-include, undefined function diagnostic)
- Binary size: 152KB (stdlib upgrade adds code, enum migration saves data)

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
