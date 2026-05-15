import paho.mqtt.client as mqtt
import ssl
import json
import time
import random

# -------------------------------
# AWS IoT Config
# -------------------------------
ENDPOINT = "aruwiuvwgnyee-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
TOPIC = "rpm/data"

CA_PATH = "C:/rpm_project/certs/AmazonRootCA1.pem"
CERT_PATH = "C:/rpm_project/certs/ca8331808c148f8d9357be948a3812fc746bb2ca8e453024a07aead78a946b79-certificate.pem.crt"
KEY_PATH = "C:/rpm_project/certs/ca8331808c148f8d9357be948a3812fc746bb2ca8e453024a07aead78a946b79-private.pem.key"

# -------------------------------
# Patients
# -------------------------------
names = [
    "Rahul Sharma", "Priya Mehta", "Amit Patel", "Sneha Iyer",
    "Vikram Singh", "Anjali Desai", "Rohan Gupta", "Neha Kulkarni",
    "Karan Verma", "Pooja Nair"
]

patients = []

for i in range(10):

    state = random.choice(["normal", "warning", "critical"])

    if state == "normal":
        base = {
            "heart_rate": random.randint(65, 85),
            "respiratory_rate": random.randint(12, 16),
            "temperature": round(random.uniform(36.5, 37.0), 1),
            "spo2": random.randint(96, 100),
            "systolic_bp": random.randint(110, 125),
            "diastolic_bp": random.randint(70, 80)
        }

    elif state == "warning":
        base = {
            "heart_rate": random.randint(95, 110),
            "respiratory_rate": random.randint(18, 22),
            "temperature": round(random.uniform(37.5, 38.2), 1),
            "spo2": random.randint(90, 94),
            "systolic_bp": random.randint(135, 150),
            "diastolic_bp": random.randint(85, 95)
        }

    else:
        base = {
            "heart_rate": random.randint(120, 135),
            "respiratory_rate": random.randint(22, 28),
            "temperature": round(random.uniform(38.5, 39.5), 1),
            "spo2": random.randint(82, 88),
            "systolic_bp": random.randint(150, 170),
            "diastolic_bp": random.randint(95, 105)
        }

    patients.append({
        "patient_id": i + 1,
        "name": names[i],
        "age": random.randint(20, 70),
        "gender": random.choice([0, 1]),
        "height": round(random.uniform(1.5, 1.85), 2),
        "weight": random.randint(50, 90),
        "trend": random.choice(["up", "down", "stable"]),
        "vitals": base
    })

# -------------------------------
# Update Vitals (realistic)
# -------------------------------
def update_vitals(v):

    if random.random() < 0.1:
        v["trend"] = random.choice(["up", "down", "stable"])

    trend = v.get("trend", "stable")

    if trend == "up":
        hr_change = random.randint(1, 3)
        spo2_change = random.randint(-2, 0)
        temp_change = random.uniform(0.1, 0.3)

    elif trend == "down":
        hr_change = random.randint(-3, -1)
        spo2_change = random.randint(0, 1)
        temp_change = random.uniform(-0.3, -0.1)

    else:
        hr_change = random.randint(-2, 2)
        spo2_change = random.randint(-1, 1)
        temp_change = random.uniform(-0.1, 0.1)

    v["heart_rate"] += hr_change
    v["spo2"] += spo2_change
    v["temperature"] += round(temp_change, 1)

    v["respiratory_rate"] += random.randint(-1, 1)
    v["systolic_bp"] += random.randint(-3, 3)
    v["diastolic_bp"] += random.randint(-2, 2)

    v["heart_rate"] = max(40, min(150, v["heart_rate"]))
    v["spo2"] = max(80, min(100, v["spo2"]))
    v["temperature"] = round(max(35.0, min(40.5, v["temperature"])), 1)

    return v

# -------------------------------
# MQTT Setup
# -------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core")
    else:
        print("Connection failed:", rc)

client = mqtt.Client(client_id="rpm_simulator")
client.on_connect = on_connect

client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

print("Connecting...")
client.connect(ENDPOINT, PORT, keepalive=60)
client.loop_start()

# -------------------------------
# MAIN LOOP (ALL PATIENTS)
# -------------------------------
try:
    while True:

        for patient in patients:

            patient["vitals"] = update_vitals(patient["vitals"])
            vitals = patient["vitals"]

            payload = {
                "patient_id": patient["patient_id"],
                "name": patient["name"],
                "age": patient["age"],
                "gender": patient["gender"],
                "height": patient["height"],
                "weight": patient["weight"],
                **vitals,
                "timestamp": int(time.time())
            }

            client.publish(TOPIC, json.dumps(payload), qos=1)

            print(f"{patient['name']} | HR: {vitals['heart_rate']} | SpO2: {vitals['spo2']}")

        time.sleep(3)

except KeyboardInterrupt:
    print("Stopped")

finally:
    client.loop_stop()
    client.disconnect()