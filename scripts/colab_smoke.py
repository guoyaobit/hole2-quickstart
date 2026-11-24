"""Exercise the Colab tool installer and real HOLE pipeline on Linux in CI."""
import hashlib
from pathlib import Path
import sys
import tempfile
import urllib.request
import zipfile

from colab_support import install_hole, import_pdbs, run_batch
import run_holeprogram as rh

python = sys.executable
install_hole('/tmp/hole2-colab-runtime')
assert sys.executable == python, 'The notebook interpreter must remain unchanged'

example_url = ('https://raw.githubusercontent.com/osmart/hole2/'
               'a8eaf6121ba66625446933f4acd7d6aa336dbb47/'
               'examples/01_gramicidin_1grm/1grm_single.pdb')
with urllib.request.urlopen(example_url, timeout=60) as response:
    example = response.read()
git_blob = b'blob ' + str(len(example)).encode() + b'\0' + example
assert hashlib.sha1(git_blob).hexdigest() == '057a55c8178a4c8a32c11697f8d7595404b7b08e'

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / '1grm.pdb'
    source.write_bytes(example)
    workspace = root / 'data'
    imported = import_pdbs([source], workspace)
    result = run_batch(workspace, selected=imported)
    assert not result['plot_errors'], result['plot_errors']
    assert result['plots'] and Path(result['plots'][0]).is_file()
    _, (coordinate, radius) = rh.plot_tsv(result['folders'][0])
    assert len(coordinate) > 10 and all(0 < value < 10 for value in radius)
    with zipfile.ZipFile(result['archive']) as archive:
        assert any(name.endswith('hole_out.tsv') for name in archive.namelist())
        assert any(name.endswith('solid_surface.vmd_plot') for name in archive.namelist())
        assert not any(name.endswith('hole_plot.png') for name in archive.namelist())
    print(f'Colab-style install and real HOLE pipeline passed: {len(radius)} profile rows')
