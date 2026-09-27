#!/usr/bin/env python3
"""reachability.py — which sectors, keys and exits a player can reach, per map.

Usage:  python3 scripts/reachability.py [wad/DOOM1.WAD] [E1M1 E1M3 ...]

An OPTIMISTIC sector flood over the WAD, written for the v0.35.6 interactables
review (docs/audit/2026-09-26-interactables-review.md). Once a mover can fire, its
sector's floor / ceiling become a RANGE (a lift is both up and down; a door both
open and shut); a move from X to Y across a non-blocking two-sided line is legal if
some pair of heights allows a step up of <= 24 with >= 56 headroom. Specials fire
when their activating side is reachable (use / gun / teleport: front sector; walk:
either side), and each one widens its tagged sectors the way vanilla moves them.
Because every range is generous, **"unreachable" is conservative** — if an exit is
unreachable here it is unreachable in game; "reachable" does not prove a level can
be finished (timing, damage and monsters are not modelled).

It runs each map twice — with every vanilla special, and with ENGINE, the set this
engine implements — and reports what the engine loses. ENGINE must be kept in step
with src/doors.cyr; it is the claim the report makes. The Episode-end slot's exit
criterion (roadmap v0.35.8) is E1M8's end sector showing up as reachable here.
"""
import struct, sys

import struct, sys, collections

def load(path):
    data = open(path, "rb").read()
    ident, n, off = struct.unpack_from("<4sii", data, 0)
    lumps = []
    for i in range(n):
        lo, ls, name = struct.unpack_from("<ii8s", data, off + i * 16)
        lumps.append((name.rstrip(b"\0").decode(), lo, ls))
    return data, lumps

def map_lumps(data, lumps, mapname):
    idx = [i for i, l in enumerate(lumps) if l[0] == mapname][0]
    out = {}
    for j, nm in enumerate(["THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SEGS",
                            "SSECTORS", "NODES", "SECTORS", "REJECT", "BLOCKMAP"]):
        name, lo, ls = lumps[idx + 1 + j]
        assert name == nm, (name, nm)
        out[nm] = data[lo:lo + ls]
    return out

