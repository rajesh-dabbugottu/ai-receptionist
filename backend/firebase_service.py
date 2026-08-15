from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


BASE_DIR = Path(__file__).resolve().parent
SERVICE_ACCOUNT_PATH = BASE_DIR / "firebase-service-account.json"


def initialize_firebase():
    if not SERVICE_ACCOUNT_PATH.exists():
        raise FileNotFoundError(
            f"Firebase service account file was not found: "
            f"{SERVICE_ACCOUNT_PATH}"
        )

    if not firebase_admin._apps:
        credential = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
        firebase_admin.initialize_app(credential)

    return firestore.client()


db = initialize_firebase()