from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "manager", "farmer"), nullable=False)
    mobile_no = db.Column(db.String(64), nullable=True)
    id_card_no = db.Column(db.String(128), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"

    @property
    def is_farmer(self) -> bool:
        return self.role == "farmer"


class ManagerFarmer(db.Model):
    __tablename__ = "manager_farmers"

    id = db.Column(db.Integer, primary_key=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    manager = db.relationship("User", foreign_keys=[manager_id])
    farmer = db.relationship("User", foreign_keys=[farmer_id])


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(512), nullable=False)
    stored_path = db.Column(db.String(1024), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum("uploaded", "ready"), nullable=False, default="uploaded")
    recorded_at = db.Column(db.DateTime, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ready_at = db.Column(db.DateTime, nullable=True)

    farmer = db.relationship("User", foreign_keys=[farmer_id])
    uploader = db.relationship("User", foreign_keys=[uploader_id])


class UploadConsent(db.Model):
    __tablename__ = "upload_consents"

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    terms_version = db.Column(db.String(64), nullable=False)


class ManagerAgreement(db.Model):
    __tablename__ = "manager_agreements"

    id = db.Column(db.Integer, primary_key=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    docusign_envelope_id = db.Column(db.String(128), nullable=True)
    status = db.Column(
        db.Enum("pending", "completed", "declined"), nullable=False, default="pending"
    )
    signed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    manager = db.relationship("User", foreign_keys=[manager_id])


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
