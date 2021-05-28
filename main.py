"""
Game of Ur in Maya

This is a recreation of my very first Python project. While learning the language,
I created a playable board game inside of Maya, based on the ancient Mesopotamian "Royal Game of Ur".

This game uses scriptjobs placed on automatically generated Maya objects to interact with the game code.
"""

from game_pieces import *


def run():
    manager = GameManager()
    return manager


class GameManager(object):
    def __init__(self):
        self.pieces = {}
        self.scriptjob = None
        self.create_board()
        self.create_pieces()
        self.create_scriptjob()
    def __del__(self):
        self.delete_scriptjob()

    def add_piece(self, piece):
        self.pieces[piece.transform] = piece

    def create_scriptjob(self):
        self.scriptjob = pm.scriptJob(conditionTrue=['SelectionChanged', self._selection_made], protected=True)
    def delete_scriptjob(self):
        if self.scriptjob is None:
            return
        print("kill sj")
        pm.scriptJob(kill=self.scriptjob, force=True)
    def _selection_made(self):
        print("sel")
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
