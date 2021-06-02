import sys
from PySide2 import QtCore, QtGui
from PySide2.QtWidgets import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui

py_version = sys.version_info.major
DIALOG_NAME = 'MGS_UR_dialog'

# TODO: replace colours with palettes
p1_colour = "QWidget {background-color:#E6E6E6; color:#000000}"
p2_colour = "QWidget {background-color:#191919; color:#FFFFFF}"


def maya_main_window():
    """Get a reference to Maya's main window"""
    main_window = omui.MQtUtil.mainWindow()
    if py_version >= 3:
        return wrapInstance(int(main_window), QWidget)
    return wrapInstance(long(main_window), QWidget)


class UrGameWindow(QDialog):
    """
    Main ui window for the game. This contains useful information about the game for convenience such as scores,
    rolled values and information about the last move

    :param parent: The parent widget for this interface (Default is Maya's main window)
    :type parent: QWidget
    """
    dlg_instance = None
    new_game = QtCore.Signal()

    def __init__(self, parent=maya_main_window()):
        super(UrGameWindow, self).__init__(parent)

        self.setObjectName(DIALOG_NAME)
        self.setWindowTitle("Royal Game of Ur, by Michael Stickler")
        self.setMinimumSize(300, 80)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.big_font = QtGui.QFont(self.font())
        self.big_font.setPointSize(20)
        self.med_font = QtGui.QFont(self.font())
        self.big_font.setPointSize(15)

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def closeEvent(self, event):
        """Overridden from QDialog to clean up the game if the UI is closed."""
        self.delete_all_action.trigger()
        event.accept()

    @classmethod
    def show_dialog(cls):
        """
        Classmethod to show the UI (and create it if it doesn't exist already)
        :return: The dialog window for this widget
        :rtype: UrGameWindow

        :Example:
            ur_interface = UrGameWindow.show_dialog()
        """
        if cls.dlg_instance is None:
            cls.dlg_instance = cls()

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()
        return cls.dlg_instance

    def set_score(self, player, score):
        """
        Set the score display for the specified player index
        :param player: Index of the player (0 is player 1)
        :type player: int
        :param score: Score value to set
        :type score: int
        """
        # TODO: replace p1 and p2 scores with list
        if player == 0:
            self.p1_score.setText(str(score))
        elif player == 1:
            self.p2_score.setText(str(score))

    def set_roll(self, values):
        """
        Set the display for the rolled value
        :param values: List of all rolled dice values
        :type values: List(int)
        """
        self.roll_num_btn.setText(str(sum(values)))

    def set_message(self, messages):
        """
        Set a series of messages to be displayed in the info panel
        :param messages: list of message strings
        :type messages: List[str]
        """
        self.info_text.setText("\n".join(map(str, messages)))

    def disable_end_btn(self):
        self.end_turn_button.setEnabled(False)

    def enable_end_btn(self):
        self.end_turn_button.setEnabled(True)

    def create_actions(self):
        self.new_game_action = QAction("New game", self)
        self.delete_all_action = QAction("Delete all", self)
        self.delete_event_action = QAction("Delete event", self)
        self.active_action = QAction("Event active", self)
        self.active_action.setCheckable(True)
        self.active_action.setChecked(True)

    def create_widgets(self):
        self.menu = QMenuBar()
        game_menu = self.menu.addMenu("Game")
        game_menu.addAction(self.new_game_action)

        debug_menu = self.menu.addMenu("Debug")
        debug_menu.addAction(self.delete_all_action)
        debug_menu.addAction(self.delete_event_action)
        debug_menu.addAction(self.active_action)

        self.score_label = QLabel("<b>Score:</b>")
        self.p1_score = QLabel()
        self.p1_score.setAlignment(QtCore.Qt.AlignCenter)
        self.p1_score.setStyleSheet(p1_colour)
        self.p1_score.setFont(self.med_font)
        self.p1_score.setMinimumSize(32, 32)
        self.p2_score = QLabel()
        self.p2_score.setAlignment(QtCore.Qt.AlignCenter)
        self.p2_score.setStyleSheet(p2_colour)
        self.p2_score.setFont(self.med_font)
        self.p2_score.setMinimumSize(32, 32)

        self.roll_num_btn = QPushButton()
        self.roll_num_btn.setFont(self.big_font)
        self.roll_num_btn.setMinimumSize(64, 64)
        self.info_text = QTextEdit()
        self.info_text.setMinimumSize(100, 64)
        self.info_text.setFixedHeight(64)
        self.info_text.setReadOnly(True)
        self.end_turn_button = QPushButton("End turn (no move possible)", enabled=False)
        self.reset_ui()

    def create_layouts(self):
        score_layout = QHBoxLayout()
        score_layout.addWidget(self.p1_score)
        score_layout.addWidget(self.p2_score)

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.roll_num_btn)
        info_layout.addWidget(self.info_text)

        main_layout = QVBoxLayout(self)
        main_layout.setMenuBar(self.menu)
        main_layout.addWidget(self.score_label)
        main_layout.addLayout(score_layout)
        main_layout.addLayout(info_layout)
        main_layout.addWidget(self.end_turn_button)

    def create_connections(self):
        self.end_turn_button.clicked.connect(self.disable_end_btn)
        self.new_game_action.triggered.connect(self._start_new_game)

    def reset_ui(self):
        """Reset the ui for a new game"""
        self.reset_roll(0)
        self.set_score(0, 0)
        self.set_score(1, 0)
        self.set_message(["Select one of the dice to roll them and begin!"])

    def reset_roll(self, player):
        """
        Reset the die roll display to be ready for a new roll from the specified player.
        :param player: player index (0 is player 1) to change colours to
        :type player: int
        """
        self.roll_num_btn.setText("Roll!")
        if player == 0:
            self.roll_num_btn.setStyleSheet(p1_colour)
        elif player == 1:
            self.roll_num_btn.setStyleSheet(p2_colour)

    def _start_new_game(self):
        self.new_game.emit()

    def win_message(self, player):
        """
        Display a win message dialog and ask if the player wants to start a new game
        :param player: The index of the player who won the game (0 is player 1)
        :type player: int
        """
        button_reply = QMessageBox.question(self, "Player {} wins!".format(player + 1), "Start a new game?",
                                           buttons=[QMessageBox.Close, QMessageBox.Ok], defaultButton=QMessageBox.Ok)
        if button_reply == QMessageBox.Ok:
            self._start_new_game()
