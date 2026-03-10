# Données de trajectoires

## Où placer vos fichiers KML ?

Placez vos fichiers KML téléchargés depuis OpenSky Network dans ce dossier :

```
data/sample/
```

Par exemple :
- `data/sample/mon_vol.kml`
- `data/sample/paris_toulouse_20240130.kml`
- `data/sample/flight_AF447.kml`

## Comment utiliser vos fichiers ?

### Option 1 : Modifier l'exemple

Dans `examples/optimize_trajectory.py`, ligne 24, remplacez :

```python
kml_file = "data/sample/flight_trajectory.kml"
```

par le nom de votre fichier :

```python
kml_file = "data/sample/mon_vol.kml"  # ← votre fichier ici
```

### Option 2 : Utiliser directement dans votre code

```python
from src.data.kml_parser import KMLParser

# Chemin vers votre fichier KML
parser = KMLParser('data/sample/votre_fichier.kml')
trajectory = parser.parse()

print(f"Vol chargé : {trajectory}")
```

## Comment obtenir des fichiers KML ?

### OpenSky Network (Gratuit)
1. Visitez https://opensky-network.org/
2. Onglet "Research" → "Download Data"
3. Cherchez un vol par numéro ou route
4. Exportez en format KML

### FlightRadar24
- Nécessite un compte premium
- Permet d'exporter l'historique des vols

## Format KML supporté

Le parser supporte plusieurs formats KML :
- ✅ `gx:Track` avec timestamps (format OpenSky standard)
- ✅ `LineString` simple avec coordonnées
- ✅ Multiple `Placemarks`

## Exemple de structure KML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Flight AF1234</name>
    <Placemark>
      <LineString>
        <coordinates>
          2.3522,48.8566,150
          2.3600,48.8700,1000
          ...
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
```
