"""Drive the legacy qpt_conv prompts through a terminal, without pexpect."""
import errno
import os
import subprocess
import time


def run_qpt_conv(command, folder, timeout=600):
    # HOLE's INTERF routine rewinds input before filename reads. Pipes can lose
    # buffered replies, and regular files rewind to the initial menu choice.
    # A PTY plus one reply per prompt reproduces interactive terminal input.
    import pty
    import select

    log_path = os.path.join(folder, 'qpt_conv.log')
    prompts = [(b'Enter conversion option character', b'D\n'),
               (b'(old) filename', b'dotsurface.qpt\n'),
               (b'(new) filename', b'dotsurface.vmd_plot\n'),
               (b'What width', b'1\n')]
    master, slave = pty.openpty()
    process = None
    deadline = time.monotonic() + timeout
    try:
        with open(log_path, 'wb') as log:
            process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=folder)
            os.close(slave)
            slave = None
            pending = b''
            stage = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                readable, _, _ = select.select([master], [], [], min(remaining, 0.1))
                if readable:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError as exc:
                        if exc.errno != errno.EIO:
                            raise
                        chunk = b''
                    if not chunk:
                        break
                    log.write(chunk)
                    pending = (pending + chunk)[-131072:]
                    if b'Sorry unable to open file' in pending:
                        raise RuntimeError(f'qpt_conv could not open its input/output file; see {log_path}')
                    if stage < len(prompts) and prompts[stage][0] in pending:
                        os.write(master, prompts[stage][1])
                        stage += 1
                        pending = b''
                elif process.poll() is not None:
                    break
            status = process.wait(timeout=max(deadline - time.monotonic(), 0.001))
            if status != 0:
                raise subprocess.CalledProcessError(status, command)
            if stage != len(prompts):
                raise RuntimeError(f'qpt_conv ended before completing its prompts; see {log_path}')
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f'qpt_conv failed or timed out; see {log_path}') from exc
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        if slave is not None:
            os.close(slave)
        os.close(master)
