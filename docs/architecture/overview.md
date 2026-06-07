# cyrius-doom Architecture

## Rendering Pipeline

```
1. BSP traversal (front-to-back, determines visible walls)
2. Wall rendering (column-by-column, textured from WAD patches)
3. Visplane collection (floor/ceiling span bounds per row)
4. Flat rendering (row-by-row, perspective-mapped 64x64 textures)
5. Sprites (back-to-front, scaled, clipped to wall columns)
6. Status bar (HUD overlay: health, ammo, armor, face, keys)
7. Framebuffer flip (palette → BGRA conversion, write to /dev/fb0)
```

All coordinates are 16.16 fixed-point. `asr()` used for all signed right shifts (Cyrius >> is logical).

## Memory Layout

All large buffers heap-allocated via `alloc()` (bump allocator, 1MB from brk).

| Buffer | Size | Purpose |
|--------|------|---------|
| screen_buf | 64KB | 320x200 × 8-bit palette indexed |
| fb_buf | ~pitch×yres | full-screen scratch for the integer-scaled, centered /dev/fb0 blit, sized to the real panel (replaced the fixed 256KB rgb_buf in v0.27.4) |
| palette | 768B | 256 × RGB from WAD PLAYPAL |
| colormap | 8.5KB | 34 × 256 light-to-palette mapping |
| sine_table | 8KB | 1024 × i64 trig values |
| wad_dir | 48KB | 2048 lump entries × 24 bytes |
| wad_lump_buf | 64KB | Shared lump read buffer |
| map_* | ~500KB | Vertices, linedefs, sidedefs, sectors, segs, subsectors, nodes, things |
| tex_table | 4KB | 128 texture definitions × 32 bytes |
| patch_lumps | 2.8KB | 350 patch name → lump index |
| patch_cache | 64KB | 8-slot LRU patch data cache |
| flat_cache | 256KB | 64 flat textures × 4KB (64x64) |
| clip_top/bottom/solid | 7.5KB | Per-column occlusion state |
| vp_floor/ceil | 12.8KB | Per-row visplane bounds and flat indices |
| sprite_order/dist | 2KB | 128 visible sprite sort buffers |
| things | 56KB | 512 thing records × 112 bytes |

Total resident: ~1.3MB. Fits within the bump allocator's initial 1MB brk + one grow.

## Module Dependency Graph

```
main.cyr
  ├── lib: string, alloc, fmt, io, args, sakshi
  ├── fixed.cyr ← tables.cyr
  ├── wad.cyr
  ├── framebuf.cyr
  ├── map.cyr ← wad, fixed
  ├── texture.cyr ← wad, fixed
  ├── render.cyr ← map, texture, framebuf, fixed, tables
  ├── sprite.cyr ← render, map, wad, fixed
  ├── input.cyr
  ├── player.cyr ← map, input, fixed
  ├── tick.cyr
  ├── things.cyr ← map, player, fixed
  ├── status.cyr ← framebuf, player
  ├── sound.cyr
  └── menu.cyr ← framebuf, input, status, tick
```

## Game Loop (35Hz)

```
while (running) {
    tick_begin()
    input_poll()          → read keyboard, update action bitmask
    player_tick()         → move, collide, update view position
    things_tick()         → monster AI, item pickups
    sound_tick()          → advance tone queue
    render_frame()        → BSP → walls → visplane spans
    sprite_render_all()   → sort + draw thing sprites
    status_render()       → HUD overlay
    framebuf_flip()       → palette→BGRA, write /dev/fb0
    tick_wait()           → nanosleep to 28.57ms boundary
}
```

## Performance

Live numbers (binary size, frame time, hot-math timings) live in
[`../development/state.md`](../development/state.md) and the per-release
[`bench-history.csv`](../../bench-history.csv) — not duplicated here, where they
rot. As of v0.28.0: `render_frame` ~1.78 ms / `+sprites` ~1.78 ms against the
22 ms @ 35 Hz tick budget (~12× headroom), binary 592,456 B (cycc 6.0.83).

## WAD File Access

Sequential reads via syscalls. WAD kept open for the session.
Directory loaded once at startup. Lumps read on demand.
Patch data cached in 8-slot LRU (eliminates I/O during rendering).
Flats pre-loaded into flat_cache at texture_init time.
