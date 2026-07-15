#!/usr/bin/env python3
"""
Profils de conteneurs Docker pour la generation de dataset.
Profile de campagne Docker.
Profils : benign_ssh, benign_dns, benign_http, benign_ping,
          malicious (nmap + hydra).
"""

import os, random, socket, subprocess, sys, time
from datetime import datetime, timezone

DOCKER_NET = "172.20.0."
MANAGER_IP = "192.168.30.3"
HOST_IP = "192.168.30.10"
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
FIRST_IP, LAST_IP = 2, 101

BENIGN_URLS = [
    "https://www.google.com", "https://github.com",
    "https://stackoverflow.com", "https://www.wikipedia.org",
    "https://www.debian.org", "https://www.ubuntu.com",
    "https://httpbin.org/ip", "https://httpbin.org/uuid",
    "https://www.archlinux.org", "https://www.docker.com",
]
NEW_URLS = [
    "https://httpbin.org/status/404", "https://httpbin.org/status/500",
    "https://httpbin.org/status/403", "https://httpbin.org/delay/1",
    "https://httpbin.org/redirect/3",
]
BENIGN_DOMAINS = [
    "google.com", "github.com", "gitlab.com", "debian.org",
    "ubuntu.com", "python.org", "docker.com", "cloudflare.com",
    "kernel.org", "stackoverflow.com", "reddit.com", "archlinux.org",
    "duckduckgo.com", "mozilla.org", "nmap.org",
]
BENIGN_URLS_ALL = BENIGN_URLS + NEW_URLS


def get_my_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("172.20.0.1", 1))
        ip = s.getsockname()[0]
    except:
        ip = "172.20.0.2"
    finally:
        s.close()
    return ip


def run(cmd: list, timeout: int = 10) -> bool:
    try:
        subprocess.run(cmd, timeout=timeout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False


def random_ip_in_docker() -> str:
    o = random.randint(FIRST_IP, LAST_IP)
    return f"{DOCKER_NET}{o}"


def random_ip_on_lan() -> str:
    o = random.randint(1, 20)
    return f"192.168.30.{o}"


# ─── Profils ────────────────────────────────────────────────────────

def benign_ssh():
    """SSH vers le Manager uniquement."""
    while True:
        user = random.choice(["vboxuser", "root", "admin"])
        run(["ssh", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
             f"{user}@{MANAGER_IP}", "exit"], timeout=8)
        time.sleep(random.uniform(15, 45))


def benign_dns():
    """Requetes DNS vers les resolveurs publics."""
    while True:
        domain = random.choice(BENIGN_DOMAINS)
        dns = random.choice(DNS_SERVERS)
        run(["dig", "+short", domain, f"@{dns}"], timeout=3)
        time.sleep(random.uniform(2, 8))


def benign_http():
    """Requetes HTTP(S) (certaines generent des erreurs)."""
    while True:
        url = random.choice(BENIGN_URLS_ALL)
        run(["curl", "-s", "-o", "/dev/null",
             "--connect-timeout", "5", "--max-time", "10", url], timeout=12)
        time.sleep(random.uniform(5, 20))


def benign_ping():
    """Echo ICMP vers differentes cibles."""
    while True:
        target = random.choice([
            random_ip_on_lan(),
            MANAGER_IP,
            random_ip_in_docker(),
        ])
        run(["ping", "-c", "1", "-W", "2", target], timeout=4)
        time.sleep(random.uniform(3, 10))


def benign_ftp():
    """Tentatives de connexion FTP (echouent, mais generent du trafic)."""
    while True:
        run(["curl", "-s", "-o", "/dev/null",
             "--connect-timeout", "3",
             f"ftp://{MANAGER_IP}/"], timeout=5)
        time.sleep(random.uniform(30, 90))


def benign_smb():
    """Tentative de connexion SMB (netbios)."""
    while True:
        run(["curl", "-s", "-o", "/dev/null",
             "--connect-timeout", "3",
             f"smb://{MANAGER_IP}/"], timeout=5)
        time.sleep(random.uniform(60, 120))


def malicious():
    """5 cycles : nmap + hydra sur toutes les cibles."""
    my_ip = get_my_ip()
    for cycle in range(8):
        # 1) Scan Docker subnet (all containers)
        run(["nmap", "-sS", "-T4", "-p", "22,80,443,3306,8080",
             "--max-rtt-timeout", "200ms", "--min-rate", "100",
             "172.20.0.0/24"], timeout=20)
        time.sleep(5)

        # 2) Scan LAN subnet
        run(["nmap", "-sS", "-T4", "-p", "22,80,443,1514,55000",
             "--max-rtt-timeout", "200ms", "--min-rate", "50",
             "192.168.30.0/24"], timeout=20)
        time.sleep(3)

        # 3) Version scan Manager
        run(["nmap", "-sV", "-T4", "-p", "22,80", MANAGER_IP], timeout=15)
        time.sleep(3)

        # 4) OS fingerprint
        run(["nmap", "-O", "--osscan-guess", MANAGER_IP], timeout=15)
        time.sleep(3)

        # 5) Hydra SSH brute sur Manager
        run(["hydra", "-l", "root", "-P", "/dev/null", "-t", "2",
             f"ssh://{MANAGER_IP}"], timeout=10)
        time.sleep(2)

        # 6) Hydra sur conteneur aléatoire
        victim = random_ip_in_docker()
        if victim != my_ip:
            run(["hydra", "-l", "root", "-p", "admin123", "-t", "1",
                 f"ssh://{victim}"], timeout=8)
            time.sleep(2)

        # Pause entre cycles
        delay = random.uniform(15, 45)
        time.sleep(delay)

    sys.exit(0)


# ─── Main ──────────────────────────────────────────────────────────

def main():
    profile = os.environ.get("PROFILE", "benign_ping").strip().lower()
    my_ip = get_my_ip()
    print(f"[profile] Starting: {profile} on {my_ip}", flush=True)

    PROFILES = {
        "benign_ssh": benign_ssh,
        "benign_dns": benign_dns,
        "benign_http": benign_http,
        "benign_ping": benign_ping,
        "malicious": malicious,
    }

    handler = PROFILES.get(profile)
    if handler is None:
        print(f"[ERROR] Unknown profile: {profile}")
        print(f"  Valid: {list(PROFILES.keys())}")
        sys.exit(1)

    try:
        handler()
    except KeyboardInterrupt:
        print("[profile] Interrupted", flush=True)


if __name__ == "__main__":
    main()
