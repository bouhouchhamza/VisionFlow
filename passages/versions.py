"""Relevé des versions et de la machine, pour le manifeste d'un run."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import passages

PAQUETS = ["av", "numpy", "onnxruntime", "opencv-python", "supervision", "trackers", "PyYAML", "scipy"]


def _git(racine: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(racine), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def nom_processeur() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    return platform.processor()


def version_ffmpeg() -> str | None:
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.splitlines()[0] if r.returncode == 0 and r.stdout else None


def relever(racine: Path) -> dict:
    paquets = {}
    for p in PAQUETS:
        try:
            paquets[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            paquets[p] = None
    commit = _git(racine, "rev-parse", "HEAD")
    etat = _git(racine, "status", "--porcelain", "--", "passages", "configs")
    return {
        "passages": passages.__version__,
        "python": sys.version.split()[0],
        "plateforme": platform.platform(),
        "processeur": nom_processeur(),
        "coeurs_logiques": os.cpu_count(),
        "paquets": paquets,
        "git_commit": commit,
        "git_modifications_locales": bool(etat) if etat is not None else None,
    }
