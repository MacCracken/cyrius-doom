# Documentation Health — cyrius-doom

> **Last refresh**: 2026-07-08 v0.32.0 prep, fourth pass (**visplane pool + viewz (0.28.5) + version renamed 0.31.5→0.32.0 per user**: CHANGELOG `[0.32.0]` gained the visplane block [-24% render_frame]; state.md → elevation/plane metrics + 0.28.5/0.28.6 forward rows struck; roadmap 0.28.5 slot + section SHIPPED with per-item disposition; audit status header updated. Third pass — **Bite B + pin 6.4.30**: CHANGELOG `[0.32.0]` gained the Bite B block [drawseg depth clipping RC-S1/S2/S9/W6 + RC-W9 endpoint re-anchor] + the pin-bump Changed entry; state.md → Bites A+B [cycc 6.4.30 pinned metrics, 115/167 tests, E1M7 band re-attributed to RC-W9]; roadmap 0.28.6 slot + section + audit Bite B row marked SHIPPED; audit doc gained a same-day status header. Second pass: **Bite A shipped** [6 fixes, +21 asserts]; CLAUDE.md lock-count inlines → state.md pointers. First pass: the render-consistency audit artifact + roadmap audit section. Prior refresh: 2026-06-29 v0.30.7). | **Refresh cadence**: opportunistic — update the affected row when the underlying doc is touched. No periodic sweep cron.
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
| `CHANGELOG.md` | 2026-07-08 | ✅ Fresh | **Source of truth per CLAUDE.md.** Through **v0.32.0** (vani-core vendoring + render-audit Bites A/B + visplane pool/viewz [−24% render_frame] + toolchain pin 6.4.30; +24 asserts). Refreshed every release. |
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
| `state.md` | 2026-07-08 | ✅ Fresh | **Rotates every release.** Current to **v0.32.0** (prepared): vani vendored (`vendor/vani-core.cyr` 0.9.9, lock 34/0), Bite A render fixes, gates re-run under drifted cycc 6.4.29 (115/164 tests, 4 fuzzers, 9-map PPM, bench A/B), QEMU owed before tag. Previously current to v0.30.7 — **positional/stereo SFX + Sound-menu live preview**: binary 623,520 B (agnos 610,152 B), `render_frame` 2.956 ms, lock 37/0 (unchanged). `audio_play_at` distance atten + pan; per-voice stereo mixer; live slider preview. Gates re-run on Linux (63/63 + 101/101, fuzz 1000/50000, `--audio-test` L/R); AGNOS QEMU not gated. v0.30.7 slot row added; 0.30.6 → shipped. |
| `roadmap.md` | 2026-07-08 | ✅ Fresh | **2026-07-08 render-audit section added** (Bite A quick wins + Bite C gameplay-sweep unslotted rows; wall-path #6 → CONFIRMED; 0.28.6 evidence note + run-before-0.28.5 recommendation; 0.28.7 gained sky-vs-sky item 0). Previously: **re-slotted at v0.28.4 cut** (0.28.5–.11 carry the Black Book parity/perf themes). Floor-render + shooting-overhaul deferrals folded in as unslotted rows. v0.30.1 wall-path/psprite/flash items RESOLVED. **v0.30.7**: distance/positional attenuation + stereo pan + Sound-menu live-preview/polish **shipped** (with 0.30.6's HW_PARAMS/ESTRPIPE); the remaining audio-hardening row now carries only items needing other hardware (48 kHz), an upstream vani API (virtual-card), or that contradict the faithful-loudness choice (normalization) + low-value double-fire gating. Slot numbers vs shipped 0.29.x/0.30.x acknowledged stale — renumbering deferred. |
| `completed-phases.md` | 2026-06-29 | ✅ Fresh | **Updated at v0.30.4 cut** — added the **v0.30.x section** (0.30.0 shooting overhaul → 0.30.4 toolchain bump), catching up the previously-absent 0.30.x rows. Chronological one-line index. |
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
| `2026-07-08-render-consistency.md` | 2026-07-08 | 🔵 Dated artifact | **Render-consistency audit** (walls/flats/sprites + 14-module sweep). 21 findings with staged-viewpoint PPM evidence + repro coordinates. Status header (same day): **Bites A+B AND the 0.28.5 visplane/viewz keystone shipped in 0.32.0** (15 findings closed + RC-W9 discovered/fixed); remaining → Bite C gameplay sweep, Bite D polish. |

---

## Tier 6 — Proposals (`docs/proposals/`)

| Path | Count | Status | Notes |
|---|---|---|---|
| `proposals/archive/` | 1 | 🔵 Frozen | `vani-audio-core-profile.md` — shipped in vani 0.9.1; archived per closing-loop pattern. Cited from CHANGELOG `[0.26.2]`. |

No open proposals today. Filing a new one: drop in `docs/proposals/{kebab-case-title}.md`; archive (delete or move to `archive/`) when shipped or rejected.

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
