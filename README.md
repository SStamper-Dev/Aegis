# Aegis

An SSH brute-force defense daemon using Python.

Aegis watches `/var/log/auth.log` for failed SSH logins, tracks source IPs, and when a threshold is exceeded it blocks the attacker with UFW (`ufw deny from <ip>`). An optional local dashboard (`aegis-view.py` + `aegis.html`) reads a JSON state file and shows recent failures and blocked IPs in your browser.

## Defender PC/VM (runs Aegis)

**Prerequisites**

- Ubuntu with OpenSSH installed and enabled (so attempts are logged to `auth.log`)
- UFW installed and enabled; allow SSH (TCP port 22) before testing so you are not locked out
- Python 3 (stdlib only for `aegis.py` and `aegis-view.py`)

**Run**

```bash
sudo python3 aegis.py
```
The SSH attempt threshold and timeframe can also be altered with -n and -w, respectively

```bash
sudo python3 aegis.py -n 5 -w 60
```

Optional: run the dashboard on the same machine (in another terminal; does not need to be root if it can read the state file):

```bash
python3 aegis-view.py
```

Then open `http://127.0.0.1:8765/` in a browser.

## Attacker PC/VM (e.g. Hammer)

Use the separate Hammer tool on another machine to generate failed logins against the defender’s SSH service. Instructions for the Hammer tool can be found in its respective Github repository.

`aegis.py` writes state to `/tmp/aegis_state.json` by default (`-s` to change). `aegis-view.py` reads that file and serves `aegis.html` plus the logo (`aegis-logo.svg`) from the same folder.
