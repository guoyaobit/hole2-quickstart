"""Initialize persistent user data, then replace this process with Jupyter."""
import os
from pathlib import Path
import shutil
import sys


def initialize_workspace(directory, template):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'run.ipynb'
    # Never overwrite a notebook edited by the user on a previous image version.
    try:
        with Path(template).open('rb') as source, target.open('xb') as output:
            shutil.copyfileobj(source, output)
    except FileExistsError:
        pass
    return directory


def main():
    try:
        workspace = initialize_workspace('/data', '/opt/hole2/run.ipynb')
        os.chdir(workspace)
    except OSError as exc:
        raise SystemExit('Cannot initialize /data. Check the bind mount permissions '
                         'and HOLE_UID/HOLE_GID settings: ' + str(exc)) from exc
    command = [sys.executable, '-m', 'jupyterlab', '--ip=0.0.0.0', '--port=8888',
               '--no-browser', '--ServerApp.port_retries=0',
               '--ServerApp.root_dir=/data',
               '--ServerApp.default_url=/lab/tree/run.ipynb']
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
