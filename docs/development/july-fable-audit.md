# July 2026 Full-Project Audit — Fable pass

> **Date**: 2026-07-04 · **Version audited**: `0.31.1` (`build/doom` 554,320 B, `build/doom_agnos` 549,656 B, cycc 6.4.2)
> **Auditor**: Claude Fable 5 · **Method**: clean build + full test/fuzz/deps gates + live PPM playthrough (movement, doors, combat, automap on E1M1) + four-cluster adversarial code review (renderer / gameplay / platform-UI / WAD-security), every finding traced to source before inclusion.
>
> **Scope note**: this audit was requested as a health check *of the whole project*, oriented toward "get the game working properly." It intentionally does **not** re-derive items already tracked in [`roadmap.md`](roadmap.md) (visplane pool, global viewz, closed-sector clip inversion, FLAT_MAX/TEX_MAX truncation, native-scale midtex, sky vertical anchoring, animated muzzle flash, audio hardware-gated hardening). Everything below is either **new** or a **material correctness/severity escalation** of something the roadmap under-weights.

> ### ✅ Resolution status — **v0.31.2 + v0.31.3** (2026-07-04)
> **v0.31.2** (13 bites, [`CHANGELOG.md`](../../CHANGELOG.md) `[0.31.2]`) fixed & verified: F-G1–F-G6 (all Tier-1 gameplay); F-S1 (HIGH memory-safety, canary-verified); F-S2, F-S4 (leaks); F-S3, F-S5, F-S6 (hardening); F-U1–F-U5, F-U7, F-U9, F-U10 (UI/input/audio); F-R1 (sprite rotation).
> **v0.31.3** ([`CHANGELOG.md`](../../CHANGELOG.md) `[0.31.3]`) added the gameplay review's MED vanilla-fidelity gaps (melee `p_random`; DOOM pickup rules — stimpack/medikit cap 100 + no-pickup-at-full, maxammo caps; player-vs-thing collision; secret sectors — special-not-tag + credit-on-entry) plus two now-doable deferred items: **F-R2** (sky 4-wraps-per-turn, visually verified) and **F-U8** (Linux audio 48000→44100 rate negotiation, math-verified; audible confirmation pending a user `--audio-test`).
> **Regression asserts**: WAD-free 63 → **99**, full 101 → **137**.
> **Still deferred → [`roadmap.md`](roadmap.md)**: F-R3 (pegging) + F-R4 (masked dead field) — entangled with native-scale-V; F-R6 (palette-0) — entangled with the masked-transparency rewrite (index-0 IS the transparency key); F-R5 (24-bpp) — needs non-32-bpp fb hardware; F-U6 (AGNOS scancode) — needs QEMU.
> Individual finding entries below are the historical audit record; consult this resolution list for current status.

---

## 1. Bottom line

The engine **builds clean, passes every automated gate, and renders + drives correctly** at the plumbing level — movement, turning, collision-against-walls, doors (first activation), hitscan firing, ammo, HUD, and automap all work in a live playthrough. The renderer is visually healthy at map spawns (E1M1/E1M3/E1M7 essentially void-free; E1M9 still shows the one catalogued left-edge void band).

What it is **not** yet is *playable start-to-finish*, and the reasons are a cluster of **gameplay state-machine bugs**, not rendering. Five of them independently make a level unwinnable or lethal in a way that a first-time player hits within seconds:

1. **Melee monsters deal ~245 DPS on contact** — a wind-up timer is clobbered the same tick it is set → instant death on any melee touch.
2. **Doors and lifts work exactly once per map** — a completed thinker is never freed, so the sector stays "occupied" forever → progression soft-lock / possible trap.
3. **Chasing monsters have zero collision** — they walk through walls, closed doors, and ledges into other rooms.
4. **Spent barrels become permanent bullet shields** — a detonated barrel stays shootable and eats every shot fired across it.
5. **Inventory is wiped on every level transition** — `player_init()` runs on each `load_map()`, resetting weapons/ammo to pistol-start.

Plus one **HIGH memory-safety hole** (WAD-controlled texture height overflows a 256-byte buffer — found independently by two reviewers) and one **HIGH resource leak** (16 KB allocated per frame on the never-free bump allocator → ~2 GB/hour).

