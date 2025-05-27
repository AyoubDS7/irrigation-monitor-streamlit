import streamlit as st
st.set_page_config(page_title="Irrigation Monitor Dashboard", layout="wide")

import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh
import requests

# --- Firebase Setup ---
cred = credentials.Certificate("sensordatairrigation-firebase-adminsdk-fbsvc-8361e6c330.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://sensordatairrigation-default-rtdb.firebaseio.com/'
    })

# --- Fetch Data from Firebase ---
def fetch_data():
    ref = db.reference("irrigation_data")
    data = ref.get()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data.values())
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    return df

# --- Optional: Header Image ---
if os.path.exists("header.jpg"):
    st.image("header.jpg", use_column_width=True)

# --- Title ---
st.title("📊 Irrigation Monitor Dashboard")

# --- Fetch Data ---
with st.spinner("Loading data from Firebase..."):
    df = fetch_data()

if df.empty:
    st.warning("No data found in Firebase.")
    st.stop()

# --- Streamlit Multi-Page Setup ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Live Measures & Charts", "Weather Forecast"])

if page == "Live Measures & Charts":
    # --- Live Sensor Values ---
    st.subheader("📟 Live Sensor Values")
    latest = df.iloc[-1]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(f"<div style='font-size:20px;'>💧 <b>Soil Moisture</b><br><span style='color:green;font-size:24px;'>{latest['soil_moisture_api']:.1f}%</span></div>", unsafe_allow_html=True)
    col2.markdown(f"<div style='font-size:20px;'>🌡️ <b>Soil Temp</b><br><span style='color:#e67300;font-size:24px;'>{latest['soil_temp']:.1f}°C</span></div>", unsafe_allow_html=True)
    col3.markdown(f"<div style='font-size:20px;'>💨 <b>Humidity</b><br><span style='color:blue;font-size:24px;'>{latest['env_moisture_api']:.1f}%</span></div>", unsafe_allow_html=True)
    col4.markdown(f"<div style='font-size:20px;'>🌞 <b>ET0</b><br><span style='color:#9933ff;font-size:24px;'>{latest['et0']:.2f} mm</span></div>", unsafe_allow_html=True)
    col5.markdown(f"<div style='font-size:20px;'>🌤️ <b>Temp</b><br><span style='color:red;font-size:24px;'>{latest['api_temp']:.1f}°C</span></div>", unsafe_allow_html=True)

    # --- Irrigation Status ---
    st.subheader(":seedling: Irrigation Status")
    prediction = int(latest.get("prediction", 0))
    status_map = {
        0: ("OFF", "gray", "Irrigation is currently not needed."),
        1: ("ON", "green", "Irrigation is ACTIVE."),
        2: ("NO ADJUSTMENT", "orange", "No change in irrigation schedule."),
        3: ("ALERT", "red", "Alert: abnormal condition detected!")
    }
    status_label, color, message = status_map.get(prediction, ("UNKNOWN", "black", "Unknown status."))
    st.markdown(f"<h4 style='color:{color}'>Status: {status_label}</h4>", unsafe_allow_html=True)
    st.info(message)
    if prediction in [0, 1]:
        button_label = "Turn OFF Irrigation" if prediction == 1 else "Turn ON Irrigation"
        if st.button(button_label, key="irrigation_toggle"):
            new_status = 0 if prediction == 1 else 1
            new_record = latest.copy()
            new_record["prediction"] = new_status
            new_record["timestamp"] = datetime.now().isoformat()
            # --- Write relay command for ESP32 ---
            relay_command = "ON" if new_status == 1 else "OFF"
            db.reference("relay_command").set({
                "command": relay_command,
                "timestamp": new_record["timestamp"]
            })
            # --- Save the new record as usual ---
            ref = db.reference("irrigation_data")
            ref.push(dict(new_record))
            st.success(f"Irrigation turned {'OFF' if new_status == 0 else 'ON'}! Command sent to ESP32.")
            st.experimental_rerun()
    else:
        st.info("Manual control is disabled for status: " + status_label)

    # --- Auto-refresh ---
    st_autorefresh(interval=10 * 1000, key="datarefresh")
    st.markdown("<p style='font-size:14px;color:gray;'>🔄 Auto-refresh every 10 seconds...</p>", unsafe_allow_html=True)

    # --- Charts ---
    st.subheader("📈 Sensor Data Over Time")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        fig1 = px.line(df, x='timestamp', y='soil_moisture_api', title='Soil Moisture (%)', markers=True)
        st.plotly_chart(fig1, use_container_width=True)
    with chart_cols[1]:
        fig2 = px.line(df, x='timestamp', y='soil_temp', title='Soil Temperature (°C)', markers=True)
        st.plotly_chart(fig2, use_container_width=True)
    chart_cols2 = st.columns(2)
    with chart_cols2[0]:
        fig3 = px.line(df, x='timestamp', y='env_moisture_api', title='Humidity (%)', markers=True)
        st.plotly_chart(fig3, use_container_width=True)
    with chart_cols2[1]:
        fig4 = px.line(df, x='timestamp', y='et0', title='ET0 (mm)', markers=True)
        st.plotly_chart(fig4, use_container_width=True)

    # --- Alerts ---
    st.subheader("🚨 Alerts")
    soil_moisture_min = st.sidebar.number_input("Min Soil Moisture (%)", 0.0, 100.0, 30.0)
    temp_max = st.sidebar.number_input("Max Temperature (°C)", -20.0, 60.0, 35.0)
    humidity_min = st.sidebar.number_input("Min Humidity (%)", 0.0, 100.0, 20.0)
    alerts = []
    if (latest['soil_moisture_api']*100) < soil_moisture_min:
        alerts.append(f"⚠️ Soil moisture low: {(latest['soil_moisture_api']*100):.1f}% < {soil_moisture_min}%")
    if latest['api_temp'] > temp_max:
        alerts.append(f"⚠️ Temperature high: {latest['api_temp']:.1f}°C > {temp_max}°C")
    if latest['env_moisture_api'] < humidity_min:
        alerts.append(f"⚠️ Humidity low: {latest['env_moisture_api']:.1f}% < {humidity_min}%")
    if alerts:
        for alert in alerts:
            st.error(alert)
    else:
        st.success("✅ All sensor values are within normal range.")

