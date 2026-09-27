# cyrius-doom — Audit: Interactable Objects (2026-09-26, v0.35.6)

> **Requested review, fixes shipped in the same release.** Three independent review lenses ran over
> the v0.35.6 tree: **use** (everything the USE key activates), **walk** (line crossings and sector
> specials), and **pickups** (items, keys, barrels). Each lens worked read-only on the repo and ran its
> probes in its own scratch copy, against the real DOOM1.WAD maps, on cyrius 6.6.6. Every finding was
> then **re-verified independently** before a fix — by an in-engine probe of the exact map line, not by
> re-reading the report — and every fix carries a test that was shown to **fail with the fix reverted**
> (mutation run: 33 of 34 mutants killed; the survivor is equivalent on this WAD, §6).
>
> Behaviour reference: doomwiki.org (Linedef types, Sector types, Door, Lift, Switch, Barrel, Item,
> Splash damage, Weapon) and the Unofficial DOOM Specs. doomwiki blocked direct fetches from the
> sandbox, so some pages were read through search snippets; every numeric expectation below was
> instead re-derived from the WAD geometry, and the in-engine result was compared against it.

---

## 1. Headline — the episode could not be finished

With the engine as shipped in v0.35.5, **only E1M1, E1M2, E1M6 and E1M7 had a reachable exit.** A new
game stopped at E1M3. The cause was not a bug in existing code but **five line specials doom never
implemented**, each gating a level's route:

| Special | Kind | Where it gates progression |
|---|---|---|
| **8** | W1 build stairs (8-unit steps) | E1M3 L967 — the only route to the normal exit |
| **18** | S1 raise floor to next higher | E1M4 L592 — the exit bridge (sector 52, 128 → 192) |
| **20** | S1 raise to next higher + change flat | E1M9 L567 — exit bridge; E1M3 L360 — secret-exit bridge; E1M3 L1020 — the only escape from the courtyard pit |
| **22** | W1 raise to next higher + change flat | E1M5 L271 — the walkway out of the nukage (99 of 130 sectors) |
| **7** | S1 build stairs | E1M8 L233 — the 14-step stair to the teleporter platform |

**Measured with the use lens's reachability model**, now committed as `scripts/reachability.py` (an
optimistic sector flood over the WAD: movers counted at every height, so "unreachable" is conservative).
Re-run it with `python3 scripts/reachability.py`. Sectors unreachable vs vanilla:

| Map | Vanilla exits | v0.35.5 exits | v0.35.6 exits | Lost sectors v0.35.5 → v0.35.6 |
|---|---|---|---|---|
| E1M1 | 11 | 11 | 11 | 5 → **0** (W1 36 — secrets 2 and 3) |
| E1M2 | 11 | 11 | 11 | 26 → 26 (gun-activated 46, optional area — slotted) |
| E1M3 | 11, 51 | **none** | 11, 51 | 24 → **0** |
| E1M4 | 11 | **none** | 11 | 12 → **0** |
| E1M5 | 11 | **none** | 11 | 99 → **0** |
| E1M6 | 11 | 11 | 11 | 1 → **0** |
| E1M7 | 11 | 11 | 11 | 1 → **0** |
| E1M8 | end sector | none | none | 9 → 1 (teleport 97, boss floor, sector 11 — the Episode-end slot) |
| E1M9 | 11 | **none** | 11 | 9 → **0** |

**Seven of nine maps are now fully reachable as in vanilla.** E1M8's ending was always its own
roadmap slot, and E1M2's remaining area is optional.

## 2. Findings — fixed in v0.35.6

IDs are the lens that found them (**U** use, **W** walk, **P** pickups); duplicates across lenses are
merged. Every row was reproduced in-engine before the fix and has a test that fails without it.

