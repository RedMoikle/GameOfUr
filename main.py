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
    TILE_NOTHING = 0
    TILE_NORMAL = 1
    TILE_ROSETTA = 2
    TILE_GOAL = 3

    STAGE_ROLLING = "rolling"
    STAGE_MOVING = "moving"

    def __init__(self):
        self.board_scale = 1.0
        self.board = [2, 1, 2,
                      1, 1, 1,
                      1, 1, 1,
                      1, 2, 1,
                      0, 1, 0,
                      3, 1, 3,
                      2, 1, 2,
                      1, 1, 1]

        self.players = 2
        self.paths = [[9, 6, 3, 0, 1, 4, 7, 10, 13, 16, 19, 22, 21, 18, 15],
                      [11, 8, 5, 2, 1, 4, 7, 10, 13, 16, 19, 22, 23, 20, 17]]

        self.player_scores = [0]*self.players
        self.target_score = 7
        self.token_count = 7
        self.running = True
        self.pieces = {}
        self.tokens = []
        self.dice = []
        self.event_idx = None
        self.create_board()
        self.create_pieces()
        pm.select(clear=True)
        self.create_event()

        self.turn_stage = None
        self.player_turn = 0

        self.rolled_value = None
        self.start_turn()

    def __del__(self):
        self.delete_all()

    def start_turn(self):
        self.turn_stage = self.STAGE_ROLLING

    def add_piece(self, piece):
        self.pieces[piece.transform] = piece

    def create_board(self):
        for i, tile in enumerate(self.board):
            if tile in [1, 2]:
                BoardTile(self, position=(i % 3, 0, i // 3), rosetta=tile == 2)

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
            piece.delete_textures()
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

    def create_pieces(self):
        for player_i in range(self.players):
            for i in range(self.token_count):
                new_token = Token(self,
                                  player=player_i,
                                  token_id=i,
                                  path=self.paths[player_i])
                self.tokens.append(new_token)
        for i in range(4):
            self.dice.append(Die(self, position=((i // 2) * 3, 0, 10 + (i % 2) * 3)))

    def roll_dice(self):
        if not self.turn_stage == self.STAGE_ROLLING:
            return
        rolled_values = [die.roll() for die in self.dice]
        self.rolled_value = sum(rolled_values)
        print("Rolled: {} [{}]".format(self.rolled_value, "| ".join(map(str, rolled_values))))
        self.turn_stage = self.STAGE_MOVING
        if self.rolled_value == 0:
            self.end_turn()

    def end_turn(self):
        self.turn_stage = self.STAGE_ROLLING
        self.player_turn = (self.player_turn + 1) % self.players

    def free_turn(self):
        self.turn_stage = self.STAGE_ROLLING

    def get_position_collision(self, tile_position):
        """Check if a token already exists on the specified tile.
        If one is present, return the token, otherwise return None"""
        # don't check for collisions if the tile_location is not specified (not on the board)
        if tile_position is None:
            return None

        # check for collisions
        for token in self.tokens:
            if token.tile_location == tile_position:
                return token
        return None
    def score_point(self, player):
        self.player_scores[player] += 1
        if self.player_scores[player] >= self.target_score:
            self.win_game(player)
    def win_game(self, player):
        print("player {} wins".format(player+1))
        self.running = False
if __name__ == '__main__':
    ur_manager = run()
