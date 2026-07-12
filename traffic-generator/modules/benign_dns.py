# Benign DNS query module.
#
# Sends dig queries to either the target (if it runs a DNS server) or to
# public resolvers for a handful of popular domains. The domain list is
# curated to include a mix of CDN, tech, and local network entries to
# make the traffic look like real user activity.
#
# If the target is not a DNS server, the queries go to 1.1.1.1 or
# 8.8.8.8. In a fully isolated lab without internet, configure
# use_public_resolvers: false and the module does nothing.

import subprocess
import sys
from datetime import datetime, timezone
import random
import time

sys.path.insert(0, "..")

from utils.logger import record_label, log_run


COMMON_DOMAINS = [
    "google.com",
    "github.com",
    "debian.org",
    "ubuntu.com",
    "docker.com",
    "python.org",
    "duckduckgo.com",
    "wikipedia.org",
    "stackoverflow.com",
    "archlinux.org",
    "kernel.org",
    "gitlab.com",
    "reddit.com",
    "npmjs.com",
    "pypi.org",
]

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT"]


def run(target_ip, config, label_file="labels.csv"):
    """Query a handful of random domains with dig.

    Config keys used:
        - intensity.benign_dns (int, queries per second)
        - dns_resolver (str, default 127.0.0.1#53)
    """
    rate = config.get("intensity", {}).get("benign_dns", 1)
    resolver = config.get("dns_resolver", "127.0.0.1#53")
    use_public = config.get("use_public_resolvers", False)

    num_queries = random.randint(3, 7)
    start_ts = datetime.now(timezone.utc)
    logfile = log_run("benign_dns")

    try:
        for i in range(num_queries):
            domain = random.choice(COMMON_DOMAINS)
            rtype = random.choice(RECORD_TYPES)
            cmd = ["dig", f"@{resolver}", domain, rtype,
                   "+short", "+time=3", "+tries=1"]
            subprocess.run(cmd, stdout=logfile, stderr=logfile,
                           timeout=5, check=False)
            time.sleep(random.uniform(0.3, 2.0 / max(rate, 1)))
    except FileNotFoundError:
        print("  [WARN] dig not installed. Install with: sudo apt install dnsutils")
        return False
    except Exception as e:
        print(f"  [ERROR] benign_dns: {e}")
        return False
    finally:
        logfile.close()

    end_ts = datetime.now(timezone.utc)

    record_label(
        label_class="benign_dns",
        module_name="benign_dns",
        tool_used="dig",
        target_ip=target_ip,
        start_ts=start_ts,
        end_ts=end_ts,
        label_file=label_file,
        extra_params={"queries": num_queries, "resolver": resolver},
    )

    print(f"  benign dns ({num_queries} queries @ {resolver})  OK")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="127.0.0.1")
    parser.add_argument("--out", default="labels.csv")
    args = parser.parse_args()
    run(args.target, {}, label_file=args.out)
