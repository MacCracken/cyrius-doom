# cyrius-doom — Audit: Episode end (2026-09-26, v0.35.8)

> **Scope.** The roadmap's Episode-end slot: teleporters (TELE-1), the diagonal double walk trigger that
> had to be fixed first (G-10), E1M8's boss death (BOSS-1), damaging floors and the radiation suit
> (DMG-1), the finale (P4) and its music (MUSIC-4). This file records the vanilla behaviour the code
> follows and where it came from, the security review of the new surface (CLAUDE.md P(-1) step 5), the
> verification, and every deliberate deviation.
>
> **Clean-room.** Behaviour facts come from the Unofficial DOOM Specs / Doom Wiki; the id source was
> consulted **for understanding only** to settle three questions the wikis left open (below). No code was
> copied — every function here is written against the engine's own structures. The finale's text is this
> project's own; id's episode texts are not reproduced.

---

## 1. Behaviour followed

### The episode ends without an intermission

The earlier research note for this slot said "intermission, then the finale, without the Entering block".
That was **wrong**: in vanilla Doom 1, completing map 8 of an episode sets the victory action directly and
**skips the intermission screen entirely** (which is also why E1M8's defined 30-second par time is never
displayed, as the Doom Wiki notes). Settled by reading the id source for understanding; the engine now
goes straight from E1M8's exit to the finale. Any exit counts — map 8 is tested before the secret flag.

### Finale (episode 1)

Background: the flat **FLOOR4_8** tiled over the screen. Music: **D_VICTOR**. Text: typed from (10, 10);
a newline returns to x = 10 and drops 11 rows; a character with no STCFN glyph advances 4 pixels; a glyph
that would cross the right edge ends the draw; one character every **3** tics after a **10**-tic pause;
the stage ends **250** tics after the last character. Then a full-screen picture: **HELP2**, or **CREDIT**
in the retail (Ultimate) IWAD — detected here by an E4M1 marker. The bunny scroll the roadmap once named
is episode 3's, and PFUB1/2 are not in DOOM1.WAD.

### Teleporters (39 W1, 97 WR; monster-only 125 W1, 126 WR)

- Fires only when the crossing **starts on the line's front side** — you can walk back off a pad.
- Landing: the first teleport-destination thing (DoomEd 14) standing in the **lowest-numbered sector**
  carrying the line's tag (sectors are the outer search). No landing → no teleport.
- The traveller takes the landing's x, y and **angle**, and stands on its floor.
- A **player** telefrags every shootable body whose box overlaps theirs at the landing, and cannot move or
  turn for **18 tics** (firing is untouched).
