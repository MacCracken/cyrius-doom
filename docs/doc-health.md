# Documentation Health — cyrius-doom

> **Last refresh**: 2026-07-12 v0.33.4 **RELEASE-READY** (thirteenth pass — **security + safety quick-wins, first audit-slot patch**: CHANGELOG `[0.33.4]` entry [M-1 Wayland resize crash, P-6 dim overflow, M-2 env-path smash, R-2 dead death-face, R-6/M-3/M-4 lump-alloc guards, G-7 sparse-switch rewrite]; state.md → 0.33.4 header/version/binary/gates/slot [155/227 tests, 439,208 B, AGNOS QEMU doom-smoke+ingame+aethersafha-present PASS]; completed-phases.md gained v0.33.4 + v0.33.3 rows; roadmap.md → v0.33.4 struck SHIPPED; consolidated-audit.md is the standing ledger the slots track. Twelfth pass — **audit round: toolchain/dep refresh + setu present-leak fix + roadmap reorg**: new `docs/audit/2026-07-12-consolidated-audit.md` [the single open-findings ledger — classifies every finding across all 7 prior audit docs + the 2026-07-12 five-agent round: P/R/G/M findings]; CHANGELOG `[0.33.3]` entry [6.4.55 + vani 1.1.1 + setu 0.5.1 P-1 fix + input hardening]; state.md → 0.33.3 header/version/pins/binary/gates/slot [+ caught up the 0.33.2 setu-backend row it shipped without], 26 modules / 3 vendored libs; completed-phases.md gained the v0.33.2 row; roadmap.md → new patch band 0.33.4/0.33.5/0.33.6 + v0.28.11/v0.34.x additions + **codegen gate corrected** [perf/regalloc arc is cyrius v6.5.x not v6.4.x]. The 7 prior audit docs stay as dated evidence artifacts, now indexed by the consolidated doc. **Eleventh pass (0.33.2, not separately doc-health'd) — setu desktop backend shipped.** Prior: tenth pass — **field-report combat/sky/movement patch shipped**: CHANGELOG `[0.33.1]` entry [4 field bugs root-caused: sky V/U parity, atan2 minimax, drop-off wedge escape, monster mover-floor collision + noise alert + ranged attacks + toolchain 6.4.43 + vani vendor 1.0.0]; state.md → 0.33.1 header/version/pins/binary/gates/slot [149/218 tests, 426,496 B, QEMU doom-smoke + in-game harness PASS]; roadmap → 0.28.7 sky item 1 struck SHIPPED, RC-G monster-z residual struck, new 0.33.1-follow-ups row [baron BAL7 / ledge-glide z / sight z-slope / P_NewChaseDir]. Prior: ninth pass — **native Wayland window backend shipped**: four `src/platform/` files [wire/client/shm + window seam], double-buffered present, full keyboard, drag-resize, wire-parser security hardening; new `docs/proposals/wayland-backend.md` + `docs/audit/2026-07-09-wayland-backend.md`; CHANGELOG `[0.33.0]` Added block; state.md → 0.33.0 header/version/binary/gates/slot/25-modules [133/193, 418,224 B, AGNOS QEMU PASS]; completed-phases v0.33.x section; roadmap v0.33.0 struck SHIPPED + Wayland-follow-ups row + v1.0.0 Wayland row ✅; CLAUDE.md module map gained the platform/ tree + the framebuf-include note. Built through 4 adversarially-reviewed bites. Eighth pass — **patch: `--audio-test`/`--music-test` separation**: `--audio-test` was mixing in music (load_map's `music_start` + default `music_volume` 8) — now `music_stop`s first (SFX-only), `--music-test` `music_start`s to re-arm (music-only); +3 WAD-free regression asserts; CHANGELOG `[0.32.1]` entry; state.md → 0.32.1 header/version/binary/gates/slot [118/178, 392,304 B, QEMU PASS on v0.32.1]; completed-phases 0.32.1 row. Seventh pass — **leftovers closed + QEMU gated**: RC-G6 menu edge-latch, F-R6 fully retired [texture fill-mask], L8-lite monster solidity; **AGNOS QEMU doom-smoke PASS on the final binary**; CHANGELOG leftovers block + final numbers [392,280 B / 2.455 ms]; state.md slot → RELEASE-READY, QEMU gate row green; roadmap F-R6 struck, Bite C residuals updated; completed-phases + audit status final. Sixth pass — **Bite D + leftovers + see-through-gun fix shipped**: CHANGELOG Bite D block; state.md final metrics [388,144 B, 2.361 ms, 115/175, closeout-complete slot row]; roadmap Bite D/0.28.7-items/F-R6/G8 rows updated; **completed-phases.md gained the v0.32.0 + v0.31.x sections**; audit status header final. Fifth pass — **Bite C gameplay sweep shipped** [RC-G1–G5, G7; +8 asserts; CHANGELOG block, state.md rows, roadmap Bite C struck] + **v0.33.0 desktop-rendering slot added** [native Wayland backend, puka as the working example — user-directed; v1.0.0 Wayland row pulled forward]. Fourth pass — **visplane pool + viewz (0.28.5) + version renamed 0.31.5→0.32.0 per user**: CHANGELOG `[0.32.0]` gained the visplane block [-24% render_frame]; state.md → elevation/plane metrics + 0.28.5/0.28.6 forward rows struck; roadmap 0.28.5 slot + section SHIPPED with per-item disposition; audit status header updated. Third pass — **Bite B + pin 6.4.30**: CHANGELOG `[0.32.0]` gained the Bite B block [drawseg depth clipping RC-S1/S2/S9/W6 + RC-W9 endpoint re-anchor] + the pin-bump Changed entry; state.md → Bites A+B [cycc 6.4.30 pinned metrics, 115/167 tests, E1M7 band re-attributed to RC-W9]; roadmap 0.28.6 slot + section + audit Bite B row marked SHIPPED; audit doc gained a same-day status header. Second pass: **Bite A shipped** [6 fixes, +21 asserts]; CLAUDE.md lock-count inlines → state.md pointers. First pass: the render-consistency audit artifact + roadmap audit section. Prior refresh: 2026-06-29 v0.30.7). | **Refresh cadence**: opportunistic — update the affected row when the underlying doc is touched. No periodic sweep cron.
>
> **Scope**: this repo only (`cyrius-doom`) — the entire `docs/` tree plus root-level docs (README, CHANGELOG, CLAUDE.md, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT). VERSION is tracked as a structural artifact, not a doc.
>
> **Convention adopted from agnosticos**: pattern from `agnosticos/docs/doc-health.md`, leaner because cyrius-doom's tree is ~16 md files (vs cyrius's ~105 / agnosticos's ~265). The tier structure here is correspondingly smaller — root files + architecture + development + audits + proposals. See [first-party-documentation § Development Docs](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#development-docs-docsdevelopment) for the convention.

