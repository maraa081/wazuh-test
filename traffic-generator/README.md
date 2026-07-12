# Traffic Generator for Wazuh AI Filter Dataset

Generates a labeled multi-class traffic dataset for training a Wazuh alert
classifier. Runs from **Kali Linux** (or any Linux machine with the right
tools) and targets a single lab machine with a Wazuh agent. The output is a
CSV file with timestamp windows and class labels, designed to be fed into
the Wazuh AI Filter labeling pipeline.

**WARNING:** This tool is designed exclusively for isolated lab environments
(VirtualBox, VMware, air-gapped networks). Never run it against a machine you
do not own or on a production network.

## Dependencies

### System packages (install on Kali before first run)

```
sudo apt update
sudo apt install -y nmap hydra hping3 sshpass dnsutils curl openssh-client
```

### Python packages (minimal)

```
pip install -r requirements.txt
```

Only `pyyaml` is needed; everything else is a standard system tool.

## Setup

1. Copy the example config:

   ```bash
   cp config.yaml.example config.yaml
   ```

2. Edit `config.yaml` and set:

   - `target_ip` -- the IP of your lab target machine (single IP, never a range)
   - `target_ssh_user` / `target_ssh_pass` -- a dedicated test account on the target
   - `total_duration_seconds` -- how long each session runs (0 for no limit)
   - `benign_ratio` -- proportion of benign vs malicious traffic (default 0.7)

3. (Optional) Create a `testuser` account on the target machine:

   ```bash
   sudo useradd -m testuser
   sudo passwd testuser
   ```

4. Verify you can reach the target:

   ```bash
   ping -c 3 <target_ip>
   ```

## Usage

```bash
python main.py --config config.yaml --duration 3600 --output labels.csv
```

- `--duration` : total run time in seconds (default 3600 = 1 hour)
- `--output`  : path to the labels CSV that gets appended to

Stop early with Ctrl+C. The CSV file is not corrupted on interruption.

### Standalone module execution (debug)

Each module can run independently:

```bash
python modules/port_scan.py --target 192.168.1.100 --out test.csv
python modules/benign_ssh.py --target 192.168.1.100 --out test.csv
python modules/bruteforce.py --target 192.168.1.100 --out test.csv
```

## Output format: labels.csv

| Column              | Content                                          |
|---------------------|--------------------------------------------------|
| timestamp_start_iso | UTC start of the traffic burst (ISO 8601)         |
| timestamp_end_iso   | UTC end of the traffic burst (ISO 8601)           |
| label_class         | One of the 9 class labels (see below)             |
| module_name         | Python module that generated the entry            |
| tool_used           | System tool invoked (nmap, hydra, curl, etc.)     |
| target_ip           | Target IP (always the same for a given session)   |
| extra columns       | Variant-specific info (scan type, file size, etc.)|

### Class labels

| Label               | Category  | Description                          |
|---------------------|-----------|--------------------------------------|
| port_scan           | malicious | Nmap scan (SYN/full/aggressive)      |
| bruteforce          | malicious | SSH password guessing via hydra       |
| dos_flood           | malicious | Short burst DOS (SYN/ICMP/HTTP)       |
| exfiltration        | malicious | Large file SCP transfer               |
| benign_web          | benign    | HTTP requests to target web server    |
| benign_dns          | benign    | DNS queries to common domains         |
| benign_icmp         | benign    | Normal ping packets                   |
| benign_filetransfer | benign    | Small file SCP up and down            |
| benign_ssh          | benign    | Legit SSH login with commands         |

## Architecture

```
main.py (orchestrator)
  |
  |-- picks module (70% benign / 30% malicious)
  |-- randomises pause between 5-30s
  |-- runs module -> records in labels.csv + logs/
  |
  modules/
  |-- port_scan.py       (nmap -sS / -sT / -A)
  |-- bruteforce.py       (hydra)
  |-- dos_flood.py        (hping3 / curl)
  |-- exfiltration.py     (scp -- large file)
  |-- benign_web.py       (curl)
  |-- benign_dns.py       (dig)
  |-- benign_icmp.py      (ping)
  |-- benign_filetransfer.py (scp -- small file)
  |-- benign_ssh.py       (ssh + commands)
  |
  utils/
  |-- logger.py           (CSV writer + log file handler)
  |
  logs/
  |-- (per-module stdout/stderr dumps)
```

The orchestrator does not care what individual modules do. It only knows the
benign/malicious split and the pause ranges. Each module is self-contained and
can be run in isolation for debugging.

## How this feeds into the Wazuh AI Filter

1. Run the traffic generator on Kali (or whatever machine generates your attacks).
2. The generated traffic triggers Wazuh alerts on the target machine.
3. The Wazuh manager stores the alerts in `/var/ossec/logs/alerts/alerts.json`.
4. The Wazuh AI Filter pipeline reads that JSON file, cross-references alert
   timestamps with labels.csv, and labels each alert as TP or FP.
5. The model is trained on the resulting labeled dataset.

## Security notes

- The traffic generator never scans IP ranges, never uses --random-targets,
  and never sends traffic outside the configured target_ip.
- DOS bursts are capped at 20 seconds and limited to configurable low rates
  to avoid actually denying service to the target.
- All credentials are read from a local config file (gitignored). Use a
  throwaway test account on the target, never real credentials.
