# Module de scan de ports.
#
# Lance nmap contre la cible avec differents types de scan pour generer
# une activite de reconnaissance detectable. Les trois variantes couvrent
# les regles de detection Wazuh les plus courantes (plage 531-540).
#
# Chaque variante s'execute une fois par appel : des scans repetes
# ressembleraient a une veritable attaque plutot qu'a du bruit.

import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


# Trois profils de scan que Wazuh detecte differemment.
SCAN_VARIANTS = [
    {"name": "syn_scan", "args": ["-sS", "-T4", "--max-rtt-timeout", "500ms"]},
    {"name": "full_scan", "args": ["-sT", "-T3"]},
    {"name": "aggressive", "args": ["-A", "-T4", "-p-", "--max-rtt-timeout", "500ms"]},
]


def run(target_ip, config, label_file="labels.csv"):
    """Execute une variante de scan nmap et enregistre le resultat.

    Choisit une variante aleatoire a chaque fois pour diversifier le dataset.
    La valeur d'intensite dans la config est ignoree pour le scan : un seul
    passage suffit a declencher Wazuh, des passages multiples ne feraient
    qu'ajouter du bruit redondant.

    Retourne True en cas de succes, False en cas d'echec.
    """
    import random
    variant = random.choice(SCAN_VARIANTS)
    name = variant["name"]
    extra_args = variant["args"]

    cmd = ["nmap"] + extra_args + [target_ip]

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("port_scan")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        with open(logfile, "a") as f:
            f.write(f"[{start_ts.isoformat()}] TIMEOUT: {' '.join(cmd)}\n")
        return False
    except Exception as e:
        with open(logfile, "a") as f:
            f.write(f"[{start_ts.isoformat()}] ERROR: {e}\n")
        return False

    end_ts = datetime.now(timezone.utc)

    # Enregistrer dans labels.csv
    extra = {"scan_variant": name, "nmap_args": " ".join(extra_args)}
    record_label(
        start_ts, end_ts, "port_scan", "port_scan", "nmap",
        target_ip, label_file, extra
    )

    with open(logfile, "a") as f:
        f.write(f"[{start_ts.isoformat()}] {' '.join(cmd)}\n")
        f.write(f"    -> {'OK' if success else 'FAIL'} (rc={result.returncode})\n")

    return success


if __name__ == "__main__":
    import json
    with open("config.yaml") as f:
        import yaml
        cfg = yaml.safe_load(f)
    run(cfg["target_ip"], cfg, label_file="/tmp/test_scan.csv")
    print("OK")
