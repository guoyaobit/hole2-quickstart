"""Convert HOLE's Fortran-record QPT output to VMD drawing commands."""
import math
import struct


def _record(stream, endian):
    marker = stream.read(4)
    if not marker:
        return None
    if len(marker) != 4:
        raise ValueError('Truncated QPT record marker')
    length = struct.unpack(endian + 'I', marker)[0]
    if length > 1024 * 1024:
        raise ValueError('Invalid QPT record length')
    payload = stream.read(length)
    trailer = stream.read(4)
    if len(payload) != length or len(trailer) != 4:
        raise ValueError('Truncated QPT record')
    if struct.unpack(endian + 'I', trailer)[0] != length:
        raise ValueError('QPT record markers do not match')
    return payload


def _vectors(filename):
    with open(filename, 'rb') as stream:
        marker = stream.read(4)
        if marker == struct.pack('<I', 16):
            endian = '<'
        elif marker == struct.pack('>I', 16):
            endian = '>'
        else:
            raise ValueError('Expected a QPT file with 4-byte Fortran record markers')
        stream.seek(0)
        while True:
            payload = _record(stream, endian)
            if payload is None:
                break
            if len(payload) != 16:
                raise ValueError('Expected four float32 values in a QPT geometry record')
            vector = struct.unpack(endian + '4f', payload)
            if not all(math.isfinite(value) for value in vector):
                raise ValueError('Non-finite value in QPT geometry')
            kind = int(vector[0])
            if vector[0] != kind or kind not in (1, 2, 3, 4, 5):
                raise ValueError('Unknown QPT record type')
            if kind == 5:
                text = _record(stream, endian)
                if text is None or len(text) < int(vector[1]):
                    raise ValueError('Missing QPT text record')
            yield vector


def convert_qpt_to_vmd(source, destination):
    """Preserve HOLE's line/point geometry and standard/extended color groups."""
    groups = [(None, 'purple'), (15, 'yellow'), (16, 'red'), (17, 'green'),
              (18, 'blue'), (19, 'purple'), (20, 'gray')]
    objects = 0
    with open(destination, 'w') as output:
        output.write('draw delete all\ndraw materials off\n')
        for group, name in groups:
            color, previous, started = 1, None, False
            for vector in _vectors(source):
                kind = int(vector[0])
                if kind == 1:
                    color = int(vector[3]) if int(vector[2]) == -55 else int(vector[1])
                valid = color < 15 if group is None else color == group
                if valid and kind in (3, 4):
                    if kind == 3 and previous is None:
                        raise ValueError('QPT line has no preceding position')
                    if not started:
                        output.write(f'draw color {name}\n')
                        started = True
                    xyz = ' '.join(f'{value:.3f}' for value in vector[1:])
                    if kind == 4:
                        output.write(f'draw point {{{xyz}}}\n')
                    else:
                        before = ' '.join(f'{value:.3f}' for value in previous)
                        output.write(f'draw line {{{xyz}}} {{{before}}} width 1\n')
                    objects += 1
                if kind in (2, 3, 4):
                    previous = vector[1:]
        if not objects:
            raise ValueError('QPT file contains no drawable points or lines')
    return destination
