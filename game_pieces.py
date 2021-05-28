import random

import pymel.core as pm


class GameObject(object):
    def __init__(self, manager, position=(0, 0, 0), game_scale=1.0):
        """Parent class for all game objects that have a mesh representation in Maya.
        This includes the tiles as well as the player tokens and dice"""
        self.manager = manager

        self.position = position
        self.game_scale = game_scale

        self.transform = None
        self.shape = None
        self.create_model()
        self.update_position()
        self.manager.add_piece(self)

    def create_model(self):
        """Override this method to create the transform for this object"""
        pass

    def update_position(self):
        xpos, ypos, zpos = (ax * self.game_scale for ax in self.position)
        pm.move(xpos, ypos, zpos, self.transform)


class BoardTile(GameObject):
    def create_model(self):
        self.transform, self.shape = pm.polyCube(name="Ur_Tile")

        # move shape but keep transform at 0,0,0
        # TODO: find a more elegant way of moving shape. Maybe movePolyVertex?
        rotate_pivot = self.transform.rotatePivot
        scale_pivot = self.transform.scalePivot
        pm.move(-0.5, 0.5, -0.5, rotate_pivot, scale_pivot, rotatePivotRelative=True)
        pm.move(0.5, -0.5, 0.5, self.transform)
        pm.makeIdentity(self.transform, apply=True, translate=True)


class Interactable(GameObject):
    def create_model(self):
        self.transform, self.shape = pm.polySphere(name="Ur_Interactable")

    def action(self):
        """Override this method to create the selection behaviour for this object"""
        print("Piece {} selected".format(self.transform.name()))


class Die(Interactable):
    def create_model(self):
        self.transform, self.shape = pm.polyCone(subdivisionsAxis=3, height=1.44)

    def action(self):
        self.manager.roll_dice()

    def roll(self):
        rolled_value = random.choice([0, 1])
        print(rolled_value)
        return rolled_value
