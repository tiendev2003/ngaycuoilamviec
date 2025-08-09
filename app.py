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
            fullPath = os.path.join(os.getcwd(), result['image_path'].lstrip('/'))
            print(f"Image saved at: {fullPath}")
            print_image(fullPath, printerName)
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


def print_image(image_path: str, printer_name: str = None):
    """In ảnh với tên máy in cụ thể. Tự động xoay và canh giữa ảnh."""

    if not os.path.exists(image_path):
        print(f"❌ Không tìm thấy ảnh: {image_path}")
        return False

    try:
        # Mở ảnh và lấy kích thước
        img = Image.open(image_path)
        img_width, img_height = img.size

        print(f"🖼️ Ảnh: {image_path} ({img_width}x{img_height}px)")

        # Nếu không có tên máy in, dùng mặc định
        if not printer_name:
            printer_name = win32print.GetDefaultPrinter()

        print(f"🖨️ Máy in: {printer_name}")

        # Tạo DC (Device Context)
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)

        # Kích thước giấy in thực tế
        printable_width = hDC.GetDeviceCaps(8)   # HORZRES
        printable_height = hDC.GetDeviceCaps(10) # VERTRES
        print(f"📄 Vùng in: {printable_width}x{printable_height}px")

        # --- Xoay ảnh nếu cần ---
        img_is_portrait = img_height > img_width
        paper_is_portrait = printable_height > printable_width
        if img_is_portrait != paper_is_portrait:
            print("🔄 Đang xoay ảnh 90 độ...")
            img = img.rotate(90, expand=True)
            img_width, img_height = img.size
            print(f"🔁 Ảnh sau khi xoay: {img_width}x{img_height}px")

        # --- Tính kích thước phù hợp để không bị méo ---
        img_aspect = img_width / img_height
        paper_aspect = printable_width / printable_height

        if img_aspect > paper_aspect:
            new_width = printable_width
            new_height = int(new_width / img_aspect)
        else:
            new_height = printable_height
            new_width = int(new_height * img_aspect)

        # Căn giữa ảnh
        x_offset = (printable_width - new_width) // 2
        y_offset = (printable_height - new_height) // 2

        print(f"📐 Kích thước in: {new_width}x{new_height}px | Căn giữa: ({x_offset}, {y_offset})")

        # In
        hDC.StartDoc(image_path)
        hDC.StartPage()
        dib = ImageWin.Dib(img)
        draw_rect = (x_offset, y_offset, x_offset + new_width, y_offset + new_height)
        dib.draw(hDC.GetHandleOutput(), draw_rect)
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()

        print("✅ In thành công.")
        return True

    except Exception as e:
        print(f"❌ Lỗi khi in ảnh: {e}")
        return False





if __name__ == '__main__':
    app.run(host="0.0.0.0",port=4000,debug=False)
