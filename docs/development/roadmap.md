# cyrius-doom Development Roadmap

> **v0.27.2** — 585,224 B (cycc 6.0.1 + vani 0.9.4 `core` profile
> + bsp 1.1.3; byte-identical to 0.27.1 — the v5.11.x annotation
> pass is parse-only and produces zero codegen delta; long-term
> recovery to ~260 KB still gated on Cyrius O3 real DCE). 20
> modules + vendored `lib/bsp.cyr` + vendored `lib/vani-core.cyr`
> (29 KB single-module bundle, 22 `audio_*` symbols). Every fn
> in `src/*.cyr` now carries a `: i64` return-type annotation
> (270 sigs total — 269 single-line + 1 multi-line). Documents
> return contracts inline; sets up 0.27.3's `Result<T, E>`
> retrofit on the IO/parse boundary without further signature
> churn. Full gameplay loop, DOOM-accurate lighting, 9/9
> shareware maps render via bsp library traversal, security
> hardened (CVE audit: 5/5 fixed). Manifest modernized: single
> `cyrius.cyml` with `version = "${file:VERSION}"`; legacy
> `cyrius.toml` + `cyrb.toml` retired (matches patra/vani/
> sakshi/mihi). CI lifted to patra-style toolchain installer;
> `cyrius deps --verify` guarded on populated lockfile pending
> the upstream cycc 6.0.1 lockfile-writer regression fix. vani
> is **transitional** — will be replaced by dhvani once the
> Rust→Cyrius port lands. CI runs the WAD-free 37-assert test
> subset + DCE on release builds. 73/73 cyrius-doom tests,
> 79/79 bsp tests, 76K fuzz iters total. fmt + lint clean.
> Bench row (0.27.2): `render_frame` 2.114 ms / `+sprites`
> 2.127 ms — variance-level vs 0.27.1 (2.146 / 2.141), as
> predicted for a parse-only annotation sweep. **Next**: 0.27.3
> `Result<T,E>` adoption in wad/render error paths; 0.27.4
> `lib/test.cyr` table-driven refactor; 0.27.5 upstream-fix
> cleanup. 0.28.x = Black Book audit; 0.29.x = perf pass gated
> on Cyrius O4.

## Completed

