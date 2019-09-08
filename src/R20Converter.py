#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import zipfile
import argparse
import sys
import os
from world import World
from module import Module
from entities import DatabaseFile, EmptyDB, Actors, Combat, Folders, Journal, Playlists, Scenes, SettingsDB, Users

version = "0.4"

class R20Converter(object):
    def __init__(self, args):
        self.args = args
        self.path = args.path
        if args.json:
            with open(args.zip_file, "r") as f:
                self.campaign = json.load(f)
            self.campaign["jukeboxfolder"] = ""
        else:
            self.zip = zipfile.ZipFile(args.zip_file, "r")
            self.campaign = json.load(self.getZipFile("campaign.json"))
        self.packs = {}
        self.fvtt_path = self.getArgument("fvtt_public_path", None)
        if self.fvtt_path == None:
            potential_path = os.path.dirname(os.path.dirname(self.path))
            if os.path.exists(os.path.join(potential_path, "systems", "dnd5e", "system.json")):
                self.fvtt_path = potential_path
        if self.fvtt_path is not None:
            self.loadDnD5ePacks()
        else:
            print("Warning: Could not find the path to the FVTT public directory, either specify a destination directory in the public/worlds/ path\n"
                  "or use the --fvtt-public-path argument to specify the path to the public directory.\n"
                  "If you do not, then Item and Spell Compendium links in journal entries will not be replaced with links to SRD data from the D&D 5e packs.")
 
    def getZipFile(self, filename):
        # On japanese systems, path separator is actually '¥' which won't work
        # when opening the files in the zip.
        return self.zip.open(filename.replace(os.path.sep, "/"))

    def getArgument(self, name, default=None):
        return vars(self.args).get(name, default)

    def loadDnD5ePacks(self):
        self.packs = {}
        for file in ["items", "spells", "classfeatures", "classes", "monsters"]:
            db  = DatabaseFile(self, "%s.db" % file)
            path = os.path.join(self.fvtt_path, "systems", "dnd5e", "packs", "%s.db" % file)
            db.load(path)
            self.packs[file] = db

    def hasSystemPacks(self):
        return len(self.packs) > 0

    def convert(self):
        print("*** Converting Campaign '%s' ***" % self.campaign["campaign_title"])
        os.makedirs(self.path)
        if self.getArgument("export_as_module", False):
            os.makedirs(os.path.join(self.path, "packs"))

            self.journal = Journal(self)
            self.actors = Actors(self)
            self.scenes = Scenes(self)
            self.playlists = Playlists(self)
            # Module will add the packs that are not empty and save them to file
            self.module = Module(self).save()
        else:
            os.makedirs(os.path.join(self.path, "data"))

            self.settings = SettingsDB(self).save()
            self.users = Users(self).save()
            self.folders = Folders(self)
            self.items = EmptyDB(self, "items")
            self.journal = Journal(self).save()
            self.actors = Actors(self).save()
            self.scenes = Scenes(self).save()
            self.combat = Combat(self).save()
            self.playlists = Playlists(self).save()

            self.sessions = EmptyDB(self, "sessions").save()
            self.chat = EmptyDB(self, "chat").save()
            # Could get modified by the journal
            self.folders.save()
            self.items.save()
            self.world = World(self).save()

        print("\nConversion completed.\nMake sure to install the FVTT modules 'permission_viewer' and 'entityorder' (see README file for more information)\n")
        print("It is strongly suggested to check the sheets of the player characters for any errors or missing information, or for adding special traits.")
        print("Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros")
        print("\nThank you for your support!")





parser = argparse.ArgumentParser(description="R20Converter v{}".format(version), epilog="Convert Roll20 campaigns into Foundry VTT worlds.")
parser.add_argument("path", metavar="destination-directory", help="The destination directory in public/worlds/")
parser.add_argument("zip_file", metavar="exported.zip", help="The exported ZIP file from R20Exporter")
parser.add_argument("--json", action="store_true", help="Use campaign.json as input instead of a ZIP file (playlist will be empty due to audio tracks being accessible only when logged into Roll20)")
parser.add_argument("--campaign-title", default=None, help="Override the Campaign title")
parser.add_argument("--description", default="Imported from Roll20 using R20Converter", help="World Desription")
parser.add_argument("-r", "--restrict-movement", action="store_true", help="Force all walls to restrict movement")
parser.add_argument("--enable-fog", action="store_true", help="Enable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--disable-fog", action="store_true", help="Disable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--interactive", action="store_true", help="Ask questions about decisions to be made during the conversion process.")
parser.add_argument("--use-original-image-urls", action="store_true", help="Do not copy images to the world folder but use Roll20 URL instead. (NOT recommended)")
parser.add_argument("--auto-doors", action="store_true", help="Automatically detect doors and set them as such.")
parser.add_argument("--door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into doors. For example, set it to '#ff0000' for Red walls.")
parser.add_argument("--secret-door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into secret doors")
parser.add_argument("--player-password", default="", help="Default player password")
parser.add_argument("--gm-password", default="", help="Default GM password")
parser.add_argument("--disable-archived", action="store_true", help="Disable the automatic move of archived scenes/handouts/characters to an Archived folder.")
parser.add_argument("--minimum-wall-length", default=0, type=float, help="Minimum distance for walls (in pixels).\n"
                    "If a wall is smaller and part of a longer chain of walls, it will get merged with the adjacent wall.\n"
                    "This is useful if there are a lot of small/jagged walls or freehand-drawn walls (Default: 0 (disabled))")
parser.add_argument("--maximum-wall-angle", default=30, type=float, help="Maximum angle (in degrees) between walls before they are merged (when using --minimum-wall-distance option).\n"
                    "This is to prevent small walls at high angles (a small triangle or U shape) from being merged and becoming a line that cuts through the map.\n"
                    "The angle is calculated with every point in the wall that is skipped, so a circle drawn with small lines and small angles will not be removed.\n"
                    "Note that the angle here is related to a straight line, so a maximum angle of 30 means an angle between 150 and 210 degrees between the 3 points (Default: 30)")
parser.add_argument("--debug-page", default=None, help="Only convert a specific page. Useful for debugging")
parser.add_argument("--fvtt-public-path", default=None, help="Path to the FVTT public directory (used for importing items and spells from dnd5e system)")
parser.add_argument("--npc-source", default="Roll 20", help="Source location for NPC actors (displayed in the character sheet)")
parser.add_argument("--no-compendium-overwrite", action="store_true", help="If enabled, items, feats and spells found in the Compendium will not be overwritten with custom description/damage/etc.. from the Roll20 data")
parser.add_argument("--add-walls-around-map", action="store_true", help="Add 4 walls to enclose the map and cut off view/movement to the side table")
parser.add_argument("--export-as-module", action="store_true", help="Export the campaign as a module with Compendium for all handouts/characters/scenes/playlists")

if __name__ == "__main__":
    args = parser.parse_args()

    if os.path.exists(args.path):
        print("Destination directory must not exist")
        sys.exit(-1)

    if args.use_original_image_urls:
        print("*** WARNING ***")
        print("You have decided to use direct image URLs instead of copying the images to the world folder")
        print("This is NOT recommended, as you are still dependent on the assets being available on Roll 20")
        print("Also, you'd be using the servers of Roll20 but not playing on their platform which is not ethically correct")
        print("Use only this option for testing purposes for examples.")
        
    converter = R20Converter(args)
    converter.convert()
