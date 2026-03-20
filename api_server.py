"""
api_server.py
Flask API wrapping generate_pdf.py for Railway / n8n Cloud.
GET  /health         → {"status": "ok"}
POST /generate-pdf   → {"success": true, "pdf_base64": "...", "size_kb": N}
"""
import io, os, sys, base64, traceback
from pathlib import Path
from flask import Flask, request, jsonify

sys.path.insert(0, str(Path(__file__).parent))
import generate_pdf as pdf_gen

app = Flask(__name__)
IMG_DIR = os.environ.get("IMG_DIR", str(Path(__file__).parent))

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "pdf-generator"}), 200

@app.route("/generate-pdf", methods=["POST"])
def generate_pdf_endpoint():
    try:
        body     = request.get_json(silent=True) or {}
        filename = body.get("output_filename", "Economic_Growth_and_Development.pdf")
        out_path = str(Path(IMG_DIR) / filename)
        pdf_gen.generate(output_path=out_path, img_dir=IMG_DIR)
        with open(out_path, "rb") as f:
            pdf_bytes = f.read()
        return jsonify({
            "success":    True,
            "filename":   filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
            "size_kb":    len(pdf_bytes) // 1024,
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting on port {port} | IMG_DIR={IMG_DIR}")
    app.run(host="0.0.0.0", port=port, debug=False)
