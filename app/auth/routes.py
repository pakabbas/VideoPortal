from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp
from app.extensions import db
from app.models import User
from app.services.settings import get_setting


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.dashboard"))
        flash("Invalid email or password.", "error")

    return render_template(
        "auth/login.html",
        site_name=get_setting("site_name", "Video Portal"),
    )


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))
