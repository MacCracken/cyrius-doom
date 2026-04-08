# Cyrius DOOM — Claude Code Instructions

## Project Identity

**cyrius-doom** — DOOM engine in Cyrius. Direct framebuffer, no libc, no SDL, kernel syscalls only.

- **Type**: Standalone game binary / kernel demo
- **License**: GPL-3.0-only (clean-room implementation)
- **Language**: Cyrius (native)
- **Version**: SemVer, version file at `VERSION`
- **Target binary size**: 30-50KB
- **Status**: Scaffolded, pre-implementation

## Genesis Layer

Part of **AGNOS** — an AI-native operating system. Genesis repo: `/home/macro/Repos/agnosticos`.

- **Compiler**: `/home/macro/Repos/cyrius` (cc2)
- **Kernel**: `/home/macro/Repos/agnos` (AGNOS kernel with PS/2 keyboard, timer, VFS, initrd)
- **Standards**: `agnosticos/docs/development/applications/first-party-standards.md`

## Architecture

```
src/
  main.cyr        — entry, game loop (35Hz tick)
  wad.cyr         — WAD parser (IWAD header, directory, lump load)
  render.cyr      — BSP traversal, wall/floor/ceiling column rendering
  map.cyr         — linedefs, sidedefs, sectors, segs, nodes, blockmap
  things.cyr      — monsters, items, projectiles, AI state machine
  player.cyr      — movement, shooting, collision detection
  status.cyr      — HUD (health, ammo, arms, face)
  input.cyr       — PS/2 scancodes → game actions
  framebuf.cyr    — direct framebuffer writes (320x200 palette indexed)
  fixed.cyr       — 16.16 fixed-point math
  tables.cyr      — precomputed sin/cos/tan (1024 entries)
  sound.cyr       — PC speaker (optional)
  menu.cyr        — title screen, menus
  tick.cyr        — timer-driven 35Hz game loop
```

## Key Constraints

- **All math is 16.16 fixed-point** — no FPU, no floating point. Original DOOM ran on a 386.
- **No libc** — direct syscalls for file I/O, framebuffer, keyboard, timer
- **No memory allocator** — fixed buffers for map data, WAD lumps, framebuffer
- **320x200 resolution** — palette indexed (256 colors from WAD PLAYPAL lump)
- **35Hz game tick** — matches original DOOM timing
- **WAD files not included** — user provides DOOM1.WAD (shareware) or DOOM.WAD

## Development Process

### Work Loop

1. **P(-1)** — Read DOOM Black Book / Unofficial DOOM Specs / vidya before implementing
2. Implement module in Cyrius
3. `cyrb build` — verify compilation
4. Test against shareware WAD (DOOM1.WAD)
5. Profile binary size — stay under 50KB budget
6. Update CHANGELOG

### Implementation Order

1. fixed.cyr + tables.cyr (math foundation)
2. wad.cyr (can test independently — parse and dump lump directory)
3. framebuf.cyr (can test independently — draw solid colors, gradients)
4. map.cyr (load E1M1, dump geometry)
5. render.cyr (BSP traversal, draw walls)
6. input.cyr + player.cyr (move through level)
7. things.cyr (monsters, items)
8. status.cyr + menu.cyr (HUD, title screen)
9. sound.cyr (PC speaker, optional)
10. tick.cyr + main.cyr (tie it all together)

## DO NOT

- **Do not commit or push** — the user handles all git operations
- **NEVER use `gh` CLI** — use `curl` to GitHub API only
- Do not include WAD files in the repo
- Do not copy id Software source code — this is a clean-room implementation from documented specs
- Do not use floating point — all math is 16.16 fixed-point
