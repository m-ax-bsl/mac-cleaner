#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="/usr/local/bin/mac-cleaner"

if [ ! -d /usr/local/bin ]; then
    sudo mkdir -p /usr/local/bin
fi

ln -sf "$SCRIPT_DIR/cleaner.py" "$TARGET"
echo "Installiert: mac-cleaner -> $TARGET"
echo "Starte mit: mac-cleaner"
