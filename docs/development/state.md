# cyrius-doom — Current State

> **Last refresh**: 2026-06-10 (v0.28.4 — gameplay correctness: render+sprite/movement 90° angle-convention unification, one-sided-wall collision, Linux `termios` VMIN blocking-read (loop froze between keystrokes), perspective-correct wall depth (F22, pulled fwd from 0.29.x), sakshi log routing; toolchain pin → 6.1.29. The 0.28.1–.3 slot rows (AGNOS bring-up arc) — skipped during those patches — were backfilled from `CHANGELOG.md` in this refresh.) | **Refresh cadence**: every release (ideally bumped by the release post-hook).
>
> CLAUDE.md is preferences / process / procedures (durable). This file is **state** (volatile — binary sizes, version, in-flight slots, dep tags, gates). Anything that rots within a minor lives here. See [first-party-documentation § CLAUDE.md](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#claudemd).

---

## Current version

**[`VERSION`](../../VERSION)** = `0.28.4` (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`).

| Surface | Pin |
|---|---|
| Cyrius toolchain | `cycc 6.1.29` (in `cyrius.cyml`; bumped from 6.0.83 — the local launchers all resolve newest cycc regardless of pin, so the pin now matches the only cycc that actually runs) |
| `[deps.bsp]` | `1.1.3` (git tag) |
| `[deps.vani]` | `0.9.4` (git tag, `core` profile — `dist/vani-core.cyr`, 22 `audio_*` symbols) |
| stdlib | `string`, `alloc`, `fmt`, `vec`, `str`, `io`, `fs`, `args`, `syscalls`, `hashmap`, `tagged`, `fnptr`, `freelist`, `process`, `sakshi` |

## Current binary

| Metric | Value |
|---|---|
| `build/doom` | **600,848 B** (cycc 6.1.29, clean `./lib/`; not directly comparable to the 0.28.0 592,456 B — toolchain codegen + bundled stdlib changed between pins) |
| Unreachable fns (NOP-sled today, real shrink under O3) | 997 / 293,561 B |
| Recovery target under Cyrius O3 real DCE | ~260 KB |
| Frame time | `render_frame` 2.520 ms / `+sprites` 2.502 ms (bench-history 2026-06-10, 0.28.4, cycc 6.1.29, clean `./lib/`; F22 perspective depth+U complete). Cross-version comparison vs the 0.28.0 ~1.78 ms is **not valid** — the cycc pin changed (6.0.83 → 6.1.29) so the delta mixes codegen + 0.28.1–.4 code; F22 perspective depth+U is per-column ≈neutral. ~8.7× headroom on the 22 ms budget. |
| Hot math | `fixed_mul` 6 ns / `asr` 4 ns / `texture_get_column` ~725 ns / `pcache_get_hit` 7 ns |

Frame-time budget: 22 ms per tick @ 35 Hz. Current: ~12× headroom.

## Gates (last green, 2026-06-10)

| Gate | Result |
|---|---|
| `cyrius deps --verify` | **37 verified, 0 failed** on a clean resolve (`rm -rf lib && cyrius deps`). `./lib/` is a gitignored build artifact regenerated from the pinned 6.1.29 stdlib + git-override deps; the committed lock (37 entries) matches it. CI runs `cyrius deps` then this gate. |
| `cyrius build src/main.cyr build/doom` | OK, 600,848 B (cycc 6.1.29 = pin; clean `./lib/`; no drift warning) |
| `cyrius test tests/doom.tcyr` (WAD-free, CI subset) | 37/37 |
| `./build/test_doom wad/DOOM1.WAD` (full) | 73/73 |
| `fuzz_wad` / `fuzz_fixed` | **not re-run this cycle** — 0.28.4 touched render/player/input/log, not the WAD parser or `fixed.cyr`; last green at 0.28.0 (1k / 50k clean). |
| `./build/doom wad/DOOM1.WAD --ppm` | E1M1 + automap + intermission PPMs at 192,015 B each; map summary `V=467 L=475 SD=648 S=85 SG=732 SS=237 N=236 T=138`. **View now faces the map-intended direction** (the prior wall transform rendered ~90° rotated). |
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

Current arc: **v0.28.x graphics** (review/hardening/parity/performance). The v0.27.x language-adoption arc is complete; the perf micro-pass remains re-targeted to v0.29.x (gated on Cyrius O4 regalloc, v6.4.x).

| Slot | Status | What |
|---|---|---|
| **v0.27.0** | shipped 2026-05-21 | Cyrius 5.7.48 → 6.0.1 lift; vani 0.9.1 → 0.9.3; manifest modernization; CI patra-style installer |
| **v0.27.1** | shipped 2026-05-21 | bsp 1.1.2 → 1.1.3 + vani 0.9.3 → 0.9.4 dep-tag re-pin |
| **v0.27.2** | shipped 2026-05-21 | `: i64` return-type annotation sweep on all 20 modules (270 sigs, ABI-identical) |
| **v0.27.3** | shipped 2026-05-21 | `Result<T, E>` adoption at the WAD IO/parse boundary: `WadError` enum, `wad_open` returns Result, `wad_read_lump_r` parallels, `?` + exhaustive `match` in `doom_main` boot path |
| **v0.27.4** | shipped 2026-06-01 | Framebuffer geometry fix — `framebuf_init` queries real `/dev/fb0` `xres`/`yres`/`bpp`/`line_length` via `FBIOGET_{V,F}SCREENINFO`; `framebuf_flip` integer-scales + center-blits at true pitch/bpp. Fixes top-band tiling on real displays. Dead `rgb_buf` dropped |
| **v0.27.5** | shipped 2026-06-01 | Movement fixes — (1) WASD strafe vectors inverted in `player_tick` (`A`/`D` swapped), (2) cardinal-axis moves dropped by a `&&` guard, now `\|\|`. Plus toolchain pin → 6.0.29 + lockfile cleanup (canonical 27-entry lock, CI guard dropped, known-issue #1 resolved) pulled forward from v0.27.6 |
| **v0.27.6** | gated | yukti `sys_stat` dup-fn cleanup — drop the duplicate-fn warning once yukti re-bundles without `sys_stat`. Did not fire under 6.0.29 or 6.0.83; likely moot. Gated on a yukti rebundle |
| **v0.28.0** | shipped 2026-06-07 | Graphics review/hardening/audit/performance. Patch-decoder bounds propagation (weapon/sprite/HUD+menu — F01/F02/F03 — and TEXTURE1 — F19), visplane heap-OOB-**write** fix + visible E1M1 corruption fix (F17), dead `render_flat_span` delete (F16), flat-fill inline ~15% `render_frame` (F11), weapon-lump cache (F14). Toolchain pin → 6.0.83. 8 of 20 verified findings shipped; rest re-slotted across 0.28.x. Audit: `docs/audit/2026-06-07-v0.28-graphics-hardening.md` |
| **v0.28.1** | shipped 2026-06-08 | **AGNOS target support** — first port. OS interactions branched under `CYRIUS_TARGET_AGNOS`: inlined agnos syscall numbers (collide with Linux), portable timing (`uptime_ms`/`sleep_ms`), fb queries (`fbinfo`#38/`blit`#39), WAD memory-load (no `lseek`), exit/input/sound paths. Linux build byte-identical. |
| **v0.28.2** | shipped 2026-06-08 | **DOOM renders on AGNOS** — the 584 KB ELF ring-3 exec's from disk, loads the 4.2 MB `DOOM1.WAD`, builds the palette, and blits a 240-colour frame to the hardware framebuffer via `fbinfo`#38 / `blit`#39. (Unblocked by two AGNOS kernel fixes: PMM→24 MB, phys-page zeroing ≥16 MB.) |
| **v0.28.3** | shipped 2026-06-09 | **AGNOS keyboard input** via `kbscan`#42 (non-blocking raw Set-1 scancode poll, make/break decode, persistent `key_state`) — DOOM playable past the title screen. WASD/arrows/space/E/F/R/Tab/1–7/Q/Esc. |
| **v0.28.4** | shipped 2026-06-10 | Gameplay correctness. (1) render+sprite/movement **90° angle-convention unification** — `render_transform_vertex` + sprite transforms used depth `dy·cos−dx·sin` (north@0) while movement/hitscan/floors/map use `(cos,sin)` (east@0); walls/sprites now match. (2) **one-sided-wall collision** — `player_check_linedef` treated flagless one-sided walls as passable. (3) **Linux `termios` VMIN** offset off-by-one (`c_line` byte) left VMIN=1 → blocking `read` → loop froze between keystrokes. (4) **perspective-correct wall + masked-seg depth** (interpolate scale not z) — this is **F22**, pulled forward from 0.29.x; texture-U half (F22b) also landed. (5) **sakshi log routing** for boot diagnostics. Toolchain pin → 6.1.29 (committed `cyrius.lock` regenerated against the new stdlib → 37 entries). |

### Forward 0.28.x slots (re-slotted at the 0.28.4 cut — the AGNOS arc consumed 0.28.1–.3 and gameplay correctness took 0.28.4, so the Black Book parity/perf themes shift to ≥ 0.28.5)

| Slot | Theme |
|---|---|
| **v0.28.5** | Visplane pool rewrite (F08) — keystone Black Book parity; subsumes F13. Rides the `lib/test.cyr` `test_each` refactor (was 0.27.x) |
| **v0.28.6** | Sprite/masked-seg depth-aware clipping (F07 per-drawseg silhouettes → F05b → F05 clip_solid) |
| **v0.28.7** | Sky + wall-mapping parity (F09 horizon anchoring) |
| **v0.28.8** | Structural perf (F12 sidedef/sector index cache, F15 thing-sector cache) — bench-gated |
| **v0.28.9–.11** | The original Black Book sub-audits: BSP+collision (.9), game-state (.10), security-refresh (.11, partly discharged early by F01/F02/F03/F19/F17 + the 0.28.4 collision fix) |

After 0.28.x: **v0.29.x** O4 micro-perf pass + deep renderer fidelity (F06 native-scale midtex). **F22 perspective-correct U/depth shipped early in 0.28.4** (pulled forward off this list). See [`roadmap.md`](roadmap.md).

## Known issues (workarounds in place)

| # | Issue | Workaround |
|---|---|---|
| 2 | `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition wins)` — stdlib defines `sys_stat` and vani's transitively-bundled yukti also defines it (unannotated). | Codegen-identical, warning-only. Did not fire under cycc 6.0.29 or 6.0.83, but kept tracked until yukti drops `sys_stat` from its dist surface. Gated on a yukti rebundle. |
> Issue #1 (cycc 6.0.1 lockfile-writer regression — empty `cyrius.lock`) was **resolved in 0.27.5**: toolchain pin bumped to 6.0.29, whose `cyrius deps` writes a canonical lock; `cyrius deps --verify` is unconditional again. The 0.28.4 pin bump to 6.1.29 changed the bundled stdlib, so the committed lock was **regenerated** against it (`rm -rf lib && cyrius deps` → **37 entries**, verify 37/0). `./lib/` is a gitignored build artifact, so the lock must always match the pinned toolchain's stdlib — regenerate + commit it whenever the pin moves. (An earlier 0.28.4 attempt mis-diagnosed this as a "writer regression" and added a CI lock-restore guard; that guard verified the *stale* lock against the *new* stdlib and broke CI — reverted.)

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
