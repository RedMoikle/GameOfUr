class Messages(object):
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
    def __init__(self):
        self._connections = []

    def connect(self, func):
        self._connections.append(func)

    def emit(self, *args, **kwargs):
        for func in self._connections:
            func(*args, **kwargs)
