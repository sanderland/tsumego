from kivy.core.text import Label as CoreLabel
from kivy.graphics import *
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stencilview import StencilView


class StencilBox(BoxLayout, StencilView):
    pass


def draw_text(pos, text, **kw):
    label = CoreLabel(text=text, bold=True, **kw)
    label.refresh()
    Rectangle(
        texture=label.texture, pos=(pos[0] - label.texture.size[0] / 2, pos[1] - label.texture.size[1] / 2), size=label.texture.size,
    )


def draw_circle(pos, r, col):
    Color(*col)
    Ellipse(pos=(pos[0] - r, pos[1] - r), size=(2 * r, 2 * r))


class CheckBoxHint(BoxLayout):
    __events__ = ("on_active",)

    @property
    def active(self):
        return self.checkbox.active

    def on_active(self, *args):
        pass
