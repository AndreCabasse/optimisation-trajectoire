# Méthodes d'Optimisation — Analyse & Comparaison

## 📊 Tableau Comparatif (Résultats sur trajectoire réelle)

| Méthode | Points | Distance | Compression | Temps calcul | Smoothness | Statut |
|---------|--------|----------|-------------|--------------|------------|--------|
| **Original** | 501 | 902.22 km | — | — | 147 624 | — |
| **Kalman** | 501 | 902.17 km | 100% | 0.040s | 147 064 | ✅ Correct |
| **B-spline** | 200 | 901.78 km | 40% | 0.002s | 25 496 | ⚠️ À corriger |
| **Hybride** | 200 | 901.76 km | 40% | 0.041s | **25 029** ⭐ | ⚠️ À corriger |
| **Météo** | 200 | 901.81 km | 40% | 0.041s | 40 403 | ✅ Correct |
| **NLP** | 99 | 896.87 km | **20%** ⭐ | 27.993s | 147 019 | ⚠️ À améliorer |

---

## 🔬 Analyse Détaillée

### 1. Filtre de Kalman

**Objectif** : Lissage probabiliste pour éliminer le bruit ADS-B.

**Comportement attendu** :
- Distance : ±0.1% (préservée naturellement)
- Points : identiques (pas de compression)
- Effet : réduit les oscillations de mesure

**Paramètres réalistes** :
```python
process_noise = 0.5        # Bruit du modèle de mouvement
measurement_noise = 5.0    # Bruit ADS-B typique (5m)
```

**Cas d'usage** : Lissage données bruitées, pré-traitement, temps réel.

**Statut : ✅ CORRECT** — Ne modifie pas la trajectoire réelle.

---

### 2. B-spline

**Objectif** : Compression et interpolation par courbes cubiques.

**Problème identifié** : Le `smoothing_factor > 0` peut couper les virages et réduire artificiellement la distance (ex: 908 km → 890 km, -2%).

**Deux modes distincts** :

| Mode | `smoothing_factor` | Variation distance | Usage |
|------|-------------------|--------------------|-------|
| COMPRESSION (défaut) | 0.0 | ±0.5% max | Archivage, stockage |
| OPTIMISATION | > 0 | ±3% acceptable | Recherche d'efficacité |

**Correction implémentée** :
```python
BSplineOptimizer(preserve_distance=True)   # Force smoothing_factor=0
BSplineOptimizer(auto_smooth=True)          # Détection par validation croisée
```

**Statut : ⚠️ Correction disponible** — Utiliser `preserve_distance=True` par défaut.

---

### 3. Hybride (Kalman + B-spline)

**Objectif** : Meilleur compromis — éliminer bruit puis compresser.

**Problème** : Héritait du bug B-spline si `smoothing_factor > 0`.

**Correction implémentée** :
```python
# Étape 1 : Kalman (lissage du bruit)
smoothed = self.kalman.smooth_trajectory(trajectory)
# Étape 2 : B-spline en mode COMPRESSION STRICT
self.bspline.smoothing_factor = 0.0
optimized = self.bspline.optimize(smoothed, target_points)
```

**Résultat corrigé** :
- Distance : ±0.5%
- Smoothness optimale (25 029 vs 147 624 original)
- 60% de compression

**Statut : ⚠️ Correction disponible** — Méthode **RECOMMANDÉE** avec les corrections. 🏆

---

### 4. Météo (Weather-Aware)

**Objectif** : Optimisation réelle pour profiter des vents favorables.

**Comportement attendu** :
- Distance peut AUGMENTER de +1% à +5% — c'est **normal**
- Raison : dévier pour profiter du vent arrière
- Gain : temps de vol ou carburant réduit

**Paramètres** :
```python
max_deviation = distance * 0.03   # 3% déviation max
```

**Validation** :
- Distance +3% ET temps -5% → ✅ Bénéfique
- Distance +3% ET temps +2% → ⚠️ Pas optimal

**Statut : ✅ CORRECT** — C'est une vraie optimisation, pas du lissage.

---

### 5. NLP Direct Collocation

**Objectif** : Optimisation mathématique avec contraintes physiques.