- A **monster** never telefrags (outside Doom II's MAP30): any shootable body there — the player included —
  cancels its teleport, and it simply finishes its step.
- Fog + DSTELEPT at both ends; the arrival fog 20 units in front of the landing along its angle.
- A W1 teleport is used up by any crossing, front or back (the id source clears the special whether or
  not the teleport happened); a 125 when a monster crosses it. *(Settled from the source for
  understanding — no DOOM1 line is a 39 or 125, so it is invisible in the shareware game.)*

DOOM1 has 20 teleport lines, all WR 97: E1M5 L787–796, E1M8 L299–306 (the way into the ending), E1M9
L514/515 (the closet ambush).

### Boss death (E1M8)

When a baron's death completes on E1M8 and **no other baron has health above 0**, every tag-666 sector's
floor lowers to its lowest neighbour at 1 unit/tic (E1M8 sector 30: 208 → −136, opening the way to the
teleporter). A baron mid-death already counts as dead, so the order two die in does not matter. Nothing
happens if the player is dead.

### Damaging floors (on the floor, every 32nd tic of the level clock)

| Type | Damage | Radiation suit |
|---|---|---|
| 7 nukage | 5 | blocks |
| 5 hellslime | 10 | blocks |
| 16 super hellslime, 4 strobe-hurt | 20 | **leaks**: the bite still lands with probability 6/256 |
| 11 E1M8 exit room | 20 | ignored; no hit can take the last point of health; the level ends at ≤ 10 |

The leak probability: vanilla rolls `P_Random() < 5` against its fixed 256-entry table, and **six** of
those entries are below 5 (0, 0, 2, 2, 3, 4 — counted, the one table fact this cut needed). This engine's
`p_random` is a uniform LCG, so the threshold is 6 to keep vanilla's odds.

Radiation suit (2025): always taken, (re)starts a 60-second (2,100-tic) timer, never counts toward
items % (it is the one DOOM1 powerup without the count flag). Powers are cleared on every map load.

Player damage order (vanilla): skill 1 halves every hit first; then the type-11 cap (`damage ≥ health` →
`health − 1`); then armor. A player at 0 health takes no damage at all.

---

## 2. Security review of the new surface

Research per P(-1) step 5 — known exploit classes in DOOM engines for this feature area, then the new code.

| Class / vector | Where it bites vanilla-derived engines | This engine |
|---|---|---|
| **spechit overflow** | Vanilla records crossed special lines in a fixed 8-entry array; a move crossing more overflows it (a classic demo-desync / memory-corruption class, reproduced in several ports' compatibility layers). | **Not applicable** — the walk sweep tests lines directly, no fixed array. The player sweep stops on a teleport; monsters test only the per-map teleport list. |
| Malformed teleport line | A tag-0 teleport matches every untagged sector in vanilla. | Tag ≤ 0 never teleports (a deliberate deviation — only a malformed line reaches it). |
| Landing outside the map | A landing placed in the void strands the traveller. | Same (mapping error, not memory): `map_point_sector` always resolves a leaf and every consumer is bounds-checked. |
| Finale font index | Vanilla's `c > HU_FONTSIZE` bound is off by one (index 63 is read past the 63-glyph array). | `g < FIN_FONT_COUNT` — no out-of-range glyph read. |
| Hostile font / picture / flat lumps | Oversized or truncated patches. | Glyphs cached through `st_cache_slot` (rejects < 8 B or > 256 B); every draw goes through the range-clamped, size-bounded status decoder; a zero width only stalls the pen (the loop is bounded by the character count); the flat needs ≥ 4,096 B and exactly 4,096 are read; the picture is bounded by `MENU_PATCH_BUF_SIZE`. |
| Type-11 cap on a dead player | — (new with this cut) | Found in review: `health − 1` on a player already at ≤ 0 is a *negative* hit, i.e. healing. Closed by vanilla's own rule, now in `player_take_damage`: a dead player takes no damage. Asserted. |
| Map-name parse | — | `map_load` reads the four name bytes only after `strlen == 4`. |
| Fog spawning | Unbounded effect things. | Finished fog slots are recycled; appends stop at `THING_MAX` (the fog is skipped, it is cosmetic). The E1M9 probe used 2 slots for 12 fogs. |
| Monster teleport list | — | Built per map in `doors_init` from `map_num_linedefs` (≤ `MAP_MAX_LINEDEFS`, the list's capacity). A stale list after a bare `map_load` (tests only) still indexes inside the fixed-size line and latch arrays. |

No new file, network or syscall surface; no new allocation that scales with WAD input beyond the existing
caps. Nothing to fix before shipping beyond the dead-player guard, which ships in this cut.

---

## 3. Verification

- **Reachability** (`scripts/reachability.py`, ENGINE now includes 39 / 97): E1M8's end sector is reachable
  — and only with both mechanisms: without the boss death the model reaches 46 sectors, with it 69, with
  the teleport too 70 (sector 66, the exit room). Every map: 0 sectors lost vs vanilla except E1M2's
  optional gun-triggered area (special 46, v0.35.10).
- **In-engine E1M8 endgame test** — the real code in the main loop's order: both barons killed, the tag-666
  wall lowers to −136, the player walks north onto the pad (9 tics) and is teleported into the exit room;
  with its monsters firing and the floor biting, the level ends after 32 tics at **1** health (never 0),
  and `level_episode_ends()` reports the finale.
- **E1M9 ambush probe** (scratch, not committed): the launcher room's ring of W1 lines opens the closet;
  over 60 s with the player in the room and a noise alert each second, **6 of the 10** HMP closet monsters
  teleported in, the first 2.1 s after the door opened. The other four hit the pre-existing give-up rule
  (§4, AI-1).
- **Tests**: WAD-free **376 / 33 / 18 / 12**, full **677 / 677** (+131). The test build now includes the
  real `level.cyr` (replacing four stubs) and `finale.cyr`.
- **Mutation: 48 mutants, 47 killed, 1 equivalent** (a player-side `is_walk` entry for 126 changes nothing
  because the teleport condition excludes 126). The first pass left two real gaps — a finale newline that
  did not move the pen, and a landing search that ignored the tag — both closed with new asserts, plus a
  lowest-sector-first case built from a decoy landing. Every rule in §1 has a mutant that a named assert
  kills: side, landing order, tag, angle, z, freeze length and scope, telefrag, monster blocking (by a body
  and by the player), fog offset and frames, W1 latching (front and back), the boss rule's three
  conditions and its hook, each floor's amount and beat, the leak in both directions, the type-11 cap,
  exit threshold and suit-immunity, skill-1 halving, the suit's timer / pickup / item count, the episode
  rule and its order, the dismiss gate's arm threshold and minimum, and the finale's edge, speed and wait.
- **41-capture battery vs v0.35.7** (sha256-matched baseline): **40 identical**; the E1M8 intermission
  differs only in x 109–210, y 156–182 — the "Entering Hangar" block that announced the old E1M8 → E1M1
  wrap. **12 / 12 `--ai-probe` fingerprints identical.** New: `--ppm-finale` captures of both finale
  screens.
- **fuzz ×8** clean. **Bench**: interleaved best-of-3, every metric within ±0.6% (noise).
- **AGNOS QEMU** on the final `doom_agnos` (sha256 `8c7b3bb5…`): boots v0.35.8, WAD loads, **64,000 /
  64,000** blocks exact against Linux. A clean strict-pin build from scratch reproduces the release and
  AGNOS binaries byte for byte.

---

## 4. Deliberate deviations and findings

| # | Item | Disposition |
|---|---|---|
| D-1 | **Finale keys.** Vanilla ignores keys on the finale (its in-game menu is the way out). Here a fresh press finishes the typing, the next moves to the picture, and a press on the picture returns to the title menu. | Kept — this engine has no menu over the finale. |
| D-2 | **Tag-0 teleports** never fire (vanilla lands on the first landing in any untagged sector). | Kept — malformed-line only. |
| D-3 | **Teleport fog** runs TFOG A..J once; vanilla opens A B A B, then C..J. | Roadmap v0.35.12 (combat cosmetics). |
| D-4 | **Monster walk lines**: monsters take teleports (39/97/125/126) but not yet the door / lift lines vanilla also lets them cross (4 / 10 / 88). | Roadmap v0.35.10. |
| AI-1 | **Chasing monsters give up after 100 tics without sight** and go back to idle — vanilla never abandons a target. Cost E1M9's ambush four of its ten monsters in the probe. Pre-existing. | Roadmap v0.35.10, with its own behaviour gate (it moves every staged fingerprint). |
| D-5 | **Radiation suit feedback**: no green palette (and no damage / bonus flashes at all yet). | Roadmap v0.35.11 (Items II). |
| D-6 | **Other episodes' boss rules and finales** (E2M8, E3M8, E4M6, E4M8; VICTORY2, the bunny scroll). | HOLD-A — need a registered IWAD to exercise. |
