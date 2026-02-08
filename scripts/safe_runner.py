import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Sequence, Mapping


class SafeRunner:
    """
    Cross-platform safe subprocess runner with timeout, output capture, and cleanup.
    - Windows: creates new process group to allow graceful termination.
    - POSIX: uses start_new_session to detach.
    - Optional tee to file for long-running logs.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        cmd: Sequence[str],
        timeout_sec: Optional[float] = None,
        cwd: Optional[Path] = None,
        env: Optional[Mapping[str, str]] = None,
        tee_to: Optional[Path] = None,
    ) -> dict:
        """Run command safely and return result dict with keys: code, stdout, stderr, duration."""
        t0 = time.perf_counter()
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        kwargs = {
            'cwd': str(cwd) if cwd else None,
            'env': env or os.environ.copy(),
            'text': True,
            'bufsize': 1,
        }
        creationflags = 0
        start_new_session = False
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            start_new_session = True

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            start_new_session=start_new_session,
            **kwargs,
        )
        tee_f = None
        try:
            if tee_to:
                tee_to.parent.mkdir(parents=True, exist_ok=True)
                tee_f = tee_to.open('a', encoding='utf-8')
            # Polling read loop with timeout
            while True:
                if timeout_sec is not None and (time.perf_counter() - t0) > timeout_sec:
                    # Graceful terminate then kill if needed
                    try:
                        if os.name == 'nt':
                            p.terminate()
                        else:
                            p.terminate()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    if p.poll() is None:
                        try:
                            p.kill()
                        except Exception:
                            pass
                    break

                # Read available output
                out = p.stdout.readline() if p.stdout else ''
                err = p.stderr.readline() if p.stderr else ''
                if out:
                    stdout_chunks.append(out)
                    if tee_f:
                        tee_f.write(out)
                if err:
                    stderr_chunks.append(err)
                    if tee_f:
                        tee_f.write(err)
                # Check process completion
                if p.poll() is not None:
                    # Drain remaining
                    if p.stdout:
                        rem = p.stdout.read()
                        if rem:
                            stdout_chunks.append(rem)
                            if tee_f:
                                tee_f.write(rem)
                    if p.stderr:
                        rem = p.stderr.read()
                        if rem:
                            stderr_chunks.append(rem)
                            if tee_f:
                                tee_f.write(rem)
                    break
                time.sleep(0.05)
        finally:
            if tee_f:
                try:
                    tee_f.flush(); tee_f.close()
                except Exception:
                    pass

        duration = time.perf_counter() - t0
        return {
            'code': p.returncode,
            'stdout': ''.join(stdout_chunks),
            'stderr': ''.join(stderr_chunks),
            'duration': duration,
        }


def which_python_candidates() -> list[Path]:
    """Return likely Python executables, preferring project venvs."""
    cands: list[Path] = []
    root = Path.cwd()
    for v in (root/'.venv_experiment', root/'.venv_run', root/'.venv_eehfr_clean'):
        exe = v/'Scripts'/'python.exe'
        if exe.exists():
            cands.append(exe)
    # Fallback to system 'py -3' resolution left to caller
    return cands