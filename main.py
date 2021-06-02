"""
Game of Ur in Maya

This is a recreation of my very first Python project. While learning the language,
I created a playable board game inside of Maya, based on the ancient Mesopotamian "Royal Game of Ur".

This game uses API callbacks and automatically generated Maya objects to interact with the game code.
"""
import maya.OpenMaya as om

from game_pieces import *
import interface
from utils import Messages, Signal


def run():
    try:
        manager = GameManager()
        ui = interface.UrGameWindow.show_dialog()

        ui.end_turn_button.clicked.connect(manager.end_turn)
        ui.delete_event_action.triggered.connect(manager.delete_event)
        ui.delete_all_action.triggered.connect(manager.delete_all)
        ui.active_action.toggled.connect(manager.set_event_active)
        ui.new_game.connect(manager.start_game)
        ui.roll_num_btn.clicked.connect(manager.roll_dice)
        manager.dice_rolled.connect(ui.set_roll)
        manager.point_scored.connect(ui.set_score)
        manager.message_updated.connect(ui.set_message)
        manager.cant_move.connect(ui.enable_end_btn)
        manager.roll_requested.connect(ui.reset_roll)
        manager.new_game_started.connect(ui.reset_ui)
        manager.game_won.connect(ui.win_message)

        manager.start_game()
        return manager, ui
    except Exception as e:
        manager.delete_event()
        raise e



class GameManager(object):
    TILE_NOTHING = 0
    TILE_NORMAL = 1
    TILE_ROSETTA = 2
    TILE_GOAL = 3

    message_text = {Messages.INVALID_MOVE: "Invalid move.",
                    Messages.FREE_TURN: "Landed on a rosetta: Free turn.",
                    Messages.MOVE_BLOCKED: "Move blocked.",
                    Messages.FRIENDLY_TOKEN: "A friendly token is in the way",
                    Messages.OPPONENT_TOKEN: "An opponent's token is in the way",
                    Messages.PROTECTED_OPPONENT: "The opponent's token is protected by the rosetta tile.",
                    Messages.DISPLACED_OPPONENT: "You sent the opponent's token back home.",
                    Messages.TOO_FAR: "Too far! This would overshoot the goal.",
                    Messages.PATH_COMPLETE: "One token reached the goal, you get 1 point!",
                    Messages.MOVE_SUCCESSFULL: "Moved token"}
    STAGE_ROLLING = "rolling"
    STAGE_MOVING = "moving"

    dice_rolled = Signal()
    point_scored = Signal()
    message_updated = Signal()
    cant_move = Signal()
    roll_requested = Signal()
    new_game_started = Signal()
    game_won = Signal()

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

        self.player_scores = [0] * self.players
        self.target_score = 7
        self.token_count = 7
        self.running = False
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

    def __del__(self):
        self.delete_all()

    def start_game(self):
        self.set_event_active(True)
        self.player_scores = [0] * self.players
        self.rolled_value = None

        for piece in self.pieces.values():
            piece.reset()

        self.new_game_started.emit()
        self.start_turn(0)

    def set_event_active(self, active):
        self.running = active

    def add_piece(self, piece):
        self.pieces[piece.transform] = piece

    def create_board(self):
        Floor(self, position=(1.5, -1, 5))
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
        sel = pm.selected()
        if not sel:
            return
        if sel[0] not in self.pieces:
            return
        game_object = self.pieces[sel[0]]
        if isinstance(game_object, Interactable):
            game_object.trigger_action()
            pm.select(clear=True)

    def create_pieces(self):
        Token.point_scored.connect(self.score_point)
        Token.move_successful.connect(self.piece_moved)
        Token.move_unsuccessful.connect(self.piece_blocked)
        Die.die_clicked.connect(self.roll_dice)
        for player_i in range(self.players):
            for i in range(self.token_count):
                new_token = Token(self,
                                  player=player_i,
                                  token_id=i,
                                  path=self.paths[player_i])
                self.tokens.append(new_token)
        for i in range(4):
            self.dice.append(Die(self,
                                 position=((i // 2) * 4, -1, 10 + (i % 2) * 3),
                                 position_randomness=(1, 0, 0.5)))

    def roll_dice(self):
        if not self.turn_stage == self.STAGE_ROLLING:
            return
        rolled_values = [die.roll() for die in self.dice]
        self.rolled_value = sum(rolled_values)
        print("Rolled: {} [{}]".format(self.rolled_value, "| ".join(map(str, rolled_values))))
        self.turn_stage = self.STAGE_MOVING
        self.dice_rolled.emit(rolled_values)
        if not self.can_move(self.rolled_value, self.player_turn):
            self.cant_move.emit()

    def can_move(self, distance, player):
        for token in self.tokens:
            if not token.player == player:
                continue
            if token.can_move(distance):
                return True
        return False

    def start_turn(self, player):
        self.turn_stage = self.STAGE_ROLLING
        self.player_turn = player
        self.roll_requested.emit(player)

    def end_turn(self):
        self.start_turn((self.player_turn + 1) % self.players)

    def free_turn(self):
        self.turn_stage = self.STAGE_ROLLING
        self.roll_requested.emit(self.player_turn)

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
        self.point_scored.emit(player, self.player_scores[player])
        if self.player_scores[player] >= self.target_score:
            self.win_game(player)

    def win_game(self, player):
        print("player {} wins".format(player + 1))
        self.message_updated.emit("Player {} wins!".format(player + 1))
        self.game_won.emit(player)
        self.running = False

    def piece_moved(self, messages):
        print(messages)
        self.message_updated.emit([self.message_text[m] for m in messages])
        if Messages.FREE_TURN not in messages:
            self.end_turn()

    def piece_blocked(self, messages):
        print(messages)
        self.message_updated.emit([self.message_text[m] for m in messages])


if __name__ == '__main__':
    ur_manager, ur_ui = run()
