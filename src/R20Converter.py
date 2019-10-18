#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import zipfile
import argparse
import sys
import os
from world import World
from module import Module
from entities import DatabaseFile, EmptyDB, Actors, Items, Combat, Folders, Journal, Playlists, Scenes, SettingsDB, Users
try:
    import PySimpleGUIQt as sg
    line_height = 0.5
except:
    line_height = 1
    try:
        import PySimpleGUI as sg
    except:
        sg = None

version = "0.6RC1"

class R20Converter(object):
    def __init__(self, args):
        self.args = args
        self.path = args.path
        if args.json:
            with open(args.zip_file, "r", encoding='utf-8') as f:
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

            if self.getArgument("disable_module_journal", False):
                self.journal = EmptyDB(self, "journal")
            else:
                self.journal = Journal(self)
            if self.getArgument("disable_module_items", False):
                # actors can modify the items list, so create the correct class
                # and overwrite it with an emptyDB later
                self.items = Items(self)
            else:
                self.items = Items(self)
                self.items.createEntities()
            if self.getArgument("disable_module_actors", False):
                self.actors = EmptyDB(self, "actors")
            else:
                self.actors = Actors(self)
            if self.getArgument("disable_module_scenes", False):
                self.scenes = EmptyDB(self, "scenes")
            else:
                self.scenes = Scenes(self)
            if self.getArgument("disable_module_playlists", False):
                self.playlists = EmptyDB(self, "playlists")
            else:
                self.playlists = Playlists(self)
            if self.getArgument("disable_module_items", False):
                self.items = EmptyDB(self, "items")
            # Module will add the packs that are not empty and save them to file
            self.module = Module(self).save()
        else:
            os.makedirs(os.path.join(self.path, "data"))

            self.settings = SettingsDB(self).save()
            self.users = Users(self).save()
            self.folders = Folders(self)
            # Items DB needs to happen as two separate calls due to cross links
            self.items = Items(self)
            self.items.createEntities()
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

