import re
import time
import argparse
import subprocess
import sys
from collections import defaultdict

FAILED_PW = re.compile(r"Failed password for .+ from ([\d.]+) ")


def parse_failed_ip(line):
    # Pulls source IP from sshd "Failed password" lines in auth.log
    m = FAILED_PW.search(line)
    return m.group(1) if m else None


def block_ip(ip):
    # Drops future traffic from this IP via UFW (run as root)
    subprocess.run(
        ["ufw", "deny", "from", ip],
        capture_output=True,
        text=True,
    )


def watch_log(path, threshold, window_sec):
    # Tails auth.log and blocks IPs that exceed failed attempt threshold in the window
    attempts = defaultdict(list)
    blocked = set()

    try:
        f = open(path, "r", encoding="utf-8", errors="replace")
    except PermissionError:
        print(f"[!] Cannot read '{path}'. Run as root (e.g. sudo python3 aegis.py).")
        sys.exit(1)

    print(f"[*] Watching {path} (threshold={threshold} failures / {window_sec}s window)...")

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
            attempts[ip] = [t for t in attempts[ip] if now - t < window_sec]
            attempts[ip].append(now)

            if ip in blocked:
                continue

            if len(attempts[ip]) >= threshold:
                print(f"[!] Blocking {ip} ({len(attempts[ip])} failed logins in window).")
                block_ip(ip)
                blocked.add(ip)
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

    args = parser.parse_args()
    watch_log(args.log, args.threshold, args.window)
