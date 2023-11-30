import os
import subprocess
import shutil
import pexpect
# from multiprocessing import Pool
def run_hole(m_pdb):
    os.chdir(current_path)
    foldername = os.path.splitext(m_pdb)[0]
    if os.path.exists(foldername):
        shutil.rmtree(foldername)
    os.mkdir(foldername)
    os.chdir(foldername)
    subprocess.run(f"cp ../{m_pdb} .", shell=True, check=True, text=True)
    with open("hole.inp","w") as file:
        file.write(f"coord ../{m_pdb}\n")
        file.write("radius /home/ubuntu/hole2/rad/simple.rad\n")
        file.write("sphpdb hole_out.sph\n")
        file.write("endrad 5.\n")
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
    command ="sph_process -sos -dotden 15 -color hole_out.sph solid_surface.sos"
    subprocess.run(command,shell=True, check=True, text=True)
    command ="sos_triangle -s < solid_surface.sos > solid_surface.vmd_plot"
    subprocess.run(command,shell=True, check=True, text=True)

current_path = os.getcwd()
pdb_files = [file for file in os.listdir(current_path) if file.endswith(".pdb")]
print(pdb_files)
# folders_to_zip = [os.path.splitext(file)[0] for file in pdb_files]
# print(folders_to_zip)
for i in pdb_files:
    run_hole(i)
# with Pool() as p:
#     p.map(run_hole,pdb_files)



    
