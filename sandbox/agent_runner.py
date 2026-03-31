import sys
import json
import importlib.util
import builtins

# ============================================================
# PHASE 0: SANDBOX SETUP
#
# CRITICAL ORDER: import os/subprocess/socket/shutil FIRST,
# then neuter their dangerous functions, THEN hard-block the
# remaining dangerous modules.
#
# Reason: subprocess.py and socket.py both import `signal`
# internally at module load time. If we set signal=None before
# importing them, agent_runner.py itself crashes at startup.
# ============================================================

_NOOP = lambda *a, **kw: (_ for _ in ()).throw(
    PermissionError("[Sandbox] This operation is blocked.")
)

# ── Step 1: Import all ML-dependency modules FIRST (clean sys.modules) ───────

import os as _os
import subprocess as _subprocess
import socket as _socket
import shutil as _shutil

# ── Step 2: Neuter dangerous functions in each module ────────────────────────

# os: block process-spawn and filesystem-write functions
for _fn in [
    "system", "popen", "execv", "execve", "execvp", "execvpe",
    "execl", "execle", "execlp", "execlpe",
    "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe",
    "fork", "forkpty", "kill", "killpg", "abort", "startfile",
    "remove", "unlink", "rmdir", "removedirs",
    "rename", "renames", "replace",
    "makedirs", "mkdir", "symlink", "link",
    "chmod", "chown", "chroot", "truncate",
]:
    if hasattr(_os, _fn):
        setattr(_os, _fn, _NOOP)
sys.modules["os"] = _os

# subprocess: allow import (pandas/torch use it for version detection),
# but block all functions that actually spawn processes
for _fn in [
    "Popen", "run", "call", "check_call",
    "check_output", "getoutput", "getstatusoutput",
]:
    if hasattr(_subprocess, _fn):
        setattr(_subprocess, _fn, _NOOP)
sys.modules["subprocess"] = _subprocess

# socket: allow import (torch IPC uses it internally),
# but block all functions that open real network connections
for _fn in ["create_connection", "create_server", "getaddrinfo", "gethostbyname"]:
    if hasattr(_socket, _fn):
        setattr(_socket, _fn, _NOOP)
for _fn in ["connect", "connect_ex", "bind", "listen", "accept",
            "sendall", "sendto", "recvfrom", "recvfrom_into"]:
    if hasattr(_socket.socket, _fn):
        setattr(_socket.socket, _fn, _NOOP)
sys.modules["socket"] = _socket

# shutil: allow import (pandas uses it), block write/delete operations
for _fn in [
    "rmtree", "move", "copy", "copy2", "copyfile",
    "copyfileobj", "copytree", "make_archive", "unpack_archive",
]:
    if hasattr(_shutil, _fn):
        setattr(_shutil, _fn, _NOOP)
sys.modules["shutil"] = _shutil

# ── Step 3: Import ctypes (pandas needs it) then neuter WinAPI access ────────
try:
    import ctypes as _ctypes
    # Block calling into Win32/libc — the dangerous part of ctypes
    if hasattr(_ctypes, "windll"):
        _ctypes.windll = None
    if hasattr(_ctypes, "cdll"):
        _ctypes.cdll = None
    if hasattr(_ctypes, "CDLL"):
        setattr(_ctypes, "CDLL", _NOOP)
    if hasattr(_ctypes, "WinDLL"):
        setattr(_ctypes, "WinDLL", _NOOP)
    sys.modules["ctypes"] = _ctypes
except ImportError:
    sys.modules["ctypes"] = None

# ── Step 4: Hard-block modules participants must never touch ──────────────────
for _mod in [
    "winreg",
    "signal",
    "multiprocessing", "multiprocessing.pool",
    "concurrent", "concurrent.futures",
    "urllib", "urllib3", "requests", "httpx", "aiohttp",
]:
    sys.modules[_mod] = None

# ── Step 4: Restrict open() — allow reads (for loading model weights),
#   block all writes/appends/creates ──────────────────────────────────────────
_real_open = builtins.open

def _safe_open(file, *args, **kwargs):
    mode = args[0] if args else kwargs.get("mode", "r")
    if any(c in str(mode) for c in ("w", "a", "x", "+")):
        raise PermissionError("[Sandbox] File write access is blocked.")
    return _real_open(file, *args, **kwargs)

builtins.open = _safe_open


def main():
    # 1. Read JSON state from stdin
    raw_input = builtins.input()
    try:
        state = json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"JSON_ERR: {e}\n")
        print("COOPERATE")
        return

    # 2. Dynamically load the participant's module
    agent_file = "my_agent.py"
    try:
        spec = importlib.util.spec_from_file_location("participant_agent", agent_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        sys.stderr.write(f"LOAD_ERR: {e}\n")
        print("COOPERATE")
        return

    # 3. Validate the decide function exists
    if not hasattr(module, "decide"):
        sys.stderr.write("NO_DECIDE_ERR\n")
        print("COOPERATE")
        return

    # ============================================================
    # PHASE 2: POST-LOAD LOCKDOWN
    # Module is compiled. Kill remaining escape hatches before
    # handing control to the participant's decide().
    # ============================================================
    builtins.eval = None
    builtins.exec = None
    builtins.compile = None
    # Nuke sys so the agent can't inspect sys.modules or call sys.exit()
    sys.modules["sys"] = None

    # 4. Execute the agent's decide function
    try:
        action = module.decide(state)
        print(str(action).strip())
    except Exception:
        print("COOPERATE")


if __name__ == "__main__":
    main()
