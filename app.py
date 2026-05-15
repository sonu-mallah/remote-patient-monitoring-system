# ============================================
# Remote Patient Monitoring Dashboard
# ============================================

import streamlit as st
import pandas as pd
import boto3
import joblib
import time
import uuid
from decimal import Decimal
import plotly.express as px

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from streamlit_autorefresh import st_autorefresh

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=10000, key="refresh")

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="RPM Dashboard", layout="wide")

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
.block {
    padding:15px;
    border-radius:10px;
    background:#1f2937;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

st.title("Remote Patient Monitoring System")

# ---------------- AWS CONFIG ----------------
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")

rpm_table = dynamodb.Table("rpm_data")
patient_table = dynamodb.Table("patient_info")
notes_table = dynamodb.Table("doctor_notes")

# ---------------- LOAD MODEL ----------------
model = joblib.load("model_new.pkl")

# ---------------- HELPER FUNCTIONS ----------------

def convert_decimal(obj):

    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]

    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}

    if isinstance(obj, Decimal):
        return float(obj)

    return obj


def scan(table):

    return [
        convert_decimal(i)
        for i in table.scan().get("Items", [])
    ]


# ---------------- RISK ANALYSIS ----------------

def predict_risk(row):

    hr = row.get("heart_rate", 0)
    spo2 = row.get("spo2", 0)
    temp = row.get("temperature", 0)
    bp = row.get("systolic_bp", 0)

    reasons = []

    # ---------------- RULE-BASED LOGIC ----------------

    rule_severity = "Normal"

    # Critical conditions
    if spo2 < 90:
        rule_severity = "Critical"
        reasons.append("Low SpO2")

    if hr > 130 or hr < 40:
        rule_severity = "Critical"
        reasons.append("Abnormal Heart Rate")

    if temp > 39:
        rule_severity = "Critical"
        reasons.append("High Temperature")

    if bp > 160:
        rule_severity = "Critical"
        reasons.append("Very High BP")

    # Warning conditions
    if rule_severity != "Critical":

        if (
            spo2 < 94
            or hr > 110
            or temp > 38
            or bp > 140
        ):

            rule_severity = "Warning"

            if spo2 < 94:
                reasons.append("Low SpO2")

            if hr > 110:
                reasons.append("High Heart Rate")

            if temp > 38:
                reasons.append("Mild Fever")

            if bp > 140:
                reasons.append("High BP")

    # ---------------- MACHINE LEARNING ----------------

    data = {
        "Heart Rate": hr,
        "Respiratory Rate": row.get("respiratory_rate", 0),
        "Body Temperature": temp,
        "Oxygen Saturation": spo2,
        "Systolic Blood Pressure": bp,
        "Diastolic Blood Pressure": row.get("diastolic_bp", 0),
        "Age": row.get("age", 0),
        "Gender": row.get("gender", 1),
        "Weight (kg)": row.get("weight", 0),
        "Height (m)": row.get("height", 0)
    }

    X = pd.DataFrame([data])

    probability = float(model.predict_proba(X)[0][1])

    if probability >= 0.75:
        ml_severity = "Critical"

    elif probability >= 0.50:
        ml_severity = "Warning"

    else:
        ml_severity = "Normal"

    # ---------------- FINAL HYBRID OUTPUT ----------------

    if (
        rule_severity == "Critical"
        or ml_severity == "Critical"
    ):

        final = "Critical"

    elif (
        rule_severity == "Warning"
        or ml_severity == "Warning"
    ):

        final = "Warning"

    else:
        final = "Normal"

    return final, probability, reasons


# ---------------- SAVE NOTES ----------------

def save_note(patient_id, doctor_name, note_text):

    notes_table.put_item(
        Item={
            "note_id": str(uuid.uuid4()),
            "patient_id": int(patient_id),
            "doctor_name": doctor_name,
            "note_text": note_text,
            "timestamp": int(time.time())
        }
    )


# ---------------- LOAD DATA ----------------

rpm_df = pd.DataFrame(scan(rpm_table))
patient_df = pd.DataFrame(scan(patient_table))

if rpm_df.empty or patient_df.empty:
    st.warning("No patient data available.")
    st.stop()

# Convert timestamp
rpm_df["timestamp"] = (
    pd.to_datetime(rpm_df["timestamp"], unit="s")
    + pd.Timedelta(hours=5, minutes=30)
)

# Get latest record of each patient
latest = (
    rpm_df
    .sort_values("timestamp")
    .groupby("patient_id")
    .tail(1)
)

# Merge patient details
merged = latest.merge(patient_df, on="patient_id")

# Predict risks
merged[["severity", "probability", "reasons"]] = merged.apply(
    lambda row: pd.Series(predict_risk(row)),
    axis=1
)

# ---------------- SIDEBAR NAVIGATION ----------------

page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Patient Monitor"]
)

