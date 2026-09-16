import os
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from flask import Flask, flash, render_template, request, send_file
from werkzeug.utils import secure_filename

from cipher_engine import decrypt_image, decrypt_text, encrypt_image, encrypt_text

TOKEN_SEPARATOR = chr(1)
DEFAULT_UPLOAD_LIMIT_MB = 20
TMP_ROOT = Path(os.getenv("CIPHERVAULT_TMP_DIR", Path(__file__).resolve().parent / ".tmp"))
TMP_ROOT.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ciphervault-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = (
    int(os.getenv("MAX_UPLOAD_MB", str(DEFAULT_UPLOAD_LIMIT_MB))) * 1024 * 1024
)
ASSET_VERSION = int((Path(__file__).resolve().parent / "static" / "styles.css").stat().st_mtime)


def _render_home(**context):
    defaults = {
        "active_tab": "text",
        "encrypt_input": "",
        "encrypt_output": "",
        "decrypt_input": "",
        "decrypt_output": "",
    }
    defaults.update(context)
    return render_template("index.html", **defaults)


@app.context_processor
def inject_asset_version():
    return {"asset_v": ASSET_VERSION}


def _normalize_cipher_input(value: str) -> str:
    """Allow users to paste tokens separated by spaces/newlines."""
    text = (value or "").strip()
    if not text:
        return ""
    if TOKEN_SEPARATOR in text:
        return text

    tokens = text.split()
    if len(tokens) > 1:
        return TOKEN_SEPARATOR.join(tokens)

    if len(text) % 2 == 0:
        pairs = [text[i : i + 2] for i in range(0, len(text), 2)]
        return TOKEN_SEPARATOR.join(pairs)

    return text


def _response_from_path(path: str, download_name: str, mimetype: str):
    with open(path, "rb") as file_obj:
        payload = BytesIO(file_obj.read())
    payload.seek(0)
    return send_file(
        payload,
        as_attachment=True,
        download_name=download_name,
        mimetype=mimetype,
    )


def _valid_filename(upload_name: str, fallback: str) -> str:
    filename = secure_filename(upload_name or "")
    return filename or fallback


@app.get("/")
def index():
    return _render_home()


@app.post("/text/encrypt")
def text_encrypt():
    plaintext = request.form.get("encrypt_input", "").strip()
    if not plaintext:
        flash("Enter text to encrypt.", "error")
        return _render_home(active_tab="text")

    cipher_raw = encrypt_text(plaintext)
    cipher_for_display = cipher_raw.replace(TOKEN_SEPARATOR, " ")
    return _render_home(
        active_tab="text",
        encrypt_input=plaintext,
        encrypt_output=cipher_for_display,
    )


@app.post("/text/decrypt")
def text_decrypt():
    cipher_text = request.form.get("decrypt_input", "").strip()
    if not cipher_text:
        flash("Enter cipher text to decrypt.", "error")
        return _render_home(active_tab="text")

    normalized = _normalize_cipher_input(cipher_text)
    decrypted = decrypt_text(normalized)
    return _render_home(
        active_tab="text",
        decrypt_input=cipher_text,
        decrypt_output=decrypted,
    )


@app.post("/image/encrypt")
def image_encrypt():
    upload = request.files.get("source_image")
    if upload is None or upload.filename == "":
        flash("Choose an image file to encrypt.", "error")
        return _render_home(active_tab="image")

    filename = _valid_filename(upload.filename, "input.png")
    work_dir = TMP_ROOT / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        source_path = str(work_dir / filename)
        upload.save(source_path)

        try:
            result = encrypt_image(source_path, str(work_dir))
        except Exception as exc:
            flash(str(exc), "error")
            return _render_home(active_tab="image")

        archive_name = f"{Path(filename).stem}_encrypted_bundle.zip"
        archive_path = str(work_dir / archive_name)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(result["actual_path"], arcname=os.path.basename(result["actual_path"]))
            archive.write(result["meta_path"], arcname=os.path.basename(result["meta_path"]))

        return _response_from_path(
            path=archive_path,
            download_name=archive_name,
            mimetype="application/zip",
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.post("/image/decrypt")
def image_decrypt():
    encrypted_image = request.files.get("encrypted_image")
    metadata_file = request.files.get("meta_file")

    if encrypted_image is None or encrypted_image.filename == "":
        flash("Upload the encrypted image (.png).", "error")
        return _render_home(active_tab="image")
    if metadata_file is None or metadata_file.filename == "":
        flash("Upload the matching .meta file.", "error")
        return _render_home(active_tab="image")

    image_name = _valid_filename(encrypted_image.filename, "encrypted.png")

    work_dir = TMP_ROOT / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        image_path = str(work_dir / image_name)
        encrypted_image.save(image_path)

        meta_path = image_path + ".meta"
        metadata_file.save(meta_path)

        try:
            result = decrypt_image(image_path, str(work_dir))
        except Exception as exc:
            flash(str(exc), "error")
            return _render_home(active_tab="image")

        return _response_from_path(
            path=result["actual_path"],
            download_name=result["filename"],
            mimetype="image/png",
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.errorhandler(413)
def file_too_large(_error):
    flash(
        f"File is too large. Limit is {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)} MB.",
        "error",
    )
    return _render_home(active_tab="image"), 413


@app.get("/health")
def health_check():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
