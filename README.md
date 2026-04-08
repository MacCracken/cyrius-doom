# Cyrius DOOM

> DOOM in Cyrius. Direct framebuffer. No libc. No SDL. Just kernel syscalls. Target: 30-50KB binary.

## What This Is

A clean-room implementation of the DOOM engine in Cyrius — the sovereign systems language bootstrapped from a 29KB seed. Reads standard WAD files (DOOM1.WAD shareware or DOOM.WAD registered). Renders directly to framebuffer via kernel syscalls. No external dependencies.

## Why

The industry-standard "is it a real OS?" test.

- Anthropic's $20,000 compiler **compiles** DOOM
- The AGNOS kernel **runs** it
- Cyrius **rewrites it smaller**

The original DOOM binary is ~700KB (with libc, SDL, X11). This version targets 30-50KB — direct syscall emission, no runtime, no linking overhead.

## Architecture

```
cyrius-doom/
  src/
    main.cyr        — entry point, game loop
    wad.cyr         — WAD file parser (IWAD header, directory, lump loading)
    render.cyr      — BSP traversal, wall/floor/ceiling rendering
    map.cyr         — map geometry (linedefs, sidedefs, sectors, segs, nodes)
    things.cyr      — monsters, items, projectiles
    player.cyr      — movement, shooting, collision, health/armor/ammo
    status.cyr      — HUD (health, ammo, arms, face)
    input.cyr       — keyboard handling (PS/2 scancodes → game actions)
    framebuf.cyr    — direct framebuffer writes (320x200, palette indexed)
    fixed.cyr       — 16.16 fixed-point math (no FPU required)
    tables.cyr      — sine/cosine/tangent lookup tables (1024 entries)
    sound.cyr       — PC speaker or VirtIO-sound (optional)
    menu.cyr        — title screen, menu navigation
    tick.cyr        — 35Hz game tick timer
```

## WAD Format

DOOM's WAD (Where's All the Data) format is fully documented:
- 12-byte header: magic ("IWAD"/"PWAD"), lump count, directory offset
- Directory: array of (offset, size, name) entries
- Lumps: raw data blobs (maps, textures, sprites, sounds, palettes)

The format is simple enough for a single-file parser. No compression. No encryption. Sequential reads.

## Rendering Pipeline

```
BSP tree traversal (back-to-front)
  → wall segments (linedefs → segs)
    → column-by-column rendering (320 columns)
      → texture mapping (fixed-point U/V)
        → framebuffer write (palette index → RGB)

Floor/ceiling: visplane algorithm
Sprites: sorted by distance, clipped to walls
Lighting: sector light level × distance falloff
```

All math is 16.16 fixed-point — no floating point required. The original DOOM ran on a 386 without an FPU. This version does the same.

## Target Platforms

| Platform | Display | Input | Sound |
|----------|---------|-------|-------|
| AGNOS kernel | VGA framebuffer / VirtIO-GPU | PS/2 keyboard (existing driver) | PC speaker / VirtIO-sound |
| Linux userspace | `/dev/fb0` or terminal | stdin / evdev | optional |

## Controls

```
Arrow keys    — move/turn
Ctrl          — shoot
Space         — open doors/use
Shift         — run
1-7           — weapon select
Esc           — menu
```

## Build

```
cyrb build
# produces build/doom (~30-50KB)
```

## Run

```
# On AGNOS kernel (from shell):
doom doom1.wad

# On Linux (framebuffer):
./build/doom /path/to/doom1.wad
```

## Size Budget

| Component | Estimated |
|-----------|-----------|
| WAD parser | ~2KB |
| BSP renderer | ~8KB |
| Map/geometry | ~4KB |
| Things/AI | ~5KB |
| Player/collision | ~3KB |
| Fixed-point math + tables | ~5KB |
| Input/framebuffer | ~2KB |
| HUD/status bar | ~2KB |
| Menu/title | ~2KB |
| Sound (optional) | ~1KB |
| **Total** | **~34KB** |

The original id Software DOOM source is ~30,000 lines of C. This version targets ~3,000-5,000 lines of Cyrius.

## References

- [DOOM Source Code](https://github.com/id-Software/DOOM) — GPL-2.0, released 1997
- [Unofficial DOOM Specs](https://doomwiki.org/wiki/WAD) — WAD format documentation
- [DOOM Black Book](https://fabiensanglard.net/gebbdoom/) — Fabien Sanglard's engine analysis
- [Game Engine Black Book: DOOM](https://fabiensanglard.net/gebbdoom/index.html) — rendering pipeline details

## License

GPL-3.0-only. Clean-room implementation — no id Software code copied. WAD format is documented and public.

## Project

Part of [AGNOS](https://agnosticos.org) — the AI-native operating system.
Part of [Cyrius](https://github.com/MacCracken/cyrius) — the sovereign systems language.