| ID | Sev | Finding | Fix | Evidence (in-engine, real map) |
|---|---|---|---|---|
| U-1 / U-2 / U-3 / W-1 | HIGH | Specials 7, 8, 18, 20, 22 unimplemented — §1 | New floor movers (§4) | E1M4 52 → 192; E1M9 17 → 88 with the switch side's flat **and its cached index**, special cleared; E1M3 66 → 64, 48/49 → 88; E1M8 14 steps −128 … −24; E1M3 10 steps 56 … 128 (an 8-unit step to the 136 landing); E1M5 91 → 56 |
| P-1 | HIGH | An exploded barrel stayed standing: frames H–L fell back to BAR1A0, so a non-solid **intact** barrel remained forever | Vanilla BEXP A–E (5/5/5/10/10 tics) drawn full-bright, then the barrel is removed | 35-tic sequence, removed; every BEXP frame resolves |
| P-12 | LOW | …and it blasted on the killing tick with a zombie death scream (DSPODTH1) | The blast lands at frame D, 15 tics after death, so chains ripple | neighbour untouched for 14 tics, blown on the 15th |
| P-2 / U-7 | MED | **Regression from v0.35.4**: stored thing-z never followed a moving floor — items, corpses and idle monsters floated or sank, and step-checks used the stale height | Every floor-moving branch resyncs the things standing in the sector (projectiles skipped) | E1M6 soulsphere rides its lift to −80 (was stuck at 48) |
| W-2 | MED | Walk lines ignored crossings more than ~114–128 units from their midpoint (a distance prefilter ran before the exact segment test) | Bounding-box reject instead — one `continue`, as the function sits at the 8-per-nest cap | E1M9 L450 crossed 165 units from its middle now fires |
| W-3 | MED | `ML_BLOCKMONSTERS` was defined and never read — monsters walked off E1M1's bridge into the nukage | Enforced for the monster mover only (`allow_drop == 0`); the player and missiles pass, as in vanilla | E1M1 L182: monster refused, player allowed |
| U-4 | MED | Doors held open 105 tics (the lift wait); vanilla 150 | `DOOR_WAIT = 150` | held open exactly 150 |
| U-6 | MED | A rising lift sealed whatever stood on it (E1M7 sector 135 closes floor-to-ceiling) | Blocked rising lift reverses, as vanilla's plat does; a blocked rising floor waits | gap never below 56 with the player inside |
| P-3 | MED | Pickup reach was a 20-unit circle (~1/5 of vanilla) | Vanilla contact box: \|dx\|, \|dy\| < item + player radius (36) | 30 u touched, 36 not, (30,30) touched |
| P-4 | MED | Items that gave nothing were consumed (full ammo, owned weapon, second chainsaw) | Stay on the floor, as in vanilla | clip at 200, owned shotgun at 50 shells, second chainsaw: all stay |
| P-5 | MED | A new weapon was never selected (E1M1's shotgun left you on the pistol); no ammo-from-empty switching | Vanilla rules: new weapon selected; ammo for an empty type switches off fist/pistol | shotgun selected; clip on the fist → pistol, or chaingun if owned |
| P-6 / W-4 | MED | Items % counted every item, weapon and key (E1M5: 88 vs vanilla 29) | Vanilla's COUNTITEM set — see §5 for the one deviation | per-map totals asserted for all nine maps |
| P-7 | MED | Splash used a Euclidean estimate between centres; too soft, chains too short | max(\|dx\|,\|dy\|) minus the target's radius, floored at 0; damage 128 minus that | player 50 u away takes 94; imp at 30 u 118 (was 98) |
| P-8 | MED | Rockets did splash only — no impact damage | The thing hit takes (1..8)×20, then the splash | direct baron hit > 128 total |
| P-9 | LOW | No height check on pickups (E1M7 bonuses grabbed from a walkway 128 above) | Item must be within 8 below to 56 above the feet — safe now that P-2 keeps z true | 57 above / 9 below refused, 8 below taken |
| P-10 | LOW | A dead player picked items up — a stimpack could undo a death | No pickups at health ≤ 0 | stays on the floor |
| P-11 | LOW | No double ammo on skills 1 and 5 | Doubled | clip gives 20 on skill 1 |
| P-14 (part) | LOW | Every pickup played DSITEMUP | Weapons DSWPNUP, soulsphere DSGETPOW (both preloaded) | — |
| U-11 | LOW | Lines could be used from their back side (E1M7 lift started from behind) | Front side only (vanilla) | back-side press does nothing |
| U-13 | LOW | S1 switches / D1 doors were used up even when nothing started (full thinker table) | Consumed only when a mover started | full table: switch stays usable |
| U-14 / W-7 | LOW | Special 23 lowered at 4 units/tic; vanilla "slow" is 1 | Per-special speed (23 / 38 / 102 slow, 70 / 71 turbo) | 128 units in 128 tics |
| U-15 | LOW | Doors closed back to their starting ceiling, not the floor (E1M5 sector 121 kept an 8-unit gap) | Close to the floor | closes flush at 80 |

**Also added for reachability and fidelity** (cheap, existing movers, each tested): W1 **36** and WR
**98** (turbo lower to highest neighbour + 8 — 36 is E1M1's route to secrets 2 and 3), W1 **5** / WR
**91** (raise floor to lowest neighbouring ceiling), WR **82** (lower to lowest), WR **86** (door open
& stay).

## 3. Findings — slotted (not in this release)

| ID | Sev | Finding | Slot |
|---|---|---|---|
| U-5 | MED | Re-using a moving DR door should reverse it | Interactables II — needs U-10's use latch first, or a held key flips the door open and shut |
| U-10 | LOW | Holding E re-triggers every tick (door cycled 4× in 600 tics) | Interactables II — touches all three input paths (tty, Wayland, AGNOS kbscan), so it gets its own cut |
| U-9 / P-14 (rest) | LOW | No "oof" or message on a locked door; no switch / mover sounds | Interactables II (feedback) |
| U-8 | LOW | Donut (9) unimplemented — E1M2's chainsaw pillar | Interactables II |
| — | — | Gun-activated 46 (E1M2's 26-sector optional area); doors 16 / 76; lights 35 | Interactables II / Lighting |
| U-12 | LOW | A closing door reverses only for things whose centre is inside the door sector | Interactables II |
| W-5 | LOW | Diagonal moves run walk triggers twice (harmless today; must be fixed before teleport) | Episode end — teleport depends on it (roadmap G-10) |
| W-6 | LOW | A dead player gets one extra tick | Interactables II |
| P-13 | LOW | Chainsaw lights ARMS slot 6 | Interactables II |
| P-15 | LOW | Monster hitscan never hits barrels | Interactables II |
| P-16 | LOW | Kills credited at the end of the death animation (a kill just before exiting is lost) | Interactables II |
| P-17 | LOW | Rocket wall / step checks use the player's floor and radius | Interactables II |
| P-18 | LOW | Two `switch` statements in `thing_classify` — correct today (totals match on all nine maps) | Watch item |
| P-19 | LOW | Pickup and barrel sprites never animate; keys / soulsphere not full-bright | Items II |
| — | — | E1M8: teleport 97 (also E1M9's monster ambush and E1M5's shortcut), boss-death floor (tag 666), sector 11 | **Episode end** (critical path) |
| — | — | Damaging floors (types 5 / 7 / 16 — 81 sectors) + radiation suit | Episode end (sector 11 needs the damage mechanism) |
| — | — | Backpack, the four DOOM1 powerups, monster drops, pickup messages / flash | Items II |
| — | — | Monsters triggering walk lines and opening doors | Interactables II |
| — | — | Switch textures (SW1 ↔ SW2) and the SR revert | Interactables II |

## 4. How the new movers work

`doors.cyr`'s thinker entry grew from 48 to 64 bytes to carry a **speed in quarter units per tic** and
the exact **position in quarter units**. Vanilla floor speeds are 1 (slow), ½ (plat raise-and-change)
and ¼ (stairs) units per tic while sector heights here are whole units; the sector gets the whole part
of the position, so a stair step visibly rises one unit every four tics. Doors and lifts are unchanged.

- **Raise to next higher** — target is the lowest neighbouring floor strictly above the current one.
- **Raise and change** — the floor flat is copied from the activating line's front sector **and** so is
  its entry in the per-sector flat-index cache (`sector_flat_floor_copy`), because the renderer reads
  the cache, not the name. The sector special is cleared.
- **Stairs** — the tagged sector rises one step; the builder then follows two-sided lines whose front
  sector is the current step to a back sector with the same floor flat, one step higher each time. The
  scan lives in its own helper so its `continue`s never sit inside the builder's `while` (see the
  toolchain audit on nested `continue`), and a step cap bounds a malformed cyclic chain.
- A **rising floor** that would squeeze the player or a solid thing waits (vanilla floors move with
  crush off); a **rising lift** reverses (vanilla plat). Every floor move resyncs thing z.

## 5. One deliberate deviation — items %

Vanilla counts the powerups too, but this engine cannot pick the DOOM1 powerups up yet (invisibility,
computer map, light amplification). Counting an item nobody can collect would make 100% impossible, so
they join the count when they become collectable. Per-map totals at skill 3, derived from the THINGS
lumps: E1M1 37, E1M2 42, E1M3 94 (vanilla 95), E1M4 45, E1M5 26 (29), E1M6 95 (99), E1M7 82 (84), E1M8 1
(3), E1M9 43. Five maps match vanilla exactly.

## 6. Verification

- **Probes on the real maps first**, then 94 new assertions in `tests/doom.tcyr` (WAD-free: pickups,
  splash, barrel sequence, rocket impact; WAD-gated: every special on its real line through the real
  use ray or crossing, the lift / door / floor fidelity items, thing-z on a lift, the monster-blocking
  bridge edge, BEXP resolution, per-map item totals).
- **Mutation run**: each fix reverted on its own, suite rebuilt and run — **33 of 34 killed**. The
  survivor removes vanilla's rule that the stair height still advances past an already-moving step;
  no DOOM1 staircase meets a moving step on first use, so it is equivalent on this WAD. One mutant
  first *survived* — the barrel's `thing_animate` guard — because the test drove the AI tick alone;
  the test now runs AI then animate in `things_tick`'s order and kills it.
- A second mutant exposed the new compiler cap working as designed: re-adding the old midpoint
  prefilter as an **extra** `continue` made `doors_walk_trigger` a 9-continue nest, which 6.6.6
  refuses to compile. The W-2 mutant was re-run as a swap.
- **Render**: vs the post-toolchain build, only the intermissions' items % (the harness draws fixed
  fake stats over the new totals) and E1M7's tick-35 status bar (a clip 32 units diagonal from the
  start is now within the vanilla contact box) change. All 12 `--ai-probe` fingerprints identical.
- AGNOS QEMU on the final binary: 64,000 / 64,000 pixels exact vs the Linux frame.
