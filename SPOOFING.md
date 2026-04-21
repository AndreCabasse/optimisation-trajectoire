# Détection de Spoofing GPS/ADS-B

Deux niveaux de détection sont disponibles :
- `SpoofingDetector` — règles physiques, rapide
- `AdvancedSpoofingDetector` — ML + patterns, +50% de détection

---

## 🚀 Guide Utilisation Rapide

### 1. Vérifier une trajectoire

```python
from src.data.kml_parser import KMLParser
from src.security.spoofing_detector import SpoofingDetector

parser = KMLParser("data/sample/F-HZUE-track-EGM96.kml")
trajectory = parser.parse()

detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)

if len(anomalies) == 0:
    print("✅ Trajectoire propre !")
else:
    print(f"⚠️ {len(anomalies)} anomalies détectées")
    summary = detector.get_summary(anomalies)
    print(f"Niveau de risque : {summary['risk_level']}")
    detector.print_report(anomalies, summary)
```

### 2. Nettoyer une trajectoire

```python
# Supprimer les points critical et high uniquement
indices_suspects = {a.index for a in anomalies if a.severity in ['critical', 'high']}
clean_positions = [p for i, p in enumerate(trajectory.positions) if i not in indices_suspects]
clean_trajectory = Trajectory(positions=clean_positions)
```

### 3. Scores de confiance (0 = suspect, 1 = normal)

```python
confidence = detector.compute_confidence_scores(trajectory, anomalies)
if confidence.mean() >= 0.9:
    print("✅ Données fiables")
elif confidence.mean() >= 0.7:
    print("⚠️ Vérification recommandée")
else:
    print("🚨 Nettoyage nécessaire")
```

### 4. Injecter du spoofing pour valider

```python
from src.security.spoofing_injector import SpoofingInjector
injector = SpoofingInjector(seed=42)
spoofed = injector.create_spoofing_scenario(trajectory, scenario="medium")
# 'light', 'medium', 'heavy', 'mixed'
```

### 5. Workflow complet avant optimisation

```python
detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)
if detector.get_summary(anomalies)['risk_level'] in ['critical', 'high']:
    print("⚠️ Nettoyage requis avant optimisation")
else:
    optimizer = TrajectoryOptimizer()
    result = optimizer.optimize(trajectory)
```

---

## 🛡️ Détecteur Avancé — Fonctionnalités

### Utilisation

```python
from src.security.advanced_spoofing_detector import AdvancedSpoofingDetector

detector = AdvancedSpoofingDetector(
    commercial_aircraft=True,
    enable_ml_scoring=True,
    enable_pattern_detection=True
)
report = detector.analyze_comprehensive(trajectory, verbose=True)

print(f"Score de risque   : {report.global_risk_score*100:.1f}%")
print(f"Patterns détectés : {report.detected_patterns}")
print(f"Replay attack     : {report.replay_attack_detected}")
print(f"Recommandations   : {report.recommendations}")
```

### Score de risque global

$$\text{Risk} = 0.4 \times \text{anomaly\_score} + 0.3 \times \text{confidence} + 0.15 \times \text{discontinuity} + 0.15 \times \text{implausibility}$$

| Score | Niveau | Action |
|-------|--------|--------|
| < 0.2 | 🟢 Authentique | Aucune |
| 0.2–0.5 | 🟡 Anomalies mineures | Vérification recommandée |
| 0.5–0.8 | 🟠 Risque élevé | Action requise |
| > 0.8 | 🔴 Spoofing quasi-certain | Alerte |

### 7 Patterns de Spoofing Reconnus

| Pattern | Description | Indique |
|---------|-------------|---------|
| **Altitude constante** | Position dérive mais altitude fixe | GPS spoofing simple |
| **Cercle parfait** | Trajectoire circulaire trop régulière | GPS jammer |
| **Répétition position** | Séquences identiques répétées | Replay attack |
| **Offset soudain** | Décalage instantané puis normal | Injection de spoofing |
| **Quantification** | Valeurs trop régulières/rondes | Spoofing algorithmique |
| **Virage impossible** | Changement > 90° en < 5s | Donnée falsifiée |
| **Discontinuité vitesse** | Saut brutal de vitesse | Coupure signal |

### Détection de Replay Attack

Fenêtres glissantes de 10 points, normalisées, comparées deux à deux. Si distance < 50 m → REPLAY DÉTECTÉ.

```
Vol authentique : A → B → C → D → E
Replay attack   : A → B → C → B → C → D   ← B→C rejoué
```

---

## 📊 Comparatif Basique vs Avancé

| Fonctionnalité | Basique | Avancé |
|----------------|---------|--------|
| Règles physiques | ✅ | ✅ |
| Outliers statistiques multivariés | ❌ | ✅ |
| Patterns de spoofing (7) | ❌ | ✅ |
| Replay attack | ❌ | ✅ |
| Score de risque 0–1 | ❌ | ✅ |
| Recommandations automatiques | ❌ | ✅ |
| Taux de détection | ~60% | ~90% |
| Faux positifs | Moyen | Faible |
| Temps de calcul (500 pts) | 0.6s | 1.5s |

---

## 🔬 Algorithmes Clés

### Outliers multivariés (Isolation Forest simplifié)
Features : [vitesse, accélération, variation altitude, altitude]. Normalisation Z-score, distance euclidienne multi-dim. Seuil : moyenne + 3×écart-type.

### Détection de cercle parfait
Coefficient de variation des distances au centroïde : si CV < 0.05 et rayon > 100m → GPS jammer.

---

## ⚙️ Personnalisation

```python
# Modifier les seuils
detector = SpoofingDetector()
detector.MAX_SPEED_COMMERCIAL = 350    # m/s (défaut : 300)
detector.MAX_ACCELERATION = 4          # m/s² (défaut : 3)
detector.MAX_G_FORCE = 2.5             # (défaut : 2.0)

# Mode moins strict (moins de faux positifs)
detector = AdvancedSpoofingDetector(strict_mode=False, commercial_aircraft=False)
```

---

## 🐛 Dépannage

| Problème | Solution |
|---------|----------|
| `ModuleNotFoundError: scipy` | `pip install scipy>=1.10.0` |
| Trop lent sur > 5000 points | Sous-échantillonner à 1000 pts avant analyse |
| Trop de faux positifs | `strict_mode=False` |
| Patterns non détectés | `enable_pattern_detection=True` |

---

## 📚 Références

1. Liu, F. T. et al. (2008). *Isolation Forest*
2. Humphreys, T. E. et al. (2012). *Detection Strategy for GPS Spoofing*
3. Strohmeier, M. et al. (2015). *On the Security of ADS-B*
4. ICAO Annex 10 — Aeronautical Telecommunications

---

## Scripts prêts à l'emploi

```bash
python examples/test_spoofing_quick.py          # Test rapide
python examples/example_advanced_spoofing.py    # 5 scénarios complets
python examples/visualiser_spoofing.py          # Carte HTML anomalies
```

---

*Version 2.0 — Février 2026 — ENAC Projet Technique 2A*
