"""This module is not intended to be imported. It is instead supposed to be run with maya's __main__ interpreter.
This file is merely for conveneience - to either copy to a shelf button, or to be run with PyCharm's MayaCharm plugin.
As such it will likely show errors in the IDE which should be ignored.

Note: could also build this into the __init__ module of the package, so the game would start upon importing it.
"""


try:
    # This should not be included in a production environment just for quick testing of changes without restarting Maya
    reload(GameOfUr.game_pieces)
    reload(GameOfUr.interface)
    reload(ur)


except NameError as e:
    print("first load")
    print(e)
import GameOfUr
import GameOfUr.main as ur

ur_game, ur_ui = ur.run()

