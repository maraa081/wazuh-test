# Module de connexion SSH benine.

import subprocess
import sys
from datetime import datetime, timezone
import random

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


COMMANDS = [
    "whoami",
    "hostname",
    "uptime",
    "date",
    "ls /tmp",
    "cat /etc/hostname",
    "uname -r",
    "df -h /",
    "free -h",
    "ps aux --sort=-%mem | head -5",
    "last -5",
    "cat /etc/os-release",
    "dmesg | tail -3",
    "journalctl --no-pager -n 3",
    "ip addr show | grep inet",
    "ss -tln | head -10",
    "id",
    "pwd",
    "ls -la ~",
    "echo 'connection test'",
]


def run(target_ip, config, label_file="labels.csv"):
    """SSH vers la cible et execute quelques commandes.

    Config keys used:
        - target_ssh_port (int, default 22)
        - target_ssh_user (str)
        - target_ssh_pass (str)
    """
    ssh_port = config.get("target_ssh_port", 22)
    ssh_user = config.get("target_ssh_user", "root")
    ssh_pass = config.get("target_ssh_pass", "toor")

    num_cmds = random.randint(2, 5)
    selected_commands = random.sample(COMMANDS, num_cmds)
    cmd_script = "; ".join(selected_commands)

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("benign_ssh")

    try:
        ssh_cmd = [
            "sshpass", "-p", ssh_pass,
            "ssh",
            "-p", str(ssh_port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=5",
            "-o", "BatchMode=no",
            f"{ssh_user}@{target_ip}",
            cmd_script,
        ]
        subprocess.run(ssh_cmd, stdout=logfile, stderr=logfile,
                       timeout=20, check=False)
    except FileNotFoundError as e:
        if "sshpass" in str(e):
            print("  [WARN] sshpass not installed. Install with: sudo apt install sshpass")
        else:
            print(f"  [WARN] missing tool: {e}")
        return False
    except subprocess.TimeoutExpired:
        print("  [WARN] benign SSH timed out")
    except Exception as e:
        print(f"  [ERROR] benign_ssh: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="benign_ssh",
        module_name="benign_ssh",
        tool_used="ssh",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"commands": len(selected_commands)},
    )

    print(f"  benign ssh ({len(selected_commands)} commands) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
