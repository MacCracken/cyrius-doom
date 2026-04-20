# cyrius-doom Development Roadmap

> **v0.26.1** — 259,920 B (cc5 5.5.2 enum-fold: −7,296 B vs 5.5.0),
> 20 modules + vendored `lib/bsp.cyr` (bsp 1.1.2), full gameplay loop,
> DOOM-accurate lighting, 9/9 shareware maps render via bsp library
> traversal, security hardened (CVE audit: 5/5 fixed), signed-shift
> correctness audit landed in bsp 1.1.0. CI runs the WAD-free test subset
> + DCE on release builds. 73/73 cyrius-doom tests, 79/79 bsp tests,
> 76K fuzz iters total. fmt + lint clean.

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
| v0.24.2–0.24.5 | bsp dep tag bump (1.0.0 → 1.0.1), Cyrius 4.6.2 / 4.8.2 / 4.8.5-1 toolchain rollups, switch-jump-table tuning (4-case weapon/ammo conversions) |
| v0.24.6 | Cyrius 5.5.0 bump, E1M6 map-cap fix (MAP_MAX_SSECTORS 512 → 1024), test suite includes repaired |
| v0.26.0 | bsp real dep: `cyrius.cyml` migration + `[deps.bsp] @ 1.1.1`, `render_bsp_node` uses bsp primitives, DCE in release CI, test job in CI, `scripts/bench-history.sh` modernized |
| v0.26.1 | Cyrius 5.5.2 + bsp 1.1.2 (enum-constant fold, −7,296 B / −2.7 %). No source changes. |

## v0.24.0 — Security Hardening (CVE Audit Fixes)

| # | Item | Severity | Detail |
|---|------|----------|--------|
| 1 | Map index bounds validation | CRITICAL | Validate all seg/linedef/sidedef/node indices after map_load() |
| 2 | Texture column bounds | CRITICAL | Validate patch col_off within lump, post_ptr within buffer |
| 3 | BLOCKMAP offset validation | CRITICAL | Validate cell list offsets within blockmap lump size |
| 4 | WAD lump read validation | HIGH | Check file_read return value, zero-fill on partial read |
| 5 | Sprite minimum lump size | HIGH | Reject sprite lumps < 8 bytes (patch header minimum) |

See: `docs/audit/2026-04-13-security-cve-audit.md`

## v0.27.0 — Performance pass (held against Cyrius O4 regalloc)

Deliberate hold. Cyrius's parallel compiler-optimization track (O1–O6
in `cyrius/docs/development/roadmap.md` §"v5.4.x Queue") has three
phases that directly move cyrius-doom's hot paths. Hand-optimizing
`fx_mul` / `asr` / column loops today would fight the codegen once
O4's linear-scan register allocator lands and delivers its projected
2–3× on hot inner loops.

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Wait for **Cyrius O2** (peephole: strength reduction, flag reuse, LEA combining, aarch64 `madd`/`msub`) | Upstream | Small runtime wins on math-dense loops. Free bump once shipped. |
| 2 | Wait for **Cyrius O3** (IR-driven DCE + const prop + dead-store elim) | Upstream | Today we NOP 49 KB of dead code (same file size). O3 strips it for real — binary genuinely shrinks. |
| 3 | Wait for **Cyrius O4** (linear-scan regalloc, Poletto–Sarkar) | Upstream | The single biggest win. `render_frame` projection: 2.5 ms → ≤1 ms. Column renderer, BSP walk, patch cache all benefit. |
| 4 | Re-bench hot paths on O2/O3/O4-enabled toolchain | Pending | `bench-history.csv` row per upstream phase landing, with A/B before/after numbers to confirm the compiler wins stick. |
| 5 | Revisit manual patterns only after O4 | Pending | At that point any remaining 5–10 % wins from column-loop restructure are worth chasing; before then, no. |

## v0.26.1 — Cyrius 5.5.2 + bsp 1.1.2 (2026-04-20) — DONE

Pure toolchain bump, no source changes. Picks up the 5.5.2 enum-constant
`sc_num` fold — every enum variant read now emits `mov rax, imm32` (5 B)
instead of `mov rcx, gvaddr; mov rax, [rcx]` (~10 B). cyrius-doom is
enum-dense, so the win compounds: **267,216 → 259,920 B (−7,296 B,
−2.7 %)**. bsp's standalone binary: −1,448 B (−1.86 %). Bench numbers
within run-to-run variance of 0.26.0 — this is a codegen-size win, not
a runtime-hot-path win.

## v0.26.0 — BSP as a real dep (2026-04-20) — DONE

Turned the "Composes: bsp" line from aspirational into mechanical truth.
Manifest migrated to `cyrius.cyml` with `[deps.bsp] @ 1.1.1`.
`render.cyr` / `player.cyr` / `sprite.cyr` swap `map_point_on_side` /
`map_node_child_{r,l}` / `map_is_subsector` / `map_subsector_idx` for
`bsp_*` equivalents; `map.cyr` sheds the duplicates. Layout-compatible
(identical 112-byte node block). Release CI runs `CYRIUS_DCE=1`;
cyrius-doom CI now runs the WAD-free 37-assert test subset.

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
