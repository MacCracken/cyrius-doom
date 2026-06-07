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
| **v0.28.1** | Visplane pool rewrite (Black Book ch.9 / F08); rides the `lib/test.cyr` `test_each` refactor | next |
| **v0.28.2** | Sprite + masked-seg depth-aware clipping (F07 / F05b / F05) | after 0.28.1 |
| **v0.28.3** | Sky + wall-mapping parity (F09) | queued |
| **v0.28.4** | Structural perf — sidedef/sector index + thing-sector caches (F12 / F15) | queued, bench-gated |
| **v0.28.5–.7** | Original Black Book sub-audits re-slotted: BSP+collision, game-state, security-refresh | queued |
| **v0.28.x** | yukti `sys_stat` dup-fn cleanup | gated on yukti rebundle (likely moot) |
| **v0.29.x** | O4 micro-perf pass + deep renderer fidelity (F06 native-scale midtex, F22 perspective-correct U/depth) | gated on Cyrius O4 regalloc (v6.4.x) |
| **v1.0.0** | Ship: full E1 + multiple display backends + AGNOS integration | future |

> **v0.28.0 shipped 2026-06-07** (graphics review/hardening/audit/performance) — moved to [`completed-phases.md`](completed-phases.md). At the user's direction this graphics pass *became* 0.28.0, and the previously-roadmapped Black Book audit + lingering 0.27.x housekeeping were pushed **behind** it (re-slotted below).

The current arc is **v0.28.x — graphics** (review / hardening / parity / performance). The language-adoption arc (v0.27.x) is complete. v0.28.0 was anchored on a multi-agent audit of the render path (`docs/audit/2026-06-07-v0.28-graphics-hardening.md`); it shipped the memory-safety hardening + safe perf, and the parity items it surfaced now drive 0.28.1–0.28.7. The O4-gated perf micro-pass and the deepest renderer-fidelity work remain at v0.29.x.

---

## v0.28.x — Graphics arc

The graphics review/hardening/audit/performance pass **became v0.28.0** (shipped — see `completed-phases.md`). The previously-roadmapped DOOM Black Book audit (originally v0.25.0, re-anchored to v0.28.x) and the lingering language-arc housekeeping were pushed **behind** it, re-slotted below. Scope across the arc: close the render-path parity gaps the 0.28.0 audit surfaced, chapter-by-chapter against Fabien Sanglard's *Game Engine Black Book: DOOM* + the Unofficial DOOM Specs, with PPM diffs as ground truth. Finding IDs (Fnn) reference [`docs/audit/2026-06-07-v0.28-graphics-hardening.md`](../audit/2026-06-07-v0.28-graphics-hardening.md).

### v0.28.1 — Visplane pool rewrite (keystone parity)

The per-row single-`(x1,x2,flat,light)` visplane model can't represent two flats on one screen row, and the farthest seg to touch a row wins (BSP is front-to-back) — so a farther sector's flat can overwrite a nearer one. Replace with a real visplane pool.

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | Visplane pool keyed by (flat, lightnum, height) | Black Book ch. 9 (R_FindPlane/R_DrawPlanes) | per-column `top[]`/`bottom[]`; F08 |
| 2 | Drop redundant per-cell flat/light re-stores | — | folds into the pool; F13 |
| 3 | `lib/test.cyr` `test_each` refactor (rides along) | v5.7.43 stdlib | ~32 asserts collapsed; the rewrite needs a healthy PPM-diff harness |
| 4 | Span shape + count vs reference | E1M1 / E1M3 / E1M5 | flag-gated, PPM-diffed |

### v0.28.2 — Sprite + masked-seg depth-aware clipping

The single collapsed `clip_top`/`clip_bottom` pair holds the *farthest* opening at draw time, so sprites and masked midtextures can't be clipped against walls at the right depth. Build the per-drawseg silhouette infrastructure, then the dependent fixes.

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | Per-drawseg `mfloorclip`/`mceilingclip` recorded at seg depth | Black Book ch. 11 | F07; foundation for the rest |
| 2 | Masked-seg clip against the wall silhouette | Black Book ch. 10 | F05b (rides on F07) |
| 3 | Masked-seg `clip_solid` over-paint guard | — | F05 — correct **only** once F07/F05b land; the bare guard over-clips the "near grate / far wall" case (probed no-op on E1M1–E1M7, so 0.28.0 correctly skipped it) |
| 4 | Sprite-vs-sprite + sprite-vs-masked clipping | Black Book ch. 11 | completeness |

