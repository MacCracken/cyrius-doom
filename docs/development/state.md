# cyrius-doom — Current State

> **Last refresh**: 2026-06-01 (v0.27.5 — movement fixes: inverted WASD strafe + cardinal-axis moves silently dropped in `player_tick`; plus toolchain pin → 6.0.29 and the lockfile-workaround cleanup pulled forward) | **Refresh cadence**: every release (ideally bumped by the release post-hook).
>
> CLAUDE.md is preferences / process / procedures (durable). This file is **state** (volatile — binary sizes, version, in-flight slots, dep tags, gates). Anything that rots within a minor lives here. See [first-party-documentation § CLAUDE.md](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#claudemd).

---

## Current version

**[`VERSION`](../../VERSION)** = `0.27.5` (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`).

| Surface | Pin |
|---|---|
| Cyrius toolchain | `cycc 6.0.29` (in `cyrius.cyml`) |
| `[deps.bsp]` | `1.1.3` (git tag) |
| `[deps.vani]` | `0.9.4` (git tag, `core` profile — `dist/vani-core.cyr`, 22 `audio_*` symbols) |
| stdlib | `string`, `alloc`, `fmt`, `vec`, `str`, `io`, `fs`, `args`, `syscalls`, `hashmap`, `tagged`, `fnptr`, `freelist`, `process`, `sakshi` |

## Current binary

| Metric | Value |
|---|---|
| `build/doom` | **590,824 B** (+128 B vs 0.27.4 — cardinal-axis move guard restructure in `player_tick`) |
| Unreachable fns (NOP-sled today, real shrink under O3) | 985 / 291,100 B |
| Recovery target under Cyrius O3 real DCE | ~260 KB |
| Frame time | `render_frame` 2.132 ms / `+sprites` 2.136 ms (bench-history 2026-05-21, 0.27.3) |
| Hot math | `fixed_mul` 6 ns / `asr` 4 ns / `pcache_get_hit` 8 ns |

Frame-time budget: 22 ms per tick @ 35 Hz. Current: ~10× headroom.

## Gates (last green, 2026-06-01)

| Gate | Result |
|---|---|
| `cyrius deps --verify` | 27 verified, 0 failed (canonical lock, unconditional gate) |
| `cyrius build src/main.cyr build/doom` | OK, 590,824 B (no pin-drift warning) |
| `cyrius test tests/doom.tcyr` (WAD-free, CI subset) | 37/37 |
| `./build/test_doom wad/DOOM1.WAD` (full) | 73/73 |
| `./build/doom wad/DOOM1.WAD --ppm` | E1M1 + automap + intermission PPMs at 192,015 B each; map summary `V=467 L=475 SD=648 S=85 SG=732 SS=237 N=236 T=138` |
| bsp 1.1.3 standalone (upstream) | 79/79 tests, 13/13 benches sub-μs, 25K fuzz iters |
| Lint / fmt | clean across all 20 src modules + vendored libs |
| All 9 shareware maps (E1M1–E1M9) | rendering via bsp library traversal |

## Architecture surface

- **20 modules** in `src/*.cyr`:
  `main`, `fixed`, `tables`, `wad`, `framebuf`, `map`, `texture`, `render`, `sprite`, `input`, `player`, `tick`, `things`, `status`, `sound`, `audio`, `doors`, `automap`, `level`, `menu`.
- **2 vendored libs** in `lib/`:
  `bsp.cyr` (1.1.3, spatial geometry primitives) + `vani-core.cyr` (0.9.4 core profile, ALSA audio shim).
- **270 fn signatures** all `: i64`-annotated (v0.27.2 sweep — parse-only, ABI-identical).
- **`Result<T, E>` adoption** at the WAD IO/parse boundary (v0.27.3): `WadError` typed-error enum, `wad_open` returns Result, `wad_read_lump_r` / `wad_read_lump_into_r` parallel forms, `?` + exhaustive `match` at the boot boundary in `doom_main`.

## In-flight slot map

Current arc: **v0.27.x language-adoption** (was perf-pass; perf-pass re-targeted to v0.29.x since Cyrius O4 slipped to v6.4.x).

| Slot | Status | What |
|---|---|---|
| **v0.27.0** | shipped 2026-05-21 | Cyrius 5.7.48 → 6.0.1 lift; vani 0.9.1 → 0.9.3; manifest modernization; CI patra-style installer |
| **v0.27.1** | shipped 2026-05-21 | bsp 1.1.2 → 1.1.3 + vani 0.9.3 → 0.9.4 dep-tag re-pin |
| **v0.27.2** | shipped 2026-05-21 | `: i64` return-type annotation sweep on all 20 modules (270 sigs, ABI-identical) |
| **v0.27.3** | shipped 2026-05-21 | `Result<T, E>` adoption at the WAD IO/parse boundary: `WadError` enum, `wad_open` returns Result, `wad_read_lump_r` parallels, `?` + exhaustive `match` in `doom_main` boot path |
| **v0.27.4** | shipped 2026-06-01 | Framebuffer geometry fix — `framebuf_init` queries real `/dev/fb0` `xres`/`yres`/`bpp`/`line_length` via `FBIOGET_{V,F}SCREENINFO`; `framebuf_flip` integer-scales + center-blits at true pitch/bpp. Fixes top-band tiling on real displays. Dead `rgb_buf` dropped |
| **v0.27.5** | shipped 2026-06-01 | Movement fixes — (1) WASD strafe vectors inverted in `player_tick` (`A`/`D` swapped), (2) cardinal-axis moves dropped by a `&&` guard, now `\|\|`. Plus toolchain pin → 6.0.29 + lockfile cleanup (canonical 27-entry lock, CI guard dropped, known-issue #1 resolved) pulled forward from v0.27.6 |
| **v0.27.6** | gated | yukti `sys_stat` dup-fn cleanup — drop the duplicate-fn warning once yukti re-bundles without `sys_stat` (did not fire under 6.0.29; re-confirm). Gated on a yukti rebundle |
| **v0.27.x** | deferred | `lib/test.cyr` table-driven test refactor (`test_each` helper, ~32 asserts collapsed) — bumped by the 0.27.4/0.27.5 hotfixes |

After 0.27.x: **v0.28.x** Black Book audit (was 0.25.0, re-anchored — written against the modernized post-language-arc code). Then **v0.29.x** performance pass against Cyrius O4 regalloc.

## Known issues (workarounds in place)

| # | Issue | Workaround |
|---|---|---|
| 2 | `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition wins)` — stdlib defines `sys_stat` and vani's transitively-bundled yukti also defines it (unannotated). | Codegen-identical, warning-only. Did not fire under cycc 6.0.29 (worth re-confirming), but kept tracked until yukti drops `sys_stat` from its dist surface. Gated on a yukti rebundle. |

> Issue #1 (cycc 6.0.1 lockfile-writer regression — empty `cyrius.lock`) was **resolved in 0.27.5**: toolchain pin bumped to 6.0.29, whose `cyrius deps` writes a canonical 27-entry lock. The `sha256sum` hand-population + CI empty-lock guard are gone; `cyrius deps --verify` is unconditional again.

## Dependency lineage

`cyrius-doom` **composes**: `bsp` (spatial geometry) + `vani` (audio, transitional — will be replaced by **dhvani** once the Rust→Cyrius port lands; `audio_*` shape is the migration target so `src/audio.cyr` stays ABI-stable across the swap).

Stdlib pulled in by `cyrius.cyml [deps]`; transitive resolution refreshes `yukti` / `patra` / `sakshi` through vani's `[deps.*]` overrides.

## Consumers

- **AGNOS kernel** — initrd demo
- **kiran** — game engine reference
- **vidya** — field notes / language research

## Verification

- `wad/DOOM1.WAD` (shareware, downloaded via `scripts/get-wad.sh`) — not in repo, gitignored.
- Headless: `--ppm` mode (no /dev/fb0 needed).
- Interactive: requires `/dev/fb0` or the GTK3 bridge (`scripts/x11view.py`).

---

*Refresh procedure: bump the per-slot status above when a version ships, update the binary metrics from `bench-history.csv` + `stat -c '%s' build/doom`, and re-anchor "Last refresh" in the header. Historical release narrative lives in [`completed-phases.md`](completed-phases.md), not here.*
