import os, sqlite3, secrets
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash, send_from_directory, jsonify
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("MADAM_DATA_DIR", BASE / "private_data"))
UPLOAD_DIR = DATA_DIR / "photos"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "madam.sqlite3"
ALLOWED = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_BYTES = 12 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            layer TEXT NOT NULL DEFAULT 'pretty',
            tags TEXT NOT NULL DEFAULT '',
            visible INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
init_db()

def logged_in():
    return bool(session.get("admin"))

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def is_allowed(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED

@app.get("/")
def home():
    with db() as con:
        photos = con.execute("SELECT id, caption, layer, tags FROM photos WHERE visible=1 AND layer != 'secret' ORDER BY id DESC").fetchall()
    return render_template("index.html", photos=photos, admin=logged_in())

@app.get("/media/<int:photo_id>")
def media(photo_id):
    with db() as con:
        photo = con.execute("SELECT filename, layer, visible FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not photo or not photo["visible"]:
        abort(404)
    if photo["layer"] == "secret" and not logged_in():
        abort(404)
    return send_from_directory(UPLOAD_DIR, photo["filename"], conditional=True)

@app.get("/admin")
def admin_login():
    if logged_in():
        return redirect(url_for("admin_dashboard"))
    return render_template("admin.html", logged_in=False)

@app.post("/admin/login")
def admin_login_post():
    password = request.form.get("password", "")
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if not password_hash:
        flash("Admin login is not configured yet. Set ADMIN_PASSWORD_HASH in your host's environment variables.", "error")
        return redirect(url_for("admin_login"))
    if check_password_hash(password_hash, password):
        session.clear()
        session["admin"] = True
        return redirect(url_for("admin_dashboard"))
    flash("That password didn't match. Try again.", "error")
    return redirect(url_for("admin_login"))

@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.get("/admin/dashboard")
@admin_required
def admin_dashboard():
    with db() as con:
        photos = con.execute("SELECT * FROM photos ORDER BY id DESC").fetchall()
    return render_template("admin.html", logged_in=True, photos=photos)

@app.post("/admin/upload")
@admin_required
def upload():
    files = request.files.getlist("photos")
    layer = request.form.get("layer", "evidence")
    if layer not in {"evidence", "pretty", "secret"}:
        layer = "evidence"
    caption = request.form.get("caption", "").strip()[:180]
    tags = request.form.get("tags", "").strip()[:240]
    saved = 0
    for file in files:
        if not file or not file.filename or not is_allowed(file.filename):
            continue
        safe = secure_filename(file.filename)
        ext = safe.rsplit(".", 1)[1].lower()
        name = secrets.token_hex(16) + "." + ext
        path = UPLOAD_DIR / name
        file.save(path)
        try:
            with Image.open(path) as img:
                img.verify()
        except Exception:
            path.unlink(missing_ok=True)
            continue
        with db() as con:
            con.execute("INSERT INTO photos(filename, caption, layer, tags) VALUES(?,?,?,?)", (name, caption, layer, tags))
        saved += 1
    flash(f"Added {saved} photo(s)." if saved else "No valid image files were added.", "success" if saved else "error")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/photo/<int:photo_id>/update")
@admin_required
def update_photo(photo_id):
    caption = request.form.get("caption", "").strip()[:180]
    tags = request.form.get("tags", "").strip()[:240]
    layer = request.form.get("layer", "evidence")
    if layer not in {"evidence", "pretty", "secret"}:
        layer = "evidence"
    visible = 1 if request.form.get("visible") == "on" else 0
    with db() as con:
        con.execute("UPDATE photos SET caption=?, tags=?, layer=?, visible=? WHERE id=?", (caption, tags, layer, visible, photo_id))
    flash("Photo details updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/photo/<int:photo_id>/delete")
@admin_required
def delete_photo(photo_id):
    with db() as con:
        photo = con.execute("SELECT filename FROM photos WHERE id=?", (photo_id,)).fetchone()
        if photo:
            (UPLOAD_DIR / photo["filename"]).unlink(missing_ok=True)
            con.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    flash("Photo deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(413)
def too_large(_):
    return "Upload too large. Please keep each upload under 12 MB.", 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
