#!/bin/bash
#
# MCP Browser One-Line Installer Launcher
# Usage: curl -sSL https://raw.githubusercontent.com/neoforge-dev/mcp-browser/main/install_one_line.sh | bash

set -e

# Configuration variables
REPO="neoforge-dev/mcp-browser"
BRANCH="main"
INSTALLER_FILE="install_mcp_browser.sh"
GITHUB_RAW_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}/${INSTALLER_FILE}"

# Check if running on Mac
if [[ "$(uname)" != "Darwin" ]]; then
  echo "This installer is designed for macOS. Please run it on a Mac."
  exit 1
fi

# Show banner
echo "========================================"
echo "      MCP Browser One-Line Installer"
echo "========================================"
echo ""
echo "This will install MCP Browser on your Mac Mini"
echo "with visualization support for AI agents."
echo ""

# Ask for confirmation
read -p "Continue with installation? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Installation cancelled."
  exit 0
fi

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Download and run the installer
echo "Downloading and running MCP Browser installer..."
curl -sSL "$GITHUB_RAW_URL" -o /tmp/install_mcp_browser.sh
chmod +x /tmp/install_mcp_browser.sh

# Run the installer
/tmp/install_mcp_browser.sh

# Clean up
rm /tmp/install_mcp_browser.sh 