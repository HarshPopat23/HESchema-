"""Build and install the wheel into a clean venv, then run the SDK example outside the checkout.

Requires network/cache access to install declared dependencies. Does not use
system-site-packages or editable installation. No providers or external actions.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, env):
    subprocess.run(command, cwd=cwd, env=env, check=True, timeout=600)


def main():
    env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
    with tempfile.TemporaryDirectory(prefix='heschema-wheel-sdk-') as folder:
        root = Path(folder)
        wheels, empty, virtual = root / 'wheels', root / 'empty', root / 'venv'
        wheels.mkdir()
        empty.mkdir()
        run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', str(wheels), str(ROOT)], empty, env)
        wheel, = wheels.glob('heschema-*.whl')
        venv.EnvBuilder(with_pip=True).create(virtual)
        python = virtual / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        run([str(python), '-m', 'pip', 'install', str(wheel)], empty, env)
        run([str(python), '-I', '-c',
             'import heschema,sys; from pathlib import Path; '
             'assert Path(heschema.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())'], empty, env)
        example = empty / 'workflow_example.py'
        shutil.copyfile(ROOT / 'examples/sdk/workflow.py', example)
        run([str(python), '-I', str(example)], empty, env)
    print('WHEEL_SDK_VERIFIED')


if __name__ == '__main__':
    main()
