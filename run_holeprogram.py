import os
import subprocess
import shutil
import sys
import math
import tempfile
from pathlib import Path
try:
    import yaml
except Exception:
    yaml = None
# from multiprocessing import Pool

def resolve_radius_file():
    """Find the radius data in an explicit, conda, or standalone installation."""
    explicit = os.environ.get('HOLE_RADIUS')
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f'HOLE_RADIUS is not a file: {path}')
        return path

    prefixes = [Path(sys.prefix)]
    if os.environ.get('CONDA_PREFIX'):
        prefixes.insert(0, Path(os.environ['CONDA_PREFIX']))
    executable = shutil.which('hole')
    if executable:
        prefixes.insert(0, Path(executable).resolve().parent.parent)
    for prefix in prefixes:
        for relative in ('share/hole2/rad/simple.rad', 'share/hole2/simple.rad',
                         'share/hole/rad/simple.rad', 'rad/simple.rad'):
            path = prefix / relative
            if path.is_file():
                return path.resolve()
        share = prefix / 'share'
        if share.is_dir():
            for path in sorted(share.rglob('simple.rad')):
                if path.is_file():
                    return path.resolve()
    path = Path.home() / 'hole2' / 'rad' / 'simple.rad'
    if path.is_file():
        return path.resolve()
    raise FileNotFoundError('Cannot find simple.rad; set HOLE_RADIUS to its full path.')


def validate_params(params):
    result = {}
    for key in ('CPOINT', 'CVECT'):
        value = params.get(key)
        if value is None:
            continue
        try:
            if isinstance(value, (str, bytes)) or len(value) != 3:
                raise ValueError()
            vector = [float(x) for x in value]
            if not all(math.isfinite(x) for x in vector):
                raise ValueError()
            if key == 'CVECT' and not any(vector):
                raise ValueError()
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f'{key} must contain three finite numbers; CVECT must be nonzero') from exc
        result[key] = vector
    return result


def run_hole(m_pdb, params=None):
    """Process one PDB, preserving previous results in an existing folder.

    A unique suffix is used on reruns. Returns the new result folder on success.
    """
    params = validate_params(params or {})
    if os.path.basename(m_pdb) != m_pdb or not m_pdb.endswith('.pdb'):
        raise ValueError('Expected a .pdb filename in the input directory')
    src = os.path.join(current_path, m_pdb)
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    executables = {}
    for name in ('hole', 'sph_process', 'qpt_conv', 'sos_triangle'):
        executables[name] = shutil.which(name)
        if executables[name] is None:
            raise FileNotFoundError(f'Required executable not found in PATH: {name}')
    radius_file = resolve_radius_file()
    foldername = os.path.splitext(m_pdb)[0]
    folderpath = os.path.join(current_path, foldername)
    try:
        os.mkdir(folderpath)
    except FileExistsError:
        folderpath = tempfile.mkdtemp(prefix=foldername + '_', dir=current_path)

    # copy pdb into folder
    src = os.path.join(current_path, m_pdb)
    dst = os.path.join(folderpath, os.path.basename(m_pdb))
    shutil.copy(src, dst)

    # write hole.inp
    inp_path = os.path.join(folderpath, "hole.inp")
    with open(inp_path, "w") as file:
        file.write(f"coord {os.path.basename(m_pdb)}\n")
        file.write(f"radius {radius_file}\n")
        file.write("sphpdb hole_out.sph\n")
        file.write("endrad 5.\n")
        # optional per-pdb parameters
        cpoint = params.get("CPOINT")
        if cpoint:
            file.write("CPOINT " + " ".join(map(str, cpoint)) + "\n")
        cvect = params.get("CVECT")
        if cvect:
            file.write("CVECT " + " ".join(map(str, cvect)) + "\n")

    # run commands with working directory set to folderpath
    def run(name, args=(), input_text='', output=None):
        log_path = os.path.join(folderpath, output or name + '.log')
        error_path = os.path.join(folderpath, name + '.stderr.log')
        with open(log_path, 'w') as log, open(error_path, 'w') as errors:
            try:
                subprocess.run([executables[name], *args], input=input_text,
                               stdout=log, stderr=errors, check=True,
                               text=True, cwd=folderpath, timeout=600)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f'{name} failed or timed out; see {log_path} and {error_path}') from exc

    with open(inp_path) as file:
        run('hole', input_text=file.read(), output='hole_out.txt')
    with open(os.path.join(folderpath, 'hole_out.txt')) as source:
        rows = [line for line in source if 'mid-' in line or 'sampled' in line]
    if not rows:
        raise ValueError(f'No HOLE profile rows found; see {folderpath}/hole_out.txt')
    with open(os.path.join(folderpath, 'hole_out.tsv'), 'w') as file:
        file.writelines(rows)
    run('sph_process', ['-dotden', '15', '-color', 'hole_out.sph', 'dotsurface.qpt'])
    run('qpt_conv', input_text='D\ndotsurface.qpt\ndotsurface.vmd_plot\n1\n')
    if not os.path.isfile(os.path.join(folderpath, 'dotsurface.vmd_plot')):
        raise RuntimeError(f'qpt_conv produced no VMD file; see {folderpath}/qpt_conv.log')
    run('sph_process', ['-sos', '-dotden', '15', '-color', 'hole_out.sph', 'solid_surface.sos'])
    with open(os.path.join(folderpath, 'solid_surface.sos')) as file:
        run('sos_triangle', ['-s'], input_text=file.read(), output='solid_surface.vmd_plot')

    return folderpath

