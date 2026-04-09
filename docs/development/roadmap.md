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

## v0.7.0 — Textures + Sprites

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Wall texture mapping | Not started | Fixed-point U/V from WAD patches |
| 2 | Floor/ceiling visplanes | Not started | Horizontal span rendering |
| 3 | Sprite rendering | Not started | Sorted by distance, clipped to walls |
| 4 | Palette lighting | Not started | COLORMAP lump, distance falloff |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 |
| 2 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 3 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 4 | Binary under 50KB | Not started | Size budget met |
| 5 | In AGNOS initrd | Not started | Boot → shell → doom |
