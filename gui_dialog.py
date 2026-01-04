from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton)
from PyQt5.QtCore import Qt

from config.settings import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD


class LoginDialog(QDialog):
    
    def __init__(self, security_manager):
        super().__init__()
        self.security = security_manager
        self.user_data = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🔐 LUCY - Authentification")
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
            }
            QLabel {
                color: #00ffff;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
            QLineEdit {
                background-color: #001a1a;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 8px;
                font-size: 14px;
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
            }
            QPushButton:pressed {
                background-color: #00ffff;
                color: #000000;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("◢◤◢ LUCY SECURITY ACCESS ◣◥◣")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 15px;")
        layout.addWidget(header)
        
        # Username
        username_label = QLabel("👤 User Name: ")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(DEFAULT_ADMIN_USERNAME)
        layout.addWidget(self.username_input)
        
        # 
        password_label = QLabel("🔑 Password: ")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.returnPressed.connect(self.try_login)
        layout.addWidget(self.password_input)
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff0000; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)
        
        login_btn = QPushButton("🔓 Have to be connected")
        login_btn.clicked.connect(self.try_login)
        login_btn.setMinimumHeight(45)
        layout.addWidget(login_btn)
        
        info = QLabel(f"Default: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
        info.setStyleSheet("color: #666666; font-size: 10px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def try_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.error_label.setText("⚠️ Obligatory")
            return
        
        success, result = self.security.authenticate(username, password)
        
        if success:
            self.user_data = result
            self.accept()
        else:
            self.error_label.setText(f"❌ {result}")
            self.password_input.clear()
            self.password_input.setFocus()