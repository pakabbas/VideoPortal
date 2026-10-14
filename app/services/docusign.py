from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Optional

from flask import current_app, url_for


class DocuSignNotConfigured(Exception):
    pass


class DocuSignError(Exception):
    pass


def is_configured() -> bool:
    cfg = current_app.config
    key = (cfg.get("DOCUSIGN_INTEGRATION_KEY") or "").strip()
    user = (cfg.get("DOCUSIGN_USER_ID") or "").strip()
    account = (cfg.get("DOCUSIGN_ACCOUNT_ID") or "").strip()
    rsa_path = Path(cfg.get("DOCUSIGN_RSA_KEY_PATH") or "")
    return bool(key and user and account and rsa_path.is_file())


def configuration_status() -> dict[str, Any]:
    cfg = current_app.config
    rsa_path = Path(cfg.get("DOCUSIGN_RSA_KEY_PATH") or "")
    pdf_path = Path(cfg.get("DOCUSIGN_AGREEMENT_PDF") or "")
    return {
        "configured": is_configured(),
        "integration_key_set": bool((cfg.get("DOCUSIGN_INTEGRATION_KEY") or "").strip()),
        "user_id_set": bool((cfg.get("DOCUSIGN_USER_ID") or "").strip()),
        "account_id_set": bool((cfg.get("DOCUSIGN_ACCOUNT_ID") or "").strip()),
        "rsa_key_present": rsa_path.is_file(),
        "agreement_pdf_present": pdf_path.is_file(),
        "auth_server": cfg.get("DOCUSIGN_AUTH_SERVER"),
        "base_path": cfg.get("DOCUSIGN_BASE_PATH"),
    }


def _api_client():
    try:
        from docusign_esign import ApiClient
    except ImportError as exc:
        raise DocuSignError("docusign-esign package is not installed") from exc

    if not is_configured():
        raise DocuSignNotConfigured("DocuSign sandbox credentials are not configured")

    cfg = current_app.config
    rsa_path = Path(cfg["DOCUSIGN_RSA_KEY_PATH"])
    private_key = rsa_path.read_bytes()
    account_id = cfg["DOCUSIGN_ACCOUNT_ID"]

    api_client = ApiClient()
    api_client.set_base_path(cfg["DOCUSIGN_BASE_PATH"])
    api_client.set_oauth_host_name(cfg["DOCUSIGN_AUTH_SERVER"])

    try:
        token = api_client.request_jwt_user_token(
            client_id=cfg["DOCUSIGN_INTEGRATION_KEY"],
            user_id=cfg["DOCUSIGN_USER_ID"],
            oauth_host_name=cfg["DOCUSIGN_AUTH_SERVER"],
            private_key_bytes=private_key,
            expires_in=3600,
            scopes=["signature", "impersonation"],
        )
        access_token = token.access_token
        # Resolve account base URI so REST calls hit demo.docusign.net/restapi
        # (not the OAuth host). Missing this causes AUTHORIZATION_INVALID_TOKEN.
        user_info = api_client.get_user_info(access_token)
        account = next(
            (a for a in user_info.accounts if a.account_id == account_id),
            user_info.accounts[0] if user_info.accounts else None,
        )
        if account is None or not account.base_uri:
            raise DocuSignError("DocuSign account base URI not found for this user")
        api_client.host = f"{account.base_uri.rstrip('/')}/restapi"
        api_client.set_default_header("Authorization", f"Bearer {access_token}")
    except DocuSignError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DocuSignError(f"DocuSign JWT auth failed: {exc}") from exc

    return api_client


