import os
import uuid
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ManagerAgreement, ManagerFarmer, UploadConsent, User, Video
from app.services.settings import (
    allowed_extensions_set,
    get_setting,
    max_upload_bytes,
)
from app.videos import bp


def manager_or_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ("admin", "manager"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def manager_has_signed_agreement(manager_id: int) -> bool:
    row = (
        ManagerAgreement.query.filter_by(manager_id=manager_id, status="completed")
        .order_by(ManagerAgreement.signed_at.desc())
        .first()
    )
    return row is not None


def farmers_for_uploader() -> list[User]:
    if current_user.is_admin:
        return User.query.filter_by(role="farmer", is_active=True).order_by(User.full_name).all()
    link_ids = [
        r.farmer_id
        for r in ManagerFarmer.query.filter_by(manager_id=current_user.id).all()
    ]
    if not link_ids:
        return []
    return (
        User.query.filter(User.id.in_(link_ids), User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )


@bp.route("/upload", methods=["GET", "POST"])
@login_required
@manager_or_admin
def upload():
    if current_user.is_manager and not manager_has_signed_agreement(current_user.id):
        flash("You must sign the blanket upload agreement before uploading.", "warning")
        return redirect(url_for("agreements.status"))

    farmers = farmers_for_uploader()
    consent_terms = get_setting("consent_terms")
    terms_version = get_setting("terms_version", "1")

    if request.method == "POST":
        if not request.form.get("consent"):
            flash("You must accept the consent terms to upload.", "error")
            return redirect(url_for("videos.upload"))

        try:
            farmer_id = int(request.form.get("farmer_id"))
        except (TypeError, ValueError):
            flash("Select a farmer.", "error")
            return redirect(url_for("videos.upload"))

        allowed_farmers = {f.id for f in farmers}
        if farmer_id not in allowed_farmers:
            flash("Invalid farmer selection.", "error")
            return redirect(url_for("videos.upload"))

        recorded_date = request.form.get("recorded_date") or ""
        recorded_time = request.form.get("recorded_time") or "00:00"
        try:
            recorded_at = datetime.strptime(
                f"{recorded_date} {recorded_time}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            flash("Invalid recorded date/time.", "error")
            return redirect(url_for("videos.upload"))

        file = request.files.get("video")
        if not file or not file.filename:
            flash("Choose a video file.", "error")
            return redirect(url_for("videos.upload"))

        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in allowed_extensions_set():
            flash(
                f"File type not allowed. Use: {', '.join(sorted(allowed_extensions_set()))}",
                "error",
            )
            return redirect(url_for("videos.upload"))

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > max_upload_bytes():
            flash(
                f"File exceeds max size of {get_setting('max_upload_mb', '500')} MB.",
                "error",
            )
            return redirect(url_for("videos.upload"))

        upload_root = Path(current_app.config["UPLOAD_FOLDER"])
        upload_root.mkdir(parents=True, exist_ok=True)
        stored_name = f"{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex}.{ext}"
        dest = upload_root / stored_name
        file.save(dest)

        video = Video(
            original_filename=filename,
            stored_path=str(dest),
            farmer_id=farmer_id,
            uploader_id=current_user.id,
            status="uploaded",
            recorded_at=recorded_at,
        )
        db.session.add(video)
        db.session.flush()
        db.session.add(
            UploadConsent(
                video_id=video.id,
                uploader_id=current_user.id,
                terms_version=terms_version,
            )
        )
        db.session.commit()
        flash("Video uploaded. Mark it ready when processing is complete.", "success")
        return redirect(url_for("videos.manage"))

    return render_template(
        "videos/upload.html",
        farmers=farmers,
        consent_terms=consent_terms,
        terms_version=terms_version,
        max_mb=get_setting("max_upload_mb", "500"),
        extensions=get_setting("allowed_extensions"),
        today=date.today().isoformat(),
    )


@bp.route("/manage")
@login_required
@manager_or_admin
def manage():
    query = Video.query
    if current_user.is_manager:
        query = query.filter_by(uploader_id=current_user.id)
    videos = query.order_by(Video.uploaded_at.desc()).all()
    return render_template("videos/manage.html", videos=videos)


@bp.route("/<int:video_id>/ready", methods=["POST"])
@login_required
@manager_or_admin
def mark_ready(video_id: int):
    video = Video.query.get_or_404(video_id)
    if current_user.is_manager and video.uploader_id != current_user.id:
        abort(403)
    if video.status != "ready":
        video.status = "ready"
        video.ready_at = datetime.utcnow()
        db.session.commit()
        flash("Video marked ready for download.", "success")
    return redirect(request.referrer or url_for("videos.manage"))


@bp.route("/download")
@login_required
def download_list():
    if current_user.is_farmer and get_setting("enable_farmer_download", "1") != "1":
        flash("Downloads are disabled for farmer accounts.", "warning")
        return redirect(url_for("main.dashboard"))

    query = Video.query.filter_by(status="ready")

    if current_user.is_farmer:
        query = query.filter_by(farmer_id=current_user.id)
    elif current_user.is_manager:
        query = query.filter_by(uploader_id=current_user.id)

    date_from = request.args.get("date_from") or ""
    date_to = request.args.get("date_to") or ""
    time_from = request.args.get("time_from") or ""
    time_to = request.args.get("time_to") or ""
    manager_id = request.args.get("manager_id") or ""
    farmer_id = request.args.get("farmer_id") or ""
    show_advanced = request.args.get("advanced") == "1"

    if date_from:
        try:
            query = query.filter(
                Video.recorded_at >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        except ValueError:
            flash("Invalid from date.", "error")
    if date_to:
        try:
            end = datetime.strptime(date_to + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(Video.recorded_at <= end)
        except ValueError:
            flash("Invalid to date.", "error")

    videos = query.order_by(Video.recorded_at.desc()).all()

    # Time-of-day filter in Python for clarity across MySQL versions
    def time_ok(v: Video) -> bool:
        t = v.recorded_at.time()
        if time_from:
            try:
                if t < datetime.strptime(time_from, "%H:%M").time():
                    return False
            except ValueError:
                return True
        if time_to:
            try:
                if t > datetime.strptime(time_to, "%H:%M").time():
                    return False
            except ValueError:
                return True
        return True

    videos = [v for v in videos if time_ok(v)]

    if current_user.is_admin and manager_id:
        try:
            mid = int(manager_id)
            videos = [v for v in videos if v.uploader_id == mid]
        except ValueError:
            pass

    if farmer_id and (current_user.is_admin or show_advanced or current_user.is_manager):
        try:
            fid = int(farmer_id)
            videos = [v for v in videos if v.farmer_id == fid]
        except ValueError:
            pass

    managers = []
    farmers = []
    if current_user.is_admin:
        managers = (
            User.query.filter_by(role="manager", is_active=True)
            .order_by(User.full_name)
            .all()
        )
        farmers = (
            User.query.filter_by(role="farmer", is_active=True)
            .order_by(User.full_name)
            .all()
        )
    elif current_user.is_manager:
        farmers = farmers_for_uploader()

    return render_template(
        "videos/download.html",
        videos=videos,
        managers=managers,
        farmers=farmers,
        filters={
            "date_from": date_from,
            "date_to": date_to,
            "time_from": time_from,
            "time_to": time_to,
            "manager_id": manager_id,
            "farmer_id": farmer_id,
            "advanced": show_advanced,
        },
        timezone_display=get_setting("timezone_display", "UTC"),
    )


def _can_access_video(video: Video, *, require_ready: bool) -> bool:
    if require_ready and video.status != "ready":
        return False
    if current_user.is_admin:
        return True
    if current_user.is_manager and video.uploader_id == current_user.id:
        return True
    if (
        current_user.is_farmer
        and video.farmer_id == current_user.id
        and get_setting("enable_farmer_download", "1") == "1"
        and video.status == "ready"
    ):
        return True
    return False


@bp.route("/<int:video_id>/preview")
@login_required
@manager_or_admin
def preview(video_id: int):
    """Stream video inline for in-page preview (uploaded or ready)."""
    video = Video.query.get_or_404(video_id)
    if not _can_access_video(video, require_ready=False):
        abort(403)

    path = Path(video.stored_path)
    if not path.is_file():
        abort(404)

    return send_file(
        path,
        as_attachment=False,
        conditional=True,
        download_name=video.original_filename,
    )


@bp.route("/<int:video_id>/file")
@login_required
def download_file(video_id: int):
    video = Video.query.get_or_404(video_id)
    if not _can_access_video(video, require_ready=True):
        abort(403)

    path = Path(video.stored_path)
    if not path.is_file():
        flash("File missing on server.", "error")
        return redirect(url_for("videos.download_list"))

    return send_file(
        path,
        as_attachment=True,
        download_name=video.original_filename,
    )
