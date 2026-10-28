- Miniconda / conda (recommended)
- Python packages: matplotlib, pandas, ipywidgets, Jupyter
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
- Packs raw result folders into a timestamped .zip before plotting. The archive intentionally excludes the plots generated afterward.
- Plots HOLE profile column 1 (channel coordinate) against column 2 (pore radius), both in Angstroms.
- Repeated runs preserve existing output folders and use a unique suffix for new results.
- All four tools must be in PATH: hole, sph_process, qpt_conv, sos_triangle. Commands have a 600-second timeout; errors identify the output and stderr logs in the result folder. qpt_conv does not require pexpect.
- Radius data is discovered from the executable's installation prefix, the active conda/Python prefix, or ~/hole2/rad/simple.rad. To select a specific file, set HOLE_RADIUS to the full path of simple.rad before processing, for example in a notebook:

```python
import os
os.environ['HOLE_RADIUS'] = '/path/to/simple.rad'
```

The supported toolchain environment is Linux (including WSL with the notebook kernel running in WSL). No native Windows toolchain support is implied.

Run regression checks without installing HOLE:

```sh
python -m unittest discover -s tests -v
```

=======
- HOLE toolchain installed and in PATH (hole, sph_process, qpt_conv, sos_triangle)
- Miniconda / conda (recommended)
- Python packages: matplotlib, pandas, ipywidgets, Jupyter

Setup (conda)
1. conda create -n hole2 python=3.11 -y
2. conda activate hole2
3. conda install matplotlib pandas ipywidgets -y

Usage (Jupyter notebook)
1. Put your .pdb files in the repo root directory.
2. Start Jupyter and open run.ipynb.
3. Run the cell to launch the interactive UI (it calls run_notebook.launch()).
4. Edit per-PDB CPOINT / CVECT values in the UI (saved in memory), then click "Process selected".

What the UI does
- Processes each selected PDB in its own folder using the HOLE pipeline.
- Generates hole_out.tsv per result and attempts to create hole_plot.png (matplotlib). If matplotlib is unavailable, a CSV fallback hole_plot_data.csv is written and previewed.
- Packs raw results before plotting; generated plots remain in the result folders and are not included in that archive.
