import numpy as np
import joblib
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import openmeteo_requests
import requests_cache
from retry_requests import retry
import requests
import time

# --- Firebase Setup ---
cred = credentials.Certificate("sensordatairrigation-firebase-adminsdk-fbsvc-8361e6c330.json")  # Replace with your Firebase service account JSON
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://sensordatairrigation-default-rtdb.firebaseio.com/'  # Replace with your Firebase project URL
})

# --- Open Meteo Setup ---
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# --- Calibration Functions ---
def calibrate_soil_moisture(raw_value, dry_value=4095, wet_value=0):
    return round((dry_value - raw_value) * 100 / (dry_value - wet_value), 2)

def calibrate_rain_sensor(raw_value):
    return round((4095 - raw_value) * 100 / 4095, 2)

# --- WeatherAPI ---
def get_weather_data(lat, lon):
    WEATHER_API_KEY = "4ba3989141d042c1b4d120030253003"
    WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"
    params = {"key": WEATHER_API_KEY, "q": f"{lat},{lon}", "aqi": "no"}
    response = requests.get(WEATHER_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return {
            "temperature": data["current"]["temp_c"],
            "precip_mm": data["current"]["precip_mm"],
            "last_update": data["current"]["last_updated"]
        }
    return None

# --- Open Meteo API ---
def get_open_meteo_data(lat, lon, current_hour):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["et0_fao_evapotranspiration", "soil_temperature_6cm", "soil_moisture_27_to_81cm", "relative_humidity_2m", "soil_moisture_0_to_1cm"],
        "timezone": "auto",
        "forecast_days": 1
    }
    responses = openmeteo.weather_api(OPEN_METEO_URL, params=params)
    if responses:
        hourly = responses[0].Hourly()
        return {
            "et0_fao_evapotranspiration": hourly.Variables(0).ValuesAsNumpy()[current_hour],
            "soil_temperature_6cm": hourly.Variables(1).ValuesAsNumpy()[current_hour],
            "soil_moisture_27_to_81cm": hourly.Variables(2).ValuesAsNumpy()[current_hour],
            "relative_humidity_2m": hourly.Variables(3).ValuesAsNumpy()[current_hour],
            "soil_moisture_0_to_1cm": hourly.Variables(4).ValuesAsNumpy()[current_hour]
        }
    return None

# --- Load Model ---
model = joblib.load("saved_models/xgb_model.pkl")
model_rf = joblib.load("random_forest_irrigation.pkl")

def process_and_save_data():
    try:
        lat, lon = 30.47028, -8.87695
        current_hour = datetime.utcnow().hour

        # Get weather and open meteo data
        weather_data = get_weather_data(lat, lon)
        meteo_data = get_open_meteo_data(lat, lon, current_hour)

        if not weather_data or not meteo_data:
            return "Weather/API error", 500

        # Prepare features for prediction
        features = np.array([[meteo_data["soil_moisture_27_to_81cm"]*100,
                              meteo_data["soil_temperature_6cm"],
                              meteo_data["relative_humidity_2m"],
                              weather_data["temperature"],
                              weather_data["precip_mm"],
                              meteo_data["et0_fao_evapotranspiration"]]])
        prediction = float(model_rf.predict(features)[0])
        result = {
            "timestamp": datetime.now().isoformat(),
            "api_temp": float(weather_data["temperature"]),
            "api_precip_mm": float(weather_data["precip_mm"]),
            "api_last_update": weather_data["last_update"],
            "et0": float(meteo_data["et0_fao_evapotranspiration"]),
            "soil_temp": float(meteo_data["soil_temperature_6cm"]),
            "soil_moisture_depth": float(meteo_data["soil_moisture_27_to_81cm"]),
            "soil_moisture_surface": float(meteo_data["soil_moisture_0_to_1cm"]),
            "env_moisture_api": float(meteo_data["relative_humidity_2m"]),
            "prediction": prediction
        }

        # --- Save to Firebase ---
        ref = db.reference("irrigation_data")
        ref.push(result)

        print(f"Data saved to Firebase: {result}")

        return "Data saved successfully", 200

    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500

# Function to receive ESP32 data (to be added later)
def receive_data_from_esp32():
    print("Ready to receive data from ESP32 (via Wi-Fi) when you are ready!")
    esp32_data = {
        "soil_moisture": 65.0,  # Example value from ESP32
        "temperature": 22.5      # Exampythle value from ESP32
    }

    # You can then call your process_and_save_data function to save this data
    process_and_save_data()

if __name__ == "__main__":
    print("Starting scheduled data collection every minute...")
    while True:
        process_and_save_data()
        receive_data_from_esp32()
        time.sleep(60) # Wait for 60 seconds before the next execution

    
    # Later, you can call receive_data_from_esp32() when you're ready to receive data from ESP32 via Wi-Fi
    # You could use a scheduler to periodically call the `process_and_save_data()` or `receive_data_from_esp32()`
    # For now, simulate ESP32 data reception
    
