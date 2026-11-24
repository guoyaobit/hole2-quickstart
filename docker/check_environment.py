"""Fail image builds if the runtime toolchain or radius data is missing."""
import shutil

from run_holeprogram import resolve_radius_file


def main():
    for tool in ('hole', 'sph_process', 'qpt_conv', 'sos_triangle'):
        executable = shutil.which(tool)
        if executable is None:
            raise SystemExit(f'Missing executable: {tool}')
        print(f'{tool}: {executable}')
    print(f'Radius file: {resolve_radius_file()}')


if __name__ == '__main__':
    main()
