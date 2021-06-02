import pymel.core as pm

COMMAND = """
import GameOfUr
import GameOfUr.main as MGS_ur

MGS_ur_game, MGS_ur_ui = MGS_ur.run()
"""


def mgs_ur_show_launcher():
    """
    Create a window that contains a shelf button that the user can either click to launch the game,
    or drag to a shelf in Maya to make a permanent shortcut to the game.
    """
    window = pm.window(title='Launch Game of Ur')

    pm.columnLayout()
    pm.text("Click to launch the game,\nor drag (with the middle mouse)\nand drop the button to the shelf.")
    shelf = pm.shelfLayout(height=64, width=64)

    pm.shelfButton(annotation="Launch the Royal Game of Ur", image1="bulge.svg", imageOverlayLabel="Ur", command=COMMAND)

    pm.showWindow(window)


mgs_ur_show_launcher()
