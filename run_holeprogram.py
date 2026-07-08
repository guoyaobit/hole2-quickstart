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
    if params is None:
        params = {}
    os.chdir(current_path)
    foldername = os.path.splitext(m_pdb)[0]
    if os.path.exists(foldername):
        shutil.rmtree(foldername)
    os.mkdir(foldername)
    os.chdir(foldername)
    home_dir = os.path.expanduser("~")
    subprocess.run(f"cp ../{m_pdb} .", shell=True, check=True, text=True)
    with open("hole.inp","w") as file:
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
    command = 'hole < hole.inp > hole_out.txt'
    subprocess.run(command, shell=True, check=True, text=True)
    command = 'egrep "mid-|sampled" hole_out.txt > hole_out.tsv'
    subprocess.run(command, shell=True, check=True, text=True)
    command = "sph_process -dotden 15 -color hole_out.sph dotsurface.qpt"
    subprocess.run(command, shell=True, check=True, text=True)
    command = "qpt_conv"
    process=pexpect.spawn(command)
    
    process.write("D\n")
    process.write("\n")
    process.write("\n")
    process.write("1\n")
    process.wait()
    process.close()
    command ="sph_process -sos -dotden 15 -color hole_out.sph solid_surface.sos"
    subprocess.run(command,shell=True, check=True, text=True)
    command ="sos_triangle -s < solid_surface.sos > solid_surface.vmd_plot"
    subprocess.run(command,shell=True, check=True, text=True)

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

if os.path.exists(config_path):
    if yaml is None:
        print(f"Found {config_path} but PyYAML not installed; skipping load.")
    else:
        with open(config_path, "r") as cf:
            try:
                loaded = yaml.safe_load(cf)
                pdb_params = loaded if isinstance(loaded, dict) else {}
            except Exception as e:
                print(f"Failed to load {config_path}: {e}")

pdb_files = [file for file in os.listdir(current_path) if file.endswith(".pdb")]
print(pdb_files)
# helper to get params for a pdb (match by filename or basename)
def get_params_for(pdb_name):
    if pdb_name in pdb_params:
        return pdb_params[pdb_name]
    base = os.path.splitext(pdb_name)[0]
    return pdb_params.get(base, {})
# folders_to_zip = [os.path.splitext(file)[0] for file in pdb_files]
# print(folders_to_zip)
for i in pdb_files:
    run_hole(i, get_params_for(i))
# with Pool() as p:
#     p.map(run_hole,pdb_files)



    
