from PyQt5.QtWidgets import QDialog

from client.nickname import Ui_NicknameDialog


class NicknameDialog(QDialog, Ui_NicknameDialog):

    def __init__(self, *args, **kwargs):
        super(NicknameDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.disabled = True
        self.buttonBox.setDisabled(True)

        self.setWindowTitle("Set Nickname")

        self.lineEdit.returnPressed.connect(self.trySubmit)
        self.lineEdit.textEdited.connect(self.controlSubmit)
        self.show()

    def controlSubmit(self):
        """Updates whether or not the dialog box is allowed to proceed"""
        if len(self.lineEdit.text()) > 2:
            if self.disabled:
                self.disabled = False
                self.buttonBox.setDisabled(False)
        else:
            if not self.disabled:
                self.disabled = True
                self.buttonBox.setDisabled(True)

    def trySubmit(self):
        """Tries to submit the Dialog through the QLineEdit via Enter key"""
        if not self.disabled:
            self.accept()
