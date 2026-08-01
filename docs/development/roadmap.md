# cyrius-doom Development Roadmap

> **Live state** (current version, sizes, dep pins, gates, in-flight slot) lives in [`state.md`](state.md), refreshed every release.
> **Historical record** (per-version shipped milestones) lives in [`completed-phases.md`](completed-phases.md).
> **CHANGELOG** ([`CHANGELOG.md`](../../CHANGELOG.md)) is the per-release detail.
>
> This file is **forward-facing only**. When a slot ships, its row moves to `completed-phases.md` and the
> CHANGELOG carries the detail — nothing struck-through accumulates here.

**Reorganized 2026-07-25 at the v0.34.6 cut.** The file had grown to 340 lines organized *by audit round*
(2026-07-08 bites, the 2026-07-12 band, the 2026-07-17 band, July Fable) with 55 already-shipped entries
still in it and roughly 70 open items scattered across `(unslotted)` / `(follow-ups)` / vague `v0.34.x`
buckets. Every open item is now **pinned to a numbered release**; blocked work sits in explicitly-labelled
holding groups instead of interleaved with actionable cuts; and refuted/superseded items are listed once in
[§ Dropped](#dropped--do-not-re-add) so they stop costing review attention every cut.

Verified against the v0.34.6 source tree, not against the previous doc — nine audit findings that had **no
roadmap row at all** are now placed, and six rows describing work already in the tree were struck.

---

## Critical path to v1.0.0 — two releases

v1.0.0 is "plays E1M1–E1M9 start to finish, on multiple display backends, on AGNOS". Three of its six
checklist items already ship. Only two things stand in the way, and they are independently schedulable:

| Blocker | Release | Why it is the blocker |
|---|---|---|
| Episode end | **v0.35.2** | `level_advance` wraps E1M8 → E1M1 ([level.cyr:136](../../src/level.cyr#L136)) — there is no finale, so the game literally cannot be finished. |
| X11 backend | **v0.37.0** | The only unmet "multiple display backends" item; fb0 / Wayland / AGNOS-setu all ship. |

Everything else below is quality, fidelity, robustness, or performance.

---

## The 0.34.x closeout band — COMPLETE

All four cuts shipped 2026-07-26/27, every one byte-identical: **v0.34.7** perf batch C,
**v0.34.8** decoder robustness, **v0.34.9** full-IWAD capacity, **v0.34.10** the `asr()` → `>>>`
migration. Band totals: `render_frame` **1.032 ms → 369 µs (−64%)**, true spawn frame
**1.22 ms → 542 µs (−56%)**. Detail in [`completed-phases.md`](completed-phases.md).

**Two holds moved as a result:**
- **HOLD-A is unblocked on the engine side.** v0.34.9 was the shared prerequisite behind all five
  registered-WAD items — the caps no longer truncate and `TEXTURE2` is parsed. They now need only a
  registered IWAD on the box.
- **HOLD-C loses one item.** The `asr()`→`>>>` migration was the last thing gated on a toolchain
  capability; the remaining upstream holds are all cyrius **v6.5.x** perf-arc work.

**Next up is the gameplay arc**, and it changes character: everything above was byte-identical and
gated on a PPM A/B. Nothing below is.

---

## v0.35.x — The gameplay arc

**Minor bump on purpose**: unlike everything above, these cuts are *not* byte-identical — they change what
monsters do, where things sit in z, and how a level ends. The PPM A/B gate stops being sufficient here, so
each release below names a gameplay gate instead.

### v0.35.1a — Monster movement: the 8-direction chase

**v0.35.1 shipped the two REPAIRS from this row** (PRE-1 stale thing-sector cache, RC-G1 door
obstruction) — see [`completed-phases.md`](completed-phases.md). What remains is the behaviour
rewrite, deliberately alone: putting it behind the same `--ai-probe` fingerprint diff as two bug
fixes would have made any unexpected delta ambiguous about its cause, which is the same reason
v0.35.0 split sight from movement.

| # | Item | Detail |
|---|------|--------|
| F331-4 | **`P_NewChaseDir` 8-direction chase** | Chasers head straight at the player via `fixed_atan2` with a single axis-slide fallback ([things.cyr:853-870](../../src/things.cyr#L853)); vanilla's 8-direction walk with dogleg fallbacks rounds corners and paces on ledges. `grep movedir\|movecount src/` is **empty** — there is no direction state of any kind on a thing, and the thing struct is exactly full at stride 128, so the two new fields need the parallel-array precedent the `thing_sec_cache` set. Baseline symptom: **E1M1 `move_blocked=247` over 350 ticks**. |

**Three facts to hold fixed or the gate is unreadable** (each verified against the source, not assumed):

1. `MONSTER_CHASE_SPEED = 65536` is **1 map unit/tic** against vanilla's 8 — monsters move ~8× slow,
   which dominates any `move_blocked` reading. Changing it must be a separately-measured step.
2. **Monsters cannot open doors** — `doors_walk_trigger` has exactly two callers, both in
   `player.cyr`, where vanilla's `P_Move` opens them. Some fraction of those 247 blocked ticks is
   door-shaped and will not respond to chase-direction work at all.
3. An 8-way dispatch must be an **if/else ladder or a table, never a `switch`** — sparse/out-of-order
   labels are the documented cycc return-address smash that bit `thing_animate`.

Also: `p_random` is a single shared LCG, so a random-direction fallback shifts every downstream roll
and will move `ranged=` for that reason alone — it must be explained, not asserted.

**Gate**: `--ai-probe` fingerprint vs the v0.35.1 baseline (v0.35.1 left it byte-identical to v0.35.0, so either is valid as "before"). `move_blocked` must fall substantially;
`wakes`/`chases` are hard invariants (neither path consumes `p_random`); `melee` is position-driven
and *will* move; the 9 idle maps are the control and must stay byte-identical. **Capture the "before"
side first** — no fingerprint is committed anywhere in the repo, so the 247 figure is prose until
regenerated. `ai_stats_reset()` ([things.cyr:676](../../src/things.cyr#L676)) still has **zero
callers**; today's totals are correct only because the probe loop is the sole thing ticking the world.

### v0.35.1b — Real thing-z

| # | Item | Detail |
|---|------|--------|
| RC-S6 | **Things have no z** | Sprites and physics use the sector floor height. Populate and read a real z; `sprite.cyr` stops BSP-resolving `thing_floor` per frame; the `+= 32` projectile-height hack goes. |
| F331-3 | **Sight / hitscan z-slope** | `thing_check_sight` is 2D — a monster fully below a window sill still "sees" over it. Errs permissive today. |
| — | **Precise missile-vs-wall trace** | z-aware, replacing the `player_check_position` approximation that lets a rocket clip on tall steps in 2.5D. |
| F331-2 | **Vanilla ledge-glide z** | tmfloorz contacted-line tracking replacing the instant z-snap + drop-off escape-rule cure. Lowest value of the four; drop if the cut gets heavy. |

**Gate**: after v0.35.1a. Exit: mutation-proven thing-struct layout asserts (the v0.34.5 `MASKED_ENTRY`
sentinel pattern — a missed offset here is silent corruption), plus a WAD-gated regression that a monster
below a sill no longer sees over it.

### v0.35.2 — Episode end ⭐ *critical path*

| # | Item | Detail |
|---|------|--------|
| P4 | **E1M8 boss kill → finale** | Text screen, then the bunny scroll. Replaces the E1M1 wrap at [level.cyr:136](../../src/level.cyr#L136). |
| MUSIC-4 | **`D_VICTOR` + `D_INTER`** | Per-map and `D_INTRO` are already wired; these two screens have no track. |
| v1.0.0-1 | **Verify "playable start-to-finish"** | A scripted E1M1→E1M8 pty playthrough under skill_normal that reaches the finale. This *is* the v1.0.0 item-1 evidence. |

**Gate**: nothing blocks it — schedulable any time after v0.34.7.

### v0.35.3 — Combat cosmetics + two dormant one-liners

BEXP rocket-explosion frames (detonation is instant today) · full xdeath giblet animation on overkill ·
animated multi-frame muzzle flash (chaingun/rocket show only frame A — needs a flash counter decoupled from
`weapon_fire_max`) · **G-11** BFG is collectible but unselectable (fix ships here; play-verification is
registered-WAD gated) · **G-10** diagonal movement calls `doors_walk_trigger` twice with identical arguments.

**Gate**: after v0.35.1. Exit: staged-viewpoint PPMs at successive ticks per animation; a WAD-free assert
that a diagonal step produces exactly one trigger call.

### v0.35.4 — Audio + music fidelity

**MUSIC-2** MUS percussion (channel 15 is dropped entirely — E1M1's track is drum-driven, so this is the
high-impact one) · **MUSIC-3** pitch bend + expression/pan controllers · **AUDIO-6** gate the PC-speaker
beep when `audio_dev != 0` (resolve the `sound.cyr`/`audio.cyr` include-order constraint with a shared flag)
· **AUDIO-7** the four 0.30.7 cosmetic nits.

**Gate**: none. Exit: `fuzz_mus` over the new paths + a deterministic PCM dump of E1M1's track.

### v0.35.4b — `texture.cyr` Result adoption

Deferred out of v0.34.9. Typed `texture_get_column` / `texture_init` errors, aligning the texture
boundary with the `Result<T, E>` treatment `wad.cyr` already has. It was slotted into the capacity
cut on the reasoning that every error path was being touched anyway — but the capacity work rewrote
the *allocation* paths while this changes the *call surface* for every consumer, and bundling an API
change into a cut gated on "shareware output must not move" would have muddied both gates.

**Gate**: independent. Exit: byte-identical 9-map A/B (a typed-error refactor must not move pixels)
plus the existing texture asserts re-pointed at the new signatures.

### v0.35.5 — Lighting + plane parity

Closes the last of the v0.28.7 sub-audit: **brightness/lighting A-B vs the COLORMAP reference** (write the
per-light-level PPM diff to `docs/audit/`) · **RC-S8** sprite dimming still uses an ad-hoc `/96` ramp
instead of the vanilla scalelight/zlight model the walls already use · half-pixel (`FRACUNIT/2`) yslope +
column-center offsets · **F_SKY1 floors** treated as sky (rare but legal in PWADs).

**Gate**: after v0.34.7.

**Also carries a v0.34.7 leftover**: no animated texture or flat is visible from any of the 9 spawn
viewpoints (E1M1's blue pool is FLAT14, not NUKAGE), so the SLADRIP animation fixed in v0.34.7 is
gated by WAD-gated unit asserts rather than the PPM sweep. Stage a viewpoint onto a SLADRIP wall
here, where staged-viewpoint work already lives, and add it to the captured set.

### v0.35.6 — Engine-invariant audit (verification-first)

The original Black Book sub-audits, deliberately run **after** the gameplay arc so they assert the shipped
engine rather than one mid-rewrite: BSP traversal invariants (`bsp_point_on_side` parity, front-to-back walk
order) · subsector containment sweep · wall-slide collision parity · blockmap cell-list parity on E1M6 (the
C3 bounds half shipped in 0.33.8 — only the parity half remains) · visplane budget stress (E1M9 + max
things, `plane_dropped` stays 0) · **G-13** sector-0 degenerate leaf → −1 plus the caller sweep the
containment audit produces.

**Gate**: after v0.35.1. Exit: new assert groups per item — this cut's deliverable *is* tests.

---

## v0.35.7–v0.38.0 — Desktop, input, and synthesis

Ordered so the `win_*` seam churns exactly once: scaling → pointer → X11.

| Release | Theme | Contents |
|---|---|---|
| **v0.35.7** | Desktop present polish | **WF-4** aspect-correct (1.2× vertical) + fill-to-window modes · **WF-3** HiDPI / fractional scale (`set_buffer_scale`, `wp_fractional_scale_v1` + viewporter) · **WF-7** re-present in the death-wait loop so the death frame rescales · **WF-6** per-event size table for the remaining fixed-offset wire handlers. Independent of the entire gameplay arc. |
| **v0.36.0** | **Mouse / pointer input** (WF-1) | The last input mode DOOM expects on a desktop. `wl_pointer` off the seat → turn/fire/use through the existing bitmask flags; a `win_next_pointer` seam entry (fb0/AGNOS/PPM return no-pointer); `zwp_relative_pointer` + `zwp_pointer_constraints` for real mouse-look; a sensitivity option following the Sound-menu live-preview pattern. **After v0.35.7** — the seam must be settled first. |
| **v0.37.0** ⭐ | **Native X11 backend** (WF-5) | *Critical path.* `src/platform/x11/{wire,client}.cyr` mirroring the wayland/ split; MIT-SHM or PutImage present; `PM_X11` in `PresentMode`; full keyboard + the pointer seam from v0.36.0; lifecycle incl. focus clearing the input latches the way Wayland and setu already do. Closes the v1.0.0 "multiple display backends" item. |
| **v0.38.0** | **OPL2 FM synthesis via GENMIDI** | The biggest remaining fidelity win and a genuinely large module: GENMIDI parsing (GM → 2-op OPL2 patches incl. the percussion bank), an OPL2 emulator (operator FM, ADSR, feedback) in pure 16.16, routing the MUS sequencer into OPL channels, and OPL rhythm mode replacing v0.35.4's noise-voice stand-in. **After v0.35.4.** |

---

## v1.0.0 — Ship

**Blocked only on v0.35.2 and v0.37.0.** Checklist items 4 (runs on AGNOS), 5 (runs on /dev/fb0) and 6 (in
the AGNOS initrd) already ship — correct them to ✅ with their evidence at tag time, and fold item 2 (X11)
into v0.37.0 as one row rather than two.

Ship criteria: a full E1M1→E1M8 playthrough under skill_normal on **each** of the four backends (fb0,
Wayland, X11, AGNOS/setu); the full CLAUDE.md closeout pass (every `tests/*.tcyr`, bench vs the prior
closeout, `CYRIUS_DCE=1` NOP-sled recorded, security re-scan, clean-from-scratch build); and tag-time doc
truth across VERSION, `cyrius.cyml`, the CHANGELOG header, `state.md`, `completed-phases.md` and the tag.

---

## Holding groups — blocked, not scheduled

These are **not** interleaved above on purpose: each needs something that does not exist yet, and mixing
them into the release plan is what made the previous roadmap unreadable.

### HOLD-A — registered-WAD gated

Needs a registered DOOM.WAD on the box **and** v0.34.9 shipped. Neither alone is sufficient — without the
capacity lift the WAD does not load intact.

Blazing/turbo door + lift speed (specials 117/118/122/70/71 run at base speed; needs a per-thinker speed
field) · **F331-1** Baron BAL7 fireballs (shareware has no BAL7 sprites, so barons stay melee-only) ·
**G-11** BFG play-verification (thing type 2006 is registered-only) · **RC-G8 L6b** WILV intermission level
names past episode 1 · episodes 2–3, which are the first real exercise of every cap raised in v0.34.9.

### HOLD-B — hardware gated

**F-R5** 24-bpp / 8-bpp `/dev/fb0` panels hit the 32-bpp blit (1-byte row overrun on 24-bpp) — needs a
non-32-bpp panel · **AGNOS blit#39 vsync watch** — the per-frame present has no timing guard; if the kernel
ever blocks to vblank on real iron the frame budget changes · **MUSIC-5** `MUS_AMP_SHIFT`/`music_volume` are
blind defaults, need a real jack · **AUDIO-5** device-pick heuristic identifies the analog codec purely by
"device 0 has a capture sibling", which snd-aloop/dummy can win (also upstream-gated).

### HOLD-C — upstream gated

**v0.29.x items 1–4** — the deep perf pass is gated on cyrius **v6.5.x Performance-Quality** (peephole /
strength reduction, IR-driven DCE for a *real* binary shrink — today `CYRIUS_DCE=1` only NOPs ~100 KB in
place — and linear-scan regalloc, the single biggest projected win) · bench formatter `min > max` lives in
the cyrius stdlib · `#io` effect annotations await a stable annotation surface · **WF-2** GPU present needs
the mabda dep + a dmabuf/EGL path.

> **Measured 2026-08-01 on the 6.5.4 pin — the substrate is NOT yet usable for doom, so this hold stands.**
> cyrius 6.5.2 announced the `CYRIUS_IR=3` optimizing substrate as unblocked (default-vs-IR=3 corpus
> mismatches 35 → 8). **doom is one of the 8.** An `CYRIUS_IR=3` build compiles and links clean, but:
>
> | | default 6.5.4 | `CYRIUS_IR=3` |
> |---|---|---|
> | binary | 477,072 B | **518,032 B (+8.6 %, larger)** |
> | 9-map `--ppm` A/B | — | **9 / 9 differ** (5 / 5 menus match) |
> | E1M1 thing census | 6 mon / 52 items / 33 decor | **6 / 51 / 34** — a classification boundary moved |
> | `test_doom` | 366 / 366 | **363 / 366** |
>
> **Bisected to a single pass: LASE apply.** `CYRIUS_IR=3 CYRIUS_LASE_OFF=1` restores **366/366**;
> `CYRIUS_FOLD_OFF=1` does not help. The three failures are all the weapon-fire path
> (`pistol fires with ammo`, `pistol deducts 1 bullet`, `fist always fires` — each getting 0 where 1 is
> expected), so `player_try_fire` returns the wrong value under applied LASE.
>
> **A second claim was made here and is WITHDRAWN — recorded so it is not re-derived.** During the
> bisect, three runs appeared to show `CYRIUS_LASE_OFF=1` being ignored whenever `CYRIUS_FOLD_OFF=1`
> was also set, and that was written up as an upstream `_read_env` defect. It **does not reproduce**:
> 22 consecutive runs afterwards, in both a normal shell and under `env -i`, honoured both knobs. The
> installed `cycc` was byte-identical throughout (sha256 `41eb0b19…`, mtime 2026-07-30), so no
> toolchain change explains the flip and **no cause was established**. Treat the earlier observation as
> unexplained, not as a known bug; the upstream filing that had been written on it was deleted rather
> than left in cyrius's tracker.
>
> **Filed upstream**: the LASE defect above is
> `cyrius/docs/development/issues/2026-08-01-cyrius-doom-ir3-lase-miscompiles-doom.md`, re-verified
> immediately before filing. Until it is fixed, `CYRIUS_IR=3` must not be used for a doom release build.

### HOLD-D — post-v1.0.0

PWAD support (needs its own P(-1) security pass on malicious-PWAD vectors) · network multiplayer via majra ·
Wolfenstein 3D raycaster mode · WF-2 GPU present if mabda ever lands.

---

## Dropped — do not re-add

Listed once so they stop costing review attention every cut.

| Item | Why |
|---|---|
| **yukti `sys_stat` dup-fn cleanup** | REFUTED — the stdlib list has no yukti; vani is vendored. Never fired under any pin. |
| **mabda 3.0 fold / bayan-ganita carve** | REFUTED — doom uses no JSON/TOML. No-op. |
| **F26 automap line pre-clip** | Refuted 2026-07-17 — measured negligible; the automap is not in the play loop. |
| **`lib/random.cyr` adoption** | Opt-in only, never wanted; doom's `p_random` is vanilla-faithful by design. |
| **48000 Hz audio fallback** | Already shipped — 48000 is the preferred rate with a working fractional upsampler. |
| **Per-sound peak normalization** | Contradicts the deliberate faithful-loudness choice. |
| **v0.28.8 as a slot** | Superseded — absorbed into the OP items (F12→OP-7, F15→OP-5's resolver, F26 dropped). |

> **Correction worth keeping**: v0.29.x item 7 (F22 perspective-correct U/depth) was marked DONE-in-0.28.4,
> but that implementation **no longer exists** — TX-1/TX-2 deleted exactly that screen-space lerp in v0.34.2
> and replaced it with a per-column world-space ray-cast. The *property* holds; the cited code does not.

---

## AgentWorld / DOOM crossover

See [`roadmap-crossover.md`](roadmap-crossover.md) — secureyeoman spatial threat visualization via the DOOM engine.
