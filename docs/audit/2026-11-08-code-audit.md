# Code audit, refactor sweep and repairs — v0.36.2 (2026-11-08)

Whole-tree audit of `src/` (14,607 lines, 27 files) at v0.36.1 on cyrius 6.7.18. Three independent read-only
reviews split the tree by area: untrusted input and platform code, gameplay, and the renderer. Each finding here
was re-read against the code before it was acted on, and shareware-data claims were measured on `DOOM1.WAD`.

**Result**: no memory corruption reachable from a WAD. One heap overflow on very small framebuffers. Three
frame-stall paths from a hostile WAD. Five bugs a player can see. All are fixed below, and nine duplicated code
paths were consolidated.

## 1. Findings fixed

| ID | Severity | Where | Problem | Fix | Evidence |
|---|---|---|---|---|---|
| CA-1 | HIGH | `framebuf.cyr` | `fb_buf` is sized to the panel, but the blit always writes 200 rows of 320 pixels. On a panel under 320×200, every frame wrote up to `(200-yres)*pitch` bytes past it. | Such a panel is not used, as when `/dev/fb0` cannot be opened. | Unit + 2 mutants |
| CA-2 | MED | `menu.cyr` | `menu_run` tested quit before `menu_tick`. Wayland, setu and AGNOS re-set `input_quit` every poll while ESC is down, so a normal press backed out of a submenu and then quit the game on the next tick. | Test after `menu_tick`, which consumes a held ESC. | New test file + mutant (3 failures) |
| CA-3 | MED | `render.cyr` | When a low sky met a higher one, the near sky's row became the portal top: far walls above it were cut off flat and painted as sky, and sprites were clipped at the same line. Visible on E1M1 and E1M2. | The back ceiling is the portal top whenever both are sky. RC-W1's band painting is now unreachable and removed. | 137 staged views, 22 changed, largest inspected by eye; test + mutant |
| CA-4 | MED | `things.cyr` | The chase commitment was re-rolled on every committed step, so it almost never counted down, contrary to the documented algorithm. | Only a newly chosen direction commits. | Unit + mutant; behaviour gate in §3 |
| CA-5 | LOW | `render.cyr` | A one-row one-sided wall was skipped (`wh > 0` on an inclusive range), leaving black specks. | `wh >= 0`. | 19 px on E1M5, all black before; test + mutant |
| CA-6 | LOW | `input.cyr` | On a tty, any ESC not followed by `[` quit: F1–F4 (`ESC O x`) and Alt+key exited the game. | SS3 and Alt+key are consumed. Only an ESC ending the read is Escape. | Unit + 2 mutants |
| CA-7 | MED (hostile WAD) | `map.cyr` | Subsectors could overlap, so one frame could walk the seg list once per subsector (about 4 million `render_seg` calls). | `map_validate` rejects a seg total above the seg count. All 9 maps sum exactly. | Test + mutant |
| CA-8 | MED (hostile WAD) | `texture.cyr` | `num_patches` was bounded only by the lump end (65,535 refs per column), and widths over 4096 went uncached, repeating that per column per frame. | Refs capped at 256 (DOOM1's most is 64), width clamped at parse. | Tests + 2 mutants |
| CA-9 | MED (hostile WAD) | 4 patch decoders | Posts could repeat rows, so one crafted patch cost thousands of iterations per column. | A post may not start above the previous post's end, capping a column at 256 rows. No real patch overlaps (944 lumps checked). | Test + mutant; fuzz reference updated |
| CA-10 | LOW (hostile WAD) | `texture.cyr` | `PNAMES` had no size cap, so a directory entry of up to 2 GiB was allocated and zero-filled at boot. | Read only what `PATCH_MAX` names can use. | By reading |
| CA-11 | LOW (hostile WAD) | `texture.cyr`, `render.cyr`, `sprite.cyr` | Composited textures had no total budget, and frame-path buffers were first allocated mid-frame, so a null return could be written through. | 64 MiB composite budget, then uncached. Frame-path buffers are allocated at init. | By reading |
| CA-12 | LOW | `doors.cyr` | With all 32 thinker slots live, a one-shot switch or stair could be spent on movers that never started. | `DOOR_MAX` 256: one per sector, so a slot always exists. | Test + mutant |
| CA-13 | LOW | `texture.cyr` | `h*31+c` could give two names one value and draw the wrong texture. No collision in DOOM1. | The packed 8-byte name is the key. | Test + mutant |
| CA-14 | LOW | `wad.cyr`, `texture.cyr` | The lump buffer (64 KB) and patch cache were re-allocated on every WAD open (fuzzers only). | Lazy-init guards. | Tests + 2 mutants |
| AUDIO-8 | LOW (hostile WAD) | `audio.cyr` | The lump was allocated before its format check and rejections are not cached, so each play leaked up to 64 KB. | Every rejection is decided from the 8-byte header first. | New test file + mutant |
| BM-1 | LOW (hostile WAD) | `map.cyr` | A map with an empty BLOCKMAP kept the previous map's grid. | Missing, truncated or zero-sized grids select the linedef scan. | Test + 2 mutants |

## 2. Refactors

All byte-identical on 46 PPMs, 9 AI fingerprints and the 25-staging AI sweep, on the plain and release builds.

| ID | What |
|---|---|
| RF-1 | `thing_slot_acquire` + `thing_fill` + `thing_remove` for three spawners and four removal pairs |
| RF-2 | `map_sector_special` / `_tag`, `map_linedef_special` / `_tag`, `map_sector_set_special` over raw offsets (18 sites) |
| RF-3 | `map_line_other_sector` for four neighbour scans |
| RF-4 | `map_lump_read` for 8 lump prologues; a count over the engine cap now warns instead of losing its tail silently |
| RF-5 | `input_flags_from_keys` shared by the tty, Wayland and setu paths |
| RF-6 | `patch_post_len` for the 4 patch decoders |
| RF-7 | `render_transform_vertex` used by the sprite pass |
| RF-8 | `map_sectors_open` for 3 closed-portal tests |
| RF-9 | `wi_draw_digit` for 6 intermission digit draws |

Dead code removed: `fixed_round`, `level_add_secret`, `sprite_find_rotated`, the `st_draw_patch` /
`st_draw_grey_num` / `st_draw_grey_number` / `st_name_buf` chain with its 16 KB buffer, `ai_stats_reset`,
`wad_name_eq`, `wad_find_lump_after`, `flat_find_name`, `texture_find_name`, `sound_menu_move`,
`sound_menu_select`, the unused 2,560 B `viewangle_to_x` table, and several unread variables and enum members.
Kept deliberately: the `win_*` seam, `sound_switch` and `sound_door_close` (U-9), `wad_read_lump_into_r`.

## 3. The chase repair's behaviour gate

The same 41 stagings, old and new binary (`--ai-at`, `--ai-probe`):

| | 350 ticks, old → new | 1,050 ticks, old → new |
|---|---|---|
| wakes / chases | 348 / 348, unchanged | 348 / 348, unchanged |
| melee | 1,593 → 1,650 (+3.6%) | 5,827 → 5,959 (+2.3%) |
| ranged | 930 → 942 (+1.3%) | 2,215 → 2,260 (+2.0%) |
| `move_blocked` | 233 → 265 | 534 → 824 |

Monsters engage slightly more. Blocked moves rise from a small base (under 1% of ticks): shorter commitments mean
more re-picks. The 9 spawn-point fingerprints are unchanged because those monsters never wake.

## 4. Left open

Recorded on the roadmap under v0.37.6.

- A weapon pickup re-opens the fire gate, worth at most one early shot.
- The non-monster death countdown in `thing_ai_tick` looks unreachable. Left in place.
- Back-facing segs are not culled, and fully occluded segs still use plane and drawseg slots.
- `map_alloc`, `music_init` and `input_init` still assume their allocations succeed.

## 5. Not covered

- `vendor/` and `lib/` were not audited.
- BSP recursion depth on the AGNOS stack was not measured.
- CA-1 was not reproduced on a real small panel; the decision is unit-tested.
- CA-2 and CA-6 are verified by driving the real functions in tests, not interactively on a compositor or terminal.
- CA-3 was inspected on staged E1M1 and E1M2 views only.
- CA-10 and CA-11 have no direct test.