current_path = os.getcwd()
# load optional per-pdb parameter config (pdb_params.yaml)
config_path = os.path.join(current_path, "pdb_params.yaml")
pdb_params = {}

def save_pdb_params(params):
    """Store params dict in-memory only (no YAML file). Updates module-level pdb_params."""
    global pdb_params
    pdb_params = dict(params or {})
    return pdb_params


def load_pdb_params():
    """Initialize in-memory pdb_params based on current directory PDB files.

    Preserves existing values for matching filenames or basenames if present in the current in-memory pdb_params.
    """
    global pdb_params
    current = pdb_params if isinstance(pdb_params, dict) else {}
    files = list_pdb_files()
    new = {}
    for p in files:
        if p in current:
            new[p] = current[p]
        else:
            base = os.path.splitext(p)[0]
            if base in current:
                new[p] = current[base]
            else:
                new[p] = {}
    pdb_params = new
    return pdb_params


def list_pdb_files(dir_path=None):
    dir_path = dir_path or current_path
    return [f for f in os.listdir(dir_path) if f.endswith('.pdb')]

# helper to get params for a pdb (match by filename or basename)
def get_params_for(pdb_name):
    if pdb_name in pdb_params:
        return pdb_params[pdb_name]
    base = os.path.splitext(pdb_name)[0]
    return pdb_params.get(base, {})


def _run_pair(arg):
    """Helper for multiprocessing: arg = (pdb, params)"""
    pdb, params = arg
    return run_hole(pdb, params)


def process_pdbs(pdb_list, workers=None):
    """Process a list of pdb filenames (relative to current_path). Returns list of output folder paths.

    If workers is None, automatically choose min(len(pdb_list), cpu_count).
    If workers <= 1, processing is sequential to avoid multiprocessing overhead.
    """
    if not pdb_list:
        return []

    # auto-select workers if not provided
    if workers is None:
        try:
            cpu = os.cpu_count() or 1
        except Exception:
            cpu = 1
        workers = min(len(pdb_list), cpu)

    if workers and workers > 1:
        from multiprocessing import Pool
        args = [(pdb, get_params_for(pdb)) for pdb in pdb_list]
        with Pool(processes=workers) as pool:
            results = pool.map(_run_pair, args)
        return results

    # sequential fallback
    results = []
    for pdb in pdb_list:
        params = get_params_for(pdb)
        print(f"Processing {pdb} with params: {params}")
        folder = run_hole(pdb, params)
        results.append(folder)
    return results


def make_zip_for_folders(folders, out_name=None):
    """Create a zip containing the given folders. Returns zip path."""
    from datetime import datetime
    import zipfile
    if out_name is None:
        out_name = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.zip'
    out_path = os.path.join(current_path, out_name)
    with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for folder in folders:
            base = os.path.basename(folder)
            for root, dirs, files in os.walk(folder):
                for fn in files:
                    full = os.path.join(root, fn)
                    arc = os.path.join(base, os.path.relpath(full, folder))
                    zf.write(full, arc)
    return out_path


def plot_tsv(folderpath, cvect=None, out_name=None, show_plot=False):
    """Plot HOLE's channel coordinate (column 1) against radius (column 2).

    cvect is retained for API compatibility: HOLE already applies CVECT when
    producing column 1, so the profile must not be projected a second time.
    Returns the saved image/CSV path and the (coordinate, radius) arrays.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None

    tsv = os.path.join(folderpath, 'hole_out.tsv')
    xs, radii = [], []
    with open(tsv) as fh:
        for line_number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                fields = line.split()
                coordinate, radius = float(fields[0]), float(fields[1])
                if not math.isfinite(coordinate) or not math.isfinite(radius):
                    raise ValueError('non-finite profile value')
            except (ValueError, IndexError) as exc:
                raise ValueError(f'Invalid HOLE profile row at {tsv}:{line_number}') from exc
            xs.append(coordinate)
            radii.append(radius)
    if not xs:
        raise ValueError(f'No numeric data parsed from {tsv}')
    xlabel = 'Channel coordinate (Angstrom)'

    # plotting
    if out_name is None:
        out_name = 'hole_plot.png'
    out_path = os.path.join(folderpath, out_name)

    if plt is None:
        # matplotlib not available, write data as CSV for external plotting
        data_path = os.path.join(folderpath, 'hole_plot_data.csv')
        with open(data_path, 'w') as fh:
            fh.write('x,radius\n')
            for xi, ri in zip(xs, radii):
                fh.write(f"{xi},{ri}\n")
        return data_path, (xs, radii)

    plt.figure(figsize=(6,4))
    plt.plot(xs, radii, '-o')
    plt.xlabel(xlabel)
    plt.ylabel('Radius (Angstrom)')
    plt.title(os.path.basename(folderpath))
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    if show_plot:
        plt.show()
    plt.close()
    return out_path, (xs, radii)


if __name__ == '__main__':
    # default behavior: load params, list pdbs and process all
    load_pdb_params()
    pdb_files = list_pdb_files()
    print('Found PDBs:', pdb_files)
    folders = process_pdbs(pdb_files)
    zipfile = make_zip_for_folders(folders)
    print('Created zip:', zipfile)



    
