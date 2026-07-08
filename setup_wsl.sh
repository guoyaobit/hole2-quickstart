#!/usr/bin/env bash
set -euo pipefail

echo "=== Update apt and install system packages ==="
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential git curl

# Create or reuse virtualenv
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv .venv"
  python3 -m venv .venv
fi

# Activate venv for remainder of script
# Note: running this script with "source setup_wsl.sh" will keep the venv active in your shell.
source .venv/bin/activate

echo "Upgrading pip and installing Python packages..."
python -m pip install --upgrade pip
python -m pip install pyyaml pexpect ipywidgets pandas notebook ipykernel

# Enable ipywidgets nbextension (works for classic Notebook)
set +e
jupyter nbextension enable --py widgetsnbextension --sys-prefix
jupyter serverextension enable --py jupyter_nbextensions_configurator --sys-prefix 2>/dev/null || true
set -e

# Ensure kernel is available for notebook
python -m ipykernel install --user --name=project-venv --display-name="Python (project .venv)" || true

# Checkout feature branch if repo exists
if [ -d ".git" ]; then
  git fetch origin || true
  git checkout guoyaobit-add-pdb-params-per-file 2>/dev/null || git checkout -b guoyaobit-add-pdb-params-per-file origin/guoyaobit-add-pdb-params-per-file 2>/dev/null || true
fi

cat <<EOF

Setup complete.
To use:
  source .venv/bin/activate
  jupyter notebook --ip=0.0.0.0 --no-browser --port=8888

Notes:
- This script installs Python packages only. External binaries required by the project (hole, sph_process, qpt_conv, sos_triangle) must be installed separately and made available in PATH.
- If your network requires a proxy, export HTTP_PROXY/HTTPS_PROXY before running the script (e.g., export HTTPS_PROXY=http://127.0.0.1:7897).

EOF
