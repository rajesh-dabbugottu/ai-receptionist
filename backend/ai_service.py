import os
from datetime import datetime
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


# ---------------------------------------------------------
# Environment and OpenAI client
# ---------------------------------------------------------

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is missing from backend/.env"
    )


client = OpenAI(api_key=api_key)


# ---------------------------------------------------------
# Structured AI response
# ---------------------------------------------------------

class AIReceptionistResult(BaseModel):
    reply: str

    intent: Literal[
        "general_question",
        "book_appointment",
        "cancel_appointment",
        "reschedule_appointment",
        "unknown",
    ]

    booking_ready: bool = False

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None


# ---------------------------------------------------------
# Dynamic service formatting
# ---------------------------------------------------------

def build_services_text(
    services: list[dict[str, Any]],
) -> str:
    if not services:
        return "No active services are currently configured."

    service_lines: list[str] = []

    for service in services:
        if not service.get("active", True):
            continue

        name = str(
            service.get("name", "")
        ).strip()

        description = str(
            service.get("description", "")
        ).strip()

        duration = service.get(
            "duration_minutes"
        )

        if not name:
            continue

        line = f"- {name}"

        if description:
            line += f": {description}"

        if duration:
            line += f" Duration: {duration} minutes."

        service_lines.append(line)

    if not service_lines:
        return "No active services are currently configured."

    return "\n".join(service_lines)


# ---------------------------------------------------------
# Dynamic working-hours formatting
# ---------------------------------------------------------

