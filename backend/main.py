from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore
from pydantic import BaseModel, Field, field_validator

from ai_service import generate_ai_reply
from firebase_service import db
from fastapi.middleware.cors import CORSMiddleware


DEFAULT_BUSINESS_ID = "demo_business_001"

app = FastAPI(
    title="AI Receptionist API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:4201",
        "http://127.0.0.1:4201",
        "https://ai-receptionist-1-g606.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
         "https://ai-receptionist-1-g606.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Pydantic models
# =========================================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    business_id: str = DEFAULT_BUSINESS_ID

    @field_validator("message", "business_id")
    @classmethod
    def clean_required_chat_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value


class AppointmentRequest(BaseModel):
    business_id: str = DEFAULT_BUSINESS_ID
    conversation_id: Optional[str] = None

    customer_name: str = Field(min_length=2, max_length=100)
    customer_phone: str = Field(min_length=7, max_length=30)
    customer_email: Optional[str] = Field(default=None, max_length=150)

    service: str = Field(min_length=2, max_length=100)
    appointment_date: str
    appointment_time: str

    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator(
        "business_id",
        "customer_name",
        "customer_phone",
        "service",
        "appointment_date",
        "appointment_time",
    )
    @classmethod
    def clean_required_appointment_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("customer_email", "notes", "conversation_id")
    @classmethod
    def clean_optional_appointment_text(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("appointment_date")
    @classmethod
    def validate_appointment_date(cls, value: str) -> str:
        try:
            selected_date = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                "Appointment date must use YYYY-MM-DD format."
            ) from error

        if selected_date < date.today():
            raise ValueError(
                "Appointment date cannot be in the past."
            )

        return value

    @field_validator("appointment_time")
    @classmethod
    def validate_appointment_time(cls, value: str) -> str:
        validate_time_string(value)
        return value


class AppointmentStatusRequest(BaseModel):
    status: Literal[
        "pending",
        "confirmed",
        "cancelled",
        "completed",
    ]


class WorkingDay(BaseModel):
    open: bool = True
    start: Optional[str] = "09:00"
    end: Optional[str] = "18:00"

    @field_validator("start", "end")
    @classmethod
    def validate_working_time(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()
        validate_time_string(value)
        return value


class WorkingHours(BaseModel):
    monday: WorkingDay
    tuesday: WorkingDay
    wednesday: WorkingDay
    thursday: WorkingDay
    friday: WorkingDay
    saturday: WorkingDay
    sunday: WorkingDay


class BusinessSettingsRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    business_type: str = Field(min_length=2, max_length=150)

    address: Optional[str] = Field(default=None, max_length=300)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=150)
    website: Optional[str] = Field(default=None, max_length=200)

    timezone: str = Field(
        default="Europe/London",
        min_length=2,
        max_length=100,
    )

    welcome_message: str = Field(
        default="Welcome. How can I help you?",
        min_length=2,
        max_length=500,
    )

    booking_message: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    working_hours: WorkingHours

    @field_validator(
        "business_name",
        "business_type",
        "timezone",
        "welcome_message",
    )
    @classmethod
    def clean_required_business_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator(
        "address",
        "phone",
        "email",
        "website",
        "booking_message",
    )
    @classmethod
    def clean_optional_business_text(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ServiceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    active: bool = True

    @field_validator("name")
    @classmethod
    def clean_service_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Service name is required.")
        return value

    @field_validator("description")
    @classmethod
    def clean_service_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ServiceStatusRequest(BaseModel):
    active: bool

class CustomerRequest(BaseModel):
    business_id: str = DEFAULT_BUSINESS_ID

    name: str = Field(
        min_length=2,
        max_length=100,
    )

    phone: str = Field(
        min_length=7,
        max_length=30,
    )

    email: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
    )

    @field_validator(
        "business_id",
        "name",
        "phone",
    )
    @classmethod
    def clean_required_customer_text(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "This field is required."
            )

        return value

    @field_validator(
        "email",
        "notes",
    )
    @classmethod
    def clean_optional_customer_text(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()

        return value or None

# =========================================================
# Helpers
# =========================================================

def validate_time_string(value: str) -> None:
    if len(value) != 5 or value[2] != ":":
        raise ValueError("Time must use HH:MM format.")

    try:
        hour = int(value[:2])
        minute = int(value[3:])
    except ValueError as error:
        raise ValueError("Time must use HH:MM format.") from error

    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 00 and 23.")

    if not 0 <= minute <= 59:
        raise ValueError("Minute must be between 00 and 59.")


def serialize_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def get_default_working_hours() -> dict[str, dict[str, Any]]:
    return {
        "monday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "tuesday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "wednesday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "thursday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "friday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "saturday": {
            "open": True,
            "start": "09:00",
            "end": "18:00",
        },
        "sunday": {
            "open": False,
            "start": None,
            "end": None,
        },
    }


def get_default_business_data(
    business_id: str,
) -> dict[str, Any]:
    return {
        "business_id": business_id,
        "business_name": "Demo Salon",
        "business_type": "Hair and beauty salon",
        "address": "London",
        "phone": "",
        "email": "",
        "website": "",
        "timezone": "Europe/London",
        "welcome_message": (
            "Welcome to Demo Salon. How can I help you?"
        ),
        "booking_message": (
            "Your appointment request will remain pending "
            "until reviewed by the business."
        ),
        "working_hours": get_default_working_hours(),
    }


def create_appointment_record(
    *,
    business_id: str,
    conversation_id: Optional[str],
    customer_name: str,
    customer_phone: str,
    customer_email: Optional[str],
    service: str,
    appointment_date: str,
    appointment_time: str,
    notes: Optional[str],
    source: str,
) -> str:
    customer_id = create_or_update_customer(
        business_id=business_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        appointment_date=appointment_date,
    )

    appointment_ref = (
        db.collection("appointments")
        .document()
    )

    appointment_ref.set({
        "business_id": business_id,
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "service": service,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "notes": notes,
        "status": "pending",
        "source": source,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    (
        db.collection("customers")
        .document(customer_id)
        .set(
            {
                "last_appointment_id": (
                    appointment_ref.id
                ),
                "updated_at": (
                    firestore.SERVER_TIMESTAMP
                ),
            },
            merge=True,
        )
    )

    return appointment_ref.id


def normalize_phone_number(
    phone: str,
) -> str:
    """
    Normalize a phone number for customer matching.

    Examples:

    +44 7700 900123 -> +447700900123
    07700-900-123   -> 07700900123
    """

    phone = phone.strip()

    normalized_characters: list[str] = []

    for index, character in enumerate(phone):
        if character.isdigit():
            normalized_characters.append(
                character
            )

        elif character == "+" and index == 0:
            normalized_characters.append(
                character
            )

    return "".join(
        normalized_characters
    )


def serialize_customer_document(
    customer_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": customer_id,
        "business_id": data.get(
            "business_id"
        ),
        "name": data.get(
            "name",
            "Unknown customer",
        ),
        "phone": data.get(
            "phone",
            "",
        ),
        "email": data.get(
            "email"
        ),
        "notes": data.get(
            "notes"
        ),
        "total_appointments": data.get(
            "total_appointments",
            0,
        ),
        "last_appointment_date": data.get(
            "last_appointment_date"
        ),
        "last_appointment_id": data.get(
            "last_appointment_id"
        ),
        "created_at": serialize_timestamp(
            data.get("created_at")
        ),
        "updated_at": serialize_timestamp(
            data.get("updated_at")
        ),
    }


def find_customer_by_phone(
    *,
    business_id: str,
    customer_phone: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    normalized_phone = normalize_phone_number(
        customer_phone
    )

    if not normalized_phone:
        return None

    customer_documents = (
        db.collection("customers")
        .where(
            filter=firestore.FieldFilter(
                "business_id",
                "==",
                business_id,
            )
        )
        .where(
            filter=firestore.FieldFilter(
                "normalized_phone",
                "==",
                normalized_phone,
            )
        )
        .limit(1)
        .stream()
    )

    for document in customer_documents:
        return (
            document.id,
            document.to_dict() or {},
        )

    return None


def create_or_update_customer(
    *,
    business_id: str,
    customer_name: str,
    customer_phone: str,
    customer_email: Optional[str],
    appointment_date: str,
) -> str:
    normalized_phone = normalize_phone_number(
        customer_phone
    )

    existing_customer = find_customer_by_phone(
        business_id=business_id,
        customer_phone=customer_phone,
    )

    if existing_customer:
        customer_id, customer_data = (
            existing_customer
        )

        customer_ref = (
            db.collection("customers")
            .document(customer_id)
        )

        existing_total = int(
            customer_data.get(
                "total_appointments",
                0,
            )
        )

        update_data: dict[str, Any] = {
            "name": customer_name,
            "phone": customer_phone,
            "normalized_phone": normalized_phone,
            "total_appointments": (
                existing_total + 1
            ),
            "last_appointment_date": (
                appointment_date
            ),
            "updated_at": (
                firestore.SERVER_TIMESTAMP
            ),
        }

        if customer_email:
            update_data["email"] = (
                customer_email
            )

        customer_ref.set(
            update_data,
            merge=True,
        )

        return customer_id

    customer_ref = (
        db.collection("customers")
        .document()
    )

    customer_ref.set({
        "business_id": business_id,
        "name": customer_name,
        "phone": customer_phone,
        "normalized_phone": normalized_phone,
        "email": customer_email,
        "notes": None,
        "total_appointments": 1,
        "last_appointment_date": (
            appointment_date
        ),
        "last_appointment_id": None,
        "created_at": (
            firestore.SERVER_TIMESTAMP
        ),
        "updated_at": (
            firestore.SERVER_TIMESTAMP
        ),
    })

    return customer_ref.id
def get_conversation_history(
    conversation_id: str,
    limit: int = 20,
) -> list[dict[str, str]]:
    messages_ref = (
        db.collection("conversations")
        .document(conversation_id)
        .collection("messages")
    )

    documents = (
        messages_ref
        .order_by(
            "created_at",
            direction=firestore.Query.DESCENDING,
        )
        .limit(limit)
        .stream()
    )

    history: list[dict[str, str]] = []

    for document in documents:
        data = document.to_dict() or {}
        sender = data.get("sender")
        message_text = data.get("message", "")

        if sender == "customer":
            role = "user"
        elif sender == "receptionist":
            role = "assistant"
        else:
            continue

        history.append({
            "role": role,
            "content": message_text,
        })

    history.reverse()
    return history


# =========================================================
# Base routes
# =========================================================

@app.get("/")
def home() -> dict[str, str]:
    return {
        "message": "Welcome to AI Receptionist API",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "running",
        "service": "AI Receptionist Backend",
        "firebase": "connected",
        "ai": "configured",
    }


# =========================================================
# Chat
# =========================================================

@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    user_message = request.message.strip()
    business_id = request.business_id.strip()
    conversation_id = (
        request.conversation_id.strip()
        if request.conversation_id
        else str(uuid4())
    )

    conversation_ref = (
        db.collection("conversations")
        .document(conversation_id)
    )

    try:
        conversation_snapshot = conversation_ref.get()

        if not conversation_snapshot.exists:
            conversation_ref.set({
                "conversation_id": conversation_id,
                "business_id": business_id,
                "source": "website",
                "status": "active",
                "appointment_created": False,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            })

        refreshed_snapshot = conversation_ref.get()
        conversation_data = (
            refreshed_snapshot.to_dict() or {}
            if refreshed_snapshot.exists
            else {}
        )

        conversation_history = get_conversation_history(
            conversation_id=conversation_id,
        )
        business_settings = (
    load_business_settings(
        business_id
    )
)
        active_services = load_active_services(
    business_id
)

        # This matches your existing ai_service.py interface.
        ai_result = generate_ai_reply(
user_message=user_message,
    conversation_history=conversation_history,
    business_settings=business_settings,
    services=active_services
        )

        reply = ai_result.reply
        appointment_id: Optional[str] = None
        appointment_created = False

        already_created = bool(
            conversation_data.get(
                "appointment_created",
                False,
            )
        )

        if ai_result.booking_ready and not already_created:
            required_fields = [
                ai_result.customer_name,
                ai_result.customer_phone,
                ai_result.service,
                ai_result.appointment_date,
                ai_result.appointment_time,
            ]

            if all(required_fields):
                appointment_id = create_appointment_record(
                    business_id=business_id,
                    conversation_id=conversation_id,
                    customer_name=ai_result.customer_name,
                    customer_phone=ai_result.customer_phone,
                    customer_email=None,
                    service=ai_result.service,
                    appointment_date=ai_result.appointment_date,
                    appointment_time=ai_result.appointment_time,
                    notes=None,
                    source="ai_chat",
                )

                appointment_created = True

                reply = (
                    f"{reply} Your appointment request reference "
                    f"is {appointment_id}."
                )

        messages_ref = conversation_ref.collection("messages")

        messages_ref.add({
            "sender": "customer",
            "message": user_message,
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        messages_ref.add({
            "sender": "receptionist",
            "message": reply,
            "intent": ai_result.intent,
            "booking_ready": ai_result.booking_ready,
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        conversation_update: dict[str, Any] = {
            "business_id": business_id,
            "last_message": reply,
            "intent": ai_result.intent,
            "customer_name": ai_result.customer_name,
            "customer_phone": ai_result.customer_phone,
            "requested_service": ai_result.service,
            "requested_date": ai_result.appointment_date,
            "requested_time": ai_result.appointment_time,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        if appointment_created:
            conversation_update.update({
                "appointment_created": True,
                "appointment_id": appointment_id,
                "status": "appointment_pending",
            })

        conversation_ref.set(
            conversation_update,
            merge=True,
        )

        return {
            "reply": reply,
            "conversation_id": conversation_id,
            "intent": ai_result.intent,
            "booking_ready": ai_result.booking_ready,
            "appointment_created": appointment_created,
            "appointment_id": appointment_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Chat error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=f"{type(error).__name__}: {error}",
        ) from error


# =========================================================
# Appointments
# =========================================================

@app.post("/api/appointments", status_code=201)
def book_appointment(
    appointment: AppointmentRequest,
) -> dict[str, Any]:
    try:
        appointment_id = create_appointment_record(
            business_id=appointment.business_id,
            conversation_id=appointment.conversation_id,
            customer_name=appointment.customer_name,
            customer_phone=appointment.customer_phone,
            customer_email=appointment.customer_email,
            service=appointment.service,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            notes=appointment.notes,
            source="booking_form",
        )

        return {
            "success": True,
            "message": "Appointment booked successfully.",
            "appointment_id": appointment_id,
            "status": "pending",
        }

    except Exception as error:
        print(
            "Create appointment error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Appointment could not be booked.",
        ) from error


@app.get("/api/appointments")
def get_appointments(
    business_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    try:
        documents = db.collection("appointments").stream()
        appointments: list[dict[str, Any]] = []

        for document in documents:
            data = document.to_dict() or {}

            if (
                business_id
                and data.get("business_id") != business_id
            ):
                continue

            appointments.append({
                "id": document.id,
                "customer_id": data.get(
    "customer_id"
),
                "business_id": data.get("business_id"),
                "conversation_id": data.get("conversation_id"),
                "customer_name": data.get(
                    "customer_name",
                    "Unknown customer",
                ),
                "customer_phone": data.get("customer_phone", ""),
                "customer_email": data.get("customer_email"),
                "service": data.get("service", ""),
                "appointment_date": data.get(
                    "appointment_date",
                    "",
                ),
                "appointment_time": data.get(
                    "appointment_time",
                    "",
                ),
                "notes": data.get("notes"),
                "status": data.get("status", "pending"),
                "source": data.get("source", "website"),
                "created_at": serialize_timestamp(
                    data.get("created_at")
                ),
                "updated_at": serialize_timestamp(
                    data.get("updated_at")
                ),
            })

        appointments.sort(
            key=lambda item: (
                item.get("appointment_date", ""),
                item.get("appointment_time", ""),
            )
        )

        return {
            "appointments": appointments,
            "total": len(appointments),
        }

    except Exception as error:
        print(
            "Get appointments error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Appointments could not be loaded.",
        ) from error


@app.get("/api/appointments/{appointment_id}")
def get_appointment(
    appointment_id: str,
) -> dict[str, Any]:
    try:
        snapshot = (
            db.collection("appointments")
            .document(appointment_id)
            .get()
        )

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found.",
            )

        data = snapshot.to_dict() or {}

        return {
            "id": snapshot.id,
            **{
                key: serialize_timestamp(value)
                if key in {"created_at", "updated_at"}
                else value
                for key, value in data.items()
            },
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Get appointment error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Appointment could not be loaded.",
        ) from error


@app.patch("/api/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: str,
    request: AppointmentStatusRequest,
) -> dict[str, Any]:
    try:
        appointment_ref = (
            db.collection("appointments")
            .document(appointment_id)
        )

        snapshot = appointment_ref.get()

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found.",
            )

        appointment_ref.update({
            "status": request.status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

        appointment_data = snapshot.to_dict() or {}
        conversation_id = appointment_data.get("conversation_id")

        if conversation_id:
            conversation_status = {
                "pending": "appointment_pending",
                "confirmed": "appointment_confirmed",
                "cancelled": "appointment_cancelled",
                "completed": "completed",
            }[request.status]

            (
                db.collection("conversations")
                .document(conversation_id)
                .set(
                    {
                        "status": conversation_status,
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    },
                    merge=True,
                )
            )

        return {
            "success": True,
            "message": "Appointment status updated.",
            "appointment_id": appointment_id,
            "status": request.status,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Update appointment error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Appointment status could not be updated.",
        ) from error


# =========================================================
# Conversations
# =========================================================

@app.get("/api/conversations")
def get_conversations(
    business_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    try:
        documents = db.collection("conversations").stream()
        conversations: list[dict[str, Any]] = []

        for document in documents:
            data = document.to_dict() or {}

            if (
                business_id
                and data.get("business_id") != business_id
            ):
                continue

            conversations.append({
                "conversation_id": document.id,
                "business_id": data.get("business_id"),
                "customer_name": data.get(
                    "customer_name",
                    "Website Visitor",
                ),
                "customer_phone": data.get("customer_phone"),
                "last_message": data.get(
                    "last_message",
                    "No messages available",
                ),
                "status": data.get("status", "active"),
                "intent": data.get("intent", "unknown"),
                "appointment_created": data.get(
                    "appointment_created",
                    False,
                ),
                "appointment_id": data.get("appointment_id"),
                "created_at": serialize_timestamp(
                    data.get("created_at")
                ),
                "updated_at": serialize_timestamp(
                    data.get("updated_at")
                ),
            })

        conversations.sort(
            key=lambda item: item.get("updated_at") or "",
            reverse=True,
        )

        return {
            "conversations": conversations,
            "total": len(conversations),
        }

    except Exception as error:
        print(
            "Get conversations error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Conversations could not be loaded.",
        ) from error


@app.get("/api/conversations/{conversation_id}")
def get_conversation_details(
    conversation_id: str,
) -> dict[str, Any]:
    try:
        conversation_ref = (
            db.collection("conversations")
            .document(conversation_id)
        )

        snapshot = conversation_ref.get()

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        data = snapshot.to_dict() or {}
        messages: list[dict[str, Any]] = []

        message_documents = (
            conversation_ref
            .collection("messages")
            .stream()
        )

        for document in message_documents:
            message_data = document.to_dict() or {}

            messages.append({
                "id": document.id,
                "sender": message_data.get(
                    "sender",
                    message_data.get("role", "unknown"),
                ),
                "message": message_data.get(
                    "message",
                    message_data.get("content", ""),
                ),
                "intent": message_data.get("intent"),
                "booking_ready": message_data.get(
                    "booking_ready",
                    False,
                ),
                "created_at": serialize_timestamp(
                    message_data.get("created_at")
                ),
            })

        messages.sort(
            key=lambda item: item.get("created_at") or ""
        )

        return {
            "conversation_id": conversation_id,
            "business_id": data.get("business_id"),
            "customer_name": data.get(
                "customer_name",
                "Website Visitor",
            ),
            "customer_phone": data.get("customer_phone"),
            "status": data.get("status", "active"),
            "intent": data.get("intent", "unknown"),
            "appointment_created": data.get(
                "appointment_created",
                False,
            ),
            "appointment_id": data.get("appointment_id"),
            "created_at": serialize_timestamp(
                data.get("created_at")
            ),
            "updated_at": serialize_timestamp(
                data.get("updated_at")
            ),
            "messages": messages,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Get conversation details error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail="Conversation could not be loaded.",
        ) from error


# =========================================================
# Business settings
# =========================================================

@app.get("/api/business-settings/{business_id}")
def get_business_settings(
    business_id: str,
) -> dict[str, Any]:
    try:
        business_ref = (
            db.collection("businesses")
            .document(business_id)
        )

        snapshot = business_ref.get()

        if not snapshot.exists:
            default_data = get_default_business_data(
                business_id
            )

            business_ref.set({
                **default_data,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            })

            return {
                **default_data,
                "created_at": None,
                "updated_at": None,
            }

        data = snapshot.to_dict() or {}
        default_data = get_default_business_data(business_id)

        return {
            "business_id": business_id,
            "business_name": data.get(
                "business_name",
                default_data["business_name"],
            ),
            "business_type": data.get(
                "business_type",
                default_data["business_type"],
            ),
            "address": data.get("address", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            "website": data.get("website", ""),
            "timezone": data.get(
                "timezone",
                default_data["timezone"],
            ),
            "welcome_message": data.get(
                "welcome_message",
                default_data["welcome_message"],
            ),
            "booking_message": data.get(
                "booking_message",
                default_data["booking_message"],
            ),
            "working_hours": data.get(
                "working_hours",
                get_default_working_hours(),
            ),
            "created_at": serialize_timestamp(
                data.get("created_at")
            ),
            "updated_at": serialize_timestamp(
                data.get("updated_at")
            ),
        }

    except Exception as error:
        print(
            "Get business settings error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@app.put("/api/business-settings/{business_id}")
def update_business_settings(
    business_id: str,
    request: BusinessSettingsRequest,
) -> dict[str, Any]:
    try:
        business_ref = (
            db.collection("businesses")
            .document(business_id)
        )

        snapshot = business_ref.get()

        business_data: dict[str, Any] = {
            "business_id": business_id,
            "business_name": request.business_name,
            "business_type": request.business_type,
            "address": request.address,
            "phone": request.phone,
            "email": request.email,
            "website": request.website,
            "timezone": request.timezone,
            "welcome_message": request.welcome_message,
            "booking_message": request.booking_message,
            "working_hours": (
                request.working_hours.model_dump()
            ),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        if not snapshot.exists:
            business_data["created_at"] = (
                firestore.SERVER_TIMESTAMP
            )

        business_ref.set(
            business_data,
            merge=True,
        )

        return {
            "success": True,
            "message": (
                "Business settings saved successfully."
            ),
            "business_id": business_id,
        }

    except Exception as error:
        print(
            "Update business settings error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


# =========================================================
# Business services
# =========================================================

@app.get(
    "/api/business-settings/{business_id}/services"
)
def get_business_services(
    business_id: str,
    include_inactive: bool = True,
) -> dict[str, Any]:
    try:
        documents = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
            .stream()
        )

        services: list[dict[str, Any]] = []

        for document in documents:
            data = document.to_dict() or {}
            active = data.get("active", True)

            if not include_inactive and not active:
                continue

            services.append({
                "id": document.id,
                "name": data.get("name", ""),
                "description": data.get("description"),
                "duration_minutes": data.get(
                    "duration_minutes",
                    60,
                ),
                "active": active,
                "created_at": serialize_timestamp(
                    data.get("created_at")
                ),
                "updated_at": serialize_timestamp(
                    data.get("updated_at")
                ),
            })

        services.sort(
            key=lambda item: item.get("name", "").lower()
        )

        return {
            "services": services,
            "total": len(services),
        }

    except Exception as error:
        print(
            "Get services error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@app.post(
    "/api/business-settings/{business_id}/services",
    status_code=201,
)
def create_business_service(
    business_id: str,
    request: ServiceRequest,
) -> dict[str, Any]:
    try:
        services_ref = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
        )

        normalized_name = request.name.strip().lower()

        duplicate_documents = (
            services_ref
            .where(
                filter=firestore.FieldFilter(
                    "normalized_name",
                    "==",
                    normalized_name,
                )
            )
            .limit(1)
            .stream()
        )

        if any(duplicate_documents):
            raise HTTPException(
                status_code=409,
                detail=(
                    "A service with this name already exists."
                ),
            )

        service_ref = services_ref.document()

        service_ref.set({
            "name": request.name,
            "normalized_name": normalized_name,
            "description": request.description,
            "duration_minutes": request.duration_minutes,
            "active": request.active,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

        return {
            "success": True,
            "message": "Service created successfully.",
            "service_id": service_ref.id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Create service error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@app.put(
    "/api/business-settings/{business_id}/services/{service_id}"
)
def update_business_service(
    business_id: str,
    service_id: str,
    request: ServiceRequest,
) -> dict[str, Any]:
    try:
        service_ref = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
            .document(service_id)
        )

        snapshot = service_ref.get()

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Service not found.",
            )

        normalized_name = request.name.strip().lower()

        duplicate_documents = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
            .where(
                filter=firestore.FieldFilter(
                    "normalized_name",
                    "==",
                    normalized_name,
                )
            )
            .stream()
        )

        for duplicate in duplicate_documents:
            if duplicate.id != service_id:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "A service with this name "
                        "already exists."
                    ),
                )

        service_ref.update({
            "name": request.name,
            "normalized_name": normalized_name,
            "description": request.description,
            "duration_minutes": request.duration_minutes,
            "active": request.active,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

        return {
            "success": True,
            "message": "Service updated successfully.",
            "service_id": service_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Update service error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@app.patch(
    "/api/business-settings/{business_id}/services/"
    "{service_id}/status"
)
def update_service_status(
    business_id: str,
    service_id: str,
    request: ServiceStatusRequest,
) -> dict[str, Any]:
    try:
        service_ref = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
            .document(service_id)
        )

        snapshot = service_ref.get()

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Service not found.",
            )

        service_ref.update({
            "active": request.active,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

        return {
            "success": True,
            "message": "Service status updated.",
            "service_id": service_id,
            "active": request.active,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Update service status error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@app.delete(
    "/api/business-settings/{business_id}/services/{service_id}"
)
def delete_business_service(
    business_id: str,
    service_id: str,
) -> dict[str, Any]:
    try:
        service_ref = (
            db.collection("businesses")
            .document(business_id)
            .collection("services")
            .document(service_id)
        )

        snapshot = service_ref.get()

        if not snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Service not found.",
            )

        service_ref.delete()

        return {
            "success": True,
            "message": "Service deleted successfully.",
            "service_id": service_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Delete service error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
def load_business_settings(
    business_id: str
) -> dict:
    business_ref = (
        db.collection("businesses")
        .document(business_id)
    )

    snapshot = business_ref.get()

    if not snapshot.exists:
        return get_default_business_data(
            business_id
        )

    return snapshot.to_dict() or {}

def load_active_services(
    business_id: str
) -> list[dict]:
    services_ref = (
        db.collection("businesses")
        .document(business_id)
        .collection("services")
    )

    documents = services_ref.stream()

    services = []

    for document in documents:
        data = document.to_dict() or {}

        if not data.get("active", True):
            continue

        services.append({
            "id": document.id,
            "name": data.get("name", ""),
            "description": data.get(
                "description",
                ""
            ),
            "duration_minutes": data.get(
                "duration_minutes",
                60
            ),
            "active": True
        })

    return services
# =========================================================
# Customers
# =========================================================

@app.get("/api/customers")
def get_customers(
    business_id: str = Query(
        default=DEFAULT_BUSINESS_ID
    ),
    search: Optional[str] = Query(
        default=None
    ),
) -> dict[str, Any]:
    try:
        customer_documents = (
            db.collection("customers")
            .stream()
        )

        customers: list[dict[str, Any]] = []

        search_value = (
            search.strip().lower()
            if search
            else None
        )

        for document in customer_documents:
            data = document.to_dict() or {}

            if (
                data.get("business_id")
                != business_id
            ):
                continue

            customer = serialize_customer_document(
                customer_id=document.id,
                data=data,
            )

            if search_value:
                searchable_text = " ".join([
                    str(
                        customer.get(
                            "name",
                            "",
                        )
                    ),
                    str(
                        customer.get(
                            "phone",
                            "",
                        )
                    ),
                    str(
                        customer.get(
                            "email",
                            "",
                        )
                    ),
                ]).lower()

                if search_value not in searchable_text:
                    continue

            customers.append(
                customer
            )

        customers.sort(
            key=lambda customer: (
                customer.get(
                    "updated_at"
                )
                or ""
            ),
            reverse=True,
        )

        return {
            "customers": customers,
            "total": len(customers),
        }

    except Exception as error:
        print(
            "Get customers error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Customers could not be loaded."
            ),
        ) from error


@app.post(
    "/api/customers",
    status_code=201,
)
def create_customer(
    request: CustomerRequest,
) -> dict[str, Any]:
    try:
        existing_customer = (
            find_customer_by_phone(
                business_id=request.business_id,
                customer_phone=request.phone,
            )
        )

        if existing_customer:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A customer with this phone "
                    "number already exists."
                ),
            )

        customer_ref = (
            db.collection("customers")
            .document()
        )

        customer_ref.set({
            "business_id": request.business_id,
            "name": request.name,
            "phone": request.phone,
            "normalized_phone": (
                normalize_phone_number(
                    request.phone
                )
            ),
            "email": request.email,
            "notes": request.notes,
            "total_appointments": 0,
            "last_appointment_date": None,
            "last_appointment_id": None,
            "created_at": (
                firestore.SERVER_TIMESTAMP
            ),
            "updated_at": (
                firestore.SERVER_TIMESTAMP
            ),
        })

        return {
            "success": True,
            "message": (
                "Customer created successfully."
            ),
            "customer_id": customer_ref.id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Create customer error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Customer could not be created."
            ),
        ) from error


@app.get("/api/customers/{customer_id}")
def get_customer(
    customer_id: str,
) -> dict[str, Any]:
    try:
        customer_ref = (
            db.collection("customers")
            .document(customer_id)
        )

        customer_snapshot = (
            customer_ref.get()
        )

        if not customer_snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        customer_data = (
            customer_snapshot.to_dict()
            or {}
        )

        appointments: list[
            dict[str, Any]
        ] = []

        appointment_documents = (
            db.collection("appointments")
            .where(
                filter=firestore.FieldFilter(
                    "customer_id",
                    "==",
                    customer_id,
                )
            )
            .stream()
        )

        for appointment_document in (
            appointment_documents
        ):
            appointment_data = (
                appointment_document.to_dict()
                or {}
            )

            appointments.append({
                "id": appointment_document.id,
                "service": (
                    appointment_data.get(
                        "service",
                        "",
                    )
                ),
                "appointment_date": (
                    appointment_data.get(
                        "appointment_date",
                        "",
                    )
                ),
                "appointment_time": (
                    appointment_data.get(
                        "appointment_time",
                        "",
                    )
                ),
                "status": (
                    appointment_data.get(
                        "status",
                        "pending",
                    )
                ),
                "source": (
                    appointment_data.get(
                        "source",
                        "",
                    )
                ),
                "conversation_id": (
                    appointment_data.get(
                        "conversation_id"
                    )
                ),
                "created_at": (
                    serialize_timestamp(
                        appointment_data.get(
                            "created_at"
                        )
                    )
                ),
            })

        appointments.sort(
            key=lambda appointment: (
                appointment.get(
                    "appointment_date",
                    "",
                ),
                appointment.get(
                    "appointment_time",
                    "",
                ),
            ),
            reverse=True,
        )

        return {
            "customer": (
                serialize_customer_document(
                    customer_id=customer_id,
                    data=customer_data,
                )
            ),
            "appointments": appointments,
            "total_appointments": (
                len(appointments)
            ),
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Get customer error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Customer could not be loaded."
            ),
        ) from error


@app.put("/api/customers/{customer_id}")
def update_customer(
    customer_id: str,
    request: CustomerRequest,
) -> dict[str, Any]:
    try:
        customer_ref = (
            db.collection("customers")
            .document(customer_id)
        )

        customer_snapshot = (
            customer_ref.get()
        )

        if not customer_snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        duplicate_customer = (
            find_customer_by_phone(
                business_id=request.business_id,
                customer_phone=request.phone,
            )
        )

        if (
            duplicate_customer
            and duplicate_customer[0]
            != customer_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another customer already uses "
                    "this phone number."
                ),
            )

        customer_ref.set(
            {
                "business_id": (
                    request.business_id
                ),
                "name": request.name,
                "phone": request.phone,
                "normalized_phone": (
                    normalize_phone_number(
                        request.phone
                    )
                ),
                "email": request.email,
                "notes": request.notes,
                "updated_at": (
                    firestore.SERVER_TIMESTAMP
                ),
            },
            merge=True,
        )

        return {
            "success": True,
            "message": (
                "Customer updated successfully."
            ),
            "customer_id": customer_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Update customer error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Customer could not be updated."
            ),
        ) from error


@app.delete("/api/customers/{customer_id}")
def delete_customer(
    customer_id: str,
) -> dict[str, Any]:
    try:
        customer_ref = (
            db.collection("customers")
            .document(customer_id)
        )

        customer_snapshot = (
            customer_ref.get()
        )

        if not customer_snapshot.exists:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        appointment_documents = (
            db.collection("appointments")
            .where(
                filter=firestore.FieldFilter(
                    "customer_id",
                    "==",
                    customer_id,
                )
            )
            .limit(1)
            .stream()
        )

        if any(appointment_documents):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This customer has appointment "
                    "history and cannot be deleted."
                ),
            )

        customer_ref.delete()

        return {
            "success": True,
            "message": (
                "Customer deleted successfully."
            ),
            "customer_id": customer_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            "Delete customer error:",
            type(error).__name__,
            str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Customer could not be deleted."
            ),
        ) from error
