import serial
import time
import pygame
import statistics
import sys
from collections import deque

# --- GET PORT FROM MANAGER ---
if len(sys.argv) < 2:
    print("Error: Port not provided. Run via startup_manager.")
    exit()

SERIAL_PORT = sys.argv[1] # <--- The Manager sent this!
BAUD_RATE = 115200

# DISTANCE & VOLUME
MAX_DIST = 50           # Max detection distance (cm)
MIN_DIST = 5            # Max volume distance (cm)
MAX_VOLUME = 0.35       # Cap volume at 35%

# PRIORITY SETTING
# 0.0 = Sides are completely silent when Front is active (Hard Priority)
# 0.2 = Sides play at 20% volume when Front is active (Soft Priority/Ducking)
SIDE_DUCKING_FACTOR = 0.2 

# SMOOTHING
WINDOW_SIZE = 5          
DECAY_RATE = 0.02   

# --- SETUP AUDIO ---
pygame.mixer.init()
pygame.mixer.set_num_channels(8)
BASE = "/home/pi4/Desktop/AssistiveTech/"
# Load SOUNDS (Ensure these files exist!)
side_sound = pygame.mixer.Sound(BASE+"alert.mp3")       
center_sound = pygame.mixer.Sound(BASE+"beep.mp3") 

left_channel = pygame.mixer.Channel(0)
right_channel = pygame.mixer.Channel(1)
center_channel = pygame.mixer.Channel(2) 

# --- SETUP SERIAL ---
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"Connected to {SERIAL_PORT}. Priority Mode: FRONT")
except Exception as e:
    print(f"Error: {e}")
    exit()

# --- MEMORY ---
hist_L = deque(maxlen=WINDOW_SIZE)
hist_C = deque(maxlen=WINDOW_SIZE)
hist_R = deque(maxlen=WINDOW_SIZE)
vol_L, vol_C, vol_R = 0.0, 0.0, 0.0

def get_target_volume(distance):
    if distance > MAX_DIST: return 0.0
    if distance < MIN_DIST: return MAX_VOLUME 
    scale = 1.0 - ((distance - MIN_DIST) / (MAX_DIST - MIN_DIST))
    return scale * MAX_VOLUME

def process_decay(current_vol, target_vol):
    if target_vol > current_vol: return target_vol 
    elif current_vol > target_vol:
        new_vol = current_vol - DECAY_RATE
        if new_vol < target_vol: new_vol = target_vol
        return max(0.0, min(MAX_VOLUME, new_vol))
    return current_vol

try:
    while True:
        if arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8').strip()
                if not line: continue
                
                parts = list(map(int, line.split(',')))
                
                if len(parts) == 3:
                    raw_L, raw_C, raw_R = parts

                    # 1. Calculate RAW Target Volumes (Before Priority)
                    hist_L.append(raw_L)
                    hist_C.append(raw_C)
                    hist_R.append(raw_R)
                    
                    target_L = get_target_volume(statistics.median(hist_L))
                    target_C = get_target_volume(statistics.median(hist_C))
                    target_R = get_target_volume(statistics.median(hist_R))

                    # 2. Process Decay (Smoothness)
                    vol_L = process_decay(vol_L, target_L)
                    vol_C = process_decay(vol_C, target_C)
                    vol_R = process_decay(vol_R, target_R)

                    # --- 3. PRIORITY LOGIC (The New Part) ---
                    # If Center volume is active, suppress the sides
                    if vol_C > 0.01:
                        vol_L = vol_L * SIDE_DUCKING_FACTOR
                        vol_R = vol_R * SIDE_DUCKING_FACTOR
                    
                    # --- 4. PLAY AUDIO ---

                    # LEFT CHANNEL
                    if vol_L > 0.01:
                        left_channel.set_volume(vol_L, 0.0) 
                        if not left_channel.get_busy(): left_channel.play(side_sound, loops=-1)
                    else:
                        left_channel.stop()

                    # CENTER CHANNEL (Front = Stereo + Priority)
                    if vol_C > 0.01:
                        center_channel.set_volume(vol_C, vol_C) 
                        if not center_channel.get_busy(): center_channel.play(center_sound, loops=-1)
                    else:
                        center_channel.stop()

                    # RIGHT CHANNEL
                    if vol_R > 0.01:
                        right_channel.set_volume(0.0, vol_R) 
                        if not right_channel.get_busy(): right_channel.play(side_sound, loops=-1)
                    else:
                        right_channel.stop()

                    # Debug Print
                    print(f"L:{int(vol_L*100)}% | CENTER (PRIORITY):{int(vol_C*100)}% | R:{int(vol_R*100)}%")

            except ValueError:
                pass 
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Stopping...")
    left_channel.stop(); right_channel.stop(); center_channel.stop()
    arduino.close()
    pygame.quit()
