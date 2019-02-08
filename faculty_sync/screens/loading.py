SEQUENCE = ["|", "/", "-", "\\", "|", "/", "-", "\\"]


class LoadingIndicator(object):
    def __init__(self):
        self._index = 0

    def current(self):
        return SEQUENCE[self._index]

    def next(self):
        self._index = (self._index + 1) % len(SEQUENCE)
        return self.current()
