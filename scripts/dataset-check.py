#!/usr/bin/env python3
"""dataset-check.py — Analyze dataset quality for ML readiness."""

import json, sys, os
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/alerts_20260713_193152.jsonl"
camp_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/CAMP_DOCKER_20260713_204420.csv"

print("==================================")
print(" DATASET QUALITY CHECK")
print("==================================")

# Load alerts
alerts = []
with open(path) as f:
    for line in f:
        line = line.strip()
        if line:
            try: alerts.append(json.loads(line))
            except: pass

print(f"\n📦 Total alerts:    {len(alerts)}")

# Rule distribution
rules = Counter()
for a in alerts:
    r = a.get("rule", {})
    rules[(r.get("id","?"), r.get("description","?")[:60])] += 1

print(f"\n📊 Top 10 rule distributions:")
for (rid, desc), count in rules.most_common(10):
    print(f"  {rid:>8} x{count:<6} {desc}")

# Timestamp range
timestamps = []
for a in alerts:
    try:
        from datetime import datetime
        ts = a.get("timestamp","").replace("Z","+00:00")
        timestamps.append(datetime.fromisoformat(ts))
    except: pass

if timestamps:
    span = max(timestamps) - min(timestamps)
    print(f"\n⏱️  Timespan:        {span}")
    print(f"   From: {min(timestamps)}")
    print(f"   To:   {max(timestamps)}")

# Agents distribution
agents = Counter()
for a in alerts:
    agents[a.get("agent",{}).get("name","?")] += 1
print(f"\n🖥️  Agents:          {len(agents)}")
for name, count in agents.most_common():
    print(f"  {name}: {count}")

# IP diversity
src_ips = set()
for a in alerts:
    ip = a.get("data",{}).get("srcip","")
    if ip: src_ips.add(ip)
print(f"\n🌐 Unique source IPs: {len(src_ips)}")

# --- Quality assessment ---
print(f"\n==================================")
print(" QUALITY ASSESSMENT")
print("==================================")

n_rules = len(rules)
n_tp_rules = sum(1 for (rid,_),_ in rules.most_common() if rid in ["1000001","1000002","1000003","1000004","1000005","1000006"])
span_hours = span.total_seconds()/3600 if timestamps else 0

print(f"\n  Rule diversity:    {n_rules} unique rules ({n_tp_rules} scan rules)")
print(f"  Timespan hours:   {span_hours:.1f}h")
print(f"  Unique agents:    {len(agents)}")

issues = []

if n_rules < 5:
    issues.append("❌ Trop peu de types d'alertes (diversite insuffisante)")
else:
    issues.append(f"✅ {n_rules} types d'alertes")

if span_hours < 1:
    issues.append(f"⚠️  Fenetre temporelle courte ({span_hours:.1f}h), les patterns temporels seront limites")
else:
    issues.append(f"✅ {span_hours:.1f}h de donnees")

if len(agents) < 2:
    issues.append("⚠️  Un seul agent Wazuh (les correlations inter-agents ne sont pas apprises)")
else:
    issues.append(f"✅ {len(agents)} agents")

# Unique days
days = set()
for t in timestamps:
    days.add(t.date())
issues.append(f"  {len(days)} jour(s) unique(s)")

# Recommendations
print(f"\n📋 Recommendations:")
print(f"  {'—'*40}")
for issue in issues:
    print(f"  {issue}")

print(f"\n🎯 VERDICT:")
if n_rules >= 5 and span_hours >= 1:
    print(f"  ✅ Dataset exploitable pour un premier modele")
    print(f"     Features disponibles: rule.id, level, srcip, timestamp, agent, groups")
    print(f"     Features derivees: frequence/heure/pattern temporel")
elif n_rules >= 5:
    print(f"  ⚠️  Dataset minimum viable mais court")
    print(f"     Une campagne de 1h ameliorerait la robustesse")
else:
    print(f"  ❌ Dataset insuffisant. Besoin de plus de diversite d'alertes")

print(f"\n💡 Pour ameliorer:")
print(f"  1. Lancer la campagne 1h au lieu de 10min")
print(f"  2. Ajouter + de profils benins (HTTP errors, FTP, SMB...)")
print(f"  3. Sequentiel: 20min benign only, 20min malicious, 20min benign only")
print(f"  = labelisation plus propre (TP/FP bien separes)")
