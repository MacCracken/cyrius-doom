#!/bin/sh
# Run DOOM
# Usage: sh scripts/run.sh [mapname]
set -e

# Download WAD if not present
sh scripts/get-wad.sh wad

# Build
mkdir -p build
cat src/main.cyr | cc2 > build/doom 2>/dev/null
chmod +x build/doom

# Run
MAP="${1:-E1M1}"
exec ./build/doom wad/DOOM1.WAD "$MAP"
