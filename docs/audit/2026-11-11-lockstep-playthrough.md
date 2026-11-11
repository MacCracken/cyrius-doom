# `--lockstep` and the scripted playthrough — v0.37.0 (2026-11-11)

P(-1) note for the one new engine surface v0.37.0 adds (`src/lockstep.cyr`, the
`lockstep_read` path in `src/input.cyr`), and the engine behaviours the
playthrough harness (`scripts/playthrough/`) confirmed or exposed while driving
E1M1–E1M8. One engine finding (RK-1, §4), recorded and slotted, not fixed here.

## 1. The new surface

| Item | Assessment |
|---|---|
| How it is reached | Only `--lockstep` on the command line, parsed in `main.cyr`'s Linux block. Not compiled into a reachable path on AGNOS (the flag is never parsed there; `lockstep_read` is dead code, as the rest of the tty path is). |
| What it reads | Key bytes from stdin, which is what an interactive session reads. Bytes up to the sync byte `0x1F` go to the unchanged tty decoder; a burst longer than the 32-byte decode buffer is truncated, never overrun. A byte after the sync in the same read is dropped (the harness sends one tick at a time). |
| What it writes | A text record to fd 3. `main` refuses to start the mode unless `fcntl(3, F_GETFD)` succeeds, so it never writes into a descriptor the caller did not hand it. A failed or short write sets `input_quit`, and doom exits cleanly. The record holds game state only (positions, counters, heights), no addresses. |
| Blocking | `poll(2)` on stdin, then `read`. On a raw tty with VMIN=0/VTIME=0 a read returns 0 when nothing is ready, so 0 is not treated as end of file: hang-up (`POLLHUP`), an error or `POLLNVAL` ends the run. A harness that dies leaves no doom spinning. |
| Buffers | `ls_buf` is 64 KB on the heap, flushed whenever it is within 24 bytes of full, so no record size can overflow it. `ls_sec_prev` is `MAP_MAX_SECTORS` × 24 bytes (floor, ceiling, special), indexed only below `map_num_sectors`, which `map_load` caps at `MAP_MAX_SECTORS`. |
| Side effects in normal play | None. `lockstep_on` stays 0 unless the flag is given. The screen markers (`game_screen`) are assignments that nothing in the engine reads. The record's own sight checks save and restore `ai_stat_sight_calls`, so `--ai-probe` counts are unchanged. Gate: 52 PPMs + 603 `--ai-probe` lines byte-identical to v0.36.3, plain and release; AGNOS 64,000 / 64,000. |
| Audio | `--lockstep` opens no PCM device and no PC speaker (`audio_headless`, no `sound_init`): a harness run cannot grab the desktop's audio. |

No finding to fix in the new surface.

## 2. Engine behaviour the harness relies on (confirmed in play)

- **Use is front-side only** (U-11, `doors.cyr`) and takes the nearest special
  line the 64-unit ray crosses. Two special lines side by side (E1M2 lift 180:
  `919` on its edge, `689` on its wall) mean one of them is unusable from most
  spots; the bot simulates the ray before pressing. A walk line counts too:
  E1M6's `602` (special 76) runs 40 units in front of switch `599`, so the
  switch is pressed from between the two, never from behind 602 — vanilla's
  use traversal stops at the first special line the same way.
- **The drop-off escape rule** (`player.cyr` `move_check_linedef`): a player
  inside a ledge line's radius may move along it but not across it. A planner
  that ignores this sees every drop-off as a dead end.
- **Lifts** lower, wait 105 tics and return; a player standing on one rides it
  (`things_resync_z_in_sector`). Verified tick by tick on E1M2 lift 109.
- **Walk-over doors that close** (special 90 on E1M4 / E1M5) can shut a player
  in. The way out is a trigger on the inside (E1M4: the open-stay lines 348–351
  around the blue key, which a pickup from outside the box does not cross).

## 3. Leads checked and closed

- **E1M8 "boss skip" — not a bug.** A run appeared to reach the end sector with
  the barons alive. A per-sector replay showed both barons died at tics
  3,699–4,540 while the player stood in the star room, the tag-666 floor then
  fell from 208 to −136, and the player walked over it at tic 4,792. The kill
  counter alone had been misread. `reachability.py`'s verdict (the end sector
  needs the boss deaths) stands, and the engine agrees with it.

## 4. Finding — RK-1: the player's rocket flies on the player's collision test

`thing_missile_tick` (`things.cyr`) moves the player's rocket only where
`player_check_position(nx, ny)` allows, which is `move_check_position` from the
**player's** position and floor with the **player's** radius. So the rocket:

- detonates within 16 units of any wall (its own radius is 11);
- detonates at any step up of more than 24 from the floor the *player* stands
  on, although it flies 32 units above that floor (`MISSILE_LAUNCH_Z`), and on
  any line the player could not pass for headroom;
- stops at `ML_BLOCKING` lines, which vanilla missiles fly over;
- applies the drop-off escape rule as if it started where the player stands.

Vanilla moves a missile on its own radius and height: it stops on a solid wall,
a closed portal, or a floor or ceiling its own z does not clear. The monster
fireballs already have a flight rule of their own (0.33.1, the sight-crossing
test); the rocket was left on the player's.

How it showed: two E1M6 deaths in one standalone run, each with the launcher
out and the target a demon 600–700 units away, losing 48 and 35 health in under
two seconds with no monster in reach. Most likely the bot's own rockets going
off a few units ahead; the record does not log explosions, so this attribution
is inference. The code path itself is certain from reading.

Not fixed here. A fix changes every rocket's flight, so it wants its own staged
gate; it is slotted in v0.37.3 with the other rocket work (roadmap). The bot
works around it: before firing it walks the first 240 units of the flight
through the engine's rule (`bot.py` `rocket_clear`).

No security impact: the rocket stops early, never late.

## 5. Left open (not engine defects)

- The playthrough is one deterministic trajectory: any change to RNG use, the AI
  or collision changes it. It is a gate to re-run, not a recording to replay.
- The bot plays HMP only and sees every monster through the record.
