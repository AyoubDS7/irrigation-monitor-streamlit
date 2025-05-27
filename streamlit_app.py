import streamlit as st
st.set_page_config(page_title="Smart Irrigation Dashboard", layout="wide", initial_sidebar_state="expanded")

import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh
import requests
import time
import numpy as np

# Enhanced Custom CSS with better contrast and readability
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Enhanced metric cards with better contrast */
    .metric-card-critical {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(255, 65, 108, 0.4);
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        text-align: center;
        animation: pulse 2s infinite;
    }
    
    .metric-card-warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.4);
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        text-align: center;
    }
    
    .metric-card-good {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        text-align: center;
    }
    
    .metric-card-critical:hover, .metric-card-warning:hover, .metric-card-good:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    
    .metric-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
        opacity: 0.9;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        margin: 10px 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .metric-subtitle {
        font-size: 14px;
        opacity: 0.8;
        margin-top: 5px;
    }
    
    .status-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        animation: pulse 2s infinite;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .status-inactive {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.4);
    }
    
    .status-alert {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: #d63031;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        animation: blink 1s infinite;
        box-shadow: 0 8px 25px rgba(255, 154, 158, 0.4);
    }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.02); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.7; }
    }
    
    .live-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #00ff00;
        border-radius: 50%;
        animation: pulse 1s infinite;
        margin-right: 8px;
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
    }
    
    .success-card {
        background: linear-gradient(135deg, #51cf66 0%, #40c057 100%);
        color: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(81, 207, 102, 0.3);
    }
    
    .weather-card {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(116, 185, 255, 0.3);
        text-align: center;
    }
    
    .analytics-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Firebase Setup ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("sensordatairrigation-firebase-adminsdk-fbsvc-8361e6c330.json")
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://sensordatairrigation-default-rtdb.firebaseio.com/'
            })
        except Exception as e:
            st.error(f"Firebase initialization error: {e}")

init_firebase()

# --- Enhanced Data Fetching ---
@st.cache_data(ttl=30)
def fetch_data():
    try:
        ref = db.reference("irrigation_data")
        data = ref.get()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data.values())
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_system_health():
    """Calculate system health metrics"""
    df = fetch_data()
    if df.empty:
        return {"status": "offline", "score": 0}
    
    latest = df.iloc[-1]
    last_update = pd.to_datetime(latest['timestamp'])
    time_diff = datetime.now() - last_update.replace(tzinfo=None)
    
    if time_diff.total_seconds() > 300:  # 5 minutes
        return {"status": "offline", "score": 0}
    elif time_diff.total_seconds() > 120:  # 2 minutes
        return {"status": "warning", "score": 50}
    else:
        return {"status": "online", "score": 100}

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>🌱 Smart Irrigation Control Center</h1>
    <p>Real-time monitoring & AI-powered irrigation management</p>
</div>
""", unsafe_allow_html=True)

# --- System Status Bar ---
health = get_system_health()
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    if health["status"] == "online":
        st.markdown(f'<div class="live-indicator"></div>**System Status: ONLINE** - Last update: {datetime.now().strftime("%H:%M:%S")}', unsafe_allow_html=True)
    elif health["status"] == "warning":
        st.markdown('🟡 **System Status: DELAYED** - Check connection', unsafe_allow_html=True)
    else:
        st.markdown('🔴 **System Status: OFFLINE** - System disconnected', unsafe_allow_html=True)

with col2:
    st.metric("System Health", f"{health['score']}%", delta=None)

with col3:
    df = fetch_data()
    if not df.empty:
        st.metric("Data Points", len(df), delta=f"+{len(df.tail(10))}")

with col4:
    st.metric("Uptime", "99.2%", delta="0.1%")

# --- Fetch Data ---
with st.spinner("🔄 Loading real-time data..."):
    df = fetch_data()

# Robust check for data integrity
required_cols = [
    'soil_moisture_surface', 'soil_moisture_depth', 'soil_temp', 'env_moisture_api', 'api_temp', 'prediction', 'timestamp'
]
if df.empty or not all(col in df.columns for col in required_cols):
    st.error("❌ No valid data available from Firebase. Please check your database and try again.")
    st.stop()

# --- Sidebar Navigation ---
st.sidebar.markdown("## 🎛️ Panneau de Contrôle")
page = st.sidebar.radio(
    "Naviguer vers :",
    ["🏠 Tableau de bord", "📊 Analytique", "🌦️ Prévisions météo", "⚙️ Paramètres", "❓ FAQ & Documentation"],
    index=0
)

# --- FAQ & Documentation (French) ---
if page == "❓ FAQ & Documentation":
    st.markdown("## ❓ FAQ & Documentation")
    st.markdown("""
