CipherVault Web

CipherVault now runs as a Flask website.

Features

- Text encryption and decryption in browser
- Image encryption (downloads zip with `.png` + `.meta`)
- Image decryption (upload encrypted `.png` + matching `.meta`)
- Health endpoint at `/health`

Project Entry Points

- Web app: `app.py`
- Previous desktop UI: `desktop_app.py`

Run Locally

powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py

Open `http://127.0.0.1:5000`.


Notes

- Uploaded files are processed in temporary folders.
- Max upload size defaults to `20 MB` and can be changed with env var `MAX_UPLOAD_MB`.
- Set `FLASK_SECRET_KEY` in production.
