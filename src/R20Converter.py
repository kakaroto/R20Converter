#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import zipfile
import argparse
import sys
import os
import platform
from slugify import slugify
from collections import OrderedDict

import utils
from version import version
from world import World
from module import Module
from entities import DatabaseFile, EmptyDB, \
        Actors, Items, Combat, \
        Folders, Journal, Playlists, \
        Scenes, SettingsDB, Users, \
        Tables, RollableTables, Decks, \
        Macros, ChatLog


class R20Converter(object):
    def __init__(self, args, logger=None):
        self._logger = utils if logger is None else logger
        self.args = args
        self.path = args.path
        self.name = os.path.basename(os.path.dirname(os.path.join(self.path, ".")))
        if args.json:
            with open(args.zip_file, "r", encoding='utf-8') as f:
                self.campaign = json.load(f, object_pairs_hook=OrderedDict)
            self.campaign["jukeboxfolder"] = ""
        else:
            self.zip = zipfile.ZipFile(args.zip_file, "r")
            self.campaign = json.load(self.getZipFile("campaign.json"), object_pairs_hook=OrderedDict)
        self.packs = {}
        self.system_templates = {}
        self.game_system = self.getArgument("game_system", "dnd5e")
        if (self.game_system == ""):
            self.game_system = "dnd5e"
        self.fvtt_path = self.getArgument("fvtt_data_path", None)
        if self.fvtt_path is None:
            potential_path = os.path.abspath(os.path.join(self.path, "..", "..", ".."))
            if os.path.exists(os.path.join(potential_path, "Data", "systems", self.game_system, "system.json")):
                self.fvtt_path = potential_path
            else:
                self.fvtt_path = utils.getFVTTDataPath()
        if self.game_system == "dnd5e":
            if self.fvtt_path is not None:
                self.loadDnD5ePacks()
            else:
                self.logWarning("Warning: Could not find the path to the FVTT Data directory, either specify a destination directory in the Data/worlds/ path\n"
                  "or use the --fvtt-data-path argument to specify the path to the Data directory.\n"
                  "If you do not, then Item and Spell Compendium links in journal entries will not be replaced with links to SRD data from the D&D 5e packs.")
        else:
            try:
                loaded_templates = False
                if self.fvtt_path is not None:
                    self.loadSystemTemplate()
                    loaded_templates = True
            except:
                pass
            if not loaded_templates:
                self.logWarning("Warning: Could not find the path to the FVTT Data directory or the system you specified is not installed locally.\n"
                  "Your character sheets may fail to open.")

    def getZipFile(self, filename):
        # On japanese systems, path separator is actually '¥' which won't work
        # when opening the files in the zip.
        return self.zip.open(filename.replace(os.path.sep, "/"))

    def getArgument(self, name, default=None):
        return getattr(self.args, name, default)

    def loadDnD5ePacks(self):
        self.packs = {}
        for file in ["items", "spells", "classfeatures", "classes", "monsters"]:
            db  = DatabaseFile(self, "%s.db" % file)
            path = os.path.join(self.fvtt_path, "Data", "systems", "dnd5e", "packs", "%s.db" % file)
            try:
                db.load(path)
                self.packs[file] = db
            except:
                pass
    def loadSystemTemplate(self):
        path = os.path.join(self.fvtt_path, "Data", "systems", self.game_system, "template.json")
        with open(path, "r", encoding='utf-8') as f:
            template = json.load(f)
        self.system_templates = {}
        for actor_type in template["Actor"]["types"]:
            actor_template = template["Actor"][actor_type]
            actor_templates = actor_template.get("templates", [])
            del actor_template["templates"]
            for sub_template in actor_templates:
                actor_template.update(template["Actor"]["templates"].get(sub_template, {}))
            self.system_templates[actor_type] = actor_template
    def hasSystemPacks(self):
        return len(self.packs) > 0

    def convert(self):
        self.logInfo("*** Converting Campaign '%s' ***" % self.campaign["campaign_title"])
        os.makedirs(self.path)
        if self.getArgument("export_as_module", False):
            os.makedirs(os.path.join(self.path, "packs"))

            if self.getArgument("disable_module_journal", False):
                self.journal = EmptyDB(self, "journal")
            else:
                self.journal = Journal(self)

            # actors can modify the items list, so create the correct class
            # and overwrite it with an emptyDB later
            self.items = Items(self)

            if self.getArgument("disable_module_actors", False):
                self.actors = EmptyDB(self, "actors")
            else:
                self.actors = Actors(self)

            if self.getArgument("disable_module_items", False):
                self.items = EmptyDB(self, "items")
            else:
                self.items.createEntities()

            if self.getArgument("disable_module_scenes", False):
                self.scenes = EmptyDB(self, "scenes")
            else:
                self.scenes = Scenes(self)

            if self.getArgument("disable_module_playlists", False):
                self.playlists = EmptyDB(self, "playlists")
            else:
                self.playlists = Playlists(self)

            if self.getArgument("disable_module_tables", False):
                self.tables = EmptyDB(self, "tables")
            else:
                self.tables = RollableTables(self)
            if self.getArgument("disable_module_decks", False):
                self.cards = EmptyDB(self, "cards")
                self.decks = EmptyDB(self, "decks")
            else:
                self.cards = Items(self, "cards.db")
                self.decks = Decks(self)

            if self.getArgument("disable_module_items", False):
                self.items = EmptyDB(self, "items")

            # Module will add the packs that are not empty and save them to file
            self.module = Module(self).save()
        else:
            os.makedirs(os.path.join(self.path, "data"))

            self.settings = SettingsDB(self).save()
            self.users = Users(self).save()
            self.folders = Folders(self)
            self.macros = Macros(self).save()
            if self.getArgument("dont_convert_chat", False):
                self.chat = EmptyDB(self, "chat").save()
            else:
                self.chat = ChatLog(self).save()
            # Items DB needs to happen as two separate calls due to cross links
            self.items = Items(self)
            self.items.createEntities()
            self.journal = Journal(self).save()
            self.actors = Actors(self).save()
            self.scenes = Scenes(self).save()
            self.combat = Combat(self).save()
            self.playlists = Playlists(self).save()
            # Use items database for deck cards
            self.cards = self.items
            self.tables = Tables(self).save()

            self.sessions = EmptyDB(self, "sessions").save()
            # Could get modified by the journal or rollable tables
            self.folders.save()
            self.items.save()
            self.world = World(self).save()

    def logInfo(self, msg):
        self._logger.logInfo(msg)
    def logWarning(self, msg):
        self._logger.logWarning(msg)
    def logError(self, msg):
        self._logger.logError(msg)

if __name__ == "__main__":
    print("Please use main.py to run R20Converter")