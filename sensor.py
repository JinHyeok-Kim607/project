import time
import board
import busio
import adafruit_adxl34x
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import cv2
import os
import gps

# I2C 인터페이스 초기화
i2c = busio.I2C(board.SCL, board.SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)

# GPS 세션 시작
session = gps.gps(mode=gps.WATCH_ENABLE)

# 웹캠 초기화 및 버퍼 크기 설정
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기를 1로 설정하여 최신 프레임만 유지

# 데이터 버퍼 초기화
xdata, ydata, zdata = [], [], []
frame_count = 50  # 그래프에 표시할 데이터 프레임 수

fig, ax = plt.subplots()
ln_x, = ax.plot([], [], 'r-', label='X-axis')
ln_y, = ax.plot([], [], 'g-', label='Y-axis')
ln_z, = ax.plot([], [], 'b-', label='Z-axis')
ax.set_xlim(0, frame_count)
ax.set_ylim(-20, 20)
ax.legend()
ax.set_title("Real-time ADXL345 Acceleration")
ax.set_xlabel("Time (frames)")
ax.set_ylabel("Acceleration (g)")

# 초기값 저장 변수
initial_y, initial_z = None, None
initial_setup_done = False

# 사진 저장 경로
save_directory = "/home/siba/pothole"
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

def get_gps_data(timeout=10):
    """GPS 데이터를 가져오는 함수, 지정된 시간 동안 기다림"""
    start_time = time.time()
    while True:
        report = session.next()
        if report['class'] == 'TPV':
            if hasattr(report, 'lat') and hasattr(report, 'lon'):
                return report.lat, report.lon
        if time.time() - start_time > timeout:
            print("GPS Timeout: Unable to get GPS data within the timeout period.")
            return None, None
        time.sleep(1)  # GPS 데이터를 받기 전에 잠시 대기

def init():
    ax.set_xlim(0, frame_count)
    ax.set_ylim(-20, 20)
    return ln_x, ln_y, ln_z,

def update(frame):
    global initial_y, initial_z, initial_setup_done

    try:
        # 가속도 값 읽기
        x, y, z = accelerometer.acceleration

        # 초기값 설정
        if not initial_setup_done:
            initial_y, initial_z = y, z
            initial_setup_done = True

        # 데이터 저장 및 그래프 업데이트
        xdata.append(x)
        ydata.append(y)
        zdata.append(z)
        if len(xdata) > frame_count:
            xdata.pop(0)
            ydata.pop(0)
            zdata.pop(0)
        ln_x.set_data(range(len(xdata)), xdata)
        ln_y.set_data(range(len(ydata)), ydata)
        ln_z.set_data(range(len(zdata)), zdata)

        # 조건: 초기 Y축 값보다 2.0 이상 크고, 초기 Z축 값보다 -0.5보다 작을 때
        if initial_y is not None and initial_z is not None:
            if y > initial_y + 2.0 and z < initial_z - 0.5:
                print(f"Condition Met! X: {x:.2f}g, Y: {y:.2f}g, Z: {z:.2f}g")
               
                # 조건이 충족되었을 때 GPS 데이터 가져오기
                lat, lon = get_gps_data(timeout=10)  # GPS 데이터를 10초 동안 대기하며 가져옴
                if lat is not None and lon is not None:
                    lat_str = f"{lat:.6f}"
                    lon_str = f"{lon:.6f}"
                else:
                    lat_str, lon_str = "unknown", "unknown"

                # 조건이 충족되었을 때 웹캠 촬영
                time.sleep(0.1)  # 차량이 지나가고 난 후 (0.1초 지연)

                # 버퍼 비우기 (최신 프레임을 얻기 위해 여러 번 읽어들임)
                for _ in range(5):
                    cap.read()

                # 최신 프레임 캡처
                ret, frame = cap.read()
                if ret:
                    # 파일 이름을 위도와 경도로만 저장
                    filename = os.path.join(save_directory, f"{lat_str},{lon_str}.jpg")
                    cv2.imwrite(filename, frame)
                    print(f"Saved image: {filename}")

    except Exception as e:
        print(f"Error: {e}")

    return ln_x, ln_y, ln_z,

# 그래프 실시간 애니메이션
ani = FuncAnimation(fig, update, init_func=init, blit=True, interval=100)

plt.show()

# 웹캠 자원 해제
cap.release()
cv2.destroyAllWindows()