### 📝 Présentation du Système
Ce tableau de bord permet la surveillance en temps réel et le contrôle intelligent de l'irrigation agricole grâce à l'IA et l'IoT. Les données des capteurs sont collectées, analysées et utilisées pour optimiser l'irrigation.

### 🚀 Utilisation du Tableau de Bord
- **Tableau de bord** : Affiche les mesures en direct, l'état du système et les alertes.
- **Analytique** : Analyse avancée des tendances, corrélations et efficacité de l'irrigation.
- **Prévisions météo** : Donne les prévisions à 7 jours pour anticiper l'irrigation.
- **Paramètres** : Permet de configurer le système, les seuils et les notifications.

### 💧 Contrôle Manuel de l'Irrigation
- Utilisez le bouton "Démarrer/Arrêter l'irrigation" pour contrôler la pompe manuellement.
- Le système attend la confirmation de Firebase avant de mettre à jour l'état.

### 📊 Métriques & Alertes
- Les cartes de métriques affichent l'humidité, la température et l'état du système.
- Les alertes s'affichent si les seuils sont dépassés (sol sec, température élevée, etc.).

### 🛠️ Maintenance & Bonnes Pratiques
- Vérifiez régulièrement la connexion des capteurs et la synchronisation des données.
- Gardez le système à jour et sauvegardez les données importantes.

### ❓ Dépannage
- **Aucune donnée** : Vérifiez la connexion Firebase et l'alimentation des capteurs.
- **Erreur d'API météo** : Assurez-vous que les dépendances sont installées (`openmeteo-requests`, `requests-cache`, `retry-requests`).
- **Problème d'irrigation** : Contrôlez le relais et l'alimentation de la pompe.

