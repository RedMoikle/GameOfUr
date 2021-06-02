import os
import random

import pymel.core as pm

from utils import Messages, Signal

TEXTURES_DIR = os.path.join(__file__.rsplit("\\", 1)[0], "textures")


class GameObject(object):
    """
    Parent class for all game objects that have a mesh representation in Maya.
    This includes the tiles as well as the player tokens and dice
    :param manager: The game manager for this object.
    :type manager: GameOfUr.main.GameManager
    :param position: The origin position for the model of this object (scaled up by game scale)
    :type position: Tuple(float, float, float)
    :param game_scale: A multiplier to scale up all transformations on the model
    :type game_scale: float
    """
    textures = {}

    def __init__(self, manager, position=(0, 0, 0), game_scale=1.0, *args, **kwargs):
        self.manager = manager
        self.model_position = position
        self.origin_position = position
        self.game_scale = game_scale

        self.transform = None
        self.shape = None
        self.create_model()
        self.update_model_transform()

    def reset(self):
        """
        Reset the model to its original position.
        Override this if anything besides the position needs to be reset
        """
        self.model_position = self.origin_position
        self.update_model_transform()

    def __del__(self):
        """Delete the model if this GameObject is deleted"""
        self.delete_model()

    def create_model(self):
        """Override this method to create the transform for this object"""
        pass

    @classmethod
    def create_material(cls, name, shader_type="blinn"):
        """
        Create and return a shader setup with the specified name. If one already exists, return that instead.
        Use this to avoid creating duplicate materials
        :param name: Name of this material
        :type name: str
        :param shader_type: Maya shader type of this material (default: "blinn")
        :type shader_type: str
        :return: grouped data about the created material (new, material, shadergroup)
            new: if this was a new material created in this command, or if it already existed
            material: the maya material node
            shadergroup: the maya shadergroup node
        :rtype: Tuple[bool, pm.ShadingNode, pm.ShaderGroup]
        """
        new = False
        if name not in cls.textures:
            print("creating new shader {}".format(name))
            new = True
            material = pm.shadingNode(shader_type, name="Ur_{}_m".format(name), asShader=True)
            sg = pm.sets(name="Ur_{}_SG".format(name), empty=True, renderable=True, noSurfaceShader=True)
            material.outColor.connect(sg.surfaceShader)
            cls.textures[name] = (material, sg)

        return new, cls.textures[name][0], cls.textures[name][1]

    @classmethod
    def delete_materials(cls):
        """
        Delete all materials created for this class.
        This will only need to be run once per object class, and will be skipped if the materials were already deleted
        """
        if not cls.textures:
            return
        for name, tex in cls.textures.items():
            try:
                pm.delete(tex)
            except pm.MayaNodeError as e:
                print("{} already deleted".format(name))
        cls.textures = {}

    def update_model_transform(self):
        """Update the position of the model in maya, and scale up the transformation by the game_scale"""
        xpos, ypos, zpos = (float(ax) * self.game_scale for ax in self.model_position)
        pm.move(xpos, ypos, zpos, self.transform)

    def delete_model(self):
        """Delete the model for this GameObject in Maya"""
        pm.delete(self.transform)
        self.transform = None
        self.shape = None


class Floor(GameObject):
    """
    The floor/table for the game.
    Purely decorative
    """
    textures = {}

    def create_model(self):
        self.transform, self.shape = pm.polyPlane(name="Ur_Table", height=30, width=30)


class BoardTile(GameObject):
    """
    A single square tile in the game board.
    These can also be rosetta tiles if the rosetta keyword is set to True
    :key rosetta: Is this tile a rosetta (free turn) tile?
    :type rosetta: bool
    """
    textures = {}

    def __init__(self, *args, **kwargs):
        self.rosetta = kwargs.pop("rosetta", False)
        super(BoardTile, self).__init__(*args, **kwargs)

    def create_model(self):
        self.transform, self.shape = pm.polyCube(name="Ur_Tile")

        # move shape but keep transform at 0,0,0
        pm.move(self.transform.vtx[:], (0.5, -0.5, 0.5), relative=True)
        self.create_textures()

    def create_textures(self):
        # assign either a rosetta texture, or a normal tile texture
        if self.rosetta:
            new, material, sg = self.create_material("tile_rosetta")
            if new:
                material.setColor((0.75, 0.1, 0.05))
            pm.sets(sg, forceElement=self.transform)
            return
        new, material, sg = self.create_material("tile_normal")
        if new:
            material.setColor((0.5, 0.25, 0.05))
        pm.sets(sg, forceElement=self.transform)


