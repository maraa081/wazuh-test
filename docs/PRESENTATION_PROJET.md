# Labo Détection d'Intrusion avec Machine Learning

## Contexte

Projet personnel : construire un pipeline de détection d'intrusion bout en bout,
automatisé, et basé sur l'IA. L'infrastructure tourne sur mon PC portable
via 3 machines virtuelles VirtualBox.

Les machines :
- **Cible** (Ubuntu 22.04) — reçoit les attaques, fait tourner Suricata
- **Manager** (Ubuntu 24.04) — centralise les alertes avec Wazuh, héberge le modèle ML
- **Attaquant** (ParrotOS) — génère le trafic malveillant

---

## Le problème

Wazuh est un bon SIEM, mais il génère des milliers d'alertes par jour.
Parmi elles, une majorité sont des **faux positifs** : du trafic normal
(requêtes DNS, scans réseaux anodins, traffic applicatif) qui déclenche
une alerte parce qu'il ressemble à une attaque.

En conditions réelles, un analyste SOC passe environ 80% de son temps à
trier ces faux positifs. C'est une perte de temps et d'énergie.

---

## Ce que j'ai fait

Un pipeline en 5 étapes :

1. **Génération de trafic** — scripts Docker qui simulent du trafic
   légitime (SSH, HTTP, DNS, ICMP) mélangé à des attaques (nmap, hydra,
   flood, exfiltration)

2. **Collecte des alertes** — Suricata capte le trafic via af-packet,
   Wazuh centralise tout dans alerts.json

3. **Labellisation** — chaque alerte est marquée "vrai positif" ou
   "faux positif" selon la fenêtre temporelle de l'attaque

4. **Feature engineering + entraînement** — 36 features extraites
   (fréquence par règle, par IP source, temporalité, etc.),
   XGBoost entraîné sur ~57 000 alertes

5. **Inférence temps réel** — le modèle tourne en continu sur le Manager,
   score chaque nouvelle alerte et stocke la prédiction dans OpenSearch
   pour l'afficher dans le dashboard Wazuh

---

## Résultats

- **Rappel (Recall) : 96.3%** — le modèle rate très peu d'attaques réelles
- **Précision : ~92%** — peu de faux positifs dans les alertes remontées
- **ROC AUC : 99.9%** — séparation quasi-parfaite entre TP et FP
- **~100 alertes traitées par seconde** — inférence en temps réel
- **44 000+ prédictions** depuis la mise en route
- Architecture sans dépendance externe : tout tourne sur les 3 VMs

---

## Architecture (schéma)

```
[ParrotOS] ──nmap/hydra──► [Cible]
                               │
                          [Suricata] (af-packet)
                               │
                          [Wazuh Agent]
                               │
                          [Manager Wazuh]
                               │
                       alerts.json (57 000 lignes)
                               │
                          [ML XGBoost]
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
          [OpenSearch]                 [Dashboard Wazuh]
         (prédictions)                (visualisations)
```

---

## Ce que j'ai appris

- Suricata peut charger 50 000 règles sans erreur et **ne pas en activer
  une seule** si le chemin des fichiers de règles est mal configuré.
  Aucun warning, juste 0 alertes.
- L'alignement entre l'entraînement et l'inférence est critique : si
  les features ne sont pas calculées exactement de la même manière,
  le modèle prédit n'importe quoi.
- Un buffer de fréquence vide au démarrage = des prédictions fausses
  jusqu'à ce qu'il se remplisse. Solution : pré-populer avec les
  dernières alertes.
- Les attaques Docker en localhost (la cible s'attaque elle-même) ne
  passent pas par l'interface réseau → Suricata ne les voit pas.
  Il faut un vrai attaquant sur le réseau.

---

## Pour aller plus loin

- Entraîner le modèle sur plus d'attaques variées (actuellement ~100 TP
  seulement)
- Automatiser le cycle complet : attaque → collecte → ré-entraînement
- Tester en conditions réelles sur un vrai réseau (pas que du labo)
