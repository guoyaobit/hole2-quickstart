import os
from pathlib import Path
import sys
import tempfile
import unittest

from qpt_control import run_qpt_conv


@unittest.skipUnless(os.name == 'posix', 'Pseudo-terminal integration requires Linux/POSIX')
class QptControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_replies_are_sent_only_after_each_prompt(self):
        script = """
import os, sys, termios
from pathlib import Path
assert os.isatty(0)
steps = [('Enter conversion option character:', 'D'),
         ('Please enter input binary plot (old) filename', 'dotsurface.qpt'),
         ('Please enter vmd format file (new) filename', 'dotsurface.vmd_plot'),
         ('What width do you want lines to appear:', '1')]
for prompt, expected in steps:
    # Simulate a legacy runtime discarding any prematurely queued replies.
    termios.tcflush(0, termios.TCIFLUSH)
    print(prompt, flush=True)
    assert sys.stdin.readline().strip() == expected
Path('dotsurface.vmd_plot').write_text('draw delete all\\n')
"""
        run_qpt_conv([sys.executable, '-u', '-c', script], str(self.folder), timeout=5)
        self.assertTrue((self.folder / 'dotsurface.vmd_plot').is_file())
        self.assertIn('What width', (self.folder / 'qpt_conv.log').read_text())

    def test_early_exit_is_reported_even_with_zero_status(self):
        with self.assertRaisesRegex(RuntimeError, 'before completing'):
            run_qpt_conv([sys.executable, '-c', "print('normal exit')"], str(self.folder), timeout=5)

    def test_prompt_timeout_terminates_child(self):
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            run_qpt_conv([sys.executable, '-c', 'import time; time.sleep(60)'],
                         str(self.folder), timeout=0.2)

    def test_file_open_error_fails_without_repeating_prompts(self):
        with self.assertRaisesRegex(RuntimeError, 'could not open'):
            run_qpt_conv([sys.executable, '-u', '-c', "print('Sorry unable to open file: D.qpt')"],
                         str(self.folder), timeout=5)
        self.assertIn('D.qpt', (self.folder / 'qpt_conv.log').read_text())


if __name__ == '__main__':
    unittest.main()