class Interactable(GameObject):
    """
    Parent class for all interactable game objects.
    These have some action that should be performed when its maya object is selected.
    """

    def __init__(self, *args, **kwargs):
        self.before_action_event = Signal()
        self.after_action_event = Signal()
        super(Interactable, self).__init__(*args, **kwargs)

    def create_model(self):
        # placeholder model, since we need a selectable transform node in Maya
        self.transform, self.shape = pm.polySphere(name="Ur_Interactable")

    def trigger_action(self):
        """
        Callback to trigger the action function.
            The action function should be overrwitten by classes inheriting this.

            The trigger_action function should be passed as a callback function into
                a scriptjob or an openMaya event callback

        This also emits signals for before and after the action, if they are neeeded.
        """
        self.before_action_event.emit(triggering_object=self)
        self.action()
        self.after_action_event.emit(triggering_object=self)

    def action(self):
        """Override this method to create the selection behaviour for this object"""
        print("Piece {} selected".format(self.transform.name()))


class Die(Interactable):
    """
    Die object which can be rolled for random numbers.

    Game of Ur uses tetrahedron dice (4 sided) with half of the corners painted white.
    when all the dice are rolled, count the number of white corners that face up and move a piece by that many places.

    Effectively it is the same as four coin flips. Chances of rolling each value are below (assuming 4 dice are rolled)
        0 or 4: 1/16
        1 or 3: 1/ 8
        2     : 1/ 4

    :key position_randomness: Amount of randomness to add to the placement of this die in each axis when it is rolled
    :type position_randomness: Tuple(int, int, int)
    """
    die_clicked = Signal()
    die_tex = pm.shadingNode("blinn", name="Ur_die", asShader=True)

    def __init__(self, *args, **kwargs):
        super(Die, self).__init__(*args, **kwargs)
        self.position_randomness = kwargs.pop("position_randomness", (1, 0, 0.5))
        # roll the dice at the start without keeping the value, just to randomise the position.
        self.roll()

    def create_model(self):
        # cone with 3 axial subdivisions
        self.transform, self.shape = pm.polyCone(subdivisionsAxis=3, radius=0.5, height=0.707)

        # move shape so the rotation origin is on a bottom edge
        # (this means we can rotate around the z axis to show either a dot or no dot)
        pm.move(self.transform.vtx[:], (0.25, 0.3535, 0), relative=True)

        # zyx rotation order
        self.transform.setRotationOrder(6, True)
        self.create_textures()

    def create_textures(self):
        new, material, sg = self.create_material("die")
        if new:
            material.setColor((0.1, 0.1, 0.1))
            texture_file = pm.shadingNode("file", asTexture=True)
            texture_file.fileTextureName.set(os.path.join(TEXTURES_DIR, "die.jpg"))
            pm.connectAttr(texture_file.outColor, material.color)
        pm.sets(sg, forceElement=self.transform)

    def action(self):
        # don't roll individual dice, call the manager if any are clicked, then roll all of them together
        self.die_clicked.emit()

    def roll(self):
        """
        Roll this die and return its result.
        Also update the model with randomness to make it looked like it was physically rolled
        :return: rolled value (1 or 0)
        :rtype: int
        """
        rolled_value = random.choice([0, 1])
        self.model_position = (ax + random.random() * ax_rand for ax, ax_rand in
                               zip(self.origin_position, self.position_randomness))
        self.update_model_transform()
        self.transform.rotate.set((0, random.random() * 360, 109.47 * rolled_value))
        return rolled_value


