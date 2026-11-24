# HOLE2 Quickstart

Batch-process PDB structures with HOLE2 and inspect pore-radius profiles in Jupyter. The notebook provides per-file parameter editing, parallel processing, raw-result archives, and plot previews.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/guoyaobit/hole2-quickstart/blob/main/colab.ipynb)

## Google Colab

Open the badge above and use a standard **CPU** runtime. Run the cells in order:

1. Clone the code and install HOLE 2.3.1. The installer verifies the micromamba 2.10.0 download, installs only HOLE's native toolchain, and keeps Colab's existing Python kernel.
2. Upload PDB files, or optionally authorize a Google Drive mount and import PDBs from a folder there.
3. Edit the per-file `parameters` dictionary and `selected_files` list in the notebook. Parameter keys must match the imported filenames shown by the upload cell.
4. Run the batch and inspect the radius plots.
5. Download the raw-result ZIP, or optionally export the ZIP and separate PNG/CSV plots to Google Drive.

Inputs and results use `/content/hole2-data`, separate from the cloned code. Imports normalize PDB filenames to simple ASCII names and add suffixes on collision; existing uploads and result folders are preserved. Colab processing is sequential. It uses standard notebook cells and Colab's upload/download controls rather than the desktop ipywidgets editor.

The raw ZIP is created **before plotting**, as in the desktop notebook. It excludes the plots generated afterward. Drive export saves that ZIP plus the separate plots in a new directory. A plot error does not remove the raw ZIP.

Runtime files and parameter values are temporary. Download or export results before the runtime is deleted. Save a notebook copy to retain edited parameter code. Each fresh runtime must rerun setup. Setup reuses an existing code clone and HOLE installation; to fetch application updates, start a fresh runtime and reopen the Colab notebook. A GPU is not needed by this pipeline.

The Colab installer targets Linux x86_64 and requires network access to GitHub and conda-forge. CI checks the notebook's Python cells and tests the installer and full HOLE pipeline on an upstream gramicidin example under Linux/Python 3.12. Browser uploads, Drive authorization, and the Google-managed Colab runtime still require an interactive Colab check.

## Requirements and installation

Use Linux, or WSL with the Jupyter kernel running inside WSL. Python 3.11 or later and conda are recommended.

```bash
git clone https://github.com/guoyaobit/hole2-quickstart.git
cd hole2-quickstart
conda create -n hole2 python=3.11 -y
conda activate hole2
conda install -c conda-forge hole2 matplotlib pandas ipywidgets jupyterlab -y
command -v hole sph_process qpt_conv sos_triangle
```

All four executables must be available in `PATH`. A standalone HOLE2 installation also works if its executables and radius data are available. Native Windows toolchain support is not provided.

`pexpect` is not required: input is passed directly to `qpt_conv`. The notebook requires pandas and ipywidgets. If matplotlib cannot be imported, plotting falls back to CSV.

## Docker deployment and updates

Docker packages the Linux HOLE toolchain and the notebook dependencies together. Use Docker Engine with Compose on Linux, or Docker Desktop in Linux-container mode on Windows/macOS. The default target is `linux/amd64`; set `HOLE_PLATFORM=linux/arm64` to attempt an ARM build (not validated here).

### First deployment

Clone the repository and run these commands from its root. On Linux/WSL:

```bash
mkdir -p data
cp .env.example .env
```

Edit `.env`, setting `HOLE_UID` and `HOLE_GID` to the output of `id -u` and `id -g`. Use a non-root account that owns the data directory. On Windows PowerShell with Docker Desktop, create `data` with `New-Item -ItemType Directory -Force data` and copy the example using `Copy-Item .env.example .env`; the default UID/GID can generally be used for Docker Desktop bind mounts.

```bash
docker compose config --quiet
docker compose build --pull
docker compose up -d --wait --wait-timeout 120
docker compose logs hole2
```

Open `http://127.0.0.1:8888/lab/tree/run.ipynb` and log in using the token printed in the container logs. Authentication remains enabled. If `HOLE_PORT` is changed, use that host port in the URL. Put your PDB files in `data/`, open `run.ipynb`, and run its launcher cell.

The container runs as a non-root user. The host data directory must already exist and be writable by the configured UID/GID; otherwise startup fails with a permissions error.

| Setting in `.env` | Default | Purpose |
| --- | --- | --- |
| `HOLE_DATA_DIR` | `./data` | Host directory mounted read/write at `/data` |
| `HOLE_PORT` | `8888` | Host port, bound to `127.0.0.1` |
| `HOLE_UID`, `HOLE_GID` | `57439` | Container user and group IDs |
| `HOLE_IMAGE_TAG` | `local` | Tag of the locally built application image |
| `HOLE_PLATFORM` | `linux/amd64` | Container platform |

