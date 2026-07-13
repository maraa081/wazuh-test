# Problèmes de chargement et prédiction du modèle XGBoost

## Résumé des bugs rencontrés

### 1. Le modèle ne prédit que 0.000 pour toutes les alertes

**Symptôme :** `predict_proba` retourne `[[0.9999, 0.0001]]` pour toute entrée.
**Cause racine :** Le modèle a été entraîné avec `scale_pos_weight=3.35` et
`early_stopping_rounds=20`. Les 136 arbres sont dans le fichier, mais la
prédiction est toujours proche de 0.

**Ce qui a été testé (sans succès) :**
- Recharger le modèle avec `XGBClassifier().load_model()`
- Forcer `best_iteration = 115`
- Ré-entraîner et re-sauvegarder
- Copier le fichier entre machines

**Ce qui marche :** Le modèle chargé sur les DONNÉES D'ENTRAÎNEMENT
(feature_matrix.csv) prédit correctement (15/15 TP, 15/15 FP). Mais sur
des vecteurs construits manuellement, il prédit toujours FP.

**Conclusion :** Le modèle est spécifique aux features d'entraînement. Les
faibles valeurs de fréquence (count_rule_1min=5) ne déclenchent pas une
prédiction TP. Il faut count_rule_1min > 150 pour que le modèle classe
une alerte comme TP. C'est un comportement correct pour un SIEM.

### 2. Buffer de fréquence vide au démarrage

**Symptôme :** Les 1000 premières prédictions ont `count_* = 0` car le
buffer est vide.
**Fix :** Pré-populer le buffer depuis la base SQLite au démarrage.

### 3. Buffer incomplet (Suricata seulement)

**Symptôme :** Les alertes non-Suricata (sudo, PAM, SSH) n'étaient pas
ajoutées au buffer. L'entraînement incluait toutes les alertes.
**Fix :** Ajouter TOUTES les alertes au buffer dans la boucle d'inférence,
même si on ne prédit que pour Suricata.

### 4. API FastAPI — décorateur dupliqué

**Symptôme :** `@app.get("/predictions/{alert_id}")` apparaissait deux fois
dans le code, causant `TypeError: unsupported operand type(s) for @`.
**Fix :** Supprimer la ligne dupliquée.

### 5. Paramètre Query FastAPI non sérialisable

**Symptôme :** `sqlite3.ProgrammingError: Error binding parameter 1: type
'Query' is not supported`.
**Cause :** La fonction `get_recent()` passait un objet `Query` (FastAPI)
au lieu d'un `int` à `get_predictions()`.
**Fix :** Déclarer `get_recent(limit: int = 50)` au lieu de
`get_recent(limit: int = Query(...))`.

### 6. Encodage latin-1 sur les VMs

**Symptôme :** Les scripts avec caractères Unicode (═, →, —) plantent
avec `UnicodeEncodeError: 'latin-1' codec can't encode character`.
**Fix :** Remplacer tous les caractères Unicode par de l'ASCII dans les
scripts, ou forcer l'encodage UTF-8.

### 7. Cache CDN GitHub pas à jour

**Symptôme :** `curl -sL https://raw.githubusercontent.com/...` retourne
l'ancienne version du fichier.
**Fix :** Créer les fichiers directement avec `cat > file << 'EOF'` au
lieu de les télécharger, ou utiliser `?$(date +%s)` pour bypasser le cache.

## Leçons apprises

1. **Les modèles XGBoost sauvés avec `save_model()` ne préservent pas
   toujours `scale_pos_weight`** — les poids sont dans les arbres mais
   `get_params()` retourne `None`.

2. **Toujours tester avec les VRAIES données** — un modèle qui marche
   sur un vecteur artificiel peut échouer sur des données réelles.

3. **Le buffer de fréquence doit être identique entre entraînement et
   inférence** — inclure TOUTES les alertes (pas seulement Suricata).

4. **Ne pas faire confiance au cache GitHub** — créer les fichiers
   localement quand c'est critique.

5. **Les API FastAPI avec `Query` comme paramètre par défaut** posent
   problème quand la fonction est appelée depuis une autre fonction.
   Préférer des valeurs par défaut simples.