All gates green as audited:

| Gate | Result |
|---|---|
| `cyrius build src/main.cyr build/doom` | OK — 554,320 B (cycc 6.4.2), 1002 unreachable fns |
| `cyrius build --agnos …` | OK — 549,656 B |
| `cyrius test tests/doom.tcyr` | **63/63** WAD-free |
| `./build/test_doom wad/DOOM1.WAD` | **101/101** full |
| `fuzz_wad` / `fuzz_fixed` / `fuzz_weapon` | **1000 / 50000 / 2000** clean |
| `cyrius deps --verify` | **100/0** (see §7 — docs still say 37) |
| `--ppm` E1M1 | 192,015 B, `V=467 L=475 SD=648 S=85 SG=732 SS=237 N=236 T=138` |

---

## 2. Playthrough observations (PPM / pty drive harness)

Driven through a pty at 35 Hz with scripted key sequences, capturing `/tmp/doom_final.ppm` + the automap on demand, and a per-second `pos: x/y/angle/hp/ammo` instrumentation build.

- **Spawn view (E1M1)** renders correctly: textured walls, ceiling/floor flats, a zombie visible down the corridor, weapon psprite + status bar all correct.
- **Walk forward** (`w`): position advances +3 map units/tick north (matches `PLAYER_WALK_SPEED`); wall-slide collision stops the player cleanly at geometry.
- **Turn** (arrows): `player_angle` steps 4/tick walk, 8/tick run — correct.
- **Door**: walked to the first door, pressed `E` — door opened (raised), player passed into the tech corridor. **First activation works.** (Second activation is broken — see F-G2.)
- **Combat**: `f` fired the pistol, ammo `50 → 47 → …` decrementing per shot, muzzle flash drawn, fire-cadence gate correctly limiting to ~1 shot per few ticks. Hitscan connects.
- **Automap** (`TAB`): full E1M1 line geometry drawn correctly (player marker, colored linedefs, Bresenham lines clean).
- **Multi-map spawn renders**: E1M2/E1M3/E1M5/E1M7 all clean at spawn; E1M9 shows the known left-edge void column band (catalogued on the roadmap, not re-filed here).

Visual verdict: **the render path is in good shape**; the problems that stop the game from being *playable* are in the simulation, not the pixels.

---

## 3. Tier 1 — Play-breaking gameplay bugs (fix first)

These are the items that make the game unwinnable or un-fun on a first encounter. All CONFIRMED by source trace.

### F-G1 · HIGH · Melee attack wind-up clobbered → instant-death contact
[`src/things.cyr:520`](../../src/things.cyr) (in `thing_ai_tick`, `STATE_CHASE`)

The chase block sets the attack state and a 15-tick wind-up, then a *separate, non-exclusive* `if` runs the "still in sight?" branch in the **same tick**:

```
if (dist < MONSTER_ATTACK_RANGE) {
    if (sight) { thing_set_state(idx, STATE_ATTACK); thing_set_tics(idx, 15); }  # line 508-509
}
if (sight == 0) { ...grace... } else { thing_set_tics(idx, 0); }                 # line 520-522  ← wipes the 15
```

Because these are sequential `if`s (not `else if`) and `sight==1` is exactly the condition that triggered the attack, the `else` branch immediately resets `tics` to 0. Next tick `STATE_ATTACK` sees `tics==0`, deals damage instantly, and returns to `CHASE` — the loop repeats every ~2 ticks. A demon in contact lands 3–24 dmg at ~17.5 Hz ≈ **245 DPS**; the player dies in **under one second** of any melee touch.
**Fix**: gate the lost-sight/reset branch so it does not run on the tick the monster transitions to `STATE_ATTACK` (early-`return` after the attack transition, or fold both into one `if/else if` ladder — the same fix pattern already applied to the `switch`→`if/else` rewrite in `thing_animate`).

### F-G2 · HIGH · Doors & lifts fire exactly once per map (no thinker free)
[`src/doors.cyr:150`](../../src/doors.cyr) (`doors_tick`) + [`:97`](../../src/doors.cyr) (`door_find_sector`)

