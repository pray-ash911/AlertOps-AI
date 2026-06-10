import cv2
import os
import time
import traceback
import requests
import urllib.parse
import numpy as np
import threading
import time
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import localtime
from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required
from .models import EventLog, EventType, EventEvidence, SurveillanceArea, Lift, LiftUsage, LiftDetection
from django.contrib.auth import login, logout
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect


# Initialize global variables
WEAPON_MODEL = None
CROWD_MODEL = None
WEAPON_EVENT_TYPE_OBJ = None
WEAPON_EVENT_TYPE_ID = None
OVERCROWDING_EVENT_TYPE_OBJ = None
OVERCROWDING_EVENT_TYPE_ID = None

try:
    from ultralytics import YOLO
    import torch
    import os

    print("Ultralytics YOLO imported successfully.")

    # MODEL 1: WEAPON DETECTION 
    MODEL_FILE_NAME_WEAPON = 'best (1).pt'
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MODEL_PATH_WEAPON = os.path.join(PROJECT_ROOT, 'models', MODEL_FILE_NAME_WEAPON)

    # MODEL 2: OVERCROWDING DETECTION 
    MODEL_FILE_NAME_CROWD = 'yolov8m.pt'
    MODEL_PATH_CROWD = os.path.join(PROJECT_ROOT, 'models', MODEL_FILE_NAME_CROWD)

    # Check CUDA and set device
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")

    if torch.cuda.is_available():
        print(f"CUDA Available: {torch.cuda.is_available()}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")

    # Load weapon detection model
    if not os.path.exists(MODEL_PATH_WEAPON):
        print(f"ERROR: Model file not found at: {MODEL_PATH_WEAPON}")
        WEAPON_MODEL = None
    else:
        try:
            WEAPON_MODEL = YOLO(MODEL_PATH_WEAPON)
            WEAPON_MODEL.to(device)
            print(f"YOLO (Weapon Detection) Model loaded successfully on: {WEAPON_MODEL.device}")
        except Exception as e:
            print(f"ERROR loading YOLO model: {e}")
            WEAPON_MODEL = None

    # Load crowd detection model
    try:
        CROWD_MODEL = YOLO(MODEL_PATH_CROWD)
        CROWD_MODEL.to(device)
        print(f"YOLO (Overcrowding Detection) Model loaded successfully on: {CROWD_MODEL.device}")
    except Exception as e:
        print(f"ERROR loading YOLO crowd model: {e}")
        CROWD_MODEL = None

    # Verify GPU placement
    if torch.cuda.is_available():
        print(f"Weapon Model on GPU: {next(WEAPON_MODEL.model.parameters()).device}")
        if CROWD_MODEL:
            print(f"Crowd Model on GPU: {next(CROWD_MODEL.model.parameters()).device}")

    """
    CONFIGURATION FOR WEAPON DETECTION
    Skip 2 frames between inference runs so YOLO doesn't block every frame.
    The last annotated result is reused for display on non-inference frames,
    keeping the stream smooth while still detecting at ~10 inferences/sec.
    """
    INFERENCE_SKIP_FRAMES = 2  # Run YOLO on 1 out of every 3 frames
    FIREARM_KEYWORDS = ['gun', 'pistol', 'handgun', 'rifle', 'firearm', 'revolver', 'shotgun']
    BLADE_KEYWORDS = ['knife', 'dagger', 'machete', 'sword', 'blade']
    WEAPON_KEYWORDS = FIREARM_KEYWORDS + BLADE_KEYWORDS

    # Detection thresholds
    WEAPON_LOG_CONFIDENCE = 0.60  # Visual drawing threshold
    WEAPON_DETECTION_CONFIDENCE = 0.60  # Alert threshold
    LOG_COOLDOWN_SECONDS = 3

    # CONFIGURATION FOR OVERCROWDING DETECTION 
    OVERCROWDING_THRESHOLD = 3
    CROWD_CONFIDENCE_THRESHOLD = 0.25
    CROWD_LOG_COOLDOWN_SECONDS = 15

    # Debug info
    if WEAPON_MODEL:
        print(f"Weapon Model Names: {list(WEAPON_MODEL.names.values())}")
    if CROWD_MODEL:
        print(f"Crowd Model Names: {list(CROWD_MODEL.names.values())}")

except Exception as e:
    WEAPON_MODEL = None
    CROWD_MODEL = None
    WEAPON_EVENT_TYPE_OBJ = None
    WEAPON_EVENT_TYPE_ID = None
    OVERCROWDING_EVENT_TYPE_OBJ = None
    OVERCROWDING_EVENT_TYPE_ID = None
    print(f"CRITICAL ERROR initializing YOLO models: {e}")
    import traceback

    traceback.print_exc()

"""
SHARED GLOBAL CAMERA CACHE (Synchronous)
Windows DirectShow (COM) can corrupt frames if a camera is passed between or
initialized in isolated Python background threads. This synchronous, globally
locked approach forces all HTTP requests to share a single read/inference cycle
inside Django's native worker threads, bypassing the threading bug.
"""
class SharedCamera:
    """Globally caches the camera device and the latest processed frame."""
    _camera = None
    _lock = threading.Lock()
    
    # State tracking
    _latest_jpeg = None
    _last_frame_time = 0
    
    # Alert state shared globally across all clients
    _global_person_count = 0
    _last_weapon_alert_time = 0
    _last_crowd_alert_time = 0
    _weapon_event_type = None
    _crowd_event_type = None
    _weapon_streak = 0  # Track consecutive detections to filter false positives

    @classmethod
    def get_camera(cls):
        """Returns the opened camera instance, opening it if necessary."""
        if cls._camera is None or not cls._camera.isOpened():
            for idx in range(3):
                cap = cv2.VideoCapture(idx + cv2.CAP_DSHOW)
                if cap.isOpened():
                    # Must read a frame before setting properties to lock format
                    ret, _ = cap.read()
                    if ret:
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        print(f"[SharedCamera] Camera opened at index {idx}")
                        cls._camera = cap
                        return cap
                    cap.release()
        return cls._camera

    @classmethod
    def release_camera(cls):
        if cls._camera:
            cls._camera.release()
            cls._camera = None


#  Utility Function for Home Route
def home(request):
    """ Simple Django view for health check. """
    return HttpResponse("<h1>AI Surveillance System Backend is Running (Weapon & Overcrowding Detection Core)!</h1>")


if WEAPON_MODEL:
    print("\n WEAPON MODEL CLASSES ")
    for idx, name in WEAPON_MODEL.names.items():
        print(f"  Class {idx}: '{name}'")

# Helper function to get or create the 'WEAPON' EventType 
def get_or_create_weapon_event_type():
    """
     Helper function to retrieve the 'WEAPON' EventType from the database,
    creating it if it doesn't exist. This function should be called only
    when needed, after Django has initialized the database connection.

    Query Parameters:
    - No parameters required

    Returns: EventType object for 'WEAPON' or None if error occurs
    """
    global WEAPON_EVENT_TYPE_OBJ, WEAPON_EVENT_TYPE_ID  # Access the global variables
    try:
        if WEAPON_EVENT_TYPE_OBJ is None:  # Only fetch/create if not already done
            weapon_event_type, created = EventType.objects.get_or_create(
                name='WEAPON',
                defaults={'description': 'A weapon (e.g., gun, knife) has been detected.'}
            )
            WEAPON_EVENT_TYPE_OBJ = weapon_event_type  # Store the object
            WEAPON_EVENT_TYPE_ID = weapon_event_type.type_id  # Store the ID
            if created:
                print(f"Created new EventType: {weapon_event_type.name} (ID: {WEAPON_EVENT_TYPE_ID})")
            else:
                print(f"Found existing EventType: {weapon_event_type.name} (ID: {WEAPON_EVENT_TYPE_ID})")
        return WEAPON_EVENT_TYPE_OBJ
    except Exception as e:
        print(f"ERROR in get_or_create_weapon_event_type: {e}")
        traceback.print_exc()
        return None


# Helper function to get or create the 'OVERCROWDING' EventType 
def get_or_create_overcrowding_event_type():
    """
    Helper function to retrieve the 'OVERCROWDING' EventType from the database,
    creating it if it doesn't exist. This function should be called only
    when needed, after Django has initialized the database connection.

    Query Parameters:
    - No parameters required

    Returns: EventType object for 'OVERCROWDING' or None if error occurs
    """
    global OVERCROWDING_EVENT_TYPE_OBJ, OVERCROWDING_EVENT_TYPE_ID  # Access the global variables
    try:
        if OVERCROWDING_EVENT_TYPE_OBJ is None:  # Only fetch/create if not already done
            overcrowding_event_type, created = EventType.objects.get_or_create(
                name='OVERCROWDING',
                defaults={'description': 'The number of people in the area exceeds the defined threshold.'}
            )
            OVERCROWDING_EVENT_TYPE_OBJ = overcrowding_event_type  # Store the object
            OVERCROWDING_EVENT_TYPE_ID = overcrowding_event_type.type_id  # Store the ID
            if created:
                print(f"Created new EventType: {overcrowding_event_type.name} (ID: {OVERCROWDING_EVENT_TYPE_ID})")
            else:
                print(f"Found existing EventType: {overcrowding_event_type.name} (ID: {OVERCROWDING_EVENT_TYPE_ID})")
        return OVERCROWDING_EVENT_TYPE_OBJ
    except Exception as e:
        print(f"ERROR in get_or_create_overcrowding_event_type: {e}")
        traceback.print_exc()
        return None


