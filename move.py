class Move:
    GTP_COORD = "ABCDEFGHJKLMNOPQRSTUVWYXYZ"
    PLAYERS = "BW"
    SGF_COORD = [chr(i) for i in range(97, 123)]

    def __init__(self, player, coords=None, gtpcoords=None, sgfcoords=None, boardsize=19):
        self.player = player
        self.coords = coords or (gtpcoords and self.gtp2ix(gtpcoords)) or self.sgf2ix(sgfcoords, boardsize)

    def __repr__(self):
        return f"{Move.PLAYERS[self.player]}{self.gtp()}"

    def gtp2ix(self, gtpmove):
        if "pass" in gtpmove:
            return (None, None)
        return Move.GTP_COORD.index(gtpmove[0]), int(gtpmove[1:]) - 1

    def sgf2ix(self, sgfmove, board_size):
        if sgfmove == "":
            return (None, None)
        return Move.SGF_COORD.index(sgfmove[0]), board_size - Move.SGF_COORD.index(sgfmove[1]) - 1

    def gtp(self):
        if self.coords[0] is None:
            return "pass"
        return Move.GTP_COORD[self.coords[0]] + str(self.coords[1] + 1)

    def sgfcoords(self, boardsize):
        return f"{Move.SGF_COORD[self.coords[0]]}{Move.SGF_COORD[boardsize - self.coords[1] - 1]}"

    def sgf(self, boardsize):
        if self.coords[0] is None:
            return f"{Move.PLAYERS[self.player]}[]"
        else:
            return f"{Move.PLAYERS[self.player]}[{self.sgfcoords(boardsize)}]"
