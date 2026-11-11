"""nav.py — where the player can walk, and how to get there (stdlib only).

An occupancy grid over one map, evaluated with the ENGINE's collision rules
(src/player.cyr move_check_linedef): a position is clear when every linedef
within the player's radius is two-sided, not ML_BLOCKING, has a step of at most
24 above the mover's current floor and at least 56 units of headroom. Players
may drop off any ledge. Heights come from the live game (the --lockstep record's
H lines over the WAD), with manual doors the bot can open treated as open.

A* runs on the grid (8-connected); the cell path is then string-pulled into a
few waypoints the bot can steer between.
"""
import heapq, math

STEP = 24
HEADROOM = 56
DAMAGE_SPECIALS = {4: 20, 5: 10, 7: 5, 16: 20, 11: 20}

# Lifts (doors.cyr lift_activate): walk 10/88/121, switch 21/62/122. A lift
# lowers to its lowest neighbouring floor, waits, and returns to its own height.
LIFT_WALK = {10, 88, 121}
LIFT_SWITCH = {21, 62, 122}
LIFT_SPECIALS = LIFT_WALK | LIFT_SWITCH

# Remote door switches (S1 / SR open-wait-close, S1 open-stay). When one sits on
# the door sector's own face and is tagged to it, it works like a manual door.
SWITCH_DOORS = {29, 63, 103}

# Manual (use-activated, local) doors: special -> key colour needed or None.
MANUAL_DOORS = {1: None, 31: None, 117: None, 118: None,
                26: 'blue', 32: 'blue', 27: 'yellow', 34: 'yellow', 28: 'red', 33: 'red'}


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / l2
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def segs_cross(ax, ay, bx, by, cx, cy, dx, dy):
    def orient(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    o1 = orient(ax, ay, bx, by, cx, cy)
    o2 = orient(ax, ay, bx, by, dx, dy)
    o3 = orient(cx, cy, dx, dy, ax, ay)
    o4 = orient(cx, cy, dx, dy, bx, by)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0) and o1 != 0 and o2 != 0