This is a **ledger**, not a one-time audit. Rewrite-in-place as docs change.

---

## At a glance — 2026-05-21 inventory (v0.27.2 / initial scaffold)

**16 markdown files** across the repo (root + `docs/`). Bucket counts:

| Bucket | Count | What it means |
|---|---|---|
| ✅ **Fresh / touched in current cycle** | 9 | Touched within the v0.27.x cycle (most through the 0.27.0 → 0.27.2 ship sequence + this doc-split sweep). |
| 🟡 **Stale — refresh in place** | 2 | `docs/audit.md` (v0.11.0-era gap analysis, mostly resolved by subsequent work); `docs/architecture/overview.md` (pre-0.27.x binary sizes + bench numbers). |
| 🟠 **Read-through outstanding** | 1 | `docs/development/roadmap-crossover.md` — secureyeoman crossover; not touched during the 0.27.x arc; status not verified against the current scope. |
| 🔵 **Evergreen / dated artifact** | 4 | 2 audit reports (`docs/audit/*`) — dated artifacts, supersede with new audits, don't refresh in place; `docs/sources.md` (citation index); `docs/proposals/archive/vani-audio-core-profile.md` (archived shipped proposal). |
| 📦 **Archive — frozen by design** | 0 | None today. Archived proposals live under `docs/proposals/archive/` and are counted under 🔵 above. |
| ❓ **Open strategic question** | 0 | None today. |

**Why now**: doc-health convention adopted at v0.27.2 alongside the doc-split sweep that moved volatile state out of CLAUDE.md (per the first-party-documentation `CLAUDE.md` rule — "stale CLAUDE.md is worse than no CLAUDE.md"). Below the ~30-doc threshold where doc-health typically earns its slot, but scaffolded ahead of time so the ledger discipline is in place before drift accumulates.

