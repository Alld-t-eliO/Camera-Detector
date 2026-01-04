import os
import psutil
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextEdit, QFrame, QProgressBar,
                             QGridLayout, QCheckBox, QMessageBox, QDialog)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap

from config.settings import (RESOURCE_UPDATE_INTERVAL, CLOCK_UPDATE_INTERVAL,
                             CAMERA_WIDTH, CAMERA_HEIGHT)
from detection.detection_thread import DetectionThread
from detection.emotion_pose import EmotionPoseDetector
from controllers.voice_assistant import VoiceAssistant
from gui.activity_graph import ActivityGraph
from gui.styles import (MAIN_STYLESHEET, HEADER_STYLE, VIDEO_LABEL_STYLE,
                        STATS_STYLE, ALERT_HEADER_STYLE, VOICE_STATUS_STYLE,
                        CLOCK_STYLE, ML_LABEL_STYLE, RESOURCE_LABEL_STYLE)
from gui.login_dialog import LoginDialog


class LucyGUI(QMainWindow):
    
    def __init__(self, user_data, security_manager, ml_brain):
        super().__init__()
        self.user_data = user_data
        self.security = security_manager
        self.ml_brain = ml_brain
        self.detection_thread = None
        self.voice_assistant = None
        self.emotion_pose_detector = EmotionPoseDetector()
        self.is_monitoring = False
        
        self.init_ui()
        
        self.resource_timer = QTimer()
        self.resource_timer.timeout.connect(self.update_resources)
        self.resource_timer.start(RESOURCE_UPDATE_INTERVAL)
        
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(CLOCK_UPDATE_INTERVAL)
        
        self.start_voice_assistant()
    
    def init_ui(self):
        self.setWindowTitle(f"◢ LUCY v1.0 - Connected: {self.user_data['username']} ◣")
        self.setGeometry(50, 50, 1800, 950)
        self.setStyleSheet(MAIN_STYLESHEET)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_layout = self.create_left_panel()
        main_layout.addLayout(left_layout, 2)

        right_layout = self.create_right_panel()
        main_layout.addLayout(right_layout, 1)
    
    def create_left_panel(self):
        left_layout = QVBoxLayout()
        
        header = QLabel(f"◢◤◢ LUCY AI SYSTEM - User: {self.user_data['username']} ◣◥◣")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        left_layout.addWidget(header)
        
        self.video_label = QLabel("◢◤ CAMERA OFFLINE ◥◣\n\nPress START")
        self.video_label.setMinimumSize(CAMERA_WIDTH, CAMERA_HEIGHT)
        self.video_label.setMaximumSize(CAMERA_WIDTH, CAMERA_HEIGHT)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet(VIDEO_LABEL_STYLE)
        left_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        stats_frame = self.create_stats_panel()
        left_layout.addWidget(stats_frame)

        options_frame = self.create_options_panel()
        left_layout.addWidget(options_frame)

        control_layout = self.create_control_buttons()
        left_layout.addLayout(control_layout)
        
        return left_layout
    
    def create_stats_panel(self):
        stats_frame = QFrame()
        stats_layout = QHBoxLayout(stats_frame)
        
        self.targets_label = QLabel("TARGETS: 0")
        self.targets_label.setStyleSheet(STATS_STYLE)
        
        self.alerts_label = QLabel("ALERTS: 0")
        self.alerts_label.setStyleSheet(STATS_STYLE)
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet(STATS_STYLE)
        
        stats_layout.addWidget(self.targets_label)
        stats_layout.addWidget(QLabel("│"))
        stats_layout.addWidget(self.alerts_label)
        stats_layout.addWidget(QLabel("│"))
        stats_layout.addWidget(self.fps_label)
        
        return stats_frame
    
    def create_options_panel(self):
        options_frame = QFrame()
        options_layout = QGridLayout(options_frame)
        
        self.night_mode_cb = QCheckBox("· Night mode")
        self.night_mode_cb.stateChanged.connect(self.toggle_night_mode)
        
        self.face_recognition_cb = QCheckBox("· Recognition")
        self.face_recognition_cb.setChecked(True)
        self.face_recognition_cb.stateChanged.connect(self.toggle_face_recognition)
        
        self.trajectories_cb = QCheckBox("· Movements")
        self.trajectories_cb.setChecked(True)
        self.trajectories_cb.stateChanged.connect(self.toggle_trajectories)
        
        options_layout.addWidget(self.night_mode_cb, 0, 0)
        options_layout.addWidget(self.face_recognition_cb, 0, 1)
        options_layout.addWidget(self.trajectories_cb, 1, 0)
        
        return options_frame
    
    def create_control_buttons(self):
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ START")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self.start_monitoring)
        
        self.stop_btn = QPushButton("■ STOP")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        return control_layout
    
    def create_right_panel(self):
        right_layout = QVBoxLayout()
        
        info_frame = self.create_info_panel()
        right_layout.addWidget(info_frame)
        
        self.voice_status = QLabel("🎤 Assistant vocal: Initialisation...")
        self.voice_status.setAlignment(Qt.AlignCenter)
        self.voice_status.setStyleSheet(VOICE_STATUS_STYLE)
        right_layout.addWidget(self.voice_status)
        
        graph_header = QLabel("◢ ACTIVITY ◣")
        graph_header.setAlignment(Qt.AlignCenter)
        graph_header.setStyleSheet(ALERT_HEADER_STYLE)
        right_layout.addWidget(graph_header)
        
        self.activity_graph = ActivityGraph(self, width=5, height=2)
        right_layout.addWidget(self.activity_graph)
        
        alert_header = QLabel("◢ ALERTS ◣")
        alert_header.setAlignment(Qt.AlignCenter)
        alert_header.setStyleSheet(ALERT_HEADER_STYLE)
        right_layout.addWidget(alert_header)
        
        self.alert_text = QTextEdit()
        self.alert_text.setReadOnly(True)
        self.alert_text.setMaximumHeight(150)
        self.alert_text.append(">>> LUCY v6.0 INITIALIZED")
        self.alert_text.append(">>> Security: ACTIVE")
        self.alert_text.append(">>> Encryption: AES-256")
        self.alert_text.append(">>> ML Brain: READY")
        self.alert_text.append("=" * 50)
        right_layout.addWidget(self.alert_text)
        
        resource_header = QLabel("◢ RESOURCES ◣")
        resource_header.setAlignment(Qt.AlignCenter)
        resource_header.setStyleSheet(ALERT_HEADER_STYLE)
        right_layout.addWidget(resource_header)
        
        resource_frame = self.create_resource_panel()
        right_layout.addWidget(resource_frame)
        
        btn_layout = self.create_bottom_buttons()
        right_layout.addLayout(btn_layout)
        
        return right_layout
    
    def create_info_panel(self):
       
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet(CLOCK_STYLE)
        
        ml_stats = self.ml_brain.get_stats()
        self.ml_label = QLabel(f"ML: {ml_stats['total_patterns']} patterns")
        self.ml_label.setStyleSheet(ML_LABEL_STYLE)
        
        info_layout.addWidget(self.clock_label)
        info_layout.addWidget(QLabel("│"))
        info_layout.addWidget(self.ml_label)
        
        self.update_clock()
        
        return info_frame
    
    def create_resource_panel(self):
       
        resource_frame = QFrame()
        resource_layout = QGridLayout(resource_frame)
        
        cpu_lbl = QLabel("CPU:")
        cpu_lbl.setStyleSheet(RESOURCE_LABEL_STYLE)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setMaximum(100)
        self.cpu_value = QLabel("0%")
        self.cpu_value.setStyleSheet(RESOURCE_LABEL_STYLE)
        
        ram_lbl = QLabel("RAM:")
        ram_lbl.setStyleSheet(RESOURCE_LABEL_STYLE)
        self.ram_bar = QProgressBar()
        self.ram_bar.setMaximum(100)
        self.ram_value = QLabel("0%")
        self.ram_value.setStyleSheet(RESOURCE_LABEL_STYLE)
        
        resource_layout.addWidget(cpu_lbl, 0, 0)
        resource_layout.addWidget(self.cpu_bar, 0, 1)
        resource_layout.addWidget(self.cpu_value, 0, 2)
        resource_layout.addWidget(ram_lbl, 1, 0)
        resource_layout.addWidget(self.ram_bar, 1, 1)
        resource_layout.addWidget(self.ram_value, 1, 2)
        
        return resource_frame
    
    def create_bottom_buttons(self):
       
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("⊗ CLEAR")
        clear_btn.setMinimumHeight(30)
        clear_btn.clicked.connect(lambda: self.alert_text.clear())
        
        logout_btn = QPushButton("🚪 LOGOUT")
        logout_btn.setMinimumHeight(30)
        logout_btn.clicked.connect(self.logout)
        
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(logout_btn)
        
        return btn_layout
    
 
    def start_voice_assistant(self):
       
        try:
            self.voice_assistant = VoiceAssistant()
            self.voice_assistant.command_signal.connect(self.handle_voice_command)
            self.voice_assistant.status_signal.connect(self.update_voice_status)
            self.voice_assistant.start()
            self.voice_status.setText("Vocal Assistant: Actif")
        except Exception as e:
            self.voice_status.setText(f"Vocal Assistant: Error")
            print(f"⚠️ Vocal Assistant not disponible: {e}")
    
    def handle_voice_command(self, command):
       
        self.alert_text.append(f"<span style='color:#00ff00'>🎤 Commande: {command}</span>")
        
        if command == 'start_surveillance':
            self.start_monitoring()
        elif command == 'stop_surveillance':
            self.stop_monitoring()
        elif command == 'night_mode':
            self.night_mode_cb.setChecked(not self.night_mode_cb.isChecked())
        elif command == 'show_status':
            self.show_system_status()
    
    def update_voice_status(self, status):
      
        self.voice_status.setText(f"🎤 {status}")
    
    def show_system_status(self):
      
        ml_stats = self.ml_brain.get_stats()
        msg = QMessageBox(self)
        msg.setWindowTitle("LUCY System Status")
        msg.setText(f"""
 LUCY v1.0 - System Status

· User: {self.user_data['username']}
· Security: Active (AES-256)
· ML Patterns: {ml_stats['total_patterns']}
· Warning: {self.alert_count if hasattr(self, 'alert_count') else 0}
·Vocal assistant : {'Actif' if self.voice_assistant and self.voice_assistant.running else 'Inactif'}
· Surveillance: {'Active' if self.is_monitoring else 'Inactive'}
        """)
        msg.exec_()
    
    # === SURVEILLANCE ===
    
    def start_monitoring(self):
       
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.alert_text.append("\n" + "=" * 50)
        self.alert_text.append(f">>> [{datetime.now().strftime('%H:%M:%S')}] SURVEILLANCE ACTIVATED")
        self.alert_text.append(">>> All systems operational")
        self.alert_text.append("=" * 50 + "\n")
        
        self.detection_thread = DetectionThread(
            self.security, 
            self.ml_brain,
            self.emotion_pose_detector
        )
        self.detection_thread.change_pixmap.connect(self.update_image)
        self.detection_thread.alert_signal.connect(self.add_alert)
        self.detection_thread.stats_signal.connect(self.update_stats)
        self.detection_thread.graph_signal.connect(self.update_graph)
        self.detection_thread.ml_learn_signal.connect(self.ml_learn)
        self.detection_thread.start()
        
        self.security.log_action(self.user_data['user_id'], "START_SURVEILLANCE", 
                                "Surveillance started", True)
        
        if self.voice_assistant:
            self.voice_assistant.speak("Surveillance activée")

    def stop_monitoring(self):
       
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if self.detection_thread:
            self.detection_thread.stop()
        
        self.video_label.setText("◢◤ CAMERA OFFLINE ◥◣\n\nAppuyez sur START")
        self.targets_label.setText("TARGETS: 0")
        self.fps_label.setText("FPS: 0.0")
        
        self.alert_text.append("\n" + "=" * 50)
        self.alert_text.append(f">>> [{datetime.now().strftime('%H:%M:%S')}] SURVEILLANCE DEACTIVATED")
        self.alert_text.append("=" * 50 + "\n")
        
        self.security.log_action(self.user_data['user_id'], "STOP_SURVEILLANCE", 
                                "Surveillance stopped", True)
        
        if self.voice_assistant:
            self.voice_assistant.speak("Surveillance detected")
    
    
    def update_image(self, image):
       
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def update_graph(self, count):
        
        self.activity_graph.update_graph(count)

    def add_alert(self, num_persons, timestamp, alert_type, extras):
       
        alerts_map = {
            "NEW_TARGET": ("NEW TARGET", "#00ff00"),
            "MULTIPLE_TARGETS": (f"{num_persons} MULTIPLE TARGETS", "#ffff00"),
        }
        
        alert_text, color = alerts_map.get(alert_type, ("warning", "#ffffff"))
        
        self.alert_text.append(f"<span style='color:{color}'>[{timestamp}] ⚠ {alert_text}</span>")
        
        if 'identities' in extras:
            identities = ", ".join(extras['identities'])
            self.alert_text.append(f"<span style='color:#00ffff'>👤 Identités: {identities}</span>")
        
        if 'emotions' in extras:
            emotions = ", ".join(extras['emotions'])
            self.alert_text.append(f"<span style='color:#ffff00'>😊 Émotions: {emotions}</span>")
        
        if 'poses' in extras:
            poses = ", ".join(extras['poses'])
            self.alert_text.append(f"<span style='color:#ff00ff'>🤸 Poses: {poses}</span>")
        
        self.alert_text.append(f"<span style='color:#00ffff'>🔐 Photo: {os.path.basename(extras.get('encrypted_photo', 'N/A'))}</span>")
        self.alert_text.append("-" * 50)
        
        self.alert_text.verticalScrollBar().setValue(
            self.alert_text.verticalScrollBar().maximum()
        )
        
        if self.voice_assistant:
            if num_persons == 1:
                self.voice_assistant.speak("One person detected")
            else:
                self.voice_assistant.speak(f"{num_persons} Peoples detected")

    def update_stats(self, targets, alerts, fps):
       
        self.targets_label.setText(f"TARGETS: {targets}")
        self.alerts_label.setText(f"ALERTS: {alerts}")
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.alert_count = alerts
        
        if targets > 0:
            self.targets_label.setStyleSheet(STATS_STYLE + "color: #ff0000;")
        else:
            self.targets_label.setStyleSheet(STATS_STYLE + "color: #00ffff;")
    
    def ml_learn(self, features):
        
        behavior, confidence = self.ml_brain.predict_behavior(features)
        
        if behavior == "normal" and confidence > 0.8:
            self.ml_brain.learn_pattern('normal_activity', features, 'normal')
    
    
    def update_clock(self):
      
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.clock_label.setText(f"◢ {current_date} {current_time} ◣")
    
    def update_resources(self):
       
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram_percent = psutil.virtual_memory().percent
        
        self.cpu_bar.setValue(int(cpu_percent))
        self.cpu_value.setText(f"{cpu_percent:.1f}%")
        self.ram_bar.setValue(int(ram_percent))
        self.ram_value.setText(f"{ram_percent:.1f}%")
        
        ml_stats = self.ml_brain.get_stats()
        self.ml_label.setText(f"ML: {ml_stats['total_patterns']} patterns")
    
    
    def toggle_night_mode(self, state):
       
        if self.detection_thread:
            self.detection_thread.night_mode = (state == Qt.Checked)
            self.security.log_action(self.user_data['user_id'], "NIGHT_MODE", 
                                    f"Night mode: {state == Qt.Checked}", True)
    
    def toggle_face_recognition(self, state):
       
        if self.detection_thread:
            self.detection_thread.face_recognition_enabled = (state == Qt.Checked)
    
    def toggle_trajectories(self, state):
       
        if self.detection_thread:
            self.detection_thread.show_trajectories = (state == Qt.Checked)
        
    def logout(self):

        reply = QMessageBox.question(self, 'Déconnexion', 
                                     'Do you really want to disconnect?',
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.is_monitoring:
                self.stop_monitoring()
            
            if self.voice_assistant:
                self.voice_assistant.stop()
            
            self.security.log_action(self.user_data['user_id'], "LOGOUT", 
                                    "User logged out", True)
            self.ml_brain.save_model()
            
            self.close()
            
            login_dialog = LoginDialog(self.security)
            if login_dialog.exec_() == QDialog.Accepted:
                new_window = LucyGUI(login_dialog.user_data, self.security, 
                                    self.ml_brain)
                new_window.show()
    
    def closeEvent(self, event):
        if self.is_monitoring:
            self.stop_monitoring()
        
        if self.voice_assistant:
            self.voice_assistant.stop()
        
        self.ml_brain.save_model()
        self.security.log_action(self.user_data['user_id'], "APP_CLOSE", 
                                "Application closed", True)
        event.accept()