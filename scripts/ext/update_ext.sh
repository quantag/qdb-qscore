#!/bin/bash
# Usage: ./update_extension.sh quantagitsolutionsgmbh.openqasm-debug-0.93.0.vsix

set -e  # exit on error

EXT_DIR="/usr/local/share/code-server/extensions"
EXT_NAME="quantagitsolutionsgmbh.openqasm-debug"

if [ $# -ne 1 ]; then
  echo "Usage: $0 <extension.vsix>"
  exit 1
fi

VSIX_FILE="$1"

# Check if file exists
if [ ! -f "$VSIX_FILE" ]; then
  echo "Error: File '$VSIX_FILE' not found."
  exit 1
fi

echo "Removing old versions of $EXT_NAME..."
sudo rm -rf "$EXT_DIR"/$EXT_NAME-*

echo "Installing new version from $VSIX_FILE..."
sudo code-server --install-extension "$VSIX_FILE" --extensions-dir "$EXT_DIR"

echo "Done. Installed: $VSIX_FILE"
