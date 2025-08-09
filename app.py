from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import uuid
import time
import socket  # Import socket module
from config import SERVER_IP  # Import SERVER_IP
import win32ui
from PIL import Image, ImageWin  # Import PIL for image handling


import sys, os
from flask import Flask


 # tạo folder outputs nếu chưa tồn tại
if not os.path.exists('outputs'):
    os.makedirs('outputs')

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


@app.route('/api/print', methods=['POST'])
def download_image():
    data = request.get_json()
    image_url = data.get('filePath')
    printerName = data.get('printerName')

    
    if not image_url:
        return jsonify({"error": "URL is required"}), 400

    local_machine_ip = get_local_ip()
    print(f"Local Machine IP: {local_machine_ip}")

    try:
        if local_machine_ip == SERVER_IP:
            print("This is the designated server. Performing local download.")
            result = _download_and_save_image(image_url)
            relative_path = result['image_path'].replace('/', os.sep).replace('\\', os.sep).lstrip(os.sep)
            full_path = os.path.join(os.getcwd(), relative_path)

            print(f"Image saved at: {full_path}")
            print_image(full_path, printerName)
            return jsonify({"message": "Image downloaded successfully", **result}), 200
        else:
            print(f"This is not the designated server. Forwarding request to {SERVER_IP}.")
            # Forward the request to the designated server
            forward_url = f"http://{SERVER_IP}:4000/api/print"  # Assuming Flask runs on port 5000
            forward_response = requests.post(forward_url, json={'filePath': image_url, 'printerName': printerName})
            forward_response.raise_for_status()  # Raise an exception for HTTP errors from the forwarded request
            return jsonify(forward_response.json()), forward_response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/outputs/<filename>')
def serve_downloaded_image(filename):
    return send_from_directory('outputs', filename)


def print_image(image_path: str, printer_name: str = None):
    """In ảnh sử dụng lệnh rundll32 shimgvw.dll,ImageView_PrintTo."""
    import subprocess
    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy ảnh: {image_path}")
        return False
    try:
        cmd = f"rundll32.exe C:\\Windows\\System32\\shimgvw.dll,ImageView_PrintTo /pt \"{image_path}\" \"{printer_name}\""
        print(f"Chạy lệnh: {cmd}")
        completed = subprocess.run(cmd, shell=False)
        if completed.returncode == 0:
            print("✅ In thành công.")
            return True
        else:
            print(f"❌ Lỗi khi in ảnh, mã lỗi: {completed.returncode}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi in ảnh: {e}")
        return False





if __name__ == '__main__':
    app.run(host="0.0.0.0",port=4000,debug=False)
