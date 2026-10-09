"""Build the launcher using PyInstaller; no repository data or secrets are bundled."""
import os
from pathlib import Path
import sys


def main():
    # Some Windows installations contain Tcl but omit its default discovery path.
    tcl = Path(sys.base_prefix) / "tcl"
    for variable, folder in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
        if (tcl / folder).is_dir():
            os.environ[variable] = str(tcl / folder)
    import tkinter
    tkinter.Tcl()  # Fail the build if Tk cannot be bundled, not on the user's first launch.
    from PyInstaller.__main__ import run
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    run(["--noconfirm", "--clean", "--onefile", "--windowed", "--name", "AstraLauncher",
         "--distpath", "dist", "--workpath", "data/launcher-build", "--specpath", "data/launcher-build",
         "scripts/desktop/launcher.py"])


if __name__ == "__main__":
    main()
