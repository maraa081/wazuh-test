# Charte de développement MLOps — Projet Wazuh AI Filter

## I. Charte technique & sécurité de code

1. **Encodage ASCII strict** — interdiction des caractères Unicode (═, →, 🔴)
   dans les scripts Bash/Python/conf. Utiliser "===", "->", "[INFO]".

2. **FastAPI & SQLite** — ne pas mélanger les `Query` FastAPI avec les types
   natifs Python. Caster systématiquement (`int()`, `str()`) avant les requêtes
   SQL. Vérifier les décorateurs dupliqués avant déploiement.

3. **Déploiement** — ne JAMAIS dépendre du cache CDN GitHub. Utiliser des
   `cat << 'EOF' >` ou des copies locales depuis un clone git propre.

## II. Protocole MLOps (Entraînement vs Inférence)

1. **Alignment strict des features** — les features temporelles (count_rule_1min)
   doivent être calculées avec le même scope en entraînement et en inférence.
   Le buffer de fréquence consomme TOUT le flux d'alertes (y compris PAM, sudo, SSH).

2. **Gestion d'état** — pas de cold start. Au démarrage, pré-charger les N
   dernières minutes d'alertes depuis SQLite pour peupler le buffer.

3. **Test de non-régression** — avant de valider un modèle reloadé, exécuter
   un test unitaire avec un vecteur d'entraînement connu et valider que
   la probabilité correspond à celle de l'évaluation.

## III. Check-list de validation

Pour chaque nouvelle fonctionnalité :
- [ ] Code en ASCII strict
- [ ] Types API castés avant SQL
- [ ] Buffer de warm-up présent
- [ ] Pas de dépendance CDN GitHub
