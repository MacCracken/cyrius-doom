# Proposal — v0.33.0 native Wayland window backend (desktop rendering)

> **Status**: design accepted, phased implementation in progress (bite 1 landing).
> **Reference**: [puka](https://github.com/MacCracken/puka) — a sovereign Cyrius Wayland terminal;
> doom lifts its `src/platform/wayland/{wire,shm,client}.cyr` + `window.cyr` seam near-verbatim.
> **Derived from**: the 2026-07-08 study+design+critique workflow (6 agents; 11 critique findings folded in below).

## Goal

Give cyrius-doom a real, resizable **Wayland window** on Hyprland/wlroots — sovereign (raw wl protocol over
the unix socket via syscalls, **no libwayland, no new deps**) — that blits the 320×200 palette-indexed frame
and takes keyboard input. This replaces the `/dev/fb0`-or-GTK-PPM-bridge (`scripts/x11view.py`) desktop story
and pulls the v1.0.0 "Wayland display backend" item forward. **fb0 / AGNOS / `--ppm` stay byte-identical.**

## Why puka is the template

puka proves the entire path in ~615 lines of sovereign Cyrius behind a platform-neutral `win_*` seam:
`wire.cyr` (pure wire codec, no syscalls), `client.cyr` (AF_UNIX connect + registry/bind + xdg-shell dispatch
+ SCM_RIGHTS fd-passing + a keyboard ring), `shm.cyr` (memfd/mmap XRGB8888 present buffer), `window.cyr` (the
`win_*` seam). doom's `framebuf_flip` ↔ `win_present_begin`/`win_present_commit` and `input_poll` ↔
`win_poll_events`/`win_next_key` map 1:1. doom needs **no** kashi/mabda (puka's font/GPU libs) — it owns its
palette→XRGB expansion (`framebuf.cyr:210-269`, already emits XRGB8888 bytes B,G,R,X on LE).

## Architecture — the seam

doom already selects present/input backends at **compile** time via `#ifdef CYRIUS_TARGET_AGNOS`. Wayland is
a **third, runtime-selected, Linux-only** backend. A `present_mode` var (`PM_FB0=0 / PM_WAYLAND=1 / PM_PPM=2`)
gates one prepended runtime branch at the top of `framebuf_flip` and `input_poll`; the existing bodies move
into the `else` unchanged. AGNOS never sets `present_mode = PM_WAYLAND`.

```
src/platform/
  wayland/
    wire.cyr    ← lifted verbatim (pure codec; the `>>` at wire.cyr:23 is on a zero-extended load32 → safe)
    client.cyr  ← lifted ~95%: rename probe emitters to sakshi_*, ADD a wl_keyboard.leave handler (F6)
    shm.cyr     ← lifted verbatim; memfd name "puka-wl" → "doom-wl"
  window.cyr    ← lifted seam; win_open signature takes explicit (w_hint,h_hint) instead of terminal cols/rows (F4)
```

Include order (single-pass build, before `src/framebuf.cyr`): `wire → client → shm → window → framebuf`.
**All four wrapped in `#ifndef CYRIUS_TARGET_AGNOS`** (F10 — `sys_socket`/`sys_connect` are Linux-common-only;
they do not resolve on the AGNOS target and would be undefined-fn → segfault-class).

## Pixel path

`framebuf_present_wayland()` reuses `framebuf_blit`'s integer-scale + center-replicate structure, with
`dst = win_present_begin(1)` (the `shm_ptr`) and `pitch = win_w*4`. Per source pixel: `po = load8(src)*3`,
read r/g/b from `palette`, `p32 = 0xFF000000 | (r<<16) | (g<<8) | b` (matches `framebuf.cyr:234` — XRGB8888
byte order [B,G,R,X] on LE; **do not swap R/B**), `store32` replicated `scale`× horizontally, then the row
replicated `scale`× vertically. Scale/letterbox recomputed against the compositor-configured `win_w/win_h`
(same math as `framebuf.cyr:124-134`, against window not panel). Letterbox bars: `shm_fill(0)` once per
(re)create.

## Keyboard path

puka delivers a 3-i64 record via `win_next_key(1, out24)`: `[+0]` = **raw evdev keycode** (not keysym, not
+8), `[+8]` = value (1=press/0=release, no repeat synthesis), `[+16]` = mods (ignored — doom latches the raw
modifier keycodes). New `doom_evdev_to_key(ev)` maps evdev → doom's ASCII-ish `key_state` indices
(`input.cyr:47-64`): W=17→119, A=30→97, S=31→115, D=32→100, E=18→101, R=19→114, Q=16→113, UP=103→128,
DOWN=108→129, LEFT=105→130, RIGHT=106→131, SPACE=57→32, ENTER=28→10, TAB=15→9, ESC=1→27, LCTRL=29/RCTRL=97→132,
LSHIFT=42/RSHIFT=54→133, KEY_1..7 = 2..8 → `ev+47` (49..55). If/else chain, **not switch** (cycc return-smash).

`input_poll_wayland()` uses the **AGNOS persistent-latch model** (real key-up, not the tty press-then-clear
loop at `input.cyr:380`): non-blocking drain → `store64(key_state + idx*8, value)` → rebuild `input_flags` via
a shared `input_build_flags_from_state()` extracted from the AGNOS branch (`input.cyr:259-294`, third-instance
rule).

**Control scheme (decision, F5)**: Wayland is Linux-desktop, so it uses the **existing Linux scheme — arrows
turn, A/D strafe, F/Ctrl fire** — NOT the AGNOS Shift-to-turn scheme. The shared flag-builder is parameterized
or the Wayland path uses the Linux flag semantics. (Trivially changed later if the user prefers Shift-to-turn.)

## Backend selection + event loop

Selection precedence (resolved **before** `framebuf_init` — see F1): `--fb0` → PM_FB0; `--wayland` → PM_WAYLAND
(fail loudly if `win_open` returns 0); `--ppm`/`--ppm-menu` → PM_PPM always; else `getenv("WAYLAND_DISPLAY")`
set → PM_WAYLAND; else `/dev/fb0` opens → PM_FB0; else PM_PPM. AGNOS is compile-time, never reaches this.

**Event loop**: doom's fixed 35 Hz `tick_begin`/`tick_wait` is the pacing authority. `wl_pump` does a
**blocking** `file_read` (`client.cyr:319`), so `input_poll_wayland` must **`poll(7)`-gate `win_fd` with a
0 ms timeout** and drain only when readable, never block (the same class as the 0.29.1 stdin O_NONBLOCK fix).
Use **`poll` (syscall 7)**, not `ppoll` — 3 args, `pollfd = {i32 fd; i16 events=POLLIN(1); i16 revents}` (8 B)
(F7). Present every tick (don't gate on the frame callback); `wl_frame_done` starts at 1 so the first present
never deadlocks.

## Critique resolutions (folded into the above)

| # | Finding | Resolution |
|---|---------|-----------|
| **F1** | **Showstopper**: `framebuf_init` (main.cyr:163) runs *before* arg-parse (:182), so the selector is dead code and a window would pop during `--ppm`. | Hoist `--ppm/--ppm-menu/--wayland/--fb0` detection above `framebuf_init` (bite 1's first edit). |
| **F2** | SCM_RIGHTS msghdr correct but cmsg slack bytes uninitialized; no proof the fd reaches the compositor. | Zero the cmsg pad; after `shm_create` do `wl_sync()+wl_dispatch()` and `sakshi_error` on `wl_closed`/`wl_display.error` instead of a silent blank window. |
| **F3** | Single-buffer tearing understated — doom presents at 35 Hz into a buffer the compositor still samples. | Move the double-buffer (ping-pong two wl_buffers, or gate on `wl_buf_busy==0`) into **bite 2**, not bite 4. |
| **F4** | `win_open` terminal `cols*cell_w` signature yields `win_w=0` on the 0×0 configure fallback. | Change `win_open` to take explicit `(w_hint, h_hint)`; default 640×400 (2× native). |
| **F5** | Reusing the AGNOS flag-builder silently imposes Shift-to-turn on a Linux desktop. | Use the **Linux arrows-turn scheme** (documented above). |
| **F6** | puka has **no `wl_keyboard.leave` handler**; persistent latches → walk-forever on focus loss. | Add a `leave` (op 2) handler that clears all `key_state` latches (bite 3, not polish). |
| **F7** | `ppoll` arity/pollfd-width footgun. | Use `poll` (syscall 7), 8-byte pollfd with `store16` events/revents; verify #7 in bite 1. |
| **F8** | `--ppm` byte-identity asserted, not proven. | Hard bite-1 gate: `--ppm` + `--ppm-menu` PPMs pixel-diff zero vs baseline (menu path catches init-order regressions). |
| **F9** | No automated gate past the pure codec — window is user-run on Hyprland. | Add a headless `socketpair` mock that feeds canned event bytes into `wl_rbuf` and asserts `wl__handle` sets oids/latches; plus the pure `wire.cyr` `.tcyr`. |
| **F10** | `sys_socket` Linux-common-only → undefined-fn on AGNOS. | Wrap all four platform files in `#ifndef CYRIUS_TARGET_AGNOS` from the start. |
| **F11** | Death-wait `input_poll` (main.cyr:446-458) + persistent latches — held key never lets respawn arm. | Verify the latch model vs the `dead_released` gate (AGNOS already latches, so likely OK — test, don't assume). |

## Phasing

- **Bite 1 — seam + connect + blank window.** Lift the 4 files (`#ifndef AGNOS`), wire includes, add
  `present_mode` + selection (F1 reorder) + `--wayland/--fb0/--wayland-probe` args, `win_open(w,h)` (F4),
  `poll(7)` plumbing (F7). `framebuf_present_wayland` = `shm_fill(solid)` + commit. Gate: probe prints globals,
  a blank titled window on Hyprland, **`--ppm`/`--ppm-menu` byte-identical, tests green, AGNOS QEMU clean**.
  Add the pure `wire.cyr` `.tcyr` + the socketpair dispatch mock (F9).
- **Bite 2 — real frame + double-buffer.** Full palette→XRGB integer-scaled blit (F2 fd-reachability check;
  F3 double-buffer). Gate: E1M1 matches `--ppm`, no R/B swap, no tearing.
- **Bite 3 — keyboard.** `doom_evdev_to_key` + `input_poll_wayland` + shared flag-builder + `poll`-gated drain
  + `wl_keyboard.leave` (F6). Gate: full control scheme, latch correct, no loop stall, clean quit, F11 respawn.
- **Bite 4 — resize/polish.** `WIN_EV_RESIZE` → `win_resize_apply` → rescale/letterbox/repaint;
  `xdg_wm_base.ping`→`pong`. Gate: smooth drag-resize, correct letterbox, clean close.

## Verification

Build + `--ppm`/`--ppm-menu` byte-identity + full test suite + AGNOS QEMU smoke are gated here (the Wayland
code is dead on AGNOS, proving no codegen regression). **The window itself is user-verified on Hyprland** —
this agent shell has no live compositor (`WAYLAND_DISPLAY` unset, no socket), same build-here/confirm-on-hardware
split as the audio tests. Headless CI exercises the pure `wire.cyr` codec + the socketpair dispatch mock.
Security (P(-1)): the `wl_rbuf` parser is an untrusted-input boundary — `wl__parse` size-checks (`size<8`
fatal) and the 8192-byte ceiling bounds it; documented at closeout in `docs/audit/{date}-wayland-backend.md`.

## Deps / build

No `cyrius.cyml [deps]` change — pure syscalls + existing stdlib (`getenv`, `sys_socket`, `sys_connect`,
`sys_close`; memfd/ftruncate/mmap/munmap/sendmsg/poll via the `syscall()` builtin). `VERSION` 0.32.1 → 0.33.0;
`src/main.cyr` banner; CLAUDE.md module map + `state.md` grow by 4 files.
