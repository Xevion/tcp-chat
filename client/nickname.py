# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Nickname.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_NicknameDialog(object):
    def setupUi(self, NicknameDialog):
        NicknameDialog.setObjectName("NicknameDialog")
        NicknameDialog.resize(449, 98)
        self.gridLayout = QtWidgets.QGridLayout(NicknameDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.buttonBox = QtWidgets.QDialogButtonBox(NicknameDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 6, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 0, 0, 1, 1)
        self.lineEdit = QtWidgets.QLineEdit(NicknameDialog)
        self.lineEdit.setObjectName("lineEdit")
        self.gridLayout.addWidget(self.lineEdit, 2, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self.gridLayout.addItem(spacerItem1, 4, 0, 1, 1)
        self.label = QtWidgets.QLabel(NicknameDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)

        self.retranslateUi(NicknameDialog)
        self.buttonBox.accepted.connect(NicknameDialog.accept)
        self.buttonBox.rejected.connect(NicknameDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NicknameDialog)

    def retranslateUi(self, NicknameDialog):
        _translate = QtCore.QCoreApplication.translate
        NicknameDialog.setWindowTitle(_translate("NicknameDialog", "Dialog"))
        self.lineEdit.setPlaceholderText(_translate("NicknameDialog", "Type your nickname..."))
        self.label.setText(_translate("NicknameDialog", "Please choose a nickname with 3 or more characters"))
