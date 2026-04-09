# DOOM Engine Audit — cyrius-doom vs Original

Gap analysis comparing cyrius-doom v0.11.0 against the original id Software DOOM rendering engine, based on doomwiki.org specs and Fabien Sanglard's renderer analysis.

## Rendering Pipeline Comparison

| Stage | Original DOOM | cyrius-doom | Status |
|-------|--------------|-------------|--------|
| R_RenderBSPNode | BSP front-to-back traversal | `render_bsp_node` | DONE |
| Seg rendering | Column-by-column textured walls | `render_seg` with `texture_get_column` | DONE |
| Backface culling | angle2-angle1 > 180° | Near-clip only | PARTIAL — no angle-based cull |
| Solidsegs occlusion | Linked list of occluded X ranges | `clip_solid[]` per-column flag | DONE (simpler) |
| R_DrawPlanes | Visplane → horizontal spans | `render_flat_spans` row-by-row | DONE |
| Visplane merging | Merge adjacent subsectors with same material | Per-column store, no merge | MISSING |
| R_DrawMasked | Sprites + masked midtextures | `sprite_render_all` | PARTIAL |
| Masked midtextures | Two-sided lines with transparent mid tex | Not implemented | MISSING |
| Screen melt | Wipe effect between levels | Not implemented | MISSING |

## Lighting Comparison

| Feature | Original DOOM | cyrius-doom | Status |
|---------|--------------|-------------|--------|
| COLORMAP lookup | 32 colormaps from WAD | `render_shade()` via loaded COLORMAP | DONE |
| Sector light → colormap | `lightlevel >> 4` (16 distinct levels) | `31 - (light >> 3)` | CLOSE — slightly different scale |
| Fake contrast | N/S walls +1 lightnum, E/W walls -1 lightnum | `orient_dim = 2` for N/S facing | CLOSE — reversed direction |
| Light diminishing (walls) | Per-column scale → colormap offset | `dist_dim = depth / 96` | PARTIAL — should use scale not depth |
| Light diminishing (flats) | Per-span distance → colormap offset | `dist_dim = dist / 96` in flat spans | DONE (approximate) |
| Extralight | Player weapon flash adds light | Not implemented | MISSING |
| Invulnerability colormap | Colormap 32 (inverse) | Not implemented | MISSING |

### Fake Contrast Fix Needed

Original: horizontal walls (same Y) get `lightnum--`, vertical walls (same X) get `lightnum++`.
We have it reversed and use an approximation based on dx vs dy magnitude instead of exact axis alignment.

```
# Original DOOM:
if (v1.y == v2.y) lightnum--;      # E-W walls darker
if (v1.x == v2.x) lightnum++;      # N-S walls brighter

# cyrius-doom (current, approximate):
if (seg_dx > seg_dy) orient_dim = 2;  # N/S-ish walls dimmed
```

Fix: check exact axis alignment, apply ±1 to COLORMAP level (= ±16 light units).

## Wall Rendering Comparison

| Feature | Original DOOM | cyrius-doom | Status |
|---------|--------------|-------------|--------|
| Wall textures from patches | Multi-patch compositing | `texture_get_column` with patch cache | DONE |
| Texture alignment (x offset) | Sidedef x_offset | `sd_xoff + seg_offset` | DONE |
| Texture alignment (y offset) | Sidedef y_offset | `sd_yoff << 16` as start | DONE |
| Upper unpegged | Texture anchored at top | Not checked | MISSING |
| Lower unpegged | Texture anchored at bottom | Not checked | MISSING |
| Animated textures | ANIM lumps cycle texture names | Not implemented | MISSING |
| Switches | Toggle texture on use | Not implemented | MISSING |

### Texture Pegging

Original DOOM uses linedef flags `ML_DONTPEGTOP` and `ML_DONTPEGBOTTOM` to control whether textures are anchored to ceiling or floor. We read these flags but don't apply them to the Y offset calculation. This causes some textures (especially door frames and window sills) to appear misaligned.

## Floor/Ceiling Comparison

| Feature | Original DOOM | cyrius-doom | Status |
|---------|--------------|-------------|--------|
| Flat textures (64x64) | Loaded from F_START..F_END | `flat_cache` with `flat_get_pixel` | DONE |
| Perspective mapping | Per-span world coord stepping | Row-by-row with horizontal step | DONE |
| Sky texture | F_SKY1 → SKY1 wall texture, mapped to view angle | `render_load_sky`, drawn as column | DONE |
| Sky always at top | Sky never clips, always full height | Clips to ceiling region | CLOSE |
| Animated flats | Cycle flat names (e.g., nukage) | Not implemented | MISSING |
| Visplane limit | 128 maximum | No limit (but no merging either) | DIFFERENT |

## Sprite Comparison

