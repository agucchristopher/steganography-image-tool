# this is the flask server that runs the whole app
# basically it takes the html frontend and connects it to the python steganography stuff
# i chose flask because it's super simple and i already knew it from a tutorial lol

import os
import sys
import base64
import tempfile
import threading
import webbrowser
from io import BytesIO
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("[✗] Flask not installed. Run: pip install flask")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("[✗] Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

from steganography import encode_message, decode_message, image_capacity

# figure out where this file lives so we can serve index.html from the same folder
BASE_DIR = Path(__file__).parent
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


# serves the main page - literally just sends index.html
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


# this endpoint takes an image and returns info about it
# like how big it is, dimensions, and how many chars we can hide in it
# also sends back a base64 thumbnail so the frontend can show a preview
@app.route("/api/info", methods=["POST"])
def api_info():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image provided"}), 400

    file = request.files["image"]
    # save to a temp file so we can open it with pillow
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = image_capacity(tmp_path)

        # make a small preview thumbnail and encode it as base64
        # the frontend just sticks this straight into an <img> tag, pretty clean
        img = Image.open(tmp_path).convert("RGB")
        img.thumbnail((400, 300))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        preview_b64 = base64.b64encode(buf.getvalue()).decode()

        result["preview"] = f"data:image/jpeg;base64,{preview_b64}"
        result["filename"] = file.filename
        return jsonify(result)
    finally:
        os.unlink(tmp_path)  # always clean up temp files, don't want junk piling up


# the main encode endpoint - takes an image + message + optional password
# hides the message in the image and sends the new image back as base64
@app.route("/api/encode", methods=["POST"])
def api_encode():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image provided"}), 400

    file    = request.files["image"]
    message = request.form.get("message", "")
    password = request.form.get("password", "")

    if not message.strip():
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    # save the uploaded image to a temp file
    suffix = Path(file.filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
        file.save(tmp_in.name)
        in_path = tmp_in.name

    out_path = in_path + "_stego.png"  # output goes right next to the input

    try:
        result = encode_message(in_path, message, out_path, password)

        if result["success"]:
            # read the stego image back and convert to base64 so browser can download it
            # (browsers can't just read files off the server's filesystem obviously)
            with open(out_path, "rb") as f:
                stego_b64 = base64.b64encode(f.read()).decode()

            # also make a preview thumbnail like in the info endpoint
            img = Image.open(out_path).convert("RGB")
            img.thumbnail((400, 300))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=80)
            preview_b64 = base64.b64encode(buf.getvalue()).decode()

            stem = Path(file.filename).stem
            result["stego_image"] = f"data:image/png;base64,{stego_b64}"
            result["preview"]     = f"data:image/jpeg;base64,{preview_b64}"
            result["filename"]    = f"{stem}_stego.png"  # name the download nicely

        return jsonify(result)
    finally:
        # clean up both temp files no matter what happens
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


# decode endpoint - takes a stego image and digs the hidden message out
# sends the message back as plain text in the json response
@app.route("/api/decode", methods=["POST"])
def api_decode():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image provided"}), 400

    file     = request.files["image"]
    password = request.form.get("password", "")

    suffix = Path(file.filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = decode_message(tmp_path, password)

        # still send a preview even on decode so the user sees the image they uploaded
        img = Image.open(tmp_path).convert("RGB")
        img.thumbnail((400, 300))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        result["preview"] = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        result["filename"] = file.filename

        return jsonify(result)
    finally:
        os.unlink(tmp_path)  # cleanup!


# opens the browser automatically so the user doesn't have to copy paste the url
def open_browser():
    webbrowser.open("http://127.0.0.1:5050")

if __name__ == "__main__":
    print("\n" + "═" * 55)
    print("  🔐  StegoCrypt Server")
    print("  → Open:  http://127.0.0.1:5050")
    print("  → Stop:  Ctrl + C")
    print("═" * 55 + "\n")
    threading.Timer(1.2, open_browser).start()  # small delay so the server starts first
    app.run(host="127.0.0.1", port=5050, debug=False)