def build_working_hours_text(
    working_hours: dict[str, Any],
) -> str:
    if not working_hours:
        return "Working hours are not available."

    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    lines: list[str] = []

    for day in days:
        details = working_hours.get(day, {})

        if not isinstance(details, dict):
            lines.append(
                f"- {day.title()}: Closed"
            )
            continue

        is_open = details.get("open", False)

        if not is_open:
            lines.append(
                f"- {day.title()}: Closed"
            )
            continue

        start = details.get(
            "start",
            "Not provided",
        )

        end = details.get(
            "end",
            "Not provided",
        )

        lines.append(
            f"- {day.title()}: {start} to {end}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------
# Generic booking rules
# ---------------------------------------------------------

BOOKING_INSTRUCTIONS = """
APPOINTMENT BOOKING FLOW

When the customer wants to book an appointment, collect:

1. Full name
2. Phone number
3. Service
4. Preferred date
5. Preferred time
6. Final confirmation

Ask only one question at a time.

Do not ask for information that the customer has already provided.

Always preserve booking details collected earlier in the conversation.

A short customer answer normally answers the assistant's most recent
question.

Examples:

Assistant:
What is your full name?

Customer:
Rajesh

This means customer_name is Rajesh.

Assistant:
Which service would you like?

Customer:
Haircut

Match the answer only against the dynamically supplied active services.

Assistant:
What date would you prefer?

Customer:
Tomorrow

Convert tomorrow into YYYY-MM-DD using today's date supplied in the
conversation context.


FIELD COLLECTION ORDER

Ask for the first missing field in this order:

1. customer_name
2. customer_phone
3. service
4. appointment_date
5. appointment_time


NAME RULES

- Collect the customer's full name.
- Do not treat greetings such as Hi or Hello as a name.
- A name should normally contain at least two characters.
- Do not invent a customer name.


PHONE RULES

- Accept international and UK phone-number formats.
- Preserve the phone number provided by the customer.
- Do not invent or complete a phone number.
- If the value clearly does not look like a phone number, ask again.


SERVICE RULES

- Only accept a service from the dynamically supplied active service list.
- Never accept an inactive service.
- Never invent a service.
- Match reasonable customer wording against the available service names.
- Preserve the official service name from the active service list.
- If the requested service is unavailable, politely display the active
  services and ask the customer to choose one.
- If there are no active services, explain that no services are currently
  available and do not proceed with booking.


DATE RULES

- Convert valid dates to YYYY-MM-DD.
- Never create appointments in the past.
- Use today's supplied date for relative expressions.
- Understand expressions such as tomorrow, next Monday and this Friday.
- Check the dynamically supplied working hours for the selected day.
- If the business is closed on that day, explain that it is closed and ask
  for another date.
- If a date is ambiguous, ask the customer to clarify it.


TIME RULES

- Convert valid times to HH:MM using 24-hour format.
- Validate the selected time using the dynamically supplied working hours
  for the selected appointment date.
- Do not accept a time before the opening time.
- Do not accept a time after the closing time.
- Do not claim that a specific time slot is available.
- This system only collects a preferred appointment time.
- If the time is outside working hours, display the correct working hours
  for that day and ask for another time.


CONFIRMATION RULES

After all five booking fields are collected, do not immediately set
booking_ready to true.

First show a clear booking summary:

Name: ...
Phone: ...
Service: ...
Date: ...
Time: ...

Then ask:

Would you like me to submit this appointment request?

At this stage:

- booking_ready must be false.
- Include all five collected fields in the structured result.
- intent must be book_appointment.

Only set booking_ready to true when:

1. All five booking fields are available.
2. The assistant previously displayed the booking summary.
3. The customer explicitly confirms using a response such as:
   - Yes
   - Confirm
   - Submit it
   - That's correct
   - Please book it

When booking_ready is true:

- customer_name must not be null.
- customer_phone must not be null.
- service must not be null.
- appointment_date must use YYYY-MM-DD.
- appointment_time must use HH:MM.
- intent must be book_appointment.
- The reply should say that the appointment request is being submitted.
- Explain that the appointment status will remain pending.
- Do not claim that the appointment is confirmed by the business.


CORRECTION RULES

Before final confirmation, allow the customer to change any detail.

Examples:

- Change the date to Friday
- Use 3 PM instead
- My number is incorrect
- I want another service instead

Apply the correction, show the updated summary and ask for confirmation
again.

If the customer says no when asked to confirm:

- Ask which detail they want to change.
- booking_ready must remain false.


GENERAL QUESTIONS

For general business questions:

- intent must be general_question.
- booking_ready must be false.
- Answer only using the dynamically supplied business information.
- Do not invent prices.
- Do not invent availability.
- Do not invent policies.
- Do not offer services outside the active service list.
- If information is not provided, clearly say that it is not available.


CANCELLATION AND RESCHEDULING

If the customer asks to cancel:

- intent must be cancel_appointment.
- booking_ready must be false.
- Explain that appointment cancellation is not yet available through chat.
- Ask them to contact the business and provide their appointment reference.

If the customer asks to reschedule:

- intent must be reschedule_appointment.
- booking_ready must be false.
- Explain that rescheduling is not yet available through chat.
- Ask them to contact the business and provide their appointment reference.


GENERAL RESPONSE RULES

- Keep replies concise, professional and natural.
- Ask only one question at a time.
- Never expose internal structured-output fields.
- Never say that an appointment is confirmed.
- The appointment request remains pending until reviewed by the business.
- Never mention Demo Salon unless that exact name is supplied dynamically.
"""


# ---------------------------------------------------------
# Dynamic system-prompt builder
# ---------------------------------------------------------

def build_system_prompt(
    business_settings: dict[str, Any],
    services: list[dict[str, Any]],
) -> str:
    business_name = str(
        business_settings.get(
            "business_name",
            "the business",
        )
    ).strip()

    business_type = str(
        business_settings.get(
            "business_type",
            "",
        )
    ).strip()

    address = str(
        business_settings.get(
            "address",
            "",
        )
    ).strip()

    phone = str(
        business_settings.get(
            "phone",
            "",
        )
    ).strip()

    email = str(
        business_settings.get(
            "email",
            "",
        )
    ).strip()

    website = str(
        business_settings.get(
            "website",
            "",
        )
    ).strip()

    timezone = str(
        business_settings.get(
            "timezone",
            "",
        )
    ).strip()

    welcome_message = str(
        business_settings.get(
            "welcome_message",
            "",
        )
    ).strip()

    booking_message = str(
        business_settings.get(
            "booking_message",
            "",
        )
    ).strip()

    services_text = build_services_text(
        services
    )

    working_hours_text = build_working_hours_text(
        business_settings.get(
            "working_hours",
            {},
        )
    )

    if not business_name:
        business_name = "the business"

    dynamic_business_information = f"""
You are the professional AI receptionist for {business_name}.

DYNAMIC BUSINESS INFORMATION

Business name:
{business_name}

Business type:
{business_type or "Not provided"}

Business address:
{address or "Not provided"}

Business phone:
{phone or "Not provided"}

Business email:
{email or "Not provided"}

Business website:
{website or "Not provided"}

Business timezone:
{timezone or "Not provided"}

Welcome message:
{welcome_message or "Not provided"}

Active services:
{services_text}

Working hours:
{working_hours_text}

Booking submission message:
{booking_message or "Your appointment request has been submitted and is pending review."}


IMPORTANT BUSINESS-DATA RULES

- Use only the business information shown above.
- Use the exact business name shown above.
- Mention only active services shown above.
- Never use old hardcoded business information.
- Never invent services, prices, addresses, phone numbers, emails,
  working hours, policies or availability.
- If information is not provided, say that it is not available.
"""

    return (
        dynamic_business_information
        + "\n\n"
        + BOOKING_INSTRUCTIONS
    )


# ---------------------------------------------------------
# Main AI function
# ---------------------------------------------------------

def generate_ai_reply(
    user_message: str,
    conversation_history: list[dict[str, Any]],
    business_settings: dict[str, Any],
    services: list[dict[str, Any]],
) -> AIReceptionistResult:
    cleaned_user_message = user_message.strip()

    if not cleaned_user_message:
        raise ValueError(
            "The user message cannot be empty."
        )

    today = datetime.now().astimezone()

    today_date = today.strftime("%Y-%m-%d")
    today_day = today.strftime("%A")

    dynamic_instructions = build_system_prompt(
        business_settings=business_settings,
        services=services,
    )

    input_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                f"Today's date is {today_date}. "
                f"Today is {today_day}. "
                "Use this date when interpreting relative dates. "
                "Never select an appointment date in the past."
            ),
        }
    ]

    for message in conversation_history:
        role = message.get("role")

        content = str(
            message.get("content", "")
        ).strip()

        if role not in {"user", "assistant"}:
            continue

        if not content:
            continue

        input_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    input_messages.append(
        {
            "role": "user",
            "content": cleaned_user_message,
        }
    )

    # Temporary debugging.
    # You can remove these print statements after testing.
    print("")
    print("========== DYNAMIC AI DEBUG ==========")
    print(
        "Business name:",
        business_settings.get("business_name"),
    )
    print(
        "Business type:",
        business_settings.get("business_type"),
    )
    print(
        "Business services:",
        [
            service.get("name")
            for service in services
            if service.get("active", True)
        ],
    )
    print(
        "Working hours:",
        business_settings.get("working_hours"),
    )
    print("======================================")
    print("")

    response = client.responses.parse(
        model="gpt-5-mini",
        instructions=dynamic_instructions,
        input=input_messages,
        text_format=AIReceptionistResult,
    )

    result = response.output_parsed

    if result is None:
        raise RuntimeError(
            "OpenAI did not return a structured response."
        )

    return result