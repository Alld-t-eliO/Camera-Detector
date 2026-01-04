import cv2
import numpy as np

from config.settings import (
    ADVANCED_FEATURES,
    POSE_DETECTION_CONFIDENCE
)

if ADVANCED_FEATURES:
    import mediapipe as mp


class EmotionPoseDetector:
    
    def __init__(self):
        if not ADVANCED_FEATURES:
            self.enabled = False
            return
        
        self.enabled = True
        
        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_DETECTION_CONFIDENCE
        )
        
        self.emotions = ['happy', 'sad', 'angry', 'neutral', 'surprised', 'fearful']
    
    def detect_emotion(self, face_image):
        if not self.enabled:
            return "neutral", 0.5
        
      
        emotion = np.random.choice(['neutral', 'happy', 'focused'])
        confidence = 0.7
        
        return emotion, confidence
    
    def detect_pose(self, frame):
        if not self.enabled:
            return None
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
        
        landmarks = results.pose_landmarks.landmark
        
        pose_type = self.analyze_pose(landmarks)
        
        return {
            'type': pose_type,
            'landmarks': landmarks,
            'confidence': 0.8
        }
    
    def analyze_pose(self, landmarks):
       
        left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP.value]
        
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        
        if shoulder_y > hip_y + 0.3:
            return "sitting"
        elif shoulder_y > hip_y + 0.15:
            return "crouching"
        elif left_shoulder.y < 0.3: 
            return "hands_up"
        else:
            return "standing"