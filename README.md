# Cyrius DOOM

> Clean-room DOOM engine in Cyrius. 191KB. Direct framebuffer. No libc. No SDL. Just kernel syscalls.

## What This Is

A playable DOOM engine implemented from documented specs in Cyrius — the sovereign systems language bootstrapped from a 29KB seed. Reads standard DOOM1.WAD shareware files. Full gameplay loop: shoot monsters, collect keys, open doors, die and respawn, transition between all 9 maps of Episode 1.

## Status — v0.24.1

- **20 modules**, ~5,500 lines of Cyrius
- **196KB** static ELF binary, no external dependencies
- **All 9 shareware maps** (E1M1–E1M9) load and render
- **3.9ms per frame** (83% headroom on 35Hz tick budget)
- **Security hardened** — CVE audit with 5 findings, all fixed
- Built on **Cyrius 4.4.3** (cc3 compiler)

### Features

| Category | What's In |
|----------|-----------|
| **Rendering** | BSP traversal, textured walls, floor/ceiling flats, COLORMAP lighting (DOOM-accurate scalelight/zlight tables), fake contrast, sky texture, masked midtextures, animated walls (SLADRIP) and flats (NUKAGE) |
| **Sprites** | Distance-sorted, rotation-aware (8 angles), frame animation (walk/attack/pain/die/dead), wall clipping, sector lighting |
| **Gameplay** | Weapon switching (1-7), firing with ammo consumption, hitscan damage, monster AI (see/chase/attack/pain/die), death + respawn, armor absorption (green 1/3, blue 1/2) |
| **Items** | Health/armor/ammo pickups, weapon pickups (shotgun through BFG), key cards (blue/yellow/red) |
| **Doors** | Open/wait/close, lifts, key-locked doors (specials 26/27/28), walk-over triggers, tagged sector activation |
| **HUD** | WAD-native status bar (STBAR, STTNUM, STYSNUM), Doomguy face (health-based), ARMS display, key indicators, current weapon ammo |
| **Menus** | TITLEPIC title screen, M_DOOM logo, M_SKULL animated cursor, skill select, all from WAD patches |
| **Intermission** | Kill%, item%, secret%, time after level exit (WIMAP0 background, WINUM digits) |
| **Audio** | ALSA PCM playback via stdlib, 12 WAD sound effects cached |
| **Other** | Automap (TAB), level transitions (E1M1→E1M9 + secret exits), weapon bob, PC speaker sounds |

## Build & Run

```sh
# Download shareware WAD
sh scripts/get-wad.sh wad

# Build (requires Cyrius 4.0.0+)
cyrius build src/main.cyr build/doom

# Run (interactive — needs /dev/fb0 or use GTK viewer)
./build/doom wad/DOOM1.WAD

# Run specific map
./build/doom wad/DOOM1.WAD E1M3

# Screenshot mode (headless)
./build/doom wad/DOOM1.WAD --ppm
./build/doom wad/DOOM1.WAD --ppm-menu
```

## Controls

```
WASD          — move/strafe
Arrow keys    — turn/move
F             — fire
E / Space     — use (open doors)
1-7           — weapon select
R             — run
TAB           — automap
Q / ESC       — quit
```

## Architecture

```
src/
  main.cyr        — entry, game loop, menu integration
  fixed.cyr       — 16.16 fixed-point math, asr() for logical-shift workaround
  tables.cyr      — 1024-entry sine table (Bhaskara I), atan2, trig wrappers
  wad.cyr         — WAD parser (IWAD/PWAD, directory, lump read/cache)
  framebuf.cyr    — 320x200 palette-indexed framebuffer, PPM output
  map.cyr         — vertices, linedefs, sidedefs, sectors, segs, subsectors, BSP nodes, things
  texture.cyr     — wall texture compositing, flat cache, patch LRU cache, animation
  render.cyr      — BSP traversal, textured walls, COLORMAP lighting, visplane spans, sky, masked midtextures
  sprite.cyr      — thing sprites: distance sort, scale, clip, frame animation, sector lighting
  input.cyr       — terminal raw mode, WASD + arrows, bitmask action flags
  player.cyr      — movement, collision, ammo, hitscan shooting, armor, death/respawn
  tick.cyr        — 35Hz timer via clock_gettime + nanosleep
  things.cyr      — monster AI state machine, item pickups, damage, key cards
  status.cyr      — HUD: WAD-native status bar, health/ammo/armor/face/keys
  sound.cyr       — PC speaker tone queue via ioctl
  audio.cyr       — WAD sound effect loading and ALSA playback
  doors.cyr       — door/lift thinkers, key checks, walk-over triggers
  automap.cyr     — 2D overhead map with Bresenham lines
  level.cyr       — level progression, stats tracking, intermission screen
  menu.cyr        — WAD-native title screen, main menu, skill select, M_SKULL cursor
```

## References

- [Game Engine Black Book: DOOM](https://fabiensanglard.net/gebbdoom/) — Fabien Sanglard's engine analysis
- [Unofficial DOOM Specs](https://doomwiki.org/wiki/WAD) — WAD format, lump types, map data
- [DOOM Source Code](https://github.com/id-Software/DOOM) — GPL-2.0 reference (read for understanding, not copied)

## License

GPL-3.0-only. Clean-room implementation — no id Software code copied. WAD format is documented and public.

## Project

Part of [AGNOS](https://agnosticos.org) — the AI-native operating system.
Built in [Cyrius](https://github.com/MacCracken/cyrius) — the sovereign systems language.
