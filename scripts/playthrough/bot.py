"""bot.py — the playthrough's player: route objectives, steering, doors, combat.

Each tick it reads the --lockstep State and answers with the keys to hold.
It sees what the record shows (its own position, things, live sector heights)
and acts only through keys; nothing in the engine is changed or skipped.
"""
import math, os

import nav as navmod
import wadmap

try:
    import reachability as R
except ImportError:      # scripts/ is the parent of this directory
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import reachability as R

A = 1024          # angle units per turn (engine: tables.cyr, 1024-entry sine)
TURN_RUN = 8      # angle units per tick with run held (player.cyr PLAYER_TURN_SPEED_RUN)
USE_RANGE = 64    # doors.cyr doors_use ray length
AWAKE = (2, 3, 4, 5)   # STATE_SEE / CHASE / ATTACK / PAIN
CAT_MONSTER, CAT_ITEM, CAT_WEAPON, CAT_KEY, CAT_PROJECTILE = 1, 2, 3, 4, 6


def ang_to(dx, dy):
    return int(round(math.atan2(dy, dx) * (A / 2) / math.pi)) % A


def adiff(a, b):
    """a - b, wrapped to [-512, 512)."""
    d = (a - b) % A
    return d - A if d >= A // 2 else d


def move_keys(rel):
    """Movement keys that best approximate a world direction `rel` angle units
    off the facing (positive = to the left)."""
    r = abs(rel)
    side = 'sl' if rel > 0 else 'sr'
    if r <= 64:
        return ['fwd']
    if r <= 192:
        return ['fwd', side]
    if r <= 320:
        return [side]
    if r <= 448:
        return ['back', side]
    return ['back']


def use_point(m, li, px, py, back_off=30.0):
    """Where to stand to `use` linedef li, and the point on the line to face. The
    engine only takes a use from a line's FRONT (right-hand) side (doors.cyr
    doors_use, U-11), so the stand point is always in front; (px, py) only picks
    where along the line to aim."""
    x1, y1, x2, y2 = m.line_xy(li)
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = (y2 - y1) / L, -(x2 - x1) / L          # right-hand normal = front side
    # aim at the point of the line nearest the player, kept off the very ends
    t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (L * L)
    t = min(max(t, 0.25), 0.75) if L > 32 else 0.5
    qx, qy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
    return (qx + nx * back_off, qy + ny * back_off), (qx, qy)


def in_front(m, li, px, py):
    x1, y1, x2, y2 = m.line_xy(li)
    return (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1) > 0


def use_ray_hit(m, floor, ceil, px, py, ang):
    """The line the engine's use ray hits from (px, py) facing `ang`
    (doors.cyr doors_use): the nearest SPECIAL line crossed within 64 units,
    unless a nearer one-sided wall or closed portal blocks it. -1 = none."""
    ux = math.cos(ang * math.pi / (A / 2)) * USE_RANGE
    uy = math.sin(ang * math.pi / (A / 2)) * USE_RANGE
    best, best_t, block_t = -1, 2.0, 2.0
    for ln in m.lines:
        x1, y1, x2, y2 = m.line_xy(ln['i'])
        ldx, ldy = x2 - x1, y2 - y1
        den = ux * ldy - uy * ldx
        if den == 0:
            continue
        t1 = ((x1 - px) * ldy - (y1 - py) * ldx) / den
        t2 = ((x1 - px) * uy - (y1 - py) * ux) / den
        if t1 <= 0 or t1 > 1 or t2 < 0 or t2 > 1:
            continue
        if ln['special']:
            if t1 < best_t:
                best, best_t = ln['i'], t1
            continue
        a, b = ln['front'], ln['back']
        if a < 0 or b < 0 or min(ceil[a], ceil[b]) <= max(floor[a], floor[b]):
            block_t = min(block_t, t1)
    if best >= 0 and block_t < best_t:
        return -1
    return best


def stand_points(m, li, px, py):
    """Candidate (stand, aim) pairs in front of li: the aim point near the
    player first, then spread along the line, at a few distances."""
    x1, y1, x2, y2 = m.line_xy(li)
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = (y2 - y1) / L, -(x2 - x1) / L
    t0 = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (L * L)
    ts = [min(max(t0, 0.25), 0.75), 0.5, 0.3, 0.7, 0.15, 0.85]
    for d in (30.0, 22.0, 40.0):
        for t in ts:
            qx, qy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            yield (qx + nx * d, qy + ny * d), (qx, qy)


def front_point(m, li, d=30.0):
    x1, y1, x2, y2 = m.line_xy(li)
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = (y2 - y1) / L, -(x2 - x1) / L
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return (mx + nx * d, my + ny * d), (mx, my)


def parse_route(text):
    steps = []
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if line:
            steps.append(line.split())
    return steps


