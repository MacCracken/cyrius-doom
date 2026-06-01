# cyrius-doom Development Roadmap

> **Live state** (current version, sizes, dep pins, gates, in-flight slot) lives in [`state.md`](state.md), refreshed every release.
> **Historical record** (per-version shipped milestones) lives in [`completed-phases.md`](completed-phases.md).
> **CHANGELOG** ([`CHANGELOG.md`](../../CHANGELOG.md)) is the per-release detail.
>
> This file is **forward-facing only** — slots that haven't shipped yet. When a slot ships, the row moves to `completed-phases.md` and the CHANGELOG carries the detail.

---

## Slot map (forward)

| Slot | Theme | Status |
|---|---|---|
| **v0.27.x** | `lib/test.cyr` table-driven test refactor | next (deferred by the 0.27.4 fb hotfix) |
| **v0.27.5** | Upstream-fix cleanup (drop cycc 6.0.1 lockfile workaround) | gated on upstream |
| **v0.28.x** | DOOM Black Book audit (5 patches) | next minor — written against post-0.27.x modernized code |
| **v0.29.x** | Performance pass | gated on Cyrius O4 linear-scan regalloc (v6.4.x cyrius slot) |
| **v1.0.0** | Ship: full E1 + multiple display backends + AGNOS integration | future |

The current arc (**v0.27.x — language-adoption**) was re-anchored from the original "performance pass" thesis when Cyrius O4 slipped to v6.4.x and the v5.8.x language arc (sum types, `Result<T, E>`, `?`, exhaustive match) matured in stdlib. Perf-pass re-targets to v0.29.x; the Black Book audit (originally v0.25.0) re-anchors to v0.28.x so audit deltas land against the modernized code.

---

## v0.27.x — Language-adoption arc

Absorb the v5.8.x → v6.0.1 Cyrius language gains (sum types, `Result<T, E>`, `?` operator, exhaustive match, parse-only `: i64` return annotations) and the modern manifest convention into doom's actual code + toolchain. Shipped through 0.27.2 (see `completed-phases.md`).

### v0.27.x — `lib/test.cyr` table-driven test refactor

> Was slotted v0.27.4; deferred when the framebuffer geometry hotfix
> (top-band tiling on real displays) claimed 0.27.4. Re-slots into the
> next free 0.27.x.

Adopt the v5.7.43 `test_each(cases, fn)` stdlib helper. Current `tests/doom.tcyr` is ~73 asserts of hand-rolled per-case calls; table-driven cuts boilerplate and makes adding new cases cheap.

| # | Item | Detail |
|---|------|--------|
| 1 | Add `"test"` to `cyrius.cyml [deps] stdlib` | One-line manifest change |
| 2 | Convert asr / fixed-point asserts → `test_each` | ~20 asserts collapsed |
| 3 | Convert trig-table asserts → `test_each` | ~12 asserts collapsed |
| 4 | Extend test corpus once boilerplate drops | Add 20+ cases per group |

### v0.27.5 — Upstream-fix cleanup

