# cyrius-doom Development Roadmap

> **v0.24.1** — 196KB, 20 modules, full gameplay loop, DOOM-accurate lighting,
> security hardened (CVE audit: 5/5 fixed), Cyrius 4.4.3 + short-circuit cleanup.
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
| v0.24.0 | Security: CVE audit, map/texture/blockmap bounds validation, WAD read zero-fill |
| v0.24.1 | Short-circuit cleanup (15+ nested-if → && chains), Cyrius 4.4.3 verified |

## v0.24.0 — Security Hardening (CVE Audit Fixes)

| # | Item | Severity | Detail |
|---|------|----------|--------|
| 1 | Map index bounds validation | CRITICAL | Validate all seg/linedef/sidedef/node indices after map_load() |
| 2 | Texture column bounds | CRITICAL | Validate patch col_off within lump, post_ptr within buffer |
| 3 | BLOCKMAP offset validation | CRITICAL | Validate cell list offsets within blockmap lump size |
| 4 | WAD lump read validation | HIGH | Check file_read return value, zero-fill on partial read |
| 5 | Sprite minimum lump size | HIGH | Reject sprite lumps < 8 bytes (patch header minimum) |

See: `docs/audit/2026-04-13-security-cve-audit.md`

## v0.26.0 — BSP as a real dep (2026-04-20)

Today `src/render.cyr` rolls its own BSP traversal (`render_bsp_node`) and
`src/map.cyr` rolls its own `map_point_on_side`. bsp 1.1.0 provides the
same primitives — identical 112-byte node layout, same field offsets —
but with the signed-shift correctness audit landed in 1.1.0. This version
turns the "Composes: bsp" line in CLAUDE.md from aspirational into
mechanical truth. Manifest layout modelled on `libro/cyrius.cyml`
(`[deps.bsp]` with `git` + `tag` + `modules` → vendored single-file
bundle in `lib/`).

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Migrate manifest to `cyrius.cyml` | In progress | Match libro pattern (5.x convention). Retire `cyrius.toml` / `cyrb.toml` if the build tool accepts `.cyml` alone. |
| 2 | `[deps.bsp]` pinned at `1.1.0` | In progress | `git = "https://github.com/MacCracken/bsp.git"`, `tag = "1.1.0"`, `modules = ["dist/bsp.cyr"]`. |
| 3 | bsp ships a `dist/bsp.cyr` bundle | In progress | Add `[lib]` to bsp's own manifest listing `src/*.cyr` in include order; concat into `dist/bsp.cyr`. Matches the sigil/patra dist shape libro consumes. |
| 4 | Vendor `lib/bsp.cyr` in cyrius-doom | In progress | Single-file copy of bsp's dist. Include early in `main.cyr` (before `src/render.cyr`). |
| 5 | Replace ad-hoc primitives with bsp calls | In progress | `map_point_on_side` → `bsp_point_on_side`; `render_bsp_node` uses `bsp_node_child_r/l`, `bsp_is_subsector`, `bsp_subsector_idx`. Layout is already compatible (112-byte nodes, identical field offsets). |
| 6 | Delete dead code in `src/map.cyr` | Planned | Drop the duplicated map-side primitives once bsp replaces them. |
| 7 | Verify all 9 maps + benches unchanged | Planned | `render_frame` should land within ±5% of 0.24.6 (2.73ms). |

## v0.25.0 — DOOM Black Book Audit (2026-04-15) — deferred behind 0.26.0

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

## AgentWorld / DOOM Crossover

See [roadmap-crossover.md](roadmap-crossover.md) — secureyeoman spatial threat visualization via DOOM engine.
