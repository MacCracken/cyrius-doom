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

## v0.14.0 — Doors & Lifts

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Door open/close | Not started | Sector ceiling height animation |
| 2 | Lift/platform movement | Not started | Sector floor height animation |
| 3 | Switch/button triggers | Not started | Linedef special actions |
| 4 | REJECT table | Not started | Fast sector-to-sector sight rejection |

## v0.15.0 — Automap & Polish

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Automap | Not started | 2D overhead line drawing |
| 2 | Visplane merging | Not started | Reduce redundant flat rendering |
| 3 | Screen wipe | Not started | Melt transition between levels |
| 4 | ENDOOM screen | Not started | Exit text screen |

## v0.16.0 — Level Transitions

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Exit switch → next level | Not started | E1M1 → E1M2 etc. |
| 2 | Intermission screen | Not started | Kill %, item %, secret %, time |
| 3 | Secret exits | Not started | E1M3 → E1M9 |
| 4 | Episode select | Not started | Knee Deep / Shores / Inferno |

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