def parse(m):
    V = [struct.unpack_from("<hh", m["VERTEXES"], i * 4) for i in range(len(m["VERTEXES"]) // 4)]
    L = []
    for i in range(len(m["LINEDEFS"]) // 14):
        v1, v2, fl, sp, tag, rs, ls = struct.unpack_from("<HHHHHHH", m["LINEDEFS"], i * 14)
        L.append(dict(v1=v1, v2=v2, flags=fl, special=sp, tag=tag,
                      rs=(-1 if rs == 0xFFFF else rs), ls=(-1 if ls == 0xFFFF else ls)))
    S = []
    for i in range(len(m["SIDEDEFS"]) // 30):
        xo, yo, up, lo, mid, sec = struct.unpack_from("<hh8s8s8sH", m["SIDEDEFS"], i * 30)
        S.append(dict(xo=xo, yo=yo, upper=up.rstrip(b"\0").decode(), lower=lo.rstrip(b"\0").decode(),
                      mid=mid.rstrip(b"\0").decode(), sector=sec))
    SEC = []
    for i in range(len(m["SECTORS"]) // 26):
        fh, ch, ft, ct, light, sp, tag = struct.unpack_from("<hh8s8shHH", m["SECTORS"], i * 26)
        SEC.append(dict(floor=fh, ceil=ch, ftex=ft.rstrip(b"\0").decode(), ctex=ct.rstrip(b"\0").decode(),
                        light=light, special=sp, tag=tag))
    T = []
    for i in range(len(m["THINGS"]) // 10):
        x, y, a, t, o = struct.unpack_from("<hhhHH", m["THINGS"], i * 10)
        T.append(dict(x=x, y=y, angle=a, type=t, opts=o))
    return V, L, S, SEC, T

def neighbors(L, S, sec):
    out = set()
    for ld in L:
        if ld["rs"] < 0 or ld["ls"] < 0: continue
        a = S[ld["rs"]]["sector"]; b = S[ld["ls"]]["sector"]
        if a == sec: out.add(b)
        if b == sec: out.add(a)
    return out

STEP, HEIGHT = 24, 56

DOOR_MANUAL = {1: None, 26: 'b', 27: 'y', 28: 'r', 31: None, 32: 'b', 33: 'r', 34: 'y', 117: None, 118: None}
DOOR_TAG = {29, 63, 103, 2, 4, 86, 90, 46, 61, 42, 50, 16, 76, 75, 3}  # (close types treated as no-op below)
DOOR_OPENING_TAG = {29, 63, 103, 2, 4, 86, 90, 46, 61, 16, 76}
LIFT = {62, 88, 10, 21, 120, 121, 122, 123}
LOWER_LOWEST = {23, 38, 60, 82}
LOWER_HIGHEST = {19, 45, 83, 102}
TURBO_LOWER = {36, 70, 71, 98}
RAISE_NEXT = {18, 20, 22, 47, 68, 69, 95, 119, 128, 129, 130, 131}
RAISE_LOWCEIL = {5, 91, 101, 64, 24, 58, 92, 94, 55, 65, 56, 93}  # rough: floor up to lowest ceiling
STAIRS = {7: 8, 8: 8}
DONUT = {9}
TELEPORT = {97, 39}
EXIT_USE = {11, 51}
EXIT_WALK = {52, 124}

USE_KINDS = {1, 26, 27, 28, 31, 32, 33, 34, 117, 118, 7, 9, 11, 18, 20, 21, 23, 29, 51, 62, 63, 70, 71, 102, 103, 122}
GUN_KINDS = {46, 24, 47}

ENGINE_V0355 = {1, 26, 27, 28, 31, 32, 33, 34, 117, 118, 11, 51, 29, 63, 103, 21, 62, 122, 23, 71, 70, 102,
          2, 4, 10, 38, 52, 88, 90, 121, 124}
# v0.35.6 added the progression specials (7 8 18 20 22) and 5 36 82 86 91 98.
# v0.35.8 added the player teleports 39 / 97 (the monster-only 125 / 126 are in
# the engine too, but a player can never ride them, so they are not modelled).
# KEEP IN SYNC with doors.cyr: this set is the claim the report makes.
ENGINE = ENGINE_V0355 | {7, 8, 18, 20, 22, 5, 36, 82, 86, 91, 98} | {39, 97}

class Map:
    def __init__(self, data, lumps, name):
        m = map_lumps(data, lumps, name)
        self.name = name
        self.V, self.L, self.S, self.SEC, self.T = parse(m)
        self.nodes = [struct.unpack_from("<hhhh8h HH".replace(" ", ""), m["NODES"], i * 28) for i in range(len(m["NODES"]) // 28)]
        self.ssec = [struct.unpack_from("<HH", m["SSECTORS"], i * 4) for i in range(len(m["SSECTORS"]) // 4)]
        self.segs = [struct.unpack_from("<HHhHhh", m["SEGS"], i * 12) for i in range(len(m["SEGS"]) // 12)]
        for ld in self.L:
            ld["fs"] = self.S[ld["rs"]]["sector"] if ld["rs"] >= 0 else None
            ld["bs"] = self.S[ld["ls"]]["sector"] if ld["ls"] >= 0 else None
        self.sec_lines = [[] for _ in self.SEC]
        for i, ld in enumerate(self.L):
            if ld["fs"] is not None: self.sec_lines[ld["fs"]].append(i)
            if ld["bs"] is not None and ld["bs"] != ld["fs"]: self.sec_lines[ld["bs"]].append(i)
        for s in self.sec_lines: s.sort()

    def point_sector(self, x, y):
        n = len(self.nodes) - 1
        while not (n & 0x8000):
            nx, ny, dx, dy = self.nodes[n][0:4]
            rc, lc = self.nodes[n][12], self.nodes[n][13]
            left = dy * (x - nx)
            right = (y - ny) * dx
            n = rc if right < left else lc
        ss = n & 0x7FFF
        cnt, first = self.ssec[ss]
        v1, v2, ang, line, side, off = self.segs[first]
        ld = self.L[line]
        sd = ld["ls"] if side == 1 else ld["rs"]
        return self.S[sd]["sector"]

    def neighbors(self, s):
        out = []
        for i in self.sec_lines[s]:
            ld = self.L[i]
            if ld["fs"] is None or ld["bs"] is None: continue
            o = ld["bs"] if ld["fs"] == s else ld["fs"]
            if o != s: out.append(o)
        return out

def run(M, enabled, start=None, init=None, trace=False, boss_dead=True, disabled_lines=()):
    SEC, L = M.SEC, M.L
    n = len(SEC)
    if init is None:
        flo = [s["floor"] for s in SEC]; fhi = flo[:]
        clo = [s["ceil"] for s in SEC]; chi = clo[:]
        ftex = [s["ftex"] for s in SEC]
    else:
        flo, fhi, clo, chi, ftex = [list(a) for a in init]
    p1 = [t for t in M.T if t["type"] == 1][0]
    if start is None:
        start = M.point_sector(p1["x"], p1["y"])
    reach = {start}
    keys = set()
    fired = set()
    base_floor = [s["floor"] for s in SEC]
    base_ceil = [s["ceil"] for s in SEC]

    def tagged(tag):
        return [i for i, s in enumerate(SEC) if s["tag"] == tag] if tag else []

    def lowest_nb_floor(s):
        return min([base_floor[s]] + [base_floor[o] for o in M.neighbors(s)])
    def highest_nb_floor(s):
        nb = M.neighbors(s)
        return max(base_floor[o] for o in nb) if nb else base_floor[s]
    def lowest_nb_ceil(s):
        nb = M.neighbors(s)
        return min(base_ceil[o] for o in nb) if nb else base_ceil[s]
    def next_higher_floor(s):
        h = base_floor[s]
        c = [base_floor[o] for o in M.neighbors(s) if base_floor[o] > h]
        return min(c) if c else h
    def widen_f(s, v):
        flo[s] = min(flo[s], v); fhi[s] = max(fhi[s], v)
    def widen_c(s, v):
        clo[s] = min(clo[s], v); chi[s] = max(chi[s], v)

    def passable(x, y):
        M_ = min(chi[x], chi[y]) - HEIGHT
        if flo[x] > M_ or flo[y] > M_: return False
        return flo[y] <= min(fhi[x], M_) + STEP

    exit_hit = []
    changed = True
    while changed:
        changed = False
        for t in M.T:
            if t["type"] in (5, 40): k = 'b'
            elif t["type"] in (6, 39): k = 'y'
            elif t["type"] in (13, 38): k = 'r'
            else: continue
            if (t["opts"] & 16): continue
            if k in keys: continue
            ks = M.point_sector(t["x"], t["y"])
            ok = ks in reach
            if not ok:
                # vanilla touch: item radius 20 + player radius 16, height window
                for li in M.sec_lines[ks]:
                    l2 = L[li]
                    if l2["fs"] is None or l2["bs"] is None: continue
                    o = l2["bs"] if l2["fs"] == ks else l2["fs"]
                    if o not in reach: continue
                    if base_floor[ks] - fhi[o] > 56: continue
                    (x1, y1), (x2, y2) = M.V[l2["v1"]], M.V[l2["v2"]]
                    dx, dy = x2 - x1, y2 - y1
                    L2 = dx * dx + dy * dy
                    tt = max(0, min(1, ((t["x"] - x1) * dx + (t["y"] - y1) * dy) / L2)) if L2 else 0
                    px, py = x1 + tt * dx, y1 + tt * dy
                    if ((t["x"] - px) ** 2 + (t["y"] - py) ** 2) ** 0.5 < 36: ok = True; break
            if ok:
                keys.add(k); changed = True
        for i, ld in enumerate(L):
            fs, bs = ld["fs"], ld["bs"]
            if fs is None or bs is None: continue
            if ld["flags"] & 1: continue
            for x, y in ((fs, bs), (bs, fs)):
                if x in reach and y not in reach and passable(x, y):
                    reach.add(y); changed = True
        for i, ld in enumerate(L):
            sp = ld["special"]
            if sp == 0 or sp not in enabled: continue
            if i in disabled_lines: continue
            fs, bs = ld["fs"], ld["bs"]
            if sp in USE_KINDS or sp in GUN_KINDS:
                act = fs in reach
            elif sp in TELEPORT:
                act = fs in reach
            else:
                act = (fs in reach) or (bs is not None and bs in reach)
            if not act: continue
            if sp in EXIT_USE or sp in EXIT_WALK:
                exit_hit.append((i, sp)); continue
            if i in fired: continue
            if sp in DOOR_MANUAL:
                k = DOOR_MANUAL[sp]
                if k and k not in keys: continue
                if bs is None: fired.add(i); continue
                widen_c(bs, max(lowest_nb_ceil(bs) - 4, base_ceil[bs]))
            elif sp in DOOR_OPENING_TAG:
                for s in tagged(ld["tag"]):
                    widen_c(s, max(lowest_nb_ceil(s) - 4, base_ceil[s]))
            elif sp in LIFT:
                for s in tagged(ld["tag"]): widen_f(s, lowest_nb_floor(s))
            elif sp in LOWER_LOWEST:
                for s in tagged(ld["tag"]): widen_f(s, lowest_nb_floor(s))
            elif sp in LOWER_HIGHEST:
                for s in tagged(ld["tag"]): widen_f(s, highest_nb_floor(s))
            elif sp in TURBO_LOWER:
                for s in tagged(ld["tag"]):
                    h = highest_nb_floor(s)
                    if h != base_floor[s]: h += 8
                    widen_f(s, h)
            elif sp in RAISE_NEXT:
                for s in tagged(ld["tag"]): widen_f(s, next_higher_floor(s))
            elif sp in RAISE_LOWCEIL:
                for s in tagged(ld["tag"]):
                    widen_f(s, min(lowest_nb_ceil(s), base_ceil[s]))
            elif sp in STAIRS:
                size = STAIRS[sp]
                for s0 in tagged(ld["tag"]):
                    s = s0; tex = SEC[s]["ftex"]; h = base_floor[s] + size
                    widen_f(s, h)
                    seen = {s}
                    while True:
                        nxt = None
                        for li in M.sec_lines[s]:
                            l2 = L[li]
                            if not (l2["flags"] & 4): continue
                            if l2["fs"] != s: continue
                            t2 = l2["bs"]
                            if t2 is None or SEC[t2]["ftex"] != tex: continue
                            h += size
                            if t2 in seen: continue
                            nxt = t2; break
                        if nxt is None: break
                        s = nxt; seen.add(s); widen_f(s, h)
            elif sp in DONUT:
                for s1 in tagged(ld["tag"]):
                    l0 = L[M.sec_lines[s1][0]]
                    s2 = l0["bs"] if l0["fs"] == s1 else l0["fs"]
                    if s2 is None: continue
                    for li in M.sec_lines[s2]:
                        l2 = L[li]
                        if not (l2["flags"] & 4) or l2["bs"] == s1: continue
                        s3 = l2["bs"]
                        widen_f(s2, base_floor[s3]); widen_f(s1, base_floor[s3])
                        break
            elif sp in TELEPORT:
                for s in tagged(ld["tag"]):
                    for t in M.T:
                        if t["type"] == 14 and M.point_sector(t["x"], t["y"]) == s:
                            if s not in reach: reach.add(s)
            fired.add(i); changed = True
        # E1M8 boss death: tag 666 lower-to-lowest when all barons are dead
        if boss_dead and M.name == "E1M8" and "boss" not in fired:
            barons = [t for t in M.T if t["type"] == 3003 and not (t["opts"] & 16)]
            if barons and all(M.point_sector(t["x"], t["y"]) in reach for t in barons):
                for s in tagged(666): widen_f(s, lowest_nb_floor(s))
                fired.add("boss"); changed = True
    end11 = [i for i, s in enumerate(SEC) if s["special"] == 11]
    return dict(reach=reach, keys=keys, exits=exit_hit, end11=[s for s in end11 if s in reach],
                state=(flo, fhi, clo, chi, ftex))

VANILLA = (set(DOOR_MANUAL) | DOOR_OPENING_TAG | LIFT | LOWER_LOWEST | LOWER_HIGHEST | TURBO_LOWER |
           RAISE_NEXT | RAISE_LOWCEIL | set(STAIRS) | DONUT | TELEPORT | EXIT_USE | EXIT_WALK)

def summary(r):
    ex = sorted(set(sp for _, sp in r["exits"]))
    return "reach=%d keys=%s exits=%s end11=%s" % (len(r["reach"]), "".join(sorted(r["keys"])), ex, r["end11"])

if __name__ == "__main__":
    args = sys.argv[1:]
    wad = "wad/DOOM1.WAD"
    if args and not args[0].upper().startswith("E"):
        wad = args.pop(0)
    data, lumps = load(wad)
    names = [a.upper() for a in args] or ["E1M%d" % i for i in range(1, 10)]
    ex = lambda r: sorted(set(sp for _, sp in r["exits"])) + (["end11"] if r["end11"] else [])
    print("map   vanilla exits   engine exits    sectors lost vs vanilla   specials that would recover them")
    for nm in names:
        M = Map(data, lumps, nm)
        a = run(M, VANILLA)
        c = run(M, ENGINE)
        lost = a["reach"] - c["reach"]
        gains = []
        if lost:
            for sp in sorted(VANILLA - ENGINE):
                g = run(M, ENGINE | {sp})["reach"] - c["reach"]
                if g: gains.append("%d:+%d" % (sp, len(g)))
        print("%-5s %-15s %-15s %-25d %s" % (nm, ex(a), ex(c), len(lost), ", ".join(gains)))
