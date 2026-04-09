#!/bin/sh
# Download DOOM1.WAD (shareware) for testing
# Source: https://github.com/nneonneo/universal-doom
set -e

WAD_DIR="${1:-wad}"
WAD_FILE="$WAD_DIR/DOOM1.WAD"
WAD_URL="https://raw.githubusercontent.com/nneonneo/universal-doom/main/DOOM1.WAD"

if [ -f "$WAD_FILE" ]; then
    echo "DOOM1.WAD already present ($WAD_FILE)"
    exit 0
fi

mkdir -p "$WAD_DIR"
echo "Downloading DOOM1.WAD (shareware)..."
curl -sLo "$WAD_FILE" "$WAD_URL"
SIZE=$(wc -c < "$WAD_FILE")
echo "DOOM1.WAD: $SIZE bytes -> $WAD_FILE"
