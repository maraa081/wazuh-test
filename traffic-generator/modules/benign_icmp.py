# Module de ping ICMP benign.

import subprocess
import sys
from datetime import datetime, timezone
import random
import time

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


def run(target_ip, config, label_file="labels.csv"):
    """Ping la cible quelques fois.

    Config keys used:
        - intensity.benign_icmp (int, packets per second)
    """
    rate = config.get("intensity", {}).get("benign_icmp", 2)
    count = random.randint(3, 10)

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("benign_icmp")

    try:
        cmd = ["ping", "-c", str(count),
               "-i", str(max(0.5, 1.0 / max(rate, 1))),
               "-W", "3", target_ip]
        subprocess.run(cmd, stdout=logfile, stderr=logfile,
                       timeout=30, check=False)
    except FileNotFoundError:
        print("  [WARN] ping not installed (unlikely)")
        return False
    except Exception as e:
        print(f"  [ERROR] benign_icmp: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="benign_icmp",
        module_name="benign_icmp",
        tool_used="ping",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"pings": count},
    )

    print(f"  benign icmp ({count} pings) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
