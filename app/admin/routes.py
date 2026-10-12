from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import bp
from app.extensions import db
from app.models import ManagerFarmer, User
from app.services import docusign as docusign_service
from app.services.settings import DEFAULTS, get_setting, set_setting


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def staff_required(view):
    """Admin or manager."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ("admin", "manager"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.route("/users", methods=["GET", "POST"])
@login_required
@staff_required
def users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            email = (request.form.get("email") or "").strip().lower()
            full_name = (request.form.get("full_name") or "").strip()
            password = request.form.get("password") or ""
            role = request.form.get("role") or ""
            manager_id = request.form.get("manager_id")
            mobile_no = (request.form.get("mobile_no") or "").strip() or None
            id_card_no = (request.form.get("id_card_no") or "").strip() or None

            if current_user.is_manager:
                role = "farmer"

            if role not in ("admin", "manager", "farmer"):
                flash("Invalid role.", "error")
                return redirect(url_for("admin.users"))
            if current_user.is_manager and role != "farmer":
                flash("Managers can only create farmers.", "error")
                return redirect(url_for("admin.users"))
            if not current_user.is_admin and role == "admin":
                flash("Only admins can create admins.", "error")
                return redirect(url_for("admin.users"))
            if not email or not full_name or len(password) < 8:
                flash("Name, email, and password (8+ chars) are required.", "error")
                return redirect(url_for("admin.users"))
            if User.query.filter_by(email=email).first():
                flash("Email already exists.", "error")
                return redirect(url_for("admin.users"))

            # Farmers: optional mobile + ID card. Managers: optional mobile. Admin: ignore extras.
            if role == "farmer":
                pass
            elif role == "manager":
                id_card_no = None
            else:
                mobile_no = None
                id_card_no = None

            user = User(
                email=email,
                full_name=full_name,
                role=role,
                mobile_no=mobile_no,
                id_card_no=id_card_no,
                created_by=current_user.id,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if role == "farmer":
                link_manager_id = current_user.id if current_user.is_manager else None
                if current_user.is_admin and manager_id:
                    try:
                        link_manager_id = int(manager_id)
                    except ValueError:
                        link_manager_id = None
                if link_manager_id:
                    mgr = User.query.filter_by(id=link_manager_id, role="manager").first()
                    if mgr:
                        db.session.add(
                            ManagerFarmer(manager_id=mgr.id, farmer_id=user.id)
                        )

            db.session.commit()
            flash(f"Created {role}: {full_name}.", "success")
            return redirect(url_for("admin.users"))

        if action == "link" and current_user.is_admin:
            try:
                manager_id = int(request.form.get("manager_id"))
                farmer_id = int(request.form.get("farmer_id"))
            except (TypeError, ValueError):
                flash("Invalid link selection.", "error")
                return redirect(url_for("admin.users"))
            manager = User.query.filter_by(id=manager_id, role="manager").first()
            farmer = User.query.filter_by(id=farmer_id, role="farmer").first()
            if not manager or not farmer:
                flash("Select a valid manager and farmer.", "error")
                return redirect(url_for("admin.users"))
            exists = ManagerFarmer.query.filter_by(
                manager_id=manager_id, farmer_id=farmer_id
            ).first()
            if exists:
                flash("Already linked.", "warning")
            else:
                db.session.add(ManagerFarmer(manager_id=manager_id, farmer_id=farmer_id))
                db.session.commit()
                flash("Farmer linked to manager.", "success")
            return redirect(url_for("admin.users"))

        if action == "toggle" and current_user.is_admin:
            try:
                user_id = int(request.form.get("user_id"))
            except (TypeError, ValueError):
                flash("Invalid user.", "error")
                return redirect(url_for("admin.users"))
            user = db.session.get(User, user_id)
            if user and user.id != current_user.id:
                user.is_active = not user.is_active
                db.session.commit()
                flash("User status updated.", "success")
            return redirect(url_for("admin.users"))

    if current_user.is_admin:
        people = User.query.order_by(User.role, User.full_name).all()
        managers = User.query.filter_by(role="manager", is_active=True).order_by(User.full_name).all()
        farmers = User.query.filter_by(role="farmer", is_active=True).order_by(User.full_name).all()
        links = ManagerFarmer.query.all()
    else:
        link_ids = [
            r.farmer_id
            for r in ManagerFarmer.query.filter_by(manager_id=current_user.id).all()
        ]
        people = (
            User.query.filter(User.id.in_(link_ids)).order_by(User.full_name).all()
            if link_ids
            else []
        )
        managers = []
        farmers = []
        links = ManagerFarmer.query.filter_by(manager_id=current_user.id).all()

    return render_template(
        "admin/users.html",
        people=people,
        managers=managers,
        farmers=farmers,
        links=links,
    )


@bp.route("/configurations", methods=["GET", "POST"])
@login_required
@admin_required
def configurations():
    keys = [
        "site_name",
        "support_contact",
        "consent_terms",
        "terms_version",
        "max_upload_mb",
        "allowed_extensions",
        "timezone_display",
        "docusign_template_id",
        "docusign_return_path",
        "enable_farmer_download",
    ]

    if request.method == "POST":
        for key in keys:
            if key in request.form:
                set_setting(key, request.form.get(key, ""), user_id=current_user.id)
        flash("Settings saved.", "success")
        return redirect(url_for("admin.configurations"))

    values = {key: get_setting(key, DEFAULTS.get(key, "")) for key in keys}
    return render_template(
        "admin/configurations.html",
        values=values,
        docusign_status=docusign_service.configuration_status(),
    )
