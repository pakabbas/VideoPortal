import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "/videoportal").rstrip("/") or "/"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:@127.0.0.1:3306/videoportal",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    if not Path(UPLOAD_FOLDER).is_absolute():
        UPLOAD_FOLDER = str(BASE_DIR / UPLOAD_FOLDER)

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@videoportal.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMeAdmin123!")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Portal Admin")

    DOCUSIGN_INTEGRATION_KEY = os.getenv("DOCUSIGN_INTEGRATION_KEY", "")
    DOCUSIGN_USER_ID = os.getenv("DOCUSIGN_USER_ID", "")
    DOCUSIGN_ACCOUNT_ID = os.getenv("DOCUSIGN_ACCOUNT_ID", "")
    DOCUSIGN_RSA_KEY_PATH = os.getenv(
        "DOCUSIGN_RSA_KEY_PATH", str(BASE_DIR / "secrets" / "docusign_private.key")
    )
    if not Path(DOCUSIGN_RSA_KEY_PATH).is_absolute():
        DOCUSIGN_RSA_KEY_PATH = str(BASE_DIR / DOCUSIGN_RSA_KEY_PATH)
    DOCUSIGN_AUTH_SERVER = os.getenv("DOCUSIGN_AUTH_SERVER", "account-d.docusign.com")
    DOCUSIGN_BASE_PATH = os.getenv(
        "DOCUSIGN_BASE_PATH", "https://demo.docusign.net/restapi"
    )
    DOCUSIGN_AGREEMENT_PDF = os.getenv(
        "DOCUSIGN_AGREEMENT_PDF", str(BASE_DIR / "static" / "docs" / "manager_agreement.pdf")
    )
    if not Path(DOCUSIGN_AGREEMENT_PDF).is_absolute():
        DOCUSIGN_AGREEMENT_PDF = str(BASE_DIR / DOCUSIGN_AGREEMENT_PDF)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
