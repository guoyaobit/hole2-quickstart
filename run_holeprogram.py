import os
import subprocess
import shutil
try:
    import pexpect
except Exception:
    pexpect = None
try:
    import yaml
except Exception:
    yaml = None
# from multiprocessing import Pool
def run_hole(m_pdb, params=None):
    """Process a single PDB file. Creates a folder named after the pdb basename
    and runs the HOLE pipeline inside it. Returns the folder path on success."""
    if params is None:
        params = {}
    foldername = os.path.splitext(m_pdb)[0]
    folderpath = os.path.join(current_path, foldername)
    # ensure clean folder
    if os.path.exists(folderpath):
        shutil.rmtree(folderpath)
    os.mkdir(folderpath)

    # copy pdb into folder
    src = os.path.join(current_path, m_pdb)
    dst = os.path.join(folderpath, os.path.basename(m_pdb))
    shutil.copy(src, dst)

    # write hole.inp
    home_dir = os.path.expanduser("~")
    # Determine HOLE installation root. Priority:
    # 1) HOLE_ROOT environment variable
    # 2) __config__.HOLE_ROOT in pdb_params.yaml
    # 3) common install locations (/root/hole2, /opt/hole2, ~/hole2)
    # 4) fallback to ~/hole2
    hole_root = os.environ.get("HOLE_ROOT")

    # check pdb_params config if available
    try:
        cfg = pdb_params.get('__config__') if isinstance(pdb_params, dict) else None
    except Exception:
        cfg = None
    if not hole_root and cfg:
        hr = cfg.get('HOLE_ROOT')
        if hr:
            hole_root = hr

    candidates = []
    if not hole_root:
        candidates = [
            os.path.join(home_dir, 'hole2'),
            '/root/hole2',
            '/opt/hole2',
            '/usr/local/hole2'
        ]
        found = None
        for c in candidates:
            radp = os.path.join(c, 'rad', 'simple.rad')
            try:
                if os.path.exists(radp):
                    found = c
                    break
            except Exception:
                continue
        if found:
            hole_root = found
        else:
            hole_root = os.path.join(home_dir, 'hole2')

    inp_path = os.path.join(folderpath, "hole.inp")
    with open(inp_path, "w") as file:
        file.write(f"coord ../{m_pdb}\n")
        file.write(f"radius {hole_root}/rad/simple.rad\n")
        file.write("sphpdb hole_out.sph\n")
        file.write("endrad 5.\n")
        # optional per-pdb parameters
        cpoint = params.get("CPOINT")
        if cpoint:
            try:
                file.write("CPOINT " + " ".join(str(float(x)) for x in cpoint) + "\n")
            except Exception:
                file.write("CPOINT " + " ".join(map(str, cpoint)) + "\n")
        cvect = params.get("CVECT")
        if cvect:
            try:
                file.write("CVECT " + " ".join(str(float(x)) for x in cvect) + "\n")
            except Exception:
                file.write("CVECT " + " ".join(map(str, cvect)) + "\n")

    # run commands with working directory set to folderpath
    def run(cmd, check=True, **kwargs):
        return subprocess.run(cmd, shell=True, check=check, text=True, cwd=folderpath, **kwargs)

    run('hole < hole.inp > hole_out.txt')
    # egrep may exit with code 1 when there are no matches; allow that without failing the whole run
    run('egrep "mid-|sampled" hole_out.txt > hole_out.tsv', check=False)
    run('sph_process -dotden 15 -color hole_out.sph dotsurface.qpt')

    # qpt_conv expects interactive input; run via pexpect in folderpath
    # Note: pexpect.spawn's cwd parameter isn't supported on Windows; change dir before spawning
    prev_cwd = os.getcwd()
    try:
        os.chdir(folderpath)
        process = pexpect.spawn('qpt_conv')
        process.write('D\n')
        process.write('\n')
        process.write('\n')
        process.write('1\n')
        process.wait()
        process.close()
    finally:
        os.chdir(prev_cwd)

    run('sph_process -sos -dotden 15 -color hole_out.sph solid_surface.sos')
    run('sos_triangle -s < solid_surface.sos > solid_surface.vmd_plot')

    return folderpath

current_path = os.getcwd()
# load optional per-pdb parameter config (pdb_params.yaml)
config_path = os.path.join(current_path, "pdb_params.yaml")
pdb_params = {}

