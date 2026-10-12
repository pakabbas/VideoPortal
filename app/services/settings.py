from __future__ import annotations

from typing import Optional

from app.extensions import db
from app.models import Setting

DEFAULTS = {
    "site_name": "Video Portal",
    "support_contact": "",
    "consent_terms": (
        "I confirm that I have collected this video from the named farmer, "
        "that the farmer consented to recording farm work, and that I am "
        "authorized to upload this video to the Video Portal for operational use."
    ),
    "terms_version": "1",
    "max_upload_mb": "500",
    "allowed_extensions": "mp4,mov,avi,mkv,webm",
    "timezone_display": "UTC",
    "docusign_template_id": "",
    "docusign_return_path": "/agreements/callback",
    "enable_farmer_download": "1",
}


def get_setting(key: str, default: Optional[str] = None) -> str:
    row = db.session.get(Setting, key)
    if row is not None:
        return row.value
    if default is not None:
        return default
    return DEFAULTS.get(key, "")


def set_setting(key: str, value: str, user_id: Optional[int] = None) -> None:
    row = db.session.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value, updated_by=user_id)
        db.session.add(row)
    else:
        row.value = value
        row.updated_by = user_id
    db.session.commit()


def ensure_default_settings() -> None:
    for key, value in DEFAULTS.items():
        if db.session.get(Setting, key) is None:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()


def allowed_extensions_set() -> set[str]:
    raw = get_setting("allowed_extensions", "mp4,mov,avi,mkv,webm")
    return {ext.strip().lower().lstrip(".") for ext in raw.split(",") if ext.strip()}


def max_upload_bytes() -> int:
    try:
        mb = int(get_setting("max_upload_mb", "500"))
    except ValueError:
        mb = 500
    return max(mb, 1) * 1024 * 1024
