# Remote Patient Monitoring System

A real-time IoT-based Remote Patient Monitoring (RPM) system developed using AWS cloud services, MQTT communication, Streamlit, and machine learning-assisted risk analysis.

The system continuously simulates patient vital signs, sends the data securely to AWS cloud infrastructure, stores patient records in DynamoDB, and visualizes patient health status through an interactive dashboard.

---

## Features

- Real-time patient monitoring
- MQTT-based IoT communication
- AWS IoT Core integration
- AWS Lambda backend processing
- DynamoDB cloud database
- Rule-based patient risk detection
- Random Forest based ML-assisted risk estimation
- Streamlit dashboard for monitoring and visualization
- Historical vital trends
- Doctor notes management
- PDF report generation

---

## Tech Stack

### Backend & Cloud
- Python
- AWS IoT Core
- AWS Lambda
- Amazon DynamoDB
- Boto3

### Dashboard & Visualization
- Streamlit
- Pandas
- Plotly

### Machine Learning
- Scikit-learn
- Random Forest Classifier
- Joblib

### Communication
- MQTT Protocol
- Paho MQTT Client

---

## System Workflow

```text
Simulator
   ↓
MQTT Protocol
   ↓
AWS IoT Core
   ↓
AWS Lambda
   ↓
DynamoDB
   ↓
Streamlit Dashboard
   ↓
Risk Analysis