---

## Tier 1 — Root files

| File | Last touched | Status | Action |
|---|---|---|---|
| `README.md` | 2026-04-30 | ✅ Fresh | Top-level project README. Verify in passing at next minor closeout — pre-dates the v0.27.x cycle but content is durable. |
| `CHANGELOG.md` | 2026-07-10 | ✅ Fresh | **Source of truth per CLAUDE.md.** Through **v0.33.1** (field-report combat/sky/movement patch + toolchain 6.4.43 + vani vendor 1.0.0). v0.33.0 = native Wayland window backend. Refreshed every release. |
| `CLAUDE.md` | 2026-07-08 | ✅ Fresh | Durable content only (state delegated to `state.md`). 2026-07-08: the two inlined lock-entry counts (Work-Loop §7 + CI/Release) replaced with `state.md` pointers — they'd gone stale twice (0.31.0 stdlib growth, 0.32.0 vani vendoring); per the file's own no-volatile-state rule. Project-identity / Goal / Process / Rules / Cyrius Conventions all durable. |
| `CONTRIBUTING.md` | 2026-04-30 | ✅ Fresh | Verify in passing at next minor closeout — durable content. |
| `SECURITY.md` | 2026-04-30 | ✅ Fresh | Public reporting policy. Durable; pre-dates v0.27.x but no surface change. |
| `CODE_OF_CONDUCT.md` | 2026-04-30 | ✅ Fresh | Standard CoC. Durable. |

---

## Tier 2 — `docs/` root

| File | Last touched | Status | Action |
|---|---|---|---|
| `docs/audit.md` | 2026-04-30 | 🟡 Stale | **v0.11.0-era gap analysis** vs original DOOM engine. Several "MISSING" rows are now resolved (masked midtextures shipped at v0.21.0; visplane merging is still missing but should be tracked under v0.28.x Black Book audit, not here). Decide at v0.28.x cycle-open: either fold into the v0.28.x audit doc and archive this, or refresh the table inline. Likely candidate for archive once v0.28.0 lands. |
| `docs/sources.md` | 2026-04-30 | 🔵 Evergreen | Citation index — Black Book / Unofficial DOOM Specs / id Source / fixed-point math sources. Durable reference. Touch only when a new external source enters use. |

---

## Tier 3 — Architecture (`docs/architecture/`)

| File | Last touched | Status | Action |
|---|---|---|---|
| `overview.md` | 2026-06-07 | ✅ Fresh | Module dependency graph + memory layout + perf. **Refreshed at v0.28.0**: stale v0.11.0 perf table replaced with a pointer to `state.md` + `bench-history.csv`; the dead `rgb_buf` memory row corrected to `fb_buf` (v0.27.4 change). |

No numbered architecture notes yet — the convention is `NNN-kebab-case-title.md` once a second arrives. Earn first.

---

## Tier 4 — Development (`docs/development/`)

> **Important framing**: `state.md` + `roadmap.md` + `completed-phases.md` form the canonical operational surface. CLAUDE.md delegates volatile state to `state.md`; `roadmap.md` is forward-facing only; `completed-phases.md` carries the chronological shipped record. These three rotate every release.

