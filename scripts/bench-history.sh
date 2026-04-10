#!/bin/sh
# Record benchmark results to CSV for tracking over time
# Usage: sh scripts/bench-history.sh [wad_path]
set -e

WAD="${1:-wad/DOOM1.WAD}"
CSV="bench-history.csv"
BUILD="build/bench_doom"

if [ ! -f "$WAD" ]; then
    echo "WAD not found: $WAD"
    echo "Run: sh scripts/get-wad.sh wad"
    exit 1
fi

# Build benchmark
cat benches/doom.bcyr | cc3 > "$BUILD" 2>/dev/null
chmod +x "$BUILD"

# Run and capture output
OUTPUT=$("$BUILD" "$WAD" 2>&1)

# Parse results
VERSION=$(cat VERSION | tr -d '[:space:]')
DATE=$(date +%Y-%m-%d)
BINARY_SIZE=$(wc -c < build/doom 2>/dev/null || echo 0)

# Create CSV header if needed
if [ ! -f "$CSV" ]; then
    echo "date,version,binary_bytes,render_frame,render_sprites,fixed_mul,texture_get_col,pcache_hit" > "$CSV"
fi

# Extract key metrics (avg time as string)
extract_avg() { echo "$OUTPUT" | grep "  $1:" | sed 's/.*: \([^ ]*\) avg.*/\1/'; }
render_avg=$(extract_avg "render_frame")
sprites_avg=$(extract_avg "render_frame+sprites")
mul_avg=$(extract_avg "fixed_mul")
texcol_avg=$(extract_avg "texture_get_column")
pcache_avg=$(extract_avg "pcache_get_hit")

echo "$DATE,$VERSION,$BINARY_SIZE,$render_avg,$sprites_avg,$mul_avg,$texcol_avg,$pcache_avg" >> "$CSV"

echo "=== Recorded to $CSV ==="
echo "  version:      $VERSION"
echo "  binary:       $BINARY_SIZE bytes"
echo "  render_frame: $render_avg"
echo "  +sprites:     $sprites_avg"
echo "  fixed_mul:    $mul_avg"
echo "  tex_get_col:  $texcol_avg"
echo "  pcache_hit:   $pcache_avg"