Lands when cyrius ships the lockfile-writer fix + yukti drops its duplicate `sys_stat`. Pure cleanup — no new doom features. See [`state.md` Known issues](state.md#known-issues-workarounds-in-place) for the workarounds being removed.

| # | Item | Gated on |
|---|------|----------|
| 1 | Drop CI `--verify` lockfile-presence guard; restore `cyrius deps --verify` as unconditional gate | cycc lockfile-writer fix |
| 2 | Drop hand-populated `cyrius.lock` workflow; let `cyrius deps --lock` write canonical hashes | cycc lockfile-writer fix |
| 3 | Re-resolve deps to drop yukti `sys_stat` dup-fn warning | yukti re-bundle |
| 4 | Strike the two workaround blocks from CHANGELOG / `state.md` Known issues | both of the above |

### Watch (not yet 0.27.x slot material)

- **`texture.cyr` Result adoption** — `texture_get_column` + `texture_composite` migration deferred from v0.27.3 (the wad-side adoption already demonstrated the full `Result` + `?` + `match` pattern; texture's hot render-path call sites are gracefully handled by the existing `0`-on-fail sentinel). Revisit alongside v0.28.0's column-rendering audit — typed errors at the texture boundary will help debug visplane / column-step issues caught by the Black Book audit's PPM diffs vs chocolate-doom.
- **`lib/random.cyr`** (v5.9.x stdlib addition) — deterministic per-DOOM-tick PRNG. Doom's monster AI is already deterministic per the original game; not adopted unless RNG is wanted for intermission/menu polish.
- **`#io` effect annotations** (v5.11.x) — would document the io-side-effect set of `wad_lump_read` / `framebuf_present` / `audio_write`. No semantic change. Defer until Cyrius pins the annotation surface as stable.
- **mabda 3.0 fold / bayan-ganita carve** (v6.0.x cyrius planned) — doom uses no JSON/TOML, no-op for us.

---

## v0.28.x — DOOM Black Book Audit

Was v0.25.0; re-anchored so audit deltas are written against the modernized 0.27.x code rather than against code we'd rewrite in the language-adoption arc. Scope: chapter-by-chapter verification against Fabien Sanglard's *Game Engine Black Book: DOOM* + the Unofficial DOOM Specs, with reference PPMs from chocolate-doom as ground truth for visual comparisons.

### v0.28.0 — Rendering pipeline audit

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | Visplane span generation | Black Book ch. 9 (R_DrawPlanes) | Spans match shape + count vs reference on E1M1 / E1M3 / E1M5 |
| 2 | Column rendering | Black Book ch. 8 (R_DrawColumn) | Texture-coord stepping, light scale, COLORMAP lookup parity |
| 3 | Sky rendering | Black Book ch. 8 (R_DrawSkyColumn) | Sky never lit; column wraps at 256 |
| 4 | Masked midtexture clipping | Black Book ch. 10 | `silhouette` masking against floor/ceiling clips |
| 5 | Sprite-to-wall clipping | Black Book ch. 11 (R_DrawMaskedColumn) | Sprite spans clipped against `mfloorclip` / `mceilingclip` arrays |

### v0.28.1 — BSP + collision audit

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | BSP traversal invariants | Black Book ch. 7 + bsp lib | `bsp_point_on_side` parity with reference; front-to-back walk order |
| 2 | Subsector containment | Black Book ch. 7 | Every point in a subsector returns that subsector |
| 3 | Wall-slide collision | Black Book ch. 12 | Player slide against angled walls matches reference geometry |
| 4 | Blockmap query correctness | Unofficial Specs §4.7 | BLOCKMAP cell-list parity on E1M6 stress map |

### v0.28.2 — Game state audit

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | `R_DrawPSprite` weapon-sprite coords | Black Book ch. 11 | Weapon bob `psprite_x` / `psprite_y` matches reference frames |
| 2 | Brightness / lighting tuning | Black Book ch. 8 (COLORMAP) | A/B screenshot diff vs chocolate-doom, per-light-level |
| 3 | Episode-end intermission | Unofficial Specs §1.10 | E1M8 boss kill → text screen → bunny scroll |
| 4 | Visplane budget under stress | Unofficial Specs §10.4 | E1M9 + max-difficulty thing count: no visplane overflow |

### v0.28.3 — Security audit refresh (post-Result adoption)

| # | Item | Detail |
|---|------|--------|
| 1 | Re-walk the v0.24.0 CVE checklist | All 5 items checked under 0.27.3 `Result`-wrapped paths |
| 2 | Fuzz-corpus refresh | Add ADT-discriminator-aware mutators for the new `Result<T, E>` shape |
| 3 | Audit doc | `docs/audit/2026-XX-XX-v0.28-black-book.md` — single artifact, sectioned per 0.28.x patch |

---

## v0.29.x — Performance pass (held against Cyrius O4 regalloc)

Re-targeted from the original 0.27.0 thesis. Cyrius's compiler-optimization track has three phases that move cyrius-doom's hot paths. Hand-optimizing `fx_mul` / `asr` / column loops today would fight the codegen once O4's linear-scan register allocator lands and delivers its projected 2–3× on hot inner loops.

| # | Item | Gated on | Detail |
|---|------|----------|--------|
| 1 | Wait for **Cyrius O2** (peephole: strength reduction, flag reuse, LEA combining, aarch64 `madd`/`msub`) | Upstream | Small runtime wins on math-dense loops. Free bump once shipped. |
| 2 | Wait for **Cyrius O3** (IR-driven DCE + const prop + dead-store elim) | Upstream | Today we NOP ~293 KB of dead code (same file size). O3 strips it for real — binary genuinely shrinks toward the ~260 KB target. |
| 3 | Wait for **Cyrius O4** (linear-scan regalloc, Poletto–Sarkar; v6.4.x per cyrius roadmap) | Upstream | The single biggest win. `render_frame` projection: 2.1 ms → ≤1.0 ms. Column renderer, BSP walk, patch cache all benefit. |
| 4 | Re-bench hot paths on O2 / O3 / O4-enabled toolchain | Pending | `bench-history.csv` row per upstream phase landing, with A/B before/after to confirm the compiler wins stick. |
| 5 | Revisit manual patterns only after O4 | Pending | Any remaining 5–10 % wins from column-loop restructure are worth chasing at that point; before then, no. |

---

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1–E1M9 (shareware) | Renders all 9 maps; full gameplay loop wired | Reframe as "playable start-to-finish under skill_normal" |
| 2 | X11 display backend (native) | Not started | Direct X11 protocol, no Python bridge |
| 3 | Wayland display backend | Not started | For AGNOS desktop |
| 4 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 5 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 6 | In AGNOS initrd | Not started | Boot → shell → doom |

---

## Future

| Item | Detail |
|------|--------|
| Wolfenstein 3D mode | Raycaster renderer using Black Book patterns |
| GPU rendering via mabda | wgpu backend for hardware acceleration |
| Network multiplayer | Peer-to-peer via majra |
| PWAD support | Custom maps/mods |
| Full DOOM.WAD | Episodes 2–3 (registered version) |

---

## AgentWorld / DOOM crossover

See [`roadmap-crossover.md`](roadmap-crossover.md) — secureyeoman spatial threat visualization via the DOOM engine.
