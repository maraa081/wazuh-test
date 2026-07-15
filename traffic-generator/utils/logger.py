# Journalisation standardisee pour le generateur de trafic.
#
# Chaque module appelle ceci pour enregistrer ce qu'il a fait et ecrire les logs
# d'execution dans un fichier pour debogage ulterieur.
#
# Le fichier labels.csv est la sortie cle : il associe chaque burst de trafic a une
# fenetre temporelle et un label de classe. Vous importez ce CSV dans le pipeline
# de labellisation Wazuh AI Filter pour le croiser avec les timestamps d'alertes Wazuh.

import csv
import os
import sys
from datetime import datetime, timezone


def record_label(label_class, module_name, tool_used, target_ip,
                 start_ts, end_ts, label_file="labels.csv",
                 extra_params=None):
    """Ajoute une ligne au fichier CSV de labels.

    Parameters
    ----------
    label_class : str
        One of the predefined traffic classes: port_scan, bruteforce,
        dos_flood, exfiltration, benign_web, benign_dns, benign_icmp,
        benign_filetransfer, benign_ssh.
    module_name : str
        Python module name that generated this entry (e.g. port_scan).
    tool_used : str
        The system tool that was invoked (nmap, hydra, curl, etc.).
    target_ip : str
        IP address of the target machine.
    start_ts : datetime
        UTC timestamp when the traffic started.
    end_ts : datetime
        UTC timestamp when the traffic ended.
    label_file : str
        Path to the labels CSV (default labels.csv in cwd).
    extra_params : dict or None
        Optional extra key-value pairs to append as columns.
    """
    file_exists = os.path.isfile(label_file)

    row = {
        "timestamp_start_iso": start_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp_end_iso": end_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label_class": label_class,
        "module_name": module_name,
        "tool_used": tool_used,
        "target_ip": target_ip,
    }

    if extra_params:
        for k, v in extra_params.items():
            row[k] = v

    with open(label_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def log_run(module_name, log_dir="logs"):
    """Retourne un gestionnaire de contexte qui capture stdout/stderr d'un sous-processus
    into a timestamped log file.

    Usage inside each module::

        with log_run("port_scan") as logfile:
            subprocess.run(["nmap", ...], stdout=logfile, stderr=logfile)
    """
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.now(timezone.utc)
    safe_ts = now.strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{module_name}_{safe_ts}.log")
    logfile = open(log_path, "w")
    return logfile
