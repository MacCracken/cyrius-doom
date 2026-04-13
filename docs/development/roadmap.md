# cyrius-doom Development Roadmap

> **v0.21.0** — 185KB, 20 modules, DOOM-accurate lighting, masked midtextures,
> animated walls/flats/sprites, WAD-native menus + HUD + intermission, ALSA audio,
> weapon switching + firing, all 9 shareware maps.
> Verified on Cyrius 3.10.1. Benchmarks: 6ns fixed_mul, 3.9ms render_frame.

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

## v0.22.0 — Gameplay

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Ammo consumption | Not started | Fire uses ammo, empty weapon no-fire |
| 2 | Shooting (hitscan) | Not started | Fire key, trace ray, damage monsters |
| 3 | Monster damage to player | Not started | AI attack → health reduction (already partially in) |
| 4 | Death/respawn | Not started | Health ≤ 0, death screen, restart map |
| 5 | Key cards + locked doors | Not started | Blue/yellow/red key pickup + door type check |

## v0.23.0 — Polish & Correctness

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Weapon bob (sine oscillation) | Not started | psp->sx/sy bob during movement |
| 2 | Episode complete screen | Not started | E1M8 boss kill → bunny scroll |
| 3 | Sound effect triggers | Not started | Wire sound_pistol/shotgun/door to gameplay events |
| 4 | Brightness tuning | Not started | Compare vs original DOOM screenshots |
| 5 | R_DrawPSprite audit | Not started | Verify weapon coords match DOOM source exactly |

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
