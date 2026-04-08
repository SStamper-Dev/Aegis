import re
import json
import time
import argparse
import subprocess
import sys
import os
from collections import defaultdict
from pathlib import Path

FAILED_PW = re.compile(r"Failed password for .+ from ([\d.]+) ")


def parse_failed_ip(line):
    # Pulls source IP from sshd "Failed password" lines in auth.log
    m = FAILED_PW.search(line)
    return m.group(1) if m else None


def block_ip(ip):
    # Drops future traffic from this IP via UFW (run as root)
    result = subprocess.run(
        ["ufw", "deny", "from", ip],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout).strip()
        print(f"[!] UFW failed to block {ip}: {err}")
        return False
    print(f"[+] UFW rule added for {ip}")
    return True


def flush_state(state_path, state):
    # Writes atomically so aegis-view can read a consistent snapshot
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    tmp.replace(state_path)
    try:
        os.chmod(state_path, 0o644)
    except OSError:
        pass


def watch_log(path, threshold, window_sec, state_path):
    # Tails auth.log and blocks IPs that exceed failed attempt threshold in the window
    attempts = defaultdict(list)
    blocked = set()
    state = {
        "log": path,
        "threshold": threshold,
        "window": window_sec,
        "blocked": [],
        "recent_failures": [],
    }
    flush_state(state_path, state)

    try:
        f = open(path, "r", encoding="utf-8", errors="replace")
    except PermissionError:
        print(f"[!] Cannot read '{path}'. Run as root (e.g. sudo python3 aegis.py).")
        sys.exit(1)

    print(f"[*] Watching {path} (threshold={threshold} failures / {window_sec}s window)...")
    print(f"[*] State file: {state_path}")

    try:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue

            ip = parse_failed_ip(line)
            if not ip:
                continue

            now = time.time()
            state["recent_failures"].append({"ip": ip, "t": now})
            state["recent_failures"] = state["recent_failures"][-100:]
            flush_state(state_path, state)

            attempts[ip] = [t for t in attempts[ip] if now - t < window_sec]
            attempts[ip].append(now)

            if ip in blocked:
                continue

            if len(attempts[ip]) >= threshold:
                print(f"[!] Blocking {ip} ({len(attempts[ip])} failed logins in window).")
                if block_ip(ip):
                    blocked.add(ip)
                    state["blocked"].append({"ip": ip, "t": now})
                    flush_state(state_path, state)
    finally:
        f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="The Aegis: Monitor auth.log and block brute-force sources with UFW."
    )
    parser.add_argument(
        "-l",
        "--log",
        default="/var/log/auth.log",
        help="Path to auth.log (default: /var/log/auth.log)",
    )
    parser.add_argument(
        "-n",
        "--threshold",
        type=int,
        default=5,
        help="Failed attempts from one IP before blocking (default: 5)",
    )
    parser.add_argument(
        "-w",
        "--window",
        type=int,
        default=60,
        help="Sliding window in seconds for counting failures (default: 60)",
    )
    parser.add_argument(
        "-s",
        "--state",
        default="/tmp/aegis_state.json",
        help="JSON state file for aegis-view.py (default: /tmp/aegis_state.json)",
    )

    args = parser.parse_args()
    watch_log(args.log, args.threshold, args.window, args.state)
