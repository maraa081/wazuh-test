#!/bin/bash
# Suricata Diagnostic Collector — run on target, paste output
# Usage: sudo bash suricata-diag.sh

set -euo pipefail

OUTFILE=/tmp/suricata-diag-$(date +%H%M%S).txt

exec > >(tee "$OUTFILE") 2>&1

echo "============================================"
echo " Suricata Diagnostic — $(date)"
echo " Host: $(hostname) — OS: $(lsb_release -ds 2>/dev/null || cat /etc/os-release 2>/dev/null | head -1)"
echo "============================================"
echo ""

# --- VERSION ---
echo "=== Suricata version ==="
suricata --build-info 2>&1 | head -3 || suricata --version 2>&1 || suricata -V 2>&1 || echo "version check failed"

# --- SERVICE STATUS ---
echo ""
echo "=== Service status ==="
systemctl status suricata --no-pager 2>&1 | head -10

# --- JOURNAL RECENT ---
echo ""
echo "=== Journal errors (last 30 lines) ==="
journalctl -u suricata --since "10 min ago" --no-pager 2>&1 | tail -30

# --- INTERFACES ---
echo ""
echo "=== Network interfaces ==="
ip -br addr
echo ""
ip route 2>/dev/null || route -n

# --- CONFIG AF-PACKET ---
echo ""
echo "=== Config: af-packet interface ==="
sudo grep -B2 -A20 "^af-packet:" /etc/suricata/suricata.yaml | head -30

# --- CONFIG HOME_NET ---
echo ""
echo "=== Config: HOME_NET ==="
grep "^    HOME_NET\|^#    HOME_NET" /etc/suricata/suricata.yaml

# --- CONFIG EXTERNAL_NET ---
echo ""
echo "=== Config: EXTERNAL_NET ==="
grep "^    EXTERNAL_NET\|^#    EXTERNAL_NET" /etc/suricata/suricata.yaml

# --- CONFIG EVE-LOG TYPES ---
echo ""
echo "=== Config: eve-log types ==="
sudo sed -n '/types:/,/^  [a-z].*:/p' /etc/suricata/suricata.yaml | head -20

# --- RULES LOADED ---
echo ""
echo "=== Rules loaded ==="
grep "rules successfully loaded" /var/log/suricata/suricata.log 2>/dev/null | tail -3 || echo "not found in log"
echo "Total rule file size:"
sudo wc -l /var/lib/suricata/rules/suricata.rules 2>/dev/null || echo "no default rule file"

# --- PORTSCAN CONFIG ---
echo ""
echo "=== Config: portscan module ==="
grep -A8 "^portscan:" /etc/suricata/suricata.yaml

# --- EVE.JSON TYPES ---
echo ""
echo "=== Eve.json event types (sample 500) ==="
python3 -c "
import json
with open('/var/log/suricata/eve.json') as f:
    types = {}
    for i, line in enumerate(f):
        if i > 2000: break
        try:
            d = json.loads(line.strip())
            et = d.get('event_type','?')
            types[et] = types.get(et, 0) + 1
        except: pass
    print('Counts:', types)
    total = sum(types.values())
    print(f'Total lines sampled: {total}')
"

# --- EVE.JSON ALERTS SEARCH ---
echo ""
echo "=== Recent lines with 'alert' string ==="
sudo grep -c "alert" /var/log/suricata/eve.json || echo "0 matches"
sudo grep "signature\|event_type.*alert" /var/log/suricata/eve.json 2>/dev/null | tail -5 || echo "no alert lines found"

# --- SURICATA STATS ---
echo ""
echo "=== Capture stats ==="
sudo grep "kernel_packets\|decoder.tcp\|decoder.udp\|decoder.ipv4\|capture.kernel" /var/log/suricata/stats.log 2>/dev/null | tail -5 || echo "no stats.log"

# --- TCPDUMP CHECK ---
echo ""
echo "=== Quick tcpdump test (interface with traffic) ==="
timeout 3 tcpdump -i enp0s8 -c 3 -n 2>&1 | tail -5 || echo "tcpdump not available or no traffic"

echo ""
echo "============================================"
echo " DIAGNOSTIC COLLECTED — file: $OUTFILE"
echo " Paste this output back in chat."
echo "============================================"
