# cyrius-doom — Current State

> **Last refresh**: 2026-05-21 (v0.27.2 — public-fn `: i64` annotation sweep) | **Refresh cadence**: every release (ideally bumped by the release post-hook).
>
> CLAUDE.md is preferences / process / procedures (durable). This file is **state** (volatile — binary sizes, version, in-flight slots, dep tags, gates). Anything that rots within a minor lives here. See [first-party-documentation § CLAUDE.md](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#claudemd).

---

## Current version

**[`VERSION`](../../VERSION)** = `0.27.2` (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`).

| Surface | Pin |
|---|---|
| Cyrius toolchain | `cycc 6.0.1` (in `cyrius.cyml`) |
| `[deps.bsp]` | `1.1.3` (git tag) |
| `[deps.vani]` | `0.9.4` (git tag, `core` profile — `dist/vani-core.cyr`, 22 `audio_*` symbols) |
| stdlib | `string`, `alloc`, `fmt`, `vec`, `str`, `io`, `fs`, `args`, `syscalls`, `hashmap`, `tagged`, `fnptr`, `freelist`, `process`, `sakshi` |

## Current binary

| Metric | Value |
|---|---|
| `build/doom` | **585,224 B** |
| Unreachable fns (NOP-sled today, real shrink under O3) | 982 / 292,798 B |
| Recovery target under Cyrius O3 real DCE | ~260 KB |
| Frame time | `render_frame` 2.114 ms / `+sprites` 2.127 ms (bench-history 2026-05-21) |
| Hot math | `fixed_mul` 6 ns / `asr` 4 ns / `pcache_get_hit` 7 ns |

Frame-time budget: 22 ms per tick @ 35 Hz. Current: ~10× headroom.

## Gates (last green, 2026-05-21)

| Gate | Result |
|---|---|
| `cyrius deps --verify` | 5 verified, 0 failed |
| `cyrius build src/main.cyr build/doom` | OK, 585,224 B |
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

## In-flight slot map

Current arc: **v0.27.x language-adoption** (was perf-pass; perf-pass re-targeted to v0.29.x since Cyrius O4 slipped to v6.4.x).

| Slot | Status | What |
|---|---|---|
| **v0.27.0** | shipped 2026-05-21 | Cyrius 5.7.48 → 6.0.1 lift; vani 0.9.1 → 0.9.3; manifest modernization; CI patra-style installer |
| **v0.27.1** | shipped 2026-05-21 | bsp 1.1.2 → 1.1.3 + vani 0.9.3 → 0.9.4 dep-tag re-pin |
| **v0.27.2** | shipped 2026-05-21 | `: i64` return-type annotation sweep on all 20 modules (270 sigs, ABI-identical) |
| **v0.27.3** | next | `Result<T, E>` adoption in `wad.cyr` / `texture.cyr` / `render.cyr` error paths; `?` operator on `r_init` / `main` cascades |
| **v0.27.4** | queued | `lib/test.cyr` table-driven test refactor (`test_each` helper, ~32 asserts collapsed) |
| **v0.27.5** | gated | Upstream-fix cleanup — drop CI lockfile-guard + hand-populated `cyrius.lock` workaround once cycc lockfile-writer regression fix lands; drop yukti dup-fn warning once yukti re-bundles |

After 0.27.x: **v0.28.x** Black Book audit (was 0.25.0, re-anchored — written against the modernized post-language-arc code). Then **v0.29.x** performance pass against Cyrius O4 regalloc.

## Known issues (workarounds in place)

Both inherited from cycc 6.0.1; tracked under v0.27.5 cleanup:

| # | Issue | Workaround |
|---|---|---|
| 1 | `cyrius deps` writes empty `cyrius.lock` for our manifest shape (cycc 6.0.1 lockfile-writer regression) | Hand-populate via `sha256sum lib/{vani-core,bsp,yukti,patra,sakshi}.cyr > cyrius.lock`. CI `--verify` step guarded on a populated lockfile so it doesn't trivially pass against an empty resolver write. |
| 2 | `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition wins)` — cycc 6.0.1 stdlib defines `sys_stat` and vani's transitively-bundled yukti 2.2.4 also defines it (unannotated). | Codegen-identical, warning-only. Drops when yukti drops its `sys_stat` from its dist surface. |

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
