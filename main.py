"""
Game of Ur in Maya

This is a recreation of my very first Python project. While learning the language,
I created a playable board game inside of Maya, based on the ancient Mesopotamian "Royal Game of Ur".

This game uses API callbacks and automatically generated Maya objects to interact with the game code.
"""
import maya.OpenMaya as om

from game_pieces import *


def run():
    manager = GameManager()
    return manager


class GameManager(object):
    def __init__(self):
        self.running = True
        self.pieces = {}
        self.dice = []
        self.event_idx = None
        self.create_board()
        self.create_pieces()
        self.create_event()

        self.turn_stage = None
        self.player_turn = 0

        self.rolled_value = None

    def __del__(self):
        self.delete_all()

    def start_turn(self):
        self.turn_stage = "rolling"

    def add_piece(self, piece):
        self.pieces[piece.transform] = piece

    def create_event(self):
        self.event_idx = om.MEventMessage.addEventCallback("SelectionChanged", self._selection_made)
        # self.event_idx = pm.scriptJob(conditionTrue=['SelectionChanged', self._selection_made], protected=True)

    def delete_event(self):
        if self.event_idx is None:
            return
        om.MMessage.removeCallback(self.event_idx)

    def delete_all(self):
        self.delete_event()
        for piece in self.pieces.values():
            piece.delete_model()
        self.pieces = {}

    def _selection_made(self, *args):
        if not self.running:
            return
        print(args)
        sel = pm.selected()
        if not sel:
            return
        if sel[0] not in self.pieces:
            return
        gameobject = self.pieces[sel[0]]
        if isinstance(gameobject, Interactable):
            gameobject.action()
            pm.select(clear=True)

    def create_board(self):
        BoardTile(self)
        BoardTile(self, position=(1, 0, 0))
        BoardTile(self, position=(0, 0, 1))

    def create_pieces(self):
        Token(self)
        for i in range(4):
            self.dice.append(Die(self, position=(10 + (i % 2) * 3, 0, (i // 2) * 3)))


    def roll_dice(self):
        if not self.turn_stage == "rolling":
            return
        rolled_values = [die.roll() for die in self.dice]
        self.rollled_value = sum(rolled_values)
        print("Rolled: {} [{}]".format(self.rollled_value, "| ".join(map(str, rolled_values))))
        self.turn_stage = "moving"

if __name__ == '__main__':
    ur_manager = run()
