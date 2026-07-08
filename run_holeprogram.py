import os
import subprocess
import shutil
import pexpect
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
    inp_path = os.path.join(folderpath, "hole.inp")
    with open(inp_path, "w") as file:
        file.write(f"coord ../{m_pdb}\n")
        file.write(f"radius {home_dir}/hole2/rad/simple.rad\n")
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
    def run(cmd, **kwargs):
        return subprocess.run(cmd, shell=True, check=True, text=True, cwd=folderpath, **kwargs)

    run('hole < hole.inp > hole_out.txt')
    run('egrep "mid-|sampled" hole_out.txt > hole_out.tsv')
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

def save_pdb_params(path, params):
    if yaml is None:
        print("PyYAML not installed; cannot save YAML config. Install with `pip install pyyaml`.")
        return
    with open(path, "w") as out:
        yaml.safe_dump(params, out)


def load_pdb_params(path=None):
    global pdb_params
    path = path or config_path
    pdb_params = {}
    if os.path.exists(path):
        if yaml is None:
            print(f"Found {path} but PyYAML not installed; skipping load.")
        else:
            with open(path, "r") as cf:
                try:
                    loaded = yaml.safe_load(cf)
                    pdb_params = loaded if isinstance(loaded, dict) else {}
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
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


def process_pdbs(pdb_list, workers=1):
    """Process a list of pdb filenames (relative to current_path). Returns list of output folder paths.

    If workers > 1, uses multiprocessing.Pool to process in parallel.
    """
    if workers and workers > 1:
        from multiprocessing import Pool
        args = [(pdb, get_params_for(pdb)) for pdb in pdb_list]
        with Pool(processes=workers) as pool:
            results = pool.map(_run_pair, args)
        return results

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


if __name__ == '__main__':
    # default behavior: load params, list pdbs and process all
    load_pdb_params()
    pdb_files = list_pdb_files()
    print('Found PDBs:', pdb_files)
    folders = process_pdbs(pdb_files)
    zipfile = make_zip_for_folders(folders)
    print('Created zip:', zipfile)



    
