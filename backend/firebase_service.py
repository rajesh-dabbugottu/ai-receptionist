import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


BASE_DIR = Path(__file__).resolve().parent
SERVICE_ACCOUNT_PATH = BASE_DIR / "firebase-service-account.json"


def initialize_firebase():
    # Firebase already initialized
    if firebase_admin._apps:
        return firestore.client()

    # -----------------------------
    # Production / Render
    # -----------------------------
    firebase_credentials = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT"
    )

    if firebase_credentials:
        try:
            service_account_info = json.loads(
                firebase_credentials
            )

            credential = credentials.Certificate(
                service_account_info
            )

            firebase_admin.initialize_app(
                credential
            )

            print(
                "Firebase initialized using "
                "environment variable."
            )

            return firestore.client()

        except json.JSONDecodeError as error:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT contains "
                "invalid JSON."
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"Firebase initialization failed: {error}"
            ) from error

    # -----------------------------
    # Local development
    # -----------------------------
    if SERVICE_ACCOUNT_PATH.exists():

        credential = credentials.Certificate(
            str(SERVICE_ACCOUNT_PATH)
        )

        firebase_admin.initialize_app(
            credential
        )

        print(
            "Firebase initialized using local "
            "service account file."
        )

        return firestore.client()

    raise RuntimeError(
        "Firebase credentials were not found. "
        "For Render set FIREBASE_SERVICE_ACCOUNT. "
        "For local development provide "
        "firebase-service-account.json."
    )


db = initialize_firebase()