#!/usr/bin/env python3
"""playthrough.py — drive cyrius-doom from E1M1 to the E1M8 finale through a pty.

    python3 scripts/playthrough/playthrough.py build/doom wad/DOOM1.WAD
        [--map E1M1] [--until E1M8|finale] [--max-ticks N] [--out DIR]

The v1.0.0 item-1 evidence (roadmap v0.37.0). doom runs with --lockstep: the
REAL game loop at the default skill (HMP, game_skill 3), its tty input decoder
fed through a pty, paced one tick at a time by this harness (src/lockstep.cyr).
The player is scripts/playthrough/bot.py following the per-map routes in
scripts/playthrough/routes/*.route; no cheat, no state is written into the
engine. With no --map it starts at E1M1 and carries inventory across levels
exactly as a player's run does; the run passes when the E1M8 finale shows.

Exit status: 0 = reached the target, 1 = did not, 2 = harness error.
Output (--out): run.log (events), trace PNGs per map (the bot's path).
"""
import argparse, os, sys, time
sys.dont_write_bytecode = True   # no __pycache__ beside the sources (scripts/, scripts/playthrough/)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import doomproc, wadmap, bot as botmod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('doom')
    ap.add_argument('wad')
    ap.add_argument('--map', default='E1M1')
    ap.add_argument('--until', default='finale', help='finale, or a map name: stop on reaching it')
    ap.add_argument('--max-ticks', type=int, default=35 * 60 * 60)
    ap.add_argument('--max-deaths', type=int, default=6,
                    help='per map: a death restarts the map from a pistol start, as in play; one more ends the run')
    ap.add_argument('--out', default='build/playthrough')
    ap.add_argument('--routes', default=os.path.join(HERE, 'routes'))
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, 'run.log'), 'w')
    wad = wadmap.read_wad(a.wad)
    d = doomproc.Doom(a.doom, a.wad, a.map, os.path.join(a.out, 'doom.log'))
    if d.state is None:
        print('doom did not start (see %s/doom.log)' % a.out)
        return 2
    b = botmod.Bot(d, wad, a.routes, log, png_dir=a.out)
    t0 = time.time()
    ticks = 0
    rc = 1
    maps_done = []
    last_map = None
    deaths_at_entry = 0
    rows = []            # per map: name, ticks, deaths, health at exit, kills, items, secrets
    map_start = 0
    prev = None
    try:
        while ticks < a.max_ticks:
            st = d.state
            if st is None:
                b.say('doom exited')
                break
            if st.map != last_map:
                if last_map is not None:
                    maps_done.append(last_map)
                    if prev is not None:
                        rows.append((last_map, ticks - map_start, b.deaths - deaths_at_entry, prev.health,
                                     '%d/%d' % (prev.kills, prev.max_kills), '%d/%d' % (prev.items, prev.max_items),
                                     '%d/%d' % (prev.secrets, prev.max_secrets)))
                map_start = ticks
                last_map = st.map
                deaths_at_entry = b.deaths
                print('%7d  %s' % (ticks, st.map), flush=True)
                if a.until != 'finale' and st.map == a.until and last_map != a.map:
                    b.result = 'reached ' + a.until
                    rc = 0
                    break
            if st.screen_name == 'play':
                prev = st         # after the map-change check: a row reports its own map
            keys = b.tick()
            if b.result == 'finale':
                b.say('FINALE reached')
                rc = 0 if a.until == 'finale' else 1
                break
            if b.result == 'menu':
                b.say('back at the menu (unexpected)')
                break
            if b.deaths - deaths_at_entry > a.max_deaths:
                b.say('too many deaths on %s' % st.map)
                break
            if keys is None:
                break
            d.step(keys)
            ticks += 1
    finally:
        b.dump_png()
        st = d.state
        summary = 'result=%s ticks=%d (%.1f game-min) deaths=%d wall=%.1fs maps=%s last=%s' % (
            b.result or 'none', ticks, ticks / 35 / 60, b.deaths, time.time() - t0,
            ','.join(maps_done + ([last_map] if last_map else [])), st.map if st else '?')
        b.say(summary)
        print(summary)
        if last_map is not None and prev is not None:
            rows.append((last_map + ('' if b.result == 'finale' else ' (unfinished)'), ticks - map_start,
                         b.deaths - deaths_at_entry, prev.health, '%d/%d' % (prev.kills, prev.max_kills),
                         '%d/%d' % (prev.items, prev.max_items), '%d/%d' % (prev.secrets, prev.max_secrets)))
        table = ['| Map | Tics | Deaths | Health at exit | Kills | Items | Secrets |', '|---|---:|---:|---:|---:|---:|---:|']
        table += ['| %s | %d | %d | %d | %s | %s | %s |' % r for r in rows]
        open(os.path.join(a.out, 'summary.md'), 'w').write(summary + '\n\n' + '\n'.join(table) + '\n')
        print('\n'.join(table))
        d.close()
        log.close()
    return rc


if __name__ == '__main__':
    sys.exit(main())
