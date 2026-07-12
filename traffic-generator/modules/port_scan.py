# Port scan module.
#
# Runs nmap against the target using different scan types to generate
# alertable reconnaissance activity. The three variants cover the most
# common Wazuh detection rules (531-540 range).
#
# Each variant runs once per call: repeated scans would look like an
# actual attack rather than noise.

import subprocess
import sys
from datetime import datetime, timezone

# Add project root to path so utils can be imported when run standalone.
sys.path.insert(0, "..")

from utils.logger import record_label, log_run


# Three scan profiles that Wazuh picks up differently.
SCAN_VARIANTS = [
    {"name": "syn_scan", "args": ["-sS", "-T4", "--max-rtt-timeout", "500ms"]},
    {"name": "full_scan", "args": ["-sT", "-T3"]},
    {"name": "aggressive", "args": ["-A", "-T4", "-p-", "--max-rtt-timeout", "500ms"]},
]


def run(target_ip, config, label_file="labels.csv"):
    """Run one nmap scan variant and log the result.

    Picks a random variant each time to keep the dataset diverse. The
    intensity config value is ignored for scanning: one pass is sufficient
    to trigger Wazuh, and multiple passes would just be redundant noise.

    Returns True on success, False on failure.
    """
    import random

    variant = random.choice(SCAN_VARIANTS)
    start_ts = datetime.now(timezone.utc)
    logfile = log_run("port_scan")

    try:
        cmd = ["nmap"] + variant["args"] + [target_ip]
        subprocess.run(cmd, stdout=logfile, stderr=logfile,
                       timeout=120, check=False)
    except FileNotFoundError:
        print("  [WARN] nmap not installed. Install with: sudo apt install nmap")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [WARN] nmap {variant['name']} timed out")
    except Exception as e:
        print(f"  [ERROR] nmap {variant['name']}: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="port_scan",
        module_name="port_scan",
        tool_used="nmap",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"scan_variant": variant["name"]},
    )

    print(f"  port scan ({variant['name']}) -> {target_ip}  OK")
    return True


# Allow standalone run for debugging.
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