class Token(Interactable):
    """
    Player token. These move along a particular path on the board, which is different for each player.

    The standard path looks like this:

    # # # #     # #
    > > > > > > > v
    ^ < < <S   E< <

    (flipped  vertically for the other player)

    A token must land exactly one space after the final tile to complete the path.
    (this end soace should also be included in the path list for the token)

    :key player: Player index (0 is player 1)
    :type player: int
    :key token_id: The ID of this token. Used to line them up at the side of the board
    :type token_id: int
    :key path: The path that this token should take on the board (including end). A list of board tile indeces
    :type path: List[int]
    :key on_path: If this token is on the path:
    :type on_path: bool
    :key finished: If this token has reached the end goal
    :type finished: bool
    """
    point_scored = Signal()
    move_successful = Signal()
    move_unsuccessful = Signal()

    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop("player", None)
        self.token_id = kwargs.pop("token_id", None)
        self.path = kwargs.pop("path", None)
        self.path_position = kwargs.pop("path_position", -1)
        self.on_path = kwargs.pop("on_path", False)
        self.finished = kwargs.pop("finished", False)

        super(Token, self).__init__(*args, **kwargs)

    def reset(self):
        self.path_position = -1
        self.on_path = False
        self.finished = False
        super(Token, self).reset()

    def tile_location(self, offset=0):
        """
        Get the tile index of this piece (or the index of its position with an offset of moves)
        :param offset: number of tiles along the path to check (Default 0 - check the tile the piece is on now)
        :type offset: int
        :return: the tile index of the specified path step
        :rtype: int
        """
        target = self.path_position + offset
        if self.path is None:
            raise IndexError("Path undefined for this token. Please set a path with Token.path")
        if self.finished or not self.on_path:
            return None
        if target == -1:
            return None
        return self.path[target]

    def update_model_transform(self):
        tile = self.tile_location()
        if tile is not None:
            self.model_position = (tile % 3 + 0.5, 0, tile // 3 + 0.5)
        else:
            xpos = (self.token_id % 4 + 2.5) * (2 * self.player - 1) + 1.5
            zpos = self.token_id // 4 + self.finished * 4
            self.model_position = (xpos + random.random() * 0.2, -1, zpos + random.random() * 0.2)
        super(Token, self).update_model_transform()

    def create_model(self):
        self.transform, self.shape = pm.polySphere(radius=0.2)
        pm.scale(self.transform, [1, 0.5, 1])
        pm.move(self.transform, [0, 0.1, 0])
        pm.makeIdentity(self.transform, apply=True, translate=True)
        self.create_textures()

    def create_textures(self):
        new, material, sg = self.create_material("player_{}".format(self.player + 1))
        if new:
            material.setColor((0.9 - self.player * 0.8, 0.9 - self.player * 0.8, 0.9 - self.player * 0.8))
        pm.sets(sg, forceElement=self.transform)

    def action(self):
        # TODO: tidy up Token action function
        # ignore moves if not your turn to move a piece
        if not self.manager.player_turn == self.player:
            return
        if not self.manager.turn_stage == self.manager.STAGE_MOVING:
            return
        # TODO: replace repeated path[posiotion] checks with new tile_location offset
        rolled_value = self.manager.rolled_value
        target_position = self.path_position + rolled_value
        if rolled_value == 0:
            target_tile = None
            move_check = [Messages.MOVE_BLOCKED, Messages.INVALID_MOVE]
            collision = None
        elif target_position < len(self.path):
            target_tile = self.path[target_position]
            move_check, collision = self.check_move(target_tile)

        else:
            target_tile = None
            move_check = [Messages.MOVE_BLOCKED, Messages.TOO_FAR]
            collision = None

        if Messages.MOVE_BLOCKED in move_check:
            self.move_unsuccessful.emit(move_check)
            return

        if Messages.DISPLACED_OPPONENT in move_check:
            collision.displace()

        if Messages.MOVE_SUCCESSFULL in move_check:
            self.on_path = True
            self.move(target_position)
        if Messages.PATH_COMPLETE in move_check:
            self.end_path()
        if Messages.FREE_TURN not in move_check:
            pass
            # self.manager.end_turn()
        else:
            self.manager.free_turn()
        self.move_successful.emit(move_check)

    def move(self, path_position):
        """
        Move the token to the specified position along its path.
        :param path_position: position on the piece's path
        :type path_position: int

        TODO: is the move function redundant?
        """
        self.path_position = path_position
        self.update_model_transform()

    def displace(self):
        """Displace this token and send it back home"""
        self.on_path = False
        self.path_position = -1
        self.update_model_transform()

    def end_path(self):
        """Complete this token's path and add it to the complete pile, then give a point."""
        self.finished = True
        self.on_path = False
        self.update_model_transform()
        self.point_scored.emit(self.player)

    def check_move(self, target_tile):
        """
        Check if a move to the specified tile can be made. Returns a list of information to describe that move.
        This includes information such as if friendly tokens are blocking the move, if the move would be a free turn,
        if the move would complete the path etc.

        :param target_tile: The tile index to check
        :type target_tile: int
        :return: A list of identifiers that explain various information about the potential move.
            Possible identifiers are found in utils.Messages
        :rtype: List[str]
        """
        messages = []
        collision = self.manager.get_position_collision(target_tile)
        tile_type = self.manager.board[target_tile]
        # token blocking/displacement
        if collision is not None:
            if collision.player == self.player:
                messages.append(Messages.MOVE_BLOCKED)
                messages.append(Messages.FRIENDLY_TOKEN)
            else:
                messages.append(Messages.OPPONENT_TOKEN)
                if tile_type == self.manager.TILE_ROSETTA:
                    messages.append(Messages.MOVE_BLOCKED)
                    messages.append(Messages.PROTECTED_OPPONENT)
                else:
                    messages.append(Messages.MOVE_SUCCESSFULL)
                    messages.append(Messages.DISPLACED_OPPONENT)
        else:
            if tile_type == self.manager.TILE_ROSETTA:
                messages.append(Messages.MOVE_SUCCESSFULL)
                messages.append(Messages.FREE_TURN)
            elif tile_type == self.manager.TILE_GOAL:
                messages.append(Messages.MOVE_SUCCESSFULL)
                messages.append(Messages.PATH_COMPLETE)
            else:
                messages.append(Messages.MOVE_SUCCESSFULL)

        return messages, collision

    def can_move(self, distance):
        """
        Check if this piece can be moved the specified distance along its path
        :param distance:
        :type distance:
        :return: if the move is possible
        :rtype: bool
        """
        if not distance:
            return False
        target_position = self.path_position + distance
        if target_position < len(self.path):
            target_tile = self.path[target_position]
            move_check, collision = self.check_move(target_tile)
            return Messages.MOVE_SUCCESSFULL in move_check
        return False
