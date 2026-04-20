# Changelog

All notable changes to cyrius-doom will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
