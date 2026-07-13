#!/usr/bin/env python3
"""
Traffic generator profile for Docker dataset containers.

Reads PROFILE env var and generates network traffic accordingly.
Each container runs in an isolated loop on Docker bridge network 172.20.0.0/16.

Profiles:
  benign_ssh    — SSH connections to Wazuh Manager + other containers
  benign_dns    — varied DNS queries to public resolvers
  benign_http   — HTTP(S) requests to varied targets
  benign_ping   — ICMP echo to random IPs
  malicious     — nmap scans + hydra bruteforce (1 container only)
"""

import os
import random
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone

# ─── Network topology ──────────────────────────────────────────────
DOCKER_NET = "172.20.0."
MANAGER_IP = "192.168.30.3"
HOST_IP = "192.168.30.10"
PARROT_IP = "192.168.30.9"
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

# Container count (sets max IP in Docker range)
CONTAINER_COUNT = 100
FIRST_IP = 2
LAST_IP = FIRST_IP + CONTAINER_COUNT - 1  # 2..101

BENIGN_URLS = [
    "https://www.google.com",
    "https://github.com",
    "https://stackoverflow.com",
    "https://www.wikipedia.org",
    "https://www.debian.org",
    "https://www.ubuntu.com",
    "https://httpbin.org/ip",
    "https://httpbin.org/uuid",
]

BENIGN_DOMAINS = [
    "google.com", "github.com", "gitlab.com",
    "debian.org", "ubuntu.com", "python.org",
    "docker.com", "cloudflare.com", "archlinux.org",
    "kernel.org", "stackoverflow.com", "reddit.com",
]


def get_my_ip() -> str:
    """Return this container's IP address in the 172.20.0.0/16 network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("172.20.0.1", 1))  # gateway
        ip = s.getsockname()[0]
    except Exception:
        ip = "172.20.0.2"
    finally:
        s.close()
    return ip


def run(cmd: list, timeout: int = 10) -> bool:
    """Run a command with timeout, return True on success."""
    try:
        subprocess.run(cmd, timeout=timeout,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def random_ip_in_docker() -> str:
    """Return a random IP within the container range."""
    o = random.randint(FIRST_IP, LAST_IP)
    return f"{DOCKER_NET}{o}"


def random_ip_on_lan() -> str:
    """Return a random IP in the lab LAN."""
    o = random.randint(1, 20)
    return f"192.168.30.{o}"


# ─── Profiles ──────────────────────────────────────────────────────

def benign_ssh():
    """Legitimate SSH connections to Wazuh Manager only."""
    while True:
        user = random.choice(["vboxuser", "root", "admin"])
        run(["ssh", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5",
             "-o", "BatchMode=yes",
             f"{user}@{MANAGER_IP}", "exit"],
            timeout=8)
        delay = random.uniform(15, 45)
        time.sleep(delay)


def benign_dns():
    """DNS lookups to public resolvers."""
    while True:
        domain = random.choice(BENIGN_DOMAINS)
        dns = random.choice(DNS_SERVERS)
        run(["dig", "+short", domain, f"@{dns}"], timeout=3)
        delay = random.uniform(2, 8)
        time.sleep(delay)


def benign_http():
    """HTTP(S) requests to varied destinations."""
    while True:
        url = random.choice(BENIGN_URLS)
        run(["curl", "-s", "-o", "/dev/null",
             "--connect-timeout", "5",
             "--max-time", "10",
             url], timeout=12)
        delay = random.uniform(5, 20)
        time.sleep(delay)


def benign_ping():
    """ICMP echo to LAN IPs with normal payload."""
    while True:
        target = random_ip_on_lan()
        run(["ping", "-c", "2", "-W", "2", target], timeout=5)
        # Sometimes ping another container
        if random.random() < 0.3:
            other = random_ip_in_docker()
            run(["ping", "-c", "1", "-W", "1", other], timeout=3)
        delay = random.uniform(3, 10)
        time.sleep(delay)


def malicious():
    """
    Simulates an attacker: nmap scans + hydra bruteforce.
    Targets: Manager IP, other containers, LAN IPs.
    Runs 3-5 cycles then exits.
    """
    my_ip = get_my_ip()
    for cycle in range(5):
        ts = datetime.now(timezone.utc).isoformat()
        # 1) Nmap SYN scan — all containers + Manager
        target_subnet = random.choice([
            "172.20.0.0/24",
            "192.168.30.0/24",
        ])
        run(["nmap", "-sS", "-T4", "-p", "22,80,443,3306",
             "--max-rtt-timeout", "300ms",
             "--min-rate", "50",
             target_subnet], timeout=30)

        # 2) Nmap version scan — Manager
        run(["nmap", "-sV", "-T4", "-p", "22,80",
             MANAGER_IP], timeout=20)

        # 3) Nmap OS fingerprint — random target
        os_target = random.choice([MANAGER_IP, HOST_IP])
        run(["nmap", "-O", "--osscan-guess", os_target], timeout=20)

        # 4) Hydra bruteforce — Manager SSH
        run(["hydra", "-l", "root", "-p", "wrongpass",
             "-t", "2", "-w", "3",
             f"ssh://{MANAGER_IP}"], timeout=15)

        # 5) Try bruteforce on a random container
        victim = random_ip_in_docker()
        if victim != my_ip:
            run(["hydra", "-l", "root", "-p", "admin123",
                 "-t", "1", "-w", "2",
                 f"ssh://{victim}"], timeout=10)

        # Sleep between cycles
        delay = random.uniform(10, 30)
        time.sleep(delay)

    # Exit after 5 cycles (~10 min total)
    sys.exit(0)


# ─── Main dispatcher ───────────────────────────────────────────────

def main():
    profile = os.environ.get("PROFILE", "benign_ping").strip().lower()
    print(f"[profile] Starting: {profile} on {get_my_ip()}", flush=True)

    PROFILES = {
        "benign_ssh": benign_ssh,
        "benign_dns": benign_dns,
        "benign_http": benign_http,
        "benign_ping": benign_ping,
        "malicious": malicious,
    }

    handler = PROFILES.get(profile)
    if handler is None:
        print(f"[ERROR] Unknown profile: {profile}", flush=True)
        print(f"  Valid: {list(PROFILES.keys())}", flush=True)
        sys.exit(1)

    try:
        handler()
    except KeyboardInterrupt:
        print("[profile] Interrupted, exiting", flush=True)


if __name__ == "__main__":
    main()
