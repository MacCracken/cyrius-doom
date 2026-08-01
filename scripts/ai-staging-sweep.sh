#!/bin/sh
# ai-staging-sweep.sh — find --ai-at staging points that actually exercise the
# behaviour you intend to gate, and rank them.
#
# WHY THIS EXISTS: the v0.35.1 roadmap recorded "E1M1 move_blocked=247 over 350
# ticks" as F331-4's symptom. No fingerprint was ever committed, so that figure
# was prose — and at the coordinates the v0.35.0 CHANGELOG recorded, E1M1
# actually measures move_blocked=0. A gate staged there would have measured
# nothing at all. Run this FIRST when adding a behaviour gate, and record the
# staging you pick alongside the numbers.
#
# Usage: sh scripts/ai-staging-sweep.sh build/doom wad/DOOM1.WAD
# stage_sweep.sh <doom> <wad> — find staging points that actually produce a
# chase, and rank them by move_blocked. The roadmap's "E1M1 move_blocked=247"
# does not reproduce at the coordinates recorded in the v0.35.0 CHANGELOG, so
# the F331-4 gate needs a staging that demonstrably exercises blocked movement.
#
# Strategy: stage the player a short distance from each monster's own spawn
# position (guaranteeing LOS and engagement), 350 ticks, and report the
# fingerprint. Offsets keep the player out of melee-lock at tick 0.
BIN="$1"; WAD="$2"
for m in E1M1 E1M2 E1M3 E1M4 E1M5 E1M6 E1M7 E1M8 E1M9; do
  # monster positions straight from the probe's own census
  "$BIN" "$WAD" "$m" --ai-probe 1 2>&1 | grep "^AI mon" | awk '{print $5}' | tr ',' ' ' | while read mx my; do
    for dx in 0 192 -192; do
      px=$((mx + dx))
      out=$("$BIN" "$WAD" "$m" --ai-at "$px" "$my" --ai-probe 350 2>&1 | grep "^AI wakes")
      blk=$(echo "$out" | sed 's/.*move_blocked=\([0-9]*\).*/\1/')
      chs=$(echo "$out" | sed 's/.*chases=\([0-9]*\).*/\1/')
      if [ "${blk:-0}" -gt 0 ]; then
        echo "$blk $m $px $my chases=$chs | $out"
      fi
    done
  done
done | sort -rn | head -25
