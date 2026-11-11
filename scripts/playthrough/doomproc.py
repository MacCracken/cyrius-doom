"""doomproc.py — run doom under --lockstep on a real pty, one tick at a time.

doom's stdin is the slave side of a pty (raw mode is doom's own, set by
input_init), so every key goes through the engine's tty decoder exactly as an
interactive session's would. doom writes a state record to fd 3 (a pipe) at the
start of each input poll and blocks until the harness writes that tick's keys
followed by the sync byte 0x1F (src/input.cyr lockstep_read). Record format:
src/lockstep.cyr.
"""
import os, pty, subprocess

SYNC = b'\x1f'
KEYS = {
    'fwd': b'w', 'back': b's', 'sl': b'a', 'sr': b'd', 'run': b'r', 'fire': b'f',
    'use': b'e', 'tl': b'\x1b[D', 'tr': b'\x1b[C', 'quit': b'q',
    '1': b'1', '2': b'2', '3': b'3', '4': b'4', '5': b'5', '6': b'6', '7': b'7',
    'enter': b'\n',
}
SCREENS = {0: 'play', 1: 'intermission', 2: 'death', 3: 'finale_text', 4: 'finale_pic', 5: 'menu'}

S_FIELDS = ('seq screen map_gen map level_time x y z angle health armor weapon weapons bullets shells '
            'rockets cells keys sector kills max_kills items max_items secrets max_secrets freeze next_level').split()


class Thing:
    __slots__ = ('idx', 'type', 'cat', 'state', 'x', 'y', 'health', 'flags', 'los')

    def __init__(self, f):
        self.idx, self.type, self.cat, self.state = int(f[1]), int(f[2]), int(f[3]), int(f[4])
        self.x, self.y = int(f[5]) / 65536.0, int(f[6]) / 65536.0
        self.health, self.flags, self.los = int(f[7]), int(f[8]), int(f[9])


class State:
    def __init__(self, lines):
        f = lines[0].split()
        assert f[0] == 'S', lines[0]
        vals = f[1:]
        for k, v in zip(S_FIELDS, vals):
            setattr(self, k, v if k == 'map' else int(v))
        self.x /= 65536.0
        self.y /= 65536.0
        self.z /= 65536.0
        self.screen_name = SCREENS.get(self.screen, str(self.screen))
        self.things = []
        self.heights = []
        for ln in lines[1:]:
            if ln[0] == 'T':
                self.things.append(Thing(ln.split()))
            elif ln[0] == 'H':
                f_ = ln.split()
                self.heights.append((int(f_[1]), int(f_[2]), int(f_[3]), int(f_[4])))


class Doom:
    def __init__(self, doom, wad, mapname=None, log_path='/dev/null', extra_args=()):
        self.master, slave = pty.openpty()
        r, w = os.pipe()
        self.log = open(log_path, 'wb')
        args = [doom, wad] + ([mapname] if mapname else []) + ['--lockstep'] + list(extra_args)

        def pre():
            os.dup2(w, 3)
            os.setsid()
        # fd 3 is created by dup2 in the child; keep it (and w) through close_fds
        # whichever order subprocess applies them in.
        self.proc = subprocess.Popen(args, stdin=slave, stdout=self.log, stderr=self.log,
                                     preexec_fn=pre, pass_fds=(w, 3), close_fds=True)
        os.close(slave)
        os.close(w)
        self.rf = os.fdopen(r, 'rb', buffering=0)
        self.buf = b''
        self.floor = None
        self.ceil = None
        self.map_gen = -1
        self.state = self._record()

    def _record(self):
        while True:
            i = self.buf.find(b'\nE\n')
            if i >= 0:
                rec, self.buf = self.buf[:i + 1], self.buf[i + 3:]
                st = State(rec.decode().splitlines())
                return st
            chunk = self.rf.read(1 << 16)
            if not chunk:
                return None
            self.buf += chunk

    def step(self, keys=()):
        """Hold `keys` (names from KEYS) for one tick; return the next State
        (None when doom has exited)."""
        data = b''.join(KEYS[k] for k in keys) + SYNC
        try:
            os.write(self.master, data)
        except OSError:
            return None
        self.state = self._record()
        return self.state

    def attach_map(self, m):
        """Reset live heights to the WAD's (call when state.map_gen changes)."""
        self.floor = [s['floor'] for s in m.sectors]
        self.ceil = [s['ceil'] for s in m.sectors]
        self.special = [s['special'] for s in m.sectors]

    def apply_heights(self, st):
        for s, fl, ce, sp in st.heights:
            self.floor[s] = fl
            self.ceil[s] = ce
            self.special[s] = sp

    def close(self):
        try:
            if self.proc.poll() is None:
                self.step(('quit',))
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        try:
            os.close(self.master)
        except OSError:
            pass
        return self.proc.returncode
