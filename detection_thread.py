import cv2
import os
import platform
import numpy as np
from datetime import datetime
from collections import deque
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from config.settings import (
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT,
    DETECTION_SCALE, WIN_STRIDE, PADDING,
    MAX_MISSING_FRAMES, TRAJECTORY_MAX_LENGTH,
    MATCH_DISTANCE_THRESHOLD, RECORD_TIMEOUT,
    RECORDING_FPS, VIDEO_CODEC, IDLE_THRESHOLD,
    RESTRICTED_ZONE, CAPTURES_DIR, RECORDINGS_DIR,
    ADVANCED_FEATURES, FACE_RECOGNITION_TOLERANCE,
    EMOTION_UPDATE_INTERVAL, POSE_UPDATE_INTERVAL
)

if ADVANCED_FEATURES:
    import face_recognition


class DetectionThread(QThread):
    change_pixmap = pyqtSignal(QImage)
    alert_signal = pyqtSignal(int, str, str, dict)
    stats_signal = pyqtSignal(int, int, float)
    graph_signal = pyqtSignal(int)
    ml_learn_signal = pyqtSignal(dict)

    def __init__(self, security_manager, ml_brain, emotion_pose_detector):
        super().__init__()
        self.security = security_manager
        self.ml_brain = ml_brain
        self.emotion_pose_detector = emotion_pose_detector
        
        self.running = False
        self.cap = None
        self.hog = None
        
        self.tracked_persons = {}
        self.next_id = 1
        self.alerted_ids = set()
        
        self.recording = None
        self.recording_active = False
        self.frames_since_last_detection = 0
        
        self.alert_count = 0
        self.frame_count = 0
        
        self.night_mode = False
        self.face_recognition_enabled = True
        self.show_trajectories = True
        
        self.known_faces = {}
        self.load_known_faces()
    
    def load_known_faces(self):
        
        if not ADVANCED_FEATURES:
            return
        
        from config.settings import KNOWN_FACES_DIR
        
        if not os.path.exists(KNOWN_FACES_DIR):
            return
        
        for filename in os.listdir(KNOWN_FACES_DIR):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(KNOWN_FACES_DIR, filename)
                try:
                    image = face_recognition.load_image_file(filepath)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        name = os.path.splitext(filename)[0]
                        self.known_faces[name] = encodings[0]
                except Exception as e:
                    print(f"Error while charging {filename}: {e}")
    
    def run(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self.running = True
        fps_counter = []

        while self.running:
            start_time = cv2.getTickCount()
            ret, frame = self.cap.read()
            if not ret:
                break

            self.frame_count += 1
            
            if self.night_mode:
                frame = self.apply_night_vision(frame)
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects, _ = self.hog.detectMultiScale(
                gray, 
                winStride=WIN_STRIDE, 
                padding=PADDING, 
                scale=DETECTION_SCALE
            )
            
            detected_ids = []

            for person_id, person_data in list(self.tracked_persons.items()):
                person_data['frames_missing'] += 1
                if person_data['frames_missing'] >= MAX_MISSING_FRAMES:
                    del self.tracked_persons[person_id]

            matched = set()
            for (x, y, w, h) in rects:
                best_match = None
                min_dist = float('inf')
                
                for person_id, person_data in self.tracked_persons.items():
                    if person_data['frames_missing'] < MAX_MISSING_FRAMES:
                        cx, cy = x + w//2, y + h//2
                        pcx, pcy = person_data['center']
                        dist = np.sqrt((pcx - cx)**2 + (pcy - cy)**2)
                        if dist < min_dist and dist < MATCH_DISTANCE_THRESHOLD:
                            min_dist = dist
                            best_match = person_id
                
                if best_match:
                    self.tracked_persons[best_match]['bbox'] = (x, y, w, h)
                    self.tracked_persons[best_match]['center'] = (x + w//2, y + h//2)
                    self.tracked_persons[best_match]['frames_missing'] = 0
                    self.tracked_persons[best_match]['trajectory'].append((x + w//2, y + h//2))
                    detected_ids.append(best_match)
                    matched.add(best_match)
                else:
                    person_id = self.next_id
                    self.tracked_persons[person_id] = {
                        'bbox': (x, y, w, h),
                        'center': (x + w//2, y + h//2),
                        'trajectory': deque(maxlen=TRAJECTORY_MAX_LENGTH),
                        'frames_missing': 0,
                        'identity': 'UNKNOWN',
                        'emotion': 'neutral',
                        'pose': 'standing'
                    }
                    self.tracked_persons[person_id]['trajectory'].append((x + w//2, y + h//2))
                    detected_ids.append(person_id)
                    self.next_id += 1

            if self.frame_count % EMOTION_UPDATE_INTERVAL == 0:
                for person_id in detected_ids:
                    person = self.tracked_persons[person_id]
                    x, y, w, h = person['bbox']
                    
                    if self.face_recognition_enabled and ADVANCED_FEATURES:
                        face_crop = frame[max(0,y):min(frame.shape[0],y+h), 
                                         max(0,x):min(frame.shape[1],x+w)]
                        if face_crop.size > 0:
                            rgb_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                            encodings = face_recognition.face_encodings(rgb_crop)
                            if encodings and self.known_faces:
                                matches = face_recognition.compare_faces(
                                    list(self.known_faces.values()), 
                                    encodings[0],
                                    tolerance=FACE_RECOGNITION_TOLERANCE
                                )
                                if True in matches:
                                    idx = matches.index(True)
                                    person['identity'] = list(self.known_faces.keys())[idx]
                            
                            emotion, conf = self.emotion_pose_detector.detect_emotion(face_crop)
                            person['emotion'] = emotion
            
            if self.frame_count % POSE_UPDATE_INTERVAL == 0:
                pose_result = self.emotion_pose_detector.detect_pose(frame)
                if pose_result and detected_ids:
                    for person_id in detected_ids:
                        self.tracked_persons[person_id]['pose'] = pose_result['type']

            if self.show_trajectories:
                for person in self.tracked_persons.values():
                    if person['frames_missing'] < MAX_MISSING_FRAMES and len(person['trajectory']) > 1:
                        points = list(person['trajectory'])
                        for i in range(1, len(points)):
                            alpha = i / len(points)
                            thickness = max(1, int(alpha * 3))
                            color = (int(255 * alpha), int(255 * alpha), 0)
                            cv2.line(frame, points[i-1], points[i], color, thickness)

            active_count = 0
            for person_id in detected_ids:
                person = self.tracked_persons[person_id]
                if person['frames_missing'] < MAX_MISSING_FRAMES:
                    active_count += 1
                    x, y, w, h = person['bbox']
                    cx, cy = person['center']

                    # Rectangle pulsant
                    thickness = 3 if self.frame_count % 20 < 10 else 2
                    color = (0, 255, 0) if person['identity'] != 'UNKNOWN' else (255, 255, 0)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
                    
                    corner_size = 20
                    cv2.line(frame, (x, y), (x+corner_size, y), (0, 255, 255), 3)
                    cv2.line(frame, (x, y), (x, y+corner_size), (0, 255, 255), 3)
                    cv2.line(frame, (x+w, y), (x+w-corner_size, y), (0, 255, 255), 3)
                    cv2.line(frame, (x+w, y), (x+w, y+corner_size), (0, 255, 255), 3)
                    cv2.line(frame, (x, y+h), (x+corner_size, y+h), (0, 255, 255), 3)
                    cv2.line(frame, (x, y+h), (x, y+h-corner_size), (0, 255, 255), 3)
                    cv2.line(frame, (x+w, y+h), (x+w-corner_size, y+h), (0, 255, 255), 3)
                    cv2.line(frame, (x+w, y+h), (x+w, y+h-corner_size), (0, 255, 255), 3)
                    
                    label = f"{person['identity']} #{person_id}"
                    cv2.rectangle(frame, (x, y-30), (x+250, y), color, -1)
                    cv2.putText(frame, label, (x+5, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                    
                    emotion_text = f"😊 {person['emotion']}"
                    cv2.putText(frame, emotion_text, (x, y+h+20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                    
                    pose_text = f"🤸 {person['pose']}"
                    cv2.putText(frame, pose_text, (x, y+h+40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                    
                    cv2.drawMarker(frame, (cx, cy), (0, 255, 255), 
                                  cv2.MARKER_CROSS, 30, 2)
                    
                    features = {
                        'person_count': active_count,
                        'zone': self.get_zone(cx, cy),
                        'emotion': person['emotion'],
                        'pose': person['pose'],
                        'time_of_day': datetime.now().hour,
                        'identity': person['identity']
                    }
                    self.ml_learn_signal.emit(features)

            x1, y1, x2, y2 = RESTRICTED_ZONE
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, "RESTRICTED ZONE", (x1+5, y1+25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            new_detections = [id for id in detected_ids if id not in self.alerted_ids]
            if new_detections:
                self.handle_new_detections(new_detections, frame)

            if active_count > 0:
                self.frames_since_last_detection = 0
            else:
                self.frames_since_last_detection += 1
                if self.recording_active and self.frames_since_last_detection > RECORD_TIMEOUT:
                    self.stop_recording()

            self.draw_indicators(frame)

            end_time = cv2.getTickCount()
            fps = cv2.getTickFrequency() / (end_time - start_time)
            fps_counter.append(fps)
            if len(fps_counter) > 30:
                fps_counter.pop(0)
            fps_display = sum(fps_counter)/len(fps_counter) if fps_counter else 0

            self.stats_signal.emit(active_count, self.alert_count, fps_display)
            self.graph_signal.emit(active_count)
            
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, ch*w, QImage.Format_RGB888)
            self.change_pixmap.emit(qt_image)

            if self.recording_active:
                self.recording.write(frame)

        self.cap.release()
        if self.recording_active:
            self.stop_recording()
    
    def get_zone(self, x, y):
        
        if x < CAMERA_WIDTH // 3:
            return "zone_left"
        elif x < 2 * CAMERA_WIDTH // 3:
            return "zone_center"
        else:
            return "zone_right"
    
    def apply_night_vision(self, frame):
       
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        green_tint = enhanced.copy()
        green_tint[:,:,0] = green_tint[:,:,0] * 0.3
        green_tint[:,:,1] = np.clip(green_tint[:,:,1] * 1.3, 0, 255)
        green_tint[:,:,2] = green_tint[:,:,2] * 0.3
        
        return green_tint.astype(np.uint8)
    
    def handle_new_detections(self, new_detections, frame):
        
        num_new = len(new_detections)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(CAPTURES_DIR, f"detection_{timestamp}.jpg")
        cv2.imwrite(photo_path, frame)
        
        # Chiffrer la photo
        encrypted_path = self.security.encrypt_file(photo_path)
        
        self.alert_count += 1
        
        # Données extras pour alerte
        extras = {
            'identities': [self.tracked_persons[id]['identity'] for id in new_detections],
            'emotions': [self.tracked_persons[id]['emotion'] for id in new_detections],
            'poses': [self.tracked_persons[id]['pose'] for id in new_detections],
            'encrypted_photo': encrypted_path
        }
        
        alert_type = "NEW_TARGET" if num_new == 1 else "MULTIPLE_TARGETS"
        self.alert_signal.emit(
            num_new, 
            datetime.now().strftime("%H:%M:%S"), 
            alert_type, 
            extras
        )
        
        self.start_recording(frame, "DETECTION")
        self.beep()
        self.alerted_ids.update(new_detections)
    
    def draw_indicators(self, frame):
        
        if self.recording_active:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (50, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if self.night_mode:
            cv2.putText(frame, "NIGHT MODE", (frame.shape[1]-150, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.putText(frame, "LUCY v1.0", (10, frame.shape[0]-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def start_recording(self, frame, alert_type="DETECTION"):
       
        if not self.recording_active:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(RECORDINGS_DIR, 
                                   f"record_{timestamp}_{alert_type}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
            h, w, _ = frame.shape
            self.recording = cv2.VideoWriter(filename, fourcc, RECORDING_FPS, (w, h))
            self.recording_active = True
            
            self.security.log_action(None, "RECORDING_START", 
                                    f"Started: {filename}", True)

    def stop_recording(self):
       
        if self.recording_active:
            self.recording.release()
            self.recording_active = False
            self.security.log_action(None, "RECORDING_STOP", 
                                    "Recording stopped", True)

    def beep(self):
       
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 200)
            except:
                pass
        else:
            os.system('printf "\\a"')

    def stop(self):
        
        self.running = False
        self.wait()