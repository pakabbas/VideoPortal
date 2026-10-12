from flask import Blueprint

bp = Blueprint("videos", __name__, url_prefix="/videos")

from app.videos import routes  # noqa: E402, F401
