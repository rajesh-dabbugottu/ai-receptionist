from firebase_admin import firestore

from firebase_service import db


def create_appointment(
    business_id: str,
    conversation_id: str,
    customer_name: str,
    customer_phone: str,
    service: str,
    appointment_date: str,
    appointment_time: str
) -> str:
    appointment_data = {
        "business_id": business_id,
        "conversation_id": conversation_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "service": service,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": "pending",
        "source": "website",
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }

    appointment_reference = (
        db.collection("appointments")
        .add(appointment_data)
    )

    return appointment_reference[1].id