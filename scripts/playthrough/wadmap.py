"""wadmap.py — one map's geometry, read straight from the IWAD (stdlib only).

Part of the scripted playthrough (roadmap v0.37.0 / v1.0.0-1). The harness plans
against the same data the engine loads: vertices, linedefs, sidedefs, sectors,
things, and the BSP (for point-in-sector, using the engine's side rule).
"""
import struct, zlib

ML_BLOCKING = 0x0001
ML_TWOSIDED = 0x0004

# Thing type numbers the harness cares about (DoomEd numbers, as src/things.cyr).
KEY_TYPES = {5: 'blue', 40: 'blue', 6: 'yellow', 39: 'yellow', 13: 'red', 38: 'red'}
KEY_BITS = {'blue': 1, 'yellow': 2, 'red': 4}
MONSTERS = {3004: 'zombie', 9: 'sergeant', 3001: 'imp', 3002: 'demon', 58: 'spectre',
            3006: 'lostsoul', 3005: 'caco', 3003: 'baron', 16: 'cyber', 7: 'spider'}
HEALTH = {2011: 10, 2012: 25, 2014: 1, 2013: 100}
ARMOR = {2018: 100, 2019: 200, 2015: 1}
# weapon slot each pickup sets (things.cyr player_give_weapon): chainsaw 6, plasma 7, BFG 8
WEAPONS = {2001: 3, 2002: 4, 2003: 5, 2004: 7, 2005: 6, 2006: 8}
AMMO = {2007: 'bullets', 2048: 'bullets', 2008: 'shells', 2049: 'shells',
        2010: 'rockets', 2046: 'rockets', 2047: 'cells', 17: 'cells'}


def read_wad(path):
    data = open(path, 'rb').read()
    ident, n, off = struct.unpack_from('<4sii', data, 0)
    lumps = []
    for i in range(n):
        lo, ls, name = struct.unpack_from('<ii8s', data, off + i * 16)
        lumps.append((name.rstrip(b'\0').decode('ascii', 'replace'), lo, ls))
    return data, lumps


