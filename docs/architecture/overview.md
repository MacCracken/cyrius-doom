# cyrius-doom Architecture

## Rendering Pipeline

Original DOOM uses a BSP (Binary Space Partitioning) tree for back-to-front rendering. No Z-buffer. Each frame:

```
1. BSP traversal (determines visible walls from player position)
2. Wall rendering (column-by-column, texture-mapped)
3. Floor/ceiling (visplane algorithm — horizontal spans)
4. Sprites (sorted by distance, clipped to wall segments)
5. Status bar (HUD overlay)
6. Framebuffer flip
```

All coordinates are 16.16 fixed-point. No floating point anywhere.

## Memory Layout

Fixed buffers — no heap allocator needed:

| Buffer | Size | Purpose |
|--------|------|---------|
| Framebuffer | 64KB | 320x200 × 8-bit palette indexed |
| WAD cache | ~256KB | Active level lumps (map, textures, sprites) |
| BSP nodes | ~16KB | Current level's BSP tree |
| Visplanes | ~8KB | Floor/ceiling rendering state |
| Segs | ~8KB | Wall segment clipping |
| Sin/cos tables | 8KB | 1024 entries × 4 bytes × 2 tables |
| Palette | 768B | 256 × RGB from WAD PLAYPAL |

Total resident: ~360KB. Fits comfortably in the AGNOS kernel's memory model.

## WAD File Access

Sequential reads only. On AGNOS kernel: `open` → `read` → `close` syscalls via VFS.
On Linux userspace: standard file I/O syscalls.

WAD directory loaded once at startup. Lumps loaded per-level on map change.

## Game Loop (35Hz)

```
while (running) {
    input_poll();           // read keyboard state
    tick_update();          // advance game state (35Hz)
    render_frame();         // draw to framebuffer
    framebuf_flip();        // present
    tick_wait();            // sleep until next tick
}
```

Timer-driven, not vsync-driven. Original DOOM ran at 35 tics/second regardless of framerate.