| Version | Milestone |
|---------|-----------|
| v0.1.0 | Scaffolded, architecture defined |
| v0.5.0 | WAD parser, BSP walls, game loop (56KB) |
| v0.6.0 | Sakshi tracing, asr() fix (WALLS VISIBLE) |
| v0.7.0 | Wall textures, COLORMAP lighting |
| v0.8.0 | Floor/ceiling flat textures |
| v0.9.0 | Sprites (monsters, items, decorations) |
| v0.10.0 | All 13 modules, patch cache (200x speedup) |
| v0.11.0 | Test suite (73), benchmarks (14), docs audit |
| v0.12.0 | Audit fixes (fake contrast, pegging, rotation, light scale) |
| v0.13.0 | Weapon sprite, BLOCKMAP collision |
| v0.14.0 | Doors, lifts, tagged sectors, walk-over triggers |
| v0.15.0 | Automap (TAB toggle, Bresenham lines) |
| v0.16.0 | Doomguy face, HUD polish, extended specials |
| v0.17.0 | Level transitions (E1M1→E1M9, secret exits) |
| v0.18.0 | WAD-native status bar (STBAR, STTNUM, STYSNUM, STFST) |
| v0.18.1 | Ammo totals polish, softened yellow, regression tests |
| v0.18.2 | Weapon hand positioning, CI lint/format, cc3 3.3.13 verified |
| v0.19.0 | ALSA audio via stdlib, shravan 2.0.0, 12 WAD sounds cached |
| v0.19.1 | Audio module, GTK3 display bridge, health/armor HUD fix |
| v0.20.0 | Dep integration, WAD-native menus, weapon switching/firing, sprite animation, refactoring |
| v0.21.0 | DOOM-accurate lighting, masked midtextures, animated walls, intermission screen |
| v0.22.0 | Gameplay: ammo, hitscan, death/respawn, key cards, locked doors |
| v0.23.0 | Polish: weapon bob, sound triggers, HUD ammo display, armor absorption |
| v0.23.1 | Cyrius 4.0.0 modernization (~300 changes: +=, negative literals) |
| v0.23.2 | P(-1) hardening: termios iflag bitmask fix, full audit clean |
| v0.24.0 | Security: CVE audit, map/texture/blockmap bounds validation, WAD read zero-fill |
| v0.24.1 | Short-circuit cleanup (15+ nested-if → && chains), Cyrius 4.4.3 verified |
| v0.24.2–0.24.5 | bsp dep tag bump (1.0.0 → 1.0.1), Cyrius 4.6.2 / 4.8.2 / 4.8.5-1 toolchain rollups, switch-jump-table tuning (4-case weapon/ammo conversions) |
| v0.24.6 | Cyrius 5.5.0 bump, E1M6 map-cap fix (MAP_MAX_SSECTORS 512 → 1024), test suite includes repaired |
| v0.26.0 | bsp real dep: `cyrius.cyml` migration + `[deps.bsp] @ 1.1.1`, `render_bsp_node` uses bsp primitives, DCE in release CI, test job in CI, `scripts/bench-history.sh` modernized |
| v0.26.1 | Cyrius 5.5.2 + bsp 1.1.2 (enum-constant fold, −7,296 B / −2.7 %). No source changes. |
| v0.26.2 | Cyrius 5.5.2 → 5.7.48 (CI dep-resolve unblock); vani 0.3.0 → 0.9.1 `core` profile (`dist/vani-core.cyr`, 22 `audio_*` symbols vs 106 in full bundle); `lib/` gitignored + untracked (was a mix of real stdlib copies + dangling local-path symlinks); `patra` dropped from stdlib (vani's `[deps.patra]` provides it); CI aligned with vani / yukti (toolchain via `cyrius.cyml`, `cyrius.lock` presence gate, `cyrius deps --verify`, version-consistency check); audio-core proposal authored, accepted in vani 0.9.1, archived. Binary 565,840 B (full recovery to ~260 KB gated on Cyrius O3). |
| v0.27.0 | Cyrius 5.7.48 → 6.0.1 lift (covers v5.8.x sum-types / `Result<T,E>` / `?` / exhaustive-match, v5.11.x annotation arc, v6.0.0 `cyrc → cybs` + `cc5 → cycc` rename, v6.0.1 stdlib-path hotfixes); vani 0.9.1 → 0.9.3 (annotation pass, ABI-identical); `cyrius.toml` + `cyrb.toml` retired (single `cyrius.cyml`); `${file:VERSION}` template; CI lifted to patra-style installer + pre-flight HTTP gate + lockfile-guarded verify. Binary 585,320 B (+19,464 B growth-tax). |
| v0.27.1 | Dep-tag re-pin to upstream-published bsp 1.1.3 + vani 0.9.4. Bundle content byte-identical save for `Version:` header. Binary 585,320 → 585,224 B (−96 B). `render_frame` 2.146 ms (variance-level). |
| v0.27.2 | `: i64` return-type annotation sweep across all 20 modules (270 fn sigs). Parse-only, byte-identical binary (585,224 B). `render_frame` 2.114 ms (variance-level). |

## v0.24.0 — Security Hardening (CVE Audit Fixes)

| # | Item | Severity | Detail |
|---|------|----------|--------|
| 1 | Map index bounds validation | CRITICAL | Validate all seg/linedef/sidedef/node indices after map_load() |
| 2 | Texture column bounds | CRITICAL | Validate patch col_off within lump, post_ptr within buffer |
| 3 | BLOCKMAP offset validation | CRITICAL | Validate cell list offsets within blockmap lump size |
| 4 | WAD lump read validation | HIGH | Check file_read return value, zero-fill on partial read |
| 5 | Sprite minimum lump size | HIGH | Reject sprite lumps < 8 bytes (patch header minimum) |

See: `docs/audit/2026-04-13-security-cve-audit.md`

## v0.27.x — Language-adoption arc

**Theme** — absorb the v5.8.x → v6.0.1 language gains (sum types,
`Result<T, E>`, `?` operator, exhaustive match, parse-only `: i64`
return annotations) and the modern manifest convention (single
`cyrius.cyml`, `${file:VERSION}` template) into doom's actual code +
toolchain. The original 0.27.0 thesis was the "performance pass held
against Cyrius O4 regalloc," but O4 has slipped to a v6.4.x slot in
cyrius's roadmap and the v5.8.x language arc is now mature in stdlib
— making *adoption* the higher-value 0.27.x sequence. The perf-pass
re-targets to **v0.29.x** (or whatever ships closest to O4 cycle).
Black Book audit (was v0.25.0) re-anchors as **v0.28.x**, sequenced
after the language arc lands so audit deltas are written against the
modernized code, not against code we're about to rewrite.

### v0.27.0 — Cyrius 6.0.1 lift + manifest hygiene (2026-05-21) — DONE

See CHANGELOG entry. Bumps: cyrius 5.7.48 → 6.0.1; vani 0.9.1 →
0.9.3; drops `cyrius.toml` + `cyrb.toml` (single `cyrius.cyml`);
`version = "${file:VERSION}"` template; CI lifted to patra-style
toolchain installer + pre-flight HTTP gate; CI `--verify` step
guarded on a populated lockfile (cycc 6.0.1 lockfile-writer
regression). Build green at 585,320 B (+19,464 B v5.11.x annotation
rt-table + v5.8.x sum-type-emit growth-tax); 37/37 WAD-free tests;
E1M1 PPM smoke matches 0.26.2 byte counts.

**Co-shipped upstream (out-of-band, gated on user publish):**
- **bsp 1.1.3** — prepared at `/home/macro/Repos/bsp` (unstaged on
  `main`, ssh remote). Cyrius pin 5.5.2 → 6.0.1, `${file:VERSION}`
  template, `cyrius.toml` retired, `.cyrius-toolchain` retired,
  CI lifted to patra-style installer (was pinned at 5.5.0 in the
  legacy `.cyrius-toolchain` — would have installed wrong cyrius).
  CHANGELOG `[1.1.3]` entry + new `docs/development/roadmap.md`
  with 1.2.x language-adoption arc. Gates: 79/79 tests, 13/13
  benches sub-μs, 25K fuzz iters, build 76,496 → 94,640 B
  (+18,144 B growth-tax).
- **vani 0.9.4** — already prepared upstream in vani's working
  tree (commit `7b44e0d`, not yet tagged). Cyrius pin 5.11.4 →
  6.0.1, yukti 2.2.2 → 2.2.4, patra 1.9.3 → 1.9.5, CI yml
  `cc5_aarch64` → `cycc_aarch64`. dist content byte-identical
  save for `Version:` header.
- **Suggested publish order**: bsp 1.1.3 → vani 0.9.4 → cyrius-doom
  0.27.0 (so dep-resolution succeeds at each step).

**Known cycc 6.0.1 issues + workarounds** (drop when upstream fixes):
- `cyrius deps` writes empty `cyrius.lock` for our manifest shape.
  Workaround: hand-populate via `sha256sum lib/{vani-core,bsp,
  yukti,patra,sakshi}.cyr > cyrius.lock`. CI's `--verify` step
  is guarded on a populated lock — drop the guard when upstream
  fixes.
- `lib/yukti.cyr:39: duplicate fn 'sys_stat' (last definition
  wins)` — cycc 6.0.1 stdlib now defines `sys_stat`; vani's
  transitively-bundled yukti 2.2.4 also defines it (unannotated).
  Codegen-identical, warning-only. Drops when yukti drops the
  duplicate from its dist.

### v0.27.1 — bsp 1.1.3 + vani 0.9.4 dep-tag re-pin (2026-05-21) — DONE

Pure dep-tag bumps to the freshly-cyrius-6.0.1-pinned upstream
tags. Both bundles' contents are byte-identical to current
(0.27.0) pin save for the `Version:` header line — same shape as
v0.26.1's Cyrius pin-only patch. See CHANGELOG entry.

| # | Item | Status |
|---|------|--------|
| 1 | `[deps.bsp]` 1.1.2 → **1.1.3** | Done |
| 2 | `[deps.vani]` 0.9.3 → **0.9.4** | Done |
| 3 | Refresh `cyrius.lock` hashes (5 of 5 rotated — bsp, vani-core, plus yukti / patra / sakshi which got re-resolved through vani's transitive tree) | Done |
| 4 | Re-bench frame time vs 0.27.0 baseline (expected: variance-level) | Done — `render_frame` 2.146 ms / `+sprites` 2.141 ms; binary 585,320 → 585,224 B (−96 B, `Version:` header swap) |

### v0.27.2 — Type annotations on public surface (2026-05-21) — DONE

Mechanical sweep adopting the v5.11.x annotation arc on doom's
own code — same shape as vani 0.9.3's "every public fn in
`src/*.cyr` carries a `: i64` return-type annotation" cut.
Parse-only, zero codegen change. Documents return contracts
inline; sets up for v0.27.3 to introduce `Result`-returning
variants on the same fns. See CHANGELOG entry.

| # | Item | Source modules | Detail |
|---|------|----------------|--------|
| 1 | `: i64` return annotations across `src/*.cyr` | all 20 modules | Done — 270 fn sigs annotated (269 single-line + 1 multi-line `render_store_masked`). Parse-only, ABI-identical |
| 2 | Public-surface type-annotation pass | `wad`, `map`, `render`, `texture` | Done — covered as part of the full sweep; no tiered rollout needed since the change is mechanical |
| 3 | Verify `bench-history.csv` shows variance-level deltas only | benches | Done — `render_frame` 2.146 → 2.114 ms (variance); binary byte-identical at 585,224 B |

### v0.27.3 — `Result<T, E>` adoption in WAD/render error paths

Adopt the v5.8.28 `lib/result.cyr` carve-out at the IO/parse
boundary where doom currently returns hand-coded error sentinels
(`-1`, `0` for null pointer, etc.). Highest-value targets:
`wad_open` / `wad_lump_read` (file-IO failure), `texture_load`
/ `patch_load` (lump-shape validation), `map_load`
(index-bounds validation already in place — Result wraps the
existing checks). `?` operator collapses cascaded error checks.

| # | Item | Module | Detail |
|---|------|--------|--------|
| 1 | `wad_open` returns `Result<WadHandle, WadError>` | wad.cyr | Replace `0`-on-fail with typed `Err` |
| 2 | `wad_lump_read` returns `Result<usize, WadError>` | wad.cyr | Replace `-1`-on-fail; bytes-read on Ok |
| 3 | `texture_composite` returns `Result<u8*, TextureError>` | texture.cyr | Replace null-on-fail; covers patch-cache load failure |
| 4 | `?` operator in `r_init` / `main` / `doom_main` call paths | render.cyr, main.cyr | Cascading unwrap; one Err short-circuits to a logged exit |
| 5 | Exhaustive-match on `WadError` / `TextureError` at the main-loop boundary | main.cyr | Compiler-enforced — no silent fall-through |

### v0.27.4 — `lib/test.cyr` table-driven test refactor

Adopt the v5.7.43 `test_each(cases, fn)` stdlib helper. Current
`tests/doom.tcyr` is ~73 asserts of hand-rolled per-case
assertion calls; table-driven cuts the boilerplate and makes it
easy to add new cases for the same property. Targets:
fixed-point arithmetic (asr / fx_mul / fx_div), trig tables,
angle math.

| # | Item | Detail |
|---|------|--------|
| 1 | Add `"test"` to `cyrius.cyml` stdlib | One-line manifest |
| 2 | Convert asr / fixed-point asserts → `test_each` | ~20 asserts collapsed |
| 3 | Convert trig-table asserts → `test_each` | ~12 asserts collapsed |
| 4 | Extend test corpus once boilerplate drops | Add 20+ cases per group |

### v0.27.5 — Upstream-fix cleanup (gated on cycc fixes)

Lands when cyrius ships the lockfile-writer fix + yukti drops its
duplicate sys_stat. Pure cleanup — no new doom features.

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Drop CI `--verify` lockfile-presence guard | Blocked on cycc lockfile fix | Restore `cyrius deps --verify` as unconditional gate |
| 2 | Drop hand-populated `cyrius.lock` workflow | Blocked on cycc lockfile fix | Let `cyrius deps --lock` write canonical hashes |
| 3 | Re-resolve deps to drop yukti `sys_stat` dup-fn warning | Blocked on yukti re-bundle | Bump vani → re-resolves transitive yukti |
| 4 | Update CHANGELOG / CLAUDE.md "Known issues" section | Pending | Strike the two workaround blocks once both fixes land |

### Watch (not yet 0.27.x slot material)

- **`lib/random.cyr`** (v5.9.x stdlib addition) — deterministic
  per-DOOM-tick PRNG. Doom's monster AI is already deterministic
  per the original game; not adopted unless RNG is wanted for
  intermission/menu polish.
- **`#io` effect annotations** (v5.11.x) — would document the
  io-side-effect set of `wad_lump_read` / `framebuf_present` /
  `audio_write`. No semantic change. Defer until Cyrius pins
  the annotation surface as stable.
- **mabda 3.0 fold / bayan-ganita carve** (v6.0.x planned) —
  doom uses no JSON/TOML, so this is a no-op for us.

## v0.29.x — Performance pass (held against Cyrius O4 regalloc)

Re-targeted from 0.27.0. Cyrius's compiler-optimization track has
three phases that directly move cyrius-doom's hot paths.
Hand-optimizing `fx_mul` / `asr` / column loops today would fight
the codegen once O4's linear-scan register allocator lands and
delivers its projected 2–3× on hot inner loops.

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Wait for **Cyrius O2** (peephole: strength reduction, flag reuse, LEA combining, aarch64 `madd`/`msub`) | Upstream | Small runtime wins on math-dense loops. Free bump once shipped. |
| 2 | Wait for **Cyrius O3** (IR-driven DCE + const prop + dead-store elim) | Upstream | Today we NOP 290 KB of dead code (same file size). O3 strips it for real — binary genuinely shrinks. |
| 3 | Wait for **Cyrius O4** (linear-scan regalloc, Poletto–Sarkar; v6.4.x per cyrius roadmap) | Upstream | The single biggest win. `render_frame` projection: 3.9 ms → ≤1.5 ms. Column renderer, BSP walk, patch cache all benefit. |
| 4 | Re-bench hot paths on O2/O3/O4-enabled toolchain | Pending | `bench-history.csv` row per upstream phase landing, with A/B before/after numbers to confirm the compiler wins stick. |
| 5 | Revisit manual patterns only after O4 | Pending | At that point any remaining 5–10 % wins from column-loop restructure are worth chasing; before then, no. |

## v0.28.x — DOOM Black Book Audit

Was v0.25.0; re-anchored here so audit deltas are written against
the modernized 0.27.x code rather than against code we'd rewrite
in the language-adoption arc. Scope: chapter-by-chapter
verification against Fabien Sanglard's _Game Engine Black Book:
DOOM_ + the Unofficial DOOM Specs, with reference PPMs from
chocolate-doom (the closest-to-original-DOOM modern engine) as
ground truth for visual comparisons.

### v0.28.0 — Rendering pipeline audit

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | Visplane span generation | Black Book ch. 9 (R_DrawPlanes) | Spans match shape + count vs reference on E1M1/M3/M5 |
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
| 1 | Re-walk the v0.24.0 CVE checklist | All 5 CVE items checked under 0.27.3 `Result`-wrapped paths |
| 2 | Fuzz-corpus refresh | Add ADT-discriminator-aware mutators for the new `Result<T, E>` shape |
| 3 | Audit doc | `docs/audit/2026-XX-XX-v0.28-black-book.md` written as a single artifact, sectioned per 0.28.x patch |

## v0.26.2 — Cyrius 5.7.48 + vani 0.9.1 `core` profile (2026-05-01) — DONE

Toolchain + audio-stack hygiene cut. Two motivations:

1. **CI was failing on dependency resolution** in two
   compounding ways. First, `cyrius.cyml` declared
   `cyrius = "5.7.48"` (required by vani 0.9.x's transitive
   stdlib surface — `fs` / `hashmap` / `tagged` / `fnptr` /
   `freelist` / `process` / `patra`), but `.cyrius-toolchain`
   was still pinned at 5.5.2 — CI installed the wrong
   toolchain. Second, the repo committed `lib/` (mix of real
   stdlib copies and dangling local-path symlinks) and listed
   `patra` in both stdlib AND vani's transitive `[deps.patra]`
   override, which `cyrius deps` couldn't reconcile
   (`error: cannot write lib/patra.cyr`). Fixed by gitignoring
   `lib/` (matching vani / yukti), dropping `patra` from
   stdlib, deleting `.cyrius-toolchain` and reading the
   toolchain pin from `cyrius.cyml` directly.
2. **vani's full bundle was overkill.** Bumping vani 0.3.0 →
   0.9.0 grew `build/doom` by +340 KB for a 117-line audio
   module that calls 6 of vani's 106 public symbols. Authored
   a proposal for a `core` distribution profile, vani accepted
   it in 0.9.1 (collapsed from a three-cut patch series into a
   single cut), shipped `dist/vani-core.cyr` — a 29 KB
   single-module bundle exposing only the 22 `audio_*` symbols
   from `src/alsa.cyr`. cyrius-doom flipped its `[deps.vani]`
   `modules` field over and recovered ~35 KB of binary.

| Change | Detail |
|--------|--------|
| Cyrius toolchain | 5.5.2 → **5.7.48** in `cyrius.cyml` + `cyrius.toml`; `.cyrius-toolchain` deleted (CI now reads from `cyrius.cyml`, matching vani / yukti) |
| vani | 0.3.0 → **0.9.1**, profile `dist/vani.cyr` → `dist/vani-core.cyr` (22 symbols vs 106) |
| `src/main.cyr:18` include | `lib/vani.cyr` → `lib/vani-core.cyr` |
| `cyrius.toml` / `cyrb.toml` `[deps]` stdlib | retired `audio` dropped; added `fs` / `hashmap` / `tagged` / `fnptr` / `freelist` / `process` / `sakshi` to match `cyrius.cyml`; **`patra` dropped** (vani's `[deps.patra] @ 1.9.2` provides it transitively — listing it in both places caused `error: cannot write lib/patra.cyr` in CI) |
| `cyrb.toml` | stale `[deps.shravan] @ 2.0.0` replaced by `[deps.vani] @ 0.9.1` |
| `lib/` | now fully gitignored (`/lib/` in `.gitignore`); 18 previously-tracked files untracked (mix of real stdlib copies and dangling local-path symlinks). `cyrius deps` populates fresh per checkout. |
| `.github/workflows/ci.yml` | toolchain version from `cyrius.cyml`; `Lock file present` gate; `cyrius deps --verify` step; version-consistency check across VERSION / `cyrius.cyml` / `cyrius.toml` / CHANGELOG.md |
| `.github/workflows/release.yml` | toolchain version from `cyrius.cyml` (was `.cyrius-toolchain`) |
| Lockfile | clean 5-deps state (`vani-core`, `bsp`, `yukti`, `patra`, `sakshi`); `cyrius deps --verify` passes |
| Binary size | 259,920 → 565,840 B (+305 KB regression vs 0.26.1; recovery gated on Cyrius O3 real DCE) |

**vani is transitional.** Replaces the retiring cyrius stdlib
`audio` (5.8.0 fold-in), and will itself be replaced by
**dhvani** once the Rust→Cyrius port lands. The `audio_*` shape
is the migration target, so `src/audio.cyr` stays ABI-stable
across the eventual swap.

Proposal artifact (drafted, accepted by vani, closing-loop
delta logged) archived at
`docs/proposals/archive/vani-audio-core-profile.md`.

## v0.26.1 — Cyrius 5.5.2 + bsp 1.1.2 (2026-04-20) — DONE

Pure toolchain bump, no source changes. Picks up the 5.5.2 enum-constant
`sc_num` fold — every enum variant read now emits `mov rax, imm32` (5 B)
instead of `mov rcx, gvaddr; mov rax, [rcx]` (~10 B). cyrius-doom is
enum-dense, so the win compounds: **267,216 → 259,920 B (−7,296 B,
−2.7 %)**. bsp's standalone binary: −1,448 B (−1.86 %). Bench numbers
within run-to-run variance of 0.26.0 — this is a codegen-size win, not
a runtime-hot-path win.

## v0.26.0 — BSP as a real dep (2026-04-20) — DONE

Turned the "Composes: bsp" line from aspirational into mechanical truth.
Manifest migrated to `cyrius.cyml` with `[deps.bsp] @ 1.1.1`.
`render.cyr` / `player.cyr` / `sprite.cyr` swap `map_point_on_side` /
`map_node_child_{r,l}` / `map_is_subsector` / `map_subsector_idx` for
`bsp_*` equivalents; `map.cyr` sheds the duplicates. Layout-compatible
(identical 112-byte node block). Release CI runs `CYRIUS_DCE=1`;
cyrius-doom CI now runs the WAD-free 37-assert test subset.

## v0.25.0 — DOOM Black Book Audit (2026-04-15) — deferred → re-anchored as v0.28.x

Original deferral was behind 0.26.0. Re-anchored as the v0.28.x
arc above so audit work lands against the 0.27.x-modernized code
rather than against the pre-language-adoption surface. Original
scope (5 items) expanded into the four 0.28.x patches.

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1-E1M9 (shareware) | Not started | Full episode 1 playable start to finish |
| 2 | X11 display backend (native) | Not started | Direct X11 protocol, no Python bridge |
| 3 | Wayland display backend | Not started | For AGNOS desktop |
| 4 | Runs on AGNOS kernel | Not started | Kernel framebuffer + PS/2 |
| 5 | Runs on Linux /dev/fb0 | Not started | Userspace fallback |
| 6 | In AGNOS initrd | Not started | Boot → shell → doom |

## Future

| Item | Detail |
|------|--------|
| Wolfenstein 3D mode | Raycaster renderer using Black Book patterns |
| GPU rendering via mabda | wgpu backend for hardware acceleration |
| Network multiplayer | Peer-to-peer via majra |
| PWAD support | Custom maps/mods |
| Full DOOM.WAD | Episodes 2-3 (registered version) |

## AgentWorld / DOOM Crossover

See [roadmap-crossover.md](roadmap-crossover.md) — secureyeoman spatial threat visualization via DOOM engine.
