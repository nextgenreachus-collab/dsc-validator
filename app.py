import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pyhanko.sign import validation
from pyhanko.pdf_utils.reader import PdfFileReader

# Flask setup
app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# Limit uploads to ~25 MB
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_dsc(filepath):
    """Validate DSC signatures using pyHanko."""
    try:
        with open(filepath, "rb") as f:
            r = PdfFileReader(f)

            if not r.embedded_signatures:
                return {"status": "Invalid", "signers": []}

            signers = []
            for sig in r.embedded_signatures:
                status = validation.validate_pdf_signature(sig, r)

                signer_name = "(Unknown)"
                try:
                    signer_name = sig.signer_cert.subject.human_friendly
                except Exception:
                    pass

                signers.append(f"{signer_name} → {status.pretty_print_details()}")

            return {"status": "Valid", "signers": signers}

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
