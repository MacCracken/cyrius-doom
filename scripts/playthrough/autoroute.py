#!/usr/bin/env python3
"""autoroute.py — draft a map's route: the triggers its exit depends on, in order.

    python3 scripts/playthrough/autoroute.py [wad/DOOM1.WAD] E1M3 [E1M4 ...]

Built on scripts/reachability.py, the sector-level model of what the ENGINE's
specials can do. Its flood fires every special the player can reach, in the
order it can reach them. This script drops each fired line in turn and keeps it
dropped if the normal exit is still reachable without it, leaving a minimal set
of triggers that the exit needs. It then prints them in firing order as route
steps:

  key <colour>    a key one of the needed key doors asks for
  use <line>      a switch (used from its front)
  cross <line>    a walk-over trigger (or teleporter)
  exit <line>     the exit switch (cross, for a walk-over exit)

Manual doors and lifts are left to the bot, which opens doors and calls lifts
where its path meets them; they are listed as comments. The draft is a starting
point. The model is optimistic (a mover can be at either end of its travel), so
a route still has to be proved in the engine with playthrough.py.
"""
import os, sys
sys.dont_write_bytecode = True   # no __pycache__ beside the sources (scripts/, scripts/playthrough/)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import reachability as R   # noqa: E402

NORMAL_EXIT = {11, 52}
KEY_NAME = {'b': 'blue', 'y': 'yellow', 'r': 'red'}


def exit_ok(r, M):
    if any(sp in NORMAL_EXIT for _, sp in r['exits']):
        return True
    return M.name == 'E1M8' and bool(r['end11'])


def draft(M):
    full = R.run(M, R.ENGINE)
    if not exit_ok(full, M):
        return None, 'exit not reachable in the model'
    fired = [i for kind, i in full['order'] if kind == 'line']
    disabled = set()
    for i in reversed(fired):
        trial = disabled | {i}
        if exit_ok(R.run(M, R.ENGINE, disabled_lines=trial), M):
            disabled = trial
    needed = [i for i in fired if i not in disabled]
    keys_needed = set()
    for i in needed:
        k = R.DOOR_MANUAL.get(M.L[i]['special'])
        if k:
            keys_needed.add(k)
    steps = []
    for kind, v in full['order']:
        if kind == 'key':
            if v in keys_needed:
                steps.append('key %s' % KEY_NAME[v])
            continue
        if v not in needed:
            continue
        sp, tag = M.L[v]['special'], M.L[v]['tag']
        if sp in R.DOOR_MANUAL:
            steps.append('# door %d (special %d) — opened by the bot on its way' % (v, sp))
        elif sp in R.LIFT:
            steps.append('# lift tag %d via line %d (special %d) — called by the bot on its way' % (tag, v, sp))
        elif sp in R.GUN_KINDS:
            steps.append('shoot %d    # gun trigger, special %d tag %d' % (v, sp, tag))
        elif sp in R.USE_KINDS:
            steps.append('use %d    # special %d tag %d' % (v, sp, tag))
        else:
            steps.append('cross %d    # special %d tag %d' % (v, sp, tag))
    exits = sorted(set((i, sp) for i, sp in full['exits'] if sp in NORMAL_EXIT))
    for i, sp in exits[:1]:
        steps.append(('exit %d' if sp == 11 else 'cross %d    # walk-over exit') % i)
    if M.name == 'E1M8' and not exits:
        steps.append('# E1M8: kill both barons (tag 666 floor), then walk into the special-11 end sector')
    return steps, None


def main():
    args = sys.argv[1:]
    wad = 'wad/DOOM1.WAD'
    if args and not args[0].upper().startswith('E'):
        wad = args.pop(0)
    data, lumps = R.load(wad)
    for nm in [a.upper() for a in args] or ['E1M%d' % i for i in range(1, 9)]:
        M = R.Map(data, lumps, nm)
        steps, err = draft(M)
        print('# %s (autoroute draft)' % nm)
        if err:
            print('# ' + err)
            continue
        for s in steps:
            print(s)
        print()


if __name__ == '__main__':
    main()