`doors_tick`'s `switch` has cases 1,2,3,5,6,7 but **no case 4 (`DS_CLOSED`)** and never decrements `door_count` or compacts the array. When a door finishes closing (or a lift finishes returning up) it lands in `DS_CLOSED` and sits in the thinker array forever bound to its sector. `door_open`/`lift_activate` both early-`return` when `door_find_sector()` finds any thinker for that sector — so **the door can never be reopened and the lift can never be re-ridden**. Vanilla DR doors (special 1, e.g. E1M1's first door) and platform lifts are infinitely repeatable; here backtracking through any auto-closing door, or needing a second lift ride, is a permanent block. Also hard-caps at `DOOR_MAX = 32` distinct activations per map (a used-then-idle thinker never yields its slot).
**Fix**: add a `DS_CLOSED` (and lift-idle) terminal case that marks the thinker dead and frees/compacts the slot so `door_find_sector` stops matching it; or convert the array to a free-list with an "inactive" flag. Repeatable (DR/SR/WR) vs one-shot (D1/S1/W1) then also needs distinguishing — see F-G3.

### F-G3 · HIGH · D1 "open and stay open" doors implemented as open-wait-close
[`src/doors.cyr:105`](../../src/doors.cyr) (`door_open`) + use dispatch [`:268`](../../src/doors.cyr)

Every door special funnels through `door_open`, which always schedules OPEN → wait `DOOR_WAIT` → CLOSING. Vanilla D1/S1 "open and stay open" specials (2, 31, 103) must **latch open**. Combined with F-G2, a D1 door closes after ~3 s and then can never reopen — a room a D1 door was meant to permanently unseal becomes permanently sealed, which can trap the player.
**Fix**: branch the thinker type on the door special — "stay open" types skip the wait→close transition. Needs the repeatable/one-shot distinction from F-G3's use path.

### F-G4 · HIGH · Chasing monsters move with no collision
[`src/things.cyr:496`](../../src/things.cyr) (`STATE_CHASE`)

