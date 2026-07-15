# Service d'inference : boucle de polling qui score les nouvelles alertes.
#
# C'est le composant de production. Il s'execute comme un service autonome qui :
#
#   1. Interroge l'API Wazuh a intervalles reguliers pour les nouvelles alertes
#      (base sur le timestamp de la derniere alerte traitee, stocke en SQLite).
#   2. Extrait les memes features que celles utilisees pendant l'entrainement,
#      via le pipeline de features sauvegarde.
#   3. Execute le modele XGBoost entraine pour obtenir une probabilite TP
#      pour chaque alerte.
#   4. Stocke la prediction (ID alerte, timestamp, probabilite TP,
#      classification binaire, valeurs des features) dans une base SQLite locale.
#
# Le service ne modifie aucun fichier Wazuh. C'est un consommateur read-only
# de l'API Wazuh et un producteur write-only pour sa propre base de donnees.
#
# A separate FastAPI server (api.py) provides read access to the stored
# predictions for dashboards and manual queries.
#
# Usage:
#   python service/inference_service.py
#
# The service runs until interrupted with Ctrl+C. Intended to be run under
# systemd or supervisord for long-term operation.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("inference_service.py - not yet implemented")
    print("This service will:")
    print("  1. Load config, model, and feature pipeline at startup")
    print("  2. Initialize the SQLite database (create tables if needed)")
    print("  3. Enter a polling loop:")
    print("     a. Fetch new alerts from Wazuh API (since last_processed)")
    print("     b. Extract features for each new alert")
    print("     c. Score each alert with the model")
    print("     d. Store the prediction in SQLite")
    print("     e. Sleep for poll_interval_seconds")
    print("  4. Gracefully shut down on SIGTERM/SIGINT")


if __name__ == "__main__":
    main()
