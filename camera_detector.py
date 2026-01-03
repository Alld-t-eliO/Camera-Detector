import cv2
import sys
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor
import platform
import os

class DetectionThread(QThread):
    """Thread pour la détection vidéo"""
    change_pixmap = pyqtSignal(QImage)
    alert_signal = pyqtSignal(int, str)
    stats_signal = pyqtSignal(int, int, float)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self.hog_detector = None
        self.alert_count = 0
        
    def run(self):
        """Boucle principale de détection"""
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Initialiser HOG
        self.hog_detector = cv2.HOGDescriptor()
        self.hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        self.running = True
        frame_count = 0
        last_alert_frame = 0
        alert_cooldown = 30
        fps_counter = []
        
        while self.running:
            start_time = cv2.getTickCount()
            ret, frame = self.cap.read()
            
            if not ret:
                break
                
            frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Détection
            persons, _ = self.hog_detector.detectMultiScale(
                gray, winStride=(8, 8), padding=(4, 4), scale=1.05
            )
            
            # Alerte si personne détectée
            if len(persons) > 0:
                if frame_count - last_alert_frame > alert_cooldown:
                    self.alert_count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.alert_signal.emit(len(persons), timestamp)
                    last_alert_frame = frame_count
                    self.beep()
                
                # Encadrer les personnes
                for i, (x, y, w, h) in enumerate(persons):
                    # Rectangle cyan
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 3)
                    
                    # Label
                    label = f"TARGET {i + 1}"
                    cv2.rectangle(frame, (x, y-30), (x+150, y), (255, 255, 0), -1)
                    cv2.putText(frame, label, (x+5, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                    
                    # Croix de visée
                    center_x, center_y = x + w//2, y + h//2
                    cv2.drawMarker(frame, (center_x, center_y), 
                                 (0, 255, 255), cv2.MARKER_CROSS, 20, 2)
            
            # Calcul FPS
            end_time = cv2.getTickCount()
            fps = cv2.getTickFrequency() / (end_time - start_time)
            fps_counter.append(fps)
            if len(fps_counter) > 30:
                fps_counter.pop(0)
            fps_display = sum(fps_counter) / len(fps_counter) if fps_counter else 0
            
            # Envoyer stats
            self.stats_signal.emit(len(persons), self.alert_count, fps_display)
            
            # Convertir pour Qt
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.change_pixmap.emit(qt_image)
            
        self.cap.release()
    
    def beep(self):
        """Bip sonore"""
        system = platform.system()
        if system == "Windows":
            try:
                import winsound
                winsound.Beep(1000, 200)
            except:
                pass
        else:
            os.system('printf "\\a"')
    
    def stop(self):
        """Arrêter la détection"""
        self.running = False
        self.wait()


class CyberpunkGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.detection_thread = None
        self.is_monitoring = False
        self.init_ui()
        
    def init_ui(self):
        """Initialiser l'interface"""
        self.setWindowTitle("◢ SURVEILLANCE SYSTEM v2.077 ◣")
        self.setGeometry(100, 100, 1400, 800)
        
        # Style cyberpunk
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0a;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                background-color: #001a1a;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Courier New', monospace;
            }
            QPushButton:hover {
                background-color: #003333;
                box-shadow: 0 0 10px #00ffff;
            }
            QPushButton:pressed {
                background-color: #00ffff;
                color: #000000;
            }
            QPushButton:disabled {
                background-color: #0a0a0a;
                color: #004444;
                border: 2px solid #004444;
            }
            QTextEdit {
                background-color: #000000;
                color: #00ff00;
                border: 2px solid #00ffff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 5px;
            }
            QFrame {
                border: 2px solid #00ffff;
                background-color: #000000;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # === COLONNE GAUCHE: Vidéo et contrôles ===
        left_layout = QVBoxLayout()
        
        # Header
        header = QLabel("◢◤◢◤◢ NEURAL DETECTION SYSTEM ◣◥◣◥◣")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 15px;
            background-color: #001a1a;
            border: 3px solid #00ffff;
            color: #00ffff;
        """)
        left_layout.addWidget(header)
        
        # Flux vidéo
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setMaximumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            border: 3px solid #00ffff;
            background-color: #000000;
        """)
        self.video_label.setText("◢◤ CAMERA OFFLINE ◥◣\n\n[PRESS START TO ACTIVATE]")
        left_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        
        # Statistiques en temps réel
        stats_frame = QFrame()
        stats_frame.setStyleSheet("border: 2px solid #00ffff; padding: 10px;")
        stats_layout = QHBoxLayout(stats_frame)
        
        self.targets_label = QLabel("TARGETS: 0")
        self.targets_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.alerts_label = QLabel("ALERTS: 0")
        self.alerts_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        stats_layout.addWidget(self.targets_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.alerts_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.fps_label)
        
        left_layout.addWidget(stats_frame)
        
        # Boutons de contrôle
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ START SURVEILLANCE")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setMinimumHeight(50)
        
        self.stop_btn = QPushButton("■ STOP SURVEILLANCE")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(50)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        left_layout.addLayout(control_layout)
        
        main_layout.addLayout(left_layout, 2)
        
        # === COLONNE DROITE: Alertes ===
        right_layout = QVBoxLayout()
        
        # Header alertes
        alert_header = QLabel("◢ ALERT LOG ◣")
        alert_header.setAlignment(Qt.AlignCenter)
        alert_header.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            background-color: #001a1a;
            border: 3px solid #00ffff;
            color: #00ffff;
        """)
        right_layout.addWidget(alert_header)
        
        # Statut système
        self.status_label = QLabel("◢ SYSTEM STATUS: STANDBY ◣")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            background-color: #003333;
            border: 2px solid #00ffff;
            color: #00ff00;
        """)
        right_layout.addWidget(self.status_label)
        
        # Horloge
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("""
            font-size: 18px;
            padding: 5px;
            border: 2px solid #00ffff;
            color: #00ffff;
        """)
        right_layout.addWidget(self.clock_label)
        
        # Timer pour l'horloge
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()
        
        # Zone d'alertes
        self.alert_text = QTextEdit()
        self.alert_text.setReadOnly(True)
        self.alert_text.append(">>> SYSTEM INITIALIZED")
        self.alert_text.append(">>> AWAITING ACTIVATION...")
        self.alert_text.append("=" * 50)
        right_layout.addWidget(self.alert_text)
        
        # Bouton clear
        clear_btn = QPushButton("⊗ CLEAR LOG")
        clear_btn.clicked.connect(self.clear_alerts)
        clear_btn.setMinimumHeight(40)
        right_layout.addWidget(clear_btn)
        
        main_layout.addLayout(right_layout, 1)
        
    def update_clock(self):
        """Mettre à jour l'horloge"""
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.clock_label.setText(f"◢ {current_date} | {current_time} ◣")
        
    def start_monitoring(self):
        """Démarrer la surveillance"""
        self.is_monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.status_label.setText("◢ SYSTEM STATUS: ACTIVE - SCANNING... ◣")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            background-color: #1a0000;
            border: 2px solid #ff0000;
            color: #ff0000;
        """)
        
        self.alert_text.append("\n" + "=" * 50)
        self.alert_text.append(f">>> [{datetime.now().strftime('%H:%M:%S')}] SURVEILLANCE ACTIVATED")
        self.alert_text.append(">>> NEURAL NETWORK ONLINE")
        self.alert_text.append(">>> SCANNING FOR TARGETS...")
        self.alert_text.append("=" * 50 + "\n")
        
        # Démarrer le thread de détection
        self.detection_thread = DetectionThread()
        self.detection_thread.change_pixmap.connect(self.update_image)
        self.detection_thread.alert_signal.connect(self.add_alert)
        self.detection_thread.stats_signal.connect(self.update_stats)
        self.detection_thread.start()
        
    def stop_monitoring(self):
        """Arrêter la surveillance"""
        self.is_monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.status_label.setText("◢ SYSTEM STATUS: STANDBY ◣")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            background-color: #003333;
            border: 2px solid #00ffff;
            color: #00ff00;
        """)
        
        if self.detection_thread:
            self.detection_thread.stop()
            
        self.video_label.setText("◢◤ CAMERA OFFLINE ◥◣\n\n[PRESS START TO ACTIVATE]")
        self.targets_label.setText("TARGETS: 0")
        self.fps_label.setText("FPS: 0.0")
        
        self.alert_text.append("\n" + "=" * 50)
        self.alert_text.append(f">>> [{datetime.now().strftime('%H:%M:%S')}] SURVEILLANCE DEACTIVATED")
        self.alert_text.append(">>> SYSTEM ENTERING STANDBY MODE")
        self.alert_text.append("=" * 50 + "\n")
        
    def update_image(self, image):
        """Mettre à jour l'image vidéo"""
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        
    def add_alert(self, num_persons, timestamp):
        """Ajouter une alerte"""
        self.alert_text.append(f"[{timestamp}] ⚠ ALERT ⚠")
        self.alert_text.append(f">>> DETECTED: {num_persons} TARGET{'S' if num_persons > 1 else ''}")
        self.alert_text.append(f">>> TRACKING INITIATED")
        self.alert_text.append("-" * 50)
        
        # Auto-scroll
        self.alert_text.verticalScrollBar().setValue(
            self.alert_text.verticalScrollBar().maximum()
        )
        
    def update_stats(self, targets, alerts, fps):
        """Mettre à jour les statistiques"""
        self.targets_label.setText(f"TARGETS: {targets}")
        self.alerts_label.setText(f"ALERTS: {alerts}")
        self.fps_label.setText(f"FPS: {fps:.1f}")
        
        # Changer la couleur selon les cibles
        if targets > 0:
            self.targets_label.setStyleSheet("""
                font-size: 16px; 
                font-weight: bold; 
                color: #ff0000;
            """)
        else:
            self.targets_label.setStyleSheet("""
                font-size: 16px; 
                font-weight: bold; 
                color: #00ffff;
            """)
            
    def clear_alerts(self):
        """Effacer le journal d'alertes"""
        self.alert_text.clear()
        self.alert_text.append(">>> LOG CLEARED")
        self.alert_text.append("=" * 50)
        
    def closeEvent(self, event):
        """Gérer la fermeture"""
        if self.detection_thread:
            self.detection_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Police monospace pour tout
    font = QFont("Courier New", 10)
    app.setFont(font)
    
    window = CyberpunkGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()