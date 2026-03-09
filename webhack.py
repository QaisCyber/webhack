#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                     QaisCyber Toolkit v1.0                    ║
║           Advanced Web Pentesting Automation Tool             ║
║                  For Authorized Testing Only                  ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_DIR    = Path("QaisCyber")
TOOLS_DIR   = BASE_DIR / "tools"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR    = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "wordlist": "/usr/share/wordlists/dirb/common.txt",
    "threads": 10,
    "timeout": 30,
    "user_agent": "QaisCyber/2.0",
    "proxy": "",
    "output_format": "txt",
    "auto_save": True,
}

# ─── Colors (ANSI) ───────────────────────────────────────────────────────────

class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def colored(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"

def info(msg):    print(f"  {colored('[*]', C.CYAN)}  {msg}")
def success(msg): print(f"  {colored('[+]', C.GREEN)} {msg}")
def warning(msg): print(f"  {colored('[!]', C.YELLOW)} {msg}")
def error(msg):   print(f"  {colored('[-]', C.RED)} {msg}")
def section(msg): print(f"\n{colored('━'*55, C.BLUE)}\n  {colored(msg, C.BOLD+C.WHITE)}\n{colored('━'*55, C.BLUE)}")

# ─── Safe Input ───────────────────────────────────────────────────────────────
# FIX: كل input يمر من هنا — يتجاهل EOFError ويتجنب loop مكسور

def safe_input(prompt: str, allow_empty: bool = False) -> str:
    while True:
        try:
            val = input(prompt).strip()
        except EOFError:
            return ""
        if val or allow_empty:
            return val

# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"qaiscyber_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    # FIX: بناء handlers بشكل صحيح بدل السطر الإشكالي
    handlers: list = [logging.FileHandler(log_file)]
    if "--debug" in sys.argv:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return log_file

# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            warning("Config file corrupted, using defaults.")
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    success(f"Config saved → {CONFIG_FILE}")

# ─── Banner ───────────────────────────────────────────────────────────────────

def banner():
    print(f"""
{colored('╔'+'═'*61+'╗', C.CYAN)}
{colored('║', C.CYAN)}                                                             {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('██╗    ██╗███████╗██████╗ ██╗  ██╗ █████╗  ██████╗██╗  ██╗', C.GREEN)}  {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('██║    ██║██╔════╝██╔══██╗██║  ██║██╔══██╗██╔════╝██║ ██╔╝', C.GREEN)}  {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('██║ █╗ ██║█████╗  ██████╔╝███████║███████║██║     █████╔╝ ', C.GREEN)}  {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('██║███╗██║██╔══╝  ██╔══██╗██╔══██║██╔══██║██║     ██╔═██╗ ', C.GREEN)}  {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('╚███╔███╔╝███████╗██████╔╝██║  ██║██║  ██║╚██████╗██║  ██╗', C.GREEN)}  {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored(' ╚══╝╚══╝ ╚══════╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝', C.GREEN)} {colored('║', C.CYAN)}
{colored('║', C.CYAN)}                                                             {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('v1.0', C.BLUE+C.BOLD)}  ──  {colored('Web Pentesting Automation Tool', C.WHITE)}              {colored('║', C.CYAN)}
{colored('║', C.CYAN)}   {colored('⚠  For authorized penetration testing only', C.RED)}               {colored('║', C.CYAN)}
{colored('╚'+'═'*61+'╝', C.CYAN)}
""")

# ─── Setup & Installation ─────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "sqlmap":  {"type": "apt", "pkg": "sqlmap",                                        "check": "sqlmap"},
    "ffuf":    {"type": "apt", "pkg": "ffuf",                                          "check": "ffuf"},
    "nmap":    {"type": "apt", "pkg": "nmap",                                          "check": "nmap"},
    "nikto":   {"type": "apt", "pkg": "nikto",                                         "check": "nikto"},
    # FIX: dalfox يحتاج go build وليس python
    "dalfox":  {"type": "go",  "repo": "https://github.com/hahwul/dalfox.git",        "dir": TOOLS_DIR / "dalfox"},
    "ssrfmap": {"type": "git", "repo": "https://github.com/swisskyrepo/SSRFmap.git",  "dir": TOOLS_DIR / "ssrfmap"},
    # FIX: arjun يُنصب بـ pip وليس git clone
    "arjun":   {"type": "pip", "pkg": "arjun",                                         "check": "arjun"},
    "commix":  {"type": "git", "repo": "https://github.com/commixproject/commix.git", "dir": TOOLS_DIR / "commix"},
}

