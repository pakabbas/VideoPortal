from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app.main import bp
from app.models import ManagerAgreement, ManagerFarmer, User, Video
from app.services.settings import get_setting


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    stats = {}
    agreement_ok = True

    if current_user.is_admin:
        stats["videos_uploaded"] = Video.query.filter_by(status="uploaded").count()
        stats["videos_ready"] = Video.query.filter_by(status="ready").count()
        stats["managers"] = User.query.filter_by(role="manager").count()
        stats["farmers"] = User.query.filter_by(role="farmer").count()
    elif current_user.is_manager:
        stats["my_uploads"] = Video.query.filter_by(uploader_id=current_user.id).count()
        stats["pending"] = Video.query.filter_by(
            uploader_id=current_user.id, status="uploaded"
        ).count()
        stats["ready"] = Video.query.filter_by(
            uploader_id=current_user.id, status="ready"
        ).count()
        stats["farmers"] = ManagerFarmer.query.filter_by(manager_id=current_user.id).count()
        agreement_ok = (
            ManagerAgreement.query.filter_by(
                manager_id=current_user.id, status="completed"
            ).first()
            is not None
        )
    else:
        stats["ready"] = Video.query.filter_by(
            farmer_id=current_user.id, status="ready"
        ).count()

    return render_template(
        "main/dashboard.html",
        stats=stats,
        agreement_ok=agreement_ok,
        site_name=get_setting("site_name", "Video Portal"),
    )