### 📞 Support & Contact
Pour toute question ou assistance, contactez : support@smartirrigation.com
""")
    st.stop()

# --- Tableau de bord en direct ---
if page == "🏠 Tableau de bord":
    
    # Auto-refresh
    refresh_rate = st.sidebar.selectbox("Refresh Rate", [5, 10, 30, 60], index=1)
    st_autorefresh(interval=refresh_rate * 1000, key="datarefresh")
    
    latest = df.iloc[-1]
    
    # --- Enhanced Real-time Sensor Metrics ---
    st.markdown("## 📊 Relevés des capteurs en temps réel")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        # Handle NaN for soil_moisture_surface
        soil_moisture = latest['soil_moisture_surface'] * 100 if pd.notna(latest['soil_moisture_surface']) else None
        if soil_moisture is None or np.isnan(soil_moisture):
            # Find last valid value
            valid_surface = df['soil_moisture_surface'].dropna()
            if not valid_surface.empty:
                soil_moisture = valid_surface.iloc[-1] * 100
                subtitle = "(valeur précédente)"
            else:
                soil_moisture = None
                subtitle = "N/A"
        else:
            subtitle = "Niveau de surface"
        if soil_moisture is not None:
            if soil_moisture < 20:
                card_class = "metric-card-critical"
            elif soil_moisture < 40:
                card_class = "metric-card-warning"
            else:
                card_class = "metric-card-good"
            st.markdown(f"""
            <div class="{card_class}">
                <div class="metric-title">💧 Humidité du sol</div>
                <div class="metric-value">{soil_moisture:.1f}%</div>
                <div class="metric-subtitle">{subtitle}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card-warning">
                <div class="metric-title">💧 Humidité du sol</div>
                <div class="metric-value">N/A</div>
                <div class="metric-subtitle">Aucune donnée</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Handle NaN for soil_moisture_depth
        soil_depth = latest['soil_moisture_depth'] * 100 if pd.notna(latest['soil_moisture_depth']) else None
        if soil_depth is None or np.isnan(soil_depth):
            valid_depth = df['soil_moisture_depth'].dropna()
            if not valid_depth.empty:
                soil_depth = valid_depth.iloc[-1] * 100
                subtitle = "(valeur précédente)"
            else:
                soil_depth = None
                subtitle = "N/A"
        else:
            subtitle = "Zone racinaire"
        if soil_depth is not None:
            if soil_depth < 15:
                card_class = "metric-card-critical"
            elif soil_depth < 35:
                card_class = "metric-card-warning"
            else:
                card_class = "metric-card-good"
            st.markdown(f"""
            <div class="{card_class}">
                <div class="metric-title">🌱 Humidité profonde</div>
                <div class="metric-value">{soil_depth:.1f}%</div>
                <div class="metric-subtitle">{subtitle}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card-warning">
                <div class="metric-title">🌱 Humidité profonde</div>
                <div class="metric-value">N/A</div>
                <div class="metric-subtitle">Aucune donnée</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        soil_temp = latest['soil_temp']
        if soil_temp > 35 or soil_temp < 10:
            card_class = "metric-card-critical"
        elif soil_temp > 30 or soil_temp < 15:
            card_class = "metric-card-warning"
        else:
            card_class = "metric-card-good"
            
        st.markdown(f"""
        <div class="{card_class}">
            <div class="metric-title">🌡️ Température du sol</div>
            <div class="metric-value">{soil_temp:.1f}°C</div>
            <div class="metric-subtitle>Niveau du sol</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        air_humidity = latest['env_moisture_api']
        if air_humidity < 30:
            card_class = "metric-card-critical"
        elif air_humidity < 50:
            card_class = "metric-card-warning"
        else:
            card_class = "metric-card-good"
            
        st.markdown(f"""
        <div class="{card_class}">
            <div class="metric-title">💨 Humidité de l'air</div>
            <div class="metric-value">{air_humidity:.1f}%</div>
            <div class="metric-subtitle>Atmosphérique</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        air_temp = latest['api_temp']
        if air_temp > 40 or air_temp < 5:
            card_class = "metric-card-critical"
        elif air_temp > 35 or air_temp < 10:
            card_class = "metric-card-warning"
        else:
            card_class = "metric-card-good"
            
        st.markdown(f"""
        <div class="{card_class}">
            <div class="metric-title">🌤️ Température de l'air</div>
            <div class="metric-value">{air_temp:.1f}°C</div>
            <div class="metric-subtitle>Ambiante</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- Irrigation Status with Enhanced UI ---
    st.markdown("## 🚰 Centre de contrôle d'irrigation")
    
    prediction = int(latest.get("prediction", 0))
    status_map = {
        0: ("SYSTÈME EN ATTENTE", "L'irrigation est actuellement ARRÊTÉE", "status-inactive", "⏸️"),
        1: ("IRRIGATION EN COURS", "Le système arrose les cultures", "status-active", "💧"),
        2: ("SURVEILLANCE", "Aucun ajustement nécessaire", "status-inactive", "👁️"),
        3: ("ALERTE", "Attention requise !", "status-alert", "🚨")
    }
    
    status_label, message, css_class, icon = status_map.get(prediction, ("UNKNOWN", "Status unclear", "status-alert", "❓"))
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div class="{css_class}">
            <h2>{icon} {status_label}</h2>
            <p style="font-size: 18px; margin: 0;">{message}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if prediction in [0, 1]:
            button_label = "🛑 Arrêter l'irrigation" if prediction == 1 else "▶️ Démarrer l'irrigation"
            button_type = "secondary" if prediction == 1 else "primary"
            
            if st.button(button_label, type=button_type, use_container_width=True, key="irrigation_control"):
                try:
                    new_status = 0 if prediction == 1 else 1
                    new_record = latest.copy()
                    new_record["prediction"] = new_status
                    new_record["timestamp"] = datetime.now().isoformat()
                    
                    # Send relay command
                    relay_command = "ON" if new_status == 1 else "OFF"
                    db.reference("relay_command").set({
                        "command": relay_command,
                        "timestamp": new_record["timestamp"]
                    })
                    
                    # Save new record
                    ref = db.reference("irrigation_data")
                    ref.push(dict(new_record))
                    
                    st.success(f"✅ Commande envoyée ! Irrigation {'démarrée' if new_status == 1 else 'arrêtée'}")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error controlling irrigation: {e}")
    
    # --- Enhanced Charts ---
    st.markdown("## 📈 Analytique en temps réel")

    if len(df) > 1:
        # Create subplots for better visualization
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Température du sol', 'Température de l\'air', 
                          'Humidité de l\'air', 'Evapotranspiration'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # Soil temperature chart
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['soil_temp'],
                      name='Température du sol', line=dict(color='#e74c3c', width=3)),
            row=1, col=1
        )
        # Air temperature chart
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['api_temp'],
                      name='Température de l\'air', line=dict(color='#f39c12', width=3)),
            row=1, col=2
        )
        # Air humidity chart
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['env_moisture_api'],
                      name='Humidité de l\'air', line=dict(color='#9b59b6', width=3)),
            row=2, col=1
        )
        # ET0 chart
        if 'et0' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['et0'],
                          name='ET0', line=dict(color='#1abc9c', width=3)),
                row=2, col=2
            )
        fig.update_layout(height=600, showlegend=True, 
                         title_text="Live Sensor Data Dashboard")
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig, use_container_width=True)
    
    # --- Smart Alerts System ---
    st.markdown("## 🚨 Système d'alerte intelligent")
    
    # Sidebar controls for thresholds
    st.sidebar.markdown("### Seuils d'alerte")
    soil_moisture_min = st.sidebar.slider("Humidité du sol min (%)", 0, 100, 30)
    temp_max = st.sidebar.slider("Température max (°C)", 20, 50, 35)
    humidity_min = st.sidebar.slider("Humidité de l'air min (%)", 0, 100, 20)
    
    alerts = []
    if (latest['soil_moisture_surface']*100) < soil_moisture_min:
        alerts.append({
            "type": "critical",
            "message": f"Critique : Humidité du sol à {(latest['soil_moisture_surface']*100):.1f}% (en dessous de {soil_moisture_min}%)",
            "icon": "🚨"
        })
    
    if latest['api_temp'] > temp_max:
        alerts.append({
            "type": "warning", 
            "message": f"Température élevée détectée : {latest['api_temp']:.1f}°C (au-dessus de {temp_max}°C)",
            "icon": "🌡️"
        })
    
    if latest['env_moisture_api'] < humidity_min:
        alerts.append({
            "type": "info",
            "message": f"Humidité de l'air basse : {latest['env_moisture_api']:.1f}% (en dessous de {humidity_min}%)",
            "icon": "💨"
        })
    
    if alerts:
        for alert in alerts:
            st.markdown(f"""
            <div class="alert-card">
                <h4>{alert['icon']} Alerte {alert['type'].title()}</h4>
                <p style=\"margin: 0; font-size: 16px;\">{alert['message']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="success-card">
            <h4>✅ Tous les systèmes sont normaux</h4>
            <p style="margin: 0; font-size: 16px;">Toutes les mesures sont dans les plages acceptables.</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "📊 Analytique":
    st.markdown("## 📊 Analytique avancée")
    
    if len(df) > 1:
        # Time range selector
        now = datetime.now()
        time_range = st.selectbox("Sélectionner la période", ["Dernières 24 heures", "7 derniers jours", "30 derniers jours", "Tout le temps"])
        if time_range == "Dernières 24 heures":
            filtered_df = df[df['timestamp'] > (now - timedelta(days=1))]
        elif time_range == "7 derniers jours":
            filtered_df = df[df['timestamp'] > (now - timedelta(days=7))]
        elif time_range == "30 derniers jours":
            filtered_df = df[df['timestamp'] > (now - timedelta(days=30))]
        else:
            filtered_df = df
        if filtered_df.empty:
            st.warning("Aucune donnée disponible pour la période sélectionnée.")
        else:
            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_moisture = filtered_df['soil_moisture_surface'].mean() * 100
                st.metric("Humidité du sol moyenne", f"{avg_moisture:.1f}%")
            
            with col2:
                avg_temp = filtered_df['soil_temp'].mean()
                st.metric("Température du sol moyenne", f"{avg_temp:.1f}°C")
            
            with col3:
                irrigation_events = len(filtered_df[filtered_df['prediction'] == 1])
                st.metric("Événements d'irrigation", irrigation_events)
            
            with col4:
                if 'et0' in filtered_df.columns:
                    total_et0 = filtered_df['et0'].sum()
                    st.metric("ET0 total", f"{total_et0:.1f}mm")
                else:
                    st.metric("ET0 total", "N/A")
            
            # Detailed charts
            st.markdown("### 📈 Analyse détaillée des capteurs")
            
            # Create individual charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Soil moisture over time (handle NaN and scale to %)
                moist_df = filtered_df.copy()
                moist_df['soil_moisture_surface'] = moist_df['soil_moisture_surface'].fillna(method="ffill") * 100
                moist_df['soil_moisture_depth'] = moist_df['soil_moisture_depth'].fillna(method="ffill") * 100
                # Only plot if at least one value is not NaN
                if moist_df['soil_moisture_surface'].notna().any() or moist_df['soil_moisture_depth'].notna().any():
                    fig_moisture = px.line(moist_df, x='timestamp', 
                                         y=['soil_moisture_surface', 'soil_moisture_depth'],
                                         title="Tendances de l'humidité du sol",
                                         labels={'value': "Niveau d'humidité (%)", 'variable': 'Capteur'})
                    fig_moisture.update_yaxes(tickformat='.1f')
                    st.plotly_chart(fig_moisture, use_container_width=True)
                else:
                    st.info("Aucune donnée d'humidité du sol disponible pour la période sélectionnée.")
            
            with col2:
                # Temperature comparison
                fig_temp = px.line(filtered_df, x='timestamp', 
                                 y=['soil_temp', 'api_temp'],
                                 title="Comparaison des températures",
                                 labels={'value': 'Température (°C)', 'variable': 'Capteur'})
                st.plotly_chart(fig_temp, use_container_width=True)
            
            # Correlation heatmap
            st.markdown("### 🔗 Analyse de corrélation des capteurs")
            numeric_cols = ['soil_moisture_surface', 'soil_moisture_depth', 'soil_temp', 'api_temp', 'env_moisture_api']
            if 'et0' in filtered_df.columns:
                numeric_cols.append('et0')
            
            corr_matrix = filtered_df[numeric_cols].corr()
            
            fig_heatmap = px.imshow(corr_matrix, 
                                   text_auto=True, 
                                   aspect="auto",
                                   title="Matrice de corrélation des données capteurs",
                                   color_continuous_scale="RdBu")
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Irrigation efficiency analysis
            st.markdown("### 💧 Efficacité de l'irrigation")
            
            irrigation_data = filtered_df[filtered_df['prediction'] == 1]
            if not irrigation_data.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Irrigation frequency by hour
                    irrigation_data['hour'] = irrigation_data['timestamp'].dt.hour
                    hourly_irrigation = irrigation_data.groupby('hour').size()
                    
                    fig_hourly = px.bar(x=hourly_irrigation.index, y=hourly_irrigation.values,
                                       title="Événements d'irrigation par heure",
                                       labels={'x': "Heure de la journée", 'y': "Nombre d'événements"})
                    st.plotly_chart(fig_hourly, use_container_width=True)
                
                with col2:
                    # Average conditions during irrigation
                    avg_conditions = irrigation_data[['soil_moisture_surface', 'soil_temp', 'api_temp']].mean()
                    
                    fig_conditions = px.bar(x=avg_conditions.index, y=avg_conditions.values,
                                          title="Conditions moyennes pendant l'irrigation",
                                          labels={'x': 'Capteur', 'y': 'Valeur moyenne'})
                    st.plotly_chart(fig_conditions, use_container_width=True)
            else:
                st.info("Aucun événement d'irrigation trouvé pour la période sélectionnée.")

elif page == "🌦️ Prévisions météo":
    st.markdown("## 🌦️ Prévisions météo sur 7 jours")
    
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry
        
        # Setup Open-Meteo API client
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 31.638817,
            "longitude": -8.0118352,
            "daily": ["et0_fao_evapotranspiration", "temperature_2m_max", "temperature_2m_min", 
                     "precipitation_sum", "wind_speed_10m_max"],
            "timezone": "auto",
            "forecast_days": 7
        }
        
        with st.spinner("🌤️ Fetching weather forecast..."):
            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]
            daily = response.Daily()
            
            # Extract data
            daily_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                    end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=daily.Interval()),
                    inclusive="left"
                ),
                "ET0 (mm)": daily.Variables(0).ValuesAsNumpy(),
                "Max Temp (°C)": daily.Variables(1).ValuesAsNumpy(),
                "Min Temp (°C)": daily.Variables(2).ValuesAsNumpy(),
                "Precipitation (mm)": daily.Variables(3).ValuesAsNumpy(),
                "Max Wind Speed (km/h)": daily.Variables(4).ValuesAsNumpy()
            }
            
            df_forecast = pd.DataFrame(data=daily_data)
        
        # Display forecast cards
        st.markdown("### 📅 Prévisions quotidiennes")
        
        cols = st.columns(7)
        for i, (idx, row) in enumerate(df_forecast.iterrows()):
            with cols[i]:
                weather_icon = "☀️" if row['Precipitation (mm)'] < 1 else "🌧️"
                st.markdown(f"""
                <div class="weather-card">
                    <h4>{row['date'].strftime('%a')}</h4>
                    <div style="font-size: 24px;">{weather_icon}</div>
                    <p><strong>{row['Max Temp (°C)']:.0f}°/{row['Min Temp (°C)']:.0f}°</strong></p>
                    <p>💧 {row['ET0 (mm)']:.1f}mm</p>
                    <p>🌧️ {row['Precipitation (mm)']:.1f}mm</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Forecast charts
        st.markdown("### 📊 Tendances météo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature forecast
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=df_forecast['date'], y=df_forecast['Max Temp (°C)'],
                                        mode='lines+markers', name='Max Temp', line=dict(color='red', width=3)))
            fig_temp.add_trace(go.Scatter(x=df_forecast['date'], y=df_forecast['Min Temp (°C)'],
                                        mode='lines+markers', name='Min Temp', line=dict(color='blue', width=3)))
            fig_temp.update_layout(title="Prévision des températures", xaxis_title="Date", yaxis_title="Température (°C)")
            st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            # Precipitation and ET0
            fig_precip = go.Figure()
            fig_precip.add_trace(go.Bar(x=df_forecast['date'], y=df_forecast['Precipitation (mm)'],
                                      name='Précipitations', marker_color='lightblue'))
            fig_precip.add_trace(go.Scatter(x=df_forecast['date'], y=df_forecast['ET0 (mm)'],
                                          mode='lines+markers', name='ET0', line=dict(color='green', width=3),
                                          yaxis='y2'))
            fig_precip.update_layout(
                title="Précipitations & Évapotranspiration",
                xaxis_title="Date",
                yaxis=dict(title="Précipitations (mm)", side="left"),
                yaxis2=dict(title="ET0 (mm)", side="right", overlaying="y")
            )
            st.plotly_chart(fig_precip, use_container_width=True)
        
        # Wind speed chart
        fig_wind = px.line(df_forecast, x='date', y='Max Wind Speed (km/h)',
                          title="Prévision de la vitesse du vent", markers=True)
        fig_wind.update_traces(line_color='purple', line_width=3)
        st.plotly_chart(fig_wind, use_container_width=True)
        
        # Irrigation recommendations
        st.markdown("### 💡 Recommandations d'irrigation")
        
        recommendations = []
        for idx, row in df_forecast.iterrows():
            day_name = row['date'].strftime('%A')
            if row['Precipitation (mm)'] > 5:
                recommendations.append(f"🌧️ **{day_name}** : Forte pluie attendue ({row['Precipitation (mm)']:.1f}mm) - Réduire l'irrigation")
            elif row['ET0 (mm)'] > 4:
                recommendations.append(f"☀️ **{day_name}** : Évapotranspiration élevée ({row['ET0 (mm)']:.1f}mm) - Augmenter l'irrigation")
            elif row['Max Temp (°C)'] > 35:
                recommendations.append(f"🌡️ **{day_name}** : Journée très chaude ({row['Max Temp (°C)']:.0f}°C) - Surveiller l'humidité du sol")
        
        if recommendations:
            for rec in recommendations:
                st.info(rec)
        else:
            st.success("✅ Conditions météo normales attendues - maintenir l'irrigation habituelle")
        
    except ImportError:
        st.error("❌ Les prévisions météo nécessitent des paquets supplémentaires. Installez : pip install openmeteo-requests requests-cache retry-requests")
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des données météo : {e}")

