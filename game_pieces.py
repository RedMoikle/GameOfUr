import os
import random

import pymel.core as pm

from utils import Messages, Signal

TEXTURES_DIR = os.path.join(__file__.rsplit("\\", 1)[0], "textures")


class GameObject(object):
    textures = {}

    def __init__(self, manager, position=(0, 0, 0), game_scale=1.0, *args, **kwargs):
        """Parent class for all game objects that have a mesh representation in Maya.
        This includes the tiles as well as the player tokens and dice"""
        self.manager = manager

        self.model_position = position
        self.origin_position = position
        self.game_scale = game_scale

        self.transform = None
        self.shape = None
        self.create_model()
        self.update_model_transform()
        self.manager.add_piece(self)

    def reset(self):
        self.model_position = self.origin_position
        self.update_model_transform()

    def __del__(self):
        self.delete_model()

    def create_model(self):
        """Override this method to create the transform for this object"""
        pass

    @classmethod
    def create_shader(cls, name, shader_type="blinn"):
        """Create and return a shader setup with the specified name. If one already exists, return that instead.

        Use this to avoid creating duplicate materials

        :return Tuple(new:Bool, material:ShadingNode, sg:ShaderGroup)"""
        new = False
        if name not in cls.textures:
            print("creating new shader {}".format(name))
            new = True
            material = pm.shadingNode(shader_type, name="Ur_{}_m".format(name), asShader=True)
            sg = pm.sets(name="Ur_{}_SG".format(name), empty=True, renderable=True, noSurfaceShader=True)
            material.outColor.connect(sg.surfaceShader)
            cls.textures[name] = (material, sg)

        return (new, cls.textures[name][0], cls.textures[name][1])

    def update_model_transform(self):
        xpos, ypos, zpos = (float(ax) * self.game_scale for ax in self.model_position)
        pm.move(xpos, ypos, zpos, self.transform)

    def delete_model(self):
        pm.delete(self.transform)
        self.transform = None
        self.shape = None

    def delete_textures(self):
        for name, tex in self.textures.items():
            try:
                pm.delete(tex)
            except pm.MayaNodeError as e:
                print("{} already deleted".format(name))
        self.textures = {}


class Floor(GameObject):
    textures = {}

    def create_model(self):
        self.transform, self.shape = pm.polyPlane(name="Ur_Table", height=30, width=30)


class BoardTile(GameObject):
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
        if self.rosetta:
            new, material, sg = self.create_shader("tile_rosetta")
            if new:
                material.setColor((0.75, 0.1, 0.05))
            pm.sets(sg, forceElement=self.transform)
            return
        new, material, sg = self.create_shader("tile_normal")
        if new:
            material.setColor((0.5, 0.25, 0.05))
        pm.sets(sg, forceElement=self.transform)


class Interactable(GameObject):
    def __init__(self, *args, **kwargs):
        self.before_action_event = Signal()
        self.after_action_event = Signal()
        super(Interactable, self).__init__(*args, **kwargs)

    def create_model(self):
        self.transform, self.shape = pm.polySphere(name="Ur_Interactable")

    def trigger_action(self):
        self.before_action_event.emit(triggering_object=self)
        self.action()
        self.after_action_event.emit(triggering_object=self)

    def action(self):
        """Override this method to create the selection behaviour for this object"""
        print("Piece {} selected".format(self.transform.name()))


class Die(Interactable):
    die_clicked = Signal()
    die_tex = pm.shadingNode("blinn", name="Ur_die", asShader=True)

    def __init__(self, *args, **kwargs):
        super(Die, self).__init__(*args, **kwargs)
        self.position_randomness = kwargs.pop("position_randomness", (1, 0, 0.5))
        self.roll()

    def create_model(self):
        self.transform, self.shape = pm.polyCone(subdivisionsAxis=3, radius=0.5, height=0.707)
        pm.move(self.transform.vtx[:], (0.25, 0.3535, 0), relative=True)
        self.transform.setRotationOrder(6, True)
        self.create_textures()

    def create_textures(self):
        new, material, sg = self.create_shader("die")
        if new:
            material.setColor((0.1, 0.1, 0.1))
            texture_file = pm.shadingNode("file", asTexture=True)
            print (texture_file)
            texture_file.fileTextureName.set(os.path.join(TEXTURES_DIR, "die.jpg"))
            pm.connectAttr(texture_file.outColor, material.color)
        pm.sets(sg, forceElement=self.transform)

    def action(self):
        self.die_clicked.emit()

    def roll(self):
        rolled_value = random.choice([0, 1])
        self.model_position = (ax + random.random() * ax_rand for ax, ax_rand in
                               zip(self.origin_position, self.position_randomness))
        print(self.model_position)
        self.update_model_transform()
        self.transform.rotate.set((0, random.random() * 360, 109.47 * rolled_value))
        return rolled_value


class Token(Interactable):
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

    @property
    def tile_location(self):
        if self.path is None:
            raise IndexError("Path undefined for this token. Please set a path with Token.path")
        if self.finished or not self.on_path:
            return None
        if self.path_position is -1:
            return None

        return self.path[self.path_position]

    def update_model_transform(self):
        tile = self.tile_location
        if tile is not None:
            print(self.path_position)
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
        new, material, sg = self.create_shader("player_{}".format(self.player + 1))
        if new:
            material.setColor((0.9 - self.player * 0.8, 0.9 - self.player * 0.8, 0.9 - self.player * 0.8))
        pm.sets(sg, forceElement=self.transform)

    def action(self):
        # ignore moves if not your turn to move a piece
        if not self.manager.player_turn == self.player:
            return
        if not self.manager.turn_stage == self.manager.STAGE_MOVING:
            return
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

        if target_tile is not None:
            print(
                "trying to move to {} - {} ({})".format(target_position, target_tile, self.manager.board[target_tile]))
        print(move_check)

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
        self.path_position = path_position
        self.update_model_transform()

    def displace(self):
        self.on_path = False
        self.path_position = -1
        self.update_model_transform()

    def end_path(self):
        self.finished = True
        self.on_path = False
        self.update_model_transform()
        self.point_scored.emit(self.player)

    def check_move(self, target_tile):
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
        if not distance:
            return False
        target_position = self.path_position + distance
        if target_position < len(self.path):
            target_tile = self.path[target_position]
            move_check, collision = self.check_move(target_tile)
            return Messages.MOVE_SUCCESSFULL in move_check
        return False
