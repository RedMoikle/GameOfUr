import sys

import pymel.core as pm
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui

py_version = sys.version_info.major
DIALOG_NAME = 'MGS_UR_dialog'
def maya_main_window():
    main_window = omui.MQtUtil.mainWindow()
    if py_version >= 3:
        return wrapInstance(int(main_window), QtWidgets.QWidget)
    return wrapInstance(long(main_window), QtWidgets.QWidget)

class UrGameWindow(QtWidgets.QDialog):
    dlg_instance = None
    def __init__(self, parent=maya_main_window()):
        super(UrGameWindow, self).__init__(parent)

        self.setObjectName(DIALOG_NAME)
        self.setWindowTitle("Royal Game of Ur, by Michael Stickler")
        self.setMinimumSize(300, 80)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
    @classmethod
    def show_dialog(cls):
        if cls.dlg_instance is None:
            cls.dlg_instance = cls()

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()
        return cls.dlg_instance

    def create_widgets(self):
        self.score_label = QtWidgets.QLabel("Score:")
        self.p1_score = QtWidgets.QLabel("0")
        self.p2_score = QtWidgets.QLabel("0")
        self.roll_num = QtWidgets.QLabel("_")
        self.info_text = QtWidgets.QLineEdit()
        self.end_turn_button = QtWidgets.QPushButton("End turn", enabled=False)


    def create_layouts(self):
        score_layout = QtWidgets.QHBoxLayout()
        score_layout.addWidget(self.p1_score)
        score_layout.addWidget(self.p2_score)

        info_layout = QtWidgets.QHBoxLayout()
        info_layout.addWidget(self.roll_num)
        info_layout.addWidget(self.info_text)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.score_label)
        main_layout.addLayout(score_layout)
        main_layout.addLayout(info_layout)
        main_layout.addWidget(self.end_turn_button)

    def create_connections(self):
        pass

