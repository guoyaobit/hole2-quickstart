Overview

This repository provides tools to run the HOLE pipeline on PDB files and preview results in a Jupyter notebook.

Quick options

- Recommended (Conda): create a conda environment and install hole2 from conda-forge (preferred):

```bash
conda create -n hole2 python=3.11 -y
conda activate hole2
conda install matplotlib pandas ipywidgets -y
conda install -c conda-forge hole2
```

- Docker (local / CI): a Dockerfile and docker-compose.yml are included for containerized runs. This is useful if you don't want to install HOLE locally or prefer reproducible environments.

  docker compose up --build
  # Open http://localhost:8888 (Jupyter Lab) and open run.ipynb

HOLE installation

The preferred way to install the HOLE toolchain is via conda (conda-forge). The script install_hole.sh is kept as an alternative for systems without conda; it downloads the HOLE tarball and installs it under the user's home directory. Use one approach only — you do not need both.

Usage (Jupyter notebook)

1. Put your .pdb files in the repo root directory.
2. Start Jupyter Lab and open run.ipynb (the containerized image also exposes Jupyter Lab on port 8888).
3. Run the cell to launch the interactive UI (it calls run_notebook.launch()).
4. Edit per-PDB CPOINT / CVECT values in the UI (saved in memory), then click "Process selected".

What the UI does

- Processes each selected PDB in its own folder using the HOLE pipeline.
- Generates hole_out.tsv per result and attempts to create hole_plot.png (matplotlib). If matplotlib is unavailable, a CSV fallback hole_plot_data.csv is written and previewed.
- Packs all result folders into a timestamped .zip and shows its path.

Notes

- Docker image contains the HOLE toolchain installed under /root/hole2 and exposes Jupyter Lab on port 8888.
- CI workflow builds and pushes a container image to ghcr.io/${{ github.repository }}:latest (see .github/workflows/docker-image.yml).

Using the GHCR image

Pull the latest image from GitHub Container Registry:

```bash
docker pull ghcr.io/guoyaobit/hole2-quickstart:latest
```

Run Jupyter Lab (maps current dir, exposes Jupyter Lab on 8888):

```bash
# Linux / macOS
docker run --rm -p 8888:8888 -v "$(pwd)":/app ghcr.io/guoyaobit/hole2-quickstart:latest

# Windows (PowerShell)
docker run --rm -p 8888:8888 -v "${PWD}:/app" ghcr.io/guoyaobit/hole2-quickstart:latest
```

Run the processing script headless (process PDBs in the repo root and produce results):

```bash
docker run --rm -v "$(pwd)":/app -w /app ghcr.io/guoyaobit/hole2-quickstart:latest python run_holeprogram.py
```

Notes on authentication

- Public images: no login required.
- Private images: login with a PAT that has packages:read scope:

```bash
echo "YOUR_PAT" | docker login ghcr.io -u YOUR_GH_USERNAME --password-stdin
```

Tips

- The HOLE binaries are installed at /root/hole2/exe inside the container and are on PATH.
- To run containers as your local user (avoid file permission issues), add `-u $(id -u):$(id -g)` on Linux.
- Use the included docker-compose.yml for local development: `docker compose up --build`.
- To run a detached container: `docker run -d --name hole2 -p 8888:8888 -v "$(pwd)":/app ghcr.io/guoyaobit/hole2-quickstart:latest`.
- For versioned images, CI can tag images by git tag (see workflow) — otherwise `:latest` is used.