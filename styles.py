"""
LUCY - Styles
Styles CSS/Qt pour l'interface
"""

MAIN_STYLESHEET = """
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
    font-size: 11px;
    padding: 5px;
}
QFrame {
    border: 2px solid #00ffff;
    background-color: #001a1a;
    padding: 5px;
}
QProgressBar {
    border: 2px solid #00ffff;
    border-radius: 3px;
    text-align: center;
    background-color: #000000;
    color: #00ffff;
    font-weight: bold;
    height: 20px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00ffff, stop:1 #00aaaa);
}
QCheckBox {
    color: #00ffff;
    font-family: 'Courier New', monospace;
    spacing: 5px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #00ffff;
    background-color: #000000;
}
QCheckBox::indicator:checked {
    background-color: #00ffff;
}
"""

HEADER_STYLE = """
font-size: 18px;
font-weight: bold;
padding: 10px;
background-color: #001a1a;
border: 3px solid #00ffff;
color: #00ffff;
"""

VIDEO_LABEL_STYLE = """
border: 3px solid #00ffff;
background-color: #000000;
color: #00ffff;
font-size: 16px;
font-weight: bold;
"""

STATS_STYLE = "font-size: 14px; font-weight: bold;"

ALERT_HEADER_STYLE = """
font-size: 14px;
font-weight: bold;
padding: 6px;
background-color: #001a1a;
border: 2px solid #00ffff;
"""

VOICE_STATUS_STYLE = """
font-size: 12px;
padding: 8px;
background-color: #003333;
border: 2px solid #00ffff;
color: #00ff00;
"""

CLOCK_STYLE = "font-size: 14px; color: #00ffff; font-weight: bold;"

ML_LABEL_STYLE = "font-size: 12px; color: #ff00ff;"

RESOURCE_LABEL_STYLE = "font-size: 10px; color: #00ffff;"