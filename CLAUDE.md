# Cyrius DOOM — Claude Code Instructions

## Project Identity

**cyrius-doom** (homage to id Software's DOOM, 1993) — Clean-room DOOM engine in Cyrius. Direct framebuffer, no libc, no SDL, kernel syscalls only.

- **Type**: Standalone game binary / kernel demo
- **License**: GPL-3.0-only (clean-room implementation)
- **Language**: Cyrius (native, compiled via cycc 6.0.1)
- **Version**: SemVer, single source of truth at `VERSION`
  (referenced via `version = "${file:VERSION}"` in `cyrius.cyml`)
- **Binary size**: 585,320 B (20 modules + vani-core + bsp);
  585,320 → ~260 KB recovery gated on Cyrius phase O3 real DCE.
  Renders at ~3.9 ms/frame.
- **Status**: v0.27.0 — Cyrius 5.7.48 → 6.0.1 lift opens the
  0.27.x **language-adoption arc** (was "perf pass held against O4
  regalloc"; perf-pass re-targets to 0.29.x as O4 slipped to
  cyrius v6.4.x). 0.27.0 covers: cyrius pin bump (picks up v5.8.x
  sum-types / `Result<T,E>` / `?` / exhaustive-match, v5.11.x
  annotation arc, v6.0.0 `cyrc → cybs` + `cc5 → cycc` rename,
  v6.0.1 stdlib-path hotfixes); vani 0.9.1 → 0.9.3 (annotation
  pass — parse-only, ABI-identical); manifest modernization
  (`cyrius.toml` + `cyrb.toml` retired, single `cyrius.cyml`
  with `${file:VERSION}` template — matches patra/vani/sakshi/
  mihi); CI lifted to patra-style installer (pre-flight HTTP
  gate; version-pinned install layout); `cyrius deps --verify`
  guarded on populated lockfile (workaround for known cycc 6.0.1
  lockfile-writer regression). Binary 565,856 → 585,320 B
  (+19,464 B honest growth-tax from v5.11.x annotation rt-table
  + v5.8.x sum-type emit). BSP 1.1.2 (0.27.1 bumps to 1.1.3
  once user publishes upstream tag). E1M6 map-cap fix
  (MAP_MAX_SSECTORS 512→1024 from 0.24.6). Security hardened.
  Full gameplay loop, DOOM-accurate lighting, masked midtextures,
  animated walls/flats/sprites, WAD-native HUD + menus +
  intermission, ALSA audio, weapon switching + bob, doors/lifts,
  automap, level transitions (E1M1–E1M9 all rendering). CVE
  audit: 5 findings fixed. **vani is transitional**: replaces
  retiring cyrius stdlib `audio` (5.8.0); will itself be replaced
  by **dhvani** once that port lands. **Next**: 0.27.1 dep-tag
  re-pin (bsp 1.1.3 + vani 0.9.4 — blocked on upstream tags);
  0.27.2 `: i64` annotation sweep on public surface; 0.27.3
  `Result<T,E>` adoption in `wad.cyr` / `texture.cyr` /
  `render.cyr` error paths; 0.27.4 `lib/test.cyr` table-driven
  refactor. **0.28.x** = DOOM Black Book Audit (was 0.25.0,
  re-anchored). **0.29.x** = performance pass against Cyrius
  O4 regalloc.
- **Genesis repo**: [agnosticos](https://github.com/MacCracken/agnosticos)
- **Philosophy**: [AGNOS Philosophy](https://github.com/MacCracken/agnosticos/blob/main/docs/philosophy.md)
- **Standards**: [First-Party Standards](https://github.com/MacCracken/agnosticos/blob/main/docs/development/applications/first-party-standards.md)

## Consumers

AGNOS kernel (initrd demo), kiran (game engine reference), vidya (field notes / language research)

**Composes**: bsp (spatial geometry, git dep tag 1.1.2 — 0.27.1 pins 1.1.3; vendored as `lib/bsp.cyr`), vani (audio, git dep tag 0.9.3 — 0.27.1 pins 0.9.4; `dist/vani-core.cyr` profile, 22 `audio_*` symbols), sakshi (tracing, via cyrius stdlib)

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
8. Version check — VERSION (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`), `src/main.cyr` banner in sync

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
# Build (requires Cyrius 5.5.0+)
cyrius build src/main.cyr build/doom

# Release build: NOPs dead functions in-place (binary size unchanged,
# but ~49KB of unreachable code becomes inert — used by release.yml).
CYRIUS_DCE=1 cyrius build src/main.cyr build/doom

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
  CODE_OF_CONDUCT.md, LICENSE, VERSION, cyrius.cyml

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

Follow [Keep a Changelog](https://keepachangelog.com/). Performance claims MUST include benchmark numbers (frame time, binary size). Every version bump updates VERSION (single source of truth — `cyrius.cyml` resolves it via `${file:VERSION}`) + `src/main.cyr` banner.
