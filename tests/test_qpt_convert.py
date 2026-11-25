from pathlib import Path
import struct
import tempfile
import unittest

from qpt_convert import convert_qpt_to_vmd


def record(payload, endian='<'):
    marker = struct.pack(endian + 'I', len(payload))
    return marker + payload + marker


def vector(values, endian='<'):
    return record(struct.pack(endian + '4f', *values), endian)


class QptConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'surface.qpt'
        self.output = self.root / 'surface.vmd_plot'

    def test_points_lines_and_extended_colors_in_both_byte_orders(self):
        for endian in ('<', '>'):
            with self.subTest(endian=endian):
                records = [(1, 4, 0, 0), (2, 1, 2, 3), (3, 4, 5, 6),
                           (1, 0, -55, 16), (4, 7, 8, 9),
                           (1, 0, -55, 17), (4, 10, 11, 12),
                           (1, 0, -55, 18), (4, 13, 14, 15)]
                self.source.write_bytes(b''.join(vector(values, endian) for values in records))
                convert_qpt_to_vmd(self.source, self.output)
                result = self.output.read_text()
                self.assertIn('draw line {4.000 5.000 6.000} {1.000 2.000 3.000} width 1', result)
                self.assertIn('draw color purple', result)
                self.assertIn('draw color red\ndraw point {7.000 8.000 9.000}', result)
                self.assertIn('draw color green\ndraw point {10.000 11.000 12.000}', result)
                self.assertIn('draw color blue\ndraw point {13.000 14.000 15.000}', result)
                self.assertEqual(result.count('draw line '), 1)
                self.assertEqual(result.count('draw point '), 3)

    def test_text_records_are_consumed_without_becoming_geometry(self):
        self.source.write_bytes(vector((5, 5, 0, 0)) + record(b'hello') + vector((4, 1, 2, 3)))
        convert_qpt_to_vmd(self.source, self.output)
        self.assertIn('draw point {1.000 2.000 3.000}', self.output.read_text())
        self.assertNotIn('hello', self.output.read_text())

    def test_color_record_does_not_replace_previous_position(self):
        self.source.write_bytes(b''.join(vector(values) for values in
                                         [(2, 10, 20, 30), (1, 4, 0, 0), (3, 11, 21, 31)]))
        convert_qpt_to_vmd(self.source, self.output)
        self.assertIn('draw line {11.000 21.000 31.000} {10.000 20.000 30.000} width 1',
                      self.output.read_text())

    def test_invalid_and_truncated_files_are_rejected(self):
        valid = vector((4, 1, 2, 3))
        examples = [b'', b'not qpt', valid[:-1], valid[:-4] + struct.pack('<I', 12),
                    vector((4, float('nan'), 0, 0)), vector((5, 5, 0, 0)),
                    vector((99, 0, 0, 0)), vector((1, 0, -55, 16))]
        for data in examples:
            with self.subTest(data=data):
                self.source.write_bytes(data)
                with self.assertRaises(ValueError):
                    convert_qpt_to_vmd(self.source, self.output)


if __name__ == '__main__':
    unittest.main()