def create_signing_envelope(
    *,
    signer_email: str,
    signer_name: str,
    return_url: str,
    email_subject: str,
    document_name: str,
    pdf_path: Optional[Path] = None,
    template_id: Optional[str] = None,
    client_user_id: Optional[str] = None,
) -> dict[str, str]:
    """Create an embedded-signing envelope; return envelope_id + signing_url."""
    from docusign_esign import (
        Document,
        EnvelopeDefinition,
        EnvelopesApi,
        Recipients,
        RecipientViewRequest,
        Signer,
        SignHere,
        Tabs,
    )

    api_client = _api_client()
    account_id = current_app.config["DOCUSIGN_ACCOUNT_ID"]
    envelopes_api = EnvelopesApi(api_client)
    embedded_id = client_user_id or str(signer_email)

    signer = Signer(
        email=signer_email,
        name=signer_name,
        recipient_id="1",
        routing_order="1",
        client_user_id=embedded_id,
    )

    if template_id:
        envelope = EnvelopeDefinition(
            email_subject=email_subject,
            status="sent",
            template_id=template_id,
            template_roles=[
                {
                    "email": signer_email,
                    "name": signer_name,
                    "roleName": "Manager",
                    "clientUserId": embedded_id,
                }
            ],
        )
    else:
        path = Path(pdf_path or current_app.config["DOCUSIGN_AGREEMENT_PDF"])
        if not path.is_file():
            raise DocuSignError(f"Agreement PDF missing: {path}")

        document = Document(
            document_base64=base64.b64encode(path.read_bytes()).decode("ascii"),
            name=document_name,
            file_extension="pdf",
            document_id="1",
        )
        sign_here = SignHere(
            document_id="1",
            page_number="1",
            x_position="100",
            y_position="650",
        )
        signer.tabs = Tabs(sign_here_tabs=[sign_here])
        envelope = EnvelopeDefinition(
            email_subject=email_subject,
            documents=[document],
            recipients=Recipients(signers=[signer]),
            status="sent",
        )

    try:
        result = envelopes_api.create_envelope(account_id, envelope_definition=envelope)
        envelope_id = result.envelope_id

        view_request = RecipientViewRequest(
            authentication_method="none",
            client_user_id=embedded_id,
            recipient_id="1",
            return_url=return_url,
            user_name=signer_name,
            email=signer_email,
        )
        view = envelopes_api.create_recipient_view(
            account_id, envelope_id, recipient_view_request=view_request
        )
    except Exception as exc:  # noqa: BLE001
        raise DocuSignError(f"DocuSign envelope creation failed: {exc}") from exc

    return {"envelope_id": envelope_id, "signing_url": view.url}


def create_manager_agreement_envelope(
    *,
    manager_email: str,
    manager_name: str,
    return_url: str,
    template_id: Optional[str] = None,
) -> dict[str, str]:
    """Signup / blanket manager agreement."""
    return create_signing_envelope(
        signer_email=manager_email,
        signer_name=manager_name,
        return_url=return_url,
        email_subject="Video Portal — Manager Signup Agreement",
        document_name="Manager Signup Agreement",
        template_id=template_id,
        client_user_id=f"signup:{manager_email}",
    )


def create_video_agreement_envelope(
    *,
    signer_email: str,
    signer_name: str,
    return_url: str,
    video_id: int,
    video_filename: str,
    template_id: Optional[str] = None,
) -> dict[str, str]:
    """Per-video upload agreement."""
    from app.config import Config

    pdf = Path(current_app.root_path).parent / "static" / "docs" / "video_upload_agreement.pdf"
    if not pdf.is_file():
        pdf = Path(Config.DOCUSIGN_AGREEMENT_PDF)
    return create_signing_envelope(
        signer_email=signer_email,
        signer_name=signer_name,
        return_url=return_url,
        email_subject=f"Video Portal — Upload agreement (video #{video_id})",
        document_name=f"Video Upload Agreement — {video_filename}",
        pdf_path=pdf,
        template_id=template_id,
        client_user_id=f"video:{video_id}:{signer_email}",
    )


def get_envelope_status(envelope_id: str) -> str:
    from docusign_esign import EnvelopesApi

    api_client = _api_client()
    account_id = current_app.config["DOCUSIGN_ACCOUNT_ID"]
    envelopes_api = EnvelopesApi(api_client)
    try:
        env = envelopes_api.get_envelope(account_id, envelope_id)
    except Exception as exc:  # noqa: BLE001
        raise DocuSignError(f"DocuSign status check failed: {exc}") from exc
    return (env.status or "").lower()


def build_return_url() -> str:
    from app.services.settings import get_setting

    path = get_setting("docusign_return_path", "/agreements/callback")
    if not path.startswith("/"):
        path = "/" + path
    # url_for with _external needs request context; caller should pass absolute URL when possible
    try:
        return url_for("agreements.callback", _external=True)
    except RuntimeError:
        root = current_app.config.get("APPLICATION_ROOT", "/videoportal")
        return f"{root.rstrip('/')}{path}"