**Problème** : Pondérations fixes dans la fonction objectif — distance trop peu prioritaire (0.01).

**Profils d'optimisation disponibles** :

```python
class OptimizationProfile(Enum):
    FUEL_SAVER = "fuel_saver"    # Priorité: économie carburant
    COMFORT    = "comfort"        # Priorité: confort passagers
    BALANCED   = "balanced"       # Équilibre (défaut)
```

| Profil | `distance` | `smoothness` | `altitude` | `climb` |
|--------|-----------|-------------|----------|--------|
| FUEL_SAVER | 0.50 | 0.10 | 0.30 | 0.50 |
| COMFORT | 0.01 | 0.40 | 0.50 | 0.80 |
| BALANCED | 0.20 | 0.30 | 0.30 | 0.15 |

**Statut : ⚠️ À améliorer** — Utiliser profils configurables.

---

## 🎯 Tolérance de Variation de Distance

| Variation | Interprétation | Action |
|-----------|----------------|--------|
| < 1% | ✅ Excellent — lissage pur | Aucune |
| 1–3% | ✅ Acceptable | Vérifier gain temps/carburant |
| 3–5% | ⚠️ Optimisation agressive | Expliquer bénéfice |
| > 5% | ❌ Suspect | Alerte utilisateur |

**Seuils par méthode** :
```python
thresholds = {
    'kalman': 0.5, 'bspline': 1.0, 'hybrid': 0.5,
    'weather': 5.0, 'direct_collocation': 3.0
}
```

---

## 💡 Recommandations d'Usage

| Besoin | Méthode | Raison |
|--------|---------|--------|
| **Usage général** | 🥇 Hybride | Meilleur équilibre qualité/performance |
| **Temps réel** | 🥈 B-spline | Ultra-rapide (0.002s) |
| **Compression max** | 🥉 NLP | 80% de réduction |
| **Lissage simple** | Kalman | Garde tous les points |
| **Avec météo** | Weather / NLP FUEL_SAVER | Gains mesurables carburant |

```python
# Usage général (recommandé)
optimizer = TrajectoryOptimizer(method=OptimizationMethod.HYBRID)
result = optimizer.optimize(trajectory, target_points=200)

# Compression maximale
optimizer = TrajectoryOptimizer(method=OptimizationMethod.NLP)
result = optimizer.optimize(trajectory, target_points=100)

# Temps réel
optimizer = TrajectoryOptimizer(method=OptimizationMethod.BSPLINE)
result = optimizer.optimize(trajectory, target_points=200)
```

---

## 📐 Métriques Expliquées

**Smoothness** : $\sum_{i} \|\mathbf{a}_i\|$ — plus faible = meilleur lissage.

**Courbure** : $\kappa = \frac{\|\mathbf{v} \times \mathbf{a}\|}{\|\mathbf{v}\|^3}$ — détecte les virages serrés.

**Compression** : $\frac{\text{points opt.}}{\text{points orig.}} \times 100\%$ — 40% = réduction de 60%.

> ⚠️ Les écarts point à point (ex: 380 km pour B-spline) sont **normaux** : les points optimisés ne correspondent pas aux mêmes instants que les originaux. La distance totale et la smoothness sont les métriques pertinentes.

---

## ✅ Checklist de Validation

Avant de présenter un résultat :

- [ ] Variation de distance < seuil de la méthode
- [ ] Altitude entre 0 et 15 000 m (A320neo)
- [ ] Taux de montée < 15 m/s (≈ 3 000 ft/min)
- [ ] Forces G < 1.5g (confort passagers)
- [ ] Timestamps strictement croissants
- [ ] Aucun point dupliqué
- [ ] Aucun avertissement de validation émis

---

## 📚 Références Théoriques

- **Kalman** : Kalman, R. E. (1960). *A New Approach to Linear Filtering and Prediction Problems*
- **B-spline** : De Boor, C. (1978). *A Practical Guide to Splines* — `scipy.interpolate.splrep`
- **Direct Collocation** : Betts, J. T. (2010). *Practical Methods for Optimal Control*

---

*Dernière mise à jour : Mars 2026 — ENAC Projet Technique 2A*
