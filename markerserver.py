import os
from flask import Flask, jsonify, send_file, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 이미지 경로 설정
REAL_DB_PATH = r'C:\Users\khj98\OneDrive\Desktop\DB\real'

# 경로에 있는 파일 목록 반환
@app.route('/get_real_files', methods=['GET'])
def get_real_files():
    files = []
    try:
        for file in os.listdir(REAL_DB_PATH):
            if file.endswith('.jpg'):
                coords = file.replace('.jpg', '').split(',')
                if len(coords) >= 2:  # 파일 이름에 위도, 경도, 숫자 형식이 있는지 확인
                    latitude = coords[0]
                    longitude = coords[1]
                    files.append({
                        "filename": file,
                        "latitude": latitude,
                        "longitude": longitude
                    })
        return jsonify(files), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return abort(500, description="Failed to get file list.")

# 특정 파일을 제공하는 API
@app.route('/real_images/<filename>', methods=['GET'])
def get_image(filename):
    image_path = os.path.join(REAL_DB_PATH, filename)
    try:
        return send_file(image_path, mimetype='image/jpeg')
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return abort(404, description="File not found")
    except Exception as e:
        print(f"Error: {str(e)}")
        return abort(500, description="Failed to load image.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)   