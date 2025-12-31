"""
Firebase Configuration for W&M Business Major Advising Backend

Uses Firebase Admin SDK for server-side operations with Firestore.
"""

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Firebase configuration from environment variables
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}

# Service account key path
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")

# Global Firestore client
_db = None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.

    For server-side operations, we use the Admin SDK with default credentials
    or a service account. The web config above is for reference.

    To use with a service account:
    1. Go to Firebase Console -> Project Settings -> Service Accounts
    2. Generate a new private key
    3. Save it as 'serviceAccountKey.json' in this directory
    """
    global _db

    if _db is not None:
        return _db

    # Build possible paths for service account key
    backend_dir = Path(__file__).parent.parent
    possible_paths = [
        backend_dir / SERVICE_ACCOUNT_PATH,             # backend/key.json
        Path("backend") / SERVICE_ACCOUNT_PATH,         # From project root
        Path(SERVICE_ACCOUNT_PATH)                      # Direct path
    ]

    for path in possible_paths:
        if path.exists():
            cred = credentials.Certificate(str(path))
            firebase_admin.initialize_app(cred)
            break
    else:
        # Initialize with default credentials (for cloud environments)
        firebase_admin.initialize_app(options={
            'projectId': FIREBASE_CONFIG['projectId']
        })

    _db = firestore.client()
    return _db


def get_firestore_client():
    """Get the Firestore client instance."""
    global _db
    if _db is None:
        _db = initialize_firebase()
    return _db
