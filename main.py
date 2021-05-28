"""
Game of Ur in Maya

This is a recreation of my very first Python project. While learning the language,
I created a playable board game inside of Maya, based on the ancient Mesopotamian "Royal Game of Ur".

This game uses scriptjobs placed on automatically generated Maya objects to interact with the game code.
"""

from game_pieces import *


def run():
    BoardTile()
    BoardTile(position=(1, 0, 0))
    BoardTile(position=(0, 0, 1))
    return None


if __name__ == '__main__':
    run()