Application modules are built into `/opt/hole2`, while `/data` contains the PDB files, result folders, ZIP files, plots, and an initial notebook copy. The input working directory is `/data`. Image rebuilds do not replace data or an existing `run.ipynb`; the existing launcher imports the updated modules from the image. Notebook parameters remain in memory and are lost when the container/kernel restarts.

### Update application code

Finish processing before updating: recreating the service stops its active kernel and any running batch. Back up `data/` as needed, then:

```bash
git pull --ff-only
docker compose build --pull
docker compose up -d --no-build --force-recreate --wait --wait-timeout 120
```

Reopen the notebook and run its launcher cell again. A restart alone does not load updated code into the image; rebuild and recreate the service. `docker compose pull` does not update this application because no prebuilt registry image is published by this repository.

To refresh the conda dependencies as well, change `environment.yml` and rebuild with `docker compose build --pull --no-cache`. Python and HOLE versions are fixed in that file; the other packages are constrained to major versions, not a complete dependency lock.

### Roll back an image

Before rebuilding, preserve the working image (the example assumes `HOLE_IMAGE_TAG=local`):

```bash
docker image tag hole2-quickstart:local hole2-quickstart:rollback
```

To restore it, set `HOLE_IMAGE_TAG=rollback` in `.env` and run:

```bash
docker compose up -d --no-build --force-recreate --wait --wait-timeout 120
```

This restores application code and dependencies; it does not restore earlier data contents. Set the tag back to `local` before the next normal build.

### Operations and checks

```bash
docker compose ps
docker compose logs --tail=100 hole2
docker compose exec hole2 python /opt/hole2/docker/check_environment.py
docker compose exec hole2 python -m unittest discover -s /opt/hole2/tests -v
docker compose run --rm --no-deps hole2 python /opt/hole2/run_holeprogram.py
docker compose down
```

The one-off `run` command processes all PDB files in `data/` with default parameters and creates a ZIP without plots. Run it when the notebook is idle. `down` removes the service container and network; the bind-mounted host data remains.

Image builds check the four executables and radius data and run the regression suite with notebook dependencies installed. The GitHub Actions Docker workflow also starts Jupyter, checks health, and recreates the container to check data persistence. It does not publish images or establish scientific correctness of real PDB outputs.

## Radius data

HOLE requires a van der Waals radius file, usually `simple.rad`. The wrapper searches in this order:

1. `HOLE_RADIUS`, if set. An invalid explicit path raises an error instead of falling back.
2. The installation prefix inferred from `hole`, followed by `CONDA_PREFIX` and the Python environment prefix. Common `rad` and `share` locations are checked, including a search for `simple.rad` under each prefix's `share` directory.
3. `~/hole2/rad/simple.rad`.

To select a file explicitly, set an absolute path before processing:

```bash
export HOLE_RADIUS=/absolute/path/to/simple.rad
jupyter lab run.ipynb
```

Alternatively, set it in a notebook cell before processing:

```python
import os
os.environ['HOLE_RADIUS'] = '/absolute/path/to/simple.rad'
```

## Notebook workflow

1. Place files with the lowercase `.pdb` extension in the repository root.
2. From that directory, activate the environment and launch the notebook:

   ```bash
   conda activate hole2
   jupyter lab run.ipynb
   ```

3. Run the notebook cell to launch the interface.
4. Choose a PDB in the parameter editor, enter optional `CPOINT` and `CVECT` values, and click **Save**. Repeat for other files as needed.
5. Select files in **To process** and click **Process selected**. All discovered files are selected initially.
6. Inspect the result folders, ZIP path, and plot previews below the interface.

Parameters are held in kernel memory only. **Save** does not write a configuration file; restarting the kernel loses those edits. The supplied `pdb_params.yaml` is an example and is not loaded by the current implementation.

**Refresh PDB list** updates both file selectors and reloads the parameter fields. The current editing selection is retained if its file still exists; an empty directory clears the selection and fields. **Clear** removes the selected file's saved parameters and clears both input fields.

### Parameters

| Parameter | Meaning | Accepted value |
| --- | --- | --- |
| `CPOINT` | Starting point for the channel search | Three finite numbers, such as `124.459, 125.13, 127.348` |
| `CVECT` | Channel search direction | Three finite numbers forming a nonzero vector, such as `0, 0, 1` |

Comma-separated and space-separated inputs are accepted. Leave an input blank to omit that card and use HOLE's default behavior. Validation runs when processing starts.