# 1. GOOGLE FORMS Configuration and Utility
FIELD_ID_IMAGE = "entry.1296951995"  # Alert Snapshot Image URL
FIELD_ID_TYPE = "entry.272940768"  # Alert Type Detected (WEAPON or OVERCROWDING)
FIELD_ID_VALUE = "entry.1032598549"  # Confidence Score / People Count
FIELD_ID_TIME = "entry.779047139"  # Incident Timestamp

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdSTffgdV_TPqxJ-fyRxe_gaZ9BPoyqtVpp5kwP-Iu62QmZ0w/formResponse"

# URLs for different access levels
NGROK_URL = "https://fb8a6d4a7b29.ngrok-free.app"
LOCAL_URL = "http://127.0.0.1:8000"


def send_google_form_alert(snapshot_relative_path, label, confidence):
    """
    Sends alert to Google Forms with proper formatting

    snapshot_relative_path: e.g., "weapon_123456.jpg"
    label: e.g., "WEAPON_FIREARM", "WEAPON_BLADE", "WEAPON_UNKNOWN_WEAPON", "OVERCROWDING"
    confidence: float for weapons (0.85), int for overcrowding (15)
    """
    # Skip if ngrok not configured
    if "ngrok-free.app" not in NGROK_URL:
        print(f"Alert suppressed: NGROK_URL = {NGROK_URL}")
        return False

    try:        # 1. Construct Image URL 
        safe_path = urllib.parse.quote(snapshot_relative_path)
        image_url = f"{NGROK_URL}{settings.MEDIA_URL}{safe_path}"

        # 2. Determine ALERT TYPE for Google Form 
        alert_type = "WEAPON_UNKNOWN (Unknown weapon type)"  

        if "WEAPON_FIREARM" in label:
            alert_type = "WEAPON_FIREARM (Gun detected)"
        elif "WEAPON_BLADE" in label:
            alert_type = "WEAPON_BLADE (Knife detected)"
        elif "OVERCROWDING" in label:
            alert_type = "OVERCROWDING (Too many people)"

        # 3. Format VALUE based on alert type
        if alert_type == "OVERCROWDING":
            # For overcrowding: send "15" or "15 people"
            alert_value = f"{int(confidence)}"  # Just the number
        else:
            # For weapons: send "0.85"
            alert_value = f"{float(confidence):.2f}"

        # 4. Format timestamp
        timestamp = localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')

        # 5. Create payload 
        payload = {
            FIELD_ID_IMAGE: image_url,
            FIELD_ID_TYPE: alert_type, 
            FIELD_ID_VALUE: alert_value,
            FIELD_ID_TIME: timestamp,
        }

        print(f"\n SENDING GOOGLE FORM ALERT:")
        print(f"   Alert Type: {alert_type}")
        print(f"   Value: {alert_value}")
        print(f"   Image: {image_url}")
        print(f"   Time: {timestamp}")

        # 6. Send to Google Forms
        response = requests.post(
            GOOGLE_FORM_URL,
            data=payload,
            timeout=10,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        # Check response
        if response.status_code == 200:
            print(f"Alert sent successfully!")
            return True
        else:
            print(f"Failed! Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"Error sending alert: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# 2. REAL-TIME STREAMING — Synchronous lock pattern
def generate_frames():
    """
    HTTP streaming generator matching original native execution context.
    Safely locks the single global webcam to process the frame and inference.
    If multiple clients stream simultaneously, only one fetches/processes at 
    a time; others serve directly from the high-speed cache.
    """
    if WEAPON_MODEL is None or CROWD_MODEL is None:
        error_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_img, "Models not loaded", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        error_frame = cv2.imencode('.jpg', error_img)[1].tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
        return

    # Exclusion config
    EXCLUDE_KEYWORDS = [
        'bottle', 'cell phone', 'phone', 'remote', 'banana',
        'scissors', 'toothbrush', 'tooth', 'brush', 'water bottle',
        'bottle of water', 'cup', 'glass', 'mug', 'can', 'container',
        'pencil', 'pen', 'marker', 'crayon', 'ruler', 'eraser',
        'spoon', 'fork', 'chopstick', 'straw',
        'key', 'keychain', 'wallet', 'card',
        'flashlight', 'remote control', 'comb', 'hairbrush'
    ]

    def is_valid_weapon(class_name, confidence, box_area=None):
        class_lower = class_name.lower()
        for excl in EXCLUDE_KEYWORDS:
            if excl in class_lower: return False
        
        weapon_keywords = FIREARM_KEYWORDS + BLADE_KEYWORDS
        for weapon in weapon_keywords:
            if weapon in class_lower:
                if weapon in ['knife', 'dagger'] and confidence < 0.60:
                    return False
                if weapon in FIREARM_KEYWORDS and confidence < 0.60:
                    return False
                return True
        
        if 'weapon' in class_lower:
            if confidence > 0.88:
                return True
            return False
            
        if box_area:
            if box_area < 200:
                return False
                
        return False

    TARGET_FRAME_INTERVAL = 1.0 / 30

    while True:
        loop_start = time.time()
        jpeg_to_send = None
        
        # Enter globally locked execution context 
        with SharedCamera._lock:
            current_time = time.time()
            
            # If multiple clients are streaming, prevent frame stealing by serving 
            # the most recent processed JPEG if it's extremely fresh (< 0.033s for 30fps)
            time_since_last_frame = current_time - SharedCamera._last_frame_time
            if SharedCamera._latest_jpeg is not None and time_since_last_frame < 0.03:
                jpeg_to_send = SharedCamera._latest_jpeg
            else:
                # We need to process a fresh frame
                cap = SharedCamera.get_camera()
                if cap is not None:
                    # Clear out the driver buffer by grabbing a few frames (improves realtime latency)
                    for _ in range(2):
                        cap.grab()
                    ret, frame = cap.retrieve()
                    
                    if not ret:
                        SharedCamera.release_camera()
                    else:
                        display = frame.copy()
                        alert_triggered = False
                        
                        # Lazy-load models and event types inside active request loop
                        if SharedCamera._weapon_event_type is None:
                            try:
                                SharedCamera._weapon_event_type = get_or_create_weapon_event_type()
                                SharedCamera._crowd_event_type = get_or_create_overcrowding_event_type()
                            except Exception as e:
                                print(f"ERROR: Failed to load event types: {e}")

                        # Maintain state for drawing 
                        if not hasattr(SharedCamera, '_executor_weapon'):
                            from concurrent.futures import ThreadPoolExecutor
                            SharedCamera._executor_weapon = ThreadPoolExecutor(max_workers=1)
                            SharedCamera._executor_crowd = ThreadPoolExecutor(max_workers=1)
                            SharedCamera._future_weapon = None
                            SharedCamera._future_crowd = None
                            SharedCamera._last_weapon_dets = []
                            SharedCamera._last_crowd_dets = []
                            SharedCamera._last_annotated = None
                            SharedCamera._alert_queued = False

                        """
                        YOLO PROCESS (Background Async)
                        Dispatches YOLO to isolated background threads to guarantee True 30FPS streaming.
                        This prevents the slow AI inference from blocking the fast HTTP video stream.
                        """
                        
                        # Weapon Inference Thread
                        # Check if no weapon detection is currently running, OR if the previous one has finished
                        if SharedCamera._future_weapon is None or SharedCamera._future_weapon.done():
                            
                            # If a previous detection just finished, let's collect its results
                            if SharedCamera._future_weapon is not None:
                                try:
                                    # Get the results from the background thread
                                    w_res = SharedCamera._future_weapon.result()
                                    SharedCamera._last_weapon_dets = [] # Clear old detections
                                    
                                    # If YOLO found something, extract boxes, confidences, and classes
                                    if w_res and w_res[0] and len(w_res[0].boxes) > 0:
                                        wr = w_res[0]
                                        w_confs = wr.boxes.conf.cpu().numpy()
                                        w_classes = wr.boxes.cls.int().cpu().tolist()
                                        w_boxes = wr.boxes.xyxy.cpu().numpy()
                                        
                                        # Save detections to the shared state to be drawn on the live feed
                                        for idx, (conf, cls) in enumerate(zip(w_confs, w_classes)):
                                            SharedCamera._last_weapon_dets.append({'box': w_boxes[idx], 'conf': conf, 'cls': cls})
                                            
                                    # Signal the system to check if these new detections should trigger an alert
                                    SharedCamera._alert_queued = True
                                except Exception as e:
                                    print(f"Weapon YOLO Processing error: {e}")

                            # Helper function to actually run the YOLO model
                            def _run_weapon(frm):
                                return WEAPON_MODEL.predict(frm, verbose=False, conf=WEAPON_LOG_CONFIDENCE, iou=0.45)
                                                            
                            # Immediately dispatch a NEW background task with the current frame
                            SharedCamera._future_weapon = SharedCamera._executor_weapon.submit(_run_weapon, frame.copy())

                        # Crowd Inference Thread
                        # Check if no crowd detection is currently running, OR if the previous one has finished
                        if SharedCamera._future_crowd is None or SharedCamera._future_crowd.done():
                            
                            # If a previous detection just finished, let's collect its results
                            if SharedCamera._future_crowd is not None:
                                try:
                                    # Get the results from the background thread
                                    c_res = SharedCamera._future_crowd.result()
                                    SharedCamera._last_crowd_dets = [] # Clear old detections
                                    
                                    # If YOLO found something, extract people (class 0 in COCO dataset)
                                    if c_res and c_res[0] and len(c_res[0].boxes) > 0:
                                        person_dets = [{'box': c_res[0].boxes.xyxy[i].cpu().numpy(),
                                                        'conf': c_res[0].boxes.conf[i].item()}
                                                       for i in range(len(c_res[0].boxes)) 
                                                       if int(c_res[0].boxes.cls[i].item()) == 0] # 0 = 'person' class
                                        
                                        # Save person detections to the shared state to be drawn on the live feed
                                        SharedCamera._last_crowd_dets = person_dets
                                except Exception as e:
                                    print(f"Crowd YOLO Processing error: {e}")

                            # Helper function to actually run the YOLO model
                            def _run_crowd(frm):
                                return CROWD_MODEL.predict(frm, verbose=False, conf=0.25)
                                
                            # Immediately dispatch a NEW background task with the current frame
                            SharedCamera._future_crowd = SharedCamera._executor_crowd.submit(_run_crowd, frame.copy())                

                        # Draw detections on current frame 
                        last_annotated = display.copy()
                        
                        # Draw Crowd
                        if SharedCamera._last_crowd_dets:
                            for d in SharedCamera._last_crowd_dets:
                                x1, y1, x2, y2 = map(int, d['box'])
                                cv2.rectangle(last_annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(last_annotated, f"Person:{d['conf']:.2f}", (x1, y1-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

                        # Draw Weapons
                        if SharedCamera._last_weapon_dets:
                            for w in SharedCamera._last_weapon_dets:
                                x1, y1, x2, y2 = map(int, w['box'])
                                class_name = WEAPON_MODEL.names.get(w['cls'], 'unknown')
                                cv2.rectangle(last_annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                cv2.putText(last_annotated, f"{class_name}:{w['conf']:.2f}", (x1, y1-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)

                        # Focus purely on logging alerts when async inference resolves 
                        if getattr(SharedCamera, '_alert_queued', False):
                            SharedCamera._alert_queued = False

                            # Weapon Alerts
                            # Apply the exact filter that prevents false positives
                            if SharedCamera._weapon_event_type and SharedCamera._last_weapon_dets:
                                for w in SharedCamera._last_weapon_dets:
                                    conf = w['conf']
                                    cls = w['cls']
                                    w_box = w['box']
                                    class_name = WEAPON_MODEL.names.get(cls, 'unknown')
                                    class_lower = class_name.lower()

                                    x1, y1, x2, y2 = w_box
                                    area = (x2 - x1) * (y2 - y1)
                                    
                                    print(f"DEBUG [RAW_DETECTION]: {class_name} conf={conf:.3f} area={area}")

                                    if not is_valid_weapon(class_name, conf, area):
                                        print(f"DEBUG [FILTERED_OUT]: {class_name} failed is_valid_weapon check")
                                        continue

                                    print(f"[WEAPON] Detected: {class_name} conf={conf:.3f} area={area}")

                                    # Determine weapon type
                                    if any(k in class_lower for k in FIREARM_KEYWORDS):
                                        ftype = 'FIREARM'
                                    elif any(k in class_lower for k in BLADE_KEYWORDS):
                                        ftype = 'BLADE'
                                    else:
                                        ftype = 'UNKNOWN'

                                    label = f'WEAPON_{ftype}'

                                    # Show overlay on live feed immediately
                                    cv2.putText(last_annotated if last_annotated is not None else display,
                                                f"!!! {label}: {conf:.2f} !!!", (10, 50),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)

                                    # Log to DB (respecting cooldown to avoid spam)
                                    if current_time - SharedCamera._last_weapon_alert_time > LOG_COOLDOWN_SECONDS and not alert_triggered:
                                        snap_dir = settings.MEDIA_ROOT
                                        os.makedirs(snap_dir, exist_ok=True)
                                        fname = f"{label}_{int(current_time)}.jpg"
                                        snap_img = last_annotated if last_annotated is not None else display
                                        cv2.imwrite(os.path.join(snap_dir, fname), snap_img)
                                        ev = EventLog.objects.create(
                                            type=SharedCamera._weapon_event_type,
                                            timestamp=timezone.now(),
                                            confidence_value=conf
                                        )
                                        EventEvidence.objects.create(log=ev, file_path=fname, file_type='image/jpeg')
                                        send_google_form_alert(fname, label, conf)
                                        SharedCamera._last_weapon_alert_time = current_time
                                        alert_triggered = True
                                        print(f"[WEAPON ALERT] Logged {label} at conf={conf:.3f}, saved {fname}")


                            # Crowd Alerts
                            p_count = 0
                            if SharedCamera._last_crowd_dets:
                                p_count = len(SharedCamera._last_crowd_dets)

                            SharedCamera._global_person_count = p_count

                            if p_count > OVERCROWDING_THRESHOLD and not alert_triggered and SharedCamera._crowd_event_type:
                                if current_time - SharedCamera._last_crowd_alert_time > CROWD_LOG_COOLDOWN_SECONDS:
                                    snap_dir = settings.MEDIA_ROOT
                                    os.makedirs(snap_dir, exist_ok=True)
                                    fname = f"OVERCROWDING{p_count}{int(current_time)}.jpg"
                                    snap_img = last_annotated if last_annotated is not None else display
                                    cv2.imwrite(os.path.join(snap_dir, fname), snap_img)
                                    ev = EventLog.objects.create(type=SharedCamera._crowd_event_type,
                                                                 timestamp=timezone.now(),
                                                                 confidence_value=p_count)
                                    EventEvidence.objects.create(log=ev, file_path=fname, file_type='image/jpeg')
                                    send_google_form_alert(fname, 'OVERCROWDING', p_count)
                                    SharedCamera._last_crowd_alert_time = current_time
                                    alert_triggered = True
                                if last_annotated is not None:
                                    cv2.putText(last_annotated, f"!!! OVERCROWDING: {p_count}/{OVERCROWDING_THRESHOLD} !!!",
                                                (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,165,255), 3)

                        # Finalize output overlay
                        output = last_annotated.copy() if last_annotated is not None else display
                        cv2.putText(output, f"People: {SharedCamera._global_person_count} (Threshold: {OVERCROWDING_THRESHOLD})",
                                    (10, output.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                        # Encode to JPEG and cache it!
                        ret, buffer = cv2.imencode('.jpg', output, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        if ret:
                            SharedCamera._latest_jpeg = buffer.tobytes()
                            SharedCamera._last_frame_time = current_time
                            jpeg_to_send = SharedCamera._latest_jpeg

        """
        Yield frame outside the lock so we don't hold it during network transmission.
        This sends the final, annotated JPEG to the web browser.
        It's yielded as a multipart stream (MJPEG), which HTML <img> tags understand natively.
        """
        if jpeg_to_send:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg_to_send + b'\r\n')
        else:
            # Fallback graphic if the camera failed to capture a frame
            err = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(err, "Camera Unavailable", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buf = cv2.imencode('.jpg', err)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

        """
        Frame Rate Limiting (Throttle HTTP delivery)
        We calculate how long this whole iteration took. 
        If it was faster than 1/30th of a second (TARGET_FRAME_INTERVAL), we sleep for the remaining time.
        This guarantees exactly 30 FPS, preventing the server from spamming the browser and wasting bandwidth.
        """
        elapsed = time.time() - loop_start
        sleep = max(0, TARGET_FRAME_INTERVAL - elapsed)
        if sleep > 0:
            time.sleep(sleep)


@api_view(['GET'])
@permission_classes([AllowAny])
def video_feed_view(request):
    """
    This view returns a StreamingHttpResponse that streams the weapon/crowd detection feed.

    Query Parameters:
    - request: HTTP request object

    Returns: StreamingHttpResponse with MJPEG stream or error response if models not loaded   
    """
    if WEAPON_MODEL is None or CROWD_MODEL is None:  # Check if both models are loaded
        return HttpResponse('Detection Models failed to load.', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# Updated Event Logs View using EventLog and EventEvidence 
@api_view(['GET'])
@permission_classes([AllowAny])
def event_logs_view(request):
    """ 
    Returns a JSON list of all logged events for the dashboard.

    Query Parameters:
    - request: HTTP request object

    Returns: JSON response containing list of recent events (limited to 100) with their details    
    """
    try:
        # Query EventLog entries, joining with EventType and prefetching EventEvidence
        events = EventLog.objects.select_related('type', 'area').prefetch_related('evidence').all().order_by(
            '-timestamp')[:100]

        data = []
        for event in events:
            local_timestamp = localtime(event.timestamp)

            # Get the first piece of evidence (snapshot) for this event
            evidence = event.evidence.first()
            snapshot_url = None
            snapshot_path = None
            if evidence:
                snapshot_path = evidence.file_path  # Get the relative path from EventEvidence
                # Generate public snapshot URL for dashboard 
                if NGROK_URL != "https://YOUR-COPIED-NGROK-URL-HERE" and NGROK_URL != "YOUR_NGROK_OR_PUBLIC_URL_HERE":
                    safe_path = urllib.parse.quote(snapshot_path)
                    snapshot_url = f"{NGROK_URL}{settings.MEDIA_URL}{safe_path}"

            data.append({
                'id': event.log_id,  # Use the primary key from EventLog
                'timestamp': local_timestamp.isoformat(),
                'label': event.type.name,  # Get the name from the related EventType
                'confidence': event.confidence_value,
                # Use confidence_value from EventLog (Conf for WEAPON, Count for CROWD)
                'snapshot_url': snapshot_url,
                'snapshot_path': snapshot_path,  # Include the path from EventEvidence
            })

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in event_logs_view: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Updated Latest Status View using EventLog (Handles Weapon & Overcrowding) 
@api_view(['GET'])
@permission_classes([AllowAny])
def get_latest_status(request):
    """
    API endpoint for Streamlit to poll for the most recent alert status.

    Query Parameters:
    - request: HTTP request object

    Returns: JSON response containing status_level, message, and confidence values for the most recent event    """
    try:
        # Query the latest EventLog entry
        latest_event = EventLog.objects.select_related('type').latest('timestamp')  # Join with EventType
        alert_window = timedelta(seconds=30)
        is_recent_alert = (timezone.now() - latest_event.timestamp) < alert_window

        # Check if the latest event is a 'WEAPON' or 'OVERCROWDING' event
        event_type_name = latest_event.type.name.upper()
        is_monitored_alert = event_type_name in ['WEAPON', 'OVERCROWDING']

        local_timestamp = localtime(latest_event.timestamp)

        if is_recent_alert and is_monitored_alert:
            # Customize message based on event type
            if event_type_name == 'WEAPON':
                message_details = f"Conf: {latest_event.confidence_value:.2f}"
            elif event_type_name == 'OVERCROWDING':
                # For overcrowding, confidence_value holds the count
                message_details = f"Count: {int(latest_event.confidence_value)}"

            status_data = {
                'status_level': 'ALERT',  # consistent single quotes
                'message': f"!!! {event_type_name} DETECTED at {local_timestamp.strftime('%H:%M:%S')} ({message_details}) !!!",
                'confidence': latest_event.confidence_value
            }
        else:
            status_data = {
                'status_level': 'OK',
                'message': 'System operational. Monitoring live stream.',
                'confidence': 0.0
            }

    # Catch the DoesNotExist exception from EventLog
    except EventLog.DoesNotExist:
        status_data = {
            'status_level': 'IDLE',
            'message': 'System operational. Waiting for first event log.',
            'confidence': 0.0
        }
    except Exception as e:
        print(f"Error in get_latest_status: {e}")
        traceback.print_exc()
        status_data = {
            'status_level': 'ERROR',
            'message': f'System Error: {str(e)}',
            'confidence': 0.0
        }

    return JsonResponse(status_data, safe=False)


# Analytics View for Monthly Trends 
@api_view(['GET'])
@permission_classes([AllowAny])
def analytics_view(request):
    """
    Returns JSON data for monthly trends (last 30 days) of events grouped by date and type.

    Query Parameters:
    - request: HTTP request object

    Returns: JSON response containing daily and hourly analytics data, recent events, type distribution, and summary statistics    
    """
    try:
        # Calculate the date 30 days ago
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Query EventLog for the last 30 days, filter by WEAPON and OVERCROWDING types
        events = EventLog.objects.filter(
            timestamp__gte=thirty_days_ago,
            type__name__in=['WEAPON', 'OVERCROWDING']
        ).annotate(
            date=TruncDate('timestamp')
        ).values('date', 'type__name').annotate(
            count=Count('log_id')
        ).order_by('date', 'type__name')

        # Prepare data for JSON response
        data = {}
        for event in events:
            date_str = event['date'].strftime('%Y-%m-%d')  # Format as date only
            event_type = event['type__name']
            count = event['count']

            if date_str not in data:
                data[date_str] = {'date': date_str, 'weapon': 0, 'overcrowding': 0, 'total_detections': 0}

            if event_type == 'WEAPON':
                data[date_str]['weapon'] = count
                data[date_str]['total_detections'] += count
            elif event_type == 'OVERCROWDING':
                data[date_str]['overcrowding'] = count
                data[date_str]['total_detections'] += count

        # Convert to list and sort by date
        result = sorted(data.values(), key=lambda x: x['date'])

        # Get hourly data (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)

        # Get weapon events for hourly data
        weapon_hourly = EventLog.objects.filter(
            timestamp__gte=seven_days_ago,
            type__name='WEAPON'
        ).extra({
            'hour': "EXTRACT(HOUR FROM timestamp)"
        }).values('hour').annotate(
            count=Count('log_id')
        ).order_by('hour')

        # Get overcrowding events for hourly data
        crowd_hourly = EventLog.objects.filter(
            timestamp__gte=seven_days_ago,
            type__name='OVERCROWDING'
        ).extra({
            'hour': "EXTRACT(HOUR FROM timestamp)"
        }).values('hour').annotate(
            count=Count('log_id')
        ).order_by('hour')

        # Prepare hourly data structure
        hourly_data = []
        for hour in range(24):
            weapon_count = next((item['count'] for item in weapon_hourly if int(item['hour']) == hour), 0)
            crowd_count = next((item['count'] for item in crowd_hourly if int(item['hour']) == hour), 0)

            hourly_data.append({
                'hour': hour,
                'weapon': weapon_count,
                'overcrowding': crowd_count,
                'total': weapon_count + crowd_count
            })

        # Calculate summary statistics
        total_weapons = sum(item['weapon'] for item in result)
        total_overcrowding = sum(item['overcrowding'] for item in result)

        # Find peak hour
        if hourly_data:
            peak_hour_item = max(hourly_data, key=lambda x: x['total'])
            peak_hour = peak_hour_item['hour']
            peak_weapon = peak_hour_item['weapon']
            peak_crowd = peak_hour_item['overcrowding']
        else:
            peak_hour = 14  # Default peak hour
            peak_weapon = 0
            peak_crowd = 0

        # Get recent events
        recent_events = EventLog.objects.filter(
            timestamp__gte=thirty_days_ago
        ).select_related('type').order_by('-timestamp')[:10].values(
            'log_id',
            'timestamp',
            'type__name',
            'confidence_value',
            'status'
        )

        # Convert timestamps to string format
        recent_events_list = []
        for event in recent_events:
            event_dict = dict(event)
            event_dict['timestamp'] = event_dict['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            recent_events_list.append(event_dict)

        # Get today's counts
        today = timezone.now().date()
        today_weapon = EventLog.objects.filter(
            timestamp__date=today,
            type__name='WEAPON'
        ).count()

        today_crowd = EventLog.objects.filter(
            timestamp__date=today,
            type__name='OVERCROWDING'
        ).count()

        # Get event type distribution
        type_distribution = EventLog.objects.filter(
            timestamp__gte=thirty_days_ago
        ).values('type__name').annotate(
            count=Count('log_id')
        )

        response_data = {
            'daily_analytics': result,
            'hourly_analytics': hourly_data,
            'recent_events': recent_events_list,
            'type_distribution': list(type_distribution),
            'summary': {
                'total_weapons': total_weapons,
                'total_overcrowding': total_overcrowding,
                'total_all': total_weapons + total_overcrowding,
                'date_range': {
                    'start': thirty_days_ago.strftime('%Y-%m-%d'),
                    'end': timezone.now().strftime('%Y-%m-%d')
                },
                'peak_hour': f"{int(peak_hour):02d}:00",
                'peak_hour_weapon': peak_weapon,
                'peak_hour_crowd': peak_crowd,
                'avg_daily_weapons': round(total_weapons / max(len(result), 1), 1),
                'avg_daily_crowd': round(total_overcrowding / max(len(result), 1), 1),
                'today_weapon': today_weapon,
                'today_crowd': today_crowd
            }
        }

        return JsonResponse(response_data, safe=False, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in analytics_view: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return sample data for development
        return JsonResponse({
            'daily_analytics': generate_sample_daily_data(),
            'hourly_analytics': generate_sample_hourly_data(),
            'recent_events': generate_sample_recent_events(),
            'type_distribution': [
                {'type__name': 'WEAPON', 'count': 45},
                {'type__name': 'OVERCROWDING', 'count': 120}
            ],
            'summary': {
                'total_weapons': 45,
                'total_overcrowding': 120,
                'total_all': 165,
                'date_range': {
                    'start': (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'end': timezone.now().strftime('%Y-%m-%d')
                },
                'peak_hour': "14:00",
                'peak_hour_weapon': 8,
                'peak_hour_crowd': 15,
                'avg_daily_weapons': 1.5,
                'avg_daily_crowd': 4.0,
                'today_weapon': 2,
                'today_crowd': 8
            }
        }, status=status.HTTP_200_OK)


def generate_sample_daily_data():
    """
    Generate sample daily analytics data 

    Query Parameters:
    - No parameters required

    Returns: List of dictionaries containing sample daily detection data for the last 30 days    
    """
    import random
    from datetime import datetime, timedelta

    analytics_data = []
    end_date = datetime.now().date()

    for i in range(30):
        date = end_date - timedelta(days=30 - i - 1)

        # Generate realistic data with patterns
        if date.weekday() in [4, 5]:  # Friday, Saturday
            weapon = random.randint(0, 5)
            crowd = random.randint(5, 15)
        # Sundays moderate
        elif date.weekday() == 6:  # Sunday
            weapon = random.randint(0, 3)
            crowd = random.randint(3, 10)
        # Weekdays
        else:
            weapon = random.randint(0, 3)
            crowd = random.randint(2, 8)

        # Add some trend
        if i > 20:  # Last 10 days
            weapon += random.randint(0, 2)
            crowd += random.randint(0, 5)

        analytics_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'weapon': weapon,
            'overcrowding': crowd,
            'total_detections': weapon + crowd
        })

    return analytics_data


def generate_sample_hourly_data():
    """
    Generate sample hourly data 

    Query Parameters:
    - No parameters required

    Returns: List of dictionaries containing sample hourly detection data for 24 hours    
    """
    import random

    hourly_data = []

    for hour in range(24):
        # Peak hours 9 AM to 9 PM
        if 9 <= hour <= 21:
            weapon = random.randint(0, 3)
            crowd = random.randint(2, 10)
        # Off-peak hours
        else:
            weapon = random.randint(0, 1)
            crowd = random.randint(0, 3)

        hourly_data.append({
            'hour': hour,
            'weapon': weapon,
            'overcrowding': crowd,
            'total': weapon + crowd
        })

    return hourly_data


def generate_sample_recent_events():
    """
    Generate sample recent events 

    Query Parameters:
    - No parameters required

    Returns: List of dictionaries containing sample recent event data    
    """
    import random
    from datetime import datetime, timedelta

    recent_events = []
    event_types = ['WEAPON', 'OVERCROWDING']
    statuses = ['NEW', 'REVIEWED', 'CLOSED']

    for i in range(10):
        event_time = datetime.now() - timedelta(hours=random.randint(0, 72))
        event_type = random.choice(event_types)

        if event_type == 'WEAPON':
            confidence = round(random.uniform(0.65, 0.95), 2)
        else:
            confidence = random.randint(5, 25)  # Count for overcrowding

        recent_events.append({
            'log_id': 1000 + i,
            'timestamp': event_time.strftime('%Y-%m-%d %H:%M:%S'),
            'type__name': event_type,
            'confidence_value': confidence,
            'status': random.choice(statuses)
        })

    return recent_events

# 5. AUTHENTICATION VIEWS (Login & Register for Admin Users)
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
     Register a new admin user.

    GET /api/register/ - Redirects to registration page
    POST /api/register/
    Body: {
        "username": "admin",
        "email": "admin@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "first_name": "Admin",
        "last_name": "User"
    }

    Query Parameters:
    - request: HTTP request object containing user registration data

    Returns: 
        - GET: Redirect to registration page
        - POST: Response with user data and success message (201) or validation errors (400)
    """
    if request.method == 'GET':
        from django.shortcuts import redirect
        return redirect('register_page')

    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        # Don't auto-login, redirect to login page
        # Return user info (excluding password)
        user_data = UserSerializer(user).data
        return Response({
            'message': 'User registered successfully. Please login.',
            'user': user_data,
            'redirect': '/login/'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login an admin user.

    GET /api/login/ - Redirects to login page
    POST /api/login/
    Body: {
        "email": "admin@example.com" or "username": "admin",
        "password": "password123"
    }

    Query Parameters:
    - request: HTTP request object containing user login data

    Returns: 
        - GET: Redirect to login page
        - POST: Response with user data and success message (200) or validation errors (400)
    """
    if request.method == 'GET':
        from django.shortcuts import redirect
        return redirect('login_page')

    serializer = UserLoginSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)

        # Return user info with redirect to landing page
        user_data = UserSerializer(user).data
        return Response({
            'message': 'Login successful',
            'user': user_data,
            'redirect': '/landing/'  # Redirect to new landing page
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout the current user.

    GET/POST /api/logout/
    Requires authentication.

    Query Parameters:
    - request: HTTP request object

    Returns: 
        - GET: Redirect to login page
        - POST: Response with success message (200)
    """
    logout(request)
    if request.method == 'GET':
        return redirect('login_page')
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user information.

    GET /api/current-user/
    Requires authentication.

    Query Parameters:
    - request: HTTP request object

    Returns: 
        - Response with user data (200)
    """
    user_data = UserSerializer(request.user).data
    return Response({'user': user_data}, status=status.HTTP_200_OK)


def login_page(request):
    """
    Render login page - always accessible
    
    Query Parameters:
    - request: HTTP request object
    
    Returns: 
        - Rendered login page (200)
    """
    # Always show the login page, even if user is authenticated
    return render(request, 'surveillance_app/login.html')


def register_page(request):
    """
    Render register page - always accessible
    
    Query Parameters:
    - request: HTTP request object
    
    Returns: 
        - Rendered register page (200)
    """
    # Always show the register page, even if user is authenticated
    return render(request, 'surveillance_app/register.html')


@login_required(login_url='/login/')
def landing_page(request):
    """
    Render the main landing page - requires login
    
    Query Parameters:
    - request: HTTP request object
    
    Returns: 
        - Rendered landing page (200)
    """
    return render(request, 'surveillance_app/landing.html')


# 1. Helper: Get or create LiftUsage for today
def get_todays_usage(lift):
    """
    Get today's usage record for a lift, create if doesn't exist
    
    Query Parameters:
    - lift: Lift instance
    
    Returns: 
        - LiftUsage instance for today
    """
    today = timezone.now().date()

    usage, created = LiftUsage.objects.get_or_create(
        lift=lift,
        date=today,
        defaults={
            'usage_count': 0,
            'total_people': 0,
            'max_people_count': 0,
            'overcrowding_count': 0
        }
    )

    return usage


# 3. API Endpoint: Upload and Process Lift Image
def count_people_in_lift(image_path, lift_config=None):
    """
    Simple people counting for lift images - NO AREA FILTERING
    
    Query Parameters:
    - image_path: Path to the image file
    - lift_config: Lift configuration dictionary
    
    Returns: 
        - Dictionary with people count and confidence
    """
    results = {
        'people_count': 0,
        'confidence': 0.0,
        'processing_time': 0.0,
        'detected_boxes': [],
        'is_overcrowded': False,
        'status': 'OK',
        'error': None
    }

    start_time = time.time()

    try:
        # Check if file exists
        if not os.path.exists(image_path):
            results['error'] = f"Image file not found: {image_path}"
            print(f"ERROR: {results['error']}")
            results['processing_time'] = time.time() - start_time
            return results

        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)

        if img is None:
            results['error'] = "Could not load image"
            results['processing_time'] = time.time() - start_time
            return results

        height, width = img.shape[:2]
       
        # Check if crowd model is loaded
        if CROWD_MODEL is None:
            results['error'] = "Crowd detection model not loaded"
            results['processing_time'] = time.time() - start_time
            return results

        # Run YOLO detection with lift-specific settings
        yolo_results = CROWD_MODEL(
            img,
            conf=0.25,  # Lower threshold for better detection
            iou=0.3,  # Lower NMS for crowded scenes
            classes=[0],  # ONLY DETECT PEOPLE (class 0)
            verbose=False
        )

        people_count = 0
        total_confidence = 0.0
        detected_boxes = []

        print(f"DEBUG: YOLO returned {len(yolo_results) if yolo_results else 0} results")

        if yolo_results and len(yolo_results) > 0:
            for result_idx, result in enumerate(yolo_results):
                boxes = result.boxes
                if boxes is not None:
                    print(f"DEBUG: Found {len(boxes)} total detections in result {result_idx}")

                    # Show all detected classes for debugging
                    for i, box in enumerate(boxes):
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        area = (x2 - x1) * (y2 - y1)

                        class_name = "Unknown"
                        if CROWD_MODEL.names and cls in CROWD_MODEL.names:
                            class_name = CROWD_MODEL.names[cls]

                        # Check if this is person (class 0 or based on name)
                        is_person = False
                        if cls == 0:  # Standard YOLO person class
                            is_person = True
                        elif 'person' in class_name.lower():  # Check if class name contains 'person'
                            is_person = True
                            print(f"DEBUG: Non-standard person class: {cls} ({class_name})")

                        if is_person:
                            # NO AREA FILTERING - Accept all person detections
                            if conf >= 0.25:  # Only minimum confidence check
                                people_count += 1
                                total_confidence += conf

                                detected_boxes.append({
                                    'box': [x1, y1, x2, y2],
                                    'confidence': conf,
                                    'area': area,
                                    'class_name': class_name
                                })
                                print(f"Person {people_count}: Class={class_name}({cls}), Conf={conf:.3f}, "
                                      f"Area={area:,}px, Box=[{x1},{y1},{x2},{y2}]")
                            else:
                                print(
                                    f"Low confidence person: {class_name}({cls}), Conf={conf:.3f} (threshold: 0.25)")
                        else:
                            print(f"  Non-person: {class_name}({cls}), Conf={conf:.3f}, Area={area:,}px")

        # Calculate average confidence
        if people_count > 0:
            avg_confidence = total_confidence / people_count
        else:
            avg_confidence = 0.0

        results['people_count'] = people_count
        results['detected_boxes'] = detected_boxes
        results['confidence'] = avg_confidence

        # Check overcrowding
        if lift_config:
            max_capacity = lift_config.max_capacity
            results['is_overcrowded'] = people_count > max_capacity
            results['status'] = 'OVERLOADED' if results['is_overcrowded'] else 'OK'
        else:
            # Default capacity
            max_capacity = 5
            results['is_overcrowded'] = people_count > max_capacity
            results['status'] = 'OVERLOADED' if results['is_overcrowded'] else 'OK'

        print(f"DEBUG: Max capacity: {max_capacity}, Overcrowded: {results['is_overcrowded']}")
        print(f"DEBUG: Average confidence: {avg_confidence:.3f}")

        # Create annotated image
        if yolo_results and len(yolo_results) > 0:
            try:
                annotated = yolo_results[0].plot()

                # Save annotated image
                timestamp = int(time.time())
                annotated_filename = f"lift_annotated_{timestamp}.jpg"
                annotated_dir = os.path.join(settings.MEDIA_ROOT, 'lift_annotated')
                os.makedirs(annotated_dir, exist_ok=True)
                annotated_path = os.path.join(annotated_dir, annotated_filename)

                success = cv2.imwrite(annotated_path, annotated)
                if success:
                    results['annotated_path'] = f"lift_annotated/{annotated_filename}"
                    print(f"DEBUG: Saved annotated image: {annotated_path}")
                else:
                    print(f"WARNING: Failed to save annotated image")
            except Exception as e:
                print(f"WARNING: Could not create annotated image: {e}")

        results['processing_time'] = time.time() - start_time
        print(f"DEBUG: Processing completed in {results['processing_time']:.2f}s")

    except Exception as e:
        results['error'] = str(e)
        print(f"ERROR in count_people_in_lift: {e}")
        import traceback
        traceback.print_exc()
        results['processing_time'] = time.time() - start_time

    return results


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt  
def process_lift_image(request):
    """
    Simple lift image processing - just count people
    """
    try:
        # Check file
        if 'file' not in request.FILES:
            return JsonResponse({
                'status': 'error',
                'message': 'No image file provided'
            }, status=400)

        uploaded_file = request.FILES['file']
        lift_id = request.POST.get('lift_id')

        print(
            f"DEBUG: Received file: {uploaded_file.name}, Size: {uploaded_file.size} bytes, Content-Type: {uploaded_file.content_type}")

        # Get lift configuration
        lift = None
        if lift_id:
            try:
                lift = Lift.objects.get(lift_id=lift_id, is_active=True)
            except Lift.DoesNotExist:
                lift = None

        # Create MEDIA_ROOT directory if it doesn't exist
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            os.makedirs(media_root)
            print(f"DEBUG: Created MEDIA_ROOT directory: {media_root}")

        # Save uploaded file PROPERLY
        timestamp = int(time.time())
        file_ext = os.path.splitext(uploaded_file.name)[1] or '.jpg'
        saved_filename = f"lift_{timestamp}{file_ext}"

        # Save file directly to MEDIA_ROOT (no subdirectory)
        saved_path = os.path.join(media_root, saved_filename)

        print(f"DEBUG: Saving to: {saved_path}")

        # Method 1: Save using Django's file handling
        with open(saved_path, 'wb+') as destination:
            # Read the uploaded file properly
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Verify file was saved
        if os.path.exists(saved_path):
            file_size = os.path.getsize(saved_path)
            print(f"DEBUG: File saved successfully. Size: {file_size} bytes")

            if file_size == 0:
                # Try alternative method if file is empty
                print("DEBUG: File is 0 bytes, trying alternative save method...")
                uploaded_file.seek(0)  # Reset file pointer
                with open(saved_path, 'wb') as f:
                    f.write(uploaded_file.read())

                file_size = os.path.getsize(saved_path)
                print(f"DEBUG: After alternative save. Size: {file_size} bytes")
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to save uploaded file'
            }, status=500)

        # Create LiftDetection instance
        relative_path = saved_filename
        detection = LiftDetection(
            lift=lift,
            people_count=0,  # Will update after processing
            confidence_score=0.0,
            image=relative_path  # Store relative path
        )
        detection.save()

        # Process image - WITHOUT any decorator on this function
        results = count_people_in_lift(saved_path, lift)

        # Update detection record
        detection.people_count = results['people_count']
        detection.confidence_score = results['confidence']
        detection.is_overcrowded = results['is_overcrowded']
        detection.processing_time = results['processing_time']
        detection.detection_data = {
            'boxes': results.get('detected_boxes', []),
            'confidence': results['confidence'],
            'processing_time': results['processing_time'],
            'error': results.get('error')
        }

        if 'annotated_path' in results:
            detection.processed_image = results['annotated_path']

        detection.save()

        # Update today's usage stats
        if lift:
            usage = get_todays_usage(lift)
            usage.update_stats(results['people_count'])
            detection.usage = usage
            detection.save()

        # Get image URLs
        original_url = f"{settings.MEDIA_URL}{relative_path}"
        processed_url = f"{settings.MEDIA_URL}{detection.processed_image}" if detection.processed_image else None

        # Prepare response
        response_data = {
            'status': 'success',
            'detection_id': detection.detection_id,
            'lift': {
                'id': lift.lift_id if lift else None,
                'name': lift.name if lift else 'Unknown Lift',
                'max_capacity': lift.max_capacity if lift else 8,
                'warning_threshold': lift.warning_threshold if lift else 6
            },
            'results': {
                'people_count': results['people_count'],
                'is_overcrowded': results['is_overcrowded'],
                'confidence': round(results['confidence'], 3),
                'processing_time': round(results['processing_time'], 2),
                'status': results['status'],
                'status_color': detection.get_status_color()
            },
            'usage_today': {
                'usage_count': usage.usage_count if lift else 1,
                'total_people': usage.total_people if lift else results['people_count'],
                'overcrowding_count': usage.overcrowding_count if lift else (1 if results['is_overcrowded'] else 0),
                'max_people_today': usage.max_people_count if lift else results['people_count']
            } if lift else None,
            'images': {
                'original': original_url,
                'processed': processed_url
            },
            'debug': {
                'saved_path': saved_path,
                'file_size': file_size,
                'media_root': media_root,
                'media_url': settings.MEDIA_URL,
                'detection_boxes_count': len(results.get('detected_boxes', [])),
                'model_loaded': CROWD_MODEL is not None
            },
            'timestamp': timezone.now().isoformat()
        }

        # Add error info if present
        if results.get('error'):
            response_data['debug']['processing_error'] = results['error']

        return JsonResponse(response_data, status=200)

    except Exception as e:
        print(f"Error in process_lift_image: {e}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'debug': {
                'error_type': type(e).__name__,
                'file_name': uploaded_file.name if 'uploaded_file' in locals() else 'Unknown'
            }
        }, status=500)

 
# 3b. Video Processing for Lifts
def count_people_in_video(video_path, lift_config=None, sample_interval=1.0):
    """
    Analyze video for lift overcrowding by sampling frames at intervals.
    Produces an annotated output video with bounding boxes on every frame.
    Uses the same CROWD_MODEL (YOLO) used for image detection.

    Args:
        video_path: path to the uploaded video file
        lift_config: Lift model instance (for max_capacity)
        sample_interval: seconds between sampled frames for stats (default: 1s)

    Returns:
        dict with aggregated results, per-frame data, and annotated video path
    """
    results = {
        'people_count': 0,          # peak people count (max across frames)
        'avg_people': 0.0,          # average across sampled frames
        'confidence': 0.0,
        'processing_time': 0.0,
        'is_overcrowded': False,
        'status': 'OK',
        'frame_results': [],
        'total_frames_analyzed': 0,
        'video_duration': 0.0,
        'error': None,
        'annotated_path': None,
        'annotated_video_path': None
    }

    start_time = time.time()

    try:
        if not os.path.exists(video_path):
            results['error'] = f"Video file not found: {video_path}"
            results['processing_time'] = time.time() - start_time
            return results

        if CROWD_MODEL is None:
            results['error'] = "Crowd detection model not loaded"
            results['processing_time'] = time.time() - start_time
            return results

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            results['error'] = "Could not open video file"
            results['processing_time'] = time.time() - start_time
            return results

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_video_frames / fps if fps > 0 else 0
        frame_skip = max(1, int(fps * sample_interval))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"DEBUG VIDEO: FPS={fps}, Total frames={total_video_frames}, "
              f"Duration={video_duration:.1f}s, Resolution={width}x{height}, "
              f"Sampling stats every {frame_skip} frames")

        # Setup annotated video writer
        timestamp_id = int(time.time())
        annotated_video_filename = f"lift_video_annotated_{timestamp_id}.mp4"
        annotated_video_dir = os.path.join(settings.MEDIA_ROOT, 'lift_annotated')
        os.makedirs(annotated_video_dir, exist_ok=True)
        annotated_video_full_path = os.path.join(annotated_video_dir, annotated_video_filename)

        # Try avc1 (H.264) first for browser compatibility, fallback to mp4v if needed
        try:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            writer = cv2.VideoWriter(annotated_video_full_path, fourcc, fps, (width, height))
            # Test if writer opened, if not retry with mp4v
            if not writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(annotated_video_full_path, fourcc, fps, (width, height))
        except:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(annotated_video_full_path, fourcc, fps, (width, height))

        frame_results_list = []
        max_people = 0
        peak_frame = None
        peak_yolo_result = None
        total_people_sum = 0
        frame_idx = 0
        frames_analyzed = 0

        # Cache for drawing boxes on intermediate frames
        last_boxes = []  # list of (x1, y1, x2, y2, conf, class_name) from last YOLO run

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_skip == 0:
                # Filter to only detect people (classes=[0])
                yolo_results = CROWD_MODEL(frame, conf=0.25, iou=0.3, classes=[0], verbose=False)

                people_count = 0
                total_conf = 0.0
                last_boxes = []  # reset cached boxes

                if yolo_results and len(yolo_results) > 0:
                    for result_obj in yolo_results:
                        boxes = result_obj.boxes
                        if boxes is not None:
                            for box in boxes:
                                cls = int(box.cls[0])
                                conf = float(box.conf[0])
                                class_name = CROWD_MODEL.names.get(cls, "Unknown") if CROWD_MODEL.names else "Unknown"

                                is_person = (cls == 0) or ('person' in class_name.lower())
                                if is_person and conf >= 0.25:
                                    people_count += 1
                                    total_conf += conf
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    last_boxes.append((x1, y1, x2, y2, conf, class_name))

                # Write YOLO-annotated frame
                if yolo_results and len(yolo_results) > 0 and people_count > 0:
                    annotated_frame = yolo_results[0].plot()
                    writer.write(annotated_frame)
                else:
                    writer.write(frame)

                avg_conf = total_conf / people_count if people_count > 0 else 0.0
                timestamp_sec = round(frame_idx / fps, 2)

                frame_result = {
                    'frame_number': frame_idx,
                    'timestamp_sec': timestamp_sec,
                    'people_count': people_count,
                    'confidence': round(avg_conf, 3),
                }
                frame_results_list.append(frame_result)
                total_people_sum += people_count
                frames_analyzed += 1

                # Track peak frame
                if people_count > max_people:
                    max_people = people_count
                    peak_frame = frame.copy()
                    peak_yolo_result = yolo_results

                if people_count > 0:
                    print(f"  Frame {frame_idx} ({timestamp_sec}s): {people_count} people detected")

            else:
                # INTERMEDIATE FRAME: Draw cached boxes 
                if last_boxes:
                    annotated_frame = frame.copy()
                    for (x1, y1, x2, y2, conf, cls_name) in last_boxes:
                        # Draw green box
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        label = f"{cls_name} {conf:.2f}"
                        # Draw label background
                        cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + 120, y1), (0, 255, 0), -1)
                        cv2.putText(annotated_frame, label, (x1 + 5, y1 - 7),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                    writer.write(annotated_frame)
                else:
                    writer.write(frame)

            frame_idx += 1

        cap.release()
        writer.release()

        # Calculate aggregated results
        avg_people = total_people_sum / frames_analyzed if frames_analyzed > 0 else 0.0
        overall_confidence = sum(f['confidence'] for f in frame_results_list) / len(frame_results_list) if frame_results_list else 0.0

        results['people_count'] = max_people
        results['avg_people'] = round(avg_people, 1)
        results['confidence'] = round(overall_confidence, 3)
        results['frame_results'] = frame_results_list
        results['total_frames_analyzed'] = frames_analyzed
        results['video_duration'] = round(video_duration, 1)

        # Check overcrowding (based on peak)
        max_capacity = lift_config.max_capacity if lift_config else 5
        results['is_overcrowded'] = max_people > max_capacity
        results['status'] = 'OVERLOADED' if results['is_overcrowded'] else 'OK'

        # Save annotated video path
        if os.path.exists(annotated_video_full_path) and os.path.getsize(annotated_video_full_path) > 0:
            results['annotated_video_path'] = f"lift_annotated/{annotated_video_filename}"
            print(f"DEBUG VIDEO: Saved annotated video: {annotated_video_full_path} "
                  f"({os.path.getsize(annotated_video_full_path)} bytes)")
        else:
            print(f"WARNING: Annotated video file is empty or missing")

        # Save annotated peak frame as image
        if peak_yolo_result and len(peak_yolo_result) > 0:
            try:
                annotated = peak_yolo_result[0].plot()
                annotated_filename = f"lift_video_peak_{timestamp_id}.jpg"
                annotated_path = os.path.join(annotated_video_dir, annotated_filename)

                if cv2.imwrite(annotated_path, annotated):
                    results['annotated_path'] = f"lift_annotated/{annotated_filename}"
                    print(f"DEBUG VIDEO: Saved peak frame: {annotated_path}")
            except Exception as e:
                print(f"WARNING: Could not save annotated peak frame: {e}")

        print(f"DEBUG VIDEO: Analysis complete. Peak={max_people}, Avg={avg_people:.1f}, "
              f"Frames processed={frame_idx}, Stats sampled={frames_analyzed}, Duration={video_duration:.1f}s")

    except Exception as e:
        results['error'] = str(e)
        print(f"ERROR in count_people_in_video: {e}")
        import traceback
        traceback.print_exc()

    results['processing_time'] = time.time() - start_time
    return results


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def process_lift_video(request):
    """
    Upload and process a lift video for overcrowding detection.
    Samples frames at intervals and runs YOLO person detection on each.

    POST /api/lift/process-video/
    Body (multipart/form-data):
        - file: video file (mp4, avi, mov, mkv)
        - lift_id: ID of the lift (optional)
        - sample_interval: seconds between sampled frames (optional, default 1.0)

    Query Parameters:
    - request: HTTP request object containing video file and processing parameters

    Returns: JSON response containing detection results, frame analysis, and usage statistics
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'status': 'error',
                'message': 'No video file provided'
            }, status=400)

        uploaded_file = request.FILES['file']
        lift_id = request.POST.get('lift_id')
        sample_interval = float(request.POST.get('sample_interval', 1.0))

        # Validate file type
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({
                'status': 'error',
                'message': f'Unsupported video format: {file_ext}. Allowed: {", ".join(allowed_extensions)}'
            }, status=400)

        print(f"DEBUG VIDEO: Received file: {uploaded_file.name}, "
              f"Size: {uploaded_file.size} bytes, Content-Type: {uploaded_file.content_type}")

        # Get lift configuration
        lift = None
        if lift_id:
            try:
                lift = Lift.objects.get(lift_id=lift_id, is_active=True)
            except Lift.DoesNotExist:
                lift = None

        # Save uploaded video
        media_root = settings.MEDIA_ROOT
        os.makedirs(media_root, exist_ok=True)

        timestamp = int(time.time())
        saved_filename = f"lift_video_{timestamp}{file_ext}"
        # Save directly to MEDIA_ROOT (no subdirectory)
        saved_path = os.path.join(media_root, saved_filename)

        with open(saved_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        file_size = os.path.getsize(saved_path)
        print(f"DEBUG VIDEO: Saved to {saved_path} ({file_size} bytes)")

        if file_size == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Uploaded video file is empty'
            }, status=400)

        # Create detection record
        relative_path = saved_filename
        detection = LiftDetection(
            lift=lift,
            source_type='VIDEO',
            people_count=0,
            confidence_score=0.0,
            video=relative_path
        )
        detection.save()

        # Process video
        video_results = count_people_in_video(saved_path, lift, sample_interval)

        # Update detection record
        detection.people_count = video_results['people_count']
        detection.confidence_score = video_results['confidence']
        detection.is_overcrowded = video_results['is_overcrowded']
        detection.processing_time = video_results['processing_time']
        detection.max_people_in_video = video_results['people_count']
        detection.avg_people_in_video = video_results['avg_people']
        detection.frame_results = video_results['frame_results']
        detection.detection_data = {
            'total_frames_analyzed': video_results['total_frames_analyzed'],
            'video_duration': video_results['video_duration'],
            'sample_interval': sample_interval,
            'error': video_results.get('error')
        }

        if video_results.get('annotated_path'):
            detection.processed_image = video_results['annotated_path']

        if video_results.get('annotated_video_path'):
            detection.processed_video = video_results['annotated_video_path']

        detection.save()

        # Update today's usage stats (use peak count)
        if lift:
            usage = get_todays_usage(lift)
            usage.update_stats(video_results['people_count'])
            detection.usage = usage
            detection.save()

        # Build response
        processed_url = f"{settings.MEDIA_URL}{detection.processed_image}" if detection.processed_image else None
        annotated_video_url = f"{settings.MEDIA_URL}{detection.processed_video}" if detection.processed_video else None

        response_data = {
            'status': 'success',
            'detection_id': detection.detection_id,
            'source_type': 'VIDEO',
            'lift': {
                'id': lift.lift_id if lift else None,
                'name': lift.name if lift else 'Unknown Lift',
                'max_capacity': lift.max_capacity if lift else 8,
                'warning_threshold': lift.warning_threshold if lift else 6
            },
            'results': {
                'peak_people_count': video_results['people_count'],
                'avg_people_count': video_results['avg_people'],
                'is_overcrowded': video_results['is_overcrowded'],
                'confidence': round(video_results['confidence'], 3),
                'processing_time': round(video_results['processing_time'], 2),
                'status': video_results['status'],
                'status_color': detection.get_status_color(),
                'video_duration': video_results['video_duration'],
                'frames_analyzed': video_results['total_frames_analyzed'],
            },
            'frame_results': video_results['frame_results'],
            'images': {
                'peak_frame': processed_url,
                'annotated_video': annotated_video_url
            },
            'usage_today': {
                'usage_count': usage.usage_count if lift else 1,
                'total_people': usage.total_people if lift else video_results['people_count'],
                'overcrowding_count': usage.overcrowding_count if lift else (1 if video_results['is_overcrowded'] else 0),
                'max_people_today': usage.max_people_count if lift else video_results['people_count']
            } if lift else None,
            'timestamp': timezone.now().isoformat()
        }

        if video_results.get('error'):
            response_data['debug'] = {'processing_error': video_results['error']}

        return JsonResponse(response_data, status=200)

    except Exception as e:
        print(f"Error in process_lift_video: {e}")
        import traceback
        traceback.print_exc()

        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'debug': {
                'error_type': type(e).__name__,
                'file_name': uploaded_file.name if 'uploaded_file' in locals() else 'Unknown'
            }
        }, status=500)

# 4. API Endpoint: Get Lift Usage Statistics
@api_view(['GET'])
@permission_classes([AllowAny])
def lift_usage_stats(request):
    """
    Get lift usage statistics

    Query Parameters:
    - lift_id: Specific lift ID (optional)
    - days: Number of past days (default: 7)

    Returns:
        JSON response containing usage statistics for the specified period
    """
    try:
        lift_id = request.GET.get('lift_id')
        days = int(request.GET.get('days', 7))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Build query
        if lift_id:
            lifts = Lift.objects.filter(lift_id=lift_id, is_active=True)
        else:
            lifts = Lift.objects.filter(is_active=True)

        stats = []

        for lift in lifts:
            # Get usage for the period
            usages = LiftUsage.objects.filter(
                lift=lift,
                date__range=[start_date, end_date]
            ).order_by('date')

            # Get today's usage
            today_usage = usages.filter(date=end_date).first()

            # Get detections for today
            today_detections = LiftDetection.objects.filter(
                lift=lift,
                timestamp__date=end_date
            ).order_by('-timestamp')[:10]  # Last 10 detections today

            # Calculate daily averages
            if usages.exists():
                total_uses = sum(u.usage_count for u in usages)
                total_people = sum(u.total_people for u in usages)
                total_overcrowding = sum(u.overcrowding_count for u in usages)

                avg_people_per_use = total_people / total_uses if total_uses > 0 else 0
                avg_uses_per_day = total_uses / days
                overcrowding_rate = (total_overcrowding / total_uses * 100) if total_uses > 0 else 0
            else:
                total_uses = 0
                total_people = 0
                total_overcrowding = 0
                avg_people_per_use = 0
                avg_uses_per_day = 0
                overcrowding_rate = 0

            # Prepare response
            lift_stats = {
                'lift_id': lift.lift_id,
                'lift_name': lift.name,
                'location': lift.location,
                'max_capacity': lift.max_capacity,
                'warning_threshold': lift.warning_threshold,

                # Today's stats
                'today': {
                    'usage_count': today_usage.usage_count if today_usage else 0,
                    'total_people': today_usage.total_people if today_usage else 0,
                    'overcrowding_count': today_usage.overcrowding_count if today_usage else 0,
                    'max_people': today_usage.max_people_count if today_usage else 0,
                    'avg_people': today_usage.get_avg_people() if today_usage else 0
                } if today_usage else None,

                # Period stats
                'period_stats': {
                    'days': days,
                    'total_uses': total_uses,
                    'total_people': total_people,
                    'total_overcrowding': total_overcrowding,
                    'avg_people_per_use': round(avg_people_per_use, 1),
                    'avg_uses_per_day': round(avg_uses_per_day, 1),
                    'overcrowding_rate': round(overcrowding_rate, 1)
                },

                # Recent detections
                'recent_detections': [
                    {
                        'detection_id': d.detection_id,
                        'people_count': d.people_count,
                        'is_overcrowded': d.is_overcrowded,
                        'confidence': d.confidence_score,
                        'timestamp': d.timestamp.isoformat(),
                        'status_color': d.get_status_color()
                    }
                    for d in today_detections
                ]
            }

            stats.append(lift_stats)

        return JsonResponse({
            'status': 'success',
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'stats': stats
        }, status=200)

    except Exception as e:
        print(f"Error in lift_usage_stats: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)



# 5. API Endpoint: Get Lift List
@api_view(['GET'])
@permission_classes([AllowAny])
def lift_list(request):
    """
    Get list of all active lifts
    
    Query Parameters:
    - request: HTTP request object
    
    Returns:
        JSON response containing list of active lifts
    """
    try:
        lifts = Lift.objects.filter(is_active=True)

        data = [
            {
                'lift_id': lift.lift_id,
                'name': lift.name,
                'location': lift.location,
                'max_capacity': lift.max_capacity,
                'warning_threshold': lift.warning_threshold,
                'created_at': lift.created_at.isoformat()
            }
            for lift in lifts
        ]

        return JsonResponse({
            'status': 'success',
            'count': len(data),
            'lifts': data
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)