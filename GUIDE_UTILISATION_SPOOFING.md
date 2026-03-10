# 🚀 Guide d'utilisation rapide - Détection de Spoofing

## Installation (déjà fait ✅)

Le système est déjà installé dans ton projet. Aucune installation supplémentaire nécessaire !

---

## 📖 Utilisation de base

### 1️⃣ Vérifier une trajectoire (le plus simple)

```python
from src.data.kml_parser import KMLParser
from src.security.spoofing_detector import SpoofingDetector

# Charger votre fichier KML
parser = KMLParser("data/sample/F-HZUE-track-EGM96.kml")
trajectory = parser.parse()

# Vérifier la sécurité
detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)

# Résultat
if len(anomalies) == 0:
    print("✅ Trajectoire propre !")
else:
    print(f"⚠️ {len(anomalies)} anomalies détectées")
```

---

### 2️⃣ Analyser en détail

```python
# Obtenir un résumé
summary = detector.get_summary(anomalies)

print(f"Niveau de risque : {summary['risk_level']}")
print(f"Spoofing détecté : {summary['spoofing_detected']}")

# Afficher le rapport complet
detector.print_report(anomalies, summary)
```

---

### 3️⃣ Nettoyer une trajectoire

```python
from src.data.data_models import Trajectory

# Identifier les points suspects (critical + high seulement)
indices_suspects = set()
for anomalie in anomalies:
    if anomalie.severity in ['critical', 'high']:
        indices_suspects.add(anomalie.index)

# Créer une trajectoire nettoyée
clean_positions = [
    p for i, p in enumerate(trajectory.positions)
    if i not in indices_suspects
]

clean_trajectory = Trajectory(positions=clean_positions)
print(f"✅ {len(clean_positions)} points conservés")
```

---

### 4️⃣ Utiliser les scores de confiance

```python
# Calculer la confiance (0.0 = suspect, 1.0 = normal)
confidence = detector.compute_confidence_scores(trajectory, anomalies)

print(f"Score moyen : {confidence.mean():.3f}")
print(f"Points suspects (<0.8) : {(confidence < 0.8).sum()}")

# Décision automatique
if confidence.mean() >= 0.9:
    print("✅ Données fiables")
elif confidence.mean() >= 0.7:
    print("⚠️ Vérification recommandée")
else:
    print("🚨 Nettoyage nécessaire")
```

---

### 5️⃣ Tester avec injection (pour valider)

```python
from src.security.spoofing_injector import SpoofingInjector

# Créer l'injecteur
injector = SpoofingInjector(seed=42)

# Injecter du spoofing artificiel
spoofed = injector.create_spoofing_scenario(
    trajectory,
    scenario="medium"  # 'light', 'medium', 'heavy', 'mixed'
)

# Vérifier que ça détecte bien
anomalies = detector.detect_anomalies(spoofed)
print(f"Détection : {len(anomalies)} anomalies trouvées")
```

---

## 🎯 Cas d'usage pratiques

### Workflow 1 : Vérification avant optimisation

```python
# 1. Charger
trajectory = parser.parse()

# 2. Vérifier
detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)
summary = detector.get_summary(anomalies)

# 3. Décider
if summary['risk_level'] in ['critical', 'high']:
    print("⚠️ Nettoyage requis")
    # Nettoyer ici...
else:
    print("✅ Données OK pour optimisation")
    # Continuer avec TrajectoryOptimizer...
```

### Workflow 2 : Analyse de fichiers multiples

```python
from pathlib import Path

kml_files = Path("data/sample").glob("*.kml")
detector = SpoofingDetector()

for kml_file in kml_files:
    parser = KMLParser(str(kml_file))
    trajectory = parser.parse()
    
    anomalies = detector.detect_anomalies(trajectory)
    print(f"{kml_file.name:30s} : {len(anomalies):3d} anomalies")
```

### Workflow 3 : Monitoring en temps réel

```python
# Analyser régulièrement
def check_trajectory_security(trajectory):
    detector = SpoofingDetector()
    anomalies = detector.detect_anomalies(trajectory)
    
    critical = [a for a in anomalies if a.severity == 'critical']
    
    if critical:
        print(f"🚨 ALERTE : {len(critical)} anomalies critiques !")
        # Envoyer notification, logs, etc.
        return False
    
    return True

# Utilisation
if check_trajectory_security(trajectory):
    # Continuer le traitement
    pass
```

---

## 🛠️ Scripts prêts à l'emploi