class Nav:
    def __init__(self, m, cell=8, radius=18.0):
        self.m = m
        self.cell = cell
        self.radius = radius
        x0, y0, x1, y1 = m.bbox
        self.ox, self.oy = x0 - 40, y0 - 40
        self.nx = int((x1 - x0 + 80) / cell) + 1
        self.ny = int((y1 - y0 + 80) / cell) + 1
        n = self.nx * self.ny
        self.sec = [0] * n
        for j in range(self.ny):
            cy = self.oy + (j + 0.5) * cell
            for i in range(self.nx):
                self.sec[j * self.nx + i] = m.point_sector(self.ox + (i + 0.5) * cell, cy)
        # lines within `radius` of each cell centre
        self.near = {}
        for ln in m.lines:
            x1_, y1_, x2_, y2_ = m.line_xy(ln['i'])
            i0 = int((min(x1_, x2_) - radius - self.ox) / cell) - 1
            i1 = int((max(x1_, x2_) + radius - self.ox) / cell) + 1
            j0 = int((min(y1_, y2_) - radius - self.oy) / cell) - 1
            j1 = int((max(y1_, y2_) + radius - self.oy) / cell) + 1
            for j in range(max(j0, 0), min(j1, self.ny - 1) + 1):
                cy = self.oy + (j + 0.5) * cell
                for i in range(max(i0, 0), min(i1, self.nx - 1) + 1):
                    cx = self.ox + (i + 0.5) * cell
                    if seg_dist(cx, cy, x1_, y1_, x2_, y2_) < radius:
                        self.near.setdefault(j * self.nx + i, []).append(ln['i'])
        self.solid = [ln['back'] < 0 or ln['front'] < 0 or (ln['flags'] & 1) != 0 for ln in m.lines]
        # lift sector -> (low, high, [activating lines])
        self.lifts = {}
        for ln in m.lines:
            if ln['special'] in LIFT_SPECIALS and ln['tag']:
                for sct in m.tagged(ln['tag']):
                    lo = m.lowest_neighbor_floor(sct)
                    hi = m.sectors[sct]['floor']
                    self.lifts.setdefault(sct, (lo, hi, []))[2].append(ln['i'])
        self.ranges = {}
        self.blocked = set()
        self.danger = set()
        self.trap = set()
        self.threat = set()
        self.avoid_cells = set()
        self.door_from = {}
        self.door_closed = {}
        # Cells on the HIGH side of a ledge (a drop of more than a step), close to
        # its edge: walking there, a little steering error drops the player off.
        self.ledge = set()
        for ln in m.lines:
            a, b = ln['front'], ln['back']
            if a < 0 or b < 0:
                continue
            fa, fb = m.sectors[a]['floor'], m.sectors[b]['floor']
            if abs(fa - fb) <= STEP:
                continue
            high = a if fa > fb else b
            x1_, y1_, x2_, y2_ = m.line_xy(ln['i'])
            for k in self.near.get(-1, ()):
                pass
            i0 = int((min(x1_, x2_) - 24 - self.ox) / cell) - 1
            i1 = int((max(x1_, x2_) + 24 - self.ox) / cell) + 1
            j0 = int((min(y1_, y2_) - 24 - self.oy) / cell) - 1
            j1 = int((max(y1_, y2_) + 24 - self.oy) / cell) + 1
            for j in range(max(j0, 0), min(j1, self.ny - 1) + 1):
                for i in range(max(i0, 0), min(i1, self.nx - 1) + 1):
                    k = j * self.nx + i
                    if self.sec[k] != high:
                        continue
                    cx, cy = self.center(k)
                    if seg_dist(cx, cy, x1_, y1_, x2_, y2_) < 22:
                        self.ledge.add(k)

    # ------------------------------------------------------------ sight
    def sight(self, ax, ay, bx, by, floor, ceil):
        """Rough 2D line of sight: False when a one-sided line, or a two-sided
        line whose opening is shut (live heights: a closed door), crosses the
        segment. The engine's own check also tests slopes; this only has to tell
        a spot behind a wall or a doorframe from one in the open, for cover."""
        if not hasattr(self, '_sb'):
            self._sb = {}
            for ln in self.m.lines:
                x1_, y1_, x2_, y2_ = self.m.line_xy(ln['i'])
                for j in range(int((min(y1_, y2_) - self.oy) // 64), int((max(y1_, y2_) - self.oy) // 64) + 1):
                    for i in range(int((min(x1_, x2_) - self.ox) // 64), int((max(x1_, x2_) - self.ox) // 64) + 1):
                        self._sb.setdefault((i, j), []).append(ln['i'])
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / 8))
        seen = set()
        for q in range(n + 1):
            x = ax + (bx - ax) * q / n
            y = ay + (by - ay) * q / n
            b = (int((x - self.ox) // 64), int((y - self.oy) // 64))
            for li in self._sb.get(b, ()):
                if li in seen:
                    continue
                seen.add(li)
                ln = self.m.lines[li]
                if ln['back'] >= 0 and ln['front'] >= 0:
                    a_, b_ = ln['front'], ln['back']
                    if min(ceil[a_], ceil[b_]) - max(floor[a_], floor[b_]) > 0:
                        continue
                x1_, y1_, x2_, y2_ = self.m.line_xy(li)
                if segs_cross(ax, ay, bx, by, x1_, y1_, x2_, y2_):
                    return False
        return True

    # ------------------------------------------------------------ heights
    def set_avoid_lines(self, lines, band=14.0):
        """Cells within `band` of linedefs that should not be crossed if there is
        another way (walk triggers that open a monster closet)."""
        self.avoid_cells = set()
        cell = self.cell
        for li in lines:
            x1_, y1_, x2_, y2_ = self.m.line_xy(li)
            i0 = int((min(x1_, x2_) - band - self.ox) / cell) - 1
            i1 = int((max(x1_, x2_) + band - self.ox) / cell) + 1
            j0 = int((min(y1_, y2_) - band - self.oy) / cell) - 1
            j1 = int((max(y1_, y2_) + band - self.oy) / cell) + 1
            for j in range(max(j0, 0), min(j1, self.ny - 1) + 1):
                for i in range(max(i0, 0), min(i1, self.nx - 1) + 1):
                    cx, cy = self.ox + (i + 0.5) * cell, self.oy + (j + 0.5) * cell
                    if seg_dist(cx, cy, x1_, y1_, x2_, y2_) < band:
                        self.avoid_cells.add(j * self.nx + i)

    def set_threats(self, monsters, radius=160.0):
        """Cells within `radius` of a live monster: priced, so a route skirts a
        crowd (or a closet of them) when there is another way."""
        self.threat = set()
        for (x, y) in monsters:
            r = radius
            for j in range(int((y - r - self.oy) / self.cell), int((y + r - self.oy) / self.cell) + 1):
                for i in range(int((x - r - self.ox) / self.cell), int((x + r - self.ox) / self.cell) + 1):
                    cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                    if (cx - x) * (cx - x) + (cy - y) * (cy - y) < r * r:
                        self.threat.add(j * self.nx + i)

    def set_obstacles(self, obstacles, learned=()):
        """Solid things the planner must keep the player's radius clear of:
        [(x, y, radius)] (barrels; monsters move and are left to the bot).
        `learned`: [(x, y, radius)] spots the player was stopped at in play,
        which the grid thinks clear — blocked, without a barrel's blast zone."""
        self.blocked = set()
        self.danger = set()
        self.near_obst = set()
        self.obst = list(obstacles)
        for (x, y, r) in learned:
            rr = r + self.radius
            for j in range(int((y - rr - self.oy) / self.cell), int((y + rr - self.oy) / self.cell) + 1):
                for i in range(int((x - rr - self.ox) / self.cell), int((x + rr - self.ox) / self.cell) + 1):
                    cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                    if math.hypot(cx - x, cy - y) < rr:
                        self.blocked.add(j * self.nx + i)
        for (x, y, r) in obstacles:
            # blast range (a barrel's explosion reaches 128 units): pricey, not forbidden
            rr = 128.0
            for j in range(int((y - rr - self.oy) / self.cell), int((y + rr - self.oy) / self.cell) + 1):
                for i in range(int((x - rr - self.ox) / self.cell), int((x + rr - self.ox) / self.cell) + 1):
                    cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                    if math.hypot(cx - x, cy - y) < rr:
                        self.danger.add(j * self.nx + i)
            rr = r + self.radius
            ro = rr + 10        # a margin string-pulling may not cut into (see smooth)
            i0 = int((x - ro - self.ox) / self.cell)
            i1 = int((x + ro - self.ox) / self.cell)
            j0 = int((y - ro - self.oy) / self.cell)
            j1 = int((y + ro - self.oy) / self.cell)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                    d_ = math.hypot(cx - x, cy - y)
                    if d_ < rr:
                        self.blocked.add(j * self.nx + i)
                    elif d_ < ro:
                        self.near_obst.add(j * self.nx + i)

    def plan_heights(self, live_floor, live_ceil, keys=0, open_doors=True, extra=None, special=None):
        """Heights to plan against: live ones, with every manual door the bot can
        open (key in hand) raised to its open height. `extra` maps sector ->
        (floor, ceil) overrides (a lift the route will ride, a bridge that will rise)."""
        f = list(live_floor)
        c = list(live_ceil)
        # sector specials as the engine has them NOW (a raise-and-change floor
        # clears its nukage): damage costs and safe cells use these
        self.SP = list(special) if special is not None else [s_['special'] for s_ in self.m.sectors]
        self.door_sectors = {}
        # A door opens only from the side an opener line faces (E1M5's sector 52
        # has a manual face to the west and a plain line to the east), so a CLOSED
        # door may be planned through only when entered from one of those sectors.
        self.door_from = {}
        self.door_closed = {}
        if open_doors:
            for ln in self.m.lines:
                sp = ln['special']
                if sp in MANUAL_DOORS and ln['back'] >= 0:
                    need = MANUAL_DOORS[sp]
                    if need is not None and not (keys & {'blue': 1, 'yellow': 2, 'red': 4}[need]):
                        continue
                    s = ln['back']
                elif sp in SWITCH_DOORS and ln['tag'] and ln['back'] >= 0 and \
                        self.m.sectors[ln['back']]['tag'] == ln['tag']:
                    # a switch on the door's own face, tagged to it (E1M3 line 520):
                    # used like a manual door from that side
                    s = ln['back']
                else:
                    continue
                self.door_sectors.setdefault(s, []).append(ln['i'])
                self.door_from.setdefault(s, set()).add(ln['front'])
                self.door_closed[s] = live_ceil[s] - live_floor[s] < HEADROOM
                top = self.m.lowest_neighbor_ceil(s) - 4
                if c[s] < top:
                    c[s] = top
        self.ranges = {sct: (lo, hi) for sct, (lo, hi, _) in self.lifts.items()} if open_doors else {}
        if extra:
            for s, (ff, cc) in extra.items():
                if ff is not None:
                    f[s] = ff
                if cc is not None:
                    c[s] = cc
        self.F, self.C = f, c
        self.trap = self.find_traps()
        return f, c

    def sector_edges(self):
        """Directed sector moves at the planned heights: a -> b when some
        two-sided line between them can be walked over from a (step up <= 24,
        enough headroom; drops are free). Lifts at either end of their travel."""
        m, F, C, R = self.m, self.F, self.C, self.ranges
        out = [set() for _ in m.sectors]
        for li, ln in enumerate(m.lines):
            if self.solid[li]:
                continue
            a, b = ln['front'], ln['back']
            if a == b:
                continue
            fa_, fb_ = R.get(a, (F[a],)), R.get(b, (F[b],))
            room = min(C[a], C[b])
            for x, y, xs, ys in ((a, b, fa_, fb_), (b, a, fb_, fa_)):
                for f1 in xs:
                    for f2 in ys:
                        if f2 - f1 <= STEP and room - max(f1, f2) >= HEADROOM:
                            out[x].add(y)
        return out

    def alive_for(self, goal_sector):
        """Sectors from which goal_sector can still be reached."""
        edges = self.sector_edges()
        rev = [set() for _ in edges]
        for a, bs in enumerate(edges):
            for b in bs:
                rev[b].add(a)
        alive = {goal_sector}
        stack = [goal_sector]
        while stack:
            x = stack.pop()
            for y in rev[x]:
                if y not in alive:
                    alive.add(y)
                    stack.append(y)
        return alive

    def cliff_cells(self, alive, margin=28.0):
        """Cells in alive sectors within `margin` of a line whose other side is
        a dead sector: the rim of a one-way drop. Keeping off it leaves room
        for steering error."""
        out = set()
        cell = self.cell
        for ln in self.m.lines:
            a, b = ln['front'], ln['back']
            if a < 0 or b < 0 or (a in alive) == (b in alive):
                continue
            live = a if a in alive else b
            x1_, y1_, x2_, y2_ = self.m.line_xy(ln['i'])
            i0 = int((min(x1_, x2_) - margin - self.ox) / cell) - 1
            i1 = int((max(x1_, x2_) + margin - self.ox) / cell) + 1
            j0 = int((min(y1_, y2_) - margin - self.oy) / cell) - 1
            j1 = int((max(y1_, y2_) + margin - self.oy) / cell) + 1
            for j in range(max(j0, 0), min(j1, self.ny - 1) + 1):
                for i in range(max(i0, 0), min(i1, self.nx - 1) + 1):
                    k = j * self.nx + i
                    if self.sec[k] != live:
                        continue
                    cx, cy = self.center(k)
                    if seg_dist(cx, cy, x1_, y1_, x2_, y2_) < margin:
                        out.add(k)
        return out

    def find_traps(self):
        """Sectors with no way out at the planned heights: every neighbour is more
        than a step up (or too low a gap). A drop into one is one-way (E1M3's
        nukage channel before its bridge rises), so A* may not enter them."""
        m, F, C, R = self.m, self.F, self.C, self.ranges
        trap = set()
        for s_ in range(len(m.sectors)):
            fs = R.get(s_, (F[s_],))
            out = False
            for li in m.sector_lines[s_]:
                ln = m.lines[li]
                if self.solid[li]:
                    continue
                n = ln['back'] if ln['front'] == s_ else ln['front']
                if n == s_:
                    continue
                fn = R.get(n, (F[n],))
                for a in fs:
                    for b in fn:
                        top = a if a > b else b
                        if b - a <= STEP and min(C[s_], C[n]) - top >= HEADROOM:
                            out = True
                if out:
                    break
            if not out:
                trap.add(s_)
        return trap

    def same_side(self, li, k, q):
        x1, y1, x2, y2 = self.m.line_xy(li)
        ax, ay = self.center(k)
        bx, by = self.center(q)
        sa = (ax - x1) * (y2 - y1) - (ay - y1) * (x2 - x1)
        sb = (bx - x1) * (y2 - y1) - (by - y1) * (x2 - x1)
        return (sa > 0 and sb > 0) or (sa < 0 and sb < 0)

    def ok(self, k, cfloor, frm=None):
        """Can a mover standing at floor `cfloor` occupy cell k? A lift's floor
        (self.ranges) may be at either end of its travel: optimistic, as the
        executor waits for or calls the lift. With `frm` (the cell it moves
        from), the engine's escape rule applies: a line the mover is ALREADY
        inside the radius of only vetoes a move that crosses it (player.cyr
        move_check_linedef) — that is how a player walks away from the foot of a
        ledge it just dropped off."""
        if k in self.blocked:
            return False
        lines = self.near.get(k)
        if not lines:
            return True
        near_from = self.near.get(frm, ()) if frm is not None else ()
        for li in lines:
            if not self._line_ok(li, cfloor):
                if li in near_from and self.same_side(li, frm, k):
                    continue
                return False
        return True

    def _line_ok(self, li, cfloor):
        if self.solid[li]:
            return False
        F, C, R = self.F, self.C, self.ranges
        if True:
            ln = self.m.lines[li]
            a, b = ln['front'], ln['back']
            if R and (a in R or b in R):
                fa = R[a] if a in R else (F[a],)
                fb = R[b] if b in R else (F[b],)
                low = C[a] if C[a] < C[b] else C[b]
                for x in fa:
                    for y in fb:
                        top = x if x > y else y
                        if top - cfloor <= STEP and low - top >= HEADROOM:
                            return True
                return False
            top = F[a] if F[a] > F[b] else F[b]
            if top - cfloor > STEP:
                return False
            low = C[a] if C[a] < C[b] else C[b]
            if low - top < HEADROOM:
                return False
        return True

    def ok_live(self, q, k, floor, ceil, override=None, cfloor=None):
        """ok_from against the LIVE heights (no ranges, no door optimism);
        override = {sector: floor} to ask "would it pass with the lift there?".
        cfloor = the mover's real floor when k's cell centre lies in another sector."""
        saved = (self.F, self.C, self.ranges)
        F = floor
        if override:
            F = list(floor)
            for s_, v in override.items():
                F[s_] = v
        self.F, self.C, self.ranges = F, ceil, {}
        try:
            return self.ok(q, F[self.sec[k]] if cfloor is None else cfloor, k)
        finally:
            self.F, self.C, self.ranges = saved

    def lift_of(self, q, k):
        """A lift sector involved in moving k -> q (q's nearby lines or either cell)."""
        for s_ in (self.sec[q], self.sec[k]):
            if s_ in self.lifts:
                return s_
        for li in self.near.get(q, ()):
            ln = self.m.lines[li]
            for s_ in (ln['front'], ln['back']):
                if s_ in self.lifts:
                    return s_
        return None

    def floors_at(self, k):
        """The floor(s) a mover in cell k can stand at (both ends on a lift)."""
        s = self.sec[k]
        r = self.ranges.get(s)
        return r if r else (self.F[s],)

    def ok_from(self, q, k):
        for cf in self.floors_at(k):
            if self.ok(q, cf, k):
                return True
        return False

    def cell_of(self, x, y):
        i = int((x - self.ox) / self.cell)
        j = int((y - self.oy) / self.cell)
        if i < 0 or j < 0 or i >= self.nx or j >= self.ny:
            return -1
        return j * self.nx + i

    def center(self, k):
        return (self.ox + (k % self.nx + 0.5) * self.cell, self.oy + (k // self.nx + 0.5) * self.cell)

    def floor_at(self, k):
        return self.F[self.sec[k]]

    # ------------------------------------------------------------ search
    def astar(self, sx, sy, goal_fn, heur_xy, max_nodes=400000, damage_ok=False, avoid=None, start_floor=None,
              alive=None, cliff=None, dmg_weight=1):
        """Cell path from (sx, sy) to the first cell where goal_fn(k) is true.
        heur_xy = (gx, gy) for the A* heuristic. avoid: set of sectors to price
        very high (but not forbid)."""
        start = self.cell_of(sx, sy)
        if start < 0:
            return None
        nx = self.nx
        gx, gy = heur_xy
        cs = self.cell
        dist = {start: 0.0}
        prev = {start: -1}
        pq = [(0.0, start)]
        SP = getattr(self, 'SP', None) or [s_['special'] for s_ in self.m.sectors]
        dmg = {i: DAMAGE_SPECIALS.get(sp_, 0) for i, sp_ in enumerate(SP)}
        n_exp = 0
        D = math.sqrt(2) * cs
        near, blocked, sec, ny = self.near, self.blocked, self.sec, self.ny
        trap, door_closed, door_from = self.trap, self.door_closed, self.door_from
        danger, ledge, threat = self.danger, self.ledge, self.threat
        avoid_cells = self.avoid_cells
        ranges, F = self.ranges, self.F
        ok = self.ok
        NB = ((1, 0, cs), (-1, 0, cs), (0, 1, cs), (0, -1, cs), (1, 1, D), (1, -1, D), (-1, 1, D), (-1, -1, D))

        def free(q, floors, k):
            # the common case first: a cell no line is within reach of
            if q not in near:
                return q not in blocked
            for f_ in floors:
                if ok(q, f_, k):
                    return True
            return False

        while pq:
            d, k = heapq.heappop(pq)
            g = dist[k]
            if goal_fn(k):
                path = []
                while k != -1:
                    path.append(k)
                    k = prev[k]
                return path[::-1]
            n_exp += 1
            if n_exp > max_nodes:
                return None
            i, j = k % nx, k // nx
            sk = sec[k]
            if k == start and start_floor is not None:
                floors = (start_floor,)   # the start cell's centre may sit across a line from the player
            else:
                r_ = ranges.get(sk)
                floors = r_ if r_ else (F[sk],)
            for di, dj, w in NB:
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= nx or jj >= ny:
                    continue
                q = jj * nx + ii
                if not free(q, floors, k):
                    continue
                if di and dj:   # no corner cutting
                    if not free(j * nx + ii, floors, k) or not free(jj * nx + i, floors, k):
                        continue
                sq = sec[q]
                if sq != sk:
                    if sq in trap or sk in trap:
                        continue      # never into a pit you cannot climb out of (nor "out" of one)
                    if door_closed.get(sq) and sk not in door_from.get(sq, ()):
                        continue      # a shut door, from a side it cannot be opened from
                    if alive is not None and sq not in alive and sk in alive:
                        continue      # nor anywhere the goal cannot be reached from
                if cliff is not None and q in cliff and k not in cliff:
                    continue          # and keep off the rim of such a drop
                cost = w
                if dmg[sq] and not damage_ok:
                    cost *= 1 + dmg[sq] * dmg_weight
                if avoid and sq in avoid:
                    cost *= 50
                if q in danger:
                    cost *= 6
                if q in ledge:
                    cost *= 5
                if q in threat:
                    cost *= 3
                if q in avoid_cells:
                    cost *= 40
                ng = g + cost
                if ng < dist.get(q, 1e18):
                    dist[q] = ng
                    prev[q] = k
                    qx = self.ox + (q % nx + 0.5) * cs
                    qy = self.oy + (q // nx + 0.5) * cs
                    # weighted A* (x1.6): the cost multipliers above make the plain
                    # straight-line bound far too weak, and a slightly longer path
                    # found 10x faster is the better trade for a bot
                    heapq.heappush(pq, (ng + 1.6 * math.hypot(qx - gx, qy - gy), q))
        return None

    def walkable_segment(self, ax, ay, bx, by, cfloor, allowed_sectors=None, forbid_cells=None):
        """Straight walk a -> b stays on clear cells, never stepping up more than
        STEP from the floor it is on. With `allowed_sectors`, it also stays inside
        those sectors (smoothing must not cut a corner the search went around,
        e.g. across nukage)."""
        n = int(math.hypot(bx - ax, by - ay) / 4) + 1
        last = self.cell_of(ax, ay)
        for s in range(1, n + 1):
            t = s / n
            k = self.cell_of(ax + (bx - ax) * t, ay + (by - ay) * t)
            if k == last:
                continue
            if k < 0 or not self.ok_from(k, last):
                return False
            sk_, sq_ = self.sec[last], self.sec[k]
            if sq_ != sk_ and self.door_closed.get(sq_) and sk_ not in self.door_from.get(sq_, ()):
                return False
            if allowed_sectors is not None and self.sec[k] not in allowed_sectors:
                return False
            if forbid_cells is not None and k in forbid_cells:
                return False
            # keep a waypoint at every lift edge: the bot stops there for the lift
            if (self.sec[k] in self.ranges) != (self.sec[last] in self.ranges):
                return False
            last = k
        return True

    def smooth(self, cells, cliff=None):
        """String-pull a cell path into waypoints (world coordinates)."""
        if not cells:
            return []
        pts = [self.center(k) for k in cells]
        # A pulled segment may cross any sector the cell path visits, except a
        # damaging one the path did not enter: those detours are deliberate.
        visited = set(self.sec[k] for k in cells)
        SP = getattr(self, 'SP', None) or [s_['special'] for s_ in self.m.sectors]
        safe = set(i for i, sp_ in enumerate(SP) if sp_ not in DAMAGE_SPECIALS)
        allowed = safe | visited
        # nor cut close past a barrel: between two of them (E1M5's secret
        # shotgun door) the way is a cell or two wide, and only the cells the
        # search chose are known to fit
        forbid = set(cliff) if cliff else set()
        forbid |= getattr(self, 'near_obst', set())
        # nor onto the lip of a drop the search kept off (ledge cells cost 5x
        # there): pulled straight, E1M4's stairs out of the nukage pit ran four
        # units from its edge, and three lives fell back in
        forbid |= self.ledge
        forbid = (forbid - set(cells)) or None
        out = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1:
                if self.walkable_segment(pts[i][0], pts[i][1], pts[j][0], pts[j][1], None, allowed, forbid):
                    break
                j -= 1
            out.append(pts[j])
            i = j
        return out

    def path_to_point(self, sx, sy, gx, gy, tol=12.0, **kw):
        gs = self.m.point_sector(gx, gy)
        if 'alive' not in kw and gs >= 0:
            alive = self.alive_for(gs)
            # the sector graph already says whether the goal can be reached at
            # all: if not, skip the grid search (a failing A* walks every cell)
            k0 = self.cell_of(sx, sy)
            if k0 >= 0 and self.sec[k0] not in alive and self.m.point_sector(sx, sy) not in alive:
                return None
            kw['alive'] = alive
            kw['cliff'] = self.cliff_cells(alive)
        goal = set()
        r = int(tol / self.cell) + 1
        gi, gj = int((gx - self.ox) / self.cell), int((gy - self.oy) / self.cell)
        for j in range(gj - r, gj + r + 1):
            for i in range(gi - r, gi + r + 1):
                if 0 <= i < self.nx and 0 <= j < self.ny:
                    cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                    if math.hypot(cx - gx, cy - gy) <= tol:
                        goal.add(j * self.nx + i)
        cells = self.astar(sx, sy, goal.__contains__, (gx, gy), **kw)
        if cells is None:
            return None
        return self.smooth(cells, kw.get('cliff'))

    def nearest_safe(self, sx, sy, limit=4000, path=False):
        """Nearest cell (BFS over clear cells) whose sector does not hurt; with
        path=True, the walk there as waypoints (out of a pit it is the stairs,
        not the wall the nearest safe floor sits on top of — E1M4 sector 42)."""
        start = self.cell_of(sx, sy)
        if start < 0:
            return None
        seen = {start}
        prev = {start: -1}
        q = [start]
        qi = 0
        while qi < len(q) and qi < limit:
            k = q[qi]
            qi += 1
            SP = getattr(self, 'SP', None)
            sp_ = SP[self.sec[k]] if SP else self.m.sectors[self.sec[k]]['special']
            if sp_ not in DAMAGE_SPECIALS and k not in self.near:
                if not path:
                    return self.center(k)
                cells = []
                while k != -1:
                    cells.append(k)
                    k = prev[k]
                return self.smooth(cells[::-1])
            i, j = k % self.nx, k // self.nx
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < self.nx and 0 <= jj < self.ny:
                    n = jj * self.nx + ii
                    if n not in seen and self.ok_from(n, k):
                        seen.add(n)
                        prev[n] = k
                        q.append(n)
        return None

    def path_to_touch(self, sx, sy, ix, iy, **kw):
        """Path to anywhere the engine would let the player pick up an item at
        (ix, iy): |dx| and |dy| under 36 (item 20 + player 16) and the item between 8 below and 56 above the player's floor
        (things.cyr things_check_pickups). A key on a pedestal (E1M7's blue) is
        taken from the floor beside it, never stood on."""
        isec = self.m.point_sector(ix, iy)
        iz = self.F[isec] if isec >= 0 else 0
        goal = set()
        # engine reach is strictly under 36; a cell counts if its centre is within
        # 36 + half a cell, and the bot's last step pushes on toward the item itself
        # (into the ledge if need be), which closes the rest
        R_ = 36.0 + self.cell / 2.0
        r = int(R_ / self.cell) + 1
        gi, gj = int((ix - self.ox) / self.cell), int((iy - self.oy) / self.cell)
        for j in range(gj - r, gj + r + 1):
            for i in range(gi - r, gi + r + 1):
                if not (0 <= i < self.nx and 0 <= j < self.ny):
                    continue
                cx, cy = self.ox + (i + 0.5) * self.cell, self.oy + (j + 0.5) * self.cell
                if abs(cx - ix) >= R_ or abs(cy - iy) >= R_:
                    continue
                k = j * self.nx + i
                f = self.F[self.sec[k]]
                if -8 <= iz - f <= 56 and k not in self.blocked and self.ok(k, f):
                    goal.add(k)
        if not goal:
            return None
        if 'alive' not in kw:
            alive = set()
            for gs in set(self.sec[k] for k in goal):
                alive |= self.alive_for(gs)
            k0 = self.cell_of(sx, sy)
            if k0 >= 0 and self.sec[k0] not in alive and self.m.point_sector(sx, sy) not in alive:
                return None
            kw['alive'] = alive
            kw['cliff'] = self.cliff_cells(alive)
        cells = self.astar(sx, sy, goal.__contains__, (ix, iy), **kw)
        if cells is None:
            return None
        return self.smooth(cells, kw.get('cliff'))

    def nearest_where(self, sx, sy, pred, limit=3000):
        """Nearest clear cell (BFS over cells the player can walk between) whose
        centre satisfies pred(x, y)."""
        start = self.cell_of(sx, sy)
        if start < 0:
            return None
        seen = {start}
        q = [start]
        qi = 0
        while qi < len(q) and qi < limit:
            k = q[qi]
            qi += 1
            cx, cy = self.center(k)
            if k != start and pred(cx, cy) and k not in self.near:
                return (cx, cy)
            i, j = k % self.nx, k // self.nx
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < self.nx and 0 <= jj < self.ny:
                    n = jj * self.nx + ii
                    if n not in seen and self.ok_from(n, k):
                        seen.add(n)
                        q.append(n)
        return None

    def path_to_cells(self, sx, sy, goal_set, hxy, **kw):
        cells = self.astar(sx, sy, lambda k: k in goal_set, hxy, **kw)
        if cells is None:
            return None
        return self.smooth(cells)
