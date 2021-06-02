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
    """
    Set up and run the game.

    :return:
    :rtype: Tuple(GameManager, interface.UrGameWindow)
    """
    manager = None
    try:
        manager = GameManager()
        ui = interface.UrGameWindow.show_dialog()

        # connect game to ui
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
        # delete selection event/scriptjob if there is an error in setup
        if manager is not None:
            manager.delete_event()
        print(e)


class GameManager(object):
    """
    Manages the game, tracks scores, turns, etc.
    creates the pieces and handles the communication between pieces and between the game and UI
    """

    # Board tile type reference
    TILE_NOTHING = 0
    TILE_NORMAL = 1
    TILE_ROSETTA = 2
    TILE_GOAL = 3

    # Messages shown in UI
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

    # Turn stages
    STAGE_ROLLING = "rolling"
    STAGE_MOVING = "moving"

    # Signals
    dice_rolled = Signal()
    point_scored = Signal()
    message_updated = Signal()
    cant_move = Signal()
    roll_requested = Signal()
    new_game_started = Signal()
    game_won = Signal()

    def __init__(self):
        # set up the board
        self.board_scale = 1.0
        self.board = [2, 1, 2,
                      1, 1, 1,
                      1, 1, 1,
                      1, 2, 1,
                      0, 1, 0,
                      3, 1, 3,
                      2, 1, 2,
                      1, 1, 1]

        # players and the path (in tile indeces) taken on the board by each player's pieces
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
        self.create_event()

        self.turn_stage = None
        self.player_turn = 0
        self.rolled_value = None

    def __del__(self):
        """Delete all models, tokens and shaders when this object is deleted"""
        self.delete_all()

    def start_game(self):
        """Start a new game (and reset all values if a game is in progress)"""
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
        """
        Add a GameObject to the pieces dict, with the piece transform node as its key
        :type piece: GameOfUr.interface.GameObject
        """
        self.pieces[piece.transform] = piece

    def create_board(self):
        """Create all objects for the game board"""
        self.add_piece(Floor(self, position=(1.5, -1, 5)))
        for i, tile in enumerate(self.board):
            if tile in [1, 2]:
                self.add_piece(BoardTile(self, position=(i % 3, 0, i // 3), rosetta=tile == 2))

    def create_event(self):
        """Create the selection event/scriptjob that triggers the callback to interract with game pieces"""
        self.event_idx = om.MEventMessage.addEventCallback("SelectionChanged", self._selection_made)
        # self.event_idx = pm.scriptJob(conditionTrue=['SelectionChanged', self._selection_made], protected=True)

    def delete_event(self):
        """Delete the selection event/scriptjob as cleanup"""
        if self.event_idx is None:
            return
        om.MMessage.removeCallback(self.event_idx)

    def delete_all(self):
        """Delete all elements created in Maya (models, shaders, scriptjobs etc.)"""
        self.delete_event()
        for piece in self.pieces.values():
            piece.delete_model()
            piece.delete_materials()
        self.pieces = {}

    def _selection_made(self, *args):
        """
        Callback triggered when a Maya object is selected.
        If the selected object is one of our Interactable GameObjects, call its action function
        """
        if not self.running:
            # ignore the event if not running the game
            return
        # check if selected object is in our pieces list
        sel = pm.selected()
        if not sel:
            return
        if sel[0] not in self.pieces:
            return

        game_object = self.pieces[sel[0]]
        if isinstance(game_object, Interactable):
            # call trigger_action() not action() so before/after action signals get called
            game_object.trigger_action()
            pm.select(clear=True)

    def create_pieces(self):
        """Create all the interactable GameObjects such as tokens and dice"""
        pm.select(clear=True)

        # Connect classwide tokens signals
        Token.point_scored.connect(self.score_point)
        Token.move_successful.connect(self.piece_moved)
        Token.move_unsuccessful.connect(self.piece_blocked)
        Die.die_clicked.connect(self.roll_dice)

        # Create all player tokens for each player
        for player_i in range(self.players):
            for i in range(self.token_count):  # TODO: unify token_count and target_score
                new_token = Token(self,
                                  player=player_i,
                                  token_id=i,
                                  path=self.paths[player_i])
                self.add_piece(new_token)
                self.tokens.append(new_token)

        # Create all dice
        for i in range(4):
            new_die = Die(self,
                          position=((i // 2) * 4, -1, 10 + (i % 2) * 3),
                          position_randomness=(1, 0, 0.5))
            self.add_piece(new_die)
            self.dice.append(new_die)

    def roll_dice(self):
        """Roll all the dice if they are ready to be rolled"""
        if not self.running:
            # ignore if game is not running
            return
        if not self.turn_stage == self.STAGE_ROLLING:
            # ignore if a roll is not needed now
            return

        #roll all dice and get a list and a sum of their values
        rolled_values = [die.roll() for die in self.dice]
        self.rolled_value = sum(rolled_values)

        #switch to piece movement
        self.turn_stage = self.STAGE_MOVING
        self.dice_rolled.emit(rolled_values)

        #if none of the pieces can move, emit a signal
        if not self.can_move(self.rolled_value, self.player_turn):
            self.cant_move.emit()

    def can_move(self, distance, player):
        """
        Check if any of the specified player's tokens can move the specified distance
        :param distance: How many tiles ahead to check for each token
        :type distance: int
        :param player: player index (0  is player 1) of the player whose pieces we need to check
        :type player: int
        :return: If any piece can be moved
        :rtype: bool
        """
        for token in self.tokens:
            if not token.player == player:
                continue
            if token.can_move(distance):
                return True
        return False

    def start_turn(self, player):
        """
        Start the specified player's turn by requesting a dice roll.
        :param player: player index (0  is player 1)
        :type player: int
        """
        self.turn_stage = self.STAGE_ROLLING
        self.player_turn = player
        self.roll_requested.emit(player)

    def end_turn(self):
        """End the current turn, start the next player's turn"""
        self.start_turn((self.player_turn + 1) % self.players)

    def free_turn(self):
        """Give the current player a free turn by requesting a dice roll without ending turn."""
        self.turn_stage = self.STAGE_ROLLING
        self.roll_requested.emit(self.player_turn)

    def get_position_collision(self, tile_position):
        """
        Check if a token already exists on the specified tile.
        If one is present, return the token, otherwise return None
        :param tile_position: The board index of the tile to check. (This is not the same as path index)
        :type tile_position: int
        :return: token that occipies the specified tile (if any)
        :rtype: Union[None, GameOfUr.game_pieces.Token]
        """
        # don't check for collisions if the tile_location is not specified (not on the board)
        if tile_position is None:
            return None

        # check for collisions
        for token in self.tokens:
            if token.tile_location() == tile_position:
                return token
        return None

    def score_point(self, player):
        """
        Score a point for the specified player. Win the game if they reach the score limit
        :param player: player index (0  is player 1)
        :type player: int
        """
        self.player_scores[player] += 1
        self.point_scored.emit(player, self.player_scores[player])

        if self.player_scores[player] >= self.target_score:
            self.win_game(player)

    def win_game(self, player):
        """
        Win the game for the specified player. Stop the game from running further.
        :param player: player index (0  is player 1)
        :type player: int

        """
        self.message_updated.emit(["Player {} wins!".format(player + 1)])
        self.game_won.emit(player)
        self.running = False

    def piece_moved(self, messages):
        """
        Event called when a piece is successfully moved. Triggers the next turn if there is no free turn.
        :param messages: Message identifiers to show in the ui)
            These should match one of the keys in GameManager.message_text
        :type messages: List[str]
        """
        self.message_updated.emit([self.message_text[m] for m in messages])
        if Messages.FREE_TURN not in messages:
            self.end_turn()

    def piece_blocked(self, messages):
        """
        Event called when an attempted move is blocked.
        :param messages: Message identifiers to show in the ui)
            These should match one of the keys in GameManager.message_text
        :type messages: List[str]
        """
        self.message_updated.emit([self.message_text[m] for m in messages])


if __name__ == '__main__':
    ur_manager, ur_ui = run()
