import json
import boto3
import time
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

rpm_table = dynamodb.Table('rpm_data')
patient_table = dynamodb.Table('patient_info')


# --------------------------------
# Convert float -> Decimal
# --------------------------------
def to_decimal(value):

    if isinstance(value, float):
        return Decimal(str(value))

    elif isinstance(value, dict):
        return {
            k: to_decimal(v)
            for k, v in value.items()
        }

    elif isinstance(value, list):
        return [
            to_decimal(v)
            for v in value
        ]

    return value


# --------------------------------
# Validate Input
# --------------------------------
def validate_event(event):

    required_fields = [
        "patient_id",
        "heart_rate",
        "respiratory_rate",
        "temperature",
        "spo2",
        "systolic_bp",
        "diastolic_bp",
        "age",
        "gender",
        "height",
        "weight"
    ]

    missing = [
        field
        for field in required_fields
        if field not in event
    ]

    return missing


# --------------------------------
# Lambda Handler
# --------------------------------
def lambda_handler(event, context):

    try:

        print("Received event:", json.dumps(event))

        # Convert string payload to JSON
        if isinstance(event, str):
            event = json.loads(event)

        # --------------------------------
        # Validate Input
        # --------------------------------
        missing_fields = validate_event(event)

        if missing_fields:

            return {
                "statusCode": 400,
                "body": json.dumps(
                    f"Missing fields: {missing_fields}"
                )
            }

        # --------------------------------
        # Extract Values
        # --------------------------------
        patient_id = int(event["patient_id"])

        timestamp = int(
            event.get("timestamp", time.time())
        )

        heart_rate = float(event["heart_rate"])

        respiratory_rate = float(
            event["respiratory_rate"]
        )

        temperature = float(event["temperature"])

        spo2 = float(event["spo2"])

        systolic_bp = float(event["systolic_bp"])

        diastolic_bp = float(
            event["diastolic_bp"]
        )

        age = int(event["age"])

        gender = int(event["gender"])

        height = float(event["height"])

        weight = float(event["weight"])

        # --------------------------------
        # Basic Rule-Based Risk Check
        # --------------------------------
        if (
            spo2 < 90
            or systolic_bp > 160
            or heart_rate > 130
        ):

            risk_flag = True

        else:

            risk_flag = False

        # --------------------------------
        # Store Dynamic Vitals
        # --------------------------------
        rpm_item = {

            "patient_id": patient_id,
            "timestamp": timestamp,

            "heart_rate": heart_rate,
            "respiratory_rate": respiratory_rate,
            "temperature": temperature,
            "spo2": spo2,

            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,

            "risk_flag": risk_flag
        }

        rpm_table.put_item(
            Item=to_decimal(rpm_item)
        )

        print(
            f"Vitals stored for patient_id: "
            f"{patient_id}"
        )

        # --------------------------------
        # Store Static Patient Info
        # --------------------------------
        response = patient_table.get_item(
            Key={
                "patient_id": patient_id
            }
        )

        # Create patient if not exists
        if "Item" not in response:

            print(
                "Creating new patient record..."
            )

            patient_item = {

                "patient_id": patient_id,

                "name": event.get(
                    "name",
                    f"Patient {patient_id}"
                ),

                "age": age,
                "gender": gender,

                "height": height,
                "weight": weight
            }

            patient_table.put_item(
                Item=to_decimal(patient_item)
            )

        # --------------------------------
        # Success Response
        # --------------------------------
        return {

            "statusCode": 200,

            "body": json.dumps({

                "message":
                "Data processed successfully",

                "patient_id": patient_id,

                "risk_flag": risk_flag
            })
        }

    except Exception as e:

        print("Error:", str(e))

        return {

            "statusCode": 500,

            "body": json.dumps({
                "error": str(e)
            })
        }