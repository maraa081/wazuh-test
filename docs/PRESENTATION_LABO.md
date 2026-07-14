# Détection d'intrusion avec Machine Learning

### Le problème de base

Quand tu mets en place un Wazuh, tu te retrouves avec des milliers d'alertes
par jour. Le souci : la plupart sont des faux positifs. Un admin passe son
temps à trier au lieu d'agir sur les vraies attaques.

### Ce que j'ai fait

J'ai monté un labo avec 3 machines virtuelles :

- **Cible** (Ubuntu) — serveur "normal" avec Suricata qui surveille le réseau
- **Manager** (Ubuntu) — Wazuh + un modèle ML entraîné sur mesure
- **Attaquant** (ParrotOS) — machine qui envoie du trafic (attaques et traffic normal)

Le principe : Suricata capte tout ce qui passe, Wazuh centralise les alertes,
et un modèle XGBoost analyse chaque alerte pour dire : "attaque réelle" ou
"faux positif". Le tout en temps réel (~100 alertes/seconde).

### Les chiffres

- **57 000 alertes** collectées pour l'entraînement
- **36 caractéristiques** extraites par alerte (fréquence, type, IP source...)
- **96.3% de rappel** — le modèle ne rate quasiment aucune attaque
- **99.9% ROC AUC** — séparation quasi parfaite entre TP et FP
- **44 000+ prédictions** effectuées depuis la mise en route
- Inférence en continu, sans intervention humaine

### Comment ça marche

```
ParrotOS → attaque → Cible/Suricata → Wazuh → ML → Dashboard
                      ↑
              trafic normal aussi
```

Le modèle regarde chaque alerte, calcule un score, et décide si c'est une
véritable attaque ou juste du bruit. Les résultats remontent directement
dans le dashboard Wazuh.

### Ce qui est fait concrètement

- Tout le pipeline de A à Z : génération de trafic → collecte → entraînement
  → inférence en temps réel
- L'infrastructure est automatisée : les 3 VMs communiquent entre elles
  sans intervention humaine
- Le dashboard Wazuh affiche les prédictions en temps réel

### Ce qui reste à améliorer

- Le jeu de données d'entraînement est encore limité (~100 vrais positifs)
- Il faudrait plus de variété d'attaques
- Le pipeline pourrait être entièrement automatisé (ré-entraînement
  périodique)

### Pour le contexte

Ce projet a été développé sur mon temps libre, en partant d'une installation
Wazuh vierge. L'objectif était d'aller au bout de la chaîne : de l'attaque
jusqu'à la prédiction ML, avec un résultat concret et mesurable.
