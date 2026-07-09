# 2026-07-09 — Wayland backend security review (v0.33.0)

**Scope**: the native Wayland window backend (`src/platform/wayland/{wire,client,shm}.cyr`,
`src/platform/window.cyr`) added in v0.33.0. Sovereign — raw wl protocol over an AF_UNIX socket via
syscalls, no libwayland, no new deps.
**Toolchain**: cycc 6.4.30 (pinned).
**Verdict**: the one untrusted-input boundary (the wire parser) is now bounds-checked; the fd-passing and
buffer paths were reviewed clean by two adversarial passes. No `sys_system`, no unchecked writes into
attacker-influenced offsets after this pass.

## Threat model

The peer is the **compositor** — a local, same-user process (Hyprland/wlroots). A cyrius-doom Wayland client
trusts the compositor for display/input; a *malicious* compositor already owns the session. So the realistic
threat is a **buggy or hostile compositor sending malformed wire messages** that crash the client or read past
its buffers (defense-in-depth, not a network boundary). Wayland is Linux-desktop-only here — the whole backend
is `#ifndef CYRIUS_TARGET_AGNOS`, so none of this surface exists on the microkernel target.

## Findings + resolutions

| # | Area | Finding | Resolution |
|---|------|---------|-----------|
| W-1 | Wire parser (`wl__parse` / `wl__handle`) | `wl__parse` only checked `size >= 8` before dispatch; the `wl_registry.global` handler then read an **attacker-controlled string length** (`wire_str_len` @ +12) and used it in `wire_str_next` / `wl__streq`, so a huge length could compute a read address **past the 8192-byte `wl_rbuf`**. | **Fixed**: `wl__handle` re-derives the message `size` and the registry branch now requires `16 <= size`, `L > 0`, and `wire_str_next(o+12, L) + 4 <= o + size` before reading the name bytes or the trailing version. A malformed global is skipped, not read out of bounds. |
| W-2 | Fixed-offset field reads | Event handlers read fixed offsets beyond `o+8` (e.g. the key event's `key@+16`/`state@+20`) with no per-event size check; a short message at the buffer tail could read a few bytes past `wl_rlen`. | **Fixed** two ways: `wl_rbuf` is alloc'd with **64 bytes of read-slack** past `WL_RBUF_CAP` (the write cap is unchanged, so this only covers over-reads), and `wl__kbd` guards `EV_KBD_KEY`/`EV_KBD_MODS` on `size >= 24`/`>= 16`. |
| W-3 | SCM_RIGHTS fd passing (`wl__send_fd`) | The `cmsg`/`msghdr` scratch could pass uninitialized slack bytes into `sendmsg`. | **Already hardened** in bite 1: `cmsg`/`mh` are fully zeroed before the fields are set (stricter than the puka original). Reviewed clean. |
| W-4 | `var x[N]` buffer sizing | (Process finding, not a live vuln) a bite-1 lift mis-sized several stack scratch buffers by assuming `var x[N]` = N i64 elements; it is N **bytes** → stack overflow. | **Fixed** in bite 1 (adversarial review caught it); recorded as a Cyrius reference note. No mis-sized buffer remains (grep-verified). |
| W-5 | Resize OOM crash (grow path) | On a `shm_create` failure during a drag-grow, `shm_ptr0/1` were left dangling (unmapped) while `win_w/win_h` were already committed → the next present `store32`s into unmapped memory (SIGSEGV). | **Fixed** in bite 4: `shm_create` clears the buffer pointers up front (any failure → 0, caught by the `dst==0` present guard), and `win_resize_apply` commits `win_w/win_h` only after `shm_resize` succeeds. |

## Regression tests (CI, headless — no compositor needed)

- `wayland: wire codec byte layout` — the pure `wire.cyr` codec (header pack, string len/pad, `wire_str_next`).
- `wayland: wl__parse bounds untrusted registry` — a well-formed `wl_registry.global` binds; a hostile
  huge-length global is **rejected with no bind and no OOB**; a `size < 8` message aborts the parse. Directly
  exercises the W-1/W-2 hardening.

## Residual / out of scope

- The remaining fixed-offset handlers (`xdg_surface.configure` @ +8, `xdg_wm_base.ping` @ +8,
  `wl_seat.capabilities` @ +8, `toplevel.configure` @ +8/+12) read at most `o+12`, bounded by the `size >= 8`
  gate plus the 64-byte read-slack; a hostile short message yields a wrong value (a spurious ack/ping/cap), not
  an OOB fault. Acceptable for the local-compositor threat model; a full per-event size table is a future
  hardening if a PWAD-style "untrusted compositor" scenario ever matters.
- The window/input functional surface is user-verified on Hyprland (no live compositor in CI/dev shell).
