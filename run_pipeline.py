#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrateur complet du pipeline ML
Execute 01..05 avec les données du traffic-generator.

Usage:
  python3 run_pipeline.py                # campagne récente (dernière heure)
  python3 run_pipeline.py --hours 24     # dernières 24h
  python3 run_pipeline.py --all          # tout l'historique
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw_alerts")
LABELED_DIR = os.path.join(PROJECT_DIR, "data", "labeled")
FEATURES_DIR = os.path.join(PROJECT_DIR, "features")
MODEL_DIR = os.path.join(PROJECT_DIR, "models")
REPORT_DIR = os.path.join(PROJECT_DIR, "reports")
TARGET_LABELS = "/home/vboxuser/wazuh-test/traffic-generator/labels.csv"
ALERTS_FILE = "/var/ossec/logs/alerts/alerts.json"


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def ok(msg):
    print(f"  ✅ {msg}")


def fail(msg):
    print(f"  ❌ {msg}")


def run_cmd(cmd, desc=""):
    """Execute une commande shell et retourne la sortie."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  stderr: {result.stderr[:500]}")
    print(result.stdout.strip()[-300:])
    return result


def fetch_labels_from_target():
    """Copie labels.csv depuis la cible via SSH."""
    step("ÉTAPE 0 : Récupération des labels depuis la Target")
    os.makedirs(LABELED_DIR, exist_ok=True)

    local_path = os.path.join(LABELED_DIR, "campaign_labels.csv")
    result = subprocess.run(
        ["ssh", "target", f"cat {TARGET_LABELS}"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        fail(f"Aucun fichier labels sur la Target : {TARGET_LABELS}")
        print("  ℹ️  Lance d'abord une campagne : ssh target 'cd ~/wazuh-test/traffic-generator && sudo python3 main.py --duration 120'")
        return None

    with open(local_path, "w") as f:
        f.write(result.stdout)

    lines = len(result.stdout.strip().split("\n")) - 1
    ok(f"{lines} campagnes récupérées → {local_path}")
    return local_path


def convert_labels_to_campaign_csv(labels_path):
    """Convertit labels.csv du generateur → format campagne Docker pour 02_label_dataset.py"""
    step("ÉTAPE 0b : Conversion labels → format campagne Docker")

    campaign_path = labels_path.replace("campaign_labels.csv", "campaign_docker_format.csv")

    malicious_types = {"bruteforce", "dos_flood", "exfiltration", "port_scan",
                       "nmap", "hydra", "slowloris", "syn_flood"}

    with open(labels_path) as f_in, open(campaign_path, "w", newline="") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.writer(f_out)
        writer.writerow(["attack_id", "start_utc", "end_utc", "attack_type", "container_count", "target_subnet"])

        count = 0
        for i, row in enumerate(reader):
            start = row.get("timestamp_start_iso", "")
            end = row.get("timestamp_end_iso", "")
            module = row.get("module_name", "").strip()
            target = row.get("target_ip", "192.168.30.10")

            # Déterminer le type d'attaque
            if module in malicious_types:
                attack_type = f"malicious_{module}"
            elif module.startswith("benign_"):
                attack_type = module
            else:
                attack_type = module

            aid = f"TG-{i+1:04d}"
            writer.writerow([aid, start, end, attack_type, 1, target])
            count += 1

    ok(f"{count} campagnes converties → {campaign_path}")
    return campaign_path


def step01(days):
    """Collecte les alertes depuis alerts.json"""
    step("ÉTAPE 1 : Collecte des alertes (01_collect_alerts.py)")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = os.path.join(RAW_DIR, f"alerts_{ts}.jsonl")

    cmd = [
        sys.executable, os.path.join(PROJECT_DIR, "pipeline", "01_collect_alerts.py"),
        "--input", ALERTS_FILE,
        "--output", output,
        "--days", str(days),
    ]
    run_cmd(cmd)

    if os.path.exists(output):
        ok(f"Alertes collectées : {output}")
        return output
    else:
        fail("Collecte échouée")
        return None


def step02(alerts_path, campaign_path):
    """Labellise le dataset"""
    step("ÉTAPE 2 : Labellisation du dataset (02_label_dataset.py)")
    output = alerts_path.replace(".jsonl", "_labeled.csv")

    cmd = [
        sys.executable, os.path.join(PROJECT_DIR, "pipeline", "02_label_dataset.py"),
        "--alerts", alerts_path,
        "--campaign", campaign_path,
        "--output", output,
    ]
    run_cmd(cmd)

    if os.path.exists(output):
        ok(f"Dataset labellisé : {output}")
        return output
    return None


def step03(labeled_path):
    """Ingenierie des features"""
    step("ÉTAPE 3 : Feature engineering (03_feature_engineering.py)")
    output = os.path.join(FEATURES_DIR, "feature_matrix.csv")
    os.makedirs(FEATURES_DIR, exist_ok=True)

    cmd = [
        sys.executable, os.path.join(PROJECT_DIR, "pipeline", "03_feature_engineering.py"),
        "--input", labeled_path,
        "--output", output,
    ]
    run_cmd(cmd)

    if os.path.exists(output):
        ok(f"Feature matrix : {output}")
        return output
    return None


def step04(features_path):
    """Entraine le modele"""
    step("ÉTAPE 4 : Entraînement XGBoost (04_train_model.py)")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "xgb_model.json")

    cmd = [
        sys.executable, os.path.join(PROJECT_DIR, "pipeline", "04_train_model.py"),
        "--input", features_path,
        "--output", model_path,
    ]
    run_cmd(cmd)

    if os.path.exists(model_path):
        ok(f"Modèle entraîné : {model_path}")
        return model_path
    return None


def step05(features_path, model_path):
    """Evalue le modele"""
    step("ÉTAPE 5 : Évaluation du modèle (05_evaluate_model.py)")
    os.makedirs(REPORT_DIR, exist_ok=True)

    cmd = [
        sys.executable, os.path.join(PROJECT_DIR, "pipeline", "05_evaluate_model.py"),
        "--input", features_path,
        "--model", model_path,
        "--output", REPORT_DIR,
    ]
    run_cmd(cmd)

    report = os.path.join(REPORT_DIR, "evaluation_report.json")
    if os.path.exists(report):
        ok(f"Rapport d'évaluation : {report}")
        return report
    return None


def install_deps():
    """Installe les paquets Python manquants."""
    step("[PRE] Vérification des dépendances")
    for pkg in ["xgboost", "scikit-learn", "shap", "matplotlib"]:
        r = subprocess.run(
            [sys.executable, "-c", f"import {pkg.replace('-', '_')}"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"  📦 Installation de {pkg}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", pkg,
                "--break-system-packages", "-q"
            ], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Pipeline ML Wazuh — execution complète")
    parser.add_argument("--hours", type=int, default=2, help="Heures à collecter (défaut: 2)")
    parser.add_argument("--all", action="store_true", help="Tout l'historique (ignore --hours)")
    args = parser.parse_args()

    days = 0 if args.all else max(1, args.hours // 24) if args.hours >= 24 else 1

    print("╔══════════════════════════════════════════════════════════╗")
    print("║    WA ZUH  AI  FILTER  —  PIPELINE  COMPLET              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Hours:  {args.hours}h{' (ALL HISTORY)' if args.all else ''}")
    print(f"  Mode:   {'Full history' if args.all else f'Last {args.hours}h'}")

    # Install deps if needed
    install_deps()

    # Étape 0 : Labels depuis la Target
    labels = fetch_labels_from_target()
    if not labels:
        sys.exit(1)

    campaign = convert_labels_to_campaign_csv(labels)

    # Étape 1 : Collecte
    alerts = step01(days)
    if not alerts:
        sys.exit(1)

    # Étape 2 : Labellisation
    labeled = step02(alerts, campaign)
    if not labeled:
        sys.exit(1)

    # Étape 3 : Feature engineering
    features = step03(labeled)
    if not features:
        sys.exit(1)

    # Étape 4 : Entraînement
    model = step04(features)
    if not model:
        sys.exit(1)

    # Étape 5 : Évaluation
    report = step05(features, model)
    if not report:
        sys.exit(1)

    # Résumé final
    step("✅ PIPELINE TERMINÉ AVEC SUCCÈS")
    print(f"  Alertes :      {alerts}")
    print(f"  Labels Target: {labels}")
    print(f"  Dataset:       {labeled}")
    print(f"  Features:      {features}")
    print(f"  Modèle:        {model}")
    print(f"  Rapport:       {report}")

    # Afficher les métriques
    with open(report) as f:
        metrics = json.load(f)
    print(f"\n{'─'*50}")
    print(f"  RÉSULTATS FINAUX")
    print(f"{'─'*50}")
    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            print(f"  {k:25s} : {v}")
    print(f"{'─'*50}")
    print(f"  Nouveau modèle prêt : {model}")
    print(f"  Copie vers /opt/wazuh-ml/ ? sudo cp {model} /opt/wazuh-ml/xgb_model.json")
    print(f"{'─'*50}")


if __name__ == "__main__":
    main()