`thing_set_x(tx + mx)` / `thing_set_y(ty + my)` are applied directly — no linedef, step-height, blockmap, or thing check. `TF_SOLID` and an `ML_BLOCKMONSTERS`-equivalent are defined but **never read anywhere in `src/`**. Monsters walk through one-sided walls, closed doors, and ledges; during the 100-tick lost-sight grace they emerge through solid walls into adjacent rooms. Reads as glitchy AI and, with F-G1, means a monster can phase through a wall directly onto the player for instant-death contact.
**Fix**: route chase movement through a `thing_check_position`-style test (reuse the player's `player_check_linedef` collision core), reverting/sliding on block.

### F-G5 · HIGH · Spent barrels are permanent bullet shields
[`src/things.cyr:458`](../../src/things.cyr) (`thing_ai_tick` early-return) + [`:650`](../../src/things.cyr) (`thing_damage` STATE_DIE guard)

A barrel is `CAT_DECOR` and spawns `TF_SOLID|TF_SHOOTABLE`. On detonation `thing_damage` sets `STATE_DIE` and calls `thing_explode`, but the `STATE_DIE → STATE_DEAD` transition that clears `TF_SHOOTABLE` lives **only** in `thing_ai_tick`, which early-returns for `cat != CAT_MONSTER` ([`:464`](../../src/things.cyr)). So a spent barrel keeps `TF_ACTIVE|TF_SOLID|TF_SHOOTABLE` **forever**, frozen on its last die frame. `player_fire_ray` still selects it as the nearest shootable target, and `thing_damage` no-ops on the `STATE_DIE` guard — so **every shot fired across a detonated barrel is silently absorbed** instead of hitting the monster behind it.
**Fix**: advance/clear decorations through the death animation too (give barrels a minimal non-monster death tick that reaches `STATE_DEAD` and drops `TF_SHOOTABLE|TF_SOLID`), or clear those flags at detonation time in `thing_damage`.

### F-G6 · HIGH · Inventory wiped on every level transition
[`src/main.cyr:59`](../../src/main.cyr) (`load_map` → `player_init`) + [`src/player.cyr:64`](../../src/player.cyr)

`load_map()` unconditionally calls `player_init()`, which resets health→100, armor→0, weapons→fist+pistol, ammo→50. `load_map()` runs on **every** exit→next-map transition ([`main.cyr:388`](../../src/main.cyr)), not just death-respawn. Vanilla carries inventory across levels — here the shotgun/chaingun you earn in E1M1 is gone at the start of E1M2, making the episode progressively harder for the wrong reason.
**Fix**: split map-geometry (re)load from player-state reset. Reset player state only on new-game / death-respawn; on level advance, keep health/armor/weapons/ammo and only reposition to the new player start.

---

## 4. Tier 2 — Memory safety & resource leaks

### F-S1 · HIGH · WAD texture height overflows the 256-byte column buffer *(found independently by 2 reviewers)*
[`src/texture.cyr:240`](../../src/texture.cyr) / callers [`src/render.cyr:520`](../../src/render.cyr), [`:1153`](../../src/render.cyr)

`texture_init` stores `th = read_le16(tex + 14)` **unclamped** (0–65535). `texture_get_column` then clears and composites up to `th` bytes into `dest`, but both callers pass `tex_col_buf = alloc(256)`:

```
for (var y = 0; y < th; y += 1) { store8(dest + y, 0); }      # OOB clear (line 240)
...
if (dy < th) { store8(dest + dy, load8(pixels + py)); }        # OOB copy, attacker-positioned (line 297)
```

A crafted WAD declaring a texture height > 256 that is referenced by any on-screen wall overflows `tex_col_buf` the first frame it draws — up to ~64 KB of zeros plus attacker-controlled patch pixels (via `topdelta`/`oy`) into whatever the bump allocator placed next (colormap / zlight / flat cache). Silent corruption → crash or worse. **Latent on DOOM1.WAD** (max height 128), but the binary accepts *any* WAD path on argv, so this is reachable, not theoretical.
**Fix**: clamp `th` to the destination capacity in `texture_get_column` before the clear loop (single clamp closes both the write and the secondary `load8(tex_col_buf + ty)` read at [`render.cyr:530`](../../src/render.cyr)); optionally also clamp at load in `texture_init`.

### F-S2 · HIGH · 16 KB allocated per frame in `sprite_render_all` (unbounded leak)
[`src/sprite.cyr:265`](../../src/sprite.cyr)

`var spr_patch_buf = alloc(16384);` sits inside `sprite_render_all`, called every frame from [`main.cyr:400`](../../src/main.cyr). On the never-free bump allocator that is **~560 KB/s at 35 Hz (~2 GB/hour)** of unrecoverable RSS growth, plus a pointless allocator-lock round-trip on the hot path. It violates the project's own lazy-init-guard rule that every neighboring buffer (`weapon_patch_buf`, `tex_col_buf`) already follows.
**Fix**: hoist to a file-scope global with the standard `if (spr_patch_buf == 0) { spr_patch_buf = alloc(16384); }` guard.

### F-S3 · MED · PNAMES count not bounded by lump size → OOB read + null-deref DoS
[`src/texture.cyr:72`](../../src/texture.cyr)

`patch_count = read_le32(pn_data)` is clamped only to `PATCH_MAX` (350), never to `(pn_size - 4) / 8`, and there is no `pn_size >= 4` guard before the count read (contrast the `TEXTURE1` path, which guards `t1_size < 4`). A truncated PNAMES (e.g. 12 bytes claiming 350 names) over-reads ~2.8 KB past the `alloc(pn_size)` block; a size-0 PNAMES makes `alloc(0)→0` and `read_le32(0)` fault. Bounded read, copied into a 9-byte scratch and used only for lookup, so impact is DoS/garbage-lookup rather than write — but it is unguarded WAD-controlled iteration.
**Fix**: `if (4 + i*8 + 8 > pn_size) break;` in the loop + a `pn_size >= 4` guard; check the `alloc` results in `texture_init` (both `pn_data` and `t1_data` are used unchecked).

### F-S4 · MED · Per-PPM-write 960 B leak in bridge mode
[`src/framebuf.cyr:304`](../../src/framebuf.cyr)

`framebuf_write_ppm` allocs `row_buf` per call. Harmless in one-shot `--ppm`, but in the no-`/dev/fb0` GTK-bridge path `framebuf_flip` writes a PPM every frame → ~34 KB/s steady leak.
**Fix**: same lazy-init global hoist as F-S2.

### F-S5 · LOW · Patch post-walk off-by-one over-read
[`src/texture.cyr:285`](../../src/texture.cyr)

Guard is `if (post_ptr >= pdata_end) break;` then `load8(post_ptr + 1)` — a 1-byte read past the cached patch when `post_ptr == pdata_end - 1`. The sprite/weapon/HUD decoders all use the correct `post_ptr + 1 >= pend` form; this decoder is the outlier.
**Fix**: change the guard to `post_ptr + 1 >= pdata_end` for parity.

### F-S6 · LOW · PPM writes are `O_CREAT|O_WRONLY` without `O_TRUNC`/`O_NOFOLLOW`
[`src/framebuf.cyr:299`](../../src/framebuf.cyr)

Fixed predictable `/tmp` paths (`/tmp/doom_frame.ppm`, written 35×/s in bridge mode), opened without `O_TRUNC` (a pre-existing larger file keeps trailing garbage) or `O_NOFOLLOW` (classic world-writable-/tmp symlink-clobber vector).
**Fix**: add `O_TRUNC` (and `O_NOFOLLOW` where available) to the open flags.

---

## 5. Tier 3 — Rendering / fidelity correctness (new, not on roadmap)

### F-R1 · MED · Sprite rotation selection is 180° off
[`src/sprite.cyr:212`](../../src/sprite.cyr)

Vanilla selects the rotation frame with an `ANG180` term: `rot = (ang_to_thing − thing_angle + ANG180 + ANG45/2) …`. This code adds only the half-step (`rel + 64`), omitting `ANG180`. Trace: a chasing monster sets `thing_angle = atan2(player − thing)` ([`things.cyr:503`](../../src/things.cyr)), so `rel = 512` → `rot = 5` (back view) for a monster facing you. **Every 8-rotation monster shows its back while approaching and its face while retreating.**
**Fix**: `rot = (((rel + 512 + 64) & 1023) * 8 / ANG360) + 1`. (Worth a close-range visual A/B on an imp before/after.)

### F-R2 · MED · Sky pans ~5× too slowly relative to geometry
[`src/render.cyr:856`](../../src/render.cyr)

`sky_col = view_angle * sky_w / ANG360 + col` scrolls one 256-texel width per full turn (0.25 texel/angle-unit) while wall geometry moves ~1.25 columns/angle-unit — so the sky looks glued to the view instead of fixed in the world. This is the **horizontal angular rate**, distinct from the roadmap's vertical `ct`-anchoring item.
**Fix**: scale the sky column by the same angular-to-screen factor the walls use (~4 texture wraps per full turn).

### F-R3 · MED · One-sided walls ignore `ML_DONTPEGBOTTOM`
[`src/render.cyr:956`](../../src/render.cyr)

The single-sided mid branch always starts texture-Y at `sd_yoff << 16`; vanilla pegs the texture bottom to the floor when the flag is set. Most visible on DOORTRAK linedefs (lower-unpegged), whose texture then slides with the door as it opens instead of staying fixed. (Full fidelity also needs the world-scale V mapping tracked as the "native-scale midtex" roadmap item, but the flag itself is ignored regardless.)
**Fix**: when `ML_DONTPEGBOTTOM` is set, start V at `(tex_h − (ceil_h − floor_h)) + yoff`.

### F-R4 · LOW · Masked-seg `dont_peg_bottom` stored but never read
[`src/render.cyr:483`](../../src/render.cyr) writes offset 112; [`:1155`](../../src/render.cyr) reads only 0..104

`render_store_masked` plumbs `dpb` (and `sd_xoff` at offset 64) into the entry, but `render_masked_segs` never loads them — lower-unpegged transparent midtextures (grates, railings) always render top-pegged. Dead field: wire it up or drop it.

### F-R5 · LOW · 24-bpp / 8-bpp framebuffers mishandled by the 32-bpp path
[`src/framebuf.cyr:232`](../../src/framebuf.cyr)

The blit assumes 16- or 32-bpp; a 24-bpp panel gets `store32` at stride 3 (one stray byte past each scaled row, and 1 byte past `fb_buf` on the last row when `xoff==0`), an 8-bpp panel gets 4-byte stores at stride 1. Real `/dev/fb0` hardware only.
**Fix**: explicit 24-bpp branch, or reject unknown bpp with a clear error.

### F-R6 · LOW/PLAUSIBLE · Palette index 0 treated as transparent everywhere
[`src/render.cyr:531`](../../src/render.cyr), [`:254`](../../src/render.cyr), [`src/sprite.cyr:411`](../../src/sprite.cyr)

DOOM encodes transparency via post gaps, not a color key. Treating palette 0 (pure black) as transparent means any art texel legitimately using color 0 becomes a pinhole to the background. Consistent engine-wide and invisible on most DOOM1 art, but diverges from vanilla; worth a one-time PLAYPAL-usage check.

---

## 6. Tier 4/5 — Input, UI/menu, audio, platform (new)

### F-U1 · MED · "New Game" falls through to instant start; skill screen unreachable
[`src/menu.cyr:267`](../../src/menu.cyr)

Same sequential-`if` bug class as F-G1: pressing `E` on "New Game" sets `menu_screen = MENU_SKILL`, and the very next `if (menu_screen == MENU_SKILL)` in the same call immediately sets `menu_result = 1; menu_active = 0` — the game starts at the default skill, and the skill-select screen is only ever seen via `--ppm-menu`. (Game is still *reachable*, so not Tier-1, but the skill menu is dead — and skill has no gameplay effect anyway, F-U2.)
**Fix**: `else if` chain, or snapshot `menu_screen` at the top of the handler before dispatch.

### F-U2 · MED · Skill selection has no effect
[`src/menu.cyr:284`](../../src/menu.cyr) + [`src/map.cyr:292`](../../src/map.cyr) + [`src/things.cyr:261`](../../src/things.cyr)

The chosen skill is never stored, and the THINGS `options` word (skill flags + multiplayer bit, offset +32) is never read — so every skill spawns the identical monster set and multiplayer-only things appear in single-player. Thing spawns need to filter on the options bitmask against the selected skill.

### F-U3 · MED · Intermission and death screens dismissed instantly (level-triggered, not edge-triggered)
[`src/level.cyr:249`](../../src/level.cyr) + [`src/main.cyr:357`](../../src/main.cyr)

Both wait loops exit on `input_flags != 0`, which is a *level* (held-key) signal. Players exit a level with `W`/`E` held (walk/switch exit); Linux tty autorepeat and AGNOS persistent key-state keep the flag non-zero, so the intermission flashes for ~28 ms and the death screen self-dismisses if you die holding a movement key. Vanilla requires a fresh press.
**Fix**: edge-detect (require a 1→0→1 transition, or clear `input_flags` on entry and wait for a new press).

### F-U4 · MED · Automap TAB toggle has no edge detection
[`src/main.cyr:334`](../../src/main.cyr)

`automap_toggle()` runs every tick `INP_TAB` is set — on AGNOS (persistent state) a held TAB flips the map at 35 Hz; on Linux autorepeat re-toggles. Needs a previous-state latch (same pattern as F-U3).

### F-U5 · MED · Split ANSI escape sequence quits the game / misfires weapon select
[`src/input.cyr:305`](../../src/input.cyr)

The Linux decoder reads ≤32 bytes; a full buffer ending in a partial `ESC [` (byte 30) fails `pos+2 < n` and the ESC falls into the `input_quit = 1` branch — **silent exit**. The orphaned `[ A` tail next read misdecodes as uppercase-A (strafe). Separately, `ESC [ 1 ; 2 C` (Shift+Arrow) leaves residue `; 2 C` where `2` (50) hits the weapon-select scan → swaps to pistol mid-fight. The comment claiming the Linux path "sets KEY_SHIFT" is false — nothing writes index 133 on Linux.
**Fix**: carry a partial escape sequence across reads (or discard it) instead of treating a bare trailing ESC as quit; don't feed escape-sequence residue bytes into the key scan.

### F-U6 · MED · AGNOS `E0`/`E1` scancode prefix is a per-call local
[`src/input.cyr:243`](../../src/input.cyr)

The extended-key prefix (`ag_ext`) is a local, so an `E0` pair split across two `kbscan` drains corrupts decode — a split arrow *break* loses the release and the arrow sticks "held" (continuous turn/strafe) until re-pressed. The Pause key (`E1 1D 45`) has no `E1` handling and decodes its inner bytes as a spurious Ctrl (fire) tap.
**Fix**: persist the prefix flag in a global across polls; add `E1` swallowing.

### F-U7 · MED · PC-speaker tone lifecycle bugs
[`src/sound.cyr:114`](../../src/sound.cyr) + [`src/main.cyr:357`](../../src/main.cyr)

`sound_tick` starts a queued tone and decrements its counter in the same call, so every tone plays N−1 ticks and all 1-tick sounds (dry-fire click, plasma, menu-move) are turned on and off within microseconds → inaudible. Separately, the dead-wait loop pumps `audio_tick()` but **not** `sound_tick()`, so a tone mid-playback at death leaves `KIOCSOUND` stuck — the speaker beeps continuously for the whole death wait, and a tone queued on the death tick plays stale after respawn. (Audible only with `/dev/console` access.)
**Fix**: start-then-decrement ordering fix in `sound_tick`; pump `sound_tick` (or force-silence the speaker) in the dead-wait/menu/intermission loops.

### F-U8 · MED/PLAUSIBLE · `OUT_RATE 48000` contradicts the on-metal Linux 44100 verification
[`src/audio.cyr:27`](../../src/audio.cyr) header vs `state.md:39`

0.31.0 switched `OUT_RATE` 44100→48000 to match the AGNOS HDA stream, and `audio_try_configure` requests **exact** 48000 (no negotiation). But the file header still says "the analog jack here takes ONLY S16/stereo/**44100**", and `state.md` records the jack verified at 44100. If that observation is literal for the dev box's codec, both `audio_open_best` passes fail and Linux audio goes silently dead. Most HDA codecs accept 48 k, but this has **not been re-verified on the metal jack since the switch**, and the comments now contradict each other.
**Fix**: re-run `--audio-test` on the real card; if 44100-only, add a 48000→44100 fallback pass to `audio_open_best`; reconcile the header comment + state.md either way.

### F-U9 · LOW · Caps-Lock alias gaps + unbound Enter
[`src/input.cyr:328`](../../src/input.cyr)

Uppercase W/S/A/D/R are aliased for Caps-Lock users but **E (use), F (fire), Q (quit) are not** — with Caps Lock on the player can move but can't open doors, fire, or quit. `KEY_ENTER` is mapped on the AGNOS table but bound to no action, so Enter does nothing in menus.
**Fix**: alias uppercase E/F/Q; bind Enter to select/use.

### F-U10 · LOW · Map-arg parse over-reads + weak validation
[`src/main.cyr:168`](../../src/main.cyr)

Reads `arg+1`/`arg+3` with no length check (an arg of `"E"` reads past its NUL) and never verifies byte 2 is `'M'` (`"E1X3"` is accepted as E1M3). Harmless OOB read of adjacent argv. Also: `sakshi` length off-by-ones at [`main.cyr:327`](../../src/main.cyr) (43 for a 42-char banner) and [`:241`](../../src/main.cyr) (31 for a 32-char string, truncating the final `s`).

---

## 7. Documentation drift (found during the audit)

- **Dep-lock count is stale**: [`state.md`](state.md) and [`CLAUDE.md`](../../CLAUDE.md) repeatedly cite a **37-entry** lock verifying "37/0". The 0.31.0 `cyrius lib sync --full` to the 6.4.2 snapshot grew it — `cyrius deps --verify` now reports **100 verified, 0 failed** and the build logs "100 deps locked, 5 commit-pinned". Every "37/0" reference across state.md, CLAUDE.md, and the roadmap should be updated to the current count, and the "clean checkout resolves 37 entries" procedure note re-measured.
- **`state.md` header still says v0.30.7 / 623,520 B** as the "current binary," while `VERSION` is `0.31.1` and `build/doom` is 554,320 B (the DCE-eligible size dropped with the 6.4.2 toolchain). The gates table, frame-time (2.956 ms from 0.30.7), and binary metrics are two minors behind; refresh against the 0.31.1 build.
- **`audio.cyr` stale comments** (cosmetic): "~186 ms @ 44100" (now ~170 ms @ 48 k), "up to ~1575 frames" (true worst case 1372), and the `audio_load` guard comment claiming AGNOS `audio_init` returns before allocating `snd_cache_*` (no longer true — caches allocate for both targets; guard is dead-but-harmless).
- **Known-issue #2** (`yukti sys_stat` dup-fn) is superseded on 6.4.2 by a **new** duplicate-symbol warning surfaced in the build: `warning: lib/yukti.cyr:57: duplicate symbol 'ERR_TIMEOUT' redefined with conflicting value (last definition wins)`. Codegen-identical/warning-only like its predecessor, but the tracked issue should note the symbol changed from `sys_stat` to `ERR_TIMEOUT`.

---

## 8. Optimizations (bench-gated; the render path is not currently a problem)

Frame time has ~7× headroom on the 22 ms budget, so these are opportunistic, not urgent. Measure before/after via `bench-history.sh` per the render-path gate.

1. **Hoist the two per-frame allocs** (F-S2 `sprite.cyr:265`, F-S4 `framebuf.cyr:304`) into lazy-init globals — fixes the leaks *and* removes two allocator-lock round-trips per frame. Trivial, zero-risk, matches the existing `weapon_patch_buf` pattern. **Do this first — it's a bug fix that happens to also be a perf win.**
2. **Direct-store inner loops for flats and wall columns** ([`render.cyr:1082`](../../src/render.cyr) spans, [`:527`](../../src/render.cyr) columns): both call `framebuf_pixel` per pixel (4 bounds checks + `y*320+x` mul + call) on loops whose ranges already guarantee in-bounds. Precompute `screen_buf + y*320` with a `+1`/`+320` step and hoist the colormap row (as F11 already did for spans). These fill most of the 64 K px/frame — realistic **10–20% frame-time** win.
3. **Memoize decoded texture columns**: `render_draw_tex_column` re-runs the full multi-patch composite for every screen column, but adjacent columns frequently resolve to the same `(tex_idx, tex_col)` once perspective-U steps < 1 texel/column. Even a **1-entry last-column cache** (compare `tex_idx+col`, skip recomposite) is a few lines; precedent is pcache's 200× on the same path.

---

## 9. Recommended fix order ("get the game working properly")

The audit's headline ask. In dependency/impact order:

1. **F-G1** melee wind-up clobber — one-line-class fix, removes instant-death; **highest playability ROI**.
2. **F-S2** sprite per-frame alloc leak — trivial, stops long-session OOM, also a perf win.
3. **F-G2 + F-G3** door/lift thinker free + latch-open — unblocks progression/soft-locks; do together.
4. **F-G4** monster chase collision — stops phase-through-walls.
5. **F-G5** barrel bullet-shield — stops absorbed shots.
6. **F-G6** inventory persistence across levels — makes the episode winnable as designed.
7. **F-S1** texture-height clamp — HIGH memory-safety; small, closes the one unclamped WAD→write path.
8. **F-U3/F-U4** intermission/death/TAB edge-detection — polish that a player notices immediately.
9. **F-U1/F-U2** menu fall-through + skill effect — restores the skill feature.
10. Then Tier-3 rendering fidelity (F-R1 sprite rotation, F-R2 sky pan, F-R3 pegging) and the remaining Tier-2 hardening (F-S3/F-S5/F-S6), each behind the standard build+test+fuzz+bench gates.

Everything in §3–§6 was traced to source and, where possible, reproduced in the live playthrough; nothing here overlaps the items already on [`roadmap.md`](roadmap.md).
