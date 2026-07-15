# Module de transfert de fichier benign.

import subprocess
import os
import sys
from datetime import datetime, timezone
import random

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


def run(target_ip, config, label_file="labels.csv"):
    """Copie un petit fichier vers et depuis la cible via SCP.

    Only runs if sshpass is installed, since we need non-interactive auth
    for the test account.

    Config keys used:
        - target_ssh_user (str)
        - target_ssh_pass (str)
        - intensity.benign_filetransfer (int, MB/s)
    """
    ssh_user = config.get("target_ssh_user", "root")
    ssh_pass = config.get("target_ssh_pass", "toor")
    rate = config.get("intensity", {}).get("benign_filetransfer", 5)

    # Small file, 1-5 MB, realistic for a config backup or log pull.
    file_size_mb = random.randint(1, 5)
    file_size = file_size_mb * 1024 * 1024
    local_src = f"/tmp/tg_benign_transfer_src_{random.randint(0,99999)}.bin"
    local_dst = f"/tmp/tg_benign_transfer_dst_{random.randint(0,99999)}.bin"
    remote_path = f"/tmp/tg_benign_remote_{random.randint(0,99999)}.bin"

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("benign_filetransfer")

    ssh_opts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

    try:
        # 1. Write a small file with random content.
        subprocess.run(
            ["dd", f"if=/dev/urandom", f"of={local_src}",
             f"bs={file_size}", "count=1", "status=none"],
            check=True, timeout=10)

        # 2. Upload to target.
        upload_cmd = (
            f"sshpass -p {ssh_pass} scp {ssh_opts} "
            f"-l {rate * 1024} "
            f"{local_src} {ssh_user}@{target_ip}:{remote_path}"
        )
        subprocess.run(upload_cmd, shell=True, stdout=logfile, stderr=logfile,
                       timeout=30, check=False)

        # 3. Download it back.
        download_cmd = (
            f"sshpass -p {ssh_pass} scp {ssh_opts} "
            f"-l {rate * 1024} "
            f"{ssh_user}@{target_ip}:{remote_path} {local_dst}"
        )
        subprocess.run(download_cmd, shell=True, stdout=logfile, stderr=logfile,
                       timeout=30, check=False)

    except FileNotFoundError as e:
        if "sshpass" in str(e):
            print("  [WARN] sshpass not installed. Install with: sudo apt install sshpass")
        else:
            print(f"  [WARN] missing tool: {e}")
        return False
    except subprocess.TimeoutExpired:
        print("  [WARN] benign file transfer timed out")
    except Exception as e:
        print(f"  [ERROR] benign_filetransfer: {e}")
        return False
    finally:
        logfile.close()
        # Cleanup local and remote temp files.
        for f in [local_src, local_dst]:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            subprocess.run(
                ["sshpass", "-p", ssh_pass, "ssh", ssh_opts.split(),
                 f"{ssh_user}@{target_ip}", f"rm -f {remote_path}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            pass

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="benign_filetransfer",
        module_name="benign_filetransfer",
        tool_used="scp",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"file_size_mb": file_size_mb, "bidirectional": True},
    )

    print(f"  benign file transfer ({file_size_mb}MB, up+down) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
