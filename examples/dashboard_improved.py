"""
Dashboard Streamlit AMÉLIORÉ pour l'optimisation de trajectoires
Lance avec : streamlit run dashboard_improved.py
"""
import streamlit as st
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.kml_parser import KMLParser
from src.optimization.trajectory_optimizer import TrajectoryOptimizer, OptimizationMethod
from src.data.data_models import Trajectory
from src.weather.weather_api import WeatherAPI

# ==================== CONFIGURATION DE LA PAGE ====================
st.set_page_config(
    page_title="Optimisation de Trajectoires Aériennes",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/votre-repo',
        'Report a bug': 'https://github.com/votre-repo/issues',
        'About': '# Optimisation de trajectoires\nProjet ENAC 2A - 2026'
    }
)

# ==================== CSS PERSONNALISÉ ====================
st.markdown("""
<style>
    /* En-tête principal */
    .main-header {
        background: linear-gradient(120deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0;
    }
    
    /* Cartes d'information */
    .info-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1e3c72;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .info-card h3 {
        color: #1e3c72;
        margin-top: 0;
        font-size: 1.3rem;
    }
    
    .info-card p {
        color: #555;
        line-height: 1.6;
    }
    
    /* Métriques */
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1e3c72;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .badge-success {
        background: #d4edda;
        color: #155724;
    }
    
    .badge-info {
        background: #d1ecf1;
        color: #0c5460;
    }
    
    .badge-warning {
        background: #fff3cd;
        color: #856404;
    }
    
    .badge-recommended {
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: #000;
        font-weight: 700;
    }
    
    /* Instructions */
    .instruction-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .instruction-box h4 {
        margin-top: 0;
        font-size: 1.2rem;
    }
    
    .instruction-box ol {
        margin-bottom: 0;
        padding-left: 1.5rem;
    }
    
    .instruction-box li {
        margin: 0.5rem 0;
        line-height: 1.6;
    }
    
    /* Sidebar */
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Dividers */
    .divider {
        height: 2px;
        background: linear-gradient(to right, transparent, #1e3c72, transparent);
        margin: 2rem 0;
    }
    
    /* Animation de succès */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .success-message {
        animation: slideIn 0.3s ease-out;
    }
    
    /* Tableaux améliorés */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Boutons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ==================== FONCTIONS UTILITAIRES ====================

def load_trajectory(uploaded_file):
    """Charge une trajectoire depuis un fichier KML"""
    if uploaded_file is not None:
        temp_path = Path("temp_upload.kml")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        parser = KMLParser(str(temp_path))
        traj = parser.parse()
        temp_path.unlink()
        
        return traj
    return None


def create_3d_plot(original, optimized):
    """Crée un graphique 3D interactif amélioré"""
    fig = go.Figure()
    
    orig_coords = original.get_coordinates_array()
    orig_ts = original.get_timestamps()
    
    # Trajectoire originale - AMÉLIORÉ: plus visible
    fig.add_trace(go.Scatter3d(
        x=orig_coords[:, 1],
        y=orig_coords[:, 0],
        z=orig_coords[:, 2],
        mode='lines',
        name=f'Original ({len(original)} pts)',
        line=dict(color='rgba(30, 144, 255, 0.9)', width=4),  # ← Opacité 0.6→0.9, width 2→4
        hovertemplate='<b>Original</b><br>Lat: %{y:.6f}°<br>Lon: %{x:.6f}°<br>Alt: %{z:.0f} m<extra></extra>'
    ))
    
    # Trajectoire optimisée
    opt_coords = optimized.get_coordinates_array()
    
    fig.add_trace(go.Scatter3d(
        x=opt_coords[:, 1],
        y=opt_coords[:, 0],
        z=opt_coords[:, 2],
        mode='lines+markers',
        name=f'Optimisé ({len(optimized)} pts)',
        line=dict(color='rgba(255, 69, 0, 0.9)', width=4),
        marker=dict(size=4, color='orangered'),
        hovertemplate='<b>Optimisé</b><br>Lat: %{y:.6f}°<br>Lon: %{x:.6f}°<br>Alt: %{z:.0f} m<extra></extra>'
    ))
    
    # Points de départ et arrivée
    fig.add_trace(go.Scatter3d(
        x=[orig_coords[0, 1], orig_coords[-1, 1]],
        y=[orig_coords[0, 0], orig_coords[-1, 0]],
        z=[orig_coords[0, 2], orig_coords[-1, 2]],
        mode='markers+text',
        name='Départ/Arrivée',
        marker=dict(size=10, color=['green', 'red']),
        text=['🛫', '🛬'],
        textfont=dict(size=20),
        hovertemplate='<b>%{text}</b><extra></extra>'
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis_title='Longitude (°)',
            yaxis_title='Latitude (°)',
            zaxis_title='Altitude (m)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
            bgcolor='rgba(240, 248, 255, 0.3)'
        ),
        height=600,
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255, 255, 255, 0.9)'),
        margin=dict(l=0, r=0, t=30, b=0),
        title=dict(text="Vue 3D de la Trajectoire", x=0.5, xanchor='center')
    )
    
    return fig


def create_comparison_plots(original, optimized, start_time_seconds=None):
    """Crée une grille de graphiques de comparaison"""
    orig_coords = original.get_coordinates_array()
    orig_ts = original.get_timestamps() / 60  # Minutes
    
    opt_coords = optimized.get_coordinates_array()
    opt_ts = optimized.get_timestamps() / 60
    
    # Créer subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Profil d\'Altitude', 'Vitesse Horizontale', 
                       'Taux de Montée', 'Courbure de la Trajectoire'),
        specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
               [{'type': 'scatter'}, {'type': 'scatter'}]],
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )
    
    # 1. Profil d'altitude
    fig.add_trace(
        go.Scatter(x=orig_ts, y=orig_coords[:, 2], 
                  name='Original', line=dict(color='dodgerblue', width=2),
                  legendgroup='original'),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=opt_ts, y=opt_coords[:, 2],
                  name='Optimisé', line=dict(color='orangered', width=3),
                  legendgroup='optimized'),
        row=1, col=1
    )
    
    # Zone préservée si applicable
    if start_time_seconds is not None and start_time_seconds > 0:
        start_time_min = start_time_seconds / 60
        fig.add_vrect(
            x0=0, x1=start_time_min,
            fillcolor='rgba(144, 238, 144, 0.2)',
            layer='below', line_width=0,
            row=1, col=1
        )
    
    # 2. Vitesse horizontale
    orig_coords_cart = original.get_cartesian_array()
    opt_coords_cart = optimized.get_cartesian_array()
    
    orig_speed = np.sqrt(np.sum(np.diff(orig_coords_cart[:, :2], axis=0)**2, axis=1)) / np.diff(orig_ts * 60)
    opt_speed = np.sqrt(np.sum(np.diff(opt_coords_cart[:, :2], axis=0)**2, axis=1)) / np.diff(opt_ts * 60)
    
    fig.add_trace(
        go.Scatter(x=orig_ts[1:], y=orig_speed, 
                  name='Original', line=dict(color='dodgerblue', width=2),
                  showlegend=False, legendgroup='original'),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=opt_ts[1:], y=opt_speed,
                  name='Optimisé', line=dict(color='orangered', width=3),
                  showlegend=False, legendgroup='optimized'),
        row=1, col=2
    )
    
    # 3. Taux de montée
    orig_climb = np.gradient(orig_coords[:, 2], orig_ts * 60)
    opt_climb = np.gradient(opt_coords[:, 2], opt_ts * 60)
    
    fig.add_trace(
        go.Scatter(x=orig_ts, y=orig_climb, 
                  name='Original', line=dict(color='dodgerblue', width=2),
                  showlegend=False, legendgroup='original'),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=opt_ts, y=opt_climb,
                  name='Optimisé', line=dict(color='orangered', width=3),
                  showlegend=False, legendgroup='optimized'),
        row=2, col=1
    )
    
    # Ligne zéro
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    # 4. Courbure (approximation)
    def compute_curvature(coords, ts):
        dx = np.gradient(coords[:, 0])
        dy = np.gradient(coords[:, 1])
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)
        curvature = np.abs(dx * ddy - dy * ddx) / (dx**2 + dy**2)**1.5
        return np.clip(curvature, 0, 1e-3)  # Limiter pour la visualisation
    
    orig_curv = compute_curvature(orig_coords_cart, orig_ts)
    opt_curv = compute_curvature(opt_coords_cart, opt_ts)
    
    fig.add_trace(
        go.Scatter(x=orig_ts, y=orig_curv, 
                  name='Original', line=dict(color='dodgerblue', width=2),
                  showlegend=False, legendgroup='original'),
        row=2, col=2
    )
    fig.add_trace(
        go.Scatter(x=opt_ts, y=opt_curv,
                  name='Optimisé', line=dict(color='orangered', width=3),
                  showlegend=False, legendgroup='optimized'),
        row=2, col=2
    )
    
    # Mise à jour des axes
    fig.update_xaxes(title_text="Temps (min)", row=1, col=1)
    fig.update_xaxes(title_text="Temps (min)", row=1, col=2)
    fig.update_xaxes(title_text="Temps (min)", row=2, col=1)
    fig.update_xaxes(title_text="Temps (min)", row=2, col=2)
    
    fig.update_yaxes(title_text="Altitude (m)", row=1, col=1)
    fig.update_yaxes(title_text="Vitesse (m/s)", row=1, col=2)
    fig.update_yaxes(title_text="Taux montée (m/s)", row=2, col=1)
    fig.update_yaxes(title_text="Courbure", row=2, col=2)
    
    fig.update_layout(
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        title_text="Analyse Comparative Complète",
        title_x=0.5,
        title_xanchor='center'
    )
    
    return fig


def create_map_view(original, optimized):
    """Crée une vue carte 2D améliorée"""
    orig_coords = original.get_coordinates_array()
    center_lat = np.mean(orig_coords[:, 0])
    center_lon = np.mean(orig_coords[:, 1])
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Trajectoire originale - AMÉLIORÉ: plus visible
    folium.PolyLine(
        locations=[(lat, lon) for lat, lon in orig_coords[:, :2]],
        color='#1E90FF',
        weight=4,  # ← weight 3→4
        opacity=0.9,  # ← opacity 0.7→0.9
        popup=f'<b>Trajectoire Originale</b><br>{len(original)} points'
    ).add_to(m)
    
    # Trajectoire optimisée
    opt_coords = optimized.get_coordinates_array()
    folium.PolyLine(
        locations=[(lat, lon) for lat, lon in opt_coords[:, :2]],
        color='#FF4500',
        weight=5,
        opacity=0.9,
        popup=f'<b>Trajectoire Optimisée</b><br>{len(optimized)} points'
    ).add_to(m)
    
    # Marqueurs
    folium.Marker(
        location=[orig_coords[0, 0], orig_coords[0, 1]],
        popup=f'<b>🛫 DÉPART</b><br>Alt: {orig_coords[0, 2]:.0f}m',
        icon=folium.Icon(color='green', icon='plane', prefix='fa'),
        tooltip='Départ'
    ).add_to(m)
    
    folium.Marker(
        location=[orig_coords[-1, 0], orig_coords[-1, 1]],
        popup=f'<b>🛬 ARRIVÉE</b><br>Alt: {orig_coords[-1, 2]:.0f}m',
        icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa'),
        tooltip='Arrivée'
    ).add_to(m)
    
    # Ajuster les limites
    all_coords = np.vstack([orig_coords[:, :2], opt_coords[:, :2]])
    m.fit_bounds([[all_coords[:, 0].min(), all_coords[:, 1].min()],
                  [all_coords[:, 0].max(), all_coords[:, 1].max()]])
    
    return m


def add_wind_arrows_to_map(folium_map, trajectory, use_weather=False, num_arrows=10):
    """
    Ajoute des flèches indiquant la direction et la vitesse du vent sur la carte
    
    Args:
        folium_map: Carte Folium
        trajectory: Trajectoire de référence
        use_weather: Si True, utilise les données météo (sinon mode mock)
        num_arrows: Nombre de flèches à afficher le long de la trajectoire
    """
    if not use_weather:
        # Mode mock : utiliser l'API météo en mode mock
        weather_api = WeatherAPI(source='mock')
    else:
        # Mode réel (nécessite clé API)
        weather_api = WeatherAPI(source='openweather')
    
    # Échantillonner des points le long de la trajectoire
    positions = trajectory.positions
    if len(positions) < num_arrows:
        indices = range(len(positions))
    else:
        # Prendre des points régulièrement espacés
        indices = np.linspace(0, len(positions) - 1, num_arrows, dtype=int)
    
    # Créer un groupe de couches pour les flèches de vent
    wind_layer = folium.FeatureGroup(name='🌬️ Vent', show=True)
    
    for idx in indices:
        pos = positions[idx]
        
        # Obtenir les conditions météo à ce point
        weather = weather_api.get_weather(pos.latitude, pos.longitude, pos.altitude)
        
        # Direction du vent (degrés) - Convention météo : d'où vient le vent
        wind_dir = weather.wind_direction
        wind_speed = weather.wind_speed
        
        # Couleur selon la vitesse du vent
        if wind_speed < 5:
            color = '#90EE90'  # Vert clair (faible)
        elif wind_speed < 15:
            color = '#FFD700'  # Jaune (modéré)
        elif wind_speed < 25:
            color = '#FFA500'  # Orange (fort)
        else:
            color = '#FF4500'  # Rouge orangé (très fort)
        
        # Taille de la flèche proportionnelle à la vitesse
        arrow_size = min(8 + wind_speed * 0.3, 20)  # Entre 8 et 20
        
        # Utiliser un DivIcon avec une flèche SVG personnalisée
        # La flèche pointe dans la direction VERS où va le vent (opposé de la convention météo)
        arrow_rotation = (wind_dir + 180) % 360  # Inverser la direction
        
        arrow_html = f"""
        <div style="transform: rotate({arrow_rotation}deg); 
                    transform-origin: center center;
                    width: {arrow_size}px; 
                    height: {arrow_size}px;">
            <svg width="{arrow_size}" height="{arrow_size}" viewBox="0 0 24 24">
                <path d="M12 2 L12 18 M12 2 L8 6 M12 2 L16 6" 
                      stroke="{color}" 
                      stroke-width="3" 
                      fill="none" 
                      stroke-linecap="round"/>
                <circle cx="12" cy="20" r="2" fill="{color}"/>
            </svg>
        </div>
        """
        
        # Popup avec informations détaillées
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>🌬️ Vent</b><br>
            <b>Vitesse:</b> {wind_speed:.1f} m/s ({wind_speed * 3.6:.1f} km/h)<br>
            <b>Direction:</b> {wind_dir:.0f}° ({_get_cardinal_direction(wind_dir)})<br>
            <b>Altitude:</b> {pos.altitude:.0f} m
        </div>
        """
        
        folium.Marker(
            location=[pos.latitude, pos.longitude],
            icon=folium.DivIcon(html=arrow_html),
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"💨 {wind_speed:.1f} m/s, {_get_cardinal_direction(wind_dir)}"
        ).add_to(wind_layer)
    
    wind_layer.add_to(folium_map)
    
    # Ajouter contrôle des couches pour activer/désactiver les flèches
    folium.LayerControl(position='topright').add_to(folium_map)
    
    return folium_map


def _get_cardinal_direction(degrees):
    """Convertit des degrés en direction cardinale (N, NE, E, etc.)"""
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def get_method_info(method_name):
    """Retourne les informations détaillées sur une méthode"""
    methods_info = {
        "Kalman": {
            "icon": "🎯",
            "description": "Lissage probabiliste par filtre de Kalman avec RTS smoother",
            "pros": ["Élimine le bruit ADS-B", "Estimation de vitesse/accélération", "Très rapide (0.04s)"],
            "cons": ["Ne réduit pas le nombre de points", "Pas de compression"],
            "use_case": "Nettoyage de données bruitées",
            "badge": "badge-info"
        },
        "B-spline": {
            "icon": "📐",
            "description": "Interpolation par courbes B-splines cubiques",
            "pros": ["Compression 60%", "Ultra-rapide (0.002s)", "Contrôle de courbure"],
            "cons": ["Peut créer des oscillations", "Pas de filtrage du bruit"],
            "use_case": "Compression rapide de trajectoires propres",
            "badge": "badge-success"
        },
        "Hybride": {
            "icon": "⭐",
            "description": "Combine Kalman (lissage) + B-spline (compression)",
            "pros": ["Meilleur compromis qualité/performance", "Compression + lissage", "Rapide (0.05s)"],
            "cons": ["Paramètres à ajuster selon contexte"],
            "use_case": "Usage général recommandé",
            "badge": "badge-primary"
        },
        "Météo": {
            "icon": "🌦️",
            "description": "Optimisation avancée avec prise en compte du vent et conditions météo",
            "pros": ["Économie de carburant réelle", "Trajectoires réalistes tenant compte du vent", "Simulation météo intégrée"],
            "cons": ["Plus lent (2-5s)", "Nécessite données météo", "Peut augmenter distance si vent favorable"],
            "use_case": "Optimisation opérationnelle avec météo",
            "badge": "badge-warning"
        },
        "Collocation Directe": {
            "icon": "🚀",
            "description": "Optimisation NLP (Non-Linear Programming) avec contraintes réalistes : altitude, taux de montée, accélérations, forces G, consommation de carburant",
            "pros": ["Modèle physique complet", "Contraintes opérationnelles respectées", "Optimisation multi-objectifs (distance + confort + sécurité)"],
            "cons": ["Plus lent (5-15s)", "Convergence parfois partielle", "Nécessite bon réglage de paramètres"],
            "use_case": "Planification de vol optimale avec respect des contraintes",
            "badge": "badge-danger"
        }
    }
    return methods_info.get(method_name, {})


# ==================== EN-TÊTE ====================
st.markdown("""
<div class="main-header">
    <h1>✈️ Optimisation de Trajectoires Aériennes</h1>
    <p>Système avancé d'optimisation de trajectoires de vol basé sur les données ADS-B</p>
    <p style="font-size: 0.9rem; margin-top: 0.5rem;">
        <span class="badge badge-success">5 Méthodes</span>
        <span class="badge badge-info">Temps Réel</span>
        <span class="badge badge-warning">Données Météo</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ==================== GUIDE D'UTILISATION ====================
with st.expander("📖 Guide d'Utilisation Rapide", expanded=False):
    st.markdown("""
    <div class="instruction-box">
        <h4>🚀 Comment utiliser ce dashboard :</h4>
        <ol>
            <li><strong>Charger les données</strong> : Uploadez un fichier KML ou utilisez l'exemple par défaut</li>
            <li><strong>Choisir la méthode</strong> : Sélectionnez une méthode d'optimisation (Hybride recommandé ⭐)</li>
            <li><strong>Configurer</strong> : Ajustez le nombre de points cible et le point de départ</li>
            <li><strong>Optimiser</strong> : Cliquez sur le bouton "🚀 Optimiser"</li>
            <li><strong>Analyser</strong> : Consultez les métriques et visualisations générées</li>
        </ol>
    </div>
    
    **💡 Astuces :**
    - Pour conserver le décollage intact : utilisez "Temps écoulé" (10 min)
    - Pour maximum de compression : choisissez "NLP Direct Collocation"
    - Pour vitesse maximale : choisissez "B-spline"
    """)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Upload de fichier
    st.markdown("### 📂 Chargement des Données")
    uploaded_file = st.file_uploader(
        "Charger un fichier KML",
        type=['kml'],
        help="Fichier de trajectoire ADS-B au format KML (OpenSky Network, FlightRadar24, etc.)"
    )
    
    if uploaded_file:
        st.success("✅ Fichier chargé avec succès")
    else:
        st.info("💡 Utilisation de l'exemple par défaut")
    
    st.markdown("---")
    
    # Choix de la méthode
    st.markdown("### 🎯 Méthode d'Optimisation")
    method_name = st.selectbox(
        "Sélectionnez une méthode",
        ["Hybride", "Kalman", "B-spline", "Météo", "NLP Direct Collocation"],
        help="La méthode Hybride est recommandée pour un usage général"
    )
    
    # Afficher les infos de la méthode
    method_info = get_method_info(method_name)
    if method_info:
        st.markdown(f"""
        <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-top: 0.5rem;'>
            <div><span style='font-size: 1.5rem;'>{method_info['icon']}</span> 
            <span class='badge {method_info["badge"]}'>{method_name}</span></div>
            <p style='font-size: 0.85rem; margin: 0.5rem 0;'>{method_info['description']}</p>
            <p style='font-size: 0.75rem; margin: 0; color: #666;'>
                <strong>Utilisation:</strong> {method_info['use_case']}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    method_mapping = {
        "Kalman": OptimizationMethod.KALMAN,
        "B-spline": OptimizationMethod.BSPLINE,
        "Hybride": OptimizationMethod.HYBRID,
        "Météo": OptimizationMethod.WEATHER,
        "NLP Direct Collocation": OptimizationMethod.DIRECT_COLLOCATION
    }
    
    st.markdown("---")
    
    # Paramètres d'optimisation
    st.markdown("### 🎛️ Paramètres")
    
    target_points = st.slider(
        "Nombre de points cible",
        min_value=50,
        max_value=500,
        value=200,
        step=10,
        help="Nombre de points dans la trajectoire optimisée (moins = plus de compression)"
    )
    
    use_weather = st.checkbox(
        "🌤️ Utiliser données météo",
        value=False,
        help="Active la prise en compte des conditions météorologiques (vent, température)"
    )
    
    st.markdown("---")
    
    # Point de départ
    st.markdown("### 🎯 Point de Départ de l'Optimisation")
    st.caption("Permet de préserver une partie initiale de la trajectoire")
    
    start_option = st.radio(
        "Commencer l'optimisation à partir de :",
        ["Début de la trajectoire", "Temps écoulé", "Distance parcourue"],
        help="Conserve la partie initiale intacte (utile pour préserver le décollage)"
    )
    
    start_time_value = None
    start_distance_value = None
    
    if start_option == "Temps écoulé":
        start_time_minutes = st.slider(
            "⏱️ Temps écoulé (minutes)",
            min_value=0,
            max_value=60,
            value=10,
            step=1
        )
        start_time_value = start_time_minutes * 60
        st.info(f"Optimisation après {start_time_minutes} min")
    
    elif start_option == "Distance parcourue":
        start_distance_km = st.slider(
            "📏 Distance parcourue (km)",
            min_value=0,
            max_value=200,
            value=50,
            step=5
        )
        start_distance_value = start_distance_km * 1000
        st.info(f"Optimisation après {start_distance_km} km")
    
    st.markdown("---")
    
    # Bouton d'optimisation
    optimize_button = st.button("🚀 LANCER L'OPTIMISATION", type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # Aide sur les méthodes
    with st.expander("📚 Détails des Méthodes"):
        for method, info in {k: get_method_info(k) for k in ["Kalman", "B-spline", "Hybride", "Météo", "Collocation Directe"]}.items():
            if info:  # Vérifier que le dictionnaire n'est pas vide
                st.markdown(f"**{info['icon']} {method}**")
                st.caption(info['description'])
                st.markdown("")

# ==================== CHARGEMENT DES DONNÉES ====================
# Initialiser session_state
if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None
if 'optimized_trajectory' not in st.session_state:
    st.session_state.optimized_trajectory = None
if 'optimization_time' not in st.session_state:
    st.session_state.optimization_time = 0

# Charger la trajectoire
if uploaded_file is None:
    example_file = Path(__file__).parent.parent / "data" / "sample" / "F-HZUE-track-EGM96.kml"
    try:
        parser = KMLParser(str(example_file))
        trajectory = parser.parse()
    except:
        st.error("❌ Erreur lors du chargement du fichier d'exemple")
        st.stop()
else:
    trajectory = load_trajectory(uploaded_file)
    if trajectory is None:
        st.error("❌ Erreur lors du chargement du fichier KML")
        st.stop()

# ==================== INFORMATIONS DE VOL ====================
if trajectory:
    st.markdown("## 📋 Informations de Vol")
    
    # Calculer les statistiques
    orig_coords = trajectory.get_coordinates_array()
    coords_cart = trajectory.get_cartesian_array()
    total_dist = np.sum(np.linalg.norm(np.diff(coords_cart, axis=0), axis=1)) / 1000
    duration_min = trajectory.duration / 60
    avg_speed = total_dist / (trajectory.duration / 3600) if trajectory.duration > 0 else 0
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("""
        <div class="metric-container">
            <div class="metric-value">{}</div>
            <div class="metric-label">✈️ Points</div>
        </div>
        """.format(len(trajectory)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-container">
            <div class="metric-value">{:.1f}</div>
            <div class="metric-label">⏱️ Minutes</div>
        </div>
        """.format(duration_min), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-container">
            <div class="metric-value">{:.1f}</div>
            <div class="metric-label">📏 Kilomètres</div>
        </div>
        """.format(total_dist), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-container">
            <div class="metric-value">{:.0f}</div>
            <div class="metric-label">🗻 Alt. Max (m)</div>
        </div>
        """.format(orig_coords[:, 2].max()), unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="metric-container">
            <div class="metric-value">{:.0f}</div>
            <div class="metric-label">🚀 Vitesse Moy. (km/h)</div>
        </div>
        """.format(avg_speed), unsafe_allow_html=True)
    
    # Détails supplémentaires
    with st.expander("ℹ️ Détails Complets de la Trajectoire"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🛫 Point de Départ")
            st.write(f"**Latitude:** {orig_coords[0, 0]:.6f}°")
            st.write(f"**Longitude:** {orig_coords[0, 1]:.6f}°")
            st.write(f"**Altitude:** {orig_coords[0, 2]:.0f} m")
            if trajectory.positions[0].timestamp:
                st.write(f"**Heure:** {trajectory.positions[0].timestamp.strftime('%H:%M:%S')}")
        
        with col2:
            st.markdown("### 🛬 Point d'Arrivée")
            st.write(f"**Latitude:** {orig_coords[-1, 0]:.6f}°")
            st.write(f"**Longitude:** {orig_coords[-1, 1]:.6f}°")
            st.write(f"**Altitude:** {orig_coords[-1, 2]:.0f} m")
            if trajectory.positions[-1].timestamp:
                st.write(f"**Heure:** {trajectory.positions[-1].timestamp.strftime('%H:%M:%S')}")
        
        with col3:
            st.markdown("### 📊 Statistiques")
            st.write(f"**Alt. Min:** {orig_coords[:, 2].min():.0f} m")
            st.write(f"**Alt. Moy:** {orig_coords[:, 2].mean():.0f} m")
            timestamps = trajectory.get_timestamps()
            avg_interval = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else 0
            st.write(f"**Intervalle moy:** {avg_interval:.1f} s")
            st.write(f"**ID Vol:** {trajectory.flight_id or 'N/A'}")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ==================== OPTIMISATION ====================
if optimize_button and trajectory:
    with st.spinner(f'⏳ Optimisation en cours avec la méthode {method_name}...'):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Initialisation de l'optimiseur...")
        progress_bar.progress(20)
        time.sleep(0.1)
        
        start_opt_time = time.time()
        
        # Optimiser
        optimizer = TrajectoryOptimizer(method=method_mapping[method_name])
        
        status_text.text(f"Application de la méthode {method_name}...")
        progress_bar.progress(50)
        
        result = optimizer.optimize(
            trajectory,
            use_weather=use_weather,
            target_points=target_points,
            start_time=start_time_value,
            start_distance=start_distance_value
        )
        
        progress_bar.progress(80)
        status_text.text("Calcul des métriques...")
        
        elapsed = time.time() - start_opt_time
        
        # Stocker dans session_state
        st.session_state.optimization_result = result
        st.session_state.optimized_trajectory = result.get_optimized_trajectory()
        st.session_state.optimization_time = elapsed
        st.session_state.start_option = start_option
        st.session_state.start_value = start_time_value or start_distance_value
        
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()
        
        # Message de succès
        if start_time_value:
            st.success(f"✅ Optimisation terminée en {elapsed:.2f}s • Départ: {start_time_value/60:.1f} min", icon="✅")
        elif start_distance_value:
            st.success(f"✅ Optimisation terminée en {elapsed:.2f}s • Départ: {start_distance_value/1000:.1f} km", icon="✅")
        else:
            st.success(f"✅ Optimisation terminée en {elapsed:.2f}s", icon="✅")
        
        st.balloons()

# ==================== RÉSULTATS ====================
if st.session_state.optimization_result is not None and trajectory:
    result = st.session_state.optimization_result
    optimized_traj = st.session_state.optimized_trajectory
    elapsed = st.session_state.optimization_time
    
    st.markdown("## 📊 Résultats de l'Optimisation")
    
    # Métriques principales avec design amélioré
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        compression_pct = (1 - result.metrics['compression_ratio']) * 100
        num_points = len(optimized_traj.positions) if optimized_traj else 0
        st.metric(
            "📉 Compression",
            f"{num_points} pts",
            f"-{compression_pct:.1f}%",
            delta_color="normal"
        )
    
    with col2:
        smoothness_improvement = ((result.metrics['original_smoothness'] - result.metrics['smoothness']) / 
                                 result.metrics['original_smoothness'] * 100)
        st.metric(
            "✨ Smoothness",
            f"{result.metrics['smoothness']:.0f}",
            f"-{smoothness_improvement:.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        fuel_saving = result.metrics.get('fuel_saving_kg', 0)
        fuel_saving_pct = result.metrics.get('fuel_saving_percent', 0)
        
        # Affichage correct : positif = économie, négatif = surconsommation
        if fuel_saving >= 0:
            st.metric(
                "⛽ Économie Carburant",
                f"{fuel_saving:.1f} kg",
                f"{fuel_saving_pct:.2f}%",
                delta_color="normal"
            )
        else:
            st.metric(
                "⛽ Surconsommation",
                f"{abs(fuel_saving):.1f} kg",
                f"{fuel_saving_pct:.2f}%",
                delta_color="inverse",
                help="La trajectoire optimisée consomme plus de carburant (distance ou manœuvres supplémentaires)"
            )
    
    with col4:
        st.metric(
            "⚡ G-force Max",
            f"{result.metrics.get('max_g_force', 0):.2f} G",
            help="Facteur de charge maximal ressenti"
        )
    
    with col5:
        st.metric(
            "⏱️ Temps Calcul",
            f"{elapsed:.2f}s",
            help="Temps d'exécution de l'algorithme"
        )
    
    # Tableau de métriques détaillées
    with st.expander("📈 Métriques Détaillées Complètes", expanded=True):
        # Préparer les valeurs de carburant avec labels corrects
        fuel_saving = result.metrics.get('fuel_saving_kg', 0)
        fuel_saving_pct = result.metrics.get('fuel_saving_percent', 0)
        
        if fuel_saving >= 0:
            fuel_label = "Économie"
            fuel_value_str = f"{fuel_saving:.1f} kg ({fuel_saving_pct:.2f}%)"
            fuel_emoji = "💰"
        else:
            fuel_label = "Surconsommation"
            fuel_value_str = f"{abs(fuel_saving):.1f} kg ({abs(fuel_saving_pct):.2f}%)"
            fuel_emoji = "⚠️"
        
        metrics_df = pd.DataFrame({
            'Catégorie': ['Distance', 'Distance', 'Distance', 
                         'Carburant', 'Carburant', 'Carburant',
                         'Dynamique', 'Dynamique', 'Dynamique'],
            'Métrique': ['Originale', 'Optimisée', 'Variation',
                        'Consommation orig.', 'Consommation opt.', fuel_label,
                        'G-force moyen', 'Courbure max', 'Courbure moyenne'],
            'Valeur': [
                f"{result.metrics['distance_original']/1000:.2f} km",
                f"{result.metrics['distance_optimized']/1000:.2f} km",
                f"{result.metrics['distance_change_percent']:.2f}%",
                f"{result.metrics.get('fuel_consumption_original_kg', 0):.1f} kg",
                f"{result.metrics.get('fuel_consumption_kg', 0):.1f} kg",
                fuel_value_str,
                f"{result.metrics.get('avg_g_force', 0):.3f} G",
                f"{result.metrics.get('curvature_max', 0):.2e}",
                f"{result.metrics.get('curvature_avg', 0):.2e}"
            ],
            'Indicateur': ['📏', '📏', '📊',
                          '⛽', '⛽', fuel_emoji,
                          '⚡', '📐', '📐']
        })
        
        st.dataframe(
            metrics_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Indicateur": st.column_config.TextColumn(width="small"),
                "Catégorie": st.column_config.TextColumn(width="medium"),
                "Métrique": st.column_config.TextColumn(width="large"),
                "Valeur": st.column_config.TextColumn(width="large")
            }
        )
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Visualisations
    st.markdown("## 🗺️ Visualisations Interactives")
    
    tab1, tab2, tab3 = st.tabs(["🗺️ Carte 2D", "🌐 Vue 3D", "📊 Analyse Comparative"])
    
    with tab1:
        st.markdown("### Trajectoires sur Carte OpenStreetMap")
        st.caption("🔵 Bleue = Trajectoire originale • 🔴 Rouge = Trajectoire optimisée")
        
        # Créer la carte avec les trajectoires
        map_view = create_map_view(trajectory, optimized_traj)
        
        # Ajouter les flèches de vent (toujours en mode mock, activer avec use_weather si nécessaire)
        map_view = add_wind_arrows_to_map(
            map_view, 
            trajectory, 
            use_weather=use_weather,  # Utilise la même option que l'optimisation
            num_arrows=12  # 12 flèches le long de la trajectoire
        )
        
        st_folium(map_view, width=1400, height=600)
        st.caption("💨 Les flèches indiquent la direction et l'intensité du vent (cliquez pour détails)")
    
    with tab2:
        st.markdown("### Visualisation 3D Interactive")
        st.caption("Utilisez la souris pour faire pivoter, zoomer et explorer la trajectoire en 3D")
        fig_3d = create_3d_plot(trajectory, optimized_traj)
        st.plotly_chart(fig_3d, use_container_width=True)
    
    with tab3:
        st.markdown("### Analyse Comparative Multi-Paramètres")
        start_time_marker = None
        if hasattr(st.session_state, 'start_option') and st.session_state.start_option == "Temps écoulé":
            start_time_marker = st.session_state.start_value
        
        fig_comp = create_comparison_plots(trajectory, optimized_traj, start_time_marker)
        st.plotly_chart(fig_comp, use_container_width=True)
        
        if hasattr(st.session_state, 'start_option') and st.session_state.start_option != "Début de la trajectoire":
            start_val = st.session_state.start_value if hasattr(st.session_state, 'start_value') and st.session_state.start_value else 0
            if st.session_state.start_option == "Temps écoulé":
                st.info(f"🎯 Zone colorée = partie préservée (0 - {start_val/60:.1f} min)")
            elif st.session_state.start_option == "Distance parcourue":
                st.info(f"🎯 Les premiers {start_val/1000:.1f} km sont préservés")
    
    # Export des résultats
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("## 💾 Export des Résultats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export CSV des métriques
        export_df = pd.DataFrame({
            'Métrique': list(result.metrics.keys()),
            'Valeur': list(result.metrics.values())
        })
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger les Métriques (CSV)",
            data=csv,
            file_name=f"metrics_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Export des coordonnées optimisées
        if optimized_traj:
            opt_coords_df = pd.DataFrame(
                optimized_traj.get_coordinates_array(),
                columns=['Latitude', 'Longitude', 'Altitude']
            )
            csv_coords = opt_coords_df.to_csv(index=False)
            st.download_button(
                label="📥 Télécharger Coordonnées Optimisées (CSV)",
                data=csv_coords,
                file_name=f"trajectory_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# Message si aucune optimisation
elif trajectory and st.session_state.optimization_result is None:
    st.markdown("""
    <div class="info-card">
        <h3>👉 Prêt à commencer ?</h3>
        <p>Configurez les paramètres dans la barre latérale, puis cliquez sur 
        <strong style="color: #1e3c72;">"🚀 LANCER L'OPTIMISATION"</strong> 
        pour analyser votre trajectoire.</p>
        <p style="margin-bottom: 0;">📋 La trajectoire est chargée et prête à être optimisée !</p>
    </div>
    """, unsafe_allow_html=True)

elif not trajectory:
    st.error("❌ Impossible de charger la trajectoire. Veuillez vérifier le fichier KML.")

# ==================== FOOTER ====================
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px;'>
    <h3 style='color: #1e3c72; margin-top: 0;'>✈️ Optimisation de Trajectoires Aériennes</h3>
    <p style='color: #666; margin: 0.5rem 0;'>
        <strong>Projet ENAC 2A • 2026</strong>
    </p>
    <p style='color: #888; font-size: 0.9rem; margin: 0.5rem 0;'>
        Développé avec Python • NumPy • SciPy • Streamlit • Plotly • Folium
    </p>
    <p style='color: #888; font-size: 0.85rem; margin-top: 1rem;'>
        <span class="badge badge-success">5 Méthodes d'Optimisation</span>
        <span class="badge badge-info">Visualisation 3D</span>
        <span class="badge badge-warning">Données Météo</span>
    </p>
</div>
""", unsafe_allow_html=True)
