# cyrius-doom Development Roadmap

> **v0.5.0** — Full game loop compiles. 56KB binary. Walk through E1M1.

## v0.1.0 — Foundations (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | fixed.cyr — 16.16 fixed-point math | Done | mul, div, abs, clamp, lerp, approx_dist |
| 2 | tables.cyr — precomputed trig tables | Done | 1024-entry sine, Bhaskara I, atan2 |
| 3 | wad.cyr — WAD parser | Done | IWAD/PWAD header, directory, lump read |
| 4 | framebuf.cyr — framebuffer output | Done | 320x200 palette indexed, PPM output |

## v0.2.0 — Rendering (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | map.cyr — geometry loading | Done | All 7 lump types from WAD |
| 2 | render.cyr — BSP renderer | Done | Front-to-back traversal, column rendering |
| 3 | Two-sided linedefs | Done | Portal rendering with upper/lower walls |
| 4 | Per-column occlusion | Done | clip_top/bottom/solid tracking |

## v0.3.0 — Playable (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | input.cyr — keyboard | Done | Terminal raw mode, WASD + arrows |
| 2 | player.cyr — movement + collision | Done | Wall sliding, step height, ceiling check |
| 3 | tick.cyr — 35Hz timer | Done | clock_gettime + nanosleep |
| 4 | Walk through E1M1 | Done | Full game loop compiles at 56KB |

## v0.4.0 — Combat (WRITTEN, needs >64 gvar_toks)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | things.cyr — monsters + items | Written | AI state machine, pickups, damage |
| 2 | status.cyr — HUD | Written | Bitmap font, health/ammo/armor/face |
| 3 | sound.cyr — PC speaker | Written | ioctl KIOCSOUND, tone queue |
| 4 | menu.cyr — title + menus | Written | Title screen, skill select |
| 5 | Integration into game loop | Blocked | Needs cc2 gvar_toks > 64 |

## v0.5.0 — Current Release

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | All 13 source modules written | Done | 3,094 lines total |
| 2 | 9-module game loop compiles | Done | 56KB binary |
| 3 | Heap-allocated data arrays | Done | Stays under 256KB output limit |
| 4 | Enum-packed constants | Done | 64 globals (at cc2 limit) |

## v0.6.0 — Full Integration

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Include things/status/menu/sound in game loop | Not started | Needs cc2 gvar_toks expansion |
| 2 | Sakshi 0.7.0 tracing integration | Not started | Error logging, span timing |
| 3 | BSP library integration | Not started | Replace inline BSP with bsp crate |
| 4 | Binary size audit | Not started | Target under 50KB |

## v0.7.0 — Textures (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Wall texture mapping | Done | Patch compositing, column rendering, U/V mapping |
| 2 | COLORMAP lighting | Done | 34-level palette shading from WAD |
| 3 | Distance shading | Done | Walls darken with depth via COLORMAP |
| 4 | Directional wall dimming | Done | N/S vs E/W, matches original DOOM |
| 5 | Flat texture loading | Done | 64x64 floor/ceiling images cached |
| 6 | asr() fix for >> | Done | Logical-to-arithmetic shift, fixed all negative math |

## v0.8.0 — Flats (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Floor flat textures | Done | Per-pixel perspective mapping from sector flat names |
| 2 | Ceiling flat textures | Done | Same technique, inverted Y plane |
| 3 | Flat texture cache | Done | 64x64 raw palette images from F_START..F_END |
| 4 | Distance shading on flats | Done | COLORMAP dimming with depth |

## v0.9.0 — Sprites (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Sprite rendering | Done | 35 thing types, patch column drawing |
| 2 | Sprite clipping | Done | Clipped to wall clip_top/clip_bottom |
| 3 | Distance sorting | Done | Back-to-front insertion sort |
| 4 | Sector floor anchoring | Done | BSP walk for per-sprite floor height |
| 5 | Sprite lighting | Done | COLORMAP + distance falloff |

## v0.12.0 — Audit Quick Fixes (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Fake contrast direction | Done | E-W dark, N-S bright (±1 colormap level) |
| 2 | Light level scale | Done | >> 4 for 16 levels, ×2 even indexing |
| 3 | Texture pegging | Done | DONTPEGTOP / DONTPEGBOTTOM applied |
| 4 | Sprite rotation | Done | 8 rotations based on viewer-thing angle |

## v0.13.0 — Medium Gaps (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Weapon sprite overlay | Done | Pistol rendered with COLORMAP shading |
| 2 | BLOCKMAP collision | Done | WAD BLOCKMAP loaded, O(1) cell lookup |
| 3 | Animated textures | Stub | Framework in place, needs animation sequences |
| 4 | Masked midtextures | Deferred | Needs R_DrawMasked pass |

## v0.14.0 — Doors & Lifts (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Door open/close | Done | Ceiling animation with wait timer |
| 2 | Lift/platform movement | Done | Floor drops to lowest neighbor, raises back |
| 3 | Use action | Done | Ray cast to nearest special linedef |
| 4 | Common specials | Done | Door types 1,26-28,31,117; lift types 62,88 |

## v0.15.0 — Automap & Polish (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Automap | Done | TAB toggle, Bresenham lines, colored by type |
| 2 | Player arrow | Done | Green arrow showing position + facing |
| 3 | Thing dots | Done | Blue dots for monsters/items |
| 4 | Visplane merging | Deferred | Performance is fine without it (2.9ms) |
| 5 | Screen wipe | Deferred | Cosmetic, not needed for gameplay |

## v0.16.0 — Polish & Triggers (DONE)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Weapon position fix | Done | Proper signed offset math |
| 2 | HUD layout fix | Done | Matches original DOOM proportions |
| 3 | Doomguy face sprite | Done | STFST from WAD, 5 health levels |
| 4 | Walk-over triggers | Done | Doors/lifts on linedef crossing |
| 5 | Tagged sector support | Done | Switches activate remote sectors |
| 6 | Extended specials | Done | 20+ linedef types supported |

## v0.18.0 — Polish

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Weapon sprite positioning | Not started | Needs DOOM source R_DrawPSprite psprite coords |
| 2 | Weapon switching | Not started | 1-7 keys change weapon sprite |
| 3 | Firing animation | Not started | Cycle weapon frames on fire |
| 4 | Sprite frame animation | Not started | Monsters/items cycle frames per state |
| 5 | Animated textures/flats | Not started | Nukage, lava, light panels cycling |
| 6 | Intermission screen | Not started | Kill %, item %, time after level exit |
| 7 | Brightness tuning | Not started | cc3 scenes darker than cc2 |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 | Not started | Full episode 1 playable |
| 2 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 3 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 4 | DOOM Black Book audit | Not started | Chapter-by-chapter verification |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 |
| 2 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 3 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 4 | In AGNOS initrd | Not started | Boot → shell → doom |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 |
| 2 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 3 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 4 | Binary under 50KB | Not started | Size budget met |
| 5 | In AGNOS initrd | Not started | Boot → shell → doom |
