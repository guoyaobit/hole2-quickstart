# hole2-quickstart

A minimal helper to run the HOLE pipeline per-PDB with per-file parameters and an interactive Jupyter UI.

Requirements
- Miniconda / conda (recommended)
- Python packages: matplotlib, pandas, ipywidgets (pexpect optional for qpt_conv)
- HOLE toolchain (hole2) — available on conda-forge. Install via conda as below.

Install HOLE (conda-forge)

conda install -c conda-forge hole2

Setup (conda)
1. conda create -n hole2 python=3.11 -y
2. conda activate hole2
3. conda install matplotlib pandas ipywidgets -y
4. conda install -c conda-forge hole2

Usage (Jupyter notebook)
1. Put your .pdb files in the repo root directory.
2. Start Jupyter and open run.ipynb.
3. Run the cell to launch the interactive UI (it calls run_notebook.launch()).
4. Edit per-PDB CPOINT / CVECT values in the UI (saved in memory), then click "Process selected".

What the UI does
- Processes each selected PDB in its own folder using the HOLE pipeline.
- Generates hole_out.tsv per result and attempts to create hole_plot.png (matplotlib). If matplotlib is unavailable, a CSV fallback hole_plot_data.csv is written and previewed.
- Packs all result folders into a timestamped .zip and shows its path.

Notes
- Per-PDB params are stored in-memory (no persistent YAML writes) and are regenerated from current directory contents on launch.
- setup_wsl.sh has been removed; use conda/miniconda in WSL instead.

If you want CI-friendly or persistent config, consider adding a YAML save toggle; open an issue or PR for that feature.
