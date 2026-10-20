import paho.mqtt.client as mqtt
import requests
import threading
import json
import pandas as pd
import joblib
import warnings
import numpy as np  

warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
MQTT_BROKER     = "broker.hivemq.com"
MQTT_PORT       = 1883
MQTT_TOPIC      = "pipenetwork/sensors/pressure"
# HTTP_SERVER_URL = "http://localhost:5000/api/pressure"
HTTP_SERVER_URL = "https://water-leakage-backend.onrender.com/api/pressure"
print("⏳ Loading ML Model (250MB)... Please wait...")
try:
    model = joblib.load("rf_optimized_leak_detector.pkl")
    print("✅ ML Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    exit()

message_count = 0

def predict_leak(pressures):
    try:
        df_input = pd.DataFrame(columns=model.feature_names_in_)
        df_input.loc[0] = 0.0 
        
        for col_name in model.feature_names_in_:
            if col_name.startswith("Pressure_"):
                node = col_name.split("_")[1]
                raw_p = pressures.get(node, 50.0)
                
                if isinstance(raw_p, dict):
                    p_val = float(raw_p.get('p', 50.0))
                else:
                    p_val = float(raw_p)
                    
                df_input.at[0, col_name] = p_val
                
        prediction = model.predict(df_input)
        
        # 🚨 FIX 1: Agar prediction numpy array hai toh use list mein badlein
        if hasattr(prediction, "tolist"):
            prediction = prediction.tolist()

        leaks = []
        # Multi-output model ke liye logic
        for idx, col in enumerate(model.classes_):
            if prediction[0][idx] == 1:
                leaks.append(str(col)) # Ensure string format for JSON
        return leaks
    except Exception as e:   
        print(f"AI Error: {e}")
        return []

def send_http(json_payload):
    try:
        requests.post(HTTP_SERVER_URL, data=json_payload, headers={"Content-Type": "application/json"}, timeout=5)
    except:
        pass 
  
def on_message(client, userdata, msg):
    global message_count
    message_count += 1
    raw = msg.payload.decode("utf-8")
    
    try:
        data = json.loads(raw)
    except:
        return

    pressures = data.get("pressures", {})
    
    # AI Prediction
    detected_leaks = predict_leak(pressures)
    
    # 🚨 FIX 2: Double Check - Final conversion for detected_leaks
    if hasattr(detected_leaks, "tolist"):
        detected_leaks = detected_leaks.tolist()
    
    if detected_leaks:
        print(f"⚠️ [AI ALERT #{message_count}] Leaks Detected: {detected_leaks}")
    else:
        print(f"✅ [MSG #{message_count}] System Normal")
    
    # Frontend Data Cleaning
    clean_pressures = {}
    for node, val in pressures.items():
        try:
            if isinstance(val, dict):
                clean_pressures[node] = float(val.get('p', 0))
            else:
                clean_pressures[node] = float(val)
        except:
            clean_pressures[node] = 0.0
            
    # Payload Setup
    payload = {
        "pressures": clean_pressures,
        "ml_leaks": detected_leaks
    }
    
    # 🚨 FIX 3: JSON dumping with error handling
    try:
        json_data = json.dumps(payload)
        thread = threading.Thread(target=send_http, args=(json_data,))
        thread.daemon = True
        thread.start()
    except Exception as e:
        print(f"JSON Serialization Error: {e}")

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("🔗 Connected to MQTT broker! Waiting for simulator data...")
        client.subscribe(MQTT_TOPIC, qos=1)

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="esp32_ai_bridge_123")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()
except Exception as e:
    print(f"Connection Error: {e}")






