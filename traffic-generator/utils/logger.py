# Standardised logging for the traffic generator.
#
# Every module calls this to record what it did and to write execution logs
# to a file so you can debug later.
#
# The labels.csv file is the key output: it pairs each traffic burst with a
# timestamp window and a class label. You import this CSV into the Wazuh AI
# Filter labeling pipeline to cross-reference with Wazuh alert timestamps.

import csv
import os
import sys
from datetime import datetime, timezone


def record_label(label_class, module_name, tool_used, target_ip,
                 start_ts, end_ts, label_file="labels.csv",
                 extra_params=None):
    """Append one row to the labels CSV file.

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
    """Return a context manager that captures stdout/stderr of a subprocess
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
