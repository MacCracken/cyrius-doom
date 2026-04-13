# Cyrius DOOM — Claude Code Instructions

## Project Identity

**cyrius-doom** (homage to id Software's DOOM, 1993) — Clean-room DOOM engine in Cyrius. Direct framebuffer, no libc, no SDL, kernel syscalls only.

- **Type**: Standalone game binary / kernel demo
- **License**: GPL-3.0-only (clean-room implementation)
- **Language**: Cyrius (native, compiled via cc3 4.0.0)
- **Version**: SemVer, version file at `VERSION`
- **Binary size**: 194KB (20 modules), renders at 3.9ms/frame
- **Status**: v0.24.0 — Security hardened. Full gameplay loop: shooting, ammo, death/respawn, key cards, armor absorption. DOOM-accurate lighting, masked midtextures, animated walls/flats/sprites, WAD-native HUD + menus + intermission, ALSA audio, weapon switching + bob, doors/lifts, automap, level transitions (E1M1-E1M9). CVE audit: 5 findings fixed. Cyrius 4.0.0.
- **Genesis repo**: [agnosticos](https://github.com/MacCracken/agnosticos)
- **Philosophy**: [AGNOS Philosophy](https://github.com/MacCracken/agnosticos/blob/main/docs/philosophy.md)
- **Standards**: [First-Party Standards](https://github.com/MacCracken/agnosticos/blob/main/docs/development/applications/first-party-standards.md)

## Consumers

AGNOS kernel (initrd demo), kiran (game engine reference), vidya (field notes / language research)

**Composes**: bsp (spatial geometry, git dep tag 0.9.0), sakshi (tracing 0.9.0)

## References

These are the primary sources for clean-room implementation. Read before implementing.

- **[Game Engine Black Book: DOOM](https://fabiensanglard.net/gebbdoom/)** — Fabien Sanglard's engine analysis (rendering pipeline, BSP, visplanes, sprites)
- **[Unofficial DOOM Specs](https://doomwiki.org/wiki/WAD)** — WAD format, lump types, map data structures
- **[DOOM Source Code](https://github.com/id-Software/DOOM)** — GPL-2.0 reference (DO NOT copy — read for understanding only)
- **[DOOM1.WAD (shareware)](https://github.com/nneonneo/universal-doom)** — Test WAD, downloaded by `scripts/get-wad.sh`
- **vidya** — `content/cyrius/field_notes.toml` documents Cyrius-specific lessons from this build

## Architecture

```
src/
  main.cyr        — entry, game loop (35Hz tick), --ppm screenshot mode
  fixed.cyr       — 16.16 fixed-point math, asr() for logical-shift workaround
  tables.cyr      — 1024-entry sine table (Bhaskara I), atan2, trig wrappers
  wad.cyr         — WAD parser (IWAD/PWAD, directory, lump read/cache)
  framebuf.cyr    — 320x200 palette-indexed framebuffer, PPM output
  map.cyr         — vertices, linedefs, sidedefs, sectors, segs, subsectors, BSP nodes, things
  texture.cyr     — wall texture compositing from patches, flat cache, patch LRU cache
  render.cyr      — BSP traversal, textured wall columns, COLORMAP lighting, visplane spans, sky
  sprite.cyr      — thing sprites: distance sort, scale, clip to walls, sector lighting
  input.cyr       — terminal raw mode, WASD + arrows, bitmask action flags
  player.cyr      — movement, wall sliding collision, step height, ceiling check
  tick.cyr        — 35Hz timer via clock_gettime + nanosleep
  things.cyr      — monster AI state machine, item pickups, damage
  status.cyr      — HUD: bitmap font, health/ammo/armor/face/keys
  sound.cyr       — PC speaker tone queue via ioctl
  menu.cyr        — WAD-native title screen (TITLEPIC), main menu, skill select, M_SKULL cursor
```

## Key Constraints

- **All math is 16.16 fixed-point** — no FPU. `asr()` required for right shifts (Cyrius >> is logical)
- **No libc** — direct syscalls via `lib/io.cyr` for file I/O, framebuffer, keyboard, timer
- **Heap-allocated data** — all large buffers via `alloc()` to stay under cc2's 256KB output limit
- **Enums for constants** — saves gvar_toks slots (cc2 limit: 1024 initialized globals)
- **320x200 resolution** — palette indexed (256 colors from WAD PLAYPAL lump)
- **35Hz game tick** — matches original DOOM timing
- **WAD files not included** — `scripts/get-wad.sh` downloads DOOM1.WAD shareware for testing
- **Clean-room** — implemented from documented specs only, no id Software code copied

## Development Process

### P(-1): Research (before implementing any module)

1. Read the relevant chapter in DOOM Black Book
2. Read the Unofficial DOOM Specs for data format details
3. Check `vidya/content/cyrius/field_notes.toml` for Cyrius-specific gotchas
4. Check `vidya/content/cyrius/language.toml` for compiler constraints
5. **Security research** — for the feature area being implemented:
   a. Search for known CVEs (DOOM, PrBoom, Chocolate Doom, ZDoom, GZDoom)
   b. Search for exploit classes (buffer overflow, integer overflow, DoS, ACE)
   c. Search for malicious WAD/savegame/network/DEHACKED attack vectors
   d. Check `docs/audit/` for prior findings that apply
   e. Write findings to `docs/audit/{date}-{topic}.md`
   f. Add fix items to roadmap as next-version security tasks
   g. Fix before shipping — no new attack surface without validation
6. Document findings as comments in the source file header

### Work Loop (continuous)

1. Work phase — implement feature, fix bug, optimize
2. Build check: `cyrius build src/main.cyr build/doom`
3. Test: `./build/doom wad/DOOM1.WAD --ppm` (headless screenshot verification)
4. Run fuzz harnesses: `cyrius fuzz` (fuzz/fuzz_wad.cyr, fuzz/fuzz_fixed.cyr)
5. Binary size check — track growth per feature
6. Review — performance (22ms frame budget), correctness (compare PPM to expected), memory (heap usage)
7. Documentation — CHANGELOG, roadmap, vidya field notes for novel findings
8. Version check — VERSION, cyrius.toml, main.cyr banner all in sync

### Task Sizing

- **Low/Medium**: Batch freely — multiple items per cycle
- **Large**: Small bites — break into sub-tasks, verify each
- **If unsure**: Treat as large. Research via vidya first, then externally for information

### Refactoring

- Refactor when the code tells you to — duplication, unclear boundaries, performance
- Never refactor speculatively. Wait for the third instance
- Every refactor must pass the same build + test + fuzz gates

### Key Principles

- **Never skip benchmarks.** 22ms frame time is the target. Measure before and after.
- **Fuzz early.** The fuzz harnesses found 3 bugs that unit tests missed.
- **asr() everywhere.** Cyrius >> is logical. Every right shift on signed values must use `asr()`.
- **Lazy init guards.** `if (ptr == 0) { ptr = alloc(N); }` — prevents double-alloc and null deref.
- **Enum for constants.** Saves gvar_toks slots — use `var` only for mutable state.
- **Patch cache.** `pcache_get()` eliminates WAD I/O during rendering (200x speedup).
- **Sakshi tracing.** All error paths use `sakshi_error/warn/info` — structured timestamped logging.

## Build & Test Commands

```sh
# Build (requires Cyrius 4.0.0+)
cyrius build src/main.cyr build/doom

# Run (requires DOOM1.WAD)
./build/doom wad/DOOM1.WAD              # interactive (needs /dev/fb0 or GTK viewer)
./build/doom wad/DOOM1.WAD --ppm        # game screenshot mode (headless)
./build/doom wad/DOOM1.WAD --ppm-menu   # menu screenshots (title/main/skill)
./build/doom wad/DOOM1.WAD E1M3 --ppm   # specific map

# Download shareware WAD
sh scripts/get-wad.sh wad

# Fuzz (build + run manually)
cyrius build fuzz/fuzz_fixed.cyr build/fuzz_fixed && ./build/fuzz_fixed
cyrius build fuzz/fuzz_wad.cyr build/fuzz_wad && ./build/fuzz_wad

# One-shot run
sh scripts/run.sh
```

## DO NOT

- **Do not commit or push** — the user handles all git operations
- **NEVER use `gh` CLI** — use `curl` to GitHub API only
- Do not include WAD files in the repo (gitignored)
- Do not copy id Software source code — clean-room implementation from documented specs only
- Do not use floating point — all math is 16.16 fixed-point
- Do not use bare `>>` on signed values — use `asr()` function
- Do not skip fuzz testing before claiming robustness
- Do not allocate with `var buf[N]` for buffers > 100 bytes — use `alloc()`

## Documentation Structure

```
Root files (required):
  README.md, CHANGELOG.md, CLAUDE.md, CONTRIBUTING.md, SECURITY.md,
  CODE_OF_CONDUCT.md, LICENSE, VERSION, cyrius.toml

docs/ (required):
  architecture/overview.md — rendering pipeline, memory layout
  development/roadmap.md — per-version milestones with status

scripts/:
  get-wad.sh — download DOOM1.WAD shareware
  run.sh — one-shot build + run

fuzz/:
  fuzz_wad.cyr — WAD parser with random malformed inputs
  fuzz_fixed.cyr — fixed-point math with extreme values
```

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/). Performance claims MUST include benchmark numbers (frame time, binary size). Every version bump updates VERSION + cyrius.toml + cyrius.toml + main.cyr banner.
