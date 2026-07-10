#!/usr/bin/env bash
set -euo pipefail

# install_hole.sh: Alternative installer for HOLE when conda is not available.
# Recommended: use the conda install (see README). This script downloads
# the HOLE tarball and extracts it into the current user's home directory.

TARBALL_URL="http://www.holeprogram.org/downloads/2.2.005/hole2-ApacheLicense-2.2.005-Linux-x86_64.tar.gz"
OUT="/tmp/hole2.tar.gz"

echo "Downloading HOLE from ${TARBALL_URL}..."
wget -O "${OUT}" "${TARBALL_URL}"

echo "Extracting to ~/hole2..."
mkdir -p "$HOME/hole2"
# the tarball contains a top-level folder; extract into $HOME and ensure exe in PATH
tar xf "${OUT}" -C "$HOME"
rm -f "${OUT}"

if ! grep -q "~/hole2/exe" "$HOME/.bashrc" 2>/dev/null; then
  echo "PATH=\$PATH:~/hole2/exe" >> "$HOME/.bashrc"
  echo "Added ~/hole2/exe to ~/.bashrc PATH"
else
  echo "~/hole2/exe already in ~/.bashrc"
fi

echo "HOLE installation complete. Start a new shell or source ~/.bashrc to update PATH."