"""A simple dark colour scheme applied across the whole client application."""

DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QLineEdit, QTextEdit, QPlainTextEdit, QListWidget {
    background-color: #353535;
    border: 1px solid #444444;
    selection-background-color: #4a6f9c;
}
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    padding: 4px 10px;
}
QPushButton:hover {
    background-color: #4a4d4f;
}
QPushButton:disabled {
    color: #777777;
}
QStatusBar {
    background-color: #313335;
}
"""