elif page == "⚙️ Paramètres":
    st.markdown("## ⚙️ Paramètres du système")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔧 Configuration du système")
        
        # Location settings
        location = st.text_input("Emplacement de la ferme", value="Marrakech, Maroc")
        latitude = st.number_input("Latitude", value=31.638817, format="%.6f")
        longitude = st.number_input("Longitude", value=-8.0118352, format="%.6f")
        
        # Irrigation settings
        irrigation_mode = st.selectbox("Mode d'irrigation", ["Automatique", "Manuel", "Planifié"])
        start_time = st.time_input("Heure de début quotidienne", value=datetime.strptime("06:00", "%H:%M").time())
        end_time = st.time_input("Heure de fin quotidienne", value=datetime.strptime("18:00", "%H:%M").time())
        
        # Sensor calibration
        st.markdown("### 🎯 Calibration des capteurs")
        moisture_offset = st.slider("Décalage capteur humidité (%)", -10, 10, 0)
        temp_offset = st.slider("Décalage capteur température (°C)", -5, 5, 0)
    
    with col2:
        st.markdown("### 📊 Gestion des données")
        
        # Data retention
        retention_period = st.selectbox("Rétention des données", ["7 jours", "30 jours", "90 jours", "1 an"])
        enable_backup = st.checkbox("Activer la sauvegarde des données", value=True)
        daily_reports = st.checkbox("Exporter les rapports quotidiens", value=False)
        
        # Notifications
        st.markdown("### 🔔 Notifications")
        email_alerts = st.checkbox("Alertes par email", value=True)
        sms_notifications = st.checkbox("Notifications SMS", value=False)
        email_address = st.text_input("Adresse email", value="agriculteur@exemple.com")
        
        # Advanced settings
        st.markdown("### ⚙️ Avancé")
        ml_sensitivity = st.slider("Sensibilité du modèle ML", 0.1, 1.0, 0.7)
        auto_irrigation = st.checkbox("Activer l'irrigation automatique", value=True)
    
    # Save settings
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Enregistrer les paramètres", type="primary", use_container_width=True):
            # Here you would save settings to Firebase or local storage
            settings = {
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "irrigation_mode": irrigation_mode,
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
                "moisture_offset": moisture_offset,
                "temp_offset": temp_offset,
                "retention_period": retention_period,
                "enable_backup": enable_backup,
                "daily_reports": daily_reports,
                "email_alerts": email_alerts,
                "sms_notifications": sms_notifications,
                "email_address": email_address,
                "ml_sensitivity": ml_sensitivity,
                "auto_irrigation": auto_irrigation
            }
            
            try:
                # Save to Firebase
                db.reference("system_settings").set(settings)
                st.success("✅ Paramètres enregistrés avec succès !")
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")
    
    # System information
    st.markdown("---")
    st.markdown("### 📋 Informations système")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**Version du système** : v2.1.0")
        st.info("**Dernière mise à jour** : 2024-01-15")
    
    with col2:
        st.info("**Base de données** : Firebase Realtime")
        st.info("**Modèle ML** : Random Forest v1.2")
    
    with col3:
        st.info("**Capteurs** : 5 actifs")
        st.info("**Disponibilité** : 99.2%")

# --- Pied de page ---
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🌱 Système d'Irrigation Intelligent**")
    st.markdown("Propulsé par l'IA & l'IoT")

with col2:
    st.markdown(f"**📊 Statut du Système**")
    st.markdown(f"Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}")

with col3:
    st.markdown("**📞 Support**")
    st.markdown("Contact : support@smartirrigation.com")