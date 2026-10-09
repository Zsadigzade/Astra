"""Wait for the launcher's Windows Job attachment before starting any workload."""
import subprocess
import sys
import os

if __name__ == "__main__":
    if sys.stdin.readline().strip() != "G":
        raise SystemExit(1)
    raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
