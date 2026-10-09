"""Windows repository launcher. Only the launcher itself is frozen into the EXE."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser

ACTIONS = ("all", "tests", "backend", "frontend", "build", "readiness", "live-probe", "rehearse", "demo", "recovery", "smoke")


def find_repo(explicit=None):
    candidates = [Path(explicit)] if explicit else [Path.cwd(), Path(sys.executable).parent, Path(__file__).resolve().parent]
    for candidate in candidates:
        for root in ((candidate,) if explicit else (candidate, *candidate.parents)):
            if (root / "backend/pyproject.toml").is_file() and (root / "scripts/dev.mjs").is_file():
                return root.resolve()
    raise ValueError("Select the Astra repository folder (containing backend, frontend and scripts).")


def tool(name):
    found = shutil.which(name)
    if not found and name == "uv":
        fallback = Path.home() / ".local/bin/uv.exe"
        found = str(fallback) if fallback.is_file() else None
    if not found:
        raise RuntimeError(f"{name} is not installed or is missing from PATH. See README setup instructions.")
    return found


def npm_command(*args):
    # Invoke npm's JS entrypoint directly: no shell parsing of paths or arguments.
    node = Path(tool("node"))
    npm = shutil.which("npm")
    candidates = [node.parent / "node_modules/npm/bin/npm-cli.js"]
    if npm:
        candidates.insert(0, Path(npm).resolve().parent / "node_modules/npm/bin/npm-cli.js")
    for entry in candidates:
        if entry.is_file():
            return [str(node), str(entry), *args]
    raise RuntimeError("Cannot find npm-cli.js beside Node/npm. Install the standard Node.js distribution.")


def dotenv_values(path, names):
    """Read selected KEY=value pairs from the repository .env (the frozen launcher cannot import the app)."""
    found = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for line in lines:
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if not sep or key not in names:
            continue
        if value[:1] in {'"', "'"} and value.find(value[0], 1) > 0:
            value = value[1:value.find(value[0], 1)]
        else:
            value = value.split(" #", 1)[0].strip()
        found[key] = value
    return found


def environment(root, artifact, profile):
    env = dict(os.environ)
    # Services read the same .env; the launcher needs the tokens for its own HTTP checks and the dashboard.
    for key, value in dotenv_values(Path(root) / ".env", {"API_TOKEN", "SELLER_API_TOKEN"}).items():
        env.setdefault(key, value)
    env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", NO_COLOR="1", NO_OPEN="1",
               PAYMENTS_MODE="simulated", LEDGER_PATH=str(artifact / "buyer.db"),
               SELLER_STORE_PATH=str(artifact / "seller.db"),
               AUDIO_DIR=str(artifact / "audio"), CRASH_AFTER_LOCK="0",
               SELLER_URL="http://127.0.0.1:8001", VITE_BUYER_URL="http://127.0.0.1:8000",
               VITE_SELLER_URL="http://127.0.0.1:8001", GUARD_CAP="10", GUARD_APPROVAL_OVER="8",
               SELLER_FLOOR="7", SELLER_OPENING_ASK="18", MAX_ROUNDS="6")
    if profile == "sample":
        # Offline providers are not a production profile: STRICT_LIVE would refuse to start them.
        env.update(LLM_MODE="mock", SELLER_LLM_MODE="mock", APIFY_MODE="sample", TTS_MODE="off", STRICT_LIVE="0")
    return env


class WindowsJob:
    """Kill only processes owned by this invocation, including grandchildren."""
    def __init__(self):
        self.handle = None
        if os.name != "nt":
            raise RuntimeError("This launcher targets Windows.")
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                        ("active", wintypes.DWORD), ("affinity", ctypes.c_size_t),
                        ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("ro", "wo", "oo", "rb", "wb", "ob")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def attach(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Popen closes the primary thread handle. Resume the suspended process only
        # after assignment; this also contains Windows venv redirector children.
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        ntdll.NtResumeProcess.restype = ctypes.c_long
        status = ntdll.NtResumeProcess(int(process._handle))
        if status < 0:
            raise OSError(f"Could not resume owned process (NTSTATUS {status:#x}).")

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class Runner:
    def __init__(self, root, profile="sample", emit=print, allow_live=False):
        self.root = find_repo(root)
        self.profile, self.emit, self.allow_live = profile, emit, allow_live
        self.artifact = self.root / "backend/data" / f"launcher-{uuid.uuid4().hex[:10]}"
        self.artifact.mkdir(parents=True)
        self.stop_event = threading.Event()
        self.results = []
        self.report = {"passed": False, "profile": profile, "payments": "SIMULATED", "results": self.results}
        self.log = (self.artifact / "launcher.log").open("w", encoding="utf-8")
        self.lock = threading.Lock()

    def say(self, line):
        with self.lock:
            self.log.write(line + "\n")
            self.log.flush()
            self.emit(line)

    def stop(self):
        self.stop_event.set()

    def launch(self, command, cwd, env, job):
        # Child waits for our stdin byte until assigned to the Job Object. This avoids
        # a race where a fast child could spawn grandchildren before ownership attaches.
        python = self.root / "backend/.venv/Scripts/python.exe"
        if not python.is_file():
            raise RuntimeError("Backend environment missing. Run uv sync --directory backend first.")
        gate = [str(python), str(self.root / "scripts/desktop/process_gate.py"), *command]
        # Frozen apps change the DLL search directory; external Python/Node must use
        # their own runtime DLLs rather than those unpacked by PyInstaller.
        dll_api = ctypes.WinDLL("kernel32", use_last_error=True) if getattr(sys, "frozen", False) else None
        if dll_api:
            dll_api.SetDllDirectoryW.argtypes = [wintypes.LPCWSTR]
            dll_api.SetDllDirectoryW(None)
        try:
            process = subprocess.Popen(gate, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW | 0x4,  # CREATE_SUSPENDED
                                       text=True, encoding="utf-8", errors="replace")
        finally:
            if dll_api:
                dll_api.SetDllDirectoryW(sys._MEIPASS)
        try:
            job.attach(process)
            process.stdin.write("G\n")
            process.stdin.flush()
            process.stdin.close()
        except BaseException:
            process.kill()
            process.wait()
            raise
        def reader():
            for line in process.stdout:
                self.say(line.rstrip())
            process.stdout.close()
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        return process, thread

    def command(self, label, command, cwd, env):
        self.say(f"\n--- {label} ---")
        job = WindowsJob()
        process = thread = None
        try:
            process, thread = self.launch(command, cwd, env, job)
            while process.poll() is None and not self.stop_event.wait(.1):
                pass
            if self.stop_event.is_set():
                self.say("Stopped by user.")
                code = -1
            else:
                code = process.returncode
        finally:
            job.close()
            if process:
                process.wait(timeout=10)
            if thread:
                thread.join(timeout=10)
        self.results.append({"check": label, "exit_code": code, "passed": code == 0})
        self.say(f"{'PASS' if code == 0 else 'FAIL'}: {label} (exit {code})")
        return code == 0

    def demo(self, env, *, crash=False, smoke=False):
        if not (self.root / "frontend/node_modules/vite/bin/vite.js").is_file():
            raise RuntimeError("Frontend dependencies missing. Run npm ci --prefix frontend first.")
        ports = [8000, 8001, 5173]
        if smoke:
            ports = []
            while len(ports) < 3:
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                    if port not in ports:
                        ports.append(port)
        buyer_url, seller_url, dashboard_url = [f"http://127.0.0.1:{p}" for p in ports]
        token = env.get("API_TOKEN", "")
        # Only the dev server gets the token (never a production build written to disk).
        env = {**env, "SELLER_URL": seller_url, "VITE_BUYER_URL": buyer_url, "VITE_SELLER_URL": seller_url,
               "VITE_API_TOKEN": token}
        # Refuse occupied ports; never stop or attach to another terminal's services.
        reserved = []
        try:
            for port in ports:
                sock = socket.socket()
                reserved.append(sock)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError("Ports 8000, 8001 or 5173 are busy. Stop the existing demo in its terminal first.") from exc
        finally:
            for sock in reserved:
                sock.close()
        job = WindowsJob()
        processes = []
        try:
            commands = [([tool("uv"), "run", "python", "scripts/up.py", *(["--crash"] if crash else [])], self.root / "backend")]
            if smoke:
                commands = [([tool("uv"), "run", "python", "-m", "uvicorn", f"app.{name}.app:app", "--host", "127.0.0.1", "--port", str(port)], self.root / "backend")
                            for name, port in (("seller", ports[1]), ("buyer", ports[0]))]
            commands.append(([tool("node"), "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(ports[2]), "--strictPort"], self.root / "frontend"))
            for cmd, cwd in commands:
                processes.append(self.launch(cmd, cwd, env, job))
            deadline = time.monotonic() + 60
            while True:
                if self.stop_event.is_set():
                    return False
                if any(p.poll() is not None for p, _ in processes):
                    raise RuntimeError("A demo service exited. Inspect the log above.")
                try:
                    for url in (buyer_url + "/health", seller_url + "/health", dashboard_url):
                        request(url, token=token)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Demo startup timed out.")
                    self.stop_event.wait(.25)
            self.say(f"READY: {dashboard_url} — SIMULATED payments; isolated ledger.")
            if smoke:
                for mode, expected in (("honest", "released"), ("con", "blocked"), ("junk", "refunded")):
                    deal_id = request(buyer_url + "/tasks", {"demo_mode": mode}, token=token)["deal_id"]
                    deadline = time.monotonic() + 45
                    while not self.stop_event.is_set():
                        deals = request(buyer_url + "/deals", token=token)
                        deal = next((d for d in deals if d["deal_id"] == deal_id), {})
                        if deal.get("status") == expected:
                            self.say(f"PASS: sample {mode} -> {expected}")
                            break
                        if time.monotonic() > deadline:
                            raise RuntimeError(f"Sample {mode} did not reach {expected} (status {deal.get('status')}).")
                        self.stop_event.wait(.1)
                    if self.stop_event.is_set():
                        return False
                balance = request(buyer_url + "/balances", token=token)
                if (balance["buyer"], balance["seller"], balance["escrow"]) != (93, 7, 0):
                    raise RuntimeError("Sample balance conservation failed.")
                self.results.append({"check": "sample HTTP demo: release/block/refund and balances", "passed": True})
                return True
            while not self.stop_event.wait(.2):
                if any(p.poll() is not None for p, _ in processes):
                    raise RuntimeError("A demo service stopped unexpectedly.")
            return True
        finally:
            job.close()
            for process, thread in processes:
                process.wait(timeout=10)
                thread.join(timeout=10)
            self.say("Owned demo services stopped; ledger and logs preserved.")

    def run(self, action):
        try:
            if action not in ACTIONS:
                raise ValueError("Unknown action.")
            if (action in ("live-probe", "rehearse") or (self.profile == "configured" and action in ("demo", "recovery"))) and not self.allow_live:
                raise ValueError("Enable provider usage first. Live actions can use subscription/API credits.")
            if action in ("live-probe", "rehearse") and self.profile != "configured":
                raise ValueError("Select the Configured profile for live provider checks.")
            self.say(f"Repository: {self.root}\nArtifacts: {self.artifact}\nPayments: SIMULATED")
            env = environment(self.root, self.artifact, self.profile)
            sample = environment(self.root, self.artifact, "sample")
            backend = self.root / "backend"
            uv = [tool("uv"), "run"]
            checks = {
                "readiness": ("Local readiness", [*uv, "python", "scripts/readiness.py"], env),
                "live-probe": ("Live readiness (provider credits)", [*uv, "python", "scripts/readiness.py", "--live-probe"], env),
                "backend": ("Backend tests", [*uv, "pytest", "-q"], sample),
                "rehearse": ("Live four-act rehearsal plus approve/decline", [*uv, "python", "scripts/rehearse.py"], env),
            }
            selected = ("readiness", "backend", "frontend", "build", "smoke") if action == "all" else (("backend", "frontend", "build") if action == "tests" else (action,))
            passed = True
            for check in selected:
                if self.stop_event.is_set():
                    passed = False
                    break
                if check in checks:
                    label, cmd, check_env = checks[check]
                    ok = self.command(label, cmd, backend, check_env)
                elif check in ("frontend", "build"):
                    ok = self.command("Frontend tests" if check == "frontend" else "Frontend production build",
                                      npm_command("run", "test" if check == "frontend" else "build"), self.root / "frontend", sample)
                else:
                    ok = self.demo(sample if check == "smoke" else env, crash=check == "recovery", smoke=check == "smoke")
                passed = ok and passed
            self.report["passed"] = passed
        except Exception as exc:
            self.say(f"FAIL: {exc}")
            self.report["error"] = str(exc)
        finally:
            self.report["cancelled"] = self.stop_event.is_set()
            self.report["artifact_dir"] = str(self.artifact)
            (self.artifact / "report.json").write_text(json.dumps(self.report, indent=2), encoding="utf-8")
            self.say(f"{'PASS' if self.report['passed'] else 'FAIL'}: {action}. Report: {self.artifact / 'report.json'}")
            self.log.close()
        return 0 if self.report["passed"] else 1


def request(url, data=None, token=""):
    payload = None if data is None else json.dumps(data).encode()
    headers = {"Content-Type": "application/json", **({"X-API-Token": token} if token else {})}
    req = urllib.request.Request(url, payload, headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=5) as response:
        body = response.read()
        return json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body


def gui(initial_root):
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
    window = tk.Tk()
    window.title("Astra — repository launcher")
    window.geometry("960x720")
    window.minsize(780, 620)
    events = queue.Queue()
    state = {"runner": None, "thread": None, "closing": False}
    root_var = tk.StringVar(value=str(initial_root or ""))
    profile = tk.StringVar(value="sample")
    allow = tk.BooleanVar(value=False)
    frame = ttk.Frame(window, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Astra / The Haggle", font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Run the repository and check the system. All launcher payments are SIMULATED.").pack(anchor="w", pady=(4, 12))
    path_row = ttk.Frame(frame)
    path_row.pack(fill="x")
    ttk.Entry(path_row, textvariable=root_var).pack(side="left", fill="x", expand=True)
    def browse():
        selected = filedialog.askdirectory(title="Select Astra repository")
        if selected:
            root_var.set(selected)
    ttk.Button(path_row, text="Browse…", command=browse).pack(side="left", padx=5)
    options = ttk.Frame(frame)
    options.pack(fill="x", pady=12)
    ttk.Label(options, text="Profile:").pack(side="left")
    ttk.Radiobutton(options, text="Sample (no keys)", variable=profile, value="sample").pack(side="left", padx=8)
    ttk.Radiobutton(options, text="Configured (.env providers)", variable=profile, value="configured").pack(side="left")
    ttk.Checkbutton(frame, text="Enable provider usage (subscription, ElevenLabs and configured Apify credits)", variable=allow).pack(anchor="w")
    status = tk.StringVar(value="Ready. Requires Node.js/npm, uv, uv sync --directory backend and npm ci --prefix frontend.")
    buttons = []
    def start(action):
        if state["thread"] and state["thread"].is_alive():
            return
        try:
            runner = Runner(root_var.get(), profile.get(), events.put, allow.get())
        except Exception as exc:
            messagebox.showerror("Cannot start", str(exc))
            return
        state["runner"] = runner
        status.set(f"Running: {action}")
        for button in buttons:
            button.configure(state="disabled")
        def work():
            result = runner.run(action)
            events.put(("done", result))
        state["thread"] = threading.Thread(target=work, daemon=True)
        state["thread"].start()
    grid = ttk.Frame(frame)
    grid.pack(fill="x", pady=12)
    labels = [("Start demo", "demo"), ("Start recovery demo", "recovery"), ("All local checks", "all"),
              ("Development tests + build", "tests"), ("Local readiness", "readiness"), ("Sample HTTP smoke", "smoke"),
              ("Live provider probes", "live-probe"), ("Live four-act rehearsal", "rehearse")]
    for i, (label, action) in enumerate(labels):
        button = ttk.Button(grid, text=label, command=lambda a=action: start(a))
        button.grid(row=i // 3, column=i % 3, sticky="ew", padx=3, pady=3)
        buttons.append(button)
    for i in range(3):
        grid.columnconfigure(i, weight=1)
    bar = ttk.Frame(frame)
    bar.pack(fill="x")
    ttk.Button(bar, text="Stop current action", command=lambda: state["runner"] and state["runner"].stop()).pack(side="left")
    ttk.Button(bar, text="Open dashboard", command=lambda: webbrowser.open("http://127.0.0.1:5173")).pack(side="left", padx=6)
    ttk.Button(bar, text="Open logs/report", command=lambda: state["runner"] and os.startfile(state["runner"].artifact)).pack(side="left")
    ttk.Label(frame, textvariable=status, wraplength=880).pack(anchor="w", pady=10)
    output = scrolledtext.ScrolledText(frame, wrap="word", height=12, font=("Consolas", 10), state="disabled")
    output.pack(fill="both", expand=True)
    ttk.Label(frame, text="Stop the demo before running checks. Live rehearsal uses cached listings and fresh speech; no real escrow.\nCheck playback and approval/pause controls in the dashboard manually.", wraplength=880).pack(anchor="w", pady=(8, 0))
    def pump():
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, tuple):
                status.set("Finished successfully. See logs/report." if event[1] == 0 else "Check failed or stopped. See logs/report.")
                for button in buttons:
                    button.configure(state="normal")
            else:
                output.configure(state="normal")
                output.insert("end", event + "\n")
                output.see("end")
                output.configure(state="disabled")
                if event.startswith("READY:"):
                    status.set("Demo ready — click Open dashboard. Stop current action when finished.")
        if state["closing"] and (not state["thread"] or not state["thread"].is_alive()):
            window.destroy()
            return
        window.after(100, pump)
    def close():
        state["closing"] = True
        status.set("Stopping owned processes…")
        if state["runner"]:
            state["runner"].stop()
    window.protocol("WM_DELETE_WINDOW", close)
    pump()
    window.mainloop()


def main(argv=None):
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--run", choices=ACTIONS)
    parser.add_argument("--profile", choices=("sample", "configured"), default="sample")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--report", type=Path, help="Also write a machine-readable result here")
    args = parser.parse_args(argv)
    if args.run:
        report = {"passed": False}
        try:
            runner = Runner(find_repo(args.repo), args.profile, lambda line: print(line) if sys.stdout else None, args.allow_live)
            code = runner.run(args.run)
            report = runner.report
        except Exception as exc:
            report["error"] = str(exc)
            code = 1
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return code
    try:
        root = find_repo(args.repo)
    except ValueError:
        root = args.repo
    gui(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
