from flask import Blueprint

bp = Blueprint("agreements", __name__, url_prefix="/agreements")

from app.agreements import routes  # noqa: E402, F401
