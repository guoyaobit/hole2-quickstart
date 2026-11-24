import ast
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import colab_support as cs


class ColabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()

    def test_notebook_code_cells_compile(self):
        notebook = json.loads(Path(cs.__file__).with_name('colab.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(notebook['nbformat'], 4)
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                ast.parse(''.join(cell['source']))
                self.assertEqual(cell['outputs'], [])

    def test_import_normalizes_filenames_and_preserves_previous_uploads(self):
        source = self.root / 'sample [1].PDB'
        source.write_bytes(b'first input')
        first = cs.import_pdbs([source], self.workspace)[0]
        source.write_bytes(b'second input')
        second = cs.import_pdbs([source], self.workspace)[0]
        self.assertEqual(first, 'sample_1.pdb')
        self.assertNotEqual(first, second)
        self.assertEqual((self.workspace / first).read_bytes(), b'first input')
        self.assertEqual((self.workspace / second).read_bytes(), b'second input')

    def test_invalid_upload_rejected_before_copying(self):
        source = self.root / 'input.pdb'
        source.write_text('ATOM')
        invalid = self.root / 'notes.txt'
        invalid.write_text('not a structure')
        with self.assertRaises(ValueError):
            cs.import_pdbs([source, invalid], self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_download_checks_checksum_and_reuses_verified_binary(self):
        binary = self.root / 'micromamba'
        data = b'verified executable'
        with patch.object(cs, 'MAMBA_SHA256', hashlib.sha256(data).hexdigest()), \
             patch.object(cs.urllib.request, 'urlopen', return_value=io.BytesIO(data)) as request:
            cs._download_micromamba(binary)
            cs._download_micromamba(binary)
        request.assert_called_once()
        self.assertEqual(binary.read_bytes(), data)

    def test_bad_download_is_not_installed(self):
        binary = self.root / 'micromamba'
        with patch.object(cs.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad download')):
            with self.assertRaisesRegex(RuntimeError, 'checksum'):
                cs._download_micromamba(binary)
        self.assertFalse(binary.exists())

    def test_installer_reuses_tools_without_replacing_notebook_python(self):
        root = self.root / 'runtime'
        prefix = root / 'hole2-2.3.1'
        radius = prefix / 'share/hole2/rad/simple.rad'
        radius.parent.mkdir(parents=True)
        radius.write_text('radius data')
        (prefix / 'bin').mkdir()
        for tool in cs.TOOLS:
            (prefix / 'bin' / tool).write_text('tool')
        python = sys.executable
        with patch.object(cs.platform, 'system', return_value='Linux'), \
             patch.object(cs.platform, 'machine', return_value='x86_64'), \
             patch.dict(os.environ), patch.object(cs, '_download_micromamba') as download, \
             patch.object(cs.subprocess, 'run') as run:
            self.assertEqual(cs.install_hole(root), prefix.resolve())
            cs.install_hole(root)
            self.assertEqual(os.environ['PATH'].split(os.pathsep).count(str(prefix / 'bin')), 1)
            self.assertEqual(os.environ['HOLE_RADIUS'], str(radius))
        download.assert_not_called()
        run.assert_not_called()
        self.assertEqual(sys.executable, python)

    def test_installer_rejects_unsupported_platform_before_download(self):
        with patch.object(cs.platform, 'system', return_value='Windows'), \
             patch.object(cs, '_download_micromamba') as download:
            with self.assertRaisesRegex(RuntimeError, 'Linux x86_64'):
                cs.install_hole(self.root / 'runtime')
        download.assert_not_called()

    def test_batch_archives_before_plotting_and_restores_module_state(self):
        (self.workspace / 'sample.pdb').write_text('ATOM')
        folder = self.workspace / 'sample'
        folder.mkdir()
        (folder / 'hole_out.tsv').write_text('1 2 3 4 (sampled)\n')
        previous_path, previous_params = cs.rh.current_path, cs.rh.pdb_params

        def plot(directory):
            archives = list(self.workspace.glob('*.zip'))
            self.assertEqual(len(archives), 1)
            with zipfile.ZipFile(archives[0]) as archive:
                self.assertFalse(any(name.endswith('.png') for name in archive.namelist()))
            image = Path(directory) / 'hole_plot.png'
            image.write_bytes(b'plot')
            return str(image), ([1], [2])

        with patch.object(cs.rh, 'process_pdbs', return_value=[str(folder)]) as process, \
             patch.object(cs.rh, 'plot_tsv', side_effect=plot):
            result = cs.run_batch(self.workspace, {'sample.pdb': {'CVECT': [0, 0, 1]}})
        process.assert_called_once_with(['sample.pdb'], workers=1)
        self.assertTrue(Path(result['archive']).is_file())
        self.assertEqual(len(result['plots']), 1)
        self.assertEqual(cs.rh.current_path, previous_path)
        self.assertIs(cs.rh.pdb_params, previous_params)

    def test_batch_keeps_raw_archive_when_plot_fails(self):
        (self.workspace / 'sample.pdb').write_text('ATOM')
        folder = self.workspace / 'sample'
        folder.mkdir()
        with patch.object(cs.rh, 'process_pdbs', return_value=[str(folder)]), \
             patch.object(cs.rh, 'plot_tsv', side_effect=ValueError('bad profile')):
            result = cs.run_batch(self.workspace)
        self.assertTrue(Path(result['archive']).exists())
        self.assertEqual(result['plot_errors'], {str(folder): 'bad profile'})

    def test_batch_validates_parameters_and_restores_state_on_failure(self):
        (self.workspace / 'sample.pdb').write_text('ATOM')
        previous_path, previous_params = cs.rh.current_path, cs.rh.pdb_params
        with patch.object(cs.rh, 'process_pdbs', side_effect=RuntimeError('tool failed')) as process:
            for parameters in ({'absent.pdb': {}}, {'sample.pdb': None},
                               {'sample.pdb': {'CVECT': [0, 0, 0]}}):
                with self.assertRaises(ValueError):
                    cs.run_batch(self.workspace, parameters)
            process.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'tool failed'):
                cs.run_batch(self.workspace)
        self.assertEqual(cs.rh.current_path, previous_path)
        self.assertIs(cs.rh.pdb_params, previous_params)

    def test_export_preserves_previous_exports_and_includes_separate_plots(self):
        archive = self.workspace / 'raw.zip'
        archive.write_bytes(b'raw archive')
        plot = self.workspace / 'sample' / 'hole_plot.png'
        plot.parent.mkdir()
        plot.write_bytes(b'image')
        result = {'archive': str(archive), 'plots': [str(plot)]}
        destination = self.root / 'drive'
        first = cs.save_results(result, destination)
        second = cs.save_results(result, destination)
        self.assertNotEqual(first, second)
        for export in (first, second):
            self.assertEqual((export / 'raw.zip').read_bytes(), b'raw archive')
            self.assertEqual((export / 'sample/hole_plot.png').read_bytes(), b'image')


if __name__ == '__main__':
    unittest.main()
