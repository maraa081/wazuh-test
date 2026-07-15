# Module de trafic web benign.

import subprocess
import sys
from datetime import datetime, timezone
import random
import time

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


DEFAULT_PATHS = [
    "/",
    "/index.html",
    "/robots.txt",
    "/favicon.ico",
    "/style.css",
    "/script.js",
    "/about",
    "/contact",
    "/login",
    "/images/logo.png",
    "/api/health",
    "/status",
]

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "curl/8.5.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
]


def run(target_ip, config, label_file="labels.csv"):
    """Effectue une petite serie de requetes HTTP vers la cible.

    Config keys used:
        - intensity.benign_web (int, requests per second)
    """
    rate = config.get("intensity", {}).get("benign_web", 2)
    paths = config.get("target_web_paths", DEFAULT_PATHS)
    ua_list = DEFAULT_USER_AGENTS

    num_requests = random.randint(3, 8)
    start_ts = datetime.now(timezone.utc)
    logfile = log_run("benign_web")

    try:
        for i in range(num_requests):
            path = random.choice(paths)
            url = f"http://{target_ip}{path}"
            ua = random.choice(ua_list)
            cmd = ["curl", "-s", "-o", "/dev/null", "-A", ua,
                   "--connect-timeout", "5", url]
            subprocess.run(cmd, stdout=logfile, stderr=logfile,
                           timeout=10, check=False)
            time.sleep(random.uniform(0.2, 1.5 / max(rate, 1)))
    except FileNotFoundError:
        print("  [WARN] curl not installed (unlikely)")
        return False
    except Exception as e:
        print(f"  [ERROR] benign_web: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="benign_web",
        module_name="benign_web",
        tool_used="curl",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"requests": num_requests},
    )

    print(f"  benign web ({num_requests} requests) -> {target_ip}  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