| Feature | Original DOOM | cyrius-doom | Status |
|---------|--------------|-------------|--------|
| Sprite rendering | Billboard, column-based patches | `sprite_render_all` with patch columns | DONE |
| Distance sorting | Back-to-front | Insertion sort back-to-front | DONE |
| Wall clipping | Clip to solidsegs ranges | Clip to `clip_top/clip_bottom` | DONE |
| Sprite rotation | 8 rotations based on view angle | Always frame A rotation 0 | MISSING |
| Sprite animation | Frame cycling per state | Not implemented | MISSING |
| Transparent sprites | Skip palette index 0 | `if (pal != 0)` check | DONE |
| Sector floor anchoring | Thing z + floor height | BSP walk for sector lookup | DONE |
| Weapon sprite (psprite) | Overlay weapon on screen | Not implemented | MISSING |
| 128 sprite limit | Max visible sprites | 128 in sort buffer | DONE |

### Sprite Rotation Fix

Original DOOM selects from 8 rotation angles based on the angle between the viewer and the thing. Sprite lump naming: `TROOA1` = front, `TROOA2A8` = front-left (frame A, rotations 2 and 8 mirrored), etc.

We always use rotation 0 or 1, showing monsters from the same angle regardless of viewer position.

## Data Format Comparison

| Lump | Original DOOM | cyrius-doom | Status |
|------|--------------|-------------|--------|
| PLAYPAL | 14 palettes × 768 bytes | Palette 0 only | PARTIAL |
| COLORMAP | 34 colormaps × 256 bytes | All 34 loaded | DONE |
| TEXTURE1/2 | Texture definitions | TEXTURE1 only (shareware) | DONE |
| PNAMES | Patch name list | Loaded, mapped to lump indices | DONE |
| ENDOOM | Exit screen text | Not used | MISSING (cosmetic) |
| DEMO1-3 | Recorded demos | Not used | MISSING |
| REJECT | PVS reject table | Not loaded | MISSING |
| BLOCKMAP | Collision grid | Not loaded (brute-force collision) | MISSING |

### REJECT and BLOCKMAP

Original DOOM uses the REJECT lump for fast line-of-sight rejection between sectors, and the BLOCKMAP lump for efficient collision detection (only test nearby linedefs). We brute-force both — iterate all linedefs for collision, iterate all one-sided linedefs for sight checks. These are performance features, not correctness features.

## Game Logic Comparison

| Feature | Original DOOM | cyrius-doom | Status |
|---------|--------------|-------------|--------|
| Movement + collision | P_TryMove with BLOCKMAP | `player_check_position` brute-force | DONE (slow) |
| Wall sliding | Separate X/Y movement on collision | X-only then Y-only fallback | DONE (simplified) |
| Step height (24 units) | Check floor height difference | `PLAYER_MAX_STEP = 24` | DONE |
| Doors | Open/close with sector height change | Not implemented | MISSING |
| Lifts/platforms | Moving sectors | Not implemented | MISSING |
| Switches/buttons | Trigger linedef specials | Not implemented | MISSING |
| Monster AI | State machine (see/chase/attack/pain/die) | `thing_ai_tick` state machine | DONE (included, not in game loop yet) |
| Item pickups | Touch radius check | `things_check_pickups` | DONE (included) |
| Damage model | Hitscan + projectile | `thing_damage` | DONE (included) |
| Automap | 2D overlay | Not implemented | MISSING |

## Priority Fixes (quick wins)

1. **Fake contrast direction** — swap the ±1 to match original
2. **Texture pegging** — apply `ML_DONTPEGTOP` / `ML_DONTPEGBOTTOM` flags to Y offset
3. **Sprite rotation** — select rotation 1-8 based on angle between viewer and thing
4. **Light scale formula** — use `lightlevel >> 4` instead of `>> 3` for correct 16-level mapping

## Medium Effort

5. **Masked midtextures** — transparent middle textures on two-sided lines
6. **BLOCKMAP loading** — use WAD BLOCKMAP for O(1) collision instead of brute-force
7. **Weapon sprite** — draw current weapon overlay on screen
8. **Animated textures** — cycle texture names per frame

## Large Effort

9. **Doors/lifts** — sector height changes triggered by linedef specials
10. **Visplane merging** — reduce redundant flat rendering
11. **Automap** — 2D overhead line drawing

Sources:
- [Doom rendering engine](https://doomwiki.org/wiki/Doom_rendering_engine)
- [Fabien Sanglard's DOOM renderer analysis](https://fabiensanglard.net/doomIphone/doomClassicRenderer.php)
- [Fake contrast](https://doomwiki.org/wiki/Fake_contrast)
- [Light diminishing](https://doomwiki.org/wiki/Light_diminishing)
- [COLORMAP](https://doomwiki.org/wiki/COLORMAP)
- [Static limits](https://doomwiki.org/wiki/Static_limits)
