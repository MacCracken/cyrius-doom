# DOOM Black Book Audit — Handoff Note

**Prepared**: 2026-04-14
**For**: v0.25.0 audit agent
**Book**: Game Engine Black Book: DOOM by Fabien Sanglard — **in hand**

## Starting State

- **cyrius-doom v0.24.5** — 196KB, 20 modules, ~5,500 lines
- **BSP 1.0.1** — spatial geometry library (stable API)
- **Cyrius 4.8.5-1** — compiler (pinned in cyrius.toml)
- Full gameplay loop working: shoot, pick up, open locked doors, die, respawn
- All 9 shareware maps (E1M1-E1M9) render clean
- render_frame: ~2.6-2.9ms (91% headroom on 35Hz budget)
- Security hardened: 5 CVE findings fixed (see `docs/audit/2026-04-13-security-cve-audit.md`)

## Chapter-by-Chapter Priorities

The roadmap (`docs/development/roadmap.md`) lists these v0.25.0 items:

1. **R_DrawPSprite psprite coords** — verify weapon positioning matches DOOM source exactly. v0.18.2 locked `sx=253+loff, sy=228+toff` via QA inspection. Book gives canonical formula; verify ours matches.
2. **Brightness tuning** — v0.21.0 added proper `scalelight[16][48]` / `zlight[16][128]` tables matching `R_InitLightTables()`. Compare rendered screenshots vs book illustrations for brightness curve accuracy.
3. **Visplane correctness** — verify our span generation matches `R_DrawPlanes()` in the book. We currently deferred to end-of-frame; book shows per-wall-render flat span accumulation.
4. **Episode complete screen** — E1M8 boss kill currently wraps back to E1M1. Book covers the ENDOOM / bunny scroll finale text flow.
5. **Chapter-by-chapter verification** — walk each rendering chapter with code side-by-side.

## Key Files to Cross-Reference with Book

| Black Book Topic | cyrius-doom File |
|-----------------|------------------|
| WAD format (Ch 3) | `src/wad.cyr` |
| BSP traversal (Ch 4) | `src/render.cyr` (render_bsp_node) + bsp library |
| Wall rendering (Ch 5) | `src/render.cyr` (render_seg) |
| Texture compositing (Ch 5) | `src/texture.cyr` (texture_get_column) |
| Visplanes / flats (Ch 5) | `src/render.cyr` (render_flat_spans) |
| Sprites (Ch 6) | `src/sprite.cyr` |
| Lighting (Ch 5/6) | `src/render.cyr` (scalelight/zlight tables) |
| Sound (Ch 7) | `src/audio.cyr`, `src/sound.cyr` |
| Network/intermission (Ch 8) | `src/level.cyr` (intermission), N/A for network |

## Known Deviations From Original

These are INTENTIONAL differences — document if the book suggests otherwise:

- **Cyrius, not C**: single compilation unit, 16.16 fixed-point throughout
- **No libc, no SDL**: direct syscalls, /dev/fb0 or PPM output
- **Masked midtextures deferred** (v0.21.0) rather than inline during wall pass — matches DOOM source per external research but verify against book
- **Security hardening**: `map_validate()` runs after `map_load()` rejecting malformed WADs — original DOOM did NOT bounds-check indices (CVE potential)
- **No DEHACKED, no savegames, no multiplayer** — out of scope for clean-room
- **PWAD support deferred** — currently only loads IWAD

## Process

Follow the P(-1) from CLAUDE.md — the security research step was just added. For rendering correctness:
1. Read relevant Black Book chapter
2. Compare our code to the chapter's algorithm
3. Check `docs/audit/` for prior findings
4. Render a PPM screenshot for comparison
5. Write findings to `docs/audit/2026-04-15-black-book-audit.md`
6. File fixes as v0.25.x roadmap items

## Notable Performance Benchmarks (v0.24.5, cc3 4.8.5-1)

```
fixed_mul:           4ns
fixed_div:           3ns
asr:                 4ns
sin_lookup:          4ns
atan2:              14ns
texture_find:      211ns
texture_get_column: 857ns
pcache_get (hit):   10ns
colormap_shade:      4ns
point_on_side:      25ns
render_frame:     ~2.6-2.9ms (run-to-run variance)
wad_find_lump:     30μs (linear scan, 1264 lumps — could hash)
```

`wad_find_lump` at 30μs is the biggest remaining perf outlier. Only called at init/level-load, not per-frame, so low priority.

## Good Luck

The engine is playable and hardened. The book will tell you what's wrong with the rendering compared to the original. Expect small fidelity issues around lighting curves and perspective correction. Be skeptical of anything claiming the current state is "DOOM-accurate" — it's DOOM-adjacent, and the book is how we get to DOOM-accurate.

Assembly up.