The generated input fixes `ENDRAD` at `5.0` Angstroms and surface dot density at `15`.

## Processing and outputs

Each PDB is processed in its own folder. For `sample.pdb`, the first run uses `sample/`. If that path exists, a new folder such as `sample_<unique_suffix>/` is created. Existing results are preserved, including when a later run fails.

Multiple PDBs use a process pool with a worker count defaulting to the smaller of the file count and CPU count. The notebook callback waits for the batch to finish.

| Output | Contents |
| --- | --- |
| Input PDB copy | Structure used by the run |
| `hole.inp` | Generated HOLE control cards |
| `hole_out.txt` | HOLE standard output, including the profile table |
| `hole_out.tsv` | Sampled and midpoint profile rows; whitespace-separated |
| `hole_out.sph` | Sphere-center and radius data |
| `dotsurface.qpt` | Dot surface generated by `sph_process` |
| `dotsurface.vmd_plot` | Dot surface converted for VMD |
| `solid_surface.sos` | Intermediate solid-surface data |
| `solid_surface.vmd_plot` | Triangulated surface for VMD |
| `*.log` | Standard-output and standard-error logs from external tools |
| `hole_plot.png` | Pore-radius plot generated after archiving |
| `hole_plot_data.csv` | Fallback when matplotlib cannot be imported |

### Archive order

**The notebook creates the ZIP before generating plots.**

After all selected PDBs finish processing, their folders are packed into a timestamped ZIP in the input directory. Plotting then saves PNG or fallback CSV files in those folders. The ZIP intentionally excludes the plots generated afterward.

Automatic ZIP names include microseconds and gain a numeric suffix if a name already exists. Existing archives are never overwritten. Passing an explicit existing `out_name` to `make_zip_for_folders()` raises `FileExistsError`.

### Plot interpretation

| HOLE profile column | Meaning | Plot use |
| --- | --- | --- |
| 1 | Channel coordinate: sphere-center projection along the channel direction | Horizontal axis, in Angstroms |
| 2 | Pore radius | Vertical axis, in Angstroms |
| 3 | Center-line distance coordinate | Not used by the current plot |
| 4 | Cumulative quantity used for conductance estimation | Not used by the current plot |

Column 1 already contains HOLE's channel projection. The wrapper does not apply `CVECT` to it again.

## Command-line and Python use

Process all PDB files in the current directory and archive the results:

```bash
python run_holeprogram.py
```

The command-line entry point uses default HOLE parameters and does not generate plots. For explicit parameters, worker control, or plotting, use the Python API:

```python
import run_holeprogram as rh

rh.save_pdb_params({'sample.pdb': {'CVECT': [0, 0, 1]}})
folders = rh.process_pdbs(['sample.pdb'], workers=1)
archive = rh.make_zip_for_folders(folders)  # Archive before plotting.
for folder in folders:
    rh.plot_tsv(folder)
print(archive)
```

The input directory is captured when `run_holeprogram` is imported. Start the notebook or Python process in the directory containing the PDB files.

## Troubleshooting

| Message or behavior | Action |
| --- | --- |
| `Required executable not found in PATH` | Activate the HOLE environment and check all four executable paths. |
| `Cannot find simple.rad` | Set `HOLE_RADIUS` to the full path of an existing radius file. |
| Invalid `CPOINT` or `CVECT` | Supply three finite numbers; the direction vector must be nonzero. |
| A tool failed or timed out | Inspect the output and stderr logs identified by the error. Each external command has a 600-second timeout. |
| `qpt_conv produced no VMD file` | Inspect `qpt_conv.log` and `qpt_conv.stderr.log` in the new result folder. |
| No profile rows or invalid profile data | Inspect `hole_out.txt`, `hole.stderr.log`, and `hole.inp`. |
| Plot warning after processing | Raw results have already been archived. Inspect the displayed traceback and profile data. |
| A batch stops after one PDB fails | Inspect that run's logs. Successful folders may remain, but archive creation does not proceed. |
| Parameters disappear after a kernel restart | Re-enter and save them; persistence is in memory only. |

## Regression checks

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests simulate external commands and cover profile parsing, radius-file discovery, parameter validation, failure and timeout reporting, preservation of previous results, missing conversion output, and ZIP-before-plot behavior. They do not require HOLE and do not replace an end-to-end run with the real toolchain.

Archive tests also verify that name collisions preserve existing ZIP files. Notebook tests exercise real ipywidgets callbacks for refresh and Clear/Save; install the notebook dependencies above to run them. Those UI tests are skipped when the dependencies are unavailable.
