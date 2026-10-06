"""Execute the actual frozen desktop app on Windows and require a clean exit."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Windows required")
    exe = Path(sys.argv[1]).resolve()
    environment = os.environ.copy()
    environment.pop("QT_QPA_PLATFORM", None)  # Exercise the native Windows Qt plugin.
    with tempfile.TemporaryDirectory(prefix="zugpferd-starttest-") as root:
        subprocess.run(
            [str(exe), "--smoke-test", "--root", root],
            check=True,
            timeout=60,
            env=environment,
        )
    print("Frozen Windows GUI and documentation wizard: start/close smoke test passed")


if __name__ == "__main__":
    main()
