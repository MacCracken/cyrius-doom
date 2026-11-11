# Scripted playthrough (v0.37.0 — v1.0.0 item 1)

Drives cyrius-doom from E1M1 to the E1M8 finale through the real game loop at
the default skill (Hurt Me Plenty), by pressing keys on a pty. It is the
evidence for v1.0.0's "plays E1M1–E1M9 start to finish": no cheats, no state
written into the engine, inventory carried from map to map as a player's run
carries it.

```sh
cyrius build src/main.cyr build/doom
python3 scripts/playthrough/playthrough.py build/doom wad/DOOM1.WAD            # E1M1 -> finale
python3 scripts/playthrough/playthrough.py build/doom wad/DOOM1.WAD --map E1M5 --until E1M6
```

Exit status 0 means the target was reached. `--out DIR` (default
`build/playthrough`) gets `run.log` (every decision the bot made, plus a status
line every 3 s), `doom.log` (the engine's own log) and one PNG per map showing
the path the player actually walked. Python 3, stdlib only; the WAD is the only
input, as for the engine.

## How doom is driven: `--lockstep`

`doom <wad> [map] --lockstep` (Linux only; `src/lockstep.cyr`) is the
interactive game with three differences:

1. every frame is rendered but none is presented, and `tick_wait` does not sleep;
2. audio and the PC speaker stay closed;
3. at the start of each input poll, doom writes a state record to fd 3 and then
   **blocks** on stdin until the harness sends that tick's keys followed by the
   sync byte `0x1F`.

The keys go through the same tty decoder an interactive session uses (doom puts
the pty in raw mode itself), so input, the game loop, collisions, doors,
switches, walk lines, teleports, the intermission and the finale are all the
shipped code paths. The harness answers one tick at a time, so a run is
deterministic and far faster than real time: about 700 ticks a second.

The record (format in `src/lockstep.cyr`) carries the player (position, angle,
health, armour, weapons, ammo, keys, sector), the level counters, which screen
is polling (play / intermission / death / finale / menu), every active monster,
pickup and projectile with the engine's own line-of-sight verdict, and every
sector whose floor or ceiling moved.

## The player

| File | Role |
|---|---|
| `doomproc.py` | Spawns doom on a pty with the record pipe on fd 3; `step(keys)` returns the next state. |
| `wadmap.py` | The map's geometry from the WAD, BSP point-in-sector with the engine's side rule, PNG overviews. |
| `nav.py` | An 8-unit occupancy grid judged by the engine's collision rules (radius, 24-unit step, 56-unit headroom, free drops, the drop-off escape rule), on live heights. A* plus string-pulling. Manual doors the bot can open count as open; a lift counts as both ends of its travel; pits and one-way drops the goal cannot be reached from are forbidden, with a margin on their rim. |
| `bot.py` | Follows the route, steers, opens doors from their front, calls and rides lifts, fights (sticky target, barrel-aware, dodges projectiles, retreats when hurt), detours for weapons, health, armour and ammo it can come back from, and, when there is no path, runs the trigger search below. |
| `autoroute.py` | Drafts a route: the triggers a map's exit depends on, in order. |
| `routes/E1Mx.route` | The per-map routes, drafted by `autoroute.py`, then proved and, where needed, pinned with waypoints. |

A route is a list of steps: `key <colour>`, `use <line>`, `cross <line>`,
`exit <line>`, `goto <x> <y>`, `killall <type>`, `endsector`, `wait <tics>`,
`until <sector> floor|ceil <=|>= <h>`.

**Trigger search.** When the planner finds no path to a step's target, the bot
runs `autoroute`'s minimal-trigger search from where it stands, against the
heights as they are now (`scripts/reachability.py`), and pushes the triggers it
needs as sub-steps. That is how it gets out of a room a door closed behind it
(E1M4's blue-key pillar) without a hand-written step.

## What it does not prove

- The bot is omniscient (it reads every monster's position from the record) and
  plays HMP only. It shows the episode can be finished through the shipped
  mechanisms, not that it is fair or well tuned.
- A run is one deterministic trajectory. A change anywhere in the engine (RNG
  use, AI, collision) changes it, so the run is a gate to re-run, not a
  recording to replay.
- Linux tty input only. Wayland, AGNOS and the menu's own key handling are not
  exercised beyond what dismissing the screens needs.
