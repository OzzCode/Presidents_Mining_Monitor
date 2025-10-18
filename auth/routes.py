from __future__ import annotations
import functools
import os
from typing import Any, Dict, Optional

from flask import (
    Blueprint, request, render_template, redirect, url_for, session, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash

from core.db import SessionLocal, User

auth_bp = Blueprint("auth", __name__)


# -----------------------------
# Helpers
# -----------------------------

def current_user() -> Optional[User]:
    uid = session.get("user_id")
    if not uid:
        return None
    s = SessionLocal()
    try:
        # SQLAlchemy 2.x: Query API still available via Session.query
        return s.query(User).filter(User.id == uid).first()
    finally:
        s.close()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user_id"):
            next_url = request.url
            return redirect(url_for("auth.login", next=next_url))
        return view(**kwargs)

    return wrapped_view


@auth_bp.before_app_request
def load_user_into_g():
    # Make current user available in templates as g.user
    try:
        g.user = current_user()
    except Exception:
        g.user = None


# -----------------------------
# Routes
# -----------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        s = SessionLocal()
        try:
            user = s.query(User).filter(User.username == username).first()
            if user and check_password_hash(user.password_hash, password):
                session["user_id"] = user.id
                session.permanent = True  # follow app.permanent_session_lifetime if set
                # Honor user default landing if set in preferences
                default_landing = None
                try:
                    prefs = user.preferences or {}
                    ui_prefs = prefs.get("ui") or {}
                    dl = ui_prefs.get("default_landing")
                    if isinstance(dl, str) and dl.strip():
                        default_landing = dl.strip()
                except Exception:
                    default_landing = None
                dest = request.args.get("next") or default_landing or url_for("dashboard.index")
                return redirect(dest)
            else:
                error = "Invalid username or password"
        finally:
            s.close()

    return render_template("login.html", error=error)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not username or not password:
            error = "Username and password are required"
        elif password != confirm:
            error = "Passwords do not match"
        else:
            s = SessionLocal()
            try:
                exists = s.query(User).filter(User.username == username).first()
                if exists:
                    error = "Username already taken"
                else:
                    user = User(
                        username=username,
                        password_hash=generate_password_hash(password),
                        preferences={"favorite_miners": [], "theme": "system"},
                    )
                    s.add(user)
                    s.commit()
                    session["user_id"] = user.id
                    return redirect(url_for("dashboard.index"))
            finally:
                s.close()

    return render_template("register.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("auth.login"))


# -----------------------------
# Preferences API (simple MVP)
# -----------------------------

@auth_bp.route("/api/user/preferences", methods=["GET", "POST"])  # mounted at /auth
def user_preferences():
    if not session.get("user_id"):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    s = SessionLocal()
    try:
        user = s.query(User).filter(User.id == session["user_id"]).first()
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        if request.method == "GET":
            # Merge user prefs with sensible defaults (non-destructive)
            defaults = {
                "ui": {
                    "theme": "system",
                    "density": "comfortable",
                    "default_landing": "/dashboard",
                    "default_fresh_minutes": 30,
                },
                "dashboard": {
                    "hidden_cards": []
                },
                "miners": {
                    "favorites": []
                },
                "discovery": {
                    "profiles": [],
                    "default_profile": None
                }
            }
            prefs = user.preferences or {}
            # shallow + 1-level deep merge for common namespaces
            merged = {**defaults}
            for k, v in prefs.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    mv = {**merged[k]}
                    mv.update(v)
                    merged[k] = mv
                else:
                    merged[k] = v
            return jsonify({"ok": True, "preferences": merged})

        # POST: merge/replace preferences
        data: Dict[str, Any] = request.get_json(silent=True) or {}
        prefs = user.preferences or {}
        # Shallow merge for MVP
        prefs.update(data)
        user.preferences = prefs
        s.add(user)
        s.commit()
        return jsonify({"ok": True, "preferences": user.preferences})
    finally:
        s.close()
