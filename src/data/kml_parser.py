"""
Parser pour fichiers KML d'OpenSky Network
"""
from typing import List, Optional
from datetime import datetime
from lxml import etree  # type: ignore
import re
from pathlib import Path

from .data_models import Position, Trajectory


class KMLParser:
    """Parse les fichiers KML contenant des données de trajectoires ADS-B"""
    
    # Namespaces KML standards
    NAMESPACES = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    def __init__(self, filepath: str):
        """
        Initialise le parser
        
        Args:
            filepath: Chemin vers le fichier KML
        """
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier KML non trouvé : {filepath}")
        
        self.tree: Optional[etree._ElementTree] = None  # type: ignore
        self.root: Optional[etree._Element] = None  # type: ignore
    
    def parse(self) -> Trajectory:
        """
        Parse le fichier KML et retourne une Trajectory
        
        Returns:
            Trajectory: Objet trajectoire avec tous les points
        """
        # Charger le fichier XML
        self.tree = etree.parse(str(self.filepath))
        assert self.tree is not None
        self.root = self.tree.getroot()
        assert self.root is not None
        
        # Extraire le nom du vol si disponible
        flight_id = self._extract_flight_id()
        
        # Extraire les positions
        positions = self._extract_positions()
        
        if not positions:
            raise ValueError("Aucune position trouvée dans le fichier KML")
        
        return Trajectory(positions=positions, flight_id=flight_id)
    
    def _extract_flight_id(self) -> Optional[str]:
        """Extrait l'identifiant du vol depuis le KML"""
        assert self.root is not None
        # Chercher dans le nom du document
        name_elem = self.root.find('.//kml:Document/kml:name', self.NAMESPACES)
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        
        # Sinon utiliser le nom du fichier
        return self.filepath.stem
    
    def _extract_positions(self) -> List[Position]:
        """Extrait toutes les positions depuis le KML"""
        assert self.root is not None
        positions = []
        
        # Méthode 1 : Track avec gx:coord et when (format OpenSky typique)
        track = self.root.find('.//gx:Track', self.NAMESPACES)
        if track is not None:
            positions = self._parse_gx_track(track)
            if positions:
                return positions
        
        # Méthode 2 : LineString avec coordonnées simples
        linestring = self.root.find('.//kml:LineString/kml:coordinates', self.NAMESPACES)
        if linestring is not None:
            positions = self._parse_linestring(linestring)
            if positions:
                return positions
        
        # Méthode 3 : Placemarks multiples
        placemarks = self.root.findall('.//kml:Placemark', self.NAMESPACES)
        if placemarks:
            positions = self._parse_placemarks(placemarks)
        
        return positions
    
    def _parse_gx_track(self, track_elem) -> List[Position]:
        """Parse un élément gx:Track (format Google Earth étendu)"""
        positions = []
        
        # Extraire les timestamps
        when_elems = track_elem.findall('kml:when', self.NAMESPACES)
        timestamps = [self._parse_timestamp(w.text) for w in when_elems]
        
        # Extraire les coordonnées
        coord_elems = track_elem.findall('gx:coord', self.NAMESPACES)
        
        for timestamp, coord_elem in zip(timestamps, coord_elems):
            if coord_elem.text:
                coords = coord_elem.text.strip().split()
                if len(coords) >= 3:
                    lon, lat, alt = float(coords[0]), float(coords[1]), float(coords[2])
                    positions.append(Position(
                        latitude=lat,
                        longitude=lon,
                        altitude=alt,
                        timestamp=timestamp
                    ))
        
        return positions
    
    def _parse_linestring(self, linestring_elem) -> List[Position]:
        """Parse un LineString simple (sans timestamps)"""
        positions = []
        
        if linestring_elem.text:
            # Les coordonnées sont au format : lon,lat,alt lon,lat,alt ...
            coord_text = linestring_elem.text.strip()
            coord_pairs = coord_text.split()
            
            # Générer des timestamps fictifs espacés d'une seconde
            base_time = datetime.now()
            
            for i, coord_str in enumerate(coord_pairs):
                coords = coord_str.split(',')
                if len(coords) >= 3:
                    lon, lat, alt = float(coords[0]), float(coords[1]), float(coords[2])
                    # Timestamp fictif
                    timestamp = datetime.fromtimestamp(base_time.timestamp() + i)
                    positions.append(Position(
                        latitude=lat,
                        longitude=lon,
                        altitude=alt,
                        timestamp=timestamp
                    ))
        
        return positions
    
    def _parse_placemarks(self, placemarks) -> List[Position]:
        """Parse des Placemarks individuels"""
        positions = []
        
        for placemark in placemarks:
            point = placemark.find('.//kml:Point/kml:coordinates', self.NAMESPACES)
            if point is not None and point.text:
                coords = point.text.strip().split(',')
                if len(coords) >= 3:
                    lon, lat, alt = float(coords[0]), float(coords[1]), float(coords[2])
                    
                    # Chercher un timestamp dans la description ou le nom
                    timestamp = self._extract_timestamp_from_placemark(placemark)
                    
                    positions.append(Position(
                        latitude=lat,
                        longitude=lon,
                        altitude=alt,
                        timestamp=timestamp
                    ))
        
        # Trier par timestamp
        positions.sort(key=lambda p: p.timestamp)
        return positions
    
    def _extract_timestamp_from_placemark(self, placemark) -> datetime:
        """Extrait le timestamp d'un Placemark"""
        # Chercher dans TimeStamp
        timestamp_elem = placemark.find('.//kml:TimeStamp/kml:when', self.NAMESPACES)
        if timestamp_elem is not None and timestamp_elem.text:
            return self._parse_timestamp(timestamp_elem.text)
        
        # Sinon timestamp actuel
        return datetime.now()
    
    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse un timestamp au format ISO 8601"""
        # Format typique : 2024-01-30T10:30:45Z ou 2024-01-30T10:30:45.123Z
        timestamp_str = timestamp_str.strip()
        
        # Supprimer le Z final si présent
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1]
        
        # Essayer différents formats
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # Si aucun format ne fonctionne, utiliser maintenant
        return datetime.now()
    
    def validate(self) -> bool:
        """Valide le fichier KML"""
        try:
            self.parse()
            return True
        except Exception as e:
            print(f"Erreur de validation : {e}")
            return False
