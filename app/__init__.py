from pathlib import Path

from flask import Flask, redirect, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    # Trust nginx proxy headers when behind reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    application_root = app.config.get("APPLICATION_ROOT", "/videoportal")
    if application_root and application_root != "/":
        app.config["APPLICATION_ROOT"] = application_root
        app.config["SESSION_COOKIE_PATH"] = application_root

        class PrefixMiddleware:
            def __init__(self, wsgi_app, prefix):
                self.app = wsgi_app
                self.prefix = prefix.rstrip("/")

            def __call__(self, environ, start_response):
                path = environ.get("PATH_INFO", "")
                script = environ.get("SCRIPT_NAME", "")
                # When nginx strips the prefix via proxy_pass .../, SCRIPT_NAME may be empty
                if path.startswith(self.prefix):
                    environ["SCRIPT_NAME"] = self.prefix
                    environ["PATH_INFO"] = path[len(self.prefix) :] or "/"
                elif script.startswith(self.prefix):
                    pass
                return self.app(environ, start_response)

        app.wsgi_app = PrefixMiddleware(app.wsgi_app, application_root)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.admin import bp as admin_bp
    from app.agreements import bp as agreements_bp
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.videos import bp as videos_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(agreements_bp)

    @app.context_processor
    def inject_globals():
        from app.services.settings import get_setting

        root = app.config.get("APPLICATION_ROOT", "")
        return {
            "site_name": get_setting("site_name", "Video Portal"),
            "support_contact": get_setting("support_contact", ""),
            "app_root": root if root != "/" else "",
        }

    @app.errorhandler(403)
    def forbidden(_e):
        from flask import render_template

        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        from flask import render_template

        return render_template("errors/404.html"), 404

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    @app.cli.command("init-db")
    def init_db_command():
        """Create tables and seed admin + default settings."""
        with app.app_context():
            db.create_all()
            from app.services.settings import ensure_default_settings

            ensure_default_settings()
            admin = User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first()
            if not admin:
                admin = User(
                    email=app.config["ADMIN_EMAIL"],
                    full_name=app.config["ADMIN_NAME"],
                    role="admin",
                )
                admin.set_password(app.config["ADMIN_PASSWORD"])
                db.session.add(admin)
                db.session.commit()
                print(f"Created admin: {admin.email}")
            else:
                print(f"Admin already exists: {admin.email}")

    return app