### Test rapide
```bash
python examples/test_spoofing_quick.py
```
Vérifie rapidement qu'une trajectoire fonctionne bien.

### Exemples interactifs
```bash
python examples/exemple_utilisation_spoofing.py
```
Menu avec 6 exemples différents :
1. Vérification simple
2. Analyse détaillée
3. Nettoyage
4. Scores de confiance
5. Test robustesse
6. Workflow complet

### Test complet
```bash
python examples/example_spoofing_detection.py
```
Teste tous les scénarios + génère des cartes HTML.

---

## 📊 Interpréter les résultats

### Niveaux de risque

| Niveau | Signification | Action |
|--------|---------------|--------|
| **low** | Pas d'anomalie significative | ✅ Utiliser les données |
| **medium** | Quelques anomalies mineures | ⚠️ Vérifier si nécessaire |
| **high** | Anomalies importantes | 🔍 Investigation recommandée |
| **critical** | Spoofing probable | 🚨 Ne pas utiliser / Nettoyer |

### Sévérités d'anomalies

| Sévérité | Confiance | Action |
|----------|-----------|--------|
| **low** | 0.8 | Surveiller |
| **medium** | 0.6 | Vérifier |
| **high** | 0.3 | Nettoyer |
| **critical** | 0.1 | Rejeter |

### Types d'anomalies courants

- **acceleration_excessive** : Changements de vitesse trop brutaux (souvent du bruit GPS)
- **montee_irrealiste** : Taux de montée irréaliste (possible spoofing)
- **saut_position** : Téléportation GPS (spoofing probable)
- **temps_incoherent** : Timestamps désordonnés (erreur de capteur ou spoofing)
- **altitude_negative** : Altitude sous la mer hors eau (spoofing certain)

---

## 💡 Conseils

### ✅ Bonnes pratiques

1. **Toujours vérifier** avant d'optimiser une trajectoire
2. **Nettoyer les critical et high**, garder medium et low
3. **Utiliser les scores de confiance** pour des décisions automatiques
4. **Tester avec injection** pour valider votre système
5. **Logger les anomalies** pour analyse ultérieure

### ⚠️ À éviter

1. Ne pas ignorer les anomalies critiques
2. Ne pas sur-nettoyer (garder medium/low peut être ok)
3. Ne pas utiliser uniquement le nombre d'anomalies (regarder la sévérité)
4. Ne pas oublier que du bruit GPS normal peut créer des anomalies mineures

---

## 🔧 Personnalisation

### Modifier les seuils

Tu peux créer ton propre détecteur avec des seuils personnalisés :

```python
detector = SpoofingDetector()

# Modifier les seuils (par défaut)
detector.MAX_SPEED_COMMERCIAL = 350  # au lieu de 300 m/s
detector.MAX_ACCELERATION = 4  # au lieu de 3 m/s²
detector.MAX_G_FORCE = 2.5  # au lieu de 2.0

anomalies = detector.detect_anomalies(trajectory)
```

### Filtrer certains types

```python
# Ignorer certains types d'anomalies
anomalies_filtrees = [
    a for a in anomalies
    if a.anomaly_type not in [AnomalyType.ACCELERATION_EXCESSIVE]
]
```

---

## 📚 Documentation complète

Pour plus de détails, consulte :
- **[SPOOFING_DETECTION.md](../SPOOFING_DETECTION.md)** - Documentation technique complète
- **[src/security/](../src/security/)** - Code source avec docstrings détaillées

---

## 🎓 Exemples d'intégration avec ton projet

### Dans optimize_trajectory.py

```python
from src.security.spoofing_detector import SpoofingDetector

# Avant l'optimisation
detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)

if detector.get_summary(anomalies)['risk_level'] == 'critical':
    print("⚠️ Trajectoire suspecte - Annulation")
    exit(1)

# Continuer avec l'optimisation...
optimizer = TrajectoryOptimizer()
optimized = optimizer.optimize(trajectory, method="hybrid")
```

### Dans dashboard.py

```python
# Ajouter un indicateur de sécurité
detector = SpoofingDetector()
anomalies = detector.detect_anomalies(trajectory)
confidence = detector.compute_confidence_scores(trajectory, anomalies)

st.metric(
    "Score de sécurité",
    f"{confidence.mean():.1%}",
    delta="Fiable" if confidence.mean() > 0.9 else "Suspect"
)
```

---

**🛡️ Tes données ADS-B sont maintenant protégées !**
