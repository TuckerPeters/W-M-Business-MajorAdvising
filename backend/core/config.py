"""
Firebase Configuration for W&M Business Major Advising Backend

Uses Firebase Admin SDK for server-side operations with Firestore.
Supports three initialization methods:
  1. FIREBASE_SERVICE_ACCOUNT_JSON env var (for Heroku / cloud platforms)
  2. Service account key file (for local development)
  3. Default credentials (for GCP environments)
"""

import json
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

    Tries initialization in this order:
    1. FIREBASE_SERVICE_ACCOUNT_JSON env var (JSON string, for Heroku)
    2. Service account key file (local development)
    3. Default credentials with projectId (GCP environments)
    """
    global _db

    if _db is not None:
        return _db

    # Method 1: Service account JSON from environment variable (Heroku)
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        service_account_info = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        return _db

    # Method 2: Service account key file (local development)
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
            _db = firestore.client()
            return _db

    # Method 3: Default credentials (for GCP environments)
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
