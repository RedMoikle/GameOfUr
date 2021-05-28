"""
Game of Ur in Maya

This is a recreation of my very first Python project. While learning the language,
I created a playable board game inside of Maya, based on the ancient Mesopotamian "Royal Game of Ur".

This game uses scriptjobs placed on automatically generated Maya objects to interact with the game code.
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
        self.event_idx = None
        self.create_board()
        self.create_pieces()
        self.create_event()

    def __del__(self):
        self.delete_event()

    def add_piece(self, piece):
        self.pieces[piece.transform] = piece

    def create_event(self):
        self.event_idx = om.MEventMessage.addEventCallback("SelectionChanged", self._selection_made)
        # self.event_idx = pm.scriptJob(conditionTrue=['SelectionChanged', self._selection_made], protected=True)

    def delete_event(self):
        if self.event_idx is None:
            return
        om.MMessage.removeCallback(self.event_idx)

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
        Interactable(self)


if __name__ == '__main__':
    ur_manager = run()