| File | Last touched | Status | Action |
|---|---|---|---|
| `state.md` | 2026-07-10 | ✅ Fresh | **Rotates every release.** Current to **v0.33.1** (release-ready): field-report combat/sky/movement patch, 149/218 tests, binary 426,496 B (agnos 395,968 B), AGNOS QEMU doom-smoke + in-game harness PASS on the v0.33.1 binary, pinned 6.4.43, vani vendor 1.0.0. v0.33.0 = Wayland window backend; v0.32.x = render-audit mega-cut. Previously current to v0.30.7 — **positional/stereo SFX + Sound-menu live preview**: binary 623,520 B (agnos 610,152 B), `render_frame` 2.956 ms, lock 37/0 (unchanged). `audio_play_at` distance atten + pan; per-voice stereo mixer; live slider preview. Gates re-run on Linux (63/63 + 101/101, fuzz 1000/50000, `--audio-test` L/R); AGNOS QEMU not gated. v0.30.7 slot row added; 0.30.6 → shipped. |
| `roadmap.md` | 2026-07-10 | ✅ Fresh | **0.33.1 pass**: 0.28.7 sky item 1 struck SHIPPED (tan-distributed U + 1:1 V), RC-G monster-z residual struck, new 0.33.1-follow-ups unslotted row (baron BAL7, ledge-glide z, sight z-slope, P_NewChaseDir wander). Previously: **v0.33.0 struck SHIPPED** (native Wayland backend) + a Wayland-follow-ups unslotted row + the v1.0.0 Wayland row marked ✅. Previously: **2026-07-08 render-audit section added** (Bite A quick wins + Bite C gameplay-sweep unslotted rows; wall-path #6 → CONFIRMED; 0.28.6 evidence note + run-before-0.28.5 recommendation; 0.28.7 gained sky-vs-sky item 0). Previously: **re-slotted at v0.28.4 cut** (0.28.5–.11 carry the Black Book parity/perf themes). Floor-render + shooting-overhaul deferrals folded in as unslotted rows. v0.30.1 wall-path/psprite/flash items RESOLVED. **v0.30.7**: distance/positional attenuation + stereo pan + Sound-menu live-preview/polish **shipped** (with 0.30.6's HW_PARAMS/ESTRPIPE); the remaining audio-hardening row now carries only items needing other hardware (48 kHz), an upstream vani API (virtual-card), or that contradict the faithful-loudness choice (normalization) + low-value double-fire gating. Slot numbers vs shipped 0.29.x/0.30.x acknowledged stale — renumbering deferred. |
| `completed-phases.md` | 2026-07-09 | ✅ Fresh | **Updated at the v0.33.0 release** — new v0.33.0 section (native Wayland window backend). Also carries the v0.32.x mega-cut + patch and the catch-up v0.31.x section. Chronological one-line index. |
| `roadmap-crossover.md` | 2026-04-30 | 🟠 Read-through | AgentWorld / secureyeoman crossover doc — spatial threat visualization via the DOOM engine. Not touched during the v0.27.x cycle; status against current secureyeoman scope not verified. Read-through at next minor closeout. |

---

## Tier 5 — Audits (`docs/audit/`)

Dated artifacts; supersede with a new audit doc rather than refresh in place.

| File | Last touched | Status | Notes |
|---|---|---|---|
| `2026-04-13-security-cve-audit.md` | 2026-04-30 | 🔵 Dated artifact | v0.24.0 CVE audit (C1–C3, H1–H2). Re-verified in the 2026-06-07 graphics audit: C2 propagated to all patch decoders (F01/F02/F03/F19), visplane OOB-**write** closed (F17). C3 (BLOCKMAP) + H1 (lump size) re-confirm pending v0.28.7. |
| `2026-04-15-black-book-handoff.md` | 2026-04-30 | 🔵 Dated artifact | Black Book handoff notes — surface map for the v0.28.x audit. Cited from `roadmap.md` v0.28.x section. |
| `2026-06-07-v0.28-graphics-hardening.md` | 2026-06-07 | 🔵 Dated artifact | v0.28.0 graphics review/hardening/audit/perf. 67→27→20 findings; 8 shipped, rest re-slotted across 0.28.1–.7. Patch-decoder bounds propagation + visplane OOB-write fix + flat-fill inline. |
| `2026-06-13-shooting-hitscan.md` | 2026-06-13 | 🔵 Dated artifact | v0.30.0 P(-1) security research for the shooting path (hitscan/projectile/psprite). Reviewed DOOM-family CVE classes (patch over-read, P_LineAttack state, autoaim, projectile DoS, damage overflow); posture green — `fuzz_weapon` 20k clean, projectile spawn bounded, splash recursion bounded. |
| `2026-07-04-mus-music.md` | 2026-07-04 | 🔵 Dated artifact | v0.31.4 P(-1) research for the MUS/music module (format bounds, sequencer DoS classes); drove `fuzz_mus`. |
| `2026-07-08-render-consistency.md` | 2026-07-08 | 🔵 Dated artifact | **Render-consistency audit** (walls/flats/sprites + 14-module sweep). 21 findings with staged-viewpoint PPM evidence + repro coordinates. Status header (same day): **Bites A+B+C AND the 0.28.5 visplane/viewz keystone all shipped in 0.32.0** (+ RC-W9 discovered/fixed); remaining → RC-G6 (QEMU-gated), RC-G8 LOW bundle, Bite D polish. |
| `2026-07-09-wayland-backend.md` | 2026-07-09 | 🔵 Dated artifact | **Wayland backend security review** (v0.33.0, P(-1)). Threat model = buggy/hostile local compositor. Findings W-1..W-5 all fixed: wire-parser registry-string OOB bound, fixed-offset read-slack + key size guards, SCM_RIGHTS zeroing, the `var x[N]`-BYTES stack-overflow, the resize-OOM dangling-pointer crash. CI headless tests exercise the wire codec + `wl__parse` bounds. |

---

## Tier 6 — Proposals (`docs/proposals/`)

| Path | Count | Status | Notes |
|---|---|---|---|
| `wayland-backend.md` | 1 | ✅ Fresh | **v0.33.0 Wayland backend design + phasing** (shipped 2026-07-09). Status header tracks bites 1–4 landed + the critique resolutions (F1–F11) + the bite-4 resize note. Keep until a follow-up (X11 backend) supersedes it, then archive. |
| `proposals/archive/` | 1 | 🔵 Frozen | `vani-audio-core-profile.md` — shipped in vani 0.9.1; archived per closing-loop pattern. Cited from CHANGELOG `[0.26.2]`. |

Filing a new proposal: drop in `docs/proposals/{kebab-case-title}.md`; archive (delete or move to `archive/`) when shipped or rejected.

---

## Refresh procedure

When docs are touched:

1. Find the affected row in the relevant tier table.
2. Update **Last touched** to the new date.
3. Update **Status** if the bucket changed.
4. Update **Action** if the next step changed.
5. If a doc moved, was archived, or was created, update its row (or add one).
6. Re-anchor "Last refresh" date in the header.

When the bucket counts at the top drift by more than ~3 in any cell, refresh the at-a-glance table.

This file's refresh cadence is **opportunistic** — touched when other docs are touched, not periodic.

---

## What this file is NOT

- Not a substitute for [`development/state.md`](development/state.md) (which holds live operational state — version, sizes, dep pins, gates).
- Not a CHANGELOG (which records what shipped, not what's stale).
- Not a TODO list (open work for the project lives in [`development/roadmap.md`](development/roadmap.md)).
- Not a per-doc review log (this is the ledger of where each doc stands, not the per-doc reasoning).

---

## Forward doc-policy commitments

Scheduled doc decisions surfaced here so they aren't forgotten when the trigger arrives.

| # | Commitment | Trigger | Source | Notes |
|---|---|---|---|---|
| 1 | **`state.md` refresh per release** — current version / binary / dep pins / in-flight slot map updated every time `VERSION` bumps. | Every release | [`CLAUDE.md`](../CLAUDE.md) "Closeout Pass" §8 | Manual today; future: add a release post-hook once the script exists. |
| 2 | **`completed-phases.md` row append per release** — move the shipped slot's row in from `state.md`'s slot map. | Every release | [`CLAUDE.md`](../CLAUDE.md) "Closeout Pass" §8 | One-line entry; CHANGELOG is the detail. |
| 3 | **`docs/audit.md` archive / fold-in** — v0.11.0-era gap analysis. The visplane/parity gaps it lists are now tracked as 0.28.5–.7 roadmap slots; fold the remaining rows into the 0.28.5 visplane work and archive. | v0.28.5 visplane work | `docs/development/roadmap.md` v0.28.x | 0.28.0's audit was hardening/perf-scoped; the Black-Book gap fold-in lands with the visplane rewrite. |
| 4 | **`docs/architecture/overview.md` perf-table refresh** — stale 0.11.0-era table replaced with a pointer to `state.md` + `bench-history.csv`; dead `rgb_buf` row corrected. | ✅ done 2026-06-07 | Tier 3 ledger row | Completed at v0.28.0 closeout. |
| 5 | **Periodic security audit** — full source scan before major releases. | Before major releases; ~every 2–3 minors | [`CLAUDE.md`](../CLAUDE.md) P(-1) §5 | Last: 2026-06-07 (v0.28.0 graphics hardening — partial, patch decoders + visplane). Prior full: 2026-04-13 (v0.24.0). Next full pinned: v0.28.7. |

---

*Initial scaffold: 2026-05-21 (v0.27.2 doc-split sweep). Refresh in place when docs are touched.*
