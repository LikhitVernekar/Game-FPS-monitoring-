import serial
import time
import csv
import os
import threading
import datetime

log_file = r"C:\Users\likhi\Documents\HardwareMonitoring.csv"
backup_file = log_file + ".bak"

FPS_INDEX = 91
CPU_TEMP_INDEX = 37
GPU2_TEMP_INDEX = 3
RAM_USAGE_INDEX = 89
TIMESTAMP_INDEX = 1
FPS_TIMEOUT_SECONDS = 10
LINES_TO_KEEP = 1000

arduino = None

def connect_arduino():
    global arduino
    while True:
        try:
            arduino = serial.Serial('COM7', 9600)
            print("✅ Arduino connected.")
            return
        except:
            print("🔌 Waiting for Arduino connection on COM7...")
            time.sleep(3)

def get_latest_stats():
    try:
        if not os.path.exists(log_file):
            return None

        with open(log_file, 'r', encoding='cp1252') as f:
            lines = f.readlines()

        header_found = False
        data_lines = []
        for line in lines:
            row = next(csv.reader([line]))
            if not header_found and "Framerate" in [col.strip() for col in row]:
                header_found = True
                continue
            if header_found:
                data_lines.append(row)

        for row in reversed(data_lines):
            if len(row) > max(FPS_INDEX, CPU_TEMP_INDEX, GPU2_TEMP_INDEX, RAM_USAGE_INDEX):
                fps_str = row[FPS_INDEX].strip()
                cpu_temp_str = row[CPU_TEMP_INDEX].strip()
                gpu2_temp_str = row[GPU2_TEMP_INDEX].strip()
                ram_usage_str = row[RAM_USAGE_INDEX].strip()
                timestamp_str = row[TIMESTAMP_INDEX].strip()

                if not fps_str or fps_str.upper() == "N/A":
                    continue

                try:
                    log_time = datetime.datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
                    now = datetime.datetime.now()
                    if (now - log_time).total_seconds() > FPS_TIMEOUT_SECONDS:
                        return None
                except:
                    return None

                try:
                    fps = int(float(fps_str))
                    cpu_temp = int(float(cpu_temp_str))
                    gpu_temp = int(float(gpu2_temp_str))
                    ram_usage = int(float(ram_usage_str))
                    return fps, cpu_temp, gpu_temp, ram_usage
                except:
                    continue

        return None

    except Exception as e:
        print("❌ Error:", e)
        return None

def clean_log_file():
    try:
        if not os.path.exists(log_file):
            return

        with open(log_file, 'r', encoding='cp1252') as f:
            lines = f.readlines()

        header_index = None
        for i, line in enumerate(lines):
            if "Framerate" in line:
                header_index = i
                break

        if header_index is None:
            return

        header_lines = lines[:header_index + 1]
        data_lines = lines[header_index + 1:]

        if len(data_lines) <= LINES_TO_KEEP:
            return

        with open(backup_file, 'w', encoding='cp1252') as f:
            f.writelines(lines)

        with open(log_file, 'w', encoding='cp1252') as f:
            f.writelines(header_lines + data_lines[-LINES_TO_KEEP:])

        if os.path.exists(backup_file):
            os.remove(backup_file)

        print(f"✅ Cleaned log. Kept last {LINES_TO_KEEP} data rows.")

    except Exception as e:
        print("❌ Error cleaning log file:", e)

def periodic_cleanup():
    clean_log_file()
    threading.Timer(600, periodic_cleanup).start()

# Start
connect_arduino()
periodic_cleanup()

prev_game_running = True  # assume game is running initially

while True:
    stats = get_latest_stats()
    if stats:
        fps, cpu_temp, gpu_temp, ram_usage = stats

        if fps == 0:
            if prev_game_running:
                print("🛑 No game running. FPS is 0.")
                prev_game_running = False
            try:
                arduino.write(b"0,0,0,0\n")
            except:
                connect_arduino()
        else:
            if not prev_game_running:
                print("✅ Game detected. Stats streaming...")
                prev_game_running = True

            print(f"🎮 FPS: {fps}, 🌡️ CPU: {cpu_temp}°C, 🖥️ GPU: {gpu_temp}°C, 🧠 RAM: {ram_usage} MB")
            try:
                arduino.write(f"{fps},{cpu_temp},{gpu_temp},{ram_usage}\n".encode())
            except:
                connect_arduino()
    time.sleep(1.0)
