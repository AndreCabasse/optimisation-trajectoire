# 📚 Scripts d'Exemples et de Comparaison

Ce dossier contient tous les scripts d'exemple pour utiliser et comparer les différentes méthodes d'optimisation de trajectoires.

---

## ⭐ NOUVEAU: Test des Corrections Réalisme 2026

### `test_corrections_realisme.py` - Validation des corrections
**Script de test pour valider toutes les corrections implémentées en janvier 2026.**

```bash
python examples/test_corrections_realisme.py
```

**Ce qu'il fait:**
- Teste les 5 méthodes d'optimisation
- Vérifie que `preserve_distance=True` fonctionne (B-spline & Hybrid)
- Teste les 3 profils d'optimisation NLP (BALANCED, FUEL_SAVER, COMFORT)
- Affiche la validation automatique pour chaque méthode
- Vérifie que toutes les contraintes physiques sont respectées

**Résultat attendu:**
```
✓ Validation réussie: résultat conforme aux contraintes physiques
```

**Si vous voyez des avertissements:**
```
⚠️  AVERTISSEMENTS DE VALIDATION:
   • Distance: 3.2% de variation (seuil hybrid: 0.5%)
```
→ Cela indique un problème à investiguer

**Durée:** ~2 minutes (teste 7 configurations)

**Voir aussi:** `CORRECTIONS_REALISME_2026.md` pour les détails des corrections

---

## 🎯 Scripts Principaux

### 1. `optimize_trajectory.py` - Exemple d'utilisation de base
Script principal montrant comment utiliser le système d'optimisation.

```bash
python optimize_trajectory.py
```

**Ce qu'il fait:**
- Charge une trajectoire KML
- L'optimise avec la méthode Hybride
- Génère des visualisations
- Affiche les métriques

**Fichiers générés:**
- `output/trajectory_map.html` - Carte interactive

---

### 2. `compare_methods.py` - Comparaison complète des 5 méthodes
Script de comparaison détaillée de toutes les méthodes d'optimisation.

```bash
python compare_methods.py
```

**Ce qu'il fait:**
- Compare les 5 méthodes (Kalman, B-spline, Hybride, Météo, NLP)
- Calcule toutes les métriques (smoothness, compression, etc.)
- Génère 8 graphiques détaillés
- Crée une carte interactive avec toutes les trajectoires
- Affiche un tableau comparatif complet

**Fichiers générés:**
- `output/methods_comparison.png` - 8 graphiques (vue dessus, altitude, zoom, écarts, barres)
- `output/methods_comparison_map.html` - Carte Folium interactive

**Durée:** ~30 secondes (dont 28s pour NLP)

---

### 3. `radar_comparison.py` - Graphique radar
Génère un graphique radar pour comparer visuellement les méthodes selon 5 critères.

```bash
python radar_comparison.py
```

**Critères évalués:**
- Compression (réduction de points)
- Lissage (smoothness)
- Distance optimisée
- Rapidité de calcul
- Précision

**Fichiers générés:**
- `output/radar_comparison.png` - Graphique radar + tableau de scores

---

### 4. `create_infographic.py` - Infographie résumée
Crée une infographie visuelle avec tableau récapitulatif.

```bash
python create_infographic.py
```

**Fichiers générés:**
- `output/infographie_comparison.png` - Infographie complète avec tableau

---

### 5. `run_all_comparisons.py` - Exécution de tout en une commande
Exécute automatiquement les 3 scripts de comparaison.

```bash
python run_all_comparisons.py
```

**Recommandé pour générer tous les visuels d'un coup !**

---

## 🔬 Scripts de Test et Débogage

### `test_visual.py`
Teste la visualisation basique des trajectoires optimisées.

### `debug_spline.py`
Débogue les interpolations B-spline pour vérifier la cohérence.

### `rapport_diff.py`
Génère un rapport détaillé des différences entre original et optimisé.

### `test_*.py`
Autres scripts de test pour différents aspects du système.

---

## 📊 Fichiers de Sortie

Tous les fichiers sont générés dans le dossier `output/`:

| Fichier | Généré par | Description |
|---------|------------|-------------|
| `methods_comparison.png` | compare_methods.py | 8 graphiques détaillés |
| `methods_comparison_map.html` | compare_methods.py | Carte interactive (toutes trajectoires) |
| `radar_comparison.png` | radar_comparison.py | Graphique radar + scores |
| `infographie_comparison.png` | create_infographic.py | Infographie résumée |
| `trajectory_map.html` | optimize_trajectory.py | Carte simple (1 trajectoire) |

---

## 🚀 Démarrage Rapide

### Option 1: Comparaison complète (recommandé)
```bash
python run_all_comparisons.py
```

### Option 2: Comparaison détaillée uniquement
```bash
python compare_methods.py
```

### Option 3: Exemple simple
```bash
python optimize_trajectory.py
```

---

## 📈 Résultats Attendus

Après exécution de `run_all_comparisons.py`, vous devriez obtenir:

```
output/
├── methods_comparison.png          # 8 graphiques (vue dessus, altitude, zoom, etc.)
├── methods_comparison_map.html     # Carte interactive avec 6 trajectoires
├── radar_comparison.png            # Graphique radar + tableau scores
└── infographie_comparison.png      # Infographie résumée
```

---

## 🎓 Pour Aller Plus Loin

### Modifier le nombre de points cibles

Dans n'importe quel script de comparaison, modifiez:
```python
TARGET_POINTS = 200  # Changez cette valeur
```

**Effets:**
- Plus élevé (300-400) → Meilleure précision, moins de compression
- Plus faible (50-100) → Compression maximale, risque d'oscillations

### Utiliser vos propres données

Modifiez le chemin du fichier KML:
```python
kml_file = Path("votre/chemin/vers/fichier.kml")
```

### Tester une seule méthode

```python
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod

optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result = optimizer.optimize(trajectory, target_points=200)
```

---

## 📖 Documentation Complémentaire

- **[../COMPARAISON_METHODES.md](../COMPARAISON_METHODES.md)** - Analyse détaillée de toutes les méthodes
- **[../README.md](../README.md)** - Vue d'ensemble du projet
- **[../QUICKSTART.md](../QUICKSTART.md)** - Guide de démarrage rapide

---

## 💡 Conseils

1. **Première utilisation** : Lancez `run_all_comparisons.py` pour avoir une vue complète
2. **Tests rapides** : Utilisez `radar_comparison.py` (le plus rapide)
3. **Analyse détaillée** : Utilisez `compare_methods.py` et consultez COMPARAISON_METHODES.md
4. **Pour présentation** : L'infographie (`create_infographic.py`) est idéale

---

## 🐛 Dépannage

### Erreur "Module not found"
```bash
pip install -r ../requirements.txt
```

### Graphiques vides ou erreurs matplotlib
```bash
pip install --upgrade matplotlib numpy scipy
```

### Carte HTML ne s'affiche pas
Ouvrez directement `output/methods_comparison_map.html` dans votre navigateur.

---

## 📝 Notes

- Les avertissements Unicode (emojis manquants) sont normaux et n'affectent pas les résultats
- Le script NLP peut prendre jusqu'à 30 secondes (optimisation complexe)
- Les fichiers de sortie sont écrasés à chaque exécution

---

**Questions ou problèmes ?** Consultez [../COMPARAISON_METHODES.md](../COMPARAISON_METHODES.md) pour plus de détails !
