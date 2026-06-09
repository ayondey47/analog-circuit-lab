"""Locate and execute ngspice in batch mode.

Resolution order for the ngspice executable:
1. NGSPICE_EXE environment variable
2. `ngspice` / `ngspice_con` on PATH
3. Common Windows install locations
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_WINDOWS_CANDIDATES = (
    Path.home() / "tools" / "Spice64" / "bin" / "ngspice_con.exe",
    Path("C:/Spice64/bin/ngspice_con.exe"),
    Path("C:/Program Files/Spice64/bin/ngspice_con.exe"),
)


def find_ngspice() -> str:
    """Return the path to an ngspice executable, or raise RuntimeError."""
    env = os.environ.get("NGSPICE_EXE")
    if env and Path(env).exists():
        return env
    for name in ("ngspice", "ngspice_con"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in _WINDOWS_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "ngspice executable not found. Install ngspice (https://ngspice.sourceforge.io) "
        "or set the NGSPICE_EXE environment variable to the full path of the binary."
    )


def run_netlist(netlist: str | Path, timeout: int = 300) -> str:
    """Run a netlist through ngspice in batch mode.

    The simulation runs with the netlist's directory as the working directory,
    so `wrdata` output files land next to the netlist. Returns captured stdout.
    """
    netlist = Path(netlist).resolve()
    if not netlist.exists():
        raise FileNotFoundError(f"Netlist not found: {netlist}")
    exe = find_ngspice()
    result = subprocess.run(
        [exe, "-b", netlist.name],
        cwd=netlist.parent,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ngspice failed on {netlist.name} (exit {result.returncode}):\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout
