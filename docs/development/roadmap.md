# cyrius-doom Development Roadmap

> **v0.1.0** — Scaffolded. Target: 30-50KB DOOM in Cyrius.

## v0.1.0 — Foundations

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | fixed.cyr — 16.16 fixed-point math | Not started | mul, div, sin, cos, tan, atan2 |
| 2 | tables.cyr — precomputed trig tables | Not started | 1024-entry sin/cos, generate or embed |
| 3 | wad.cyr — WAD parser | Not started | IWAD header, directory, lump read |
| 4 | framebuf.cyr — framebuffer output | Not started | 320x200 palette indexed, /dev/fb0 or VGA |

## v0.2.0 — Rendering

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | map.cyr — geometry loading | Not started | Linedefs, sidedefs, sectors, segs, nodes from WAD |
| 2 | render.cyr — BSP renderer | Not started | Back-to-front wall rendering, column-by-column |
| 3 | Floor/ceiling visplanes | Not started | Horizontal span rendering |
| 4 | Texture mapping | Not started | Wall/floor textures from WAD lumps |

## v0.3.0 — Playable

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | input.cyr — keyboard | Not started | PS/2 scancodes or evdev |
| 2 | player.cyr — movement + collision | Not started | Clipping against BSP geometry |
| 3 | Walk through E1M1 | Not started | First playable milestone |

## v0.4.0 — Combat

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | things.cyr — monsters + items | Not started | Sprite rendering, pickup logic |
| 2 | AI state machine | Not started | Chase, attack, pain, death states |
| 3 | Weapons + projectiles | Not started | Hitscan + projectile types |
| 4 | Damage + health | Not started | Player/monster damage model |

## v0.5.0 — Complete

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | status.cyr — HUD | Not started | Health, ammo, arms, face |
| 2 | menu.cyr — title + menus | Not started | Title screen, episode select |
| 3 | sound.cyr — PC speaker | Not started | Optional, basic sound effects |
| 4 | tick.cyr — 35Hz game loop | Not started | Timer-driven tick |
| 5 | Binary size audit | Not started | Must be under 50KB |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 |
| 2 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 3 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 4 | Binary under 50KB | Not started | Size budget met |
| 5 | In AGNOS initrd | Not started | Boot → shell → doom |
