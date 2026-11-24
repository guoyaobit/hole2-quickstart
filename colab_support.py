"""Colab adapters; keep the notebook's Python kernel and reuse the HOLE pipeline."""
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request

import run_holeprogram as rh

MAMBA_URL = ('https://github.com/mamba-org/micromamba-releases/releases/download/'
             '2.10.0-0/micromamba-linux-64')
MAMBA_SHA256 = '701f39c06f8e6a670a0e186c8479b9e5c0502a2f0cda6cef65d83bdd2875e8bd'
TOOLS = ('hole', 'sph_process', 'sos_triangle')


def _download_micromamba(destination):
    if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == MAMBA_SHA256:
        return
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            with urllib.request.urlopen(MAMBA_URL, timeout=60) as response:
                shutil.copyfileobj(response, output)
        except Exception:
            output.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != MAMBA_SHA256:
            raise RuntimeError('micromamba checksum mismatch; download was not installed')
        temporary.chmod(0o755)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def install_hole(root='/content/hole2-runtime'):
    """Install only HOLE and its native dependencies, without installing Python."""
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise RuntimeError('This Colab installer requires a Linux x86_64 CPU runtime')
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    prefix = root / 'hole2-2.3.1'
    radius = prefix / 'share' / 'hole2' / 'rad' / 'simple.rad'

    def ready():
        return radius.is_file() and all((prefix / 'bin' / name).is_file() for name in TOOLS)

    if not ready():
        binary = root / 'micromamba-2.10.0'
        _download_micromamba(binary)
        environment = os.environ.copy()
        environment['MAMBA_ROOT_PREFIX'] = str(root / 'mamba-cache')
        operation = 'install' if (prefix / 'conda-meta' / 'history').exists() else 'create'
        subprocess.run([str(binary), operation, '--yes', '--prefix', str(prefix),
                        '--channel', 'conda-forge', '--strict-channel-priority', 'hole2=2.3.1'],
                       check=True, timeout=600, env=environment)
    if not ready():
        raise RuntimeError(f'HOLE installation is incomplete: {prefix}')
    bin_path = str(prefix / 'bin')
    existing = os.environ.get('PATH', '').split(os.pathsep)
    os.environ['PATH'] = os.pathsep.join([bin_path] + [p for p in existing if p != bin_path])
    os.environ['HOLE_RADIUS'] = str(radius)
    return prefix


def import_pdbs(paths, workspace):
    """Copy PDB inputs to safe filenames without replacing previous uploads."""
    paths = [Path(path) for path in paths]
    for path in paths:
        if not path.is_file() or path.suffix.lower() != '.pdb':
            raise ValueError(f'Expected a PDB file: {path}')
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    imported = []
    for source in paths:
        stem = re.sub(r'[^A-Za-z0-9_-]+', '_', source.stem).strip('_')[:48] or 'structure'
        suffix = 0
        while True:
            name = f'{stem}_{suffix}.pdb' if suffix else f'{stem}.pdb'
            target = workspace / name
            try:
                with source.open('rb') as input_file, target.open('xb') as output:
                    shutil.copyfileobj(input_file, output)
                break
            except FileExistsError:
                suffix += 1
        imported.append(name)
    return imported


def run_batch(workspace, parameters=None, selected=None):
    """Run sequentially, archive before plots, and restore the shared module state."""
    workspace = Path(workspace).resolve()
    files = sorted(p.name for p in workspace.glob('*.pdb') if p.is_file())
    targets = files if selected is None else list(selected)
    if not targets:
        raise ValueError('No PDB files selected; upload or import files first')
    if len(set(targets)) != len(targets) or any(name not in files for name in targets):
        raise ValueError('Selected filenames must be unique PDB files in the workspace')
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict) or any(name not in files for name in parameters):
        raise ValueError('Parameters must be a dictionary keyed by workspace PDB filenames')
    if any(not isinstance(value, dict) for value in parameters.values()):
        raise ValueError('Each PDB parameter entry must be a dictionary')
    validated = {name: rh.validate_params(value) for name, value in parameters.items()}
    previous_path, previous_params = rh.current_path, rh.pdb_params
    try:
        rh.current_path = str(workspace)
        rh.save_pdb_params(validated)
        folders = rh.process_pdbs(targets, workers=1)
        archive = rh.make_zip_for_folders(folders)
        plots, errors = [], {}
        for folder in folders:
            try:
                plot, _ = rh.plot_tsv(folder)
                plots.append(plot)
            except Exception as exc:
                errors[folder] = str(exc)
        return {'archive': archive, 'folders': folders, 'plots': plots, 'plot_errors': errors}
    finally:
        rh.current_path, rh.pdb_params = previous_path, previous_params


def save_results(result, destination):
    """Export the raw ZIP and separate plots to a new directory, e.g. on Drive."""
    destination = Path(destination).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    stem = Path(result['archive']).stem
    suffix = 0
    while True:
        export = destination / (f'{stem}_{suffix}' if suffix else stem)
        try:
            export.mkdir()
            break
        except FileExistsError:
            suffix += 1
    shutil.copy2(result['archive'], export / Path(result['archive']).name)
    for plot in result['plots']:
        plot = Path(plot)
        parent = export / plot.parent.name
        parent.mkdir(exist_ok=True)
        shutil.copy2(plot, parent / plot.name)
    return export
