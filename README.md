hole2-quickstart — Reproducible HOLE pipeline and Jupyter-based analysis

Abstract

hole2-quickstart provides a compact, reproducible environment for running the HOLE pore-analysis pipeline on biomolecular structures (PDB). It combines the HOLE toolchain with Python-based post-processing and a Jupyter Lab interface to make routine analyses, visualization, and batch processing straightforward and auditable.

Background and motivation

Automated pore profiling (HOLE) is widely used in structural biology to analyse ion channels and pores. However, installing HOLE, managing its binary dependencies, and integrating outputs into plotting and reporting workflows can be time-consuming. This project packages a reproducible Docker image, helper scripts, and a lightweight Jupyter-based UI to lower the barrier for reproducible HOLE analyses.

Key features

- Reproducible Docker image containing HOLE and Python tooling (Jupyter Lab) for immediate use.
- run_holeprogram.py: a script to process multiple PDBs, generate hole_out.tsv and visualizations, and package outputs.
- pdb_params.yaml: persistent per-PDB configuration including a __config__ section for global settings (e.g., HOLE_ROOT).
- CI workflow that builds and publishes a GHCR image for reproducible deployment.

Installation

Two primary options are provided for users:

1. Docker (recommended for reproducibility)

Pull the container image from GHCR and run Jupyter Lab (maps current directory into /app):

```bash
docker pull ghcr.io/guoyaobit/hole2-quickstart:latest
docker run --rm -p 8888:8888 -v "$(pwd)":/app ghcr.io/guoyaobit/hole2-quickstart:latest
```

2. Native (Conda)

Create a conda environment and install HOLE from conda-forge when Docker cannot be used:

```bash
conda create -n hole2 python=3.11 -y
conda activate hole2
conda install matplotlib pandas ipywidgets -y
conda install -c conda-forge hole2
```

Usage

1. Place one or more .pdb files in the repository root.
2. Start Jupyter Lab (see above) and open run.ipynb.
3. Use the notebook UI to set per-PDB parameters (CPOINT, CVECT) and process selected entries.
4. For batch headless runs, use the command:

```bash
docker run --rm -v "$(pwd)":/app -w /app ghcr.io/guoyaobit/hole2-quickstart:latest python run_holeprogram.py
```

Configuration and reproducibility

- The script detects HOLE installation using (in order): HOLE_ROOT environment variable, the __config__.HOLE_ROOT entry in pdb_params.yaml, several common install locations, and a default fallback.
- To persist configuration for the repository, edit pdb_params.yaml and add a top-level __config__ section, for example:

```yaml
__config__:
  HOLE_ROOT: /root/hole2
```

- The Docker image includes HOLE at /root/hole2 (or the location set in HOLE_ROOT) to simplify container runs.

Citation

If you use this software in a publication, please cite the repository (see CITATION.cff) and include the GHCR image tag used for reproducibility.

Example

```bash
# Pull image and start Jupyter Lab
docker pull ghcr.io/guoyaobit/hole2-quickstart:latest
docker run --rm -p 8888:8888 -v "$(pwd)":/app ghcr.io/guoyaobit/hole2-quickstart:latest
# Open run.ipynb in Jupyter Lab and run the analysis.
```

Acknowledgements

This project packages the HOLE toolset and Python analysis code into a reproducible environment. Thanks to contributors and the broader open-source ecosystem for tools and libraries used here.

License

See the LICENSE file for license details.

Contact

Repository: https://github.com/guoyaobit/hole2-quickstart
