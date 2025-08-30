import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

# Tell Flask to look for templates in the current folder (.)
app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")  # needed for flash messages

# Limit uploads to ~25 MB
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _extract_signatures_via_acroform(reader):
    """Try to find signatures via AcroForm -> Fields and extract signer names."""
    names = []
    try:
        root = reader.trailer.get("/Root")
        if not root:
            return names
        acroform = root.get("/AcroForm")
        if not acroform:
            return names
        fields = acroform.get("/Fields", [])
        for f in fields:
            try:
                fobj = f.get_object()
                v = fobj.get("/V")
                if v:
                    vobj = v.get_object()
                    name = vobj.get("/Name")
                    if name:
                        names.append(str(name))
                    else:
                        m = vobj.get("/M")
                        if m:
                            names.append(str(m))
            except Exception:
                continue
    except Exception:
        pass
    return names

def _extract_signatures_by_scanning(reader):
    """Fallback: scan resolved_objects for any dicts containing /Sig and try to pull names."""
    names = []
    try:
        for obj in getattr(reader, "resolved_objects", {}).values():
            try:
                if isinstance(obj, dict) and "/Sig" in obj:
                    sig = obj.get("/Sig")
                    if isinstance(sig, dict):
                        name = sig.get("/Name")
                        if name:
                            names.append(str(name))
                        else:
                            m = sig.get("/M")
                            if m:
                                names.append(str(m))
            except Exception:
                continue
    except Exception:
        pass
    return names

def validate_dsc(filepath):
    """Return dict with status and list of signer names (if any)."""
    try:
        reader = PdfReader(filepath)
        names = _extract_signatures_via_acroform(reader)
        if not names:
            names = _extract_signatures_by_scanning(reader)

        if names:
            return {"status": "Valid", "signers": names}
        else:
            return {"status": "Invalid", "signers": []}
    except Exception as e:
        return {"status": "Error", "error": str(e), "signers": []}

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part in request.")
            return redirect(url_for("index"))
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.")
            return redirect(url_for("index"))
        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are supported.")
            return redirect(url_for("index"))

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)

        result = validate_dsc(path)

        # Clean up uploaded file
        try:
            os.remove(path)
        except Exception:
            pass

    return render_template("index.html", result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
