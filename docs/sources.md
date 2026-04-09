# Sources

Primary references for the cyrius-doom clean-room implementation.

## Books

- **Game Engine Black Book: DOOM** — Fabien Sanglard, 2018
  - Chapter 4: WAD file format, lump structure
  - Chapter 5: Software rendering pipeline
  - Chapter 6: BSP tree construction and traversal
  - Chapter 7: Wall rendering (column-by-column)
  - Chapter 8: Floor/ceiling rendering (visplanes)
  - Chapter 9: Sprites and things
  - Chapter 10: Lighting (COLORMAP, sector light levels)
  - Chapter 11: Status bar and HUD
  - Used for: rendering pipeline design, data structure choices, performance insights

## Specifications

- **Unofficial DOOM Specs** — https://doomwiki.org/wiki/WAD
  - WAD header format (12 bytes: magic + numlumps + diroffset)
  - Directory entry format (16 bytes: offset + size + name)
  - Map lump order (THINGS, LINEDEFS, SIDEDEFS, VERTEXES, SEGS, SSECTORS, NODES, SECTORS)
  - Patch/texture composition format (PNAMES, TEXTURE1)
  - Flat format (64x64 raw palette, F_START..F_END)
  - PLAYPAL (768 bytes × 14 palettes)
  - COLORMAP (256 bytes × 34 light levels)
  - Used for: all binary format parsing

## Code References (read-only, NOT copied)

- **id Software DOOM source** — https://github.com/id-Software/DOOM (GPL-2.0, released 1997)
  - r_bsp.c: BSP traversal (R_RenderBSPNode)
  - r_segs.c: Wall segment rendering (R_RenderSegLoop)
  - r_plane.c: Visplane rendering (R_DrawPlanes, R_MakeSpans)
  - r_things.c: Sprite rendering (R_DrawSprite, R_SortVisSprites)
  - p_map.c: Collision detection (P_CheckPosition, P_TryMove)
  - p_mobj.c: Thing management (P_SpawnMobj)
  - st_stuff.c: Status bar (ST_Drawer)
  - Used for: understanding algorithm intent, NOT for code copying

## Test Data

- **DOOM1.WAD (shareware)** — https://github.com/nneonneo/universal-doom
  - 4,196,020 bytes, 1264 lumps
  - Episode 1: Knee Deep in the Dead (E1M1-E1M9)
  - Downloaded by: `scripts/get-wad.sh`

## Internal References

- **vidya** — `content/cyrius/field_notes.toml`
  - Cyrius-specific lessons: logical shift trap, double alloc bug, gvar limits
  - `content/cyrius/language.toml` — compiler reference
  - `content/cyrius/assets/` — rendering screenshots (first walls, textured, sprites)

## Mathematical References

- **Bhaskara I sine approximation** (7th century)
  - sin(x) ≈ 16x(π-x) / [5π² - 4x(π-x)] for x ∈ [0, π]
  - Used in: tables.cyr for generating 1024-entry sine table
  - Accuracy: sufficient for 320x200 rendering

- **P_AproxDistance** (DOOM original)
  - dist ≈ max(|dx|, |dy|) + min(|dx|, |dy|) / 2
  - Used in: fixed.cyr `fixed_approx_dist`
  - Error: max ~8% vs true Euclidean, but ~10x faster than sqrt
