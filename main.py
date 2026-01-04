import sys
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QFont

from config.settings import VERSION, ADVANCED_FEATURES
from core.security_manager import SecurityManager
from core.ml_brain import LucyMLBrain
from gui.login_dialog import LoginDialog
from gui.main_window import LucyGUI


def print_banner():
    """Afficher bannière de démarrage"""
    print("=" * 70)
    print(f"  LUCY v{VERSION} - Learning Unified Cybersecurity System")
    print("=" * 70)
    print()
    print("Security fonctionallity:")
    print("  ✓ Secured Authentification(PBKDF2)")
    print("  ✓ AES-256 Encryption(Fernet)")
    print("  ✓ CompleteAudit trail")
    print("  ✓ Secured Session")
    print("  ✓ Lockout Protection (5 attempts)")
    print("  ✓ Secured Suppresiion of Every Files")
    print()
    print("Artificial Intelligence")
    if ADVANCED_FEATURES:
        print("  ✓ Facial recognition")
        print("  ✓ Emotion Detection")
        print("  ✓ Body analyse")
    else:
        print("  ⚠️  Advanced features disabled")
        print("  ⚠️  Install: pip install face_recognition mediapipe")
    print()
    print("Advenced Control:")
    print("  ✓ Vocal command (say 'Lucy start')")
    print("  ✓ Hands control (main ouverte/fermée)")
    print()
    print("⚠️  Needed dependencies:")
    print("  pip install opencv-python PyQt5 psutil numpy matplotlib")
    print("  pip install cryptography face_recognition mediapipe")
    print("  pip install SpeechRecognition pyttsx3 pyaudio")
    print()
    print("Default ID:")
    print("  Username: admin")
    print("  Password: Lucy2025!")
    print()
    print(" Starting camera software...")
    print("=" * 70)
    print()


def main():

    print_banner()
    
    app = QApplication(sys.argv)
    font = QFont("Courier New", 10)
    app.setFont(font)
    
    security_manager = SecurityManager()
    ml_brain = LucyMLBrain(security_manager)
    
    login_dialog = LoginDialog(security_manager)
    
    if login_dialog.exec_() == QDialog.Accepted:
        print(f"✓ Connexion achieved: {login_dialog.user_data['username']}")
        
        window = LucyGUI(login_dialog.user_data, security_manager, ml_brain)
        window.show()
        
        sys.exit(app.exec_())
    else:
        print("\n❌ Connexion refused")
        sys.exit(0)


if __name__ == "__main__":
    main()
