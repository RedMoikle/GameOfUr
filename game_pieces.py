import random

import pymel.core as pm


class GameObject(object):
    textures = {}

    def __init__(self, manager, position=(0, 0, 0), game_scale=1.0, *args, **kwargs):
        """Parent class for all game objects that have a mesh representation in Maya.
        This includes the tiles as well as the player tokens and dice"""
        self.manager = manager

        self.model_position = position
        self.game_scale = game_scale

        self.transform = None
        self.shape = None
        self.create_model()
        self.update_position()
        self.manager.add_piece(self)

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
        else:
            print("shader {} already exists".format(name))
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


class BoardTile(GameObject):
    textures = {}

    def __init__(self, *args, **kwargs):
        self.rosetta = kwargs.pop("rosetta", False)
        super(BoardTile, self).__init__(*args, **kwargs)

    def create_model(self):
        self.transform, self.shape = pm.polyCube(name="Ur_Tile")

        # move shape but keep transform at 0,0,0
        # TODO: find a more elegant way of moving shape. Maybe movePolyVertex?
        # TODO: rosetta tiles
        rotate_pivot = self.transform.rotatePivot
        scale_pivot = self.transform.scalePivot
        pm.move(-0.5, 0.5, -0.5, rotate_pivot, scale_pivot, rotatePivotRelative=True)
        pm.move(0.5, -0.5, 0.5, self.transform)
        pm.makeIdentity(self.transform, apply=True, translate=True)
        print(self.transform)
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
    def create_model(self):
        self.transform, self.shape = pm.polySphere(name="Ur_Interactable")

    def action(self):
        """Override this method to create the selection behaviour for this object"""
        print("Piece {} selected".format(self.transform.name()))


class Die(Interactable):
    die_tex = pm.shadingNode("blinn", name="Ur_die", asShader=True)

    def create_model(self):
        self.transform, self.shape = pm.polyCone(subdivisionsAxis=3, height=1.44)
        self.create_textures()

    def create_textures(self):
        new, material, sg = self.create_shader("die")
        if new:
            material.setColor((0.1, 0.1, 0.1))
        pm.sets(sg, forceElement=self.transform)

    def action(self):
        self.manager.roll_dice()

    def roll(self):
        rolled_value = random.choice([0, 1])
        print(rolled_value)
        return rolled_value


class Token(Interactable):

    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop("player", None)
        self.token_id = kwargs.pop("token_id", None)
        self.path = kwargs.pop("path", None)
        self.path_position = kwargs.pop("path_position", -1)
        self.on_path = kwargs.pop("on_path", False)
        self.finished = kwargs.pop("finished", False)

        super(Token, self).__init__(*args, **kwargs)

    @property
    def tile_location(self):
        if self.path is None:
            raise IndexError("Path undefined for this token. Please set a path with Token.path")
        if self.finished or not self.on_path:
            return None
        if self.path_position is -1:
            return None

        return self.path[self.path_position]
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
        # check turn stage/player turn
        # get rolled value
        # check target tile
        # move
        # free turn or end turn
        pass

    def check_target_tile(self):
        rolled_value = self.manager.rolled_value()
