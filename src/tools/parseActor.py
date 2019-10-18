#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import zipfile
import argparse
import sys
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
import entities


class R20Converter(object):
    def __init__(self, path):
        self.path = "."
        self.campaign = {"handouts" : [], "characters": []}
        self.packs = {}
        self.fvtt_path = None
        self.parse(path)
 
    def getArgument(self, name, default=None):
        if name in ["json", "use_original_image_urls", "export_as_module"]:
            return True
        return default

    def hasSystemPacks(self):
        return False

    def parse(self, path):
        self.journal = entities.EmptyDB(self, "journal")
        self.items = entities.Items(self)
        self.actors = entities.EmptyDB(self, "actors")
        entities.actors.DISPLAY_ATTRIBUTES = True
        with open(path, "r", encoding='utf-8') as f:
            character = json.load(f)
            if "oldId" in character:
                character["id"] = character["oldId"]
                character["attributes"] = character["attribs"]
            entities.Actor(self.actors, character, 0)

if __name__ == "__main__":
    R20Converter(sys.argv[1])
