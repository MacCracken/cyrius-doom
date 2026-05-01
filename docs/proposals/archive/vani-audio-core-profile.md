# Proposal: vani `audio-core` profile (playback-only subset)

**Status**: ✅ **Accepted and shipped** in vani **0.9.1** (2026-05-01)
— collapsed from the proposed 3-cut patch series (0.9.1 → 0.9.2 →
0.9.3) into a single cut. See "Resolution" section at the bottom.

**Target (as proposed)**: vani roadmap **v0.9.1** (kicks off the work),
with the expectation that landing cleanly may span a short patch
series — **v0.9.1 → v0.9.2 → v0.9.3** — before the v1.0.0
freeze locks the profile into v1's SemVer commitment.
**Author**: cyrius-doom maintainers (first downstream consumer)
**Date drafted**: 2026-05-01
**Date resolved**: 2026-05-01 (same day — the collapse meant the
work landed on the proposal's own filing date)
**Vani baseline**: 0.9.0 (pre-1.0 RC, 106-symbol surface,
`dist/vani.cyr` = 76 KB)

---

## TL;DR

Add an opt-in `audio-core` distribution profile to vani that
ships only the playback-path surface — the `audio_*` shim from
`src/alsa.cyr`, plus whatever minimum from `error.cyr` /
`format.cyr` it transitively needs. Consumers that want the full
`vani_*` device wrapper, ring buffers, capture, mixer, and
yukti integration keep using today's `dist/vani.cyr`. Consumers
that just want "open device, set params, write bytes" pull a
much smaller bundle.

This is the single highest-leverage thing vani can do for
cyrius-doom and for any future "I just want playback" consumer.

## Motivation

### What cyrius-doom actually uses

Out of vani 0.9.0's **106 public symbols**, `src/audio.cyr` calls
exactly **six**:

```
alsa::audio_open_playback/2
alsa::audio_set_params/4
alsa::audio_prepare/1
alsa::audio_drain/1
alsa::audio_close/1
alsa::audio_write_bytes/3
```

That is 5.7% of vani's surface. All six live in the `audio_*`
legacy shim that `src/alsa.cyr` (28 KB) provides for byte-stable
compatibility with cyrius stdlib's pre-5.8 `lib/audio.cyr`.

cyrius-doom does **not** use:

- `vani_*` device wrapper (`device.cyr`, 14 KB) — yukti adapter,
  state machine, configuration presets, xrun counter
- ring buffers (`buffer.cyr`, 4 KB)
- capture (`capture.cyr`, 3 KB)
- mixer (`mixer.cyr`, 12 KB) — control-device ioctls
- error/observability (`error.cyr`, 6 KB) — `vani_err_*` typed
  results, observability toggle
- format helpers (`format.cyr`, 4 KB) — `vani_format_*`,
  bytes/frames conversions
- high-level playback (`playback.cyr`, 3 KB) —
  `vani_play` / `vani_play_from_ring`

### What it costs us today

Bumping cyrius-doom from vani 0.3.0 → 0.9.0 (same-day cut, no
audio API changes) grew the binary by **+340 KB** (259,920 →
600,608 B). The `dist/vani.cyr` bundle itself is 76 KB; the rest
is downstream codegen for code we never call. Cyrius's current
DCE pass NOPs dead functions in place rather than stripping
them, so the size lands on disk regardless of whether the
release path uses `CYRIUS_DCE=1`.

Real DCE (cyrius roadmap phase O3) will eventually shrink this,
but:

1. It hasn't landed.
2. Even with O3, paying compile-time + IR-pass cost to strip
   ~70 KB of source we never touch is wasteful when the
   playback consumer can opt out at the manifest level.
3. The single-pass include order means every line of vani's
   sources is currently parsed and codegen'd by cc2 on every
   build of every consumer.

### Why now (and why a patch series, not a single cut)

vani 0.9.0 is a pre-1.0 RC. The v1.0.0 freeze locks the
public surface and SemVer-guarantees it. The natural time to
introduce profile granularity is **before** the freeze, so that
`audio-core` becomes a stable v1 commitment rather than a v1.x
addition that risks bifurcating the ecosystem.

This work doesn't have to land in a single cut. The cleanest
path is to spread it across the **v0.9.x patch series** so each
release is independently verifiable and revertable:

- **v0.9.1** — mechanism scaffolding only (the `cyrius distlib`
  profile flag, second target, CI gate). No new public symbols;
  consumers see no change.
- **v0.9.2** — actual `dist/vani-core.cyr` emitted, second
  `api-surface.core.snapshot` captured, cyrius-doom flips its
  `[deps.vani]` `modules` field over and reports the size delta
  back upstream as the validation signal.
- **v0.9.3** — fold-in adjustments based on whatever
  `audio-core` consumers shake loose (likely: trimming
  unnecessary `error.cyr` transitive pulls; tightening the
  `alsa.cyr` boundary so the audio-core source surface stays
  self-contained).

After 0.9.3 the profile boundary is real, exercised by a
downstream consumer, and ready to lock into v1.0.0 with both
`api-surface.full.snapshot` and `api-surface.core.snapshot` as
SemVer baselines.

The v1.0.0 roadmap row #2 is "first downstream consumer landed:
cyrius-doom audio upgrade" — cyrius-doom is exactly the consumer
that would benefit from this proposal, which makes the
0.9.1/0.9.2 feedback loop unusually tight.

## Proposal

### Surface

Define a profile named **`audio-core`** containing the minimum
surface a pure-playback consumer needs:

**Required (PCM playback path)**:

- `audio_open_playback/2`
- `audio_close/1`
- `audio_set_params/4`
- `audio_set_params_full/5`
- `audio_set_sw_params/4`
- `audio_prepare/1`
- `audio_start/1`
- `audio_write/3`
- `audio_write_bytes/3`
- `audio_drain/1`
- `audio_drop/1`
- `audio_get_state/1`
- `audio_is_running/1`
- `audio_resume/1`
- `audio_query_caps/2`
- `audio_can_set_params/4`

**Excluded** (capture / control / high-level / observability):

- All of `capture.cyr`, `mixer.cyr`, `playback.cyr`, `buffer.cyr`
- `device.cyr` (the `vani_*` device wrapper) — playback-only
  consumers can call `audio_*` directly
- `error.cyr` `vani_err_*` typed-result helpers — keep only
  what `alsa.cyr` itself needs internally

That gives a profile of roughly **16 public symbols** (vs. 106)
and a source surface around **28–32 KB** (vs. 76 KB) — pending
exact transitive measurement.

### Mechanism

Three options, in increasing order of vani-side complexity:

**(A) Second dist target.** vani's `[lib]` block already feeds
`cyrius distlib`. Add a parallel target — e.g. `[lib.core]` —
that emits `dist/vani-core.cyr`. Consumers reference it via:

```toml
[deps.vani]
git = "https://github.com/MacCracken/vani.git"
tag = "1.0.0"
modules = ["dist/vani-core.cyr"]
```

Drop-in: cyrius-doom's `cyrius.cyml` changes one path. No code
change in `src/audio.cyr` because `audio_*` symbols are
identical between profiles.

**(B) Module-subset selection in the manifest.** Let consumers
pick modules à la carte:

```toml
[deps.vani]
git = "https://github.com/MacCracken/vani.git"
tag = "1.0.0"
modules = ["src/alsa.cyr", "src/error.cyr"]
```

This is more flexible but pushes the burden of getting the
include order right onto consumers, and any reshuffling on
vani's side breaks downstream manifests.

**(C) Feature flag inside `dist/vani.cyr`.** Use a build-time
constant (`VANI_PROFILE_CORE`) that gates the non-core modules.
Cyrius's compiler doesn't currently support conditional
compilation cleanly, so this is the most invasive option.

**Recommendation: (A)**. It matches the pattern yukti uses for
`dist/yukti-core.cyr` (if that exists; if not, vani sets the
precedent). It's a single new `cyrius distlib --profile core`
invocation in CI and a single new file in `dist/`. The
`api-surface.snapshot` becomes two snapshots
(`api-surface.full.snapshot` + `api-surface.core.snapshot`),
both diffed at v1.0.0 freeze.

### Compatibility

- **Existing consumers**: zero churn. `dist/vani.cyr` keeps
  shipping with the full surface.
- **New `audio-core` consumers**: opt in by changing the
  `modules` field. No source-level changes required because the
  `audio_*` shim ABI is byte-stable.
- **SemVer**: `audio-core` is a strict subset of the full
  surface, so any v1.x addition to the full surface that
  doesn't touch `alsa.cyr` is a no-op for `audio-core`. Adds
  **inside** `alsa.cyr` propagate to both profiles.

### What this unlocks long-term

1. **cyrius-doom**: trims ~340 KB of dead-code overhead, makes
   the "≤256 KB output limit" room budget realistic again, and
   stops paying parse/codegen cost for unused vani modules.
2. **agnoshi audio path** (when it lands per v1.0.0 row #3):
   if the agnoshi audio surface is also playback-only at first,
   it can adopt `audio-core` from day one.
3. **Kernel demos / initrd contexts** (AGNOS): smaller surface
   = smaller initrd, faster boot.
4. **Embedded / kiran reference engine**: same argument.
5. **Vani itself**: the profile boundary doubles as a forcing
   function for keeping `alsa.cyr` self-contained, which
   simplifies the eventual aarch64 / non-Linux backend story
   (the `audio_*` shim is the natural portability seam).

## Non-goals

- Not asking vani to drop, deprecate, or restructure any of the
  `vani_*` higher-level API. The proposal is purely additive.
- Not asking for runtime feature flags or dynamic dispatch.
  This is a build-time profile, period.
- Not asking for new functionality. Every symbol in the
  proposed `audio-core` surface already exists in vani 0.9.0.
- Not blocking vani 1.0.0. The proposal targets the v0.9.x
  patch series so the profile is exercised pre-freeze. If
  v0.9.1–0.9.3 slip and v1.0.0 ships with only the full
  bundle, this becomes a v1.1.0 additive — same end state,
  later. cyrius-doom can ship 0.27.0 against full vani 1.0.0
  today.

## Open questions for the vani maintainer

1. Is `cyrius distlib` plumbed for multiple profile outputs, or
   does it currently only emit one bundle per invocation?
2. Does yukti or any other already-folded-in stdlib library
   ship a `-core` variant that sets a precedent?
3. Should the profile name be `audio-core`, `playback`, or
   `pcm-out`? `audio-core` matches the v0.1.0 → 5.8.0 stdlib
   retirement narrative ("the original `lib/audio.cyr` was the
   playback core, that's what we're calling out as a profile").
4. Are any `vani_err_*` symbols *actually* called from inside
   `alsa.cyr`'s success paths, or is the dependency only on the
   error-path branches that the playback-only consumer never
   takes? If the latter, the audio-core profile may not need
   `error.cyr` at all and shrinks further.
5. Does the **v0.9.1 → v0.9.3 patch series** shape work for
   vani's release cadence, or would you prefer to fold the
   whole thing into a single v0.9.1 cut? The patch-series
   shape is proposed to keep each step small and revertable;
   collapsing it is fine if vani prefers monolithic cuts.
   Either way, the goal is to have it exercised before the
   v1.0.0 freeze rather than punted to v1.1.0.

## Suggested vani roadmap entry

To slot as a new top-level section between "v0.3.0 / v0.9.0 —
done" and "Optional pre-1.0 work":

> ## v0.9.1 → v0.9.3 — `audio-core` distribution profile
>
> Driven by cyrius-doom's "I use 6 of 106 symbols" usage
> profile (see `cyrius-doom/docs/proposals/
> vani-audio-core-profile.md`). Adds a second `cyrius distlib`
> target — `dist/vani-core.cyr` — containing only the
> `audio_*` PCM playback shim from `src/alsa.cyr` (~16 public
> symbols vs. 106 in the full bundle, ~28 KB vs. 76 KB
> source). Strict subset of the full surface — no SemVer risk,
> additive only. Spread across three patch releases so each
> step is independently verifiable:
>
> - [ ] **v0.9.1 — mechanism scaffolding.** `cyrius distlib`
>       profile flag wired up; second target declared in
>       `cyrius.cyml`; CI emits both bundles; no new public
>       symbols. Consumers see no change.
> - [ ] **v0.9.2 — `dist/vani-core.cyr` emitted.** Second API
>       surface snapshot at `docs/api-surface.core.snapshot`.
>       cyrius-doom flips `[deps.vani]` `modules` over to the
>       core profile and reports the binary-size delta as the
>       validation signal. (Expected: ~340 KB recovered on
>       cyrius-doom's `build/doom`.)
> - [ ] **v0.9.3 — boundary tightening.** Trim transitive
>       `error.cyr` pulls if any landed unintentionally;
>       confirm `alsa.cyr` is self-contained against the
>       core-profile build; lock both `api-surface.*.snapshot`
>       files as the v1.0.0 freeze baselines.
>
> After 0.9.3 the profile is exercised by a downstream
> consumer and ready for v1.0.0 to lock as a stable v1
> commitment rather than a v1.x addition.

## References

- Vani 0.9.0 API surface:
  `https://raw.githubusercontent.com/MacCracken/vani/0.9.0/docs/api-surface.snapshot`
- Vani 0.9.1 core API surface (post-resolution):
  `https://raw.githubusercontent.com/MacCracken/vani/0.9.1/docs/api-surface.core.snapshot`
- cyrius-doom audio consumer: `src/audio.cyr` (118 lines, 6
  vani symbols)
- cyrius-doom 0.26.1 → vani-0.9.0 size delta: 259,920 →
  600,608 B (+340 KB)
- Cyrius DCE roadmap: phase O3 (real DCE replaces NOP-sled)
  per `cyrius/docs/development/roadmap.md` "v5.4.x Queue"

---

## Resolution — vani 0.9.1, 2026-05-01

**Accepted in full. Collapsed to a single cut** (vani 0.9.1)
rather than the proposed 0.9.1 → 0.9.2 → 0.9.3 series. Justified
by the answer to **open question #4**: vani's `src/alsa.cyr` is
fully self-contained (zero cross-module references in its source),
so the boundary-tightening pass that motivated the 0.9.3 step
turned out to be unnecessary — the boundary was already clean. With
the boundary clean, mechanism scaffolding (0.9.1) and bundle
emission (0.9.2) became indistinguishable changes.

### What landed in vani 0.9.1

- `[lib.core]` profile in `cyrius.cyml` listing exactly one
  module: `src/alsa.cyr`. Same `cyrius distlib core` invocation
  pattern yukti uses for `dist/yukti-core.cyr` (answering open
  question #2 — yukti was the precedent).
- `dist/vani-core.cyr` — **29,015 bytes / 800 lines / 22 public
  symbols**. Beats the proposal's "~28–32 KB / ~16 symbols"
  estimate slightly (the extra 6 symbols are `audio_*` getters
  and the capture-side path that live alongside playback in
  `src/alsa.cyr` and were free to ship).
- `docs/api-surface.core.snapshot` captured at v0.9.1 as the
  v1.0.0 freeze baseline for the core profile (paired with
  the existing `docs/api-surface.snapshot` for the full
  profile).
- CI gate: `.github/workflows/ci.yml` regenerates **both**
  bundles and rejects drift on either.
- Release artifacts: `vani-X.Y.Z.cyr` and `vani-X.Y.Z-core.cyr`
  both shipped + checksummed. Both smoke ELFs (x86_64 +
  aarch64, the latter unblocked at 0.9.0) continue to ship
  alongside.
- Audit: `docs/audit/2026-05-01-v0.9.1-audit.md` (no findings —
  pure-additive cut).

### Answers to the proposal's open questions

1. **Multi-profile distlib?** Yes — `cyrius distlib [profile]`
   has supported it since yukti landed `[lib.core]`. Vani's
   `[lib]` and `[lib.core]` blocks emit `dist/vani.cyr` and
   `dist/vani-core.cyr` respectively.
2. **Yukti precedent?** Yes — `dist/yukti-core.cyr` set the
   pattern; vani follows it.
3. **Profile name?** Settled on `core` (matching yukti) rather
   than `audio-core` / `playback` / `pcm-out`. Cleaner under
   `[lib.core]` as a generic "stripped subset" name. Vani is an
   audio library so "core" is unambiguous in context.
4. **`error.cyr` transitive pulls?** Confirmed NO. `src/alsa.cyr`
   has zero cross-module references — single-module bundle.
   This was the open question that justified collapsing the
   0.9.3 step.
5. **Patch series cadence?** Collapsed to one cut as the
   proposal explicitly allowed ("collapsing it is fine if vani
   prefers monolithic cuts"). The work was small enough that
   spreading it across three patches would have been ceremony,
   not value.

### Action for cyrius-doom

To opt into the core profile, change one line in
`cyrius-doom/cyrius.cyml`:

```toml
[deps.vani]
git = "https://github.com/MacCracken/vani.git"
tag = "0.9.1"                         # was 0.9.0
modules = ["dist/vani-core.cyr"]      # was ["dist/vani.cyr"]
```

No change in `src/audio.cyr` — the `audio_*` ABI is byte-identical
between profiles. Expected size delta on `build/doom`: ~340 KB
recovered (the proposal's prediction). Reporting that delta back
to vani is the closing-loop signal for the resolution.

### Closing-loop signal — measured 2026-05-01

Applied on cyrius-doom main: `cyrius.cyml` / `cyrius.toml` /
`cyrb.toml` `[deps.vani]` flipped to `tag = "0.9.1"` +
`modules = ["dist/vani-core.cyr"]`; `src/main.cyr` include
swapped `lib/vani.cyr` → `lib/vani-core.cyr`; orphan
`lib/vani.cyr` symlink removed; `cyrius deps` re-resolved
(5/5 clean, lockfile rewritten with `lib/vani-core.cyr` SHA).

| Build | Bytes | Δ vs prior |
|---|---|---|
| 0.26.1 pre-bump (vani 0.3.0 / `vani.cyr`) | 259,920 | baseline |
| post-bump (vani 0.9.0 / `vani.cyr`) | 600,608 | +340,688 |
| post-resolution (vani 0.9.1 / `vani-core.cyr`) | **565,856** | **−34,752** |

Tests: 37/37 WAD-free assertions pass. WAD render
(`./build/doom wad/DOOM1.WAD --ppm`) emits E1M1, automap, and
intermission cleanly.

**Honest read on the prediction**: the proposal's "~340 KB
recovered" was overstated. Trimming vani's `dist/` source
from 76 KB → 29 KB (47 KB source delta) translated to a
binary delta of **~34 KB / 5.8 %**, not ~340 KB. The remaining
~305 KB of regression vs. the 0.26.1 baseline is unreachable
under Cyrius's current NOP-sled DCE — every public symbol
in the bundle still gets a NOPped function body in the output
regardless of whether it's called. Real recovery to the
~260 KB pre-vani size lands when **Cyrius phase O3 (real DCE
replaces NOP-sled)** ships, at which point the core profile's
smaller surface compounds with O3 to drop the dead `audio_*`
getters and capture-side path entirely.

Net assessment: profile mechanism works as designed; the
predicted size win was bottlenecked by Cyrius DCE, not by
anything vani could have done differently. The core profile
becomes the right default for cyrius-doom and the size win
will compound automatically once O3 lands — no further
vani-side action needed.
