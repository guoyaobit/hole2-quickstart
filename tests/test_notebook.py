"""Exercise real widget callbacks without starting a notebook server."""
import contextlib
import io
import unittest
from unittest.mock import patch

try:
    import run_notebook as notebook
except ModuleNotFoundError as exc:
    if exc.name not in ('ipywidgets', 'pandas', 'IPython'):
        raise
    notebook = None


@unittest.skipIf(notebook is None, 'Notebook dependencies are not installed')
class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.files = ['old.pdb', 'keep.pdb']
        self.params = {'old.pdb': {'CPOINT': [1, 2, 3], 'CVECT': [0, 0, 1]},
                       'keep.pdb': {'CPOINT': [4, 5, 6]}}
        self.patcher(patch.object(notebook.rh, 'pdb_params', self.params))
        self.patcher(patch.object(notebook.rh, 'list_pdb_files', side_effect=lambda: list(self.files)))
        displayed = []
        self.patcher(patch.object(notebook, 'display', side_effect=displayed.append))
        self.patcher(patch.object(notebook, 'clear_output'))
        with contextlib.redirect_stdout(io.StringIO()):
            notebook.launch()
        widgets = []

        def collect(widget):
            if isinstance(widget, notebook.widgets.Widget):
                widgets.append(widget)
                for child in getattr(widget, 'children', ()):
                    collect(child)

        for item in displayed:
            collect(item)
        self.widgets = widgets
        self.editor = next(w for w in widgets if isinstance(w, notebook.widgets.Dropdown))
        self.batch = next(w for w in widgets if isinstance(w, notebook.widgets.SelectMultiple))
        self.cpoint = self.find('CPOINT (csv)')
        self.cvect = self.find('CVECT (csv)')

    def patcher(self, item):
        item.start()
        self.addCleanup(item.stop)

    def find(self, description):
        return next(w for w in self.widgets if getattr(w, 'description', None) == description)

    def click(self, description):
        # Call the registered callback directly so ipywidgets cannot hide errors.
        button = self.find(description)
        with contextlib.redirect_stdout(io.StringIO()):
            for callback in button._click_handlers.callbacks:
                callback(button)

    def test_refresh_updates_both_lists_and_loads_new_selection(self):
        self.editor.value = 'old.pdb'
        self.files[:] = ['new.pdb', 'keep.pdb']
        self.click('Refresh PDB list')
        self.assertEqual(set(self.editor.options), set(self.files))
        self.assertEqual(set(self.batch.options), set(self.files))
        self.assertEqual(self.editor.value, 'keep.pdb')
        self.assertEqual(self.cpoint.value, '4, 5, 6')
        self.editor.value = 'new.pdb'
        self.cpoint.value = '7, 8, 9'
        self.click('Save')
        self.assertEqual(notebook.rh.pdb_params['new.pdb']['CPOINT'], [7, 8, 9])

    def test_refresh_preserves_existing_selection(self):
        self.editor.value = 'old.pdb'
        self.files.append('new.pdb')
        self.click('Refresh PDB list')
        self.assertEqual(self.editor.value, 'old.pdb')
        self.assertEqual(self.cpoint.value, '1, 2, 3')

    def test_refresh_empty_directory_clears_selection_and_fields(self):
        self.editor.value = 'old.pdb'
        self.files.clear()
        self.click('Refresh PDB list')
        self.assertEqual(tuple(self.editor.options), ())
        self.assertIsNone(self.editor.value)
        self.assertEqual(tuple(self.batch.options), ())
        self.assertEqual(self.cpoint.value, '')
        self.assertEqual(self.cvect.value, '')

    def test_clear_then_save_does_not_restore_old_parameters(self):
        self.editor.value = 'old.pdb'
        self.assertEqual(self.cpoint.value, '1, 2, 3')
        self.click('Clear')
        self.assertEqual(self.cpoint.value, '')
        self.assertEqual(self.cvect.value, '')
        self.assertEqual(notebook.rh.pdb_params['old.pdb'], {})
        self.click('Save')
        self.assertEqual(notebook.rh.pdb_params['old.pdb'], {})


if __name__ == '__main__':
    unittest.main()
