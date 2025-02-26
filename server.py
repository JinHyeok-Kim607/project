import os
import logging
import subprocess
import hashlib
import time
from smbclient import listdir, register_session, remove
from concurrent.futures import ThreadPoolExecutor

# 로그 설정
logging.basicConfig(
    filename='yolo_samba_test.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s'
)

# Samba 서버 설정
SAMBA_SERVER = '192.168.145.105'
SAMBA_FOLDER = r'\\192.168.145.105\siba\pothole'
samba_username = 'siba'
samba_password = '111111'

# YOLOv5 설정
weights_path = r'C:\Users\khj98\OneDrive\Desktop\포트폴리오\finalproject\pothole.pt'
yolov5_script_path = r'C:\Users\khj98\OneDrive\Desktop\JH\졸작\zz\yolov5-master\yolov5-master\detect.py'

# 데이터베이스 경로
real_db_path = r'C:\Users\khj98\OneDrive\Desktop\DB\real'
fake_db_path = r'C:\Users\khj98\OneDrive\Desktop\DB\fake'

# 처리된 파일 기록
processed_files = {}

# Samba 세션 등록
try:
    register_session(SAMBA_SERVER, username=samba_username, password=samba_password)
    logging.info("Samba 세션 등록 성공")
except Exception as e:
    logging.error(f"Samba 세션 등록 중 오류 발생: {e}")
    exit(1)

def calculate_file_hash(filepath):
    """파일의 해시(MD5) 값을 계산."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_next_exp_folder(base_path='runs/detect'):
    """다음 사용 가능한 exp 폴더 이름을 반환."""
    i = 0
    while True:
        exp_folder = os.path.join(base_path, f'exp{i}' if i > 0 else 'exp')
        if not os.path.exists(exp_folder):
            return exp_folder
        i += 1

def run_yolo(image_path, exp_folder):
    """YOLOv5 모델로 이미지 분석."""
    command = [
        'python', yolov5_script_path, '--source', image_path,
        '--weights', weights_path, '--save-txt', '--save-conf',
        '--project', 'runs/detect', '--name', os.path.basename(exp_folder), '--exist-ok'
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        logging.info(f"YOLOv5 실행 결과: {result.stdout}")
        return result.returncode == 0  # YOLO 실행 성공 여부 반환
    except Exception as e:
        logging.error(f"YOLOv5 실행 중 오류 발생: {str(e)}")
        return False

def increment_filename_if_exists(folder, base_name, extension):
    """파일이 이미 존재할 경우 숫자를 증가시킨 새로운 파일명을 반환."""
    i = 1
    new_filename = f"{base_name},{i}{extension}"
    while os.path.exists(os.path.join(folder, new_filename)):
        i += 1
        new_filename = f"{base_name},{i}{extension}"
    return new_filename

def move_files_based_on_labels(exp_folder):
    """YOLOv5 라벨 여부에 따라 파일을 이동."""
    labels_folder = os.path.join(exp_folder, 'labels')
    detected_files = set(f.replace('.txt', '.jpg') for f in os.listdir(labels_folder)) if os.path.exists(labels_folder) else set()

    for file in os.listdir(exp_folder):
        if file.endswith('.jpg'):
            src_path = os.path.join(exp_folder, file)
            base_name = file.rsplit('.', 1)[0]  # 위도,경도 추출

            if file in detected_files:
                folder_path = real_db_path
                logging.info(f"검출됨: {file}, real 폴더로 이동")
            else:
                folder_path = fake_db_path
                logging.info(f"검출되지 않음: {file}, fake 폴더로 이동")

            new_filename = increment_filename_if_exists(folder_path, base_name, '.jpg')
            dest_path = os.path.join(folder_path, new_filename)
            move_file(src_path, dest_path)

def move_file(src, dest):
    """이미지를 지정된 폴더로 이동."""
    try:
        os.rename(src, dest)
        logging.info(f"{src} -> {dest}로 이동 완료")
    except Exception as e:
        logging.error(f"{src} 이동 중 오류 발생: {str(e)}")

def delete_file_on_samba(file_path):
    """Samba 폴더에서 파일 삭제."""
    try:
        remove(file_path, username=samba_username, password=samba_password)
        logging.info(f"Samba에서 파일 삭제 완료: {file_path}")
    except Exception as e:
        logging.error(f"Samba 파일 삭제 중 오류 발생: {file_path}, {str(e)}")

def process_image(file):
    """이미지 처리."""
    exp_folder = get_next_exp_folder()  # 다음 사용 가능한 exp 폴더 계산
    if run_yolo(file, exp_folder):  # YOLO 실행 성공 시
        move_files_based_on_labels(exp_folder)  # 결과에 따라 파일 이동
        delete_file_on_samba(file)  # Samba 폴더에서 원본 파일 삭제
    else:
        logging.warning(f"YOLO 실행 실패: {file}, 파일 삭제 안 함")

def test_yolo_on_samba_files():
    """Samba 폴더에서 이미지 파일 처리."""
    try:
        file_list = listdir(SAMBA_FOLDER, username=samba_username, password=samba_password)
        logging.info(f"Samba 폴더에서 읽은 파일 목록: {file_list}")

        with ThreadPoolExecutor() as executor:
            futures = []
            for file in file_list:
                if file.endswith('.jpg'):
                    image_path = os.path.join(SAMBA_FOLDER, file)
                    file_hash = calculate_file_hash(image_path)  # 파일 해시 계산

                    # 이미 처리된 파일인지 확인
                    if file in processed_files and processed_files[file] == file_hash:
                        logging.info(f"이미 처리된 파일: {file}, 건너뜀")
                        continue  # 중복 파일은 건너뜀

                    # 처리 시작 (병렬로 수행)
                    futures.append(executor.submit(process_image, image_path))

                    # 처리된 파일로 기록
                    processed_files[file] = file_hash

            # 작업이 모두 완료될 때까지 대기
            for future in futures:
                future.result()
    except Exception as e:
        logging.error(f"파일 처리 중 오류 발생: {str(e)}")

def start_server(interval=5):
    """서버가 계속 실행되도록 설정."""
    while True:
        test_yolo_on_samba_files()
        time.sleep(interval)  # interval(초)마다 반복

if __name__ == '__main__':
    start_server()
