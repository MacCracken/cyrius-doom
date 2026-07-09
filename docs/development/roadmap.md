# cyrius-doom Development Roadmap

> **Live state** (current version, sizes, dep pins, gates, in-flight slot) lives in [`state.md`](state.md), refreshed every release.
> **Historical record** (per-version shipped milestones) lives in [`completed-phases.md`](completed-phases.md).
> **CHANGELOG** ([`CHANGELOG.md`](../../CHANGELOG.md)) is the per-release detail.
>
> This file is **forward-facing only** — slots that haven't shipped yet. When a slot ships, the row moves to `completed-phases.md` and the CHANGELOG carries the detail.

---

## Slot map (forward)

> **Re-slotted at the 0.28.4 cut (2026-06-10):** v0.28.1–.3 shipped the AGNOS bring-up arc (target support → renders on AGNOS → keyboard input) and v0.28.4 shipped gameplay correctness — see `completed-phases.md` for all four. The Black Book parity / perf themes below therefore start at **v0.28.5**. F22 (perspective-correct U/depth) was pulled forward and shipped in 0.28.4, so it is off the v0.29.x list.

| Slot | Theme | Status |
|---|---|---|
| ~~**v0.28.5**~~ | ~~Visplane pool rewrite (Black Book ch.9 / F08, subsumes F13)~~ **SHIPPED 0.32.0** (2026-07-08 — global `view_z` + real plane pool, −24% render_frame; the `test_each` refactor did NOT ride along, dropped from scope) | — |
| **(unslotted)** | Wall-path correctness: closed-door black holes (E1M3/4/7), near-parallel one-sided wall drop (E1M9), SLADRIP anim no-op, FLAT_MAX full-IWAD truncation, vendored-bsp `asr()` trunc-vs-floor | new — 2026-06-12 floor-render review |
| **(unslotted)** | Shooting cosmetics deferred from **0.30.0**: BEXP rocket-explosion frames (detonation is instant), ~~separate muzzle-flash overlay sprite~~ (**shipped 0.30.1**), full xdeath giblet animation on overkill (currently a faster death); precise missile-vs-wall trace (reuses `player_check_position`, so a rocket can clip on tall steps in 2.5D) | new — 2026-06-13 shooting overhaul |
| **(unslotted)** | **Animated multi-frame muzzle flash** for chaingun (CHGFB0) + rocket (MISFB0–D0): the 0.30.1 flash overlay shows only frame A because those guns have a 2-frame animation (`weapon_fire_frame` only ever reaches 1). Needs an independent flash-frame counter in `weapon_tick` decoupled from `weapon_fire_max`. | new — 2026-06-13 0.30.1 review (confirmed cosmetic finding) |
| **(unslotted)** | **Audio output hardening** (remaining; HW_PARAMS-fallback thresholds + ESTRPIPE recovery shipped 0.30.6; **distance/positional attenuation + stereo pan + Sound-menu live-preview/polish shipped 0.30.7**): (3) **Per-sound peak normalization** or a finer **master-gain curve** — soft lumps like `DSITEMUP` (±19) play ~6× quieter than gunfire; kept faithful for now (the `sfx_volume` gain + per-voice `lvol/rvol` are the hooks). (4) **48000 Hz fallback** — jack also accepts it; needs fractional 11025→48000 resample vs the clean 4× for 44100; **untestable on the dev box (does 44100), so deferred until a card that needs it appears** (reproduce-first). (5) **Device-pick virtual-card heuristic** — the capture-sibling test can pick snd-aloop/dummy over the real codec; **needs an upstream vani CARD_INFO API** (out of this repo's scope; `lib/vani-core.cyr` is a gitignored resolved artifact). (6) **ALSA-vs-PC-speaker double-fire gating** — `sound_*` (PC speaker) and ALSA both fire per event; gate the beep when `audio_dev!=0`. Deferred: `sound.cyr` is included before `audio.cyr` so it can't cleanly read `audio_dev` without a reorder/shared flag; low value (PC speaker usually silent). (7) **0.30.7 review cosmetic nits** (all INFO/LOW, no functional impact): `menu_handle_input` dec/inc tie-break at `sfx_volume==0` (gate `inc` on `dec==0`); drop the unreachable `sep`/`lvol`/`rvol` clamps in `audio_play_at`; far-channel `rsep=256-sep` vs original DOOM `254-sep` (1–2 unit pan offset); 1-LSB attenuation boundary step at `dist==160<<16`. | updated — 2026-06-29 0.30.7 (positional + menu polish shipped; remaining items need upstream/other-hardware, contradict faithful-loudness, or are cosmetic) |
| ~~(unslotted)~~ | ~~**Render-consistency audit Bite A — quick wins**~~ **SHIPPED 0.32.0** (2026-07-08, all six: RC-S3 sprite-lookup gaps + corpse frames, RC-S4 `fixed_atan2` octants, RC-S5 screen-driven V scaler, RC-W5 masked reverse order, RC-W1 sky-vs-sky suppression, RC-W2 closed-portal solid promotion — each staged-PPM-verified, +21 regression asserts) | — |
| ~~(unslotted)~~ | ~~**Render-consistency audit Bite C — gameplay sweep**~~ **SHIPPED 0.32.0** (2026-07-08: RC-G1 door-entombment reversal, RC-G2 trigger segment-span, RC-G3 real use-ray + blocking veto, RC-G4 closed-portal sight/hitscan, RC-G5 missile spawn check + splash LOS, RC-G7 alloc guards — +8 regression asserts, doors.cyr added to the test harness. **Release leftovers, same cut**: RC-G6 AGNOS menu edge-latch, F-R6 texture fill-mask, L8-lite monster thing-solidity). **Residuals**: monsters aren't obstruction-checked by closing doors + monster z/step parity (ride the F15 thing-sector cache); G8's L2 (speculative) / L5 BFG (unreachable in shareware) / L6b WILV (registered-only) | — |
| ~~**v0.33.0**~~ | ~~Desktop rendering — native Wayland window backend~~ **SHIPPED 0.33.0** (2026-07-09): sovereign wl protocol (no libwayland/deps), puka-pattern seam, four `src/platform/` files behind `present_mode`; double-buffered present, full keyboard, xdg lifecycle + drag-resize + close, wire-parser hardening; fb0/AGNOS/`--ppm` byte-identical; 4 adversarially-reviewed bites; AGNOS QEMU PASS; window user-verified on Hyprland. See [`completed-phases.md`](completed-phases.md) + [proposal](../proposals/wayland-backend.md) + [audit](../audit/2026-07-09-wayland-backend.md). **Follow-ups** → below. | — |
| **(follow-ups)** | **Wayland/desktop backend — post-0.33.0 follow-ups** — the seam is in; these extend it. Detailed in [§ Wayland backend follow-ups](#wayland-backend--follow-ups-post-0330) below (mouse/pointer input, GPU present via mabda, HiDPI/fractional scale, X11 backend, deeper wire hardening, aspect/fill scaling, resize-during-death). | queued — 2026-07-09 |
| ~~**v0.28.6**~~ | ~~Sprite + masked-seg depth-aware clipping (F07 / F05b / F05)~~ **SHIPPED 0.32.0** (2026-07-08, Bite B — drawseg occlusion records + `render_clip_band_build`: RC-S1/RC-S2/RC-S9/RC-W6 fixed, plus RC-W9 screen-edge endpoint re-anchor found during implementation; staged-PPM verified incl. the audit barrel + E1M5 spectre) | — |
| **v0.28.7** | Sky + wall-mapping parity (F09) | queued |
| **v0.28.8** | Structural perf — sidedef/sector index + thing-sector caches (F12 / F15) | queued, bench-gated |
| **v0.28.9–.11** | Original Black Book sub-audits: BSP+collision (.9), game-state (.10), security-refresh (.11) | queued |
| **v0.28.x** | yukti `sys_stat` dup-fn cleanup | gated on yukti rebundle (likely moot) |
| **v0.29.x** | O4 micro-perf pass + deep renderer fidelity (F06 native-scale midtex) — **F22 perspective-correct U/depth shipped early in 0.28.4** | gated on Cyrius O4 regalloc (v6.4.x) |
| **v1.0.0** | Ship: full E1 + multiple display backends + AGNOS integration | future |

> **v0.28.0 shipped 2026-06-07** (graphics review/hardening/audit/performance) — moved to [`completed-phases.md`](completed-phases.md). At the user's direction this graphics pass *became* 0.28.0, and the previously-roadmapped Black Book audit + lingering 0.27.x housekeeping were pushed **behind** it (re-slotted below).

### Wayland backend — follow-ups (post-0.33.0)

v0.33.0 shipped the native Wayland window (sovereign wl protocol, `src/platform/{wayland/*,window.cyr}` behind
the `win_*` seam + runtime `present_mode`; double-buffered CPU present, full keyboard, xdg lifecycle + drag-resize
+ close; wire-parser security hardening). The seam is designed to grow — these extend it. None block anything;
ordered roughly by user-facing value. References: [proposal](../proposals/wayland-backend.md),
[security audit](../audit/2026-07-09-wayland-backend.md), `completed-phases.md` v0.33.x.

| # | Item | Detail | Gated on / notes |
|---|------|--------|------------------|
| WF-1 | **Mouse / pointer input** (`wl_pointer`) | Bind `wl_pointer` off the seat, feed relative motion → turn (mouse-look) and buttons → fire/use. The only major input mode DOOM expects on a desktop that the keyboard-only backend lacks. Fits `input_poll_wayland` + a `win_next_pointer`-style seam addition. | New protocol surface (pointer enter/leave/motion/button/axis); relative-motion needs `zwp_relative_pointer` + `zwp_pointer_constraints` for proper mouse-look (pointer-lock). |
| WF-2 | **GPU present via mabda** (`WIN_CAP_GPU`) | Today `win_present_begin` returns a CPU `wl_shm` buffer (`WIN_CAP_SHM`) and doom blits on the CPU. A `WIN_CAP_GPU` path (mabda, as puka plans) would upload the palette-expanded frame to a texture and let the GPU scale/present — the same seam, `win_caps` already distinguishes them. | Needs mabda as a dep (doom currently has none for display) + a dmabuf/EGL path; large. The CPU shm path stays the permanent no-GPU fallback. Mirrors puka's cut #2/#3. |
| WF-3 | **HiDPI / fractional scale** | The buffer is 1× device pixels, so on a scale-2 (HiDPI) output the window renders physically small. Honor `wl_surface.set_buffer_scale` (integer) and/or `wp_fractional_scale_v1` + `wp_viewporter`, and read the output scale from `wl_output`. | `wl_output` + the fractional-scale/viewporter protocols; interacts with the integer-scale/letterbox math in `framebuf_wl_recompute`. |
| WF-4 | **Aspect-correct / fill scaling option** | Present is integer-scale + black letterbox. DOOM's 320×200 is displayed 4:3 (non-square pixels) on real hardware; and users may prefer fill-to-window over letterbox. Offer aspect-correct (1.2× vertical) and/or fit-to-window (non-integer) modes. | A scaling-mode flag + the `framebuf_present_wayland` blit loop (non-integer needs per-row interpolation or accept nearest-neighbor). Cosmetic/fidelity. |
| WF-5 | **X11 display backend** (native) | Fill the same `win_*` contract with a direct X11 protocol client (no Python bridge), so `present_mode` gains `PM_X11`. Currently the v1.0.0 "X11 display backend" item. | Direct X11 wire protocol (a second sovereign client, ~puka-sized). Keeps the v1.0.0 "multiple display backends" goal. |
| WF-6 | **Deeper wire-parser hardening** | The remaining fixed-offset event handlers (`xdg_surface.configure` @+8, `xdg_wm_base.ping` @+8, `wl_seat.capabilities` @+8, `toplevel.configure` @+8/+12) read at most `o+12`, bounded by the `size>=8` gate + the 64-byte `wl_rbuf` read-slack — a hostile short message yields a wrong value, not an OOB fault. Add a per-event size table for strictness. | Low priority under the local-compositor threat model (a malicious compositor already owns the session — see [audit](../audit/2026-07-09-wayland-backend.md) W-6). Do it if an untrusted-compositor scenario ever matters. |
| WF-7 | **Death-screen rescales on resize** (cosmetic) | The death-wait loop (`main.cyr`) pumps input (so a resize rebuilds buffers + re-blacks them) but has no `framebuf_flip`, so the red death frame freezes at the old size until respawn. Add a re-present in the death loop. | Cosmetic; both buffers are blacked on resize so no garbage shows. One-line-ish (`framebuf_flip()` in the death loop). |
| WF-8 | **AGNOS desktop backend** (long-horizon) | Once AGNOS grows a compositor, the same `win_*` seam could back the microkernel's native window path — the contract is already platform-neutral (the puka `aethersafha`-crate framing). | Post-v1.0.0; gated on AGNOS having a display server at all. |

### July Fable audit — deferred items (2026-07-04)

The [July Fable full-project audit](july-fable-audit.md) drove the **v0.31.2 playability pass** (all Tier-1 gameplay F-G1–F-G6, HIGH memory-safety F-S1, leaks F-S2/F-S4, hardening F-S3/F-S5/F-S6, UI/input F-U1–F-U5/F-U7/F-U9/F-U10, sprite rotation F-R1) and the **v0.31.3 vanilla-fidelity + sky pass** (the gameplay-review MED gaps — melee p_random, pickup rules, player-vs-thing collision, secret sectors — plus **F-R2** sky pan and **F-U8** audio rate negotiation). Remaining deferred items each need hardware the dev box lacks, are entangled with a bigger render rewrite, or need AGNOS QEMU:

| # | Item | Why deferred |
|---|------|--------------|
| ~~F-R2~~ | ~~Sky pans ~4× too slow~~ **SHIPPED 0.31.3** — 4-wraps-per-turn (ANGLETOSKYSHIFT), visually verified on E1M1's outdoor courtyard | — |
| ~~F-U8~~ | ~~OUT_RATE 48000 vs "jack takes only 44100"~~ **SHIPPED 0.31.3** — 48000→44100 negotiated fallback, upsampler reads the negotiated rate (math-verified drift-free); stale comments reconciled. Audible confirmation on the jack pending a user `--audio-test` (the agent context can't open `/dev/snd`). | — |
| **F-R3** | One-sided walls ignore `ML_DONTPEGBOTTOM` (door-track textures slide with the door) | **Entangled with native-scale-V (F06):** the current stretch-to-fit renderer always fills ceiling→floor exactly, so there is no meaningful peg-top-vs-bottom distinction to implement until native-scale V lands. |
| **F-R4** | Masked-seg `dont_peg_bottom` (+ `sd_xoff`) stored but never read in `render_masked_segs` | Same native-scale entanglement as F-R3; cosmetic dead store — wire it up with F-R3 or drop it. |
| **F-R5** | 24-bpp / 8-bpp `/dev/fb0` panels handled by the 32-bpp blit (1-byte row overrun on 24-bpp) | Needs real non-32-bpp framebuffer hardware to verify (this box is 32-bpp / the `--ppm`+bridge path doesn't use the fb blit). |
| ~~**F-R6**~~ | ~~Palette index 0 treated as transparent everywhere~~ **RESOLVED 0.32.0** (all halves: psprite blitter draws every in-post pixel; sprite dense buffer + `texture_get_column` both gained fill masks — grates get true post-gap transparency, walls stop punching pinholes at dark texels, the see-through gun is solid). | — |
| **F-U6** | AGNOS `E0`/`E1` scancode prefix is a per-call local → split extended-key across polls sticks/misfires | AGNOS-only; needs QEMU verification (not gated this cut per the reproduce-first/QEMU-verify process). |

### 2026-07-08 render-consistency audit (walls / flats / sprites + module sweep)

Full findings + staged-viewpoint evidence + repro coordinates: [`docs/audit/2026-07-08-render-consistency.md`](../audit/2026-07-08-render-consistency.md). Twenty-one findings (8 NEW self-contained, 2 keystones re-confirmed with hard evidence, the rest cross-referenced to existing slots). Recommended sequencing:

| Bite | Contents | Where it lands |
|---|---|---|
| **A — quick wins** | ~~RC-S3, RC-S4, RC-S5, RC-W5, RC-W1, RC-W2~~ | **SHIPPED 0.32.0** (2026-07-08) — all six staged-PPM-verified, +21 regression asserts |
| **B — depth clipping keystone** | ~~RC-S1, RC-S2, RC-S9, RC-W6~~ | **SHIPPED 0.32.0** (2026-07-08) — drawseg records + per-column depth bands; masked segs merged into the sprite phase's painter's walk. Bonus: **RC-W9** (seg scale/U endpoints not re-anchored after screen-edge clamping — texture swim at edges + the E1M7 right-edge stripe band) found during implementation and fixed in the same cut. |
| **— visplane keystone** | ~~RC-F1, RC-F4, RC-W8~~ | **SHIPPED 0.32.0** (2026-07-08) — global `view_z` (elevation renders across walls/flats/sprites) + R_FindPlane/R_CheckPlane/R_MakeSpans pool + both-sector portal clip; `render_frame` −24% |
| **C — gameplay sweep** | ~~RC-G1–G5, G7~~ | **SHIPPED 0.32.0** (2026-07-08); RC-G6 stays QEMU-gated |
| **D — parity polish** | ~~RC-W4, RC-F3, RC-S6/S7/S8 slices, RC-G8 bundle~~ | **SHIPPED 0.32.0** (2026-07-08: sky V anchored to the screen [the courtyard white-strip shear], flat V negated-worldY parity, projectile height+fullbright, THING_MAX sprite collection, MASKED_MAX warn, all 7 doable G8 LOWs, **plus the see-through-gun fix** — psprite/sprite blitters no longer treat palette index 0 as transparent). Residuals: RC-W3 native-scale V (0.29.x), F-R6 texture-path fill-mask (with the masked rewrite), real thing-z, G8's L2/L5/L8/L6b |

The current arc is **v0.28.x — graphics** (review / hardening / parity / performance). The language-adoption arc (v0.27.x) is complete. v0.28.0 was anchored on a multi-agent audit of the render path (`docs/audit/2026-06-07-v0.28-graphics-hardening.md`); it shipped the memory-safety hardening + safe perf, and the parity items it surfaced now drive 0.28.5–0.28.11 (0.28.1–.4 were consumed by the AGNOS bring-up arc and the 0.28.4 gameplay-correctness cut). The O4-gated perf micro-pass and the deepest renderer-fidelity work remain at v0.29.x.

---

## v0.28.x — Graphics arc

The graphics review/hardening/audit/performance pass **became v0.28.0** (shipped — see `completed-phases.md`). The previously-roadmapped DOOM Black Book audit (originally v0.25.0, re-anchored to v0.28.x) and the lingering language-arc housekeeping were pushed **behind** it, re-slotted below. Scope across the arc: close the render-path parity gaps the 0.28.0 audit surfaced, chapter-by-chapter against Fabien Sanglard's *Game Engine Black Book: DOOM* + the Unofficial DOOM Specs, with PPM diffs as ground truth. Finding IDs (Fnn) reference [`docs/audit/2026-06-07-v0.28-graphics-hardening.md`](../audit/2026-06-07-v0.28-graphics-hardening.md).

### ~~v0.28.5 — Visplane pool rewrite (keystone parity)~~ SHIPPED 0.32.0 (2026-07-08)

Implemented as DOOM's structure: `plane_get` (R_FindPlane + R_CheckPlane column-overlap split), per-column top/bottom spans, `render_plane_spans` (R_MakeSpans via `plane_spanstart`), `PLANE_MAX=128` + one-shot warn. **~24% faster** than the per-row pass it replaced (2.351 vs 3.075 ms `render_frame`, same compiler).

| # | Item | Disposition |
|---|------|-------------|
| 1 | Visplane pool keyed by (height, flat, lightnum) | ✅ per-column `top[]`/`bottom[]`, same-key planes split on overlap (F08) |
| 2 | Drop redundant per-cell flat/light re-stores | ✅ the row-union model is deleted outright (F13) |
| 3 | `lib/test.cyr` `test_each` refactor (rides along) | ✂ dropped from scope — the suite grew targeted regression groups instead (115/167) |
| 4 | Span shape + count vs reference | ✅ via staged-viewpoint PPM verification (courtyard bleed band gone, E1M3/E1M5 elevation renders) rather than a flag-gated span dump |
| 5 | Global `viewz` replacing the per-seg `eye_h = front_floor + 41` model | ✅ `view_z` BSP-resolved per frame from the view coords; walls, masked segs, drawseg deltas, AND sprites project against it — world elevation renders; supersedes the 0.29.x `vp_ceil_h` stopgap (deleted) |
| 6 | Portal clip updates bounded by BOTH sectors | ✅ opening top = lower ceiling, bottom = higher floor, in the seg clip update |

### Wall-path correctness (surfaced by the 2026-06-12 floor-render review; re-diagnosed at the 0.29.4 cut)

> **0.29.4 update (2026-06-12):** a multi-agent A/B-render workflow proved items **1 and 2 were MISATTRIBUTED** — both the closed-door "black holes" and the E1M9 "near-parallel drop" were **texture-resolution** bugs, *not* the geometry/draw defects hypothesized below. The geometry hypotheses (NEAR_CLIP degenerate depth, `fixed_mul(tx,PROJ_DIST)` 64-bit overflow, one-sided clip-drop) were all empirically refuted (toggling them does not move the black). Root causes were: PNAMES `strlen` over-read of non-null-terminated 8-byte patch names (161/350 → `patch_lumps=-1` → composite nothing → black) **and** patch-cache 8192-byte truncation of large patches. **Both fixed in 0.29.4** (all 4 sampled maps ≤0.1% viewport black). Items 6–7 are new survivors the spawn-view A/B did not exercise; items 3–5 stand.

| # | Item | Evidence | Detail |
|---|------|----------|--------|
| 1 | ~~Closed-door faces render as black holes~~ **RESOLVED 0.29.4** | E1M3/E1M7 — BIGDOOR2 = patch `DOOR2_4` (17544 B) | NOT a geometry/draw bug — the patch cache truncated `DOOR2_4` past byte 8192 (cols 58–127 lost → black). Fixed by `PCACHE_DATA_SIZE` 8192→40960. |
| 2 | ~~Near-view-parallel one-sided walls dropped entirely~~ **RESOLVED 0.29.4** | E1M9 spawn corridor (BROWN1) | NOT a geometry drop — the BROWN1 texture's patches are 8-char PNAMES names that `wad_name_eq`→`strlen` over-read and rejected → `patch_lumps=-1` → walls composited to all-black (looked like void). Fixed by null-terminating the PNAMES field in `texture_init`. |
| 6 | ~~closed-sector portals never promoted to solid~~ **RESOLVED 0.32.0** (RC-W2) | E1M1 line 151 (BIGDOOR2) staged at (1420,−2496) ang 0 | The `clip_top==clip_bottom` see-through seam across closed doors is fixed: vanilla promotion test (`back_ceil<=back_floor \|\| back_ceil<=front_floor \|\| back_floor>=front_ceil`) marks the column solid, collapses the clip (occludes sprites too), and the upper/lower sections meet across the old seam row. Staged-PPM verified. |
| 7 | ~~wall texture-U swap mirror~~ **RESOLVED 0.30.1** | reported as "walls warp when turning"; multi-agent-verified correct | the `sx1>sx2` swap in `render_seg` reordered `sx`/`ty` but not the texture-U endpoints, mirroring segs that project right-to-left (and flipping the instant a turn crossed the threshold). Fixed via a `seg_u_swapped` flag that swaps `u_left`/`u_right` in both the wall pass and `render_masked_segs`. |
| 3 | SLADRIP wall animation is a no-op | `anim_rotate_tex_3` (texture.cyr) | rotates the 32-byte entry **including the name hash**, and `render_seg` re-resolves textures by name every frame — lookup follows the rotation, content never visibly changes; rotate `width/height/def_ptr` only (or resolve indices at map load — F12 cache) |
| 4 | `FLAT_MAX = 64` silently truncates full-IWAD flats (shareware's 54 fit) | texture.cyr flat scan | full/registered IWADs exceed 64 → `flat_find = -1` fallback paths activate (gray vlines, scalelight-not-zlight shading); raise cap + log truncation |
| 5 | Vendored bsp `asr()` is round-toward-zero, not floor | lib (bsp dep) | `fixed_to_int` inherits trunc semantics → one-texel flat mis-wrap over negative world coords + doubled texel band straddling world axes; fix upstream in bsp, bump pin |

### ~~v0.28.6 — Sprite + masked-seg depth-aware clipping~~ SHIPPED 0.32.0 (2026-07-08, Bite B)

Implemented as drawseg occlusion records (screen range, endpoint scales, solid flag, eye-relative opening deltas; `DS_MAX=512` + one-shot overflow warn) + `render_clip_band_build` (per-column visibility for a subject at any depth — only *nearer* drawsegs occlude). All four items landed:

| # | Item | Disposition |
|---|------|-------------|
| 1 | Per-drawseg silhouettes (F07) | ✅ drawseg records; bands recomputed per subject from stored deltas × column scale (same projection the wall pass used) |
| 2 | Masked-seg clip against wall silhouettes (F05b) | ✅ each masked entry clips per column vs nearer drawsegs (own scale lerped → oblique crossings resolve per-column) |
| 3 | Masked-seg `clip_solid` over-paint guard (F05) | ✅ superseded — the depth test makes the "near grate / far wall" over-clip impossible by construction |
| 4 | Sprite-vs-masked + sprite-vs-sprite ordering | ✅ masked segs sort far→near by midpoint depth and merge into the sprite pass's painter's walk; sprites keep their existing far→near sort |

Bonus fix (RC-W9, found during implementation): seg scale/U interpolation endpoints are now re-anchored onto the clamped screen span — previously every seg crossing a screen edge compressed its depth/lighting/U line into the visible span (edge texture swim; the E1M7 right-edge stripe band).

### v0.28.7 — Sky + wall-mapping parity

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 0 | ~~Sky-to-sky upper-wall suppression~~ **SHIPPED 0.32.0** (RC-W1) | r_segs (`worldhigh = worldtop` when both ceilings sky) | The E1M1 courtyard STARTAN3 band is gone — both-ceilings-sky portals draw the band as sky via the shared `render_draw_sky_column`, V-anchored with the ceiling sky above. Staged-PPM verified. |
| 1 | Sky horizon anchoring + corrected angular scale — **V anchor SHIPPED 0.32.0** (absolute screen row 0; the clip-top shear + courtyard white strips are gone) | Black Book ch. 8 (R_DrawSkyColumn) | Remaining: per-column tan-distributed view-angle table (horizontal term is linear today — subtle) |
| 2 | Brightness / lighting A-B vs reference | Black Book ch. 8 (COLORMAP) | per-light-level PPM diff (carries the F25 verification forward) |
| 3 | ~~Flat V axis parity~~ **SHIPPED 0.32.0** (`render_plane_row` samples negated world-Y — flats no longer vertically mirrored vs the reference) | Unofficial Specs / r_plane semantics | — |
| 4 | Half-pixel (`FRACUNIT/2`) yslope + column-center offsets | Black Book ch. 9 | rows nearest the horizon get up to 1.5× distance; low visual impact (2026-06-12 review) |
| 5 | F_SKY1 **floors** treated as sky (vanilla: any plane with `picnum == skyflatnum`) | r_plane semantics | rare but legal in PWADs (2026-06-12 review) |

### v0.28.8 — Structural performance (O4-independent, bench-gated)

| # | Item | Detail |
|---|------|--------|
| 1 | Per-sidedef texture + per-sector flat index cache at map load | F12 — removes 3 `texture_find` + 2 `flat_find` linear scans per seg/frame |
| 2 | Per-thing sector/floor-height cache | F15 — re-walk BSP only when the thing moves |
| 3 | Automap line pre-clip | F26 — optional; negligible (overlay, not hot path) |

### v0.28.9 — BSP + collision audit (original Black Book sub-phase)

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | BSP traversal invariants | Black Book ch. 7 + bsp lib | `bsp_point_on_side` parity; front-to-back walk order |
| 2 | Subsector containment | Black Book ch. 7 | every point in a subsector returns that subsector |
| 3 | Wall-slide collision | Black Book ch. 12 | slide against angled walls matches reference |
| 4 | Blockmap query correctness (+ C3 BLOCKMAP bounds) | Unofficial Specs §4.7 | cell-list parity on E1M6; re-verify the 2026-04-13 C3 finding |

### v0.28.10 — Game state audit (original Black Book sub-phase)

| # | Item | Reference | Detail |
|---|------|-----------|--------|
| 1 | ~~`R_DrawPSprite` weapon-sprite coords~~ **RESOLVED 0.30.1** | Black Book ch. 11 | psprite hotspot `sx=1−leftoffset / sy=16−topoffset` (was `253+loff/228+toff`, pistol-only by coincidence) — all weapons/frames now anchored; muzzle-flash overlay added. Bob still rides the same `weapon_bob_x/y` deltas. |
| 2 | Episode-end intermission | Unofficial Specs §1.10 | E1M8 boss kill → text → bunny scroll |
| 3 | Visplane budget under stress | Unofficial Specs §10.4 | E1M9 + max things: no overflow (bounded by the F08 pool) |

### v0.28.11 — Security audit refresh

Partly discharged early by 0.28.0 (F01/F02/F03/F19 patch-decode propagation + F17 OOB-write fix). Remaining:

| # | Item | Detail |
|---|------|--------|
| 1 | Re-walk the 2026-04-13 CVE checklist | confirm C3 (BLOCKMAP) + H1 (WAD lump size) under current code |
| 2 | Fuzz-corpus refresh | add patch / TEXTURE1 / ADT-discriminator mutators to exercise the F01/F02/F03/F19 decoders directly |
| 3 | Bench formatter fix | `benches/doom.bcyr` sub-ms avg formatter (prints min > max) |

### Gated / watch (carried forward)

- **yukti `sys_stat` dup-fn cleanup** — strike known-issue #2 once yukti re-bundles without `sys_stat`. Did not fire under 6.0.29 or 6.0.83; likely already moot. Gated on a yukti rebundle. Does not block any 0.28.x graphics slot.
- **`texture.cyr` Result adoption** — `texture_get_column` typed errors; revisit alongside the 0.28.5 visplane rewrite.
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
| 7 | Perspective-correct U / depth across segs | ✅ **DONE — 0.28.4** | F22 — shipped: interpolate scale (∝ 1/z) for depth and u·scale for U, both ÷ the interpolated scale, in `render_seg` + `render_masked_segs`. Depth + U landed together (the "half-fix worse than none" concern is exactly why both, not just depth, were corrected in one pass). |

---

## Music (v0.31.4 wired the base; fidelity follow-ups)

`src/music.cyr` (v0.31.4) parses/sequences the MUS lumps and plays them through a simple
sine+envelope synth. Follow-ups toward fidelity:

| # | Item | Detail |
|---|------|--------|
| 1 | **OPL2 FM synthesis via `GENMIDI`** | Real DOOM timbre. The IWAD's `GENMIDI` lump (11908 B) maps GM instruments to 2-operator OPL2 patches; needs an OPL2 emulator (operator FM + envelope generators + feedback) + GENMIDI parsing. Large module — the biggest fidelity win. |
| 2 | **MUS percussion (channel 15)** | v1 skips the drum channel. Map percussion notes to a noise/drum voice (or the OPL rhythm mode once #1 lands). E1M1 is drum-driven, so this is high-impact for feel. |
| 3 | **Pitch bend + fine controllers** | v1 ignores pitch-bend (type 2) and most controllers (keeps volume + all-notes-off). Apply bend to the voice phase; honour expression/pan. |
| 4 | **Per-map + intermission/victory tracks** | `D_INTER` (intermission), `D_VICTOR` (E1M8 end) tracks — wire them to the intermission/ending screens (map + title `D_INTRO` already wired). |
| 5 | **Amplitude/level tuning** | `MUS_AMP_SHIFT` + `music_volume` default set blind (no audio on the dev box); tune on a real jack via `--music-test`. |

---

## v1.0.0 — Ship

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Plays E1M1–E1M9 (shareware) | Renders all 9 maps; full gameplay loop wired | Reframe as "playable start-to-finish under skill_normal" |
| 2 | X11 display backend (native) | Not started | Direct X11 protocol, no Python bridge — fills the same `win_*` seam as Wayland (WF-5 in the Wayland follow-ups) |
| 3 | Wayland display backend | ✅ **SHIPPED 0.33.0** (2026-07-09) | puka-pattern sovereign Wayland client; see completed-phases |
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