### v0.28.3 — Sky + wall-mapping parity

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | Sky horizon anchoring + corrected angular scale | Black Book ch. 8 (R_DrawSkyColumn) | F09; sky-Y to the horizon (not per-column `ct`), per-column view-angle table; never lit |
| 2 | Brightness / lighting A-B vs reference | Black Book ch. 8 (COLORMAP) | per-light-level PPM diff (carries the F25 verification forward) |

### v0.28.4 — Structural performance (O4-independent, bench-gated)

| # | Item | Detail |
|---|------|--------|
| 1 | Per-sidedef texture + per-sector flat index cache at map load | F12 — removes 3 `texture_find` + 2 `flat_find` linear scans per seg/frame |
| 2 | Per-thing sector/floor-height cache | F15 — re-walk BSP only when the thing moves |
| 3 | Automap line pre-clip | F26 — optional; negligible (overlay, not hot path) |

### v0.28.5 — BSP + collision audit (original Black Book sub-phase)

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | BSP traversal invariants | Black Book ch. 7 + bsp lib | `bsp_point_on_side` parity; front-to-back walk order |
| 2 | Subsector containment | Black Book ch. 7 | every point in a subsector returns that subsector |
| 3 | Wall-slide collision | Black Book ch. 12 | slide against angled walls matches reference |
| 4 | Blockmap query correctness (+ C3 BLOCKMAP bounds) | Unofficial Specs §4.7 | cell-list parity on E1M6; re-verify the 2026-04-13 C3 finding |

### v0.28.6 — Game state audit (original Black Book sub-phase)

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | `R_DrawPSprite` weapon-sprite coords | Black Book ch. 11 | weapon bob `psprite_x`/`psprite_y` vs reference |
| 2 | Episode-end intermission | Unofficial Specs §1.10 | E1M8 boss kill → text → bunny scroll |
| 3 | Visplane budget under stress | Unofficial Specs §10.4 | E1M9 + max things: no overflow (bounded by the F08 pool) |

### v0.28.7 — Security audit refresh

Partly discharged early by 0.28.0 (F01/F02/F03/F19 patch-decode propagation + F17 OOB-write fix). Remaining:

| # | Item | Detail |
|---|------|--------|
| 1 | Re-walk the 2026-04-13 CVE checklist | confirm C3 (BLOCKMAP) + H1 (WAD lump size) under current code |
| 2 | Fuzz-corpus refresh | add patch / TEXTURE1 / ADT-discriminator mutators to exercise the F01/F02/F03/F19 decoders directly |
| 3 | Bench formatter fix | `benches/doom.bcyr` sub-ms avg formatter (prints min > max) |

### Gated / watch (carried forward)

- **yukti `sys_stat` dup-fn cleanup** — strike known-issue #2 once yukti re-bundles without `sys_stat`. Did not fire under 6.0.29 or 6.0.83; likely already moot. Gated on a yukti rebundle. Does not block any 0.28.x graphics slot.
- **`texture.cyr` Result adoption** — `texture_get_column` typed errors; revisit alongside the 0.28.1 visplane rewrite.
- **`lib/random.cyr`** (v5.9.x) — deterministic per-tick PRNG; not adopted unless wanted for intermission/menu polish.
- **`#io` effect annotations** (v5.11.x) — defer until Cyrius pins the annotation surface as stable.
- **mabda 3.0 fold / bayan-ganita carve** — doom uses no JSON/TOML, no-op for us.

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
| 6 | Native-scale midtexture w/ peg anchoring | Needs an `rw_scale` path | F06 — deep renderer fidelity; the engine is uniformly stretch-to-section today, so there's no scale path to hook onto |
| 7 | Perspective-correct U / depth across segs | Renderer rework | F22 — engine is consistently affine (screen-linear frac/depth/U); a half-fix is worse than none |

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
