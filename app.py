from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import uuid
import time
import socket  # Import socket module
from config import SERVER_IP  # Import SERVER_IP
from PIL import Image
import subprocess


import sys, os
from flask import Flask

def resource_path(relative_path):
    """Lấy đường dẫn thực khi chạy cả file .py và .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Add win32api and win32print for direct printing
try:
    import win32print
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static')
)

CORS(app)


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a public server to get local IP
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost if unable to get actual IP


def _download_and_save_image(image_url):
    """Helper function to download and save an image."""
    start_time = time.time()
    response = requests.get(image_url)
    response.raise_for_status()

    file_extension = image_url.split('.')[-1]
    if '?' in file_extension:
        file_extension = file_extension.split('?')[0]
    if not file_extension or len(file_extension) > 5:
        file_extension = 'jpg'

    filename = f"{uuid.uuid4()}.{file_extension}"
    filepath = os.path.join('outputs', filename)

    with open(filepath, 'wb') as f:
        f.write(response.content)

    end_time = time.time()
    download_time = round(end_time - start_time, 2)
    return {"image_path": f"/outputs/{filename}", "download_time": download_time}


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/download_image', methods=['POST'])
def download_image():
    data = request.get_json()
    image_url = data.get('url')
    if not image_url:
        return jsonify({"error": "URL is required"}), 400

    local_machine_ip = get_local_ip()
    print(f"Local Machine IP: {local_machine_ip}")

    try:
        if local_machine_ip == SERVER_IP:
            print("This is the designated server. Performing local download.")
            result = _download_and_save_image(image_url)
            return jsonify({"message": "Image downloaded successfully", **result}), 200
        else:
            print(f"This is not the designated server. Forwarding request to {SERVER_IP}.")
            # Forward the request to the designated server
            forward_url = f"http://{SERVER_IP}:5000/download_image"  # Assuming Flask runs on port 5000
            forward_response = requests.post(forward_url, json={'url': image_url})
            forward_response.raise_for_status()  # Raise an exception for HTTP errors from the forwarded request
            return jsonify(forward_response.json()), forward_response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/outputs/<filename>')
def serve_downloaded_image(filename):
    return send_from_directory('outputs', filename)

@app.route('/print_image', methods=['POST'])
def print_image():
    data = request.get_json()
    image_path = data.get('image_path')

    if not image_path:
        return jsonify({"error": "Image path is required"}), 400

    # Ensure the path is relative to the outputs directory
    if image_path.startswith('/outputs/'):
        filename = image_path.replace('/outputs/', '')
    else:
        filename = image_path # Assume it's just the filename if not starting with /outputs/

    full_image_path = os.path.join(os.getcwd(), 'outputs', filename)

    if not os.path.exists(full_image_path):
        return jsonify({"error": "Image not found"}), 404

    try:
        # Convert image to PDF
        pdf_path = full_image_path + '.pdf'
        with Image.open(full_image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(pdf_path, "PDF", resolution=100.0)
        # Use Windows print command
        print_cmd = f'print /d:"{win32print.GetDefaultPrinter()}" "{pdf_path}"'
        result = subprocess.run(print_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({"message": f"Sent {filename} (as PDF) to printer automatically."}), 200
        else:
            return jsonify({"error": f"Print command failed: {result.stderr}"}), 500
    except Exception as e:
        print(f"Error printing image: {str(e)}")
        return jsonify({"error": f"Failed to print image: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
