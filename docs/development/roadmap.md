# cyrius-doom Development Roadmap

> **v0.23.2** — 191KB, 20 modules, full gameplay loop, DOOM-accurate lighting,
> modernized to Cyrius 4.0.0, P(-1) hardened.
> Clean build, zero warnings, 51K fuzz iterations.

## Completed

| Version | Milestone |
|---------|-----------|
| v0.1.0 | Scaffolded, architecture defined |
| v0.5.0 | WAD parser, BSP walls, game loop (56KB) |
| v0.6.0 | Sakshi tracing, asr() fix (WALLS VISIBLE) |
| v0.7.0 | Wall textures, COLORMAP lighting |
| v0.8.0 | Floor/ceiling flat textures |
| v0.9.0 | Sprites (monsters, items, decorations) |
| v0.10.0 | All 13 modules, patch cache (200x speedup) |
| v0.11.0 | Test suite (73), benchmarks (14), docs audit |
| v0.12.0 | Audit fixes (fake contrast, pegging, rotation, light scale) |
| v0.13.0 | Weapon sprite, BLOCKMAP collision |
| v0.14.0 | Doors, lifts, tagged sectors, walk-over triggers |
| v0.15.0 | Automap (TAB toggle, Bresenham lines) |
| v0.16.0 | Doomguy face, HUD polish, extended specials |
| v0.17.0 | Level transitions (E1M1→E1M9, secret exits) |
| v0.18.0 | WAD-native status bar (STBAR, STTNUM, STYSNUM, STFST) |
| v0.18.1 | Ammo totals polish, softened yellow, regression tests |
| v0.18.2 | Weapon hand positioning, CI lint/format, cc3 3.3.13 verified |
| v0.19.0 | ALSA audio via stdlib, shravan 2.0.0, 12 WAD sounds cached |
| v0.19.1 | Audio module, GTK3 display bridge, health/armor HUD fix |
| v0.20.0 | Dep integration, WAD-native menus, weapon switching/firing, sprite animation, refactoring |
| v0.21.0 | DOOM-accurate lighting, masked midtextures, animated walls, intermission screen |
| v0.22.0 | Gameplay: ammo, hitscan, death/respawn, key cards, locked doors |
| v0.23.0 | Polish: weapon bob, sound triggers, HUD ammo display, armor absorption |
| v0.23.1 | Cyrius 4.0.0 modernization (~300 changes: +=, negative literals) |
| v0.23.2 | P(-1) hardening: termios iflag bitmask fix, full audit clean |

## v0.24.0 — DOOM Black Book Audit (2026-04-15)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Chapter-by-chapter verification | Not started | Walk through book with code side-by-side |
| 2 | R_DrawPSprite psprite coords | Not started | Verify weapon positioning matches source exactly |
| 3 | Brightness tuning | Not started | Compare screenshots vs original DOOM |
| 4 | Episode complete screen | Not started | E1M8 boss kill → text screen / bunny scroll |
| 5 | Visplane correctness | Not started | Verify span generation matches R_DrawPlanes |

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 playable start to finish |
| 2 | X11 display backend (native) | Not started | Direct X11 protocol, no Python bridge |
| 3 | Wayland display backend | Not started | For AGNOS desktop |
| 4 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 5 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 6 | In AGNOS initrd | Not started | Boot → shell → doom |

## Future

| Item | Detail |
|------|--------|
| Wolfenstein 3D mode | Raycaster renderer using Black Book patterns |
| GPU rendering via mabda | wgpu backend for hardware acceleration |
| Network multiplayer | Peer-to-peer via majra |
| PWAD support | Custom maps/mods |
| Full DOOM.WAD | Episodes 2-3 (registered version) |
