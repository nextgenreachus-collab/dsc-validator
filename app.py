import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pypdf import PdfReader

# Tell Flask to look for index.html in the same folder
app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# Limit uploads to ~25 MB
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_dsc(filepath):
    """Try to detect DSC in the PDF and extract signer names if possible."""
    try:
        reader = PdfReader(filepath)
        names = []

        # --- Method 1: Look in AcroForm fields ---
        try:
            root = reader.trailer["/Root"]
            if "/AcroForm" in root:
                acroform = root["/AcroForm"]
                if "/Fields" in acroform:
                    fields = acroform["/Fields"]
                    for f in fields:
                        fobj = f.get_object()
                        if "/V" in fobj:
                            v = fobj["/V"].get_object()
                            if "/Name" in v:
                                names.append(str(v["/Name"]))
                            elif "/M" in v:
                                names.append(str(v["/M"]))
        except Exception:
            pass

        # --- Method 2: Scan all objects for /Sig ---
        try:
            for obj in reader.objects.values():
                if isinstance(obj, dict) and "/Type" in obj and obj["/Type"] == "/Sig":
                    if "/Name" in obj:
                        names.append(str(obj["/Name"]))
                    elif "/M" in obj:
                        names.append(str(obj["/M"]))
        except Exception:
            pass

        if names:
            return {"status": "Valid", "signers": list(set(names))}
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
