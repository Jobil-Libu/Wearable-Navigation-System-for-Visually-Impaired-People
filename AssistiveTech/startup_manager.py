import time
import sys
import subprocess
import glob
import re
import os

# --- CONFIGURATION ---
VENV_PYTHON = "/home/pi4/yolo-env/bin/python3"
APP_FOLDER = "/home/pi4/Desktop/AssistiveTech/"

# --- PIPER TTS CONFIGURATION (ABSOLUTE PATHS) ---
PIPER_BINARY = "/home/pi4/piper/piper"
MODEL_PATH = "/home/pi4/model/voice.onnx"

def speak(text):
    print(f"[SPEAKER] {text}")
    try:
        # Save to RAM (/dev/shm) for instant playback
        wav_file = "/dev/shm/startup_msg.wav"
        
        # 1. Generate Audio
        gen_cmd = f'echo "{text}" | {PIPER_BINARY} --model {MODEL_PATH} --output_file {wav_file}'
        subprocess.run(gen_cmd, shell=True)
        
        # 2. Play Audio
        play_cmd = f'paplay {wav_file}'
        subprocess.run(play_cmd, shell=True)
        
    except Exception as e: 
        print(f"Audio Error: {e}")

def get_esp_port():
    # Looks for USB Serial devices (ESP32/Arduino)
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return ports[0] if ports else None

def get_camera_ip():
    """Attempts to find the Phone Camera IP via Gateway."""
    try:
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
        if match:
            return f"http://{match.group(1)}:8080/video"
    except: 
        pass
    return None

def get_camera_source():
    """
    Priority:
    1. USB Camera (Physical connection, most reliable)
    2. IP Camera (Phone Hotspot)
    """
    # Check for physical USB camera device
    # Usually /dev/video0. If you have multiple, it might be video2.
    if os.path.exists('/dev/video0'):
        print("Found USB Camera at /dev/video0")
        return "0"  # We pass "0" as a string, vision.py handles the rest
    
    # If no USB camera, check IP
    return get_camera_ip()

def main():
    time.sleep(5) 
    speak("System initializing")

    # 1. FIND ESP32 (Sensors)
    esp_port = get_esp_port()
    while esp_port is None:
        speak("Connect Sensors")
        time.sleep(4)
        esp_port = get_esp_port()
     
    speak("Sensors Connected")

    # 2. FIND CAMERA (USB or IP)
    cam_source = get_camera_source()
    while cam_source is None:
        speak("Connect Camera")
        time.sleep(4)
        cam_source = get_camera_source()
    
    if cam_source == "0":
        speak("USB Camera Found")
    else:
        speak("Phone Camera Found")

    # 3. LAUNCH WORKERS
    speak("Starting Navigation")
     
    # Pass the detected source (either "0" or "http://...") to vision.py
    subprocess.Popen([VENV_PYTHON, "vision.py", cam_source], cwd=APP_FOLDER)
     
    # Pass the esp port to ultrasonic.py
    subprocess.Popen([VENV_PYTHON, "ultrasonic.py", esp_port], cwd=APP_FOLDER)

    sys.exit()

if __name__ == "__main__":
    main()
