import math

from kivy.app import App
from kivy.graphics import *
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior

from controller import Controls
from kivyutils import *
from move import Move

COLORS = [(0.05, 0.05, 0.05), (0.95, 0.95, 0.95)]
OUTLINE = [(0.3, 0.3, 0.3, 0.5), (0.7, 0.7, 0.7, 0.5)]


class Badukpan(StencilView):
    def __init__(self, **kwargs):
        super(Badukpan, self).__init__(**kwargs)

    # drawing functions
    def on_size(self, *args):
        self.redraw()

    def on_touch_down(self, touch):
        self.controls.hint.text = "Ten Thousand Tsumego does not support 'clicking through' problems. Read out the problem in your head, and move on when you are done."

    def draw_stone(self, x, y, col, stone_size, outline_col=None, innercol=None):
        draw_circle((self.gridpos_x[x], self.gridpos_y[y]), stone_size, col)
        if outline_col:
            Color(*outline_col)
            Line(circle=(self.gridpos_x[x], self.gridpos_y[y], stone_size), width=0.03 * stone_size)
        if innercol:
            Color(*innercol)
            Line(circle=(self.gridpos_x[x], self.gridpos_y[y], stone_size * 0.4 / 0.85), width=0.1 * stone_size)

    def redraw(self, force_whole_board=False):
        self.canvas.clear()
        with self.canvas:
            # board
            sz = self.height
            Color(0.85, 0.68, 0.40)
            board = Rectangle(pos=self.pos, size=(sz, sz))
            boardsize = int(self.controls.game.get("SZ", "19"))

            placements = []
            solution = []
            solution_comment = ""
            for pl, gtpcol in enumerate("BW"):
                for stone in self.controls.game.get("A" + gtpcol, []):
                    placements.append(Move(player=pl, sgfcoords=stone, boardsize=boardsize))
            for i, (bw, sgfc, comment, warning) in enumerate(self.controls.game.get("SOL", [])):
                if warning and not solution_comment:
                    solution_comment = warning + "\n"
                mv = Move(player=0 if bw == "B" else 1, sgfcoords=sgfc, boardsize=boardsize)
                solution_comment += f"Solution {i+1}: {mv.gtp()}"
                if comment:
                    solution_comment += ": " + comment
                solution_comment += f"\n"
                solution.append(mv)
            if not placements:
                xs = [10]
                ys = [10]
            else:
                xs, ys = zip(*[m.coords for m in placements + solution])

            if min(xs) < (boardsize - 1) - max(xs):
                xtype = 0
                nc_x = max(xs) + 1
            else:
                xtype = 1
                nc_x = boardsize - min(xs) + 1
            if min(ys) < (boardsize - 1) - max(ys):
                ytype = 0
                nc_y = max(ys) + 1
            else:
                ytype = 1
                nc_y = boardsize - min(ys) + 1
            num_cells = max(nc_x, nc_y)
            if num_cells > boardsize - 3:
                num_cells = boardsize or force_whole_board

            xbounds = [0, num_cells - 1] if xtype == 0 else [boardsize - num_cells, boardsize - 1]
            ybounds = [0, num_cells - 1] if ytype == 0 else [boardsize - num_cells, boardsize - 1]
            # grid lines
            margin = 1.5
            self.grid_size = board.size[0] / (num_cells - 1 + 2 * margin)
            halfmargin = margin / 2 * self.grid_size
            self.stone_size = self.grid_size * 0.475
            self.gridpos_x = [
                self.pos[0] + math.floor((margin + (i - xbounds[0])) * self.grid_size + 0.5) for i in range(boardsize)
            ]
            self.gridpos_y = [
                self.pos[1] + math.floor((margin + (i - ybounds[0])) * self.grid_size + 0.5) for i in range(boardsize)
            ]

            line_color = (0, 0, 0)
            Color(*line_color)

            for i in range(boardsize):
                Line(points=[(self.gridpos_x[i], self.gridpos_y[0]), (self.gridpos_x[i], self.gridpos_y[-1])])
                Line(points=[(self.gridpos_x[0], self.gridpos_y[i]), (self.gridpos_x[-1], self.gridpos_y[i])])

            # star points
            star_point_pos = 3 if boardsize <= 11 else 4
            starpt_size = self.grid_size * 0.1
            for x in [star_point_pos - 1, boardsize - star_point_pos, int(boardsize / 2)]:
                for y in [star_point_pos - 1, boardsize - star_point_pos, int(boardsize / 2)]:
                    draw_circle((self.gridpos_x[x], self.gridpos_y[y]), starpt_size, line_color)

            # coordinates
            Color(0.25, 0.25, 0.25)
            for i in range(boardsize):
                draw_text(
                    pos=(self.gridpos_x[i], self.gridpos_y[0] - halfmargin),
                    text=Move.GTP_COORD[i],
                    font_size=self.grid_size / 1.5,
                )
                draw_text(
                    pos=(self.gridpos_x[i], self.gridpos_y[-1] + halfmargin),
                    text=Move.GTP_COORD[i],
                    font_size=self.grid_size / 1.5,
                )
                draw_text(
                    pos=(self.gridpos_x[0] - halfmargin, self.gridpos_y[i]),
                    text=str(i + 1),
                    font_size=self.grid_size / 1.5,
                )
                draw_text(
                    pos=(self.gridpos_x[-1] + halfmargin, self.gridpos_y[i]),
                    text=str(i + 1),
                    font_size=self.grid_size / 1.5,
                )

            # stones etc
            for move in placements:
                self.draw_stone(*move.coords, COLORS[move.player], self.stone_size, OUTLINE[move.player])

            if self.controls.show_solution:
                for move in solution:
                    self.draw_stone(
                        *move.coords,
                        COLORS[move.player],
                        self.stone_size,
                        OUTLINE[move.player],
                        COLORS[1 - move.player],
                    )
                self.controls.hint.text = solution_comment


class TsumegoGUI(BoxLayout):
    def on_size(self, *args):
        pass
        # self.controls.set_text_to_fit(self.controls.hint, self.controls.hint.text)


class TsumegoApp(App):
    def build(self):
        self.icon = "./icon.png"
        self.gui = TsumegoGUI()
        return self.gui

    def on_start(self):
        self.gui.controls.browse_cat(0)


if __name__ == "__main__":
    TsumegoApp().run()
