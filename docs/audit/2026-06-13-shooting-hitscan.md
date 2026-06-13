# Security audit — shooting / hitscan / projectile path (v0.30.0)

**Date**: 2026-06-13
**Scope**: the 0.30.0 shooting overhaul — `player_try_fire`, `player_fire_ray`,
`player_hitscan`, `thing_damage`, `thing_explode`, `thing_spawn_missile` /
`thing_missile_tick`, and the weapon psprite decoder `render_draw_weapon`.
**Trigger**: CLAUDE.md P(-1) step 5 (security research before shipping a feature
area). The shooting code predates this process; this entry discharges the back-fill.

## CVE / exploit classes reviewed

DOOM-family engines (Chocolate Doom, PrBoom+, ZDoom/GZDoom, Doomsday) have a
long history of memory-safety bugs reachable from untrusted WADs/demos. The
classes relevant to *this* feature area:

| Class | Upstream example | Applies here? |
|---|---|---|
| Sprite/patch column over-read | malformed patch `column_ofs` / missing 0xFF post terminator → OOB read in `R_DrawColumn` family | **Yes** — `render_draw_weapon` decodes a WAD patch. Mitigated (see below). |
| Hitscan / `P_LineAttack` global-state poisoning | crafted map manipulating the shared `bulletslope`/`linetarget` aim state | **No** — `player_fire_ray` is self-contained and side-effect-free; no shared aim globals. |
| Autoaim cone abuse (telefrag / wrong-target) | wide/odd autoaim cone hitting unintended actors | Low — cone is `dot>0` + lateral ≤ thing radius; bounded, deterministic, no Z exploit (engine is 2.5D, all things Z=0). |
| Projectile thinker exhaustion / DoS | unbounded missile spawns → allocator/thinker-list exhaustion | **Yes (new surface)** — addressed: spawns reuse spent slots and are hard-capped at `THING_MAX`. |
| Integer overflow in damage/distance math | large `dx/dy` products overflowing fixed-point | Reviewed — `fixed_mul` operands bounded by the `range` (≤ 2048<<16) check; max product ~2^43 ≪ i64. No overflow. |
| Negative/huge damage underflow | hp wrap, negative-modulo RNG | Reviewed — damage is `5 + p_random_range(N)` (bounded, non-negative); hp may go negative but is only compared, never indexed. |

## Findings & posture

1. **psprite decoder bounds** — `render_draw_weapon` carries the 0.28.0 F01
   hardening: column-directory bound (`8 + col*4 + 4 > psz`), `col_off >= psz`
   reject, post-walk `pend` bounds, and a `safety < 128` post cap. New fuzz
   target `fuzz/fuzz_weapon.cyr` drives the **real** decoder with malformed
   one-lump WADs (over-claimed lengths, offsets past the lump, missing
   terminators); **20,000 iterations clean**. `read_le32` column offsets are
   unsigned in Cyrius (`load8` zero-extends, `<<` is logical), so no
   sign-extension trapdoor (refuted during review).
2. **No line-of-sight bypass** — the 0.30.0 LOS check (`thing_check_sight`)
   closes the shoot-through-walls bug; it is a read-only geometry query with no
   shared state, so it adds no new surface.
3. **Projectile DoS** — `thing_spawn_missile` reuses spent `CAT_PROJECTILE`
   slots and refuses to grow past `THING_MAX` (512). `thing_missile_tick` has a
   `MISSILE_LIFETIME` cap (100 tics) so a missile can never loop forever.
4. **Splash recursion** — `thing_explode` → `thing_damage` → (barrel) →
   `thing_explode` is bounded: the `STATE_DIE`/`STATE_DEAD` guard at the top of
   `thing_damage` stops a barrel detonating twice, so recursion depth ≤ the
   chain length (small, map-bounded).
5. **No floating point, `asr` on signed shifts** — verified across the new code;
   the only right-shifts on signed values (`asr(rng_state,16)`,
   `asr(map_sector_light,3)`) use `asr`.

## Residual risk / follow-ups

- Missile-vs-wall reuses `player_check_position` (player radius + step-height),
  a behavioural approximation, not a security issue.
- PWAD support remains the main future attack surface; the psprite decoder is
  now fuzzed, but sprite/flat/texture decoders should get parallel
  `fuzz_*` targets when PWAD loading lands.

**Verdict**: no memory-safety defects found in the 0.30.0 shooting path; the new
projectile/splash surface is bounded against exhaustion and the psprite decoder
is fuzz-clean. Cross-reference: `docs/audit/2026-04-13-security-cve-audit.md`,
`docs/audit/2026-06-07-v0.28-graphics-hardening.md` (F01/F02/F03 patch hardening).
