import pymel.core as pm


class GameObject(object):
    def __init__(self, position=(0, 0, 0), game_scale=1.0):
        """Parent class for all game objects that have a mesh representation in Maya.
        This includes the tiles as well as the player tokens and dice"""
        self.position = position
        self.game_scale = game_scale

        self.transform = None
        self.shape = None
        self.create_model()
        self.update_position()

    def create_model(self):
        """Override this method to create the transform for this object"""
        pass

    def update_position(self):
        xpos, ypos, zpos = (ax * self.game_scale for ax in self.position)
        pm.move(xpos, ypos, zpos, self.transform)


class BoardTile(GameObject):
    def create_model(self):
        self.transform, self.shape = pm.polyCube(name="Ur_Tile")

        #move shape but keep transform at 0,0,0
        #TODO: find a more elegant way of moving shape. Maybe movePolyVertex?
        rotate_pivot = self.transform.rotatePivot
        scale_pivot = self.transform.scalePivot
        pm.move(-0.5, 0.5, -0.5, rotate_pivot, scale_pivot, rotatePivotRelative=True)
        pm.move(0.5, -0.5, 0.5, self.transform)
        pm.makeIdentity(self.transform, apply=True, translate=True)
