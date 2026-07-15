# Module de simulation d'exfiltration.
#
# Genere un gros fichier factice en local et le transfere vers la cible via
# SCP a un debit configurable. L'objectif est de produire un motif de trafic
# qui ressemble a une tentative d'exfiltration de donnees : transfert sortant
# volumineux, inhabituel pour un comportement utilisateur normal.
#
# Le fichier factice est cree dans /tmp et supprime apres le transfert pour
# ne pas remplir le disque de Kali.

import subprocess
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


def run(target_ip, config, label_file="labels.csv"):
    """Copie un gros fichier factice sur la cible via SCP.

    Cles de configuration utilisees :
        - target_ssh_user (str)
        - target_ssh_pass (str)
        - intensity.exfiltration (int, MB/s)
    """
    ssh_user = config.get("target_ssh_user", "root")
    ssh_pass = config.get("target_ssh_pass", "toor")
    rate = config.get("intensity", {}).get("exfiltration", 10)

    # File size: 50 MB minimum to look exfil-like. If rate is high,
    # bump it up so the transfer takes at least 5 seconds.
    file_size_mb = max(50, rate * 5)
    local_file = "/tmp/tg_exfil_data.bin"
    remote_path = f"/tmp/tg_exfil_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.bin"

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("exfiltration")

    try:
        # 1. Generate the dummy file with dd (fast, no RAM waste).
        dd_cmd = ["dd", "if=/dev/urandom", f"of={local_file}",
                  f"bs=1M", f"count={file_size_mb}", "status=none"]
        subprocess.run(dd_cmd, check=True, timeout=60)

        # 2. SCP it to the target using sshpass to avoid interactive prompt.
        scp_cmd = [
            "sshpass", "-p", ssh_pass,
            "scp", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-l", str(rate * 1024),  # bandwidth limit in kbit/s
            local_file,
            f"{ssh_user}@{target_ip}:{remote_path}",
        ]
        subprocess.run(scp_cmd, stdout=logfile, stderr=logfile,
                       timeout=file_size_mb * 2, check=False)

    except FileNotFoundError as e:
        if "sshpass" in str(e):
            print("  [WARN] sshpass not installed. Install with: sudo apt install sshpass")
        else:
            print(f"  [WARN] missing tool: {e}")
        return False
    except subprocess.TimeoutExpired:
        print("  [WARN] exfiltration SCP timed out")
    except Exception as e:
        print(f"  [ERROR] exfiltration: {e}")
        return False
    finally:
        logfile.close()
        try:
            os.remove(local_file)
        except OSError:
            pass
        # Cleanup the remote file via SSH if SCP succeeded.
        try:
            subprocess.run(
                ["sshpass", "-p", ssh_pass, "ssh",
                 "-o", "StrictHostKeyChecking=no",
                 f"{ssh_user}@{target_ip}",
                 f"rm -f {remote_path}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            pass

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="exfiltration",
        module_name="exfiltration",
        tool_used="scp",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"file_size_mb": file_size_mb},
    )

    print(f"  exfiltration ({file_size_mb}MB) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
