from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.agreements import bp
from app.extensions import db
from app.models import ManagerAgreement
from app.services import docusign as docusign_service
from app.services.settings import get_setting


@bp.route("/")
@login_required
def status():
    if not current_user.is_manager and not current_user.is_admin:
        flash("Agreements apply to manager accounts.", "warning")
        return redirect(url_for("main.dashboard"))

    agreement = None
    if current_user.is_manager:
        agreement = (
            ManagerAgreement.query.filter_by(manager_id=current_user.id)
            .order_by(ManagerAgreement.created_at.desc())
            .first()
        )

    return render_template(
        "agreements/status.html",
        agreement=agreement,
        docusign_status=docusign_service.configuration_status(),
    )


@bp.route("/start", methods=["POST"])
@login_required
def start():
    if not current_user.is_manager:
        flash("Only managers sign the blanket agreement.", "error")
        return redirect(url_for("main.dashboard"))

    existing = (
        ManagerAgreement.query.filter_by(manager_id=current_user.id, status="completed")
        .first()
    )
    if existing:
        flash("Agreement already signed.", "success")
        return redirect(url_for("agreements.status"))

    if not docusign_service.is_configured():
        flash(
            "DocuSign is not configured yet. Ask an admin to add sandbox credentials.",
            "error",
        )
        return redirect(url_for("agreements.status"))

    # Prefer HTTPS return URL (DocuSign + our nginx TLS site)
    return_url = url_for(
        "agreements.callback",
        _external=True,
        _scheme="https",
    )
    template_id = (get_setting("docusign_template_id") or "").strip() or None

    try:
        result = docusign_service.create_manager_agreement_envelope(
            manager_email=current_user.email,
            manager_name=current_user.full_name,
            return_url=return_url,
            template_id=template_id or None,
        )
    except docusign_service.DocuSignNotConfigured:
        flash("DocuSign is not configured.", "error")
        return redirect(url_for("agreements.status"))
    except docusign_service.DocuSignError as exc:
        flash(str(exc), "error")
        return redirect(url_for("agreements.status"))

    agreement = ManagerAgreement(
        manager_id=current_user.id,
        docusign_envelope_id=result["envelope_id"],
        status="pending",
    )
    db.session.add(agreement)
    db.session.commit()
    return redirect(result["signing_url"])


@bp.route("/callback")
@login_required
def callback():
    """Return URL from DocuSign embedded signing."""
    if not current_user.is_manager:
        return redirect(url_for("main.dashboard"))

    event = (request.args.get("event") or "").lower()
    agreement = (
        ManagerAgreement.query.filter_by(manager_id=current_user.id)
        .order_by(ManagerAgreement.created_at.desc())
        .first()
    )

    if not agreement:
        flash("No agreement in progress.", "warning")
        return redirect(url_for("agreements.status"))

    # Prefer live status from DocuSign when possible
    if agreement.docusign_envelope_id and docusign_service.is_configured():
        try:
            status = docusign_service.get_envelope_status(agreement.docusign_envelope_id)
            if status in ("completed", "signed"):
                agreement.status = "completed"
                agreement.signed_at = datetime.utcnow()
                db.session.commit()
                flash("Agreement signed. You can upload videos now.", "success")
                return redirect(url_for("videos.upload"))
            if status in ("declined", "voided"):
                agreement.status = "declined"
                db.session.commit()
                flash("Agreement was declined.", "error")
                return redirect(url_for("agreements.status"))
        except docusign_service.DocuSignError:
            pass

    if event in ("signing_complete", "viewing_complete"):
        # Optimistic complete when DocuSign returns success event but API poll failed
        agreement.status = "completed"
        agreement.signed_at = datetime.utcnow()
        db.session.commit()
        flash("Agreement signed. You can upload videos now.", "success")
        return redirect(url_for("videos.upload"))

    if event in ("decline", "cancel"):
        agreement.status = "declined"
        db.session.commit()
        flash("Signing was cancelled or declined.", "warning")

    return redirect(url_for("agreements.status"))


@bp.route("/dev-complete", methods=["POST"])
@login_required
def dev_complete():
    """Testing helper when DocuSign sandbox credentials are not configured."""
    if docusign_service.is_configured():
        flash("Use DocuSign signing when configured.", "warning")
        return redirect(url_for("agreements.status"))

    if not current_user.is_manager:
        flash("Managers only.", "error")
        return redirect(url_for("main.dashboard"))

    existing = ManagerAgreement.query.filter_by(
        manager_id=current_user.id, status="completed"
    ).first()
    if existing:
        flash("Agreement already signed.", "success")
        return redirect(url_for("videos.upload"))

    agreement = ManagerAgreement(
        manager_id=current_user.id,
        docusign_envelope_id="dev-bypass",
        status="completed",
        signed_at=datetime.utcnow(),
    )
    db.session.add(agreement)
    db.session.commit()
    flash("Dev agreement marked complete (DocuSign not configured).", "success")
    return redirect(url_for("videos.upload"))


@bp.route("/reset", methods=["POST"])
@login_required
def reset():
    """Clear completed agreement so the manager can sign again (demos / re-sign)."""
    if current_user.is_admin:
        try:
            manager_id = int(request.form.get("manager_id") or current_user.id)
        except (TypeError, ValueError):
            flash("Invalid manager.", "error")
            return redirect(url_for("agreements.status"))
        from app.models import User

        manager = User.query.filter_by(id=manager_id, role="manager").first()
        if not manager:
            flash("Manager not found.", "error")
            return redirect(url_for("agreements.status"))
    elif current_user.is_manager:
        manager_id = current_user.id
    else:
        flash("Not allowed.", "error")
        return redirect(url_for("main.dashboard"))

    rows = ManagerAgreement.query.filter_by(manager_id=manager_id).all()
    if not rows:
        flash("No agreement to reset.", "warning")
        return redirect(url_for("agreements.status"))

    for row in rows:
        # Keep history visible as declined/revoked locally; upload gate only checks completed
        if row.status == "completed":
            row.status = "declined"
            row.signed_at = None
        elif row.status == "pending":
            row.status = "declined"

    db.session.commit()
    flash(
        "Agreement reset. You can sign with DocuSign again before uploading.",
        "success",
    )
    return redirect(url_for("agreements.status"))
