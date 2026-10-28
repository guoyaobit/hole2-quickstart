import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import run_holeprogram as rh


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.radius = self.root / 'simple.rad'
        self.radius.write_text('radius data')
        (self.root / 'sample.pdb').write_text('ATOM\n')
        self.patch(rh, 'current_path', str(self.root))

    def patch(self, target, name, value):
        patcher = patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_command(self, command, **kwargs):
        name = Path(command[0]).name
        folder = Path(kwargs['cwd'])
        self.assertNotIn('shell', kwargs)
        self.assertTrue(kwargs['check'])
        self.assertEqual(kwargs['timeout'], 600)
        if name == 'hole':
            kwargs['stdout'].write('-17.51225 4.87622 -19.96329 0.00167 (sampled)\n')
            (folder / 'hole_out.sph').write_text('sphere data')
        elif name == 'sph_process':
            (folder / command[-1]).write_text('surface data')
        elif name == 'qpt_conv':
            self.assertEqual(kwargs['input'], 'D\ndotsurface.qpt\ndotsurface.vmd_plot\n1\n')
            (folder / 'dotsurface.vmd_plot').write_text('draw delete all\n')
        elif name == 'sos_triangle':
            kwargs['stdout'].write('draw triangle\n')
        return subprocess.CompletedProcess(command, 0)

    def test_pipeline_preserves_old_results_and_archives_before_plot(self):
        old = self.root / 'sample'
        old.mkdir()
        marker = old / 'keep.txt'
        marker.write_text('previous result')
        cwd = os.getcwd()
        with patch.object(rh.shutil, 'which', side_effect=lambda name: name), \
             patch.object(rh, 'resolve_radius_file', return_value=self.radius), \
             patch.object(rh.subprocess, 'run', side_effect=self.fake_command):
            folder = rh.run_hole('sample.pdb', {'CVECT': [0, 0, 1]})
        self.assertEqual(marker.read_text(), 'previous result')
        self.assertNotEqual(Path(folder), old)
        self.assertEqual(os.getcwd(), cwd)
        self.assertIn(str(self.radius), (Path(folder) / 'hole.inp').read_text())
        archive = rh.make_zip_for_folders([folder])
        with patch.dict(sys.modules, {'matplotlib': None}):
            result, (xs, radii) = rh.plot_tsv(folder, cvect=[1, 0, 0])
        self.assertEqual(xs, [-17.51225])
        self.assertEqual(radii, [4.87622])
        self.assertTrue(Path(result).is_file())
        with zipfile.ZipFile(archive) as zf:
            self.assertTrue(any(n.endswith('hole_out.tsv') for n in zf.namelist()))
            self.assertFalse(any(n.endswith(('hole_plot.png', 'hole_plot_data.csv')) for n in zf.namelist()))

    def test_notebook_keeps_zip_before_plot(self):
        source = Path(rh.__file__).with_name('run_notebook.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        calls = {node.func.attr: node.lineno for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr in ('make_zip_for_folders', 'plot_tsv')}
        self.assertLess(calls['make_zip_for_folders'], calls['plot_tsv'])

    def test_missing_tool_does_not_create_result_folder(self):
        with patch.object(rh.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, 'hole'):
                rh.run_hole('sample.pdb')
        self.assertFalse((self.root / 'sample').exists())

    def test_subprocess_failure_and_timeout_are_reported(self):
        for error in (subprocess.CalledProcessError(1, 'hole'),
                      subprocess.TimeoutExpired('hole', 600)):
            with self.subTest(error=type(error).__name__), \
                 patch.object(rh.shutil, 'which', side_effect=lambda name: name), \
                 patch.object(rh, 'resolve_radius_file', return_value=self.radius), \
                 patch.object(rh.subprocess, 'run', side_effect=error):
                with self.assertRaisesRegex(RuntimeError, 'hole.*failed.*hole_out.txt'):
                    rh.run_hole('sample.pdb')

    def test_missing_conversion_output_is_reported(self):
        def command(args, **kwargs):
            if args[0] != 'qpt_conv':
                return self.fake_command(args, **kwargs)
        with patch.object(rh.shutil, 'which', side_effect=lambda name: name), \
             patch.object(rh, 'resolve_radius_file', return_value=self.radius), \
             patch.object(rh.subprocess, 'run', side_effect=command):
            with self.assertRaisesRegex(RuntimeError, 'no VMD file'):
                rh.run_hole('sample.pdb')

    def test_explicit_radius_and_missing_explicit_path(self):
        with patch.dict(os.environ, {'HOLE_RADIUS': str(self.radius)}):
            self.assertEqual(rh.resolve_radius_file(), self.radius.resolve())
        with patch.dict(os.environ, {'HOLE_RADIUS': str(self.root / 'absent')}):
            with self.assertRaisesRegex(FileNotFoundError, 'HOLE_RADIUS'):
                rh.resolve_radius_file()

    def test_conda_radius_discovery(self):
        prefix = self.root / 'conda'
        radius = prefix / 'share' / 'hole2' / 'rad' / 'simple.rad'
        radius.parent.mkdir(parents=True)
        radius.write_text('radius data')
        with patch.dict(os.environ, {'HOLE_RADIUS': '', 'CONDA_PREFIX': str(prefix)}), \
             patch.object(rh.shutil, 'which', return_value=None):
            self.assertEqual(rh.resolve_radius_file(), radius.resolve())

    def test_invalid_parameters_are_rejected(self):
        for params in ({'CVECT': [0, 0, 0]}, {'CPOINT': [1, 2]},
                       {'CVECT': [1, 2, float('nan')]}, {'CPOINT': ['x', 2, 3]}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                rh.run_hole('sample.pdb', params)
        self.assertFalse((self.root / 'sample').exists())


if __name__ == '__main__':
    unittest.main()
