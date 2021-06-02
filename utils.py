class Messages(object):
    """Helper class to store identifiers for different types of message"""
    INVALID_MOVE = "invalid-move"
    FREE_TURN = "free-turn"
    MOVE_BLOCKED = "move-blocked"
    FRIENDLY_TOKEN = "friendly-token"
    OPPONENT_TOKEN = "opponent-token"
    PROTECTED_OPPONENT = "protected-opponent"
    DISPLACED_OPPONENT = "displaced-opponent"
    TOO_FAR = "too-far"
    PATH_COMPLETE = "path-complete"
    MOVE_SUCCESSFULL = "move-successful"


class Signal(object):
    """Helper class to set up connections between the game and the UI, similar to Qt's slot/signal system"""
    def __init__(self):
        self._connections = []

    def connect(self, func):
        """
        Connect a function to this signal.
        If this signal's emit contains parameters, the function should match this signature
        :param func: the function object that will be called when the signal gets emitted
        :type func: callable
        """
        self._connections.append(func)

    def emit(self, *args, **kwargs):
        """
        Emit this signal to all of the connected callback functions with the specified parameters
        :param args: Arguments to pass to the connected callbacks
        :type args:
        :param kwargs: Keyword arguments to pass to the connected callbacks
        :type kwargs:
        """
        for func in self._connections:
            func(*args, **kwargs)