def run(cmd: str, capture: bool = False) -> Optional[str]:
    logging.info(f"RUN: {cmd}")
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout + result.stderr
        else:
            subprocess.call(cmd, shell=True)
    except KeyboardInterrupt:
        warning("Command interrupted by user.")
    return None

def tool_available(name: str) -> bool:
    return shutil.which(name) is not None

def go_available() -> bool:
    return shutil.which("go") is not None

def setup(force_reinstall: bool = False):
    section("Environment Setup")
    for d in [TOOLS_DIR, RESULTS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
    install_tools(force_reinstall)

# FIX: دالة setup_force كانت مفقودة تماماً
def setup_force():
    setup(force_reinstall=True)

def install_tools(force: bool = False):
    info("Checking and installing required tools...")
    run("sudo apt-get update -qq")

    for name, meta in TOOL_REGISTRY.items():

        # ── apt ──────────────────────────────────────────────────────────────
        if meta["type"] == "apt":
            if force or not tool_available(meta["check"]):
                info(f"Installing {name} via apt...")
                run(f"sudo apt-get install -y {meta['pkg']} -qq")
                if tool_available(meta["check"]):
                    success(f"{name} installed ✓")
                else:
                    error(f"Failed to install {name}")
            else:
                success(f"{name} already available ✓")

        # ── pip ──────────────────────────────────────────────────────────────
        elif meta["type"] == "pip":
            if force or not tool_available(meta["check"]):
                info(f"Installing {name} via pip...")
                run(f"pip3 install {meta['pkg']} -q --break-system-packages")
                if tool_available(meta["check"]):
                    success(f"{name} installed ✓")
                else:
                    error(f"Failed to install {name}")
            else:
                success(f"{name} already available ✓")

        # ── go build ─────────────────────────────────────────────────────────
        elif meta["type"] == "go":
            dest: Path = meta["dir"]
            binary = dest / name
            if force and dest.exists():
                shutil.rmtree(dest)
            if not binary.exists():
                if not go_available():
                    error("Go is not installed. Install with: sudo apt-get install golang")
                    error(f"Skipping {name}.")
                    continue
                info(f"Cloning {name}...")
                run(f"git clone --depth=1 {meta['repo']} {dest} --quiet")
                info(f"Building {name} (may take a moment)...")
                out = run(f"cd {dest} && go build -o {name} . 2>&1", capture=True)
                if binary.exists():
                    success(f"{name} built and ready ✓")
                else:
                    error(f"{name} build failed:\n{out}")
            else:
                success(f"{name} already built ✓")

        # ── git + pip requirements ────────────────────────────────────────────
        elif meta["type"] == "git":
            dest: Path = meta["dir"]
            if force and dest.exists():
                shutil.rmtree(dest)
            if not dest.exists():
                info(f"Cloning {name}...")
                run(f"git clone --depth=1 {meta['repo']} {dest} --quiet")
                req = dest / "requirements.txt"
                if req.exists():
                    run(f"pip3 install -r {req} -q --break-system-packages")
                success(f"{name} cloned ✓")
            else:
                success(f"{name} already present ✓")

    success("All tools ready!\n")

# ─── Target Validation ────────────────────────────────────────────────────────

def validate_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url

def confirm_target(url: str) -> bool:
    print(f"\n  {colored('Target:', C.YELLOW)} {colored(url, C.WHITE+C.BOLD)}")
    ans = safe_input(f"  {colored('Proceed? [y/N]:', C.CYAN)} ", allow_empty=True)
    return ans.lower() == "y"

# ─── Result Saver ─────────────────────────────────────────────────────────────

def save_result(scan_type: str, url: str, output: str, cfg: dict):
    if not cfg.get("auto_save"):
        return
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{scan_type}_{ts}.{cfg['output_format']}"
    path = RESULTS_DIR / name

    if cfg["output_format"] == "json":
        data = {"scan": scan_type, "target": url, "timestamp": ts, "output": output}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    else:
        with open(path, "w") as f:
            f.write(f"Scan: {scan_type}\nTarget: {url}\nDate: {ts}\n{'─'*60}\n{output}")

    success(f"Results saved → {path}")

# ─── Scan Modules ─────────────────────────────────────────────────────────────

def sql_scan(cfg: dict):
    section("SQL Injection Scan  [SQLMap]")
    url = validate_url(safe_input(f"  {colored('Target URL:', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    level = safe_input(f"  {colored('Scan level [1-5, default 2]:', C.CYAN)} ", allow_empty=True) or "2"
    risk  = safe_input(f"  {colored('Risk level [1-3, default 1]:', C.CYAN)} ", allow_empty=True) or "1"
    extra = f"--proxy={cfg['proxy']}" if cfg.get("proxy") else ""
    output_dir = RESULTS_DIR / "sqlmap"
    output_dir.mkdir(exist_ok=True)

    # FIX: threads ثابت على 10 (حد sqlmap الأقصى) + flags لتجاوز WAF
    cmd = (
        f"sqlmap -u \"{url}\" --batch --dbs --forms --crawl=2 "
        f"--level={level} --risk={risk} --threads=10 "
        f"--timeout={cfg['timeout']} --output-dir={output_dir} "
        f"--random-agent --delay=1 --retries=3 --ignore-code=403 {extra}"
    )
    info(f"Running: {colored(cmd, C.DIM)}")
    out = run(cmd, capture=True) or ""
    save_result("sqli", url, out, cfg)

def xss_scan(cfg: dict):
    section("XSS Scan  [Dalfox]")
    url = validate_url(safe_input(f"  {colored('Target URL:', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    # FIX: ابحث عن dalfox في المسار المبني أو في PATH
    dalfox_bin = TOOLS_DIR / "dalfox" / "dalfox"
    if not dalfox_bin.exists():
        if tool_available("dalfox"):
            dalfox_bin = Path(shutil.which("dalfox"))
        else:
            error("Dalfox not found. Run setup (u) first, and make sure Go is installed.")
            return

    mode  = safe_input(f"  {colored('Mode: (1) URL  (2) Pipe  (3) File [default 1]:', C.CYAN)} ", allow_empty=True) or "1"
    extra = f"--proxy {cfg['proxy']}" if cfg.get("proxy") else ""

    if mode == "2":
        cmd = f"echo \"{url}\" | {dalfox_bin} pipe {extra}"
    elif mode == "3":
        fpath = safe_input(f"  {colored('URL list file path:', C.CYAN)} ")
        if not fpath:
            error("No file path provided.")
            return
        cmd = f"cat \"{fpath}\" | {dalfox_bin} pipe {extra}"
    else:
        cmd = f"{dalfox_bin} url \"{url}\" {extra} --follow-redirects"

    info("Running Dalfox...")
    out = run(cmd, capture=True) or ""
    save_result("xss", url, out, cfg)

def idor_scan(cfg: dict):
    section("IDOR / Parameter Discovery  [Arjun]")
    url = validate_url(safe_input(f"  {colored('Target URL:', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    method = safe_input(f"  {colored('Method: GET / POST [default GET]:', C.CYAN)} ", allow_empty=True).upper() or "GET"

    # FIX: arjun الآن في PATH مباشرة بعد pip install
    if not tool_available("arjun"):
        error("Arjun not found. Run setup (u) first.")
        return

    cmd = f"arjun -u \"{url}\" -m {method} --stable -t {cfg['threads']}"
    info("Discovering hidden parameters...")
    out = run(cmd, capture=True) or ""
    save_result("idor", url, out, cfg)

def file_upload_scan(cfg: dict):
    section("File Upload & Directory Fuzzing  [ffuf]")
    url = validate_url(safe_input(f"  {colored('Base URL (FUZZ will be appended):', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    default_wl = cfg["wordlist"]
    wordlist = safe_input(f"  {colored(f'Wordlist [{default_wl}]:', C.CYAN)} ", allow_empty=True) or default_wl
    ext_str  = safe_input(f"  {colored('Extensions [e.g. php,asp,txt | blank to skip]:', C.CYAN)} ", allow_empty=True)
    ext_flag = f"-e {ext_str}" if ext_str else ""

    if not tool_available("ffuf"):
        error("ffuf not found. Run setup (u) first.")
        return

    out_file = RESULTS_DIR / f"ffuf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    cmd = (
        f"ffuf -u \"{url}/FUZZ\" -w {wordlist} {ext_flag} "
        f"-t {cfg['threads']} -timeout {cfg['timeout']} "
        f"-o {out_file} -of json -mc 200,201,204,301,302,307,401,403"
    )
    info("Fuzzing directories and files...")
    run(cmd)
    success(f"Results saved → {out_file}")

def ssrf_scan(cfg: dict):
    section("SSRF Scan  [SSRFMap]")
    # FIX: إضافة validate_url
    url = validate_url(safe_input(f"  {colored('Target URL with parameter (e.g. http://site.com/?url=):', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    ssrfmap = TOOLS_DIR / "ssrfmap" / "ssrfmap.py"
    if not ssrfmap.exists():
        error("SSRFmap not found. Run setup (u) first.")
        return

    cmd = f"python3 \"{ssrfmap}\" -r \"{url}\" --level 3"
    info("Probing for SSRF vulnerabilities...")
    out = run(cmd, capture=True) or ""
    save_result("ssrf", url, out, cfg)

def port_scan(cfg: dict):
    section("Port & Service Scan  [Nmap]")
    target = safe_input(f"  {colored('Target host/IP:', C.CYAN)} ")
    if not target or not confirm_target(target):
        return

    profile = safe_input(f"  {colored('Profile: (1) Quick  (2) Full  (3) Vuln  (4) Stealth [default 1]:', C.CYAN)} ", allow_empty=True) or "1"
    profiles = {
        "1": f"nmap -T4 -F {target}",
        "2": f"nmap -T4 -A -p- {target}",
        "3": f"nmap -T4 --script=vuln {target}",
        "4": f"nmap -T2 -sS -Pn {target}",
    }
    cmd = profiles.get(profile, profiles["1"])
    out_file = RESULTS_DIR / f"nmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    cmd += f" -oN {out_file}"

    if not tool_available("nmap"):
        error("nmap not found. Run setup (u) first.")
        return

    info("Scanning ports...")
    run(cmd)
    success(f"Results saved → {out_file}")

def nikto_scan(cfg: dict):
    section("Web Server Vulnerability Scan  [Nikto]")
    url = validate_url(safe_input(f"  {colored('Target URL:', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    out_file = RESULTS_DIR / f"nikto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    proxy    = f"-useproxy {cfg['proxy']}" if cfg.get("proxy") else ""
    cmd = f"nikto -h \"{url}\" -output {out_file} {proxy}"

    if not tool_available("nikto"):
        error("nikto not found. Run setup (u) first.")
        return

    info("Running Nikto web scanner...")
    run(cmd)
    success(f"Results saved → {out_file}")

def command_injection_scan(cfg: dict):
    section("Command Injection Scan  [Commix]")
    url = validate_url(safe_input(f"  {colored('Target URL:', C.CYAN)} "))
    if not url or not confirm_target(url):
        return

    commix = TOOLS_DIR / "commix" / "commix.py"
    if not commix.exists():
        error("Commix not found. Run setup (u) first.")
        return

    cmd = f"python3 \"{commix}\" --url=\"{url}\" --batch --level=2"
    info("Testing for command injection...")
    out = run(cmd, capture=True) or ""
    save_result("cmdi", url, out, cfg)

def view_results():
    section("Saved Scan Results")
    # FIX: فلتر is_file() لتجنب الكراش على المجلدات
    files = sorted(
        [f for f in RESULTS_DIR.rglob("*") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    if not files:
        warning("No results found yet.")
        return

    for i, f in enumerate(files[:20], 1):
        size = f.stat().st_size
        ts   = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {colored(str(i).rjust(2), C.YELLOW)}. {colored(f.name, C.WHITE)}  {colored(f'({size} bytes)', C.DIM)}  {colored(ts, C.DIM)}")

    choice = safe_input(f"\n  {colored('Enter file number to view (or Enter to skip):', C.CYAN)} ", allow_empty=True)
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            try:
                with open(files[idx]) as fh:
                    print(f"\n{colored('─'*60, C.DIM)}\n{fh.read()}\n{colored('─'*60, C.DIM)}")
            except Exception as e:
                error(f"Could not read file: {e}")

def settings_menu(cfg: dict) -> dict:
    section("Settings")
    print(f"""
  {colored('Current Settings:', C.BOLD)}
  1. Wordlist      : {colored(cfg['wordlist'], C.WHITE)}
  2. Threads       : {colored(str(cfg['threads']), C.WHITE)}
  3. Timeout       : {colored(str(cfg['timeout']), C.WHITE)}s
  4. Proxy         : {colored(cfg['proxy'] or 'None', C.WHITE)}
  5. Output Format : {colored(cfg['output_format'], C.WHITE)}
  6. Auto Save     : {colored(str(cfg['auto_save']), C.WHITE)}
  0. Back
""")
    opt = safe_input(f"  {colored('Option:', C.CYAN)} ", allow_empty=True)
    prompts = {
        "1": ("wordlist",      "New wordlist path"),
        "2": ("threads",       "Thread count"),
        "3": ("timeout",       "Timeout (seconds)"),
        "4": ("proxy",         "Proxy (e.g. http://127.0.0.1:8080)"),
        "5": ("output_format", "Format [txt/json]"),
        "6": ("auto_save",     "Auto save [true/false]"),
    }
    if opt in prompts:
        key, label = prompts[opt]
        val = safe_input(f"  {colored(label+':', C.CYAN)} ")
        if key in ("threads", "timeout"):
            cfg[key] = int(val) if val.isdigit() else cfg[key]
        elif key == "auto_save":
            cfg[key] = val.lower() == "true"
        else:
            cfg[key] = val
        save_config(cfg)
    return cfg

# ─── Main Menu ────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "SQL Injection Scan",              "sql_scan"),
    ("2", "XSS Scan",                        "xss_scan"),
    ("3", "IDOR / Parameter Discovery",      "idor_scan"),
    ("4", "File Upload & Directory Fuzzing", "file_upload_scan"),
    ("5", "SSRF Scan",                       "ssrf_scan"),
    ("6", "Port & Service Scan",             "port_scan"),
    ("7", "Web Server Vulnerability Scan",   "nikto_scan"),
    ("8", "Command Injection Scan",          "command_injection_scan"),
    ("r", "View Results",                    "view_results"),
    ("s", "Settings",                        "settings_menu"),
    ("u", "Update / Reinstall Tools",        "setup_force"),
    ("0", "Exit",                            "exit"),
]

SCAN_MAP = {
    "sql_scan":               sql_scan,
    "xss_scan":               xss_scan,
    "idor_scan":              idor_scan,
    "file_upload_scan":       file_upload_scan,
    "ssrf_scan":              ssrf_scan,
    "port_scan":              port_scan,
    "nikto_scan":             nikto_scan,
    "command_injection_scan": command_injection_scan,
}

def print_menu():
    print(f"\n  {colored('┌─ QaisCyber Menu ─────────────────────────────┐', C.CYAN)}")
    for key, label, _ in MENU_ITEMS:
        k = colored(f" {key} ", C.YELLOW+C.BOLD)
        print(f"  {colored('│', C.CYAN)} {k}  {label:<40}{colored('│', C.CYAN)}")
    print(f"  {colored('└──────────────────────────────────────────────┘', C.CYAN)}")

def menu(cfg: dict):
    while True:
        print_menu()
        choice = safe_input(f"\n  {colored('Select option:', C.CYAN)} ", allow_empty=True).lower()

        # FIX: تجاهل Enter الفارغ بدل "Invalid option"
        if not choice:
            continue

        if choice == "0":
            success("Goodbye! — QaisCyber")
            sys.exit(0)
        elif choice == "u":
            setup_force()
        elif choice == "r":
            view_results()
        elif choice == "s":
            cfg = settings_menu(cfg)
        else:
            fn_name = {k: fn for k, _, fn in MENU_ITEMS}.get(choice)
            if fn_name in SCAN_MAP:
                try:
                    SCAN_MAP[fn_name](cfg)
                except KeyboardInterrupt:
                    warning("\nScan cancelled.")
            else:
                error("Invalid option. Try again.")

# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="QaisCyber v2.0 - Web Pentesting Automation",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--setup",     action="store_true", help="Install/update all tools and exit")
    parser.add_argument("--debug",     action="store_true", help="Enable verbose logging to console")
    parser.add_argument("--no-banner", action="store_true", help="Skip the banner")
    parser.add_argument(
        "--scan", choices=["sqli", "xss", "idor", "fuzz", "ssrf", "ports", "nikto", "cmdi"],
        help="Run a single scan directly from CLI"
    )
    parser.add_argument("--url", help="Target URL (for direct --scan mode)")
    return parser.parse_args()

DIRECT_SCAN_MAP = {
    "sqli":  "sql_scan",
    "xss":   "xss_scan",
    "idor":  "idor_scan",
    "fuzz":  "file_upload_scan",
    "ssrf":  "ssrf_scan",
    "ports": "port_scan",
    "nikto": "nikto_scan",
    "cmdi":  "command_injection_scan",
}

def main():
    args     = parse_args()
    log_file = setup_logging()

    if not args.no_banner:
        banner()

    cfg = load_config()

    print(f"  {colored('Session log:', C.DIM)} {log_file}")
    print(f"  {colored('Results dir:', C.DIM)} {RESULTS_DIR}\n")

    if args.setup:
        setup(force_reinstall=True)
        sys.exit(0)

    if args.scan:
        setup()
        SCAN_MAP[DIRECT_SCAN_MAP[args.scan]](cfg)
        sys.exit(0)

    setup()
    menu(cfg)

if __name__ == "__main__":
    main()

