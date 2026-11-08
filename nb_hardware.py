"""Best-effort local hardware inventory. No telemetry and no third-party dependencies.

Memory figures are estimates; GPU allocations and usable context caches vary by backend.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
from pathlib import Path

GIB = 1024**3


def total_memory_bytes() -> int | None:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(state)
        return state.ullTotalPhys if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)) else None
    if platform.system() == "Darwin":
        try:
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=3).strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    try:
        values = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
        for line in values:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError, AttributeError):
        return None


def nvidia_gpus() -> list[dict]:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=5, text=True)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []
    devices = []
    for row in output.splitlines():
        parts = [part.strip() for part in row.rsplit(",", 2)]
        if len(parts) != 3:
            continue
        try:
            devices.append({"name": parts[0], "vram_total_mib": int(parts[1]),
                            "vram_free_mib": int(parts[2]), "backend": "nvidia-smi"})
        except ValueError:
            continue
    return devices


def hardware_inventory() -> dict:
    system = platform.system()
    data = {"platform": system, "machine": platform.machine(),
            "cpu_cores_logical": os.cpu_count(), "system_ram_bytes": total_memory_bytes(),
            "gpus": nvidia_gpus(), "notes": []}
    if system == "Darwin" and platform.machine() == "arm64":
        data["notes"].append("Apple Silicon shares system RAM with GPU; available GPU memory is not directly measured.")
    if not data["gpus"]:
        data["notes"].append("No NVIDIA GPU reported; AMD/Intel/Apple accelerators may still be present.")
    return data


def gguf_fit(file_bytes: int, inventory: dict, *, reserve_gib: float = 2.0) -> dict:
    """Heuristic, not an accuracy or guaranteed loadability check."""
    if file_bytes <= 0:
        raise ValueError("Model size must be positive")
    ram = inventory.get("system_ram_bytes")
    available = max((x.get("vram_free_mib", 0) for x in inventory.get("gpus", [])), default=0)
    required = file_bytes + int(reserve_gib * GIB)
    if available * 1024**2 >= required:
        assessment = "gpu_plausible"
    elif ram is not None and ram >= required:
        assessment = "cpu_or_partial_offload_plausible"
    else:
        assessment = "unknown_or_insufficient"
    return {"model_file_bytes": file_bytes, "estimated_total_bytes": required,
            "available_nvidia_vram_mib": available, "system_ram_bytes": ram,
            "assessment": assessment,
            "warning": "File size plus reserve is only a rough estimate; context length, architecture and backend affect real requirements."}
