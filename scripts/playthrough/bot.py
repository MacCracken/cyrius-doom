"""bot.py — the playthrough's player: route objectives, steering, doors, combat.

Each tick it reads the --lockstep State and answers with the keys to hold.
It sees what the record shows (its own position, things, live sector heights)
and acts only through keys; nothing in the engine is changed or skipped.
"""
import math, os

import nav as navmod
import wadmap

# One-shot specials (doors.cyr special_is_once): once fired, gone. Only these
# are passed to the reachability model as spent; a WR/SR line (a lift, a
# repeatable door) can be used again, and treating it as spent once left the
# bot "unable" to leave E1M7's red-key room by the lift it came up on.
ONCE = {2,4,5,7,8,10,18,20,21,22,23,29,31,32,33,34,36,38,39,71,102,103,118,121,122,125}

# Remote door-opening specials: W1/WR/S1/SR/G1 open (and open-wait-close).
DOOR_OPENERS = {2, 4, 29, 46, 61, 63, 86, 90, 103}

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
        self.boom = []
        self.barrels_prev = {}
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
        self.skip_items = {}     # pickup idx -> level_time it may be tried again
        self.next_scan = 0
        self.prev_hp = st.health
        self.prev_kills = st.kills
        # timers below are level_time stamps, and level_time restarts at 0 on every
        # map (and every respawn): carried over, they freeze the bot (a 9,000-tic
        # hold_retry from E1M3 stalled E1M4)
        self.hold = None
        self.hold_retry = 0
        self.safe_at = -1
        self.safe_pt = None
        self.safe_path = None
        self.learned_blocks = []  # spots the engine stopped the player at, this life
        self.leg_damage = 0
        self.wd = None
        self.escape_off = -1
        self.escape_pos = None
        self.retreat_pt = None
        self.jiggle = 0
        self.tgt_seen = -99
        self.lift_act = None
        self.recent = []         # (tag, tick) of door-opening triggers just fired
        self.fired = set()       # trigger lines this bot has walked over / used on this map
        self.trig_tried = {}     # goal -> tick of the last runtime trigger search
        self.ambush = self.find_ambush_lines(st)
        self.nav.set_avoid_lines(self.ambush)
        if self.ambush:
            self.say('avoiding closet triggers %s' % sorted(self.ambush))
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
        # A shot barrel leaves the record (health 0) and explodes a few tics later.
        bar = {t.idx: (t.x, t.y) for t in st.things if t.type == 2035}
        for idx, pos in getattr(self, 'barrels_prev', {}).items():
            if idx not in bar:
                self.boom.append((pos[0], pos[1], st.level_time))
                self.say('barrel #%d going off at (%d, %d)' % (idx, pos[0], pos[1]))
        self.barrels_prev = bar
        self.boom = [b_ for b_ in self.boom if st.level_time - b_[2] <= 45]
        if len(self.hp_hist) > 140:
            del self.hp_hist[:40]
        if self.tgt is None:
            self.retreating = False
        self.last_keys = self.play(st)
        self.watchdog(st)
        return self.last_keys

    def watchdog(self, st):
        """Net progress, whatever the mode: a bot that moves less than 32 units in
        175 tics while it is not fighting or deliberately waiting (a lift, a door,
        no route) is stuck in a way the per-leg check misses — the damage escape
        and the steer can take turns resetting it (E1M4's pit, E1M6's nukage).
        Two such windows in a row: back off along the trace and block the spot."""
        fighting = self.tgt is not None
        waiting = self.door is not None or getattr(self, 'hold', None) is not None or \
            getattr(self, 'why', '') == 'lift' or self.mode == 'dead' or getattr(self, 'standing', False)
        w = getattr(self, 'wd', None)
        if w is None or fighting or waiting:
            self.wd = (st.level_time, st.x, st.y, 0)
            return
        t0, x0, y0, n = w
        if st.level_time - t0 < 175:
            return
        if math.hypot(st.x - x0, st.y - y0) >= 32:
            self.wd = (st.level_time, st.x, st.y, 0)
            return
        n += 1
        self.wd = (st.level_time, st.x, st.y, n)
        if n < 2 or any(sb[0] == 'goto' for sb in self.sub):
            return
        back = None
        for i_ in range(len(self.trace) - 1, max(len(self.trace) - 1500, 0), -4):
            x_, y_ = self.trace[i_]
            if math.hypot(x_ - st.x, y_ - st.y) >= 96:
                back = (x_, y_)
                break
        wx, wy = self.path[0] if self.path else (st.x, st.y)
        L_ = math.hypot(wx - st.x, wy - st.y)
        if L_ > 1:
            bx_, by_ = st.x + (wx - st.x) / L_ * 14, st.y + (wy - st.y) / L_ * 14
            self.learned_blocks = getattr(self, 'learned_blocks', []) + [(bx_, by_, 6.0, st.level_time + 700)]
        self.say('no progress for %d tics at (%d, %d); backing off to %s' % (175 * n, st.x, st.y, back))
        self.wd = (st.level_time, st.x, st.y, 0)
        if back is not None:
            self.sub.append(['goto', '%.1f' % back[0], '%.1f' % back[1], '16'])
        self.path = None
        self.goal = None

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
            self.say('status hp=%d ar=%d w=%d ammo=%d/%d/%d kills=%d/%d visible=%d at (%d,%d) step=%d sub=%s '
                     'keys=%s door=%s hold=%s ret=%s why=%s dbg=%s' % (
                st.health, st.armor, st.weapon, st.bullets, st.shells, st.rockets, st.kills, st.max_kills,
                vis, st.x, st.y, self.si, self.sub, '+'.join(getattr(self, 'last_keys', None) or []) or '-',
                self.door and self.door[0], getattr(self, 'hold', None) is not None, self.retreating,
                getattr(self, 'why', '-'), getattr(self, 'dbg', '-')))
        dry = self.shots(st) == 0
        # The leg ahead costs about what the player has (E1M5's way to the blue
        # key crosses hurting floor; two lives set off on it at 20 and 10):
        # heal first, from anywhere the planner reaches that pays.
        need = getattr(self, 'leg_damage', 0) >= st.health - 15
        if (aim is None or (dry and not aim[3])) and st.level_time >= self.next_scan and not self.sub:
            self.next_scan = st.level_time + 17
            pk = self.want_pickup(st, need_health=need)
            if pk is not None:
                self.sub.append(pk)
                self.say('detour for %s at (%s, %s)' % (pk[3], pk[1], pk[2]))
                self.path = None
                self.goal = None
        # a sub-objective buried under newer ones still runs out of time
        for sb in list(self.sub[:-1]):
            tag_ = sb[-1] if sb[-1].startswith('#') else None
            t0_ = self.sub_started.get(tag_, st.level_time) if tag_ else st.level_time
            expired = st.level_time - t0_ > 1500
            if sb[0] == 'pickup' and len(sb) > 6 and st.level_time - int(sb[5]) > int(sb[6]):
                expired = True
                self.skip_items[int(sb[4])] = st.level_time + 1050
            if expired:
                self.say('dropped stale sub-objective: %s' % ' '.join(sb))
                self.sub.remove(sb)
        while self.sub:
            top = self.sub[-1]
            if not top[-1].startswith('#'):
                self.sub_seq += 1
                top.append('#%d' % self.sub_seq)       # a unique tag to key its start time
            started = self.sub_started.setdefault(top[-1], st.level_time)
            if (top[0] in ('use', 'cross') and st.level_time - started > 420) or \
                    (top[0] == 'goto' and st.level_time - started > 210):
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
                if self.m.lines[int(top[1])]['special'] in ONCE:
                    self.fired.add(int(top[1]))
                self.note_trigger(st, int(top[1]))
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
                if self.m.lines[int(self.steps[self.si][1])]['special'] in ONCE:
                    self.fired.add(int(self.steps[self.si][1]))
                self.note_trigger(st, int(self.steps[self.si][1]))
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
        # the objective itself says stand (E1M8's end room, a wait, a use press)
        self.standing = move_to is None
        engaged = aim is not None and aim[3]
        # Outgunned by a melee monster (pistol only, demon or spectre still out of
        # bite range): do not stand and trade — 15 pistol rounds a demon, and
        # E1M8 lets five in at once. Keep going where the route or the weapon
        # detour leads, shooting on the way; it has to come to the player.
        has_ = lambda w: (st.weapons >> w) & 1
        kite = engaged and not (has_(3) or has_(4) or has_(6)) and aim[4].type in (3002, 58) and aim[5] > 120
        # A barrel about to blow within reach: get clear first (max-axis 160
        # covers its 128 + the player's radius with room to spare).
        for bx, by, _ in self.boom:
            if max(abs(st.x - bx), abs(st.y - by)) < 160:
                rel = adiff(ang_to(st.x - bx, st.y - by), st.angle)
                return move_keys(rel) + ['run']
        # Standing in a damaging sector while not travelling through it (holding,
        # fighting, backing off, stuck): get out to the nearest safe cell first.
        in_dmg = st.sector >= 0 and self.d.special[st.sector] in navmod.DAMAGE_SPECIALS
        escaping = False
        if in_dmg and st.level_time >= getattr(self, 'escape_off', -1) and \
                (engaged or getattr(self, 'hold', None) or self.retreating or self.stuck_t > 20):
            if st.level_time >= getattr(self, 'safe_at', -1):
                # the walk out, along clear cells (not a straight line at the
                # nearest safe floor, which from a pit is the wall above it)
                sp_ = self.nav.nearest_safe(st.x, st.y, path=True)
                self.safe_path = list(sp_[1:]) if sp_ and len(sp_) > 1 else None
                self.safe_at = st.level_time + 35
                # an escape that gets nowhere in 35 tics is abandoned for 3 s,
                # and the route replanned from here (stairs out of the pit)
                last = getattr(self, 'escape_pos', None)
                if last is not None and math.hypot(st.x - last[0], st.y - last[1]) < 8:
                    self.escape_off = st.level_time + 105
                    self.safe_path = None
                    # and it counts as a stall: the steer that follows runs the
                    # stuck handler at once (replan, then learned blocks / back
                    # off) — escape and steer had been resetting each other on
                    # E1M6's nukage while the engine held the player at a corner
                    self.stuck_t = 46
                self.escape_pos = (st.x, st.y)
                if self.safe_path:
                    self.stuck_t = 0      # (with no way out found, the stuck replan stays armed)
            sp_ = getattr(self, 'safe_path', None)
            while sp_ and len(sp_) > 1 and math.hypot(sp_[0][0] - st.x, sp_[0][1] - st.y) < 12:
                sp_.pop(0)
            if sp_:
                rel = adiff(ang_to(sp_[0][0] - st.x, sp_[0][1] - st.y), st.angle)
                keys += move_keys(rel) + ['run']
                move_to = None
                escaping = True
        else:
            self.escape_pos = None
        self.dbg = 'eng=%d kite=%d mv=%s aim=%s' % (
            bool(engaged), bool(kite), move_to and (int(move_to[0]), int(move_to[1])),
            aim and '%s@%d%s' % (aim[4].type, aim[5], '/fire' if aim[1] else ''))
        if move_to is not None and (not engaged or kite):
            mk, tface = self.steer(st, move_to, aiming=aim is not None)
            keys += mk
            if face is None:
                face = tface
        if aim is not None:
            face = aim[0]
            if aim[1]:
                keys.append('fire')
            if aim[2]:
                keys.append(aim[2])
            if engaged and not escaping and not kite:
                rk = self.retreat_keys(st)
                dk = self.dodge(st)
                if rk:
                    keys += rk
                    if dk and 'sl' not in rk and 'sr' not in rk:
                        keys.append(dk)              # back off AND side-step the fireball
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
            # In position only where a press from HERE would reach the line: the
            # ray takes the nearest special line it crosses, and E1M6's walk line
            # 602 lies 40 units in front of switch 599 — 24 units short of the
            # stand point, the bot faced 602 for 60,000 tics.
            reach = use_ray_hit(m, self.d.floor, self.d.ceil, st.x, st.y, want) == li
            if (d <= 24 or near_ok) and in_front(m, li, st.x, st.y) and reach:
                if abs(adiff(want, st.angle)) <= 6 and use_ray_hit(m, self.d.floor, self.d.ceil, st.x, st.y, st.angle) == li:
                    self.mode = ('used', li)
                    self.used_tick = st.level_time
                    self.say('use line %d' % li)
                    return (None, want, ['use'])
                return (None, want, [])
            if d <= 4:
                return ((qx, qy), None, [])      # on the spot and still short: lean in
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
                    self.nav.set_obstacles(self.obstacles(st), self.learned(st))
                    self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys, special=self.d.special)
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
                    self.skip_items[idx] = st.level_time + 1400
                    return 'done'
                if st.level_time - int(step[5]) > int(step[6]):
                    self.skip_items[idx] = st.level_time + 1050
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

    def learned(self, st):
        self.learned_blocks = [b for b in getattr(self, 'learned_blocks', []) if b[3] > st.level_time]
        return [(x, y, r) for x, y, r, _ in self.learned_blocks]

    def monsters(self, st):
        return [(t.x, t.y) for t in st.things if t.cat == CAT_MONSTER]

    def crowd_near_path(self, st, p, r=250.0):
        """Live monsters within r of a path (its waypoints and their midpoints)."""
        pts = list(p) + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(p, p[1:])]
        n = 0
        for t in st.things:
            if t.cat != CAT_MONSTER:
                continue
            if any((t.x - x) ** 2 + (t.y - y) ** 2 < r * r for x, y in pts):
                n += 1
        return n

    def find_ambush_lines(self, st):
        """Walk-over door triggers that open onto a sector holding 3+ monsters
        (a monster closet: E1M5's line 192 lets 8 out) and that the route does
        not name. The planner prices crossing them, so detours go around."""
        m = self.m
        named = set(int(sp[1]) for sp in self.steps if sp[0] in ('use', 'cross', 'exit') and sp[1].isdigit())
        count = {}
        for t in st.things:
            if t.cat == CAT_MONSTER:
                s_ = m.point_sector(t.x, t.y)
                count[s_] = count.get(s_, 0) + 1
        out = set()
        for ln in m.lines:
            if ln['special'] not in (2, 4, 86, 90) or not ln['tag'] or ln['i'] in named:
                continue
            for door in m.tagged(ln['tag']):
                if any(count.get(n, 0) >= 3 for n in m.neighbors[door] | {door}):
                    out.add(ln['i'])
        return out

    def note_trigger(self, st, li):
        ln = self.m.lines[li]
        if ln['special'] in DOOR_OPENERS and ln['tag']:
            self.recent.append((ln['tag'], st.level_time))

    def opening_doors(self, st):
        """Doors a trigger the bot just fired is opening: plan as if open for 200
        tics, so it walks straight in instead of finding no path while they rise
        and wandering off until an open-wait-close door shuts again (E1M4's
        pillar room, tag 1, special 90)."""
        self.recent = [(tg, t0) for tg, t0 in self.recent if st.level_time - t0 <= 200]
        extra = {}
        for tg, _ in self.recent:
            for s_ in self.m.tagged(tg):
                extra[s_] = (None, self.m.lowest_neighbor_ceil(s_) - 4)
        return extra or None

    def plan(self, st, gx, gy):
        self.nav.set_obstacles(self.obstacles(st), self.learned(st))
        self.nav.set_threats(self.monsters(st))
        self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys, special=self.d.special,
                              extra=self.opening_doors(st))
        sf = self.d.floor[st.sector] if st.sector >= 0 else None
        dw = 20 if st.health < 35 else 4 if st.health < 50 else 1   # hurt: nukage costs far more
        item = any(t.cat in (CAT_ITEM, CAT_WEAPON, CAT_KEY) and abs(t.x - gx) < 1 and abs(t.y - gy) < 1
                   for t in st.things)
        if item:
            # an item is touched, not stood on: any cell within the engine's reach.
            # That cell is a waypoint of its own, and the item the last one: the
            # final push goes from there (from the far side of a pillar it would
            # walk into the pillar — an E1M6 run stood in nukage doing that)
            p = self.nav.path_to_touch(st.x, st.y, gx, gy, start_floor=sf, dmg_weight=dw)
            if p:
                p = list(p) + [(gx, gy)]
        else:
            p = self.nav.path_to_point(st.x, st.y, gx, gy, tol=10.0, start_floor=sf, dmg_weight=dw)
            if p is None:
                # target may sit inside a wall's standoff band: accept anywhere near
                p = self.nav.path_to_point(st.x, st.y, gx, gy, tol=28.0, start_floor=sf, dmg_weight=dw)
        self.path = p if p else None
        self.goal = (gx, gy)
        self.leg_damage = self.path_damage(p) if p else 0
        self.hold = None
        self.best = 1e18
        self.stuck_t = 0
        if p is None:
            self.say('NO PATH to (%d, %d)' % (gx, gy))
            self.no_path += 1
            self.trigger_search(st, gx, gy)
        return p

    def steer(self, st, target, aiming=False):
        gx, gy = target
        if self.goal != (gx, gy) or self.path is None:
            if self.plan(st, gx, gy) is None:
                # no route: hold position rather than walk blind (that walks off
                # ledges); the stuck timer retries the plan with a back-off
                self.path = [(st.x, st.y)]
                self.hold = (gx, gy)
        # Next to a barrel the engine's gap can be 12 units (two barrels 64
        # apart): reach each waypoint exactly, face it closely, and walk.
        tight = any(t.type == 2035 and math.hypot(t.x - st.x, t.y - st.y) < 60 for t in st.things)
        # Walking the high side of a drop (nav.ledge: within 22 of an edge more
        # than a step down): a few units of drift and the player is in the pit
        # below (E1M4's walkway over nukage sector 42, two lives). Walk it.
        ledge = self.nav.cell_of(st.x, st.y) in self.nav.ledge
        adv = 7 if tight else 16
        # advance along waypoints: near one, and in its sector (or on it): popped
        # 12 units short, still in E1M4's nukage pit, the next leg ran into the
        # 48-unit wall the stairs go round, and the bot pushed on it until dead
        sec_now = self.m.point_sector(st.x, st.y)
        while len(self.path) > 1 and math.hypot(st.x - self.path[0][0], st.y - self.path[0][1]) < adv and (
                math.hypot(st.x - self.path[0][0], st.y - self.path[0][1]) < 6 or
                self.m.point_sector(*self.path[0]) == sec_now):
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
            self.why = 'lift'
            return lk
        dk = self.door_check(st, wx, wy)
        if dk is not None:
            self.why = 'door'
            return dk
        self.why = 'walk(%d,%d) d=%d' % (wx, wy, math.hypot(wx - st.x, wy - st.y))
        dist = math.hypot(wx - st.x, wy - st.y)
        if dist < self.best - 2:
            self.best = dist
            self.stuck_t = 0
        elif self.last_moving:
            self.stuck_t += 1
        if self.stuck_t > 45:
            self.say('stuck near (%d, %d) -> replan' % (st.x, st.y))
            # The same spot three times running: whatever stops the player is not
            # in the plan (a thing, a corner the grid rounds off). Say what is
            # near, and back off along the walked trace before planning again.
            hist = [(t_, x_, y_) for t_, x_, y_ in getattr(self, 'stuck_hist', [])
                    if st.level_time - t_ < 500 and math.hypot(x_ - st.x, y_ - st.y) < 24]
            hist.append((st.level_time, st.x, st.y))
            self.stuck_hist = hist
            if len(hist) >= 3 and not any(sb[0] == 'goto' for sb in self.sub):
                near_ = ['%s@(%d,%d)' % (t.type, t.x, t.y) for t in st.things
                         if math.hypot(t.x - st.x, t.y - st.y) < 72]
                back = None
                for i_ in range(len(self.trace) - 1, max(len(self.trace) - 900, 0), -4):
                    x_, y_ = self.trace[i_]
                    if math.hypot(x_ - st.x, y_ - st.y) >= 80:
                        back = (x_, y_)
                        break
                # and plan round the spot just ahead for a while: the grid calls
                # it clear, the engine does not (E1M4's corner at (128, 416))
                L_ = math.hypot(wx - st.x, wy - st.y) or 1.0
                bx_, by_ = st.x + (wx - st.x) / L_ * 14, st.y + (wy - st.y) / L_ * 14
                self.learned_blocks = getattr(self, 'learned_blocks', []) + [(bx_, by_, 6.0, st.level_time + 700)]
                self.say('stuck x%d at (%d, %d); near: %s; backing off to %s; blocking (%d, %d)' % (
                    len(hist), st.x, st.y, ' '.join(near_) or 'nothing', back, bx_, by_))
                self.stuck_hist = []
                if back is not None:
                    self.sub.append(['goto', '%.1f' % back[0], '%.1f' % back[1], '16'])
                    self.path = None
                    self.goal = None
                    return [], ang_to(back[0] - st.x, back[1] - st.y)
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
        # While combat owns the facing (aiming at something), that would never
        # move at all: walk relative to the aim instead (forward/strafe mixes).
        if aiming:
            keys = move_keys(rel) + (['run'] if dist >= 24 and not tight and not ledge else [])
        elif tight:
            keys = ['fwd'] if abs(rel) <= 8 else []
        elif ledge:
            keys = ['fwd'] if abs(rel) <= 12 else []
        elif abs(rel) <= 20:
            keys = ['fwd', 'run'] if dist >= 24 else ['fwd']
        elif abs(rel) <= 64:
            keys = ['fwd']
        else:
            keys = []
        if getattr(self, 'jiggle', 0) > 0:
            self.jiggle -= 1
            keys = ['back', 'sl' if (st.level_time // 6) % 2 else 'sr']
        if dist < 8 and len(self.path) <= 1:
            keys = []             # at the goal itself (a waypoint short of it is popped at `adv`)
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
            # Already on the way to call it, and the way to the switch needs the
            # lift too (E1M7 lift 70: up, the bot on it, switch 645 faces the
            # room below): that call cannot be made from here. Drop it and pick
            # another (642 / 643 face the lift itself), never stack a second one.
            top = self.sub[-1] if self.sub else None
            if top and top[0] in ('use', 'cross') and top[1].isdigit() and int(top[1]) in acts:
                self.lift_fail[(lift, int(top[1]))] = st.level_time + 1200
                self.say('lift %d: the way to line %s needs the lift itself; another call' % (lift, top[1]))
                self.sub.pop()
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
        nv.set_obstacles(self.obstacles(st), self.learned(st))
        nv.plan_heights(self.d.floor, self.d.ceil, st.keys, special=self.d.special)
        # where the lift is NOW: the walk to its switch cannot count on it
        nv.ranges.pop(lift, None)
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
        return n             # rockets are kept for what bullets and shells cannot do

    def rockets_ok(self, st, d, t=None):
        """The blast reaches 128 (+ the player's radius): never at what is close,
        and never at a melee monster inside 300 — a demon or spectre covers ten
        units a tic, so the NEXT rocket would meet it at the player's feet (an
        E1M6 run lost 86 health in a tic that way)."""
        rush = t is not None and t.type in (3002, 58, 3006)
        if not (((st.weapons >> 5) & 1) and st.rockets > 0 and d > (300 if rush else 200)):
            return False
        return t is None or self.rocket_clear(st, ang_to(t.x - st.x, t.y - st.y), d)

    def rocket_clear(self, st, ang, d):
        """The engine detonates the player's rocket wherever the PLAYER could not
        stand: within 16 of a wall, past a step up of more than 24 from the
        player's floor, under a low ceiling (things.cyr thing_missile_tick calls
        player_check_position, from the player's own position; audit RK-1).
        Vanilla flies it on its own radius and height. Only the first 240 units
        can splash the player, so fire only if that stretch is clear."""
        nv = self.nav
        a = ang * 2 * math.pi / A
        ca, sa = math.cos(a), math.sin(a)
        k0 = nv.cell_of(st.x, st.y)
        cf = self.d.floor[st.sector] if st.sector >= 0 else None
        if k0 < 0:
            return False
        s_ = 32.0                       # MISSILE_SPAWN_OFFSET
        lim = min(d - 24.0, 240.0)      # where the target stands it may go off
        while s_ <= lim:
            q = nv.cell_of(st.x + ca * s_, st.y + sa * s_)
            if q < 0 or q in nv.blocked or not nv.ok_live(q, k0, self.d.floor, self.d.ceil, cfloor=cf):
                return False
            s_ += 8.0
        return True

    def want_pickup(self, st, need_health=False):
        """A nearby item worth a detour, as a 'pickup' sub-objective, or None.
        need_health: the route's next leg would cost about the health left, so
        any reachable health that pays is worth the walk."""
        has = lambda w: (st.weapons >> w) & 1
        shots = self.shots(st)
        ammo_limit = 3000 if shots == 0 else 1500 if shots < 15 else 0
        # Low on ammo (no monster drops or backpack in this engine yet, so the
        # map's own ammo is all there is): the walk to it is worth more.
        low = st.bullets < 60 or (has(3) and st.shells < 16)
        reach_b = 900 if st.bullets < 60 else 400
        reach_s = 900 if st.shells < 16 else 450
        # about to leave the map: what is left here is lost, so top up first
        leaving = self.si < len(self.steps) and self.steps[self.si][0] in ('exit', 'endsector')
        # no wandering off while something awake is close: finish the fight first
        # (unless all there is to fight with is the pistol: then the shotgun or
        # chaingun IS how the fight gets finished — E1M8 from a pistol start)
        weak = not (has(3) or has(4) or has(6))
        if shots > 0 and not weak and any(t.cat == CAT_MONSTER and t.state in AWAKE and
                             math.hypot(t.x - st.x, t.y - st.y) < 600 for t in st.things):
            return None
        best = None
        for t in st.things:
            if t.cat not in (CAT_ITEM, CAT_WEAPON) or self.skip_items.get(t.idx, -1) > st.level_time:
                continue
            d = math.hypot(t.x - st.x, t.y - st.y)
            what, limit = None, 0
            if t.type in wadmap.WEAPONS and not has(wadmap.WEAPONS[t.type]):
                what, limit = 'weapon', 900
            elif t.type in (2011, 2012) and (st.health < 80 or need_health):
                # below half health, healing comes before the route: anywhere on
                # the map the planner can reach (the path-length check below)
                what, limit = 'health', 2500 if (st.health < 50 or leaving or need_health) else 450 if st.health < 65 else 250
            elif t.type == 2014 and st.health < 60:
                what, limit = 'health', 400
            elif t.type == 2013:
                what, limit = 'soulsphere', 700
            elif t.type in (2018, 2019) and st.armor < 60:
                what, limit = 'armor', 1500 if leaving else 500
            elif t.type == 8:
                what, limit = 'backpack', 700
            elif t.type in (2008, 2049) and has(3) and st.shells < 50:
                what, limit = 'shells', ammo_limit or reach_s
            elif t.type in (2007, 2048) and st.bullets < 150:
                what, limit = 'bullets', ammo_limit or reach_b
            elif t.type in (2010, 2046) and has(5) and st.rockets < 20:
                what, limit = 'rockets', ammo_limit or 400
            elif t.type == 2001 and has(3) and st.shells < 50:
                what, limit = 'shells', ammo_limit or reach_s  # an owned shotgun still carries shells
            elif t.type == 2002 and has(4) and st.bullets < 150:
                what, limit = 'bullets', ammo_limit or reach_b
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
        self.nav.set_obstacles(self.obstacles(st), self.learned(st))
        self.nav.plan_heights(self.d.floor, self.d.ceil, st.keys, special=self.d.special)
        p = self.nav.path_to_touch(st.x, st.y, t.x, t.y,
                                   max_nodes=200000 if what == 'health' and st.health < 50 else 60000)
        if p is None:
            self.skip_items[t.idx] = st.level_time + 1400
            return None
        length = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(p, p[1:]))
        # Never a detour over a closet trigger: E1M5's line 191 lets eight
        # sergeants out, and the soulsphere and chainsaw lie past it (three lives
        # went that way). The route itself never needs to cross one.
        for a, b in zip(p, p[1:]):
            hit = next((li for li in getattr(self, 'ambush', ())
                        if any(self.d.ceil[s_] - self.d.floor[s_] < 56 for s_ in self.m.tagged(self.m.lines[li]['tag']))
                        and navmod.segs_cross(a[0], a[1], b[0], b[1], *self.m.line_xy(li))), None)
            if hit is not None:
                self.skip_items[t.idx] = st.level_time + 2100
                self.say('skip %s at (%d, %d): the way crosses closet trigger %d' % (what, t.x, t.y, hit))
                return None
        # how far round is acceptable depends on need: ammo when low is worth a walk
        stretch = 2.4 if (what in ('shells', 'bullets', 'rockets') and low) else 1.6
        if length > stretch * math.hypot(t.x - st.x, t.y - st.y) + 200 or length > 3000:
            self.skip_items[t.idx] = st.level_time + 700     # it may be nearer from elsewhere
            return None
        # a detour past a crowd (often a closet that opens as you pass) is not
        # worth it unless at full strength, or for ammo when dry
        # (a weapon only when all the bot has is the pistol: E1M5's chainsaw sits
        # past five sergeants, and three lives went after it with a shotgun in hand)
        essential = (what == 'weapon' and st.health > 50 and weak) or what == 'soulsphere'
        # badly hurt, health is worth more risk: going on at 26 is worse
        crowd_cap = 8 if (what == 'health' and st.health < 40) else 3
        if st.health < 100 and not essential and not (ammo_limit and what in ('shells', 'bullets', 'rockets')) and \
                self.crowd_near_path(st, p) >= crowd_cap:
            self.skip_items[t.idx] = st.level_time + 700
            self.say('skip %s at (%d, %d): %d monsters along the way' % (what, t.x, t.y, self.crowd_near_path(st, p)))
            return None
        # never detour somewhere it cannot come back from (a drop-off is one-way)
        back = self.nav.path_to_point(t.x, t.y, st.x, st.y, tol=24.0, max_nodes=60000)
        if back is None:
            self.skip_items[t.idx] = st.level_time + 1400
            return None
        # What the walk there and back costs in damaging floors: a stimpack
        # across nukage at 26 health is a loss (E1M6 sector 34 killed two
        # lives that way). The floor bites every 32 tics (path_damage).
        cost = self.path_damage(p) + self.path_damage(back)
        gain = {2011: 10, 2012: 25, 2014: 1, 2013: 100}.get(t.type, 0) if what in ('health', 'soulsphere') else 0
        # never a walk that could kill; health only for a net gain; anything else
        # only for a scratch (a soulsphere at 18 health is worth 7 of nukage)
        if cost and (cost >= st.health - 2 or (gain and gain - cost < 5) or
                     (not gain and (cost > 20 or cost >= st.health - 15))):
            self.skip_items[t.idx] = st.level_time + 700
            self.say('skip %s at (%d, %d): %d damage on the way' % (what, t.x, t.y, cost))
            return None
        # budget: the walk at 3 units a tick, plus time for a lift or a door
        budget = int(length / 3) + (800 if what == 'soulsphere' else 400)
        return ['pickup', '%.1f' % t.x, '%.1f' % t.y, what, str(t.idx), str(st.level_time), str(budget)]

    def path_damage(self, p):
        """Health a walk along waypoints p loses to damaging floors (live specials)."""
        sp, sec_of = self.d.special, self.m.point_sector
        tot = 0.0
        for a, b in zip(p, p[1:]):
            n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 8) + 1
            for q in range(n):
                s_ = sec_of(a[0] + (b[0] - a[0]) * q / n, a[1] + (b[1] - a[1]) * q / n)
                if s_ >= 0:
                    # 8 units at ~6 a tic (turns, precise walking near ledges and
                    # barrels: measured E1M6 detours ran slower than 10)
                    tot += navmod.DAMAGE_SPECIALS.get(sp[s_], 0) * (8.0 / 6.0) / 32.0
        return int(tot + 0.5)

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
            if d > 900 or (shots == 0 and d > 160 and not self.rockets_ok(st, d, t)):
                continue
            if st.health < 30 and d > 500:
                continue      # badly hurt: no long-range trades, break line of sight instead
            if shots < 40 and t.type in (3001, 3002, 58, 3006) and d > 450:
                continue      # low on ammo: what is not a hitscanner can come to the saw / shotgun
            # nearest first, weighted by how much it hurts: hitscanning sergeants
            # and cacodemons before imps, imps before zombiemen
            danger = {9: 1.6, 3005: 1.5, 3003: 1.4, 3001: 1.2, 3002: 1.3, 58: 1.3, 3006: 1.1}.get(t.type, 1.0)
            score = d / danger - (300 if awake else 0)
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
        # a sticky target keeps the aim for a moment after it ducks out of sight,
        # but a shot needs line of sight NOW (the hitscan stops at the wall)
        fire = err <= tol and t.los == 1
        if st.weapon in (1, 6) and d > 78:
            fire = False          # melee reaches 64 past the centre gap; a swing at air only makes noise
        if st.weapon == 5 and not self.rockets_ok(st, d, t):
            fire = False          # the switch away lands next tic; no rocket into the wall meanwhile
        # never shoot a barrel we are standing next to (shotgun spread, a miss)
        self.barrel_side = None
        for b in st.things:
            if b.type != 2035:
                continue
            db = math.hypot(b.x - st.x, b.y - st.y)
            # only a barrel BEFORE the target can take the shot (bullets stop at
            # the first thing they hit), and only one inside blast range of us
            # matters: a farther one going off is good news. The blast reaches
            # 128 units measured as max(|dx|, |dy|) less the player's radius
            # (things.cyr splash_damage_at): from 144 on the axis it cannot hurt.
            cheb = max(abs(b.x - st.x), abs(b.y - st.y))
            if cheb >= 160 or db > d - 12:
                continue
            cone = math.atan2(24.0, max(db, 1.0)) * (A / 2) / math.pi + 10
            off = adiff(ang_to(b.x - st.x, b.y - st.y), want)
            if abs(off) <= cone:
                fire = False
                # walk to the nearest spot out of its blast range (a straight
                # back-step is often into a wall); from there it may be shot
                key_ = (b.idx, st.level_time // 20)
                if getattr(self, 'barrel_key', None) != key_:
                    self.barrel_key = key_
                    bx_, by_ = b.x, b.y
                    self.barrel_pt = self.nav.nearest_where(
                        st.x, st.y, lambda cx, cy: max(abs(cx - bx_), abs(cy - by_)) >= 170)
                pt_ = getattr(self, 'barrel_pt', None)
                if pt_ is not None:
                    self.barrel_side = ang_to(pt_[0] - st.x, pt_[1] - st.y)
        engaged = awake and d < 1100
        return (want, fire, wkey, engaged, t, d)

    def retreat_keys(self, st):
        """Hurt in a fight (under 45 health, or 30 lost in the last 2 s): back
        off toward where the bot stood a few seconds ago (cleared ground) while
        it keeps aiming. Breaking line of sight with a group is what lets it
        take them one at a time."""
        hist = self.hp_hist
        lost = max((h for t_, h in hist if st.level_time - t_ <= 70), default=st.health) - st.health
        many = sum(1 for t in st.things if t.cat == CAT_MONSTER and t.state in AWAKE and t.los == 1 and
                   math.hypot(t.x - st.x, t.y - st.y) < 600)
        if st.health >= 45 and lost < 30 and many < 3:
            return None
        # keep one retreat point until it is reached or 2 s pass: re-picking from
        # the trace every tick (which the retreat itself extends) made it jitter
        rp = getattr(self, 'retreat_pt', None)
        if rp is not None and (st.level_time - rp[2] > 70 or math.hypot(rp[0] - st.x, rp[1] - st.y) < 16):
            rp = None
        if rp is None:
            # Back along cleared ground, to the nearest point there that the awake
            # shooters cannot see (behind a corner they come round one at a time);
            # failing that, the first point 96 units back.
            tr = self.trace
            shooters = [(t.x, t.y) for t in st.things if t.cat == CAT_MONSTER and t.state in AWAKE and
                        t.los == 1 and math.hypot(t.x - st.x, t.y - st.y) < 1200]
            first = None
            for i in range(len(tr) - 30, max(len(tr) - 900, 0), -6):
                x, y = tr[i]
                if math.hypot(x - st.x, y - st.y) < 96:
                    continue
                if first is None:
                    first = (x, y, st.level_time, i, len(tr))
                    if not shooters:
                        break
                if math.hypot(x - st.x, y - st.y) > 700:
                    break
                if all(not self.nav.sight(mx, my, x, y, self.d.floor, self.d.ceil) for mx, my in shooters):
                    rp = (x, y, st.level_time, i, len(tr))
                    self.say('cover at (%d, %d) from %d shooter(s)' % (x, y, len(shooters)))
                    break
            if rp is None:
                rp = first
            self.retreat_pt = rp
        if rp is None:
            return None
        pt = (rp[0], rp[1])
        # Walk back ALONG the trace, not straight at the point: the point may be
        # round a corner, and a straight line there ran into the wall while a
        # sergeant shot (E1M6, held at (-1647, 1472) for 300 tics). Head for the
        # trace a little behind where the player now is, never past the point.
        # (only the trace as it was when the point was picked: what the retreat
        # itself adds leads back toward the fight)
        tr, i0, i1 = self.trace, rp[3], rp[4]
        j = min(range(i0, i1, 2), key=lambda k: (tr[k][0] - st.x) ** 2 + (tr[k][1] - st.y) ** 2, default=i0)
        step = j
        while step > i0 and math.hypot(tr[step][0] - st.x, tr[step][1] - st.y) < 24:
            step -= 1
        pt = tr[step]
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
        """Shells are the scarce, strong ammo: spend them on what needs them
        (sergeants, demons, spectres, the big ones, imps up close) and bullets
        on the rest. A run that shot zombiemen with the shotgun reached E1M5's
        east wing with 115 bullets and no shells."""
        has = lambda w: (st.weapons >> w) & 1
        tough = t.type in (3003, 3005, 3002, 58)   # baron, caco, demon, spectre
        gun = 4 if has(4) else 2
        shotgun = has(3) and st.shells > 0
        crowd = sum(1 for o in st.things if o.cat == CAT_MONSTER and o.state in AWAKE and
                    math.hypot(o.x - t.x, o.y - t.y) < 128)
        choice = None
        # The chainsaw costs nothing and cuts about as fast as the chaingun
        # fires (2..20 every 8 tics, player.cyr): it is for the melee monsters,
        # which come to the player anyway, and for anything weak up close.
        # A little hysteresis so the bot does not flick between weapons.
        saw_r = {3002: 200, 58: 200, 3006: 160, 3004: 90, 3001: 80}.get(t.type, 0)
        if has(6) and st.weapon == 6:
            saw_r += 40
        if has(6) and d < saw_r and crowd < 3 and (st.health >= 40 or t.type in (3004, 3006) or self.shots(st) == 0):
            choice = 6           # (a demon or spectre bites back: not at under 40 if there is a gun)
        elif self.rockets_ok(st, d, t) and d > 260 and crowd >= 3:
            choice = 5           # a rocket into a group: the splash does the work
        elif self.rockets_ok(st, d, t) and (t.type in (3003, 3005, 3002, 58) or self.shots(st) == 0):
            choice = 5
        elif t.type == 3004 and st.bullets >= 20:
            choice = gun         # zombieman: 20 hp, two bullets
        elif t.type == 3001 and not (shotgun and (d < 250 or st.shells >= 30)) and st.bullets >= 20:
            choice = gun         # imp at range: the chaingun, keep the shells
        elif shotgun and (d < 500 or tough or t.type == 9):
            choice = 3
        elif has(4) and st.bullets > 0:
            choice = 4
        elif shotgun:
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