def save_pdb_params(params=None):
    """Store params dict in-memory and persist to config_path (YAML).

    params can be a dict mapping pdb filenames/basenames to per-pdb config,
    with an optional special key '__config__' for global settings (e.g., HOLE_ROOT).
    If params is None, the current in-memory pdb_params is saved.
    """
    global pdb_params
    if params is not None:
        pdb_params = dict(params)

    # ensure parent dir exists
    try:
        with open(config_path, 'w') as fh:
            if yaml:
                yaml.safe_dump(pdb_params, fh)
            else:
                # fallback: write a repr if PyYAML isn't available
                fh.write(repr(pdb_params))
    except Exception:
        # ignore disk write errors but keep in-memory
        pass
    return pdb_params


def load_pdb_params():
    """Load pdb_params and optional __config__ from config_path (YAML).

    Returns the in-memory pdb_params mapping each pdb filename (or basename)
    to its params dict. Preserves existing in-memory values when possible.
    """
    global pdb_params
    data = {}
    if os.path.exists(config_path):
        try:
            if yaml:
                with open(config_path, 'r') as fh:
                    data = yaml.safe_load(fh) or {}
            else:
                # try eval as fallback (not recommended)
                with open(config_path, 'r') as fh:
                    data = eval(fh.read() or '{}')
        except Exception:
            data = {}

    # separate config and per-pdb entries
    cfg = data.get('__config__', {}) if isinstance(data, dict) else {}

    current = pdb_params if isinstance(pdb_params, dict) else {}
    files = list_pdb_files()
    new = {}
    for p in files:
        # prefer explicit filename entry in file, then basename, then in-memory
        if isinstance(data, dict) and p in data and isinstance(data[p], dict):
            new[p] = data[p]
        else:
            base = os.path.splitext(p)[0]
            if isinstance(data, dict) and base in data and isinstance(data[base], dict):
                new[p] = data[base]
            elif p in current:
                new[p] = current[p]
            elif base in current:
                new[p] = current[base]
            else:
                new[p] = {}

    # attach config under special key
    if cfg:
        new['__config__'] = cfg

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
    """Read hole_out.tsv in folderpath, compute abscissa and plot radius vs abscissa.

    - cvect: iterable of 3 numbers (channel vector). If provided, abscissa = dot(center, cvect).
      Otherwise abscissa = cumulative distance along centre-line.
    - out_name: optional PNG filename (written inside folderpath). If omitted, uses 'hole_plot.png'.
    - show_plot: if True and matplotlib backend supports it, show interactively (not used here).

    Returns path to saved PNG and the (x,y) arrays.
    """
    import math
    try:
        import matplotlib
        try:
            matplotlib.use('Agg')
        except Exception:
            # ignore if backend can't be set
            pass
    except Exception:
        matplotlib = None
    try:
        import matplotlib.pyplot as plt
    except Exception:
        plt = None

    tsv = os.path.join(folderpath, 'hole_out.tsv')
    if not os.path.exists(tsv):
        raise FileNotFoundError(f"{tsv} not found")

    centers = []
    radii = []
    with open(tsv, 'r') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # extract floats from the line
            parts = []
            for tok in line.split():
                try:
                    parts.append(float(tok))
                except Exception:
                    # ignore non-numeric tokens
                    pass
            if len(parts) < 4:
                continue
            x, y, z, r = parts[0], parts[1], parts[2], parts[3]
            centers.append((x, y, z))
            radii.append(r)

    if not centers:
        raise ValueError(f"No numeric data parsed from {tsv}")

    if cvect:
        # normalize cvect
        try:
            vx, vy, vz = float(cvect[0]), float(cvect[1]), float(cvect[2])
            norm = math.sqrt(vx*vx + vy*vy + vz*vz)
            if norm == 0:
                raise ValueError('CVECT has zero length')
            vx, vy, vz = vx/norm, vy/norm, vz/norm
            xs = [c[0]*vx + c[1]*vy + c[2]*vz for c in centers]
            xlabel = 'Channel coordinate (dot(center, CVECT))'
        except Exception:
            # fallback to cumulative distance
            xs = []
            total = 0.0
            prev = centers[0]
            xs.append(0.0)
            for c in centers[1:]:
                d = math.sqrt((c[0]-prev[0])**2 + (c[1]-prev[1])**2 + (c[2]-prev[2])**2)
                total += d
                xs.append(total)
                prev = c
            xlabel = 'Distance along centre-line (Angstrom)'
    else:
        xs = []
        total = 0.0
        prev = centers[0]
        xs.append(0.0)
        for c in centers[1:]:
            d = math.sqrt((c[0]-prev[0])**2 + (c[1]-prev[1])**2 + (c[2]-prev[2])**2)
            total += d
            xs.append(total)
            prev = c
        xlabel = 'Distance along centre-line (Angstrom)'

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



    