class Bot:
    def __init__(self, doom, wad, route_dir, log, png_dir=None):
        self.d = doom
        self.wad = wad
        self.route_dir = route_dir
        self.log = log
        self.png_dir = png_dir
        self.maps = {}
        self.gen = None
        self.m = None
        self.nav = None
        self.deaths = 0
        self.events = []
        self.trace = []
        self.result = None

    # ---------------------------------------------------------------- setup
    def say(self, msg):
        st = self.d.state
        line = '[%s t=%d hp=%d] %s' % (st.map, st.level_time, st.health, msg) if st else msg
        self.log.write(line + '\n')
        self.log.flush()

    def enter_map(self, st):
        if st.map not in self.maps:
            m = wadmap.Map(self.wad, st.map)
            self.maps[st.map] = (m, navmod.Nav(m))
        self.m, self.nav = self.maps[st.map]
        self.d.attach_map(self.m)
        self.gen = st.map_gen
        path = os.path.join(self.route_dir, st.map + '.route')
        self.steps = parse_route(open(path).read()) if os.path.exists(path) else []
        self.si = 0
        self.path = None
        self.goal = None
        self.mode = None
        self.trace = []
        self.hp_hist = []
        self.retreating = False
        self.stuck_t = 0
        self.best = 1e18
        self.wait_until = None
        self.used_tick = -999
        self.door = None
        self.fire_hold = 0
        self.obj_cache = {}
        self.sub = []            # pushed sub-objectives (lift calls), run before the route step
        self.sub_started = {}
        self.sub_seq = 0
        self.lift_seen = {}      # lift sector -> (floor, tick it last changed)
        self.lift_wait = None
        self.lift_called = {}
        self.no_path = 0
        self.last_moving = False
        self.lift_fail = {}      # (lift, line) -> tick until which that call is not tried
        self.lift_pending = None # (lift, line, tick, floor) awaiting proof the call worked
        self.tgt = None          # (idx, since_tick, health_then)
        self.ignore = {}         # monster idx -> tick until which it is ignored
        self.proj_prev = {}      # projectile idx -> (x, y)
        self.skip_items = set()  # pickups that proved unreachable this life
        self.next_scan = 0
        self.prev_hp = st.health
        self.prev_kills = st.kills
        self.fired = set()       # trigger lines this bot has walked over / used on this map
        self.trig_tried = {}     # goal -> tick of the last runtime trigger search
        self.say('enter map (route: %d steps)' % len(self.steps))

    # ---------------------------------------------------------------- per tick
    def tick(self):
        st = self.d.state
        if st is None:
            return None
        if st.map_gen != self.gen:
            if self.m is not None and self.png_dir:
                self.dump_png()
            self.enter_map(st)
        self.d.apply_heights(st)
        if st.screen_name in ('finale_text', 'finale_pic'):
            self.result = 'finale'
            return None
        if st.screen_name == 'menu':
            self.result = 'menu'
            return None
        if st.screen_name in ('intermission', 'death'):
            if st.screen_name == 'death' and self.mode != 'dead':
                self.deaths += 1
                self.mode = 'dead'
                self.say('DIED (deaths=%d)' % self.deaths)
                self.screen_t = 0
            if self.mode not in ('dead', 'inter'):
                self.mode = 'inter'
                self.screen_t = 0
                self.say('intermission: kills %d/%d items %d/%d secrets %d/%d' % (
                    st.kills, st.max_kills, st.items, st.max_items, st.secrets, st.max_secrets))
            self.screen_t += 1
            # dismiss gate: ignore 35 tics, need 8 quiet tics, then a press
            if self.screen_t > 50 and self.screen_t % 12 == 0:
                return ['use']
            return []
        if self.mode in ('dead', 'inter'):
            self.mode = None
            if st.map_gen == self.gen:
                # respawn on the same map: start the route over
                self.enter_map(st)
        self.trace.append((st.x, st.y))
        self.hp_hist.append((st.level_time, st.health))
        if len(self.hp_hist) > 140:
            del self.hp_hist[:40]
        if self.tgt is None:
            self.retreating = False
        return self.play(st)

    # ---------------------------------------------------------------- play
    def play(self, st):
        keys = []
        aim = self.combat(st)
        # current objective
        move_to = None
        face = None
        self.track_lifts(st)
        if st.level_time % 105 == 0:
            vis = sum(1 for t in st.things if t.cat == CAT_MONSTER and t.los == 1)
            self.say('status hp=%d ar=%d w=%d ammo=%d/%d/%d kills=%d/%d visible=%d at (%d,%d) step=%d sub=%s' % (
                st.health, st.armor, st.weapon, st.bullets, st.shells, st.rockets, st.kills, st.max_kills,
                vis, st.x, st.y, self.si, self.sub))
        dry = self.shots(st) == 0
        if (aim is None or (dry and not aim[3])) and st.level_time >= self.next_scan and not self.sub:
            self.next_scan = st.level_time + 17
            pk = self.want_pickup(st)
            if pk is not None:
                self.sub.append(pk)
                self.say('detour for %s at (%s, %s)' % (pk[3], pk[1], pk[2]))
                self.path = None
                self.goal = None
        while self.sub:
            top = self.sub[-1]
            if not top[-1].startswith('#'):
                self.sub_seq += 1
                top.append('#%d' % self.sub_seq)       # a unique tag to key its start time
            started = self.sub_started.setdefault(top[-1], st.level_time)
            if top[0] in ('use', 'cross') and st.level_time - started > 420:
                la = getattr(self, 'lift_act', None)
                if la:
                    self.lift_fail[la] = st.level_time + 1200
                    self.lift_act = None
                self.say('sub-objective timed out: %s' % ' '.join(top))
                self.sub.pop()
                self.path = None
                self.goal = None
                self.mode = None
                continue
            r = self.objective(st, top)
            if r == 'done' and top[0] in ('use', 'cross'):
                self.fired.add(int(top[1]))
            if r == 'done':
                self.say('done (sub): %s' % ' '.join(map(str, self.sub[-1])))
                self.sub.pop()
                self.path = None
                self.goal = None
                continue
            break
        else:
            r = None
        while r is None and self.si < len(self.steps):
            r = self.objective(st, self.steps[self.si])
            if r == 'done' and self.steps[self.si][0] in ('use', 'cross'):
                self.fired.add(int(self.steps[self.si][1]))
            if r == 'done':
                self.say('done: %s' % ' '.join(self.steps[self.si]))
                self.si += 1
                self.path = None
                self.goal = None
                self.door = None
                continue
            break
        if r is not None and r != 'done':
            move_to, face, extra = r
            keys += extra
        elif not self.steps:
            return []
        engaged = aim is not None and aim[3]
        # Standing in a damaging sector while not travelling through it (holding,
        # fighting, backing off, stuck): get out to the nearest safe cell first.
        in_dmg = st.sector >= 0 and self.m.sectors[st.sector]['special'] in navmod.DAMAGE_SPECIALS
        escaping = False
        if in_dmg and (engaged or getattr(self, 'hold', None) or self.retreating or self.stuck_t > 20):
            if st.level_time >= getattr(self, 'safe_at', -1):
                self.safe_pt = self.nav.nearest_safe(st.x, st.y)
                self.safe_at = st.level_time + 35
            if getattr(self, 'safe_pt', None):
                rel = adiff(ang_to(self.safe_pt[0] - st.x, self.safe_pt[1] - st.y), st.angle)
                keys += move_keys(rel) + ['run']
                move_to = None
                escaping = True
        if move_to is not None and not engaged:
            mk, tface = self.steer(st, move_to)
            keys += mk
            if face is None:
                face = tface
        if aim is not None:
            face = aim[0]
            if aim[1]:
                keys.append('fire')
            if aim[2]:
                keys.append(aim[2])
            if engaged and not escaping:
                rk = self.retreat_keys(st)
                dk = self.dodge(st)
                if rk:
                    keys += rk
                elif dk:
                    keys.append(dk)
                elif getattr(self, 'barrel_side', None) is not None:
                    keys += move_keys(adiff(self.barrel_side, st.angle))
                elif st.health <= 35 and aim[5] < 160:
                    keys.append('back')          # too close and hurt: give ground
        else:
            self.dodge(st)
        if face is not None:
            dlt = adiff(face, st.angle)
            if dlt >= TURN_RUN:
                keys += ['tl']
            elif dlt <= -TURN_RUN:
                keys += ['tr']
            elif dlt >= 4:
                keys += ['tl']
                if 'run' in keys:
                    keys.remove('run')
            elif dlt <= -4:
                keys += ['tr']
                if 'run' in keys:
                    keys.remove('run')
        return keys

    # ---------------------------------------------------------------- objectives
    def objective(self, st, step):
        """-> 'done' or (move_to_point|None, face_angle|None, extra_keys)."""
        op = step[0]
        m = self.m
        if op == 'goto':
            gx, gy = float(step[1]), float(step[2])
            tol = float(step[3]) if len(step) > 3 else 20.0
            if math.hypot(st.x - gx, st.y - gy) <= tol:
                return 'done'
            return ((gx, gy), None, [])
        if op in ('use', 'exit'):
            li = int(step[1])
            if self.mode == ('used', li):
                if st.level_time - self.used_tick > 3:
                    self.mode = None
                    return 'done'
                return (None, None, [])
            key = ('use', self.si, len(self.sub), tuple(step))
            if self.obj_cache.get('k') != key:
                # Used from the front only (the engine ignores a press from behind),
                # from a spot whose use ray reaches THIS line before any other
                # special line (the engine takes the nearest one it crosses).
                tgt = None
                for (sx_, sy_), (ax_, ay_) in stand_points(m, li, st.x, st.y):
                    k_ = self.nav.cell_of(sx_, sy_)
                    if k_ < 0 or k_ in self.nav.blocked:
                        continue
                    if not self.nav.ok(k_, self.d.floor[self.nav.sec[k_]]):
                        continue
                    if use_ray_hit(m, self.d.floor, self.d.ceil, sx_, sy_, ang_to(ax_ - sx_, ay_ - sy_)) == li:
                        tgt = ((sx_, sy_), (ax_, ay_))
                        break
                if tgt is None:
                    tgt = front_point(m, li)
                    self.say('use %d: no clean stand point, trying the front centre' % li)
                self.obj_cache = {'k': key, 't': tgt}
            (ux, uy), (qx, qy) = self.obj_cache['t']
            d = math.hypot(st.x - ux, st.y - uy)
            want = ang_to(qx - st.x, qy - st.y)
            near_ok = math.hypot(st.x - qx, st.y - qy) < USE_RANGE - 12 and self.path_done()
            if (d <= 24 or near_ok) and in_front(m, li, st.x, st.y):
                if abs(adiff(want, st.angle)) <= 6 and use_ray_hit(m, self.d.floor, self.d.ceil, st.x, st.y, st.angle) == li:
                    self.mode = ('used', li)
                    self.used_tick = st.level_time
                    self.say('use line %d' % li)
                    return (None, want, ['use'])
                return (None, want, [])
            return ((ux, uy), None, [])
        if op == 'cross':
            # Walk over linedef li: to a point just in front of it on the side the
            # player can reach first, then to the matching point on the far side.
            # (A step named 'cross <li> front|back' only fixes the far side.)
            li = int(step[1])
            key = ('cross', self.si, len(self.sub), tuple(step))
            if self.obj_cache.get('k') != key:
                pts = {}
                for side in ('front', 'back'):
                    want_sec = m.lines[li]['front'] if side == 'front' else m.lines[li]['back']
                    pts[side] = self.cross_point(m, li, side, want_sec)
                far = step[2] if len(step) > 2 and not step[2].startswith('#') else None
                if far is None and m.lines[li]['special'] in (39, 97):
                    far = 'back'          # a teleporter fires only when crossed from its front
                if far is None:
                    self.nav.set_obstacles(self.obstacles(st))
                    self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys)
                    sf = self.d.floor[st.sector] if st.sector >= 0 else None
                    lens = {}
                    for side, (px_, py_) in pts.items():
                        p_ = self.nav.path_to_point(st.x, st.y, px_, py_, tol=12.0, start_floor=sf)
                        lens[side] = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(p_, p_[1:])) if p_ else 1e9
                    near = 'front' if lens['front'] <= lens['back'] else 'back'
                    far = 'back' if near == 'front' else 'front'
                near = 'back' if far == 'front' else 'front'
                self.obj_cache = {'k': key, 'pts': [pts[near], pts[far]], 'phase': 0}
            c = self.obj_cache
            gx, gy = c['pts'][c['phase']]
            if math.hypot(st.x - gx, st.y - gy) <= 12:
                if c['phase'] == 1:
                    return 'done'
                c['phase'] = 1
                self.path = None
                self.goal = None
                gx, gy = c['pts'][1]
            return ((gx, gy), None, [])
        if op == 'key':
            bit = wadmap.KEY_BITS[step[1]]
            if st.keys & bit:
                return 'done'
            t = [t for t in m.things if t['type'] in wadmap.KEY_TYPES and wadmap.KEY_TYPES[t['type']] == step[1]][0]
            return ((t['x'], t['y']), None, [])
        if op == 'pickup':
            gx, gy = float(step[1]), float(step[2])
            if math.hypot(st.x - gx, st.y - gy) <= 12:
                return 'done'
            if len(step) > 4:   # auto pickup: give up when it is gone, or after a while
                idx = int(step[4])
                if not any(t.idx == idx for t in st.things):
                    return 'done'
                if self.goal == (gx, gy) and self.path is None:
                    self.skip_items.add(idx)
                    return 'done'
                if st.level_time - int(step[5]) > int(step[6]):
                    self.skip_items.add(idx)
                    self.say('detour timed out')
                    return 'done'
            return ((gx, gy), None, [])
        if op == 'wait':
            if self.wait_until is None:
                self.wait_until = st.level_time + int(step[1])
            if st.level_time >= self.wait_until:
                self.wait_until = None
                return 'done'
            return (None, None, [])
        if op == 'until':   # until S floor|ceil <=|>= H
            s, what, cmp_, h = int(step[1]), step[2], step[3], int(step[4])
            v = self.d.floor[s] if what == 'floor' else self.d.ceil[s]
            if (cmp_ == '<=' and v <= h) or (cmp_ == '>=' and v >= h):
                return 'done'
            return (None, None, [])
        if op == 'killall':
            # hunt every live monster of DoomEd type step[1] (E1M8's barons: their
            # deaths lower the tag-666 floor); the combat code does the shooting
            typ = int(step[1])
            live = [t for t in st.things if t.cat == CAT_MONSTER and t.type == typ]
            if not live:
                return 'done'
            t = min(live, key=lambda t: math.hypot(t.x - st.x, t.y - st.y))
            if t.los == 1 and math.hypot(t.x - st.x, t.y - st.y) < 700:
                return (None, ang_to(t.x - st.x, t.y - st.y), [])   # hold and let combat work
            return ((t.x, t.y), None, [])
        if op == 'endsector':
            # walk into a special-11 sector and stay: it hurts until health drops
            # below 11%, then ends the episode (the finale shows)
            key = ('end', self.si)
            if self.obj_cache.get('k') != key:
                tgt = None
                for i, sc in enumerate(m.sectors):
                    if sc['special'] != 11:
                        continue
                    xs = [p_ for li in m.sector_lines[i] for p_ in (m.line_xy(li)[0], m.line_xy(li)[2])]
                    ys = [p_ for li in m.sector_lines[i] for p_ in (m.line_xy(li)[1], m.line_xy(li)[3])]
                    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
                    if m.point_sector(cx, cy) == i:
                        tgt = (cx, cy)
                        break
                self.obj_cache = {'k': key, 't': tgt}
            tgt = self.obj_cache['t']
            if tgt is None:
                raise ValueError('no special-11 sector on this map')
            if m.sectors[st.sector]['special'] == 11 if st.sector >= 0 else False:
                return (None, None, [])
            return (tgt, None, [])
        if op == 'face':
            want = int(step[1])
            if abs(adiff(want, st.angle)) <= 4:
                return 'done'
            return (None, want, [])
        raise ValueError('bad route step %r' % (step,))

    def cross_point(self, m, li, side, want_sec):
        """A point just off linedef li on `side`, inside the sector that is
        really there (a thin sector can put a point 40 units out into a third)."""
        x1_, y1_, x2_, y2_ = m.line_xy(li)
        L_ = math.hypot(x2_ - x1_, y2_ - y1_) or 1.0
        nx_, ny_ = (y2_ - y1_) / L_, -(x2_ - x1_) / L_
        sg = -1.0 if side == 'back' else 1.0
        for dd in (20.0, 14.0, 28.0, 10.0, 36.0):
            for tt in (0.5, 0.35, 0.65, 0.2, 0.8):
                px_ = x1_ + (x2_ - x1_) * tt + nx_ * dd * sg
                py_ = y1_ + (y2_ - y1_) * tt + ny_ * dd * sg
                if m.point_sector(px_, py_) == want_sec:
                    return (px_, py_)
        return (x1_ + (x2_ - x1_) * 0.5 + nx_ * 20 * sg, y1_ + (y2_ - y1_) * 0.5 + ny_ * 20 * sg)

    def trigger_search(self, st, gx, gy):
        """No path to (gx, gy): ask the reachability model, from where the player
        stands and the heights as they are NOW, which triggers would open the
        way, and push them as sub-objectives (first trigger runs first). This is
        autoroute's minimal-trigger search, run live — it gets the player out of
        rooms a door closed behind (E1M4's blue-key pillar)."""
        key = (round(gx), round(gy))
        if st.level_time - self.trig_tried.get(key, -10000) < 700 or self.sub:
            return
        self.trig_tried[key] = st.level_time
        if not hasattr(self, 'rmaps'):
            self.rmaps = {}
        if self.m.name not in self.rmaps:
            data, lumps = self.wad
            self.rmaps[self.m.name] = R.Map(data, lumps, self.m.name)
        M = self.rmaps[self.m.name]
        goal = self.m.point_sector(gx, gy)
        n = len(M.SEC)
        flo = list(self.d.floor[:n]); clo = list(self.d.ceil[:n])
        init = (flo, list(flo), clo, list(clo), [s_['ftex'] for s_ in M.SEC])
        keys0 = [c for c, b in (('b', 1), ('y', 2), ('r', 4)) if st.keys & b]
        start = st.sector

        def ok(disabled):
            r = R.run(M, R.ENGINE, start=start, init=init, disabled_lines=disabled, keys0=keys0)
            return goal in r['reach'], r
        good, full = ok(set(self.fired))
        if not good:
            self.say('trigger search: goal sector %d not reachable from sector %d even with triggers' % (goal, start))
            return
        fired = [i for kind, i in full['order'] if kind == 'line']
        disabled = set(self.fired)
        for i in reversed(fired):
            if ok(disabled | {i})[0]:
                disabled.add(i)
        need = [i for i in fired if i not in disabled]
        subs = []
        for i in need:
            sp = M.L[i]['special']
            if sp in R.DOOR_MANUAL or sp in R.LIFT:
                continue             # the bot opens doors and calls lifts on its way
            if sp in R.GUN_KINDS:
                self.say('trigger search: needs gun trigger %d (not supported)' % i)
                continue
            subs.append(['use' if sp in R.USE_KINDS else 'cross', str(i)])
        if not subs:
            return
        self.say('trigger search: %s' % ', '.join(' '.join(x) for x in subs))
        for sb in reversed(subs):
            self.sub.append(sb)
        self.path = None
        self.goal = None
        self.hold = None

    def path_done(self):
        return self.path is not None and len(self.path) <= 1

    # ---------------------------------------------------------------- steering
    def obstacles(self, st):
        # barrels (2035): the engine's only solid decoration (things.cyr)
        return [(t.x, t.y, 10.0) for t in st.things if t.type == 2035]

    def plan(self, st, gx, gy):
        self.nav.set_obstacles(self.obstacles(st))
        self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys)
        sf = self.d.floor[st.sector] if st.sector >= 0 else None
        dw = 4 if st.health < 50 else 1          # hurt: nukage costs far more
        p = self.nav.path_to_point(st.x, st.y, gx, gy, tol=10.0, start_floor=sf, dmg_weight=dw)
        if p is None:
            # target may sit inside a wall's standoff band: accept anywhere near
            p = self.nav.path_to_point(st.x, st.y, gx, gy, tol=28.0, start_floor=sf, dmg_weight=dw)
        self.path = p if p else None
        self.goal = (gx, gy)
        self.hold = None
        self.best = 1e18
        self.stuck_t = 0
        if p is None:
            self.say('NO PATH to (%d, %d)' % (gx, gy))
            self.no_path += 1
            self.trigger_search(st, gx, gy)
        return p

    def steer(self, st, target):
        gx, gy = target
        if self.goal != (gx, gy) or self.path is None:
            if self.plan(st, gx, gy) is None:
                # no route: hold position rather than walk blind (that walks off
                # ledges); the stuck timer retries the plan with a back-off
                self.path = [(st.x, st.y)]
                self.hold = (gx, gy)
        # advance along waypoints
        while len(self.path) > 1 and math.hypot(st.x - self.path[0][0], st.y - self.path[0][1]) < 16:
            self.path.pop(0)
            self.best = 1e18
        if getattr(self, 'hold', None):
            wx, wy = self.path[0]            # no route: stay put, and look again now and then
            # (a door or bridge a switch just started may not be open yet)
            if st.level_time >= getattr(self, 'hold_retry', 0):
                self.hold_retry = st.level_time + min(35 * (1 + self.no_path // 3), 350)
                if self.plan(st, gx, gy) is not None:
                    wx, wy = self.path[0] if len(self.path) > 1 else (gx, gy)
                else:
                    self.path = [(st.x, st.y)]
                    self.hold = (gx, gy)
        else:
            wx, wy = self.path[0] if len(self.path) > 1 else (gx, gy)
        # lifts and doors on the way
        lk = self.lift_check(st, wx, wy)
        if lk is not None:
            return lk
        dk = self.door_check(st, wx, wy)
        if dk is not None:
            return dk
        dist = math.hypot(wx - st.x, wy - st.y)
        if dist < self.best - 2:
            self.best = dist
            self.stuck_t = 0
        elif self.last_moving:
            self.stuck_t += 1
        if self.stuck_t > 45:
            self.say('stuck near (%d, %d) -> replan' % (st.x, st.y))
            if self.plan(st, gx, gy) is None:
                self.path = [(st.x, st.y)]
                self.hold = (gx, gy)
                self.stuck_t = -200 * min(self.no_path, 5)   # failing searches are costly: back off
            self.jiggle = 12
        want = ang_to(wx - st.x, wy - st.y)
        rel = adiff(want, st.angle)
        # Face first, then go: run only when lined up, walk when nearly, and turn
        # on the spot when well off (the turn rate is only 8 units a tick, and
        # walking while turning drifts off the planned line, e.g. over a ledge).
        if abs(rel) <= 20:
            keys = ['fwd', 'run'] if dist >= 24 else ['fwd']
        elif abs(rel) <= 64:
            keys = ['fwd']
        else:
            keys = []
        if getattr(self, 'jiggle', 0) > 0:
            self.jiggle -= 1
            keys = ['back', 'sl' if (st.level_time // 6) % 2 else 'sr']
        if dist < 8:
            keys = []
        self.last_moving = bool(keys)
        return keys, want

    def track_lifts(self, st):
        for L in self.nav.lifts:
            f = self.d.floor[L]
            old = self.lift_seen.get(L)
            if old is None or old[0] != f:
                self.lift_seen[L] = (f, st.level_time)
                if self.lift_pending and self.lift_pending[0] == L:
                    self.lift_pending = None          # it moved: the call worked
        # a lift call's sub-objective just finished: start watching for movement
        la = getattr(self, 'lift_act', None)
        if la and not self.sub:
            self.lift_pending = (la[0], la[1], st.level_time, self.d.floor[la[0]])
            self.lift_act = None

    def lift_check(self, st, wx, wy):
        """If the next leg is blocked only by a lift's current height: wait for it,
        or go and call it (a sub-objective: its switch, or walking over its line)."""
        nv, m = self.nav, self.m
        L_ = math.hypot(wx - st.x, wy - st.y) or 1.0
        reach = min(L_, 48.0)
        k = nv.cell_of(st.x, st.y)
        n = int(reach / 6) + 1
        cf = self.d.floor[st.sector] if st.sector >= 0 else None   # the real floor, not the cell's
        for i in range(1, n + 1):
            px = st.x + (wx - st.x) / L_ * reach * i / n
            py = st.y + (wy - st.y) / L_ * reach * i / n
            q = nv.cell_of(px, py)
            if q == k or q < 0:
                continue
            if nv.ok_live(q, k, self.d.floor, self.d.ceil, cfloor=cf):
                k = q
                cf = None
                continue
            lift = nv.lift_of(q, k)
            if lift is None:
                return None
            if st.sector != lift and nv.sec[k] == lift:
                # the leg boards the lift first and only later needs it at the
                # other level: board now, and wait ON it (it carries us there)
                return None
            lo, hi, acts = nv.lifts[lift]
            want = None
            for lvl in (lo, hi):
                cf2 = cf
                if cf2 is not None and st.sector == lift:
                    cf2 = lvl
                if nv.ok_live(q, k, self.d.floor, self.d.ceil, {lift: lvl}, cfloor=cf2):
                    want = lvl
                    break
            if want is None:
                return None
            f, since = self.lift_seen.get(lift, (self.d.floor[lift], st.level_time))
            still = st.level_time - since
            face = ang_to(wx - st.x, wy - st.y)
            if f == want:
                return None
            if still <= 3:
                return ([], face)                 # moving: wait
            if want == hi and f == lo and still < 160:
                return ([], face)                 # down and waiting: it comes back up
            if self.lift_pending and self.lift_pending[0] == lift and not self.sub:
                L0, li0, t0, f0 = self.lift_pending
                if st.level_time - t0 > 45:
                    self.lift_fail[(lift, li0)] = st.level_time + 1200
                    self.say('lift %d did not answer line %d: try another way' % (lift, li0))
                    self.lift_pending = None
                    self.lift_called.pop(lift, None)
            if st.level_time - self.lift_called.get(lift, -999) < 70:
                return ([], face)                 # just called: give it time to start
            # parked at the wrong level: call it
            act = self.pick_lift_activation(st, lift, acts)
            if act is None:
                self.say('lift %d: no way to call it' % lift)
                return None
            self.sub.append(act)
            self.lift_called[lift] = st.level_time + 40   # the walk to the switch takes a while too
            self.lift_pending = None
            self.lift_act = (lift, int(act[1]))
            self.say('call lift %d (%s %s), want floor %d, now %d [cell sec %d -> %d, me (%d,%d) -> leg (%d,%d)]' % (
                lift, act[0], act[1], want, f, nv.sec[k], nv.sec[q], st.x, st.y, wx, wy))
            self.path = None
            self.goal = None
            return ([], face)
        return None

    def pick_lift_activation(self, st, lift, acts):
        best = None
        nv, m = self.nav, self.m
        nv.set_obstacles(self.obstacles(st))
        nv.plan_heights(self.d.floor, self.d.ceil, st.keys)
        for li in acts:
            if self.lift_fail.get((lift, li), -1) > st.level_time:
                continue
            sp = m.lines[li]['special']
            if sp in navmod.LIFT_SWITCH:
                (ux, uy), _ = use_point(m, li, st.x, st.y)
                p = nv.path_to_point(st.x, st.y, ux, uy, tol=20.0)
                cand = ('use', li)
            else:
                (fx, fy), _ = front_point(m, li, 40.0)
                (bx, by), _ = front_point(m, li, -40.0)
                near_f = math.hypot(st.x - fx, st.y - fy) < math.hypot(st.x - bx, st.y - by)
                ux, uy = (fx, fy) if near_f else (bx, by)
                p = nv.path_to_point(st.x, st.y, ux, uy, tol=20.0)
                cand = ('cross', li, 'back' if near_f else 'front')
            if p is None:
                continue
            length = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(p, p[1:]))
            if best is None or length < best[0]:
                best = (length, cand)
        return [str(x) for x in best[1]] if best else None

    def door_check(self, st, wx, wy):
        """If the next leg crosses a closed manual door, open it."""
        m = self.m
        if self.door is not None:
            li, s, t0 = self.door
            if self.d.ceil[s] - self.d.floor[s] >= 60 or st.level_time - t0 > 140:
                self.door = None
                self.best = 1e18
                self.stuck_t = 0
                return None
            return ([], None)   # wait for it
        L = math.hypot(wx - st.x, wy - st.y) or 1.0
        reach = min(L, 96.0)
        ex, ey = st.x + (wx - st.x) / L * reach, st.y + (wy - st.y) / L * reach
        for s, lines in getattr(self.nav, 'door_sectors', {}).items():
            if self.d.ceil[s] - self.d.floor[s] >= 56:
                continue
            for li in lines:
                if not in_front(m, li, st.x, st.y):
                    continue          # the far face of the door; the near one faces us
                x1, y1, x2, y2 = m.line_xy(li)
                if navmod.segs_cross(st.x, st.y, ex, ey, x1, y1, x2, y2):
                    (ux, uy), (qx, qy) = use_point(m, li, st.x, st.y, 36.0)
                    want = ang_to(qx - st.x, qy - st.y)
                    dq = math.hypot(st.x - qx, st.y - qy)
                    if dq < USE_RANGE - 8 and abs(adiff(want, st.angle)) <= 8:
                        self.door = (li, s, st.level_time)
                        self.say('open door line %d (sector %d)' % (li, s))
                        return (['use'], want)
                    if dq < USE_RANGE - 8:
                        return ([], want)
                    rel = adiff(ang_to(ux - st.x, uy - st.y), st.angle)
                    return (move_keys(rel), want)
        return None

    def shots(self, st):
        """Shots left across the weapons held (a shell is worth more than a bullet)."""
        has = lambda w: (st.weapons >> w) & 1
        n = st.bullets
        if has(3):
            n += 2 * st.shells
        if has(5):
            n += 3 * st.rockets
        return n

    def want_pickup(self, st):
        """A nearby item worth a detour, as a 'pickup' sub-objective, or None."""
        has = lambda w: (st.weapons >> w) & 1
        shots = self.shots(st)
        ammo_limit = 3000 if shots == 0 else 1500 if shots < 15 else 0
        # no wandering off while something awake is close: finish the fight first
        if shots > 0 and any(t.cat == CAT_MONSTER and t.state in AWAKE and
                             math.hypot(t.x - st.x, t.y - st.y) < 600 for t in st.things):
            return None
        best = None
        for t in st.things:
            if t.cat not in (CAT_ITEM, CAT_WEAPON) or t.idx in self.skip_items:
                continue
            d = math.hypot(t.x - st.x, t.y - st.y)
            what, limit = None, 0
            if t.type in wadmap.WEAPONS and not has(wadmap.WEAPONS[t.type]):
                what, limit = 'weapon', 900
            elif t.type in (2011, 2012) and st.health < 80:
                what, limit = 'health', 800 if st.health < 40 else 450 if st.health < 60 else 250
            elif t.type == 2014 and st.health < 60:
                what, limit = 'health', 300
            elif t.type == 2013:
                what, limit = 'soulsphere', 700
            elif t.type in (2018, 2019) and st.armor < 60:
                what, limit = 'armor', 500
            elif t.type == 8:
                what, limit = 'backpack', 700
            elif t.type in (2008, 2049) and has(3) and st.shells < 50:
                what, limit = 'shells', ammo_limit or 450
            elif t.type in (2007, 2048) and st.bullets < 120:
                what, limit = 'bullets', ammo_limit or 400
            elif t.type in (2010, 2046) and has(5) and st.rockets < 20:
                what, limit = 'rockets', ammo_limit or 400
            elif t.type == 2001 and has(3) and st.shells < 50:
                what, limit = 'shells', ammo_limit or 450     # an owned shotgun still carries shells
            elif t.type == 2002 and has(4) and st.bullets < 120:
                what, limit = 'bullets', ammo_limit or 400
            elif t.type in (2008, 2049) and ammo_limit:   # shells without the shotgun yet: still worth it when dry
                what, limit = 'shells', ammo_limit // 2
            if what is None or d > limit:
                continue
            score = d - (400 if what in ('weapon', 'soulsphere', 'backpack') else 0) - (600 if ammo_limit and what in ('shells', 'bullets', 'rockets') else 0)
            if best is None or score < best[0]:
                best = (score, t, what)
        if best is None:
            return None
        _, t, what = best
        # reachable at a sane cost? (the planner, not the crow)
        self.nav.set_obstacles(self.obstacles(st))
        self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys)
        p = self.nav.path_to_point(st.x, st.y, t.x, t.y, tol=10.0, max_nodes=60000)
        if p is None:
            self.skip_items.add(t.idx)
            return None
        length = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(p, p[1:]))
        if length > 1.6 * math.hypot(t.x - st.x, t.y - st.y) + 200:
            self.skip_items.add(t.idx)
            return None
        # never detour somewhere it cannot come back from (a drop-off is one-way)
        back = self.nav.path_to_point(t.x, t.y, st.x, st.y, tol=24.0, max_nodes=60000)
        if back is None:
            self.skip_items.add(t.idx)
            return None
        # budget: the walk at 3 units a tick, plus time for a lift or a door
        budget = int(length / 3) + 400
        return ['pickup', '%.1f' % t.x, '%.1f' % t.y, what, str(t.idx), str(st.level_time), str(budget)]

    # ---------------------------------------------------------------- combat
    def combat(self, st):
        """-> (face_angle, fire?, weapon_key|None, engaged?) or None. `engaged`
        means hold position: an awake monster can see the player and is close
        enough to matter, so clear it before walking on."""
        best = None
        # Sticky target: line of sight flickers at grazing angles, and swapping
        # targets every tick means turning back and forth and never firing.
        if self.tgt is not None:
            cur = next((t for t in st.things if t.idx == self.tgt[0] and t.cat == CAT_MONSTER), None)
            if cur is not None:
                if cur.los == 1:
                    self.tgt_seen = st.level_time
                if st.level_time - getattr(self, 'tgt_seen', -99) <= 25:
                    d = math.hypot(cur.x - st.x, cur.y - st.y)
                    best = (0, cur, d, cur.state in AWAKE)
        for t in (st.things if best is None else ()):
            if t.cat != CAT_MONSTER or t.los != 1:
                continue
            if self.ignore.get(t.idx, -1) > st.level_time:
                continue
            d = math.hypot(t.x - st.x, t.y - st.y)
            awake = t.state in AWAKE
            shots = self.shots(st)
            # ammo is finite: leave sleeping monsters alone unless close, and do
            # not trade shots at long range
            if not awake and d > 250:
                continue      # every shot wakes the room: let sleepers lie
            if d > 900 or (shots == 0 and d > 160):
                continue
            score = d - (300 if awake else 0)
            if best is None or score < best[0]:
                best = (score, t, d, awake)
        if best is None:
            self.tgt = None
            return None
        _, t, d, awake = best
        # a target that does not lose health in 10 s is out of reach: skip it
        if self.tgt is None or self.tgt[0] != t.idx:
            self.tgt = (t.idx, st.level_time, t.health)
            self.tgt_seen = st.level_time
            self.say('engage %s #%d at %d (%s, hp %d)' % (wadmap.MONSTERS.get(t.type, t.type), t.idx, d,
                                                       'awake' if awake else 'idle', t.health))
        elif t.health < self.tgt[2]:
            self.tgt = (t.idx, st.level_time, t.health)
        elif st.level_time - self.tgt[1] > 350:
            self.ignore[t.idx] = st.level_time + 700
            self.say('give up on #%d (no damage in 10 s)' % t.idx)
            self.tgt = None
            return None
        want = ang_to(t.x - st.x, t.y - st.y)
        err = abs(adiff(want, st.angle))
        tol = max(2, int(math.atan2(18.0, max(d, 1.0)) * (A / 2) / math.pi))
        wkey = self.pick_weapon(st, t, d)
        fire = err <= tol
        # never shoot a barrel we are standing next to (shotgun spread, a miss)
        self.barrel_side = None
        for b in st.things:
            if b.type != 2035:
                continue
            db = math.hypot(b.x - st.x, b.y - st.y)
            # only a barrel BEFORE the target can take the shot (bullets stop at
            # the first thing they hit), and only one inside blast range of us
            # (128) matters: a farther one going off is good news
            if db > 130 or db > d - 12:
                continue
            cone = math.atan2(24.0, max(db, 1.0)) * (A / 2) / math.pi + 10
            off = adiff(ang_to(b.x - st.x, b.y - st.y), want)
            if abs(off) <= cone:
                fire = False
                # back straight away from it (a sidestep is often into a wall):
                # once it is out of blast range it may be shot
                self.barrel_side = ang_to(st.x - b.x, st.y - b.y)
        engaged = awake and d < 1100
        return (want, fire, wkey, engaged, t, d)

    def retreat_keys(self, st):
        """Hurt in a fight (under 45 health, or 30 lost in the last 2 s): back
        off toward where the bot stood a few seconds ago (cleared ground) while
        it keeps aiming. Breaking line of sight with a group is what lets it
        take them one at a time."""
        hist = self.hp_hist
        lost = max((h for t_, h in hist if st.level_time - t_ <= 70), default=st.health) - st.health
        if st.health >= 45 and lost < 30:
            return None
        tr = self.trace
        pt = None
        for i in range(len(tr) - 30, max(len(tr) - 700, 0), -6):
            x, y = tr[i]
            if math.hypot(x - st.x, y - st.y) >= 96:
                pt = (x, y)
                break
        if pt is None:
            return None
        rel = adiff(ang_to(pt[0] - st.x, pt[1] - st.y), st.angle)
        if not getattr(self, 'retreating', False):
            self.say('retreat toward (%d, %d) (hp %d, lost %d)' % (pt[0], pt[1], st.health, lost))
            self.retreating = True
        return move_keys(rel) + ['run']

    def dodge(self, st):
        """Strafe across an incoming projectile's track: -> 'sl' / 'sr' / None."""
        threat = None
        seen = {}
        for t in st.things:
            if t.cat != CAT_PROJECTILE:
                continue
            seen[t.idx] = (t.x, t.y)
            prev = self.proj_prev.get(t.idx)
            if prev is None:
                continue
            vx, vy = t.x - prev[0], t.y - prev[1]
            sp = math.hypot(vx, vy)
            if sp < 1:
                continue
            rx, ry = st.x - t.x, st.y - t.y
            along = (rx * vx + ry * vy) / sp
            if along <= 0 or along > 260:
                continue
            miss = abs(rx * vy - ry * vx) / sp
            if miss < 40 and (threat is None or along < threat[0]):
                threat = (along, vx, vy)
        self.proj_prev = seen
        if threat is None:
            return None
        _, vx, vy = threat
        # strafe to the side the projectile's track is NOT drifting toward
        perp = ang_to(-vy, vx)            # 90 deg left of its travel
        rel = adiff(perp, st.angle)
        return 'sl' if rel > 0 else 'sr'

    def pick_weapon(self, st, t, d):
        has = lambda w: (st.weapons >> w) & 1
        tough = t.type in (3003, 3005, 3002, 58)   # baron, caco, demon, spectre
        choice = None
        if has(5) and st.rockets > 0 and d > 220 and t.type in (3003, 3005):
            choice = 5
        elif has(3) and st.shells > 0 and (d < 500 or tough):
            choice = 3
        elif has(4) and st.bullets > 0:
            choice = 4
        elif has(3) and st.shells > 0:
            choice = 3
        elif st.bullets > 0:
            choice = 2
        elif has(6):
            choice = 6          # chainsaw: no ammo, far better than the fist
        else:
            choice = 1
        if choice != st.weapon:
            return str(choice)
        return None

    # ---------------------------------------------------------------- output
    def dump_png(self):
        if not self.png_dir or self.m is None:
            return
        tr = self.trace

        def extra(cv):
            for a, b in zip(tr, tr[1:]):
                cv.line(a[0], a[1], b[0], b[1], (0, 255, 0))
        os.makedirs(self.png_dir, exist_ok=True)
        wadmap.render_overview(self.m, os.path.join(self.png_dir, self.m.name + '.png'), 0.3, True, extra)
