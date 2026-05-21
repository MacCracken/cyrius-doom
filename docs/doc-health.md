# Documentation Health — cyrius-doom

> **Last refresh**: 2026-05-21 (v0.27.3 — `Result<T, E>` adoption shipped; state.md / completed-phases.md / roadmap.md / CHANGELOG.md rows touched). Prior refresh: 2026-05-21 v0.27.2 initial scaffold. | **Refresh cadence**: opportunistic — update the affected row when the underlying doc is touched. No periodic sweep cron.
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
| `CHANGELOG.md` | 2026-05-21 | ✅ Fresh | **Source of truth per CLAUDE.md.** Through v0.27.3 (Result/`?`/match adoption at WAD boundary). Refreshed every release. |
| `CLAUDE.md` | 2026-05-21 | ✅ Fresh | **Just trimmed (2026-05-21) to durable content only** — Status section + Composes line moved to `state.md`. Pointer block in place. Project-identity / Goal / Process / Rules / Cyrius Conventions all durable. |
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
| `overview.md` | 2026-04-30 | 🟡 Stale | Module dependency graph, memory layout, performance table. **Pre-0.27.x** — binary sizes + render_frame numbers in any tables here are 0.24.x-era. Refresh action: re-anchor numbers against `state.md` (binary 585,224 B, `render_frame` 2.114 ms) at next minor closeout, or replace the perf table with a pointer at `state.md` + `bench-history.csv`. |

No numbered architecture notes yet — the convention is `NNN-kebab-case-title.md` once a second arrives. Earn first.

---

## Tier 4 — Development (`docs/development/`)

> **Important framing**: `state.md` + `roadmap.md` + `completed-phases.md` form the canonical operational surface. CLAUDE.md delegates volatile state to `state.md`; `roadmap.md` is forward-facing only; `completed-phases.md` carries the chronological shipped record. These three rotate every release.

| File | Last touched | Status | Action |
|---|---|---|---|
| `state.md` | 2026-05-21 | ✅ Fresh | **Rotates every release.** Through v0.27.3 — refreshed with new binary metric (587,752 B, +2,528 B Result tax), v0.27.3 slot moved to shipped, Architecture surface gained a Result-adoption bullet. New scheme: 0.27.4 (next) → 0.27.5 (gated) → 0.28.x → 0.29.x → v1.0. |
| `roadmap.md` | 2026-05-21 | ✅ Fresh | **Updated 2026-05-21** at v0.27.3 ship — 0.27.3 row removed from forward-list (moved to completed-phases); texture-side migration added to Watch section as deferred follow-up tied to v0.28.0. Slot map now leads with 0.27.4 → 0.27.5 → 0.28.x → 0.29.x → v1.0. |
| `completed-phases.md` | 2026-05-21 | ✅ Fresh | **Updated 2026-05-21** at v0.27.3 ship — v0.27.3 row appended (top of v0.27.x table). Chronological one-line index of shipped versions (v0.1.0 → v0.27.3). Per-version detail in CHANGELOG; this file is the index. |
| `roadmap-crossover.md` | 2026-04-30 | 🟠 Read-through | AgentWorld / secureyeoman crossover doc — spatial threat visualization via the DOOM engine. Not touched during the v0.27.x cycle; status against current secureyeoman scope not verified. Read-through at next minor closeout. |

---

## Tier 5 — Audits (`docs/audit/`)

Dated artifacts; supersede with a new audit doc rather than refresh in place.

| File | Last touched | Status | Notes |
|---|---|---|---|
| `2026-04-13-security-cve-audit.md` | 2026-04-30 | 🔵 Dated artifact | v0.24.0 CVE audit. 5 findings — 3 CRITICAL + 2 HIGH all fixed in v0.24.0. Pending refresh under v0.28.3 (Black Book audit security refresh, against post-Result paths). |
| `2026-04-15-black-book-handoff.md` | 2026-04-30 | 🔵 Dated artifact | Black Book handoff notes — surface map for the v0.28.x audit. Cited from `roadmap.md` v0.28.x section. |

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
| 3 | **`docs/audit.md` archive / fold-in** — v0.11.0-era gap analysis to be folded into the v0.28.x Black Book audit doc and archived. | v0.28.0 cycle-open | `docs/development/roadmap.md` v0.28.x section | Either fold into `docs/audit/2026-XX-XX-v0.28-black-book.md` or refresh inline; current 🟡 status is provisional pending that decision. |
| 4 | **`docs/architecture/overview.md` perf-table refresh** — pre-0.27.x numbers either re-anchored against `state.md` or replaced with a pointer at `state.md` + `bench-history.csv`. | Next minor closeout (v0.28.0) | Tier 3 ledger row | Either path is fine; pointer is preferred (less to maintain). |
| 5 | **Periodic security audit** — full source scan before major releases. | Before major releases; cycle audit ~every 2–3 minors | [`CLAUDE.md`](../CLAUDE.md) P(-1) §5 | Last full audit: 2026-04-13 (v0.24.0). Next pinned: v0.28.3. |

---

*Initial scaffold: 2026-05-21 (v0.27.2 doc-split sweep). Refresh in place when docs are touched.*
