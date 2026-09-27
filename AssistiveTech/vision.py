import cv2
import time
import subprocess
import threading
from ultralytics import YOLO
import sys
import os

# ==========================================
# CONFIGURATION
# ==========================================

# --- AUDIO CONFIGURATION ---
AUDIO_DIR = "/home/pi4/Desktop/AssistiveTech/sounds/" 

# MAP: What the Code Says -> Which File to Play
AUDIO_MAP = {
    "Stairs Ahead": "Stairs.wav",
    "Vehicle Ahead": "Vehicle.wav",
    "Door Ahead":   "Door.wav",
    "Crowd ahead":  "Crowd ahead.wav",
    "Person left":  "P-left.wav",
    "Person right": "P-right.wav",
    "Person ahead": "P-ahead.wav",
    "System Ready": "System Ready.wav"
}

# 1. LOAD MODEL
model = YOLO("best_ncnn_model", task="detect") 

# 2. CAMERA CONFIGURATION
if len(sys.argv) > 1:
    received_arg = sys.argv[1]
    print(f"Vision module received: {received_arg}")
    
    if received_arg.isdigit():
        URL = int(received_arg) 
    else:
        URL = received_arg       
else:
    PHONE_IP = "192.168.1.2" 
    PORT = "8080"
    URL = f"http://{PHONE_IP}:{PORT}/video"

# 3. TUNING
SKIP_FRAMES = 3     
CONF_THRESHOLD = 0.38
ID_DOOR = 0
ID_PERSON = 1
ID_STAIRS = 2
ID_VEHICLE = 3
PRIORITY_MAP = {"hazard": 3, "nav": 2, "info": 1}

# ==========================================

# Initialize Camera
print(f"Connecting to: {URL}")
cap = cv2.VideoCapture(URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Error: Could not connect to camera.")
    exit()

# State Variables
last_spoken_message = ""
last_speech_time = 0
speech_interval = 3.5 
frame_count = 0
detected_objects = [] 

# FPS Variables (Enabled for Console Logging)
prev_frame_time = 0
fps_display = 0.0

def speak_system(message):
    """Plays the pre-recorded wav file associated with the message"""
    def run():
        try:
            filename = AUDIO_MAP.get(message)
            if filename:
                filepath = os.path.join(AUDIO_DIR, filename)
                if os.path.exists(filepath):
                    subprocess.run(f'paplay "{filepath}"', shell=True)
                else:
                    print(f"⚠️ File missing: {filepath}")
            else:
                print(f"⚠️ No audio mapping for: {message}")
        except Exception as e:
            print(f"Audio Error: {e}")
            
    threading.Thread(target=run, daemon=True).start()

def get_person_position(x1, x2, frame_width):
    center_x = (x1 + x2) / 2
    if center_x < frame_width / 3: return "left"
    elif center_x > 2 * frame_width / 3: return "right"
    else: return "ahead"

print("Starting High-Performance Navigation (Headless)...")
speak_system("System Ready") 

while True:
    # Start Timer for FPS
    new_frame_time = time.time()
    
    ret, frame = cap.read()
    if not ret: break

    # Resize
    frame = cv2.resize(frame, (640, 480))
    height, width = frame.shape[:2]

    # --- FRAME SKIPPING LOGIC ---
    if frame_count % (SKIP_FRAMES + 1) == 0:
        results = model(frame, imgsz=320, conf=CONF_THRESHOLD, verbose=False)
        detected_objects = []
        person_list = []
        
        for box in results[0].boxes:
            cls = int(box.cls[0])
            x1, y1, x2, y2 = box.xyxy[0].int().tolist()
            
            # Note: We do NOT need visual_data for headless
            if cls == ID_STAIRS:
                detected_objects.append((PRIORITY_MAP["hazard"], "Stairs Ahead"))
            elif cls == ID_VEHICLE:
                detected_objects.append((PRIORITY_MAP["hazard"], "Vehicle Ahead"))
            elif cls == ID_DOOR:
                detected_objects.append((PRIORITY_MAP["nav"], "Door Ahead"))
            elif cls == ID_PERSON:
                pos = get_person_position(x1, x2, width)
                person_list.append(pos)

        # Crowd Logic
        if len(person_list) > 3:
            detected_objects.append((PRIORITY_MAP["info"], "Crowd ahead"))
        elif len(person_list) > 0:
            detected_objects.append((PRIORITY_MAP["info"], f"Person {person_list[0]}"))
            
    frame_count += 1

    # --- HEADLESS FPS LOGGING ---
    # We print FPS to terminal every 30 frames instead of drawing on screen
    loop_time = time.time() - new_frame_time
    instant_fps = 1.0 / loop_time if loop_time > 0 else 0
    
    if prev_frame_time == 0:
        fps_display = instant_fps
    else:
        fps_display = (fps_display * 0.9) + (instant_fps * 0.1)
    
    prev_frame_time = new_frame_time
    
    if frame_count % 30 == 0:
        print(f"Status: Running | FPS: {fps_display:.1f}")

    # --- AUDIO LOGIC (FIXED) ---
    current_time = time.time()
    if detected_objects:
        detected_objects.sort(key=lambda x: x[0], reverse=True)
        msg = detected_objects[0][1]
        
        # LOGIC: Speak if it's a NEW message OR if the time interval has passed
        if (msg != last_spoken_message and (current_time - last_speech_time) > 2.5) or (current_time - last_speech_time) > speech_interval:
            print(f"🎤 Speaking: {msg}")
            speak_system(msg)
            last_spoken_message = msg
            last_speech_time = current_time
    else:
        # Reset if silence lasts too long (optional)
        if (current_time - last_speech_time) > 10: 
             last_spoken_message = ""

    # Note: cv2.waitKey is not needed in headless mode if imshow is gone.
    # To stop the script, press Ctrl+C in the terminal.

cap.release()