elif page == "Weather Forecast":
    st.subheader("🌦️ Weather Forecast (Open-Meteo API)")
    import openmeteo_requests
    import pandas as pd
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
        "daily": ["et0_fao_evapotranspiration", "temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto",
        "forecast_days": 7
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        daily = response.Daily()
        daily_et0 = daily.Variables(0).ValuesAsNumpy()
        daily_temp_max = daily.Variables(1).ValuesAsNumpy()
        daily_temp_min = daily.Variables(2).ValuesAsNumpy()
        daily_data = {"date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        )}
        daily_data["ET0 (mm)"] = daily_et0
        daily_data["Temp Max (°C)"] = daily_temp_max
        daily_data["Temp Min (°C)"] = daily_temp_min
        df_forecast = pd.DataFrame(data=daily_data)
        st.dataframe(df_forecast, use_container_width=True)
        st.line_chart(df_forecast.set_index("date")[["ET0 (mm)", "Temp Max (°C)", "Temp Min (°C)"]])
    except Exception as e:
        st.error(f"Error fetching Open-Meteo forecast: {e}")

# --- FAQ / Docs ---
with st.expander("📘 FAQ / Documentation"):
    st.markdown("""
    ## 💧 How the Irrigation System Works

    This smart irrigation dashboard uses real-time data from field sensors and weather APIs to automate irrigation decisions using a Machine Learning (ML) model. Here's what you need to know:

    ### 🌿 Sensor Inputs
    - **Soil Moisture Sensor**: Measures how wet or dry the soil is.
    - **Soil Temperature**: Affects how water evaporates from the ground.
    - **Humidity & Air Temperature**: Help assess evaporation rate and plant water demand.
    - **ET0 (Reference Evapotranspiration)**: Calculated from weather data, it tells us how much water the plant is losing.

    ### 🧠 What the AI Model Predicts
    The model predicts one of the following **4 irrigation classes**:
    - `0 - OFF`: No irrigation needed.
    - `1 - ON`: Irrigation needed now.
    - `2 - NO ADJUSTMENT`: Keep current state, no changes.
    - `3 - ALERT`: Abnormal readings, requires attention (e.g., sensor failure, extreme weather).

    These decisions are based on a combination of:
    - Recent trends in moisture, temperature, and humidity
    - Weather forecast and evapotranspiration
    - Your location (if GPS is enabled)

    ### 🛠️ How to Use This Dashboard
    - 📊 **Live Sensor Values**: Shows the latest data from your field.
    - 💡 **Status Indicator**: Tells you if the system is currently irrigating, idle, or has detected an issue.
    - 🔘 **Irrigation Button**: Manually override if needed (enabled only when safe).
    - ⚠️ **Alerts**: Triggered when temperature or humidity go beyond thresholds.
    - 📈 **Charts**: Visualize historical trends and patterns.

    ### ⏱️ Data Update Frequency
    - Sensor readings are sent every 1 minute.
    - The dashboard refreshes automatically every 10 seconds.

    ### 📱 Access Anywhere
    This app is web-based. You can access it from any smartphone, tablet, or computer with internet.

    ### ❓ Questions or Problems?
    If you see unusual data or alerts:
    - Check sensor connections and battery
    - Make sure WiFi or GSM module is online
    - Contact support if needed (if using with a service)

    ---
    _Empowering farmers with AI and automation for smarter water use._
    """, unsafe_allow_html=True)
