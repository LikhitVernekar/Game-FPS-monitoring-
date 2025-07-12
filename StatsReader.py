import serial
import time
import csv
import os
import threading
import datetime

# Path to MSI Afterburner CSV log file
log_file = r"C:\Users\likhi\Documents\HardwareMonitoring.csv"
backup_file = log_file + ".bak"

FPS_COLUMN_INDEX = 91
TIMESTAMP_COLUMN_INDEX = 1
LINES_TO_KEEP = 1000
FPS_TIMEOUT_SECONDS = 10  # Stale threshold

arduino = None

# --- Try to connect to Arduino repeatedly ---
def connect_arduino():
    global arduino
    while True:
        try:
            arduino = serial.Serial('COM3', 9600)
            print("✅ Arduino connected.")
            return
        except:
            print("🔌 Waiting for Arduino connection on COM3...")
            time.sleep(3)

# --- Function to Get Latest Valid FPS ---
def get_latest_fps():
    try:
        if not os.path.exists(log_file):
            print("❌ Log file not found.")
            return 0

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

        if not data_lines:
            print("⚠️ No data found after header.")
            return 0

        for data_row in reversed(data_lines):
            if len(data_row) > FPS_COLUMN_INDEX:
                fps_value = data_row[FPS_COLUMN_INDEX].strip()
                timestamp_str = data_row[TIMESTAMP_COLUMN_INDEX].strip()

                if not fps_value or fps_value.upper() == "N/A":
                    continue

                try:
                    log_time = datetime.datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
                    now = datetime.datetime.now()
                    if (now - log_time).total_seconds() > FPS_TIMEOUT_SECONDS:
                        return 0
                except:
                    return 0

                return int(float(fps_value))

        return 0

    except Exception as e:
        print("❌ Error reading file:", e)
        return 0

# --- Function to Display Cute Face on Arduino ---
def send_robot_face():
    face = "[o_o]"
    print("🤖 No game running", face)
    try:
        arduino.write(f"{face}\n".encode())
    except:
        print("⚠️ Failed to write to Arduino. Reconnecting...")
        connect_arduino()

# --- Clean Log File (Preserve Header + Last N Data Rows) ---
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
            print("❌ Header not found.")
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

# --- Periodic Cleanup (Every 10 Minutes) ---
def periodic_cleanup():
    clean_log_file()
    threading.Timer(600, periodic_cleanup).start()

# --- Start everything ---
connect_arduino()
periodic_cleanup()

while True:
    fps = get_latest_fps()

    if fps == 0:
        send_robot_face()
    else:
        print(f"🎮 FPS: {fps}")
        try:
            arduino.write(f"{fps}\n".encode())
        except:
            print("⚠️ Failed to write to Arduino. Reconnecting...")
            connect_arduino()

    time.sleep(0.5)
