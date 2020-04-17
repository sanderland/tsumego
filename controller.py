import glob
import os
import re, json

from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform
from natsort import natsorted

from move import Move

APPNAME = "TenThousandTsumego"
STORE_FILE = "problem_status.json"


def get_store():
    if False:  # Not working for now :(
        try:
            from jnius import autoclass
            from android.permissions import request_permissions, Permission

            # request a permission from user
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            # path to sdcard (external storage that user have access to)
            Environment = autoclass("android.os.Environment")
            sdpath = Environment.getExternalStorageDirectory().getAbsolutePath()
            storage_dir = f"{sdpath}/{APPNAME}"
            if not os.path.exists(storage_dir):
                os.makedirs(storage_dir)
            print("made", storage_dir, os.path.exists(storage_dir))
            store = JsonStore(f"{storage_dir}/{STORE_FILE}")
            return store
        except Exception as e:
            print(f"Could not get storage permissions, exception {e}, using local storage")

    store = JsonStore(f"./{STORE_FILE}")
    return store


class Controls(BoxLayout):
    def __init__(self, **kwargs):
        super(Controls, self).__init__(**kwargs)
        self.game = {}
        self.show_solution = False
        self.boardsize = 19
        self.store = get_store()
        self.cats = [d for d in natsorted(glob.glob("problems/*"))]
        self.cat_ix = self.store_get("root").get("ix", 0)

    def store_get(self, key):

        try:
            return self.store.get(key)
        except KeyError:
            return {}

    def browse_cat(self, dir):
        self.cat_ix = (self.cat_ix + dir) % len(self.cats)
        self.store.put("root", ix=self.cat_ix)
        self.cat_lbl.text = self.cats[self.cat_ix].strip("/").split("/")[-1]
        self.dirs = [d for d in natsorted(glob.glob(self.cats[self.cat_ix] + "/*"))]
        self.dir_ix = self.store_get(f"cat_{self.cats[self.cat_ix]}").get("ix", 0)
        self.browse_dirs(0)

    def browse_dirs(self, dir):
        self.dir_ix = (self.dir_ix + dir) % len(self.dirs)
        self.store.put(f"cat_{self.cats[self.cat_ix]}", ix=self.dir_ix)
        self.dir_lbl.text = self.dirs[self.dir_ix].strip("/").split("/")[-1]
        self.files = [d for d in natsorted(glob.glob(self.dirs[self.dir_ix] + "/*.json"))]
        self.file_ix = self.store_get(f"dir_{self.dirs[self.dir_ix]}").get("ix", 0)
        self.browse_files(0)

    def browse_files(self, dir):
        self.file_ix = (self.file_ix + dir) % len(self.files)
        self.store.put(f"dir_{self.dirs[self.dir_ix]}", ix=self.file_ix)
        self.file_lbl.text = self.files[self.file_ix].split("/")[-1][:-5]  # strip .json
        self.load(self.files[self.file_ix])

    def set_done(self, state):
        self.store.put(f"done_{self.files[self.file_ix]}", state=state)

    def load(self, file):
        self.show_solution = False
        self.done.checkbox.active = self.store_get(f"done_{self.files[self.file_ix]}").get("state", False)
        try:
            with open(file, "r") as f:
                self.game = json.load(f)
        except Exception as e:
            self.hint.text = "Exception while reading problem file {file}: {e}"
            self.game = {}
        self.hint.text = self.game.get("C", "")
        self.parent.board.redraw()

    def solution(self):
        self.show_solution = True
        self.done.checkbox.active = True
        self.parent.board.redraw()

    def set_text_to_fit(self, widget, text):
        widget.text = text
        # for long names, reduce font size until it fits in its widget
        m = 0.35
        widget.font_size = widget.height * m
        widget.texture_update()
        while m >= 0.025 and widget.texture_size[1] > widget.height:
            m = m - 0.0125
            widget.font_size = widget.height * m
            widget.texture_update()