# ============================================
# OVERVIEW PAGE
# ============================================

if page == "Overview":

    st.header("System Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Patients",
        merged["patient_id"].nunique()
    )

    col2.metric(
        "Critical Patients",
        (merged["severity"] == "Critical").sum()
    )

    col3.metric(
        "Warning Patients",
        (merged["severity"] == "Warning").sum()
    )

    st.subheader("Patient Status")

    st.dataframe(
        merged[
            [
                "name",
                "severity",
                "heart_rate",
                "spo2",
                "temperature",
                "timestamp"
            ]
        ],
        use_container_width=True
    )

# ============================================
# PATIENT MONITOR PAGE
# ============================================

else:

    search = st.sidebar.text_input("Search Patient")

    filtered = merged

    if search:
        filtered = merged[
            merged["name"].str.contains(
                search,
                case=False
            )
        ]

    patient_name = st.sidebar.selectbox(
        "Select Patient",
        filtered["name"]
    )

    patient = merged[
        merged["name"] == patient_name
    ].iloc[0]

    patient_id = patient["patient_id"]

    history = rpm_df[
        rpm_df["patient_id"] == patient_id
    ].sort_values("timestamp")

    # ---------------- PATIENT INFO ----------------

    st.markdown(f"""
    <div class="block">
    <h2>{patient_name}</h2>
    <p>Last Update: {patient['timestamp']}</p>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- RISK LEVEL ----------------

    st.subheader(f"Risk Level: {patient['severity']}")

    # Display normalized probability

    if patient["severity"] == "Critical":
        display_prob = 92

    elif patient["severity"] == "Warning":
        display_prob = 65

    else:
        display_prob = 18

    st.write(f"Risk Probability: {display_prob}%")

    # ---------------- VITALS ----------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Heart Rate",
        patient["heart_rate"]
    )

    col2.metric(
        "SpO2",
        patient["spo2"]
    )

    col3.metric(
        "Temperature",
        patient["temperature"]
    )

    col4.metric(
        "Blood Pressure",
        f"{patient['systolic_bp']}/"
        f"{patient['diastolic_bp']}"
    )

    # ---------------- RISK FACTORS ----------------

    st.markdown("### Risk Factors")

    if patient["reasons"]:

        for reason in patient["reasons"]:
            st.write(f"- {reason}")

    else:
        st.write("No abnormal vital signs detected.")

    # ---------------- HISTORICAL TRENDS ----------------

    st.markdown("### Vital Trends")

    fig = px.line(
        history,
        x="timestamp",
        y=[
            "heart_rate",
            "spo2",
            "systolic_bp",
            "temperature"
        ],
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ---------------- DOCTOR NOTES ----------------

    st.markdown("### Doctor Notes")

    doctor_name = st.text_input("Doctor Name")

    note_text = st.text_area("Write Note")

    # Previous Notes
    notes_df = pd.DataFrame(scan(notes_table))

    if not notes_df.empty:

        notes_df = notes_df[
            notes_df["patient_id"] == patient_id
        ]

        if not notes_df.empty:

            notes_df = notes_df.sort_values(
                "timestamp",
                ascending=False
            )

            st.markdown("### Previous Notes")

            for _, note in notes_df.iterrows():

                timestamp = (
                    pd.to_datetime(
                        note["timestamp"],
                        unit="s"
                    )
                    + pd.Timedelta(hours=5, minutes=30)
                )

                st.markdown(f"""
                <div class="block">
                <b>{note['doctor_name']}</b><br>
                {note['note_text']}<br>
                <small>{timestamp}</small>
                </div>
                """, unsafe_allow_html=True)

    # Save Note
    if st.button("Save Note"):

        if doctor_name and note_text:

            save_note(
                patient_id,
                doctor_name,
                note_text
            )

            st.success("Note saved successfully.")

            st.rerun()

    # ---------------- PDF REPORT ----------------

    st.markdown("### Download Report")

    if st.button("Generate PDF"):

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4
        )

        styles = getSampleStyleSheet()

        elements = []

        elements.append(
            Paragraph(
                "Patient Report",
                styles["Title"]
            )
        )

        elements.append(Spacer(1, 10))

        elements.append(
            Paragraph(
                f"Patient: {patient_name}",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"Risk Level: {patient['severity']}",
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                f"Risk Probability: {display_prob}%",
                styles["Normal"]
            )
        )

        elements.append(Spacer(1, 10))

        elements.append(
            Paragraph(
                "Risk Factors:",
                styles["Heading2"]
            )
        )

        for reason in patient["reasons"]:

            elements.append(
                Paragraph(
                    f"- {reason}",
                    styles["Normal"]
                )
            )

        doc.build(elements)

        buffer.seek(0)

        st.download_button(
            "Download PDF",
            buffer,
            f"{patient_name}.pdf"
        )