class Map:
    def __init__(self, wad, name):
        data, lumps = wad
        idx = [i for i, l in enumerate(lumps) if l[0] == name][0]
        raw = {}
        for j, nm in enumerate(['THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS',
                                'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP']):
            ln, lo, ls = lumps[idx + 1 + j]
            assert ln == nm, (ln, nm)
            raw[nm] = data[lo:lo + ls]
        self.name = name
        v = raw['VERTEXES']
        self.verts = [struct.unpack_from('<hh', v, i * 4) for i in range(len(v) // 4)]
        s = raw['SIDEDEFS']
        self.sides = []
        for i in range(len(s) // 30):
            xo, yo, up, lo, mid, sec = struct.unpack_from('<hh8s8s8sH', s, i * 30)
            self.sides.append(sec)
        l = raw['LINEDEFS']
        self.lines = []
        for i in range(len(l) // 14):
            v1, v2, fl, sp, tag, rs, lsd = struct.unpack_from('<HHHHHHH', l, i * 14)
            rs = -1 if rs == 0xFFFF else rs
            lsd = -1 if lsd == 0xFFFF else lsd
            self.lines.append(dict(i=i, v1=v1, v2=v2, flags=fl, special=sp, tag=tag,
                                   front=(self.sides[rs] if rs >= 0 else -1),
                                   back=(self.sides[lsd] if lsd >= 0 else -1)))
        sc = raw['SECTORS']
        self.sectors = []
        for i in range(len(sc) // 26):
            fh, ch, ft, ct, light, sp, tag = struct.unpack_from('<hh8s8shHH', sc, i * 26)
            self.sectors.append(dict(floor=fh, ceil=ch, light=light, special=sp, tag=tag))
        t = raw['THINGS']
        self.things = []
        for i in range(len(t) // 10):
            x, y, ang, typ, fl = struct.unpack_from('<hhhHH', t, i * 10)
            self.things.append(dict(i=i, x=x, y=y, angle=ang, type=typ, flags=fl))
        sg = raw['SEGS']
        self.segs = [struct.unpack_from('<HHhHhh', sg, i * 12) for i in range(len(sg) // 12)]
        ss = raw['SSECTORS']
        self.ssectors = [struct.unpack_from('<HH', ss, i * 4) for i in range(len(ss) // 4)]
        nd = raw['NODES']
        self.nodes = [struct.unpack_from('<hhhh8hHH', nd, i * 28) for i in range(len(nd) // 28)]
        self.ss_sector = []
        for cnt, first in self.ssectors:
            v1, v2, ang, li, dirn, off = self.segs[first]
            ln = self.lines[li]
            self.ss_sector.append(ln['front'] if dirn == 0 else ln['back'])
        xs = [p[0] for p in self.verts]
        ys = [p[1] for p in self.verts]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        # sector adjacency through two-sided lines
        self.neighbors = [set() for _ in self.sectors]
        self.sector_lines = [[] for _ in self.sectors]
        for ln in self.lines:
            for s_ in (ln['front'], ln['back']):
                if s_ >= 0:
                    self.sector_lines[s_].append(ln['i'])
            if ln['front'] >= 0 and ln['back'] >= 0 and ln['front'] != ln['back']:
                self.neighbors[ln['front']].add(ln['back'])
                self.neighbors[ln['back']].add(ln['front'])

    def line_xy(self, li):
        ln = self.lines[li]
        return self.verts[ln['v1']] + self.verts[ln['v2']]

    def point_sector(self, x, y):
        """Sector at world point (x, y), by the engine's BSP descent and side rule
        (bsp_point_on_side: left >= right → child 0). x, y may be fractional."""
        n = len(self.nodes) - 1
        if n < 0:
            return 0
        guard = 0
        while (n & 0x8000) == 0:
            nx, ny, ndx, ndy = self.nodes[n][:4]
            left = (x - nx) * ndy
            right = (y - ny) * ndx
            n = self.nodes[n][12] if left >= right else self.nodes[n][13]
            guard += 1
            if guard > len(self.nodes):
                return -1
        return self.ss_sector[n & 0x7FFF]

    def player_start(self):
        for t in self.things:
            if t['type'] == 1:
                return t
        return None

    def lowest_neighbor_ceil(self, s):
        cs = [self.sectors[n]['ceil'] for n in self.neighbors[s]]
        return min(cs) if cs else self.sectors[s]['ceil']

    def lowest_neighbor_floor(self, s):
        fs = [self.sectors[n]['floor'] for n in self.neighbors[s]]
        return min([self.sectors[s]['floor']] + fs)

    def tagged(self, tag):
        return [i for i, s in enumerate(self.sectors) if s['tag'] == tag and tag != 0]


# ---------------------------------------------------------------- PNG output
def _png(path, w, h, rgb):
    raw = b''.join(b'\0' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(raw, 6)))
        f.write(chunk(b'IEND', b''))


class Canvas:
    def __init__(self, m, scale=0.25, margin=24):
        x0, y0, x1, y1 = m.bbox
        self.x0, self.y1, self.s, self.mg = x0, y1, scale, margin
        self.w = int((x1 - x0) * scale) + 2 * margin
        self.h = int((y1 - y0) * scale) + 2 * margin
        self.px = bytearray(b'\x10' * (self.w * self.h * 3))

    def to(self, x, y):
        return (int((x - self.x0) * self.s) + self.mg, int((self.y1 - y) * self.s) + self.mg)

    def dot(self, X, Y, c):
        if 0 <= X < self.w and 0 <= Y < self.h:
            o = (Y * self.w + X) * 3
            self.px[o:o + 3] = bytes(c)

    def line(self, x1, y1, x2, y2, c):
        X1, Y1 = self.to(x1, y1)
        X2, Y2 = self.to(x2, y2)
        n = max(abs(X2 - X1), abs(Y2 - Y1), 1)
        for k in range(n + 1):
            self.dot(X1 + (X2 - X1) * k // n, Y1 + (Y2 - Y1) * k // n, c)

    def box(self, x, y, r, c):
        X, Y = self.to(x, y)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                self.dot(X + dx, Y + dy, c)

    # 3x5 digits for labels
    _D = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111',
          '3': '111001111001111', '4': '101101111001001', '5': '111100111001111',
          '6': '111100111101111', '7': '111001001001001', '8': '111101111101111',
          '9': '111101111001111', '-': '000000111000000'}

    def text(self, x, y, s, c):
        X, Y = self.to(x, y)
        for ch in s:
            g = self._D.get(ch)
            if g:
                for k, b in enumerate(g):
                    if b == '1':
                        self.dot(X + k % 3, Y + k // 3, c)
            X += 4

    def save(self, path):
        _png(path, self.w, self.h, self.px)


def render_overview(m, path, scale=0.25, labels=True, extra=None):
    """Lines (white one-sided, grey two-sided, colour = special), keys, start,
    monsters; special lines labelled with their linedef index. `extra(canvas)`
    draws on top (planned paths, the bot's trace)."""
    cv = Canvas(m, scale)
    for ln in m.lines:
        x1, y1, x2, y2 = m.line_xy(ln['i'])
        c = (200, 200, 200) if ln['back'] < 0 else (90, 90, 90)
        if ln['special']:
            c = (255, 200, 0) if ln['special'] in (11, 51, 52, 124, 197, 198) else (0, 200, 255)
        cv.line(x1, y1, x2, y2, c)
    if labels:
        for ln in m.lines:
            if ln['special']:
                x1, y1, x2, y2 = m.line_xy(ln['i'])
                cv.text((x1 + x2) / 2, (y1 + y2) / 2, str(ln['i']), (255, 255, 255))
    for t in m.things:
        if t['type'] in KEY_TYPES:
            col = {'blue': (60, 60, 255), 'yellow': (255, 255, 0), 'red': (255, 40, 40)}[KEY_TYPES[t['type']]]
            cv.box(t['x'], t['y'], 3, col)
        elif t['type'] == 1:
            cv.box(t['x'], t['y'], 3, (0, 255, 0))
        elif t['type'] in MONSTERS:
            cv.box(t['x'], t['y'], 1, (255, 0, 255))
    if extra:
        extra(cv)
    cv.save(path)
    return cv
