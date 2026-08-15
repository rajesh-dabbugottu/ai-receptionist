from firebase_service import db


BUSINESS_ID = "demo_business_001"


def delete_collection(collection_ref, batch_size: int = 100):
    documents = list(
        collection_ref.limit(batch_size).stream()
    )

    if not documents:
        return 0

    deleted_count = 0

    for document in documents:
        document.reference.delete()
        deleted_count += 1

    if len(documents) >= batch_size:
        deleted_count += delete_collection(
            collection_ref,
            batch_size
        )

    return deleted_count


def clear_test_data():
    print("Clearing AI Receptionist test data...")
    print(f"Business ID: {BUSINESS_ID}")

    appointment_count = delete_collection(
        db.collection("appointments")
    )

    print(
        f"Deleted appointments: {appointment_count}"
    )

    conversations = list(
        db.collection("conversations").stream()
    )

    message_count = 0
    conversation_count = 0

    for conversation in conversations:
        messages_ref = (
            conversation.reference
            .collection("messages")
        )

        message_count += delete_collection(
            messages_ref
        )

        conversation.reference.delete()
        conversation_count += 1

    print(
        f"Deleted conversation messages: {message_count}"
    )

    print(
        f"Deleted conversations: {conversation_count}"
    )

    business_ref = (
        db.collection("businesses")
        .document(BUSINESS_ID)
    )

    services_ref = business_ref.collection(
        "services"
    )

    service_count = delete_collection(
        services_ref
    )

    print(
        f"Deleted services: {service_count}"
    )

    business_snapshot = business_ref.get()

    if business_snapshot.exists:
        business_ref.delete()
        print("Deleted business settings: 1")
    else:
        print("Deleted business settings: 0")

    print("")
    print("Test database cleanup completed.")


if __name__ == "__main__":
    confirmation = input(
        "Type DELETE to clear all test data: "
    )

    if confirmation == "DELETE":
        clear_test_data()
    else:
        print("Cleanup cancelled.")