class GUI(object):
    LABEL_SIZE = (40, line_height)
    BIG_LABEL_SIZE = (70, line_height)
    def __init__(self, *args, **kwargs):
        self.parser = argparse.ArgumentParser(*args, **kwargs)
        sg.ChangeLookAndFeel('Reddit')
        self.layout = [[sg.Text(self.parser.description, justification="center", font=("Helvetica", 15), text_color="blue")],
                        [sg.Text(self.parser.epilog, font=("Helvetica", 12))],
                        [sg.Text('Use campaign.json as input instead of a ZIP file', key="--json_help", size=self.BIG_LABEL_SIZE), sg.Checkbox('', key="--json")],
                        [sg.Text("ZIP File (or JSON file) export by R20Exporter", size=self.LABEL_SIZE), sg.Input('Campaign.zip', key="zip_file", tooltip='The exported ZIP file (or campaign.json) exported by R20Exporter'), sg.FileBrowse()],
                        [sg.Text("FVTT Public Directory", size=self.LABEL_SIZE), sg.Input('C:\\FVTT\\resources\\app\\public', key="--fvtt-public-path", tooltip='Path to the Foundry VTT public directory'), sg.FolderBrowse()],
                        [sg.Text("Export as a Module instead of a World", size=self.BIG_LABEL_SIZE, tooltip='Export the campaign as a module (instead of a world) with Compendium packs for all handouts/characters/scenes/playlists', key="--export-as-module_help"), sg.Checkbox('', key="--export-as-module")],
                        [sg.Text("World or Module URL name", size=self.LABEL_SIZE, tooltip='Name of the directory in which to convert the campaign. Must be URL-safe (Destination directory will be based on the FVTT public directory and this name)'), sg.Input('your-world-url', key="world-name")],
                        [sg.Text("_"*100)],
                        ]
        self.options = {}

    def add_argument(self, argument, **kwargs):
        self.parser.add_argument(argument, **kwargs)
        if not argument.startswith("--") or argument in ["--interactive", "--debug-page", "--fvtt-public-path"]:
            return
        self.options[argument] = kwargs
        if argument in ["--json", "--export-as-module"]:
            return
        argument_labels = {
            "--campaign-title": "Campaign Title (leave empty to use exported title)",
            "--gm-password": "GM Password",
            "--npc-source": "NPC Source",
            "--no-compendium-overwrite": "Overwrite actor items and feats with data from SRD Compendium",
            "--use-original-image-urls": "Use Roll 20 Image URLs (NOT Recommended)"
        }
        name = " ".join(map(lambda x: x.capitalize(), argument[2:].split("-")))
        name = argument_labels.get(argument, name)
        default = kwargs.get("default", None) if kwargs.get("default", None) is not None else ""
        size = self.LABEL_SIZE
        if argument == "--description":
            widget = sg.Multiline(default, key=argument)
        elif argument in ["--enable-fog", "--disable-fog"]:
            size = self.BIG_LABEL_SIZE
            enabled = False
            if argument == "--enable-fog":
                self.layout.append([sg.Text("Do not modify Fog", tooltip="Sets Fog Exploration on all Scenes according to Advanced Fog of war setting", size=size), sg.Radio("", "fog")])
                enabled = True
            widget = sg.Radio(default, "fog", key=argument, default=enabled)
        elif kwargs.get("action", "") == "store_true":
            size = self.BIG_LABEL_SIZE
            widget = sg.Checkbox(default, key=argument, default=argument in ["--add-walls-around-map", "--restrict-movement"])
        else:   
            widget = sg.Input(default, key=argument)
        self.layout.append([sg.Text(name, tooltip=kwargs.get("help", ""), size=size), widget])

    def parse_args(self):
        self.layout.append([sg.Button("Convert Campaign")])
        window = sg.Window(self.parser.description).Layout(self.layout)
        while True:
            button, values = window.Read()
            if button == None:
                args = None
            else:
                if values["--export-as-module"]:
                    directory = "modules"
                else:
                    directory = "worlds"
                fvtt_path = values["--fvtt-public-path"]
                if not os.path.exists(fvtt_path):
                    sg.Popup(self.parser.description, "Specified FVTT directory does not exist : ", fvtt_path)
                    continue
                    
                if not os.path.exists(os.path.join(fvtt_path, "worlds")):
                    if os.path.exists(os.path.join(fvtt_path, "public", "worlds")):
                        fvtt_path = os.path.join(fvtt_path, "public")
                    elif os.path.exists(os.path.join(fvtt_path, "resources", "app", "public")):
                        fvtt_path = os.path.join(fvtt_path, "resources", "app", "public")
                    else:
                        sg.Popup(self.parser.description, "Specified FVTT directory does not seem to be a valid FVTT installation : ", fvtt_path)
                        continue
                path = os.path.join(fvtt_path, directory, values["world-name"])
                args = [path, values["zip_file"]]
                for option in self.options:
                    value = values[option]
                    if option == "--description":
                        value = "".join(list(map(lambda l: "<p>" + l + "</p>", value.split("\n"))))
                    if self.options[option].get("action", "") == "store_true":
                        if value:
                            args.append(option)
                    elif self.options[option].get("default", None) is not None or value != "":
                        args.extend([option, value])
                if os.path.exists(path):
                    sg.Popup(self.parser.description, "Destination directory must not exist : ", path)
                    continue
                if not os.path.exists(values["zip_file"]):
                    sg.Popup(self.parser.description, "%s file does not exist : " % ("JSON" if values["--json"] else "ZIP"), values["zip_file"])
                    continue
            break
        window.close()
        print("Running with arguments : ", args)
        return self.parser.parse_args(args)

    def done(self, message):
        print(message)
        sg.Popup(self.parser.description, message)

use_gui = False
if len(sys.argv) > 1 or sg is None:
    ArgumentParser = argparse.ArgumentParser
else:
    ArgumentParser = GUI
    use_gui = True
parser = ArgumentParser(description="R20Converter v{}".format(version), epilog="Convert Roll20 campaigns into Foundry VTT worlds or modules.")
parser.add_argument("path", metavar="destination-directory", help="The destination directory in public/worlds/ or public/modules/")
parser.add_argument("zip_file", metavar="exported.zip", help="The exported ZIP file from R20Exporter")
parser.add_argument("--json", action="store_true", help="Use campaign.json as input instead of a ZIP file (playlist will be empty due to audio tracks being accessible only when logged into Roll20)")
parser.add_argument("--export-as-module", action="store_true", help="Export the campaign as a module (instead of a world) with Compendium packs for all handouts/characters/scenes/playlists")
parser.add_argument("--campaign-title", default=None, help="Override the Campaign title")
parser.add_argument("--description", default="Imported from Roll20 using R20Converter", help="World Desription")
parser.add_argument("--gm-password", default="", help="Default GM password")
parser.add_argument("--player-password", default="", help="Default player password")
parser.add_argument("--restrict-movement", action="store_true", help="Force all walls to restrict movement")
parser.add_argument("--add-walls-around-map", action="store_true", help="Add 4 walls to enclose the map and cut off view/movement to the side table")
parser.add_argument("--enable-fog", action="store_true", help="Enable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--disable-fog", action="store_true", help="Disable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--cleanup-scenes", action="store_true", help="Remove any tiles, tokens or walls that are outside of a scene's boundary")
parser.add_argument("--interactive", action="store_true", help="Ask questions about decisions to be made during the conversion process.")
parser.add_argument("--auto-doors", action="store_true", help="Automatically detect doors and set them as such.")
parser.add_argument("--door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into doors. For example, set it to '#ff0000' for Red walls.")
parser.add_argument("--secret-door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into secret doors")
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
parser.add_argument("--npc-source", default="Roll 20", help="Source reference for NPC actors (displayed in the character sheet)")
parser.add_argument("--no-compendium-overwrite", action="store_true", help="If enabled, items, feats and spells found in the Compendium will not be overwritten with custom description/damage/etc.. from the Roll20 data")
parser.add_argument("--images-as-drawings", action="store_true", help="Set all images on the scene as textured drawings instead of tiles (requires Furnace to function properly)")
parser.add_argument("--use-original-image-urls", action="store_true", help="Do not copy images to the world folder but use Roll20 URL instead. (NOT recommended)")
parser.add_argument("--disable-module-journal", action="store_true", help="Disable conversion of Journal entries in the module (requires --export-as-module)")
parser.add_argument("--disable-module-actors", action="store_true", help="Disable conversion of Actors in the module (requires --export-as-module)")
parser.add_argument("--disable-module-scenes", action="store_true", help="Disable conversion of Scenes in the module (requires --export-as-module)")
parser.add_argument("--disable-module-playlists", action="store_true", help="Disable conversion of Playlists in the module (requires --export-as-module)")
parser.add_argument("--folder-as-items", action="append", default=["Magic Items"], help="Converts each entry in a journal folder into items. Useful for 'Magic Items' folders. Can be passed multiple times to convert more than one folder.")
parser.add_argument("--dont-export-actor-items", action="store_true", help="Items from actors will be exported as individual Entity Items. This option disables that behavior and no items will be created.")
parser.add_argument("--no-duplicate-actor-items", action="store_true", help="This option causes items with the same name from different actors to be exported under a single item. The first processed actor with the item of that name gets their item in the item entities.")
parser.add_argument("--max-path", default=256, type=int, help="Set the maximum allowed length for the asset's absolute file paths. Most File Systems will have a limit of 256 characters, but you can set it to lower (or higher) if you plan on moving the worlds directory to a different FVTT path. Files that don't fit will be written in an 'assets' directory instead of the usual hierarchy.")


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
    
    error = None
    try:
        converter = R20Converter(args)
        converter.convert()
    except Exception as e:
        error = e
        print(e)
        try:
            import traceback
            traceback.print_exc()
        except:
            pass

    if error:
        message = "Error converting campaign : \n" + str(error)
        message += "\nPlease contact the author with the log of the error from the console window"
    else:
        message = "\nConversion completed.\nMake sure to install the FVTT modules 'permission_viewer', 'entityorder' and 'furnace' (see README file for more information)\n\n"
        message += "It is strongly suggested to check the sheets of the player characters for any errors or missing information, or for adding special traits.\n"
        message += "Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros\n"
        message += "\nThank you for your support!"
    if use_gui:
        parser.done(message)
    else:
        print(message)
