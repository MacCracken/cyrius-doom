# cyrius-doom — Current State

> **Last refresh**: 2026-07-04 (v0.31.3 — **vanilla-fidelity gameplay pass + sky-pan fix**, follow-on to the 0.31.2 July Fable audit playability pass. Closes the MED gameplay-fidelity gaps the audit's gameplay review surfaced but that were scoped out of the play-breaking Tier-1 cut, plus the one cleanly-doable deferred render item. **Fixed**: monster melee `p_random` (was time-correlated); item/ammo pickup rules (stimpack/medikit cap 100 + no-pickup-at-full; DOOM maxammo caps); player-vs-thing collision (`TF_SOLID` was never tested); secret sectors (counted sector *tag* not *special* → E1M1 now `max_secrets=3`, credited on entry); **F-U8** Linux audio rate now negotiated (48000→44100 fallback, upsampler reads the negotiated rate, math-verified drift-free at both — audible confirmation pending a user `--audio-test` since the agent context can't open `/dev/snd`); **F-R2** sky pans at the DOOM 4-wraps-per-turn rate (visually verified on E1M1's outdoor courtyard). Binary 558,448→**558,456 B**; `doom_agnos` **553,792 B**. `render_frame` **2.952 ms**. Tests **99/99** WAD-free + **137/137** full (+9 asserts: pickups, player-thing collision); fuzz 1000/50000/2000; deps 100/0. Reviewed the full diff with a 2-agent adversarial pass (0.31.2). Still deferred → roadmap: F-R3/F-R4/F-R5/F-R6 (render, hardware/rewrite-entangled), F-U6 (AGNOS scancode, needs QEMU).) | v0.31.2 was the **playability pass from the July Fable audit** ([`july-fable-audit.md`](july-fable-audit.md)). 13 committable bites down the audit's fix order. Gameplay state-machine correctness: melee wind-up no longer clobbered (instant-death contact fixed, F-G1); doors/lifts release their thinker slots so they're repeatable (one-shot soft-lock fixed, F-G2) + D1/W1/S1 "open & stay" doors latch (F-G3); chasing monsters are collision-checked (no more wall-phasing, F-G4); spent barrels drop shootable (no more bullet-shield, F-G5); inventory carries across levels (F-G6). One HIGH memory-safety hole closed: WAD texture-height clamp (F-S1, canary-verified). Leaks fixed: per-frame sprite alloc (F-S2) + PPM row buffer (F-S4). Parser/IO hardening: PNAMES bound (F-S3), patch post off-by-one (F-S5), PPM `O_TRUNC|O_NOFOLLOW` (F-S6). UI: New Game reaches the skill screen (F-U1) + skill actually filters spawns (F-U2, E1M1 skill 1/3/5 → 4/6/29 monsters); intermission/death edge-detect a fresh press + TAB latches (F-U3/F-U4); Linux escape-seq/CSI decode + Caps-Lock E/F/Q aliases + map-arg bounds (F-U5/F-U9/F-U10); PC-speaker tone lifecycle + audio pump in wait loops (F-U7). Render: sprite rotation 180° fix — monsters face you (F-R1). Binary 554,320→**558,448 B**; `doom_agnos` **553,784 B**. `render_frame` **2.856 ms** (variance-level). Tests **90/90** + **128/128** (+27 regression asserts); fuzz 1000/50000/2000; deps **100/0**; DCE 1002/272,320 B. **AGNOS QEMU not gated** — kernel mid-overhaul; audio path unchanged for agnos in this cut. Deferred to roadmap (hardware/risky/AGNOS-only): F-R2 sky-pan rate, F-R3 one-sided pegging, F-R4 masked dead field, F-R5 24bpp, F-R6 palette-0, F-U6 AGNOS scancode prefix, F-U8 OUT_RATE re-verify.) | **Refresh cadence**: every release (ideally bumped by the release post-hook).
>
> CLAUDE.md is preferences / process / procedures (durable). This file is **state** (volatile — binary sizes, version, in-flight slots, dep tags, gates). Anything that rots within a minor lives here. See [first-party-documentation § CLAUDE.md](https://github.com/MacCracken/agnosticos/blob/main/docs/development/planning/first-party-documentation.md#claudemd).

---

## Current version

**[`VERSION`](../../VERSION)** = `0.31.3` (single source of truth — `cyrius.cyml` reads it via `${file:VERSION}`).

| Surface | Pin |
|---|---|
| Cyrius toolchain | `cycc 6.4.2` (in `cyrius.cyml`; bumped at 0.31.0 for the `sys_snd_*` audio-syscall peer). `cyrius --version` → `manifest-pin: 6.4.2`, no drift. The 6.4.2 `cyrius lib sync --full` grew the vendored `lib/` snapshot, so the resolved lock is now **100 entries** (was 37 on the 6.1–6.3 stdlib). |
| `[deps.bsp]` | `1.2.0` (git tag; bumped at 0.30.6 — source-module change, no ABI surface) |
| `[deps.vani]` | `0.9.5` (git tag, `core` profile — `dist/vani-core.cyr`, 22 `audio_*` symbols) |
| stdlib | `string`, `alloc`, `fmt`, `vec`, `str`, `io`, `fs`, `args`, `syscalls`, `hashmap`, `tagged`, `fnptr`, `freelist`, `process`, `sakshi` |

## Current binary

| Metric | Value |
|---|---|
| `build/doom` | **558,456 B** (cycc 6.4.2; +8 B over 0.31.2's 558,448 — the 0.31.3 vanilla-fidelity pass is mostly logic swaps: melee p_random, pickup caps, thing-collision, secret counting, audio rate-fallback, sky formula). `build/doom_agnos` = **553,792 B** (builds clean; AGNOS QEMU not gated this cut — kernel mid-overhaul). |
| Unreachable fns (NOP-sled today, real shrink under O3) | 1002 / 272,320 B |
| Recovery target under Cyrius O3 real DCE | ~260 KB |
| Frame time | `render_frame` **2.952 ms** (E1M1, 0.31.3, cycc 6.4.2). Variance-level — the gameplay/collision/pickup/secret fixes are off the render path; the F-R2 sky formula is the only render touch (indoor spawn byte-identical). ~7.5× headroom on the 22 ms budget. |
| Hot math | `fixed_mul` 6 ns / `asr` 4 ns / `texture_get_column` ~690 ns / `pcache_get_hit` 7 ns |

Frame-time budget: 22 ms per tick @ 35 Hz. Current: ~12× headroom.

## Gates (last green, 2026-07-04)

| Gate | Result |
|---|---|
| `cyrius deps --verify` | **100 verified, 0 failed** (the 6.4.2 `lib sync --full` snapshot; was 37 on the 6.1–6.3 stdlib). Regenerate via `rm -rf lib && cyrius deps` if a cross-target build pollutes `./lib/`. CI runs `cyrius deps` then this gate. |
| `cyrius build src/main.cyr build/doom` | OK, **558,456 B** (cycc **6.4.2**). Clean-from-scratch (`rm -rf build`) build passes. |
| `cyrius build --agnos src/main.cyr build/doom_agnos` | OK, **553,792 B**. **AGNOS QEMU not gated this cut** — the agnos kernel is mid-overhaul; the 0.31.3 pass is gameplay/pickup/collision/secret logic + a Linux audio rate-fallback (the agnos `sys_snd_*` path is hard-armed 48000 and never runs it) + a sky formula — all target-agnostic. |
| `./build/doom wad/DOOM1.WAD --audio-test` | Plays 6 centered SFX + LEFT/RIGHT pan pings over ~8 s (analog jack, S16/stereo). Audio path unchanged in 0.31.2. |
| `./build/doom wad/DOOM1.WAD --ppm-menu` | Renders all 5 menu screens (`192,015 B` each). |
| `cyrius test tests/doom.tcyr` (WAD-free, CI subset) | **99/99** (+9 over 0.31.2's 90: `pickups: health cap + no-pickup-at-full + ammo cap`, `collision: player vs solid things`; 0.31.2 added the F-G1/F-G4/F-G5/F-G6/F-R1 groups). |
| `./build/test_doom wad/DOOM1.WAD` (full) | **137/137** (99 WAD-free + 38 WAD-gated). |
| `fuzz_wad` / `fuzz_fixed` / `fuzz_weapon` | **1000 / 50000 / 2000 clean**. |
| `./build/doom wad/DOOM1.WAD --ppm` | E1M1 PPM at 192,015 B; map summary `V=467 L=475 SD=648 S=85 SG=732 SS=237 N=236 T=138` (138 raw map things). **Spawn count now skill-filtered** (F-U2): default HMP = 96 things (6 monsters, 52 items, 38 decor); skill 1 → 4 monsters, skill 5 → 29 (was a flat 29 on every skill). |
| All 9 shareware maps (E1M1–E1M9) | E1M1/E1M3/E1M7/E1M9 PPM-rendered + **visually verified** at the 0.29.4 cut: the black-hole/void family is gone (≤0.1% viewport black). Remaining wall items catalogued on the roadmap (closed-sector-clip-inversion = closed-door-in-play, U-swap mirror, SLADRIP no-op, FLAT_MAX, bsp asr). |
| bsp 1.1.3 standalone (upstream) | 79/79 tests, 13/13 benches sub-μs, 25K fuzz iters |
| Lint / fmt | clean across all 20 src modules + vendored libs |

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
| **v0.31.3** | prepared 2026-07-04 (Linux verified — clean build/99+137 tests/fuzz/bench/deps 100-0; sky visually verified on E1M1 outdoor courtyard; AGNOS builds clean, QEMU not gated. **Audio audible-verify pending** — agent context can't open `/dev/snd`, user runs `--audio-test`) | **Vanilla-fidelity gameplay pass + sky-pan fix.** Closes the MED gameplay-fidelity gaps from the July Fable audit's gameplay review (scoped out of the 0.31.2 Tier-1 cut): monster melee `p_random`, DOOM item/ammo pickup rules (stimpack/medikit cap 100 + no-pickup-at-full, maxammo caps), player-vs-thing collision (`TF_SOLID`), secret sectors (special-not-tag + credit-on-entry, E1M1 `max_secrets=3`). Plus deferred-audit items now doable: **F-U8** Linux audio rate negotiation (48000→44100 fallback, upsampler reads negotiated rate) and **F-R2** sky 4-wraps-per-turn pan. +9 regression asserts. Binary 558,448→558,456 B. |
| **v0.31.2** | prepared 2026-07-04 (Linux verified — clean build/90+128 tests/1000-50000-2000 fuzz/bench/deps 100-0/PPM+menu; AGNOS builds clean, QEMU not gated — kernel mid-overhaul) | **Playability pass from the July Fable audit** ([`july-fable-audit.md`](july-fable-audit.md)) — 13 committable bites down the audit's fix order. Tier-1 gameplay: F-G1 melee wind-up clobber (instant-death fixed), F-G2/F-G3 door/lift thinker lifecycle + stay-open doors (soft-lock fixed), F-G4 collision-checked chase, F-G5 spent-barrel shield, F-G6 inventory carry. HIGH security: F-S1 texture-height clamp (canary-verified). Leaks: F-S2 sprite alloc, F-S4 PPM row buf. Hardening: F-S3/F-S5/F-S6. UI: F-U1 menu fall-through, F-U2 skill filter, F-U3/F-U4 edge-detection, F-U5/F-U9/F-U10 input, F-U7 audio pumping. Render: F-R1 sprite rotation. +27 regression asserts. Binary 554,320→558,448 B. Deferred → roadmap: F-R2/F-R3/F-R4/F-R5/F-R6, F-U6, F-U8. |
| **v0.31.1** | 2026-07-04 | Audio iron-validated on archaemenid (root cause was an agnos LAPIC-timer miscalibration, fixed kernel-side in agnos 1.52.8); restored per-SFX logs, DMX pad skip. |
| **v0.31.0** | 2026-07-04 | Sound on AGNOS via `sys_snd_*` (#64–#69); OUT_RATE 44100→48000 + Bresenham upsampler; adaptive ring-fill producer; toolchain 6.3.5→**6.4.2** (lock grew 37→100 via `lib sync --full`). |
| **v0.30.7** | shipped 2026-06-29 | Positional/stereo SFX + Sound-menu live preview. `audio_play_at` distance attenuation + stereo pan; per-voice stereo mixer. Binary 621,080→623,520 B. |
| **v0.30.6** | shipped 2026-06-29 | **SFX volume + Sound menu + ALSA hardening + bsp bump.** Options→Sound sub-menu (`MENU_SOUND`) with a DOOM thermometer slider → master `sfx_volume` (0–15) gain in `audio_tick` (v=15 bit-identical full, v=0 mute). `-ESTRPIPE` suspend/resume recovery; `audio_set_sw_params` gated on `audio_explicit_params` (fallback-buffer silence fixed). bsp 1.1.5→1.2.0 (no ABI; lock 37/0). Pre-cut 29-agent review: 20/20 confirmed, zero defects; 3 nice-to-haves → roadmap. Binary 619,224→621,080 B; `render_frame` 2.950 ms; 63/63 + 101/101; fuzz 1000/50000. |
| **v0.30.5** | shipped 2026-06-29 | **Audio revive.** The dead ALSA/WAD-SFX path (`audio_play` had zero callers) is now live: 8-voice non-blocking software mixer (`audio_tick`), analog-card auto-pick (`audio_open_best` — old hardcoded card0 was HDMI), S16/stereo/44100 output (U8→S16 + mono→stereo + clean 4× upsample from 11025, since HDA rejects S8/mono/11025), idempotent init + `audio_shutdown` at exit, AGNOS `#ifdef` guards + `audio_load` null-cache guard, DMX validation, `--audio-test` harness, real WAD sounds wired to weapon/door/pickup/pain/death events. Pre-cut 29-agent review: 18 confirmed, 1 HIGH fixed (AGNOS null-write), MED/LOW → roadmap. Binary 613,720→619,224 B; `render_frame` 3.082 ms; 63/63 + 101/101; fuzz 1000/50000; deps 37/0. |
| **v0.30.4** | shipped 2026-06-29 | **Toolchain + dependency bump.** cyrius pin 6.2.44→6.3.5 (drift closed), vani 0.9.4→0.9.5, bsp 1.1.3→1.1.5; `cyrius.lock` regenerated (37/0, transitive trio unmoved). No logic changes (only the banner). Picks up cyrius CVE-32 resolver fix. Binary 612,672→613,720 B; `render_frame` 2.971 ms; 63/63 + 101/101; fuzz clean. |
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
| **v0.30.2** | prepared 2026-06-14 (Linux build + tests green; **AGNOS QEMU verification of the new input path PENDING** — deferred per user to avoid colliding with in-progress kernel work; not yet committed/tagged) | **Player-feedback + controls patch.** (1) **Combat coredump** fixed — `thing_animate`'s sparse/out-of-order `switch` smashed its own return under cycc codegen; rewrote as an `if/else` ladder. (2) Dead main-menu **Options** item → navigable `MENU_OPTIONS` screen (display-only stubs). (3) **Fist thumb** raised — per-weapon `weapon_y_lift`=14 px so the thumb clears the status bar (DOOM clips it in status-bar mode; matches the reference fist sprite). (4) **Controls reworked** — AGNOS gains DOOM-faithful **Ctrl-fire** (`0x1D`/`E0 1D`) + **Shift-to-turn** (`0x2A`/`0x36`; arrows + A/D branch strafe↔turn; Caps Lock inherently ignored on the raw-scancode path); **Linux** keeps the simple, Caps-Lock-immune scheme (arrows turn, A/D strafe, F fires — a raw tty can't see bare Ctrl/Shift and uppercase-letter Shift is ambiguous with Caps Lock; uppercase W/A/S/D/R alias their movement actions). Binary 610,576→612,576 B (+2,000). Tests 63/63 WAD-free, 101/101 full. cycc 6.2.5. |
| **v0.30.1** | prepared 2026-06-13 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Player-feedback rendering patch.** Four live-play bugs: (1) weapon psprite position — `253+loff/228+toff` matched only the pistol ready frame by coincidence → DOOM hotspot `1−loff/16−toff` via shared `render_blit_psprite` (fist now lower-right, no more lurch while firing); (2) **muzzle-flash overlay** added (`render_draw_flash`, `PISF/SHTF/CHGF/MISF` fullbright — closes 0.30.0-deferred item); (3) **wall texture-U mirror** on turn — `sx1>sx2` swap now reorders U endpoints in wall + masked passes (closes 0.29.4-deferred U-swap-mirror); (4) **enemies always faced player** — `sprite_find_frame` now resolves DOOM combined-rotation lumps (`TROOA2A8`) + returns a flip flag, `sprite_render_all` mirrors columns. Plus SEE/CHASE walk-strobe gated to ~4-tick. Multi-agent diff review (9 findings, 1 confirmed-cosmetic: chaingun/rocket flash_max capped to reachable=1, animated multi-frame flash → roadmap). No control changes (fire stays `F`). Binary 608,344→610,576 B; `render_frame` 2.957 ms (render path unchanged). |
| **v0.30.0** | prepared 2026-06-13 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Shooting-mechanics overhaul.** Multi-agent review of input→hitscan→damage→psprite (27 confirmed). Fixed: unbounded fire cadence (ammo+hitscan every tick → now gated on weapon-ready), shoot-through-walls (LOS via `thing_check_sight`), pain-lock (painchance-gated), corpse re-kill + vanishing corpses, psprite `alloc`/frame leak, weapon-7 silent-fire. Fidelity: rocket→projectile+splash (`thing_spawn_missile`/`thing_explode`), barrels explode + chain, shotgun 7-pellet spread, per-weapon refire cadence, sector-tracked weapon light + muzzle-flash fullbright, `p_random` PRNG. Tests +26 (37→63 WAD-free, 75→101 full) + `fuzz_weapon` 20k. Audit `2026-06-13-shooting-hitscan.md`. Binary 602,032→608,344 B; `render_frame` 3.10 ms (render path unchanged). Deferred (cosmetic): BEXP explosion frames, muzzle-flash overlay sprite, xdeath giblets → roadmap. |
| **v0.29.4** | prepared 2026-06-12 (Linux + **AGNOS QEMU verified**; not yet committed/tagged) | **Wall black-holes + walk-through-walls fixed.** Walls: A/B-render diagnosis pinned the "void/black-hole" family to **texture resolution, not geometry** — (1) PNAMES `strlen` over-read of non-null-terminated 8-byte patch names [161/350 → `patch_lumps=-1` → black; fixed by a null-terminated copy in `texture_init`], (2) patch-cache `PCACHE_DATA_SIZE` 8192→40960 [big patches truncated past byte 8192 → black columns]. All 4 sampled maps ≤0.1% viewport black (E1M9 70.7%→0.1%). Collision: blockmap cell-index double-shift collapsed every query to cell (0,0) → walk-through-walls [latent since 0.13.0] + a new `doom.tcyr` regression group [73→75]. `render_frame` 2.451→2.93 ms (PNAMES fix = real wall draw, A/B-isolated; not the cache). Refuted/deferred: NEAR_CLIP overflow [not a black cause], closed-sector-clip-inversion [HIGH, closed-door-in-play] + U-swap mirror [MED] → roadmap. |
| **v0.29.3** | shipped 2026-06-12 | **Flat rendering fixed** — `render_flat_spans` distance was missing the ×`PROJ_DIST` factor (160× too small → world step ~0 → one texel smeared per row = the "untextured gray floors" bug on AGNOS hardware + Linux; same error pinned zlight fullbright). Follow-ups in the same cut: sky rows no longer registered into `vp_ceil` (F_SKY1 is a real flat — span pass was overdrawing the sky once flats textured), fake contrast no longer leaks into plane lights, per-row `vp_ceil_h` so ceiling spans invert the same height the wall pass projected. Multi-agent review (units/fidelity/refutation + 2 sweeps + 9-map visual + AGNOS QEMU in-game). Review findings → roadmap (visplane slot evidence + new unslotted wall-path bug table). |
| **v0.29.2** | shipped 2026-06-11 | Toolchain pin → **6.1.37** (fixes the `--agnos` 3-op-multiply miscompile; 0.29.1 2-op workarounds reverted to clean chained form in `framebuf.cyr` + `render.cyr`, QEMU-verified fb_buf=256000 / scalelight=6144 / zlight=16384). World-tick **aliveness**: removed the 1000-unit `MONSTER_SIGHT_RANGE` cap (monsters wake on LOS like real DOOM — was keeping all but the nearest asleep), and idle monsters now animate their two standing frames (were pinned to a static frame). Reproduced via a pty harness driving the real-tty input path. |
| **v0.29.1** | shipped 2026-06-11 | World-tick froze without input — two platform-specific causes (Linux: `read(stdin)` blocked for non-tty stdin → `input_enable_raw_mode` now forces `O_NONBLOCK` via `fcntl`; AGNOS: a 255 KB/frame `fb_buf` heap overflow from a cycc `--agnos` 3-op-multiply miscompile stomped the render tables → 2-operand workaround). Both found by reproducing the freeze, not static reading. |
| **v0.29.0** | shipped 2026-06-11 | AGNOS: the kernel scales now — `framebuf_blit_agnos` palette-converts a FIXED 256 KB 32bpp frame and passes the integer scale to `blit`#39 a4[39:32] (agnos 1.44.20); ring 3 writes 64K px/frame instead of scale²·64K, old scale-3 heap cap gone. |
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
| 2 | `lib/yukti.cyr:57: duplicate symbol 'ERR_TIMEOUT' redefined with conflicting value (last definition wins)` — on cycc 6.4.2 the yukti duplicate-symbol warning is now `ERR_TIMEOUT` (was `sys_stat` on the 6.0–6.3 stdlib; the earlier dup-fn moved/resolved when the lib snapshot changed). | Warning-only, last-definition-wins, codegen builds clean. Kept tracked until yukti re-bundles without the collision. Gated on a yukti rebundle. |
> Issue #3 (cycc `--agnos` 3-operand-chained-constant-multiply miscompile — `alloc(320*200*4)` folded to 800 not 256000 on `--agnos` only, root cause of the 0.29.1 AGNOS world-tick freeze) was **resolved in 0.29.2** by the toolchain pin bump to cycc 6.1.37. The 0.29.1 2-operand workarounds in `framebuf.cyr` + `render.cyr` were reverted to the clean chained form and the fold **verified on the actual `--agnos` binary in QEMU** (serial: fb_buf=256000, scalelight=6144, zlight=16384). Confirmed broken on cycc 6.1.29 + 6.1.35.
>
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
