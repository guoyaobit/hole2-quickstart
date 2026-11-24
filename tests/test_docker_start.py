import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    'hole2_docker_start', Path(__file__).resolve().parents[1] / 'docker' / 'start.py')
startup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(startup)


class DockerStartupTests(unittest.TestCase):
    def test_first_start_copies_notebook_and_update_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / 'template.ipynb'
            template.write_text(json.dumps({'cells': [], 'nbformat': 4}))
            data = root / 'data'
            startup.initialize_workspace(data, template)
            notebook = data / 'run.ipynb'
            self.assertEqual(notebook.read_bytes(), template.read_bytes())
            notebook.write_text('user notebook edits')
            (data / 'input.pdb').write_text('input structure')
            (data / 'result.zip').write_bytes(b'archived results')
            template.write_text('new image notebook template')
            startup.initialize_workspace(data, template)
            self.assertEqual(notebook.read_text(), 'user notebook edits')
            self.assertEqual((data / 'input.pdb').read_text(), 'input structure')
            self.assertEqual((data / 'result.zip').read_bytes(), b'archived results')

    def test_start_runs_jupyter_in_data_directory(self):
        with patch.object(startup, 'initialize_workspace', return_value=Path('/data')), \
             patch.object(startup.os, 'chdir') as chdir, \
             patch.object(startup.os, 'execv') as execute:
            startup.main()
        chdir.assert_called_once_with(Path('/data'))
        executable, command = execute.call_args.args
        self.assertEqual(executable, startup.sys.executable)
        self.assertEqual(command[:3], [executable, '-m', 'jupyterlab'])
        self.assertIn('--ServerApp.root_dir=/data', command)
        self.assertIn('--ServerApp.port_retries=0', command)

    def test_permissions_failure_reports_bind_mount_settings(self):
        with patch.object(startup, 'initialize_workspace', side_effect=PermissionError('denied')):
            with self.assertRaisesRegex(SystemExit, 'HOLE_UID/HOLE_GID'):
                startup.main()


if __name__ == '__main__':
    unittest.main()
