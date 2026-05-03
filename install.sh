#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
TARGET="$BIN_DIR/mac-cleaner"

mkdir -p "$BIN_DIR"
ln -sf "$SCRIPT_DIR/cleaner.py" "$TARGET"
echo "Installiert: $TARGET"

# ~/.local/bin in PATH eintragen falls noch nicht vorhanden
ZSHRC="$HOME/.zshrc"
if ! grep -q '.local/bin' "$ZSHRC" 2>/dev/null; then
    echo '\nexport PATH="$HOME/.local/bin:$PATH"' >> "$ZSHRC"
    echo "PATH aktualisiert in ~/.zshrc"
    echo "Fuehre aus: source ~/.zshrc"
else
    echo "Starte mit: mac-cleaner"
fi
