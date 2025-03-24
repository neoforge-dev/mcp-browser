#!/bin/bash
#
# MCP Browser Installation Helper
# This script ensures proper line endings for the one-line installer

set -e

# Configuration
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/neoforge-dev/mcp-browser/main/install_one_line.sh"
INSTALLER_FILE="/tmp/mcp_fixed_installer.sh"
MCP_INSTALLER="/tmp/install_mcp_browser.sh"

# Show banner
echo "========================================"
echo "  MCP Browser Installation Helper"
echo "========================================"
echo ""
echo "This will download and prepare the installer with"
echo "correct line endings to avoid common errors."
echo ""

# Download and fix line endings
echo "Downloading installer..."
curl -sSL "$INSTALL_SCRIPT_URL" | tr -d '\r' > "$INSTALLER_FILE"
chmod +x "$INSTALLER_FILE"

echo "Installer prepared successfully!"

# Run the one-line installer to download the main installer
"$INSTALLER_FILE" &
pid=$!

# Wait for the main installer to be downloaded
max_wait=30
count=0
while [ ! -f "$MCP_INSTALLER" ] && [ $count -lt $max_wait ]; do
  sleep 1
  count=$((count + 1))
done

if [ -f "$MCP_INSTALLER" ]; then
  # Kill the one-line installer process
  kill $pid 2>/dev/null || true
  
  # Fix the XQuartz path in the main installer
  echo "Fixing paths in the installer..."
  sed -i '' 's|open -a XQuartz|open "/Applications/Utilities/XQuartz.app"|g' "$MCP_INSTALLER"
  
  # Run the fixed main installer
  echo "Running the fixed installer..."
  chmod +x "$MCP_INSTALLER"
  "$MCP_INSTALLER"
else
  echo "Timed out waiting for the main installer to download."
  echo "Continuing with the original installer..."
  wait $pid
fi

# Clean up
rm -f "$INSTALLER_FILE" "$MCP_INSTALLER" 2>/dev/null || true

echo "Installation complete!" 