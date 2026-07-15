# Orchestrateur du generateur de trafic.
#
# Lit un fichier de config, puis execute un entrelacement aleatoire de modules
# benins et malveillants contre une seule IP cible dans votre labo isole.
# Chaque execution de module est enregistree dans labels.csv et la sortie brute
# des outils sous-jacents est sauvegardee dans le dossier logs/ pour debogage.
#
# Usage :
#   cp config.yaml.example config.yaml
#   # editer config.yaml pour definir votre IP cible et compte de test
#   python main.py --config config.yaml --duration 3600 --output labels.csv
#
# Pour arreter tot : Ctrl+C. Le script se termine proprement sans corrompre
# le fichier CSV.
#

import argparse
import random
import sys
import time
from datetime import datetime, timezone

# -------------------------------------------------------------------
# Registre des modules
# -------------------------------------------------------------------
# Chaque module expose une fonction run(target_ip, config, label_file) qui
# retourne True en cas de succes, False en cas d'echec. Le reste de
# l'orchestrateur ne se soucie pas de ce que fait le module en interne.

MALICIOUS_MODULES = [
    ("port_scan", "modules.port_scan"),
    ("bruteforce", "modules.bruteforce"),
    ("dos_flood", "modules.dos_flood"),
    ("exfiltration", "modules.exfiltration"),
]

BENIGN_MODULES = [
    ("benign_web", "modules.benign_web"),
    ("benign_dns", "modules.benign_dns"),
    ("benign_icmp", "modules.benign_icmp"),
    ("benign_filetransfer", "modules.benign_filetransfer"),
    ("benign_ssh", "modules.benign_ssh"),
]


def import_module(module_path, module_name):
    """Dynamically import a module by its dotted path.

    This keeps the overhead low: modules are imported only when they are
    about to run, so a missing tool only causes a warning at runtime.
    """
    import importlib
    try:
        mod = importlib.import_module(module_path)
        return mod
    except ModuleNotFoundError as e:
        print(f"  [WARN] could not load {module_name}: {e}")
        return None


def pick_module(benign_ratio, rng):
    """Pick a module category and a specific module from it.

    Returns (name, module_path) or (name, None) if the category is empty.
    """
    if rng.random() < benign_ratio:
        return rng.choice(BENIGN_MODULES)
    else:
        return rng.choice(MALICIOUS_MODULES)


def load_config(config_path):
    """Parse the YAML config file and return a dict."""
    import yaml
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[FATAL] config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"[FATAL] config parse error: {e}")
        sys.exit(1)

    required = ["target_ip"]
    for key in required:
        if key not in cfg:
            print(f"[FATAL] missing required config key: {key}")
            sys.exit(1)
    return cfg


def main():
    parser = argparse.ArgumentParser(
        description="Generate lab traffic for Wazuh AI Filter dataset."
    )
    parser.add_argument("--config", default="config.yaml",
                        help="Path to config.yaml (default: config.yaml)")
    parser.add_argument("--duration", type=int, default=3600,
                        help="Total run duration in seconds (default: 3600)")
    parser.add_argument("--output", default="labels.csv",
                        help="Output labels CSV path (default: labels.csv)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    target = cfg["target_ip"]
    benign_ratio = cfg.get("benign_ratio", 0.7)
    pause_min = cfg.get("pause_min", 5)
    pause_max = cfg.get("pause_max", 30)
    real_timing = cfg.get("real_timing", False)
    duration = args.duration

    print(f"[+] Target: {target}")
    print(f"[+] Duration: {duration}s")
    print(f"[+] Benign ratio: {benign_ratio}")
    print(f"[+] Output: {args.output}")
    print()

    # Seeded RNG for reproducibility during debug sessions.
    rng = random.Random()

    start_time = time.time()
    module_count = 0
    success_count = 0

    # Main loop.
    while True:
        # Check duration.
        elapsed = time.time() - start_time
        if duration > 0 and elapsed >= duration:
            break

        # Adjust pauses for real_timing mode.
        current_pause_min = pause_min
        current_pause_max = pause_max
        if real_timing:
            now = datetime.now(timezone.utc)
            hour = now.hour
            weekday = now.weekday()
            is_office_hours = (weekday < 5 and 8 <= hour < 18)
            if not is_office_hours:
                # Longer pauses at night and on weekends: sparser traffic.
                current_pause_min = pause_min * 3
                current_pause_max = pause_max * 5

        # Pick and run a module.
        name, module_path = pick_module(benign_ratio, rng)
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
              f"running {name} ...")

        mod = import_module(module_path, name)
        if mod is None:
            print(f"  [SKIP] {name} could not be loaded")
        else:
            module_count += 1
            try:
                ok = mod.run(target, cfg, label_file=args.output)
                if ok:
                    success_count += 1
            except Exception as e:
                print(f"  [ERROR] {name} raised an exception: {e}")

        # Pause before the next execution.
        pause = rng.uniform(current_pause_min, current_pause_max)
        print(f"  (pause {pause:.0f}s)")
        time.sleep(pause)

    print()
    print(f"[+] Done. {module_count} modules executed ({success_count} OK)")
    print(f"[+] Labels written to: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted. Labels up to last completed execution are saved.")
        sys.exit(0)
