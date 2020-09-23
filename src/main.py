#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import zipfile
import sys
import os
import platform
import argparse

# If we're in windowed mode, we need to have stdout/stderr because the
# GUI/argparse/anything will try to write to stderr/stdout whenever it feels
# like it and will cause a crash on import
if sys.stdout is None:
    sys.stdout = open('stdout.log', 'w')
    sys.stderr = open('stderr.log', 'w')

from version import version
from R20Converter import R20Converter
try:
    from GUI import GUI
except:
    # Because fuck you python and cx_freeze and mac and everything
    try:
        from GUI import GUI
    except:
        GUI = None

parser = argparse.ArgumentParser(description="R20Converter v{}".format(version), epilog="Convert Roll20 campaigns into Foundry VTT worlds or modules.")
parser.add_argument("path", metavar="destination-directory", help="The destination directory in Data/worlds/ or Data/modules/")
parser.add_argument("zip_file", metavar="exported.zip", help="The exported ZIP file from R20Exporter")
parser.add_argument("--json", action="store_true", help="Use campaign.json as input instead of a ZIP file (playlist will be empty due to audio tracks being accessible only when logged into Roll20)")
parser.add_argument("--export-as-module", action="store_true", help="Export the campaign as a module (instead of a world) with Compendium packs for all handouts/characters/scenes/playlists")
parser.add_argument("--campaign-title", default=None, help="Override the Campaign title")
parser.add_argument("--description", default="Imported from Roll20 using R20Converter", help="World Desription")
parser.add_argument("--gm-password", default="", help="Default GM password")
parser.add_argument("--player-password", default="", help="Default player password")
parser.add_argument("--restrict-movement", action="store_true", help="Force all walls to restrict movement")
parser.add_argument("--force-hp-for-token-bar1", action="store_true", help="Forces the use of HP attribute for all tokens' first bar")
parser.add_argument("--force-hp-for-token-bar2", action="store_true", help="Forces the use of HP attribute for all tokens' second bar")
parser.add_argument("--add-walls-around-map", action="store_true", help="Add 4 walls to enclose the map and cut off view/movement to the side table")
parser.add_argument("--enable-fog", action="store_true", help="Enable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--disable-fog", action="store_true", help="Disable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
parser.add_argument("--cleanup-scenes", action="store_true", help="Remove any tiles, tokens or walls that are outside of a scene's boundary")
parser.add_argument("--interactive", action="store_true", help="Ask questions about decisions to be made during the conversion process.")
parser.add_argument("--auto-doors", action="store_true", help="Automatically detect doors and set them as such.")
parser.add_argument("--door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into doors. For example, set it to '#ff0000' for Red walls.")
parser.add_argument("--secret-door-color", default=None, help="Sets the color of the dynamic lighting walls to convert into secret doors")
parser.add_argument("--disable-archived", action="store_true", help="Disable the automatic move of archived scenes/handouts/characters to an Archived folder.")
parser.add_argument("--all-backgrounds-as-tiles",  action="store_true", help="Set all page backgrounds as tiles.")
parser.add_argument("--minimum-wall-length", default=0, type=float, help="Minimum distance for walls (in pixels).\n"
                    "If a wall is smaller and part of a longer chain of walls, it will get merged with the adjacent wall.\n"
                    "This is useful if there are a lot of small/jagged walls or freehand-drawn walls (Default: 0 (disabled))")
parser.add_argument("--maximum-wall-angle", default=30, type=float, help="Maximum angle (in degrees) between walls before they are merged (when using --minimum-wall-distance option).\n"
                    "This is to prevent small walls at high angles (a small triangle or U shape) from being merged and becoming a line that cuts through the map.\n"
                    "The angle is calculated with every point in the wall that is skipped, so a circle drawn with small lines and small angles will not be removed.\n"
                    "Note that the angle here is related to a straight line, so a maximum angle of 30 means an angle between 150 and 210 degrees between the 3 points (Default: 30)")
parser.add_argument("--debug-page", default=None, help="Only convert a specific page. Useful for debugging")
parser.add_argument("--fvtt-data-path", default=None, help="Path to the FVTT Data directory (used for importing items and spells from dnd5e system)")
parser.add_argument("--npc-source", default="Roll 20", help="Source reference for NPC actors (displayed in the character sheet)")
parser.add_argument("--no-compendium-overwrite", action="store_true", help="If enabled, items, feats and spells found in the Compendium will not be overwritten with custom description/damage/etc.. from the Roll20 data")
parser.add_argument("--images-as-drawings", action="store_true", help="Set all images on the scene as textured drawings instead of tiles (requires Furnace to function properly)")
parser.add_argument("--disable-module-journal", action="store_true", help="Disable conversion of Journal entries in the module (requires --export-as-module)")
parser.add_argument("--disable-module-actors", action="store_true", help="Disable conversion of Actors in the module (requires --export-as-module)")
parser.add_argument("--disable-module-scenes", action="store_true", help="Disable conversion of Scenes in the module (requires --export-as-module)")
parser.add_argument("--disable-module-playlists", action="store_true", help="Disable conversion of Playlists in the module (requires --export-as-module)")
parser.add_argument("--disable-module-tables", action="store_true", help="Disable conversion of rollable tables in the module (requires --export-as-module)")
parser.add_argument("--disable-module-decks", action="store_true", help="Disable conversion of card decks in the module (requires --export-as-module)")
parser.add_argument("--dont-convert-chat", action="store_true", help="Disable converting the chat and leave the chat log empty")
parser.add_argument("--folder-as-items", action="append", default=["Magic Items"], help="Converts each entry in a journal folder into items. Useful for 'Magic Items' folders. Can be passed multiple times to convert more than one folder.")
parser.add_argument("--dont-export-actor-items", action="store_true", help="Items from actors will be exported as individual Entity Items. This option disables that behavior and no items will be created.")
parser.add_argument("--no-duplicate-actor-items", action="store_true", help="This option causes items with the same name from different actors to be exported under a single item. The first processed actor with the item of that name gets their item in the item entities.")
parser.add_argument("--use-original-image-urls", action="store_true", help="Do not copy images to the world folder but use Roll20 URL instead. (NOT recommended)")
parser.add_argument("--max-path", default=256, type=int, help="Set the maximum allowed length for the asset's absolute file paths. Most File Systems will have a limit of 256 characters, but you can set it to lower (or higher) if you plan on moving the worlds directory to a different FVTT path. Files that don't fit will be written in an 'assets' directory instead of the usual hierarchy.")
parser.add_argument("--overwrite", action="store_true", help="Overwrite the destination directory if it exists.")
parser.add_argument("--game-system", default="dnd5e", help="Set the game system to use for actors and items's sheets (only dnd5e sheets will be converted)")


if __name__ == "__main__":
    if len(sys.argv) == 1 and GUI is not None:
        try:
            GUI.start()
            sys.exit(0)
        except Exception as e:
            print(e)
            pass

    args = parser.parse_args()

    if os.path.exists(args.path):
        if args.overwrite:
            import shutil
            shutil.rmtree(args.path)
        else:
            print("Destination directory must not exist")
            sys.exit(-1)

    if args.use_original_image_urls:
        print("*** WARNING ***")
        print("You have decided to use direct image URLs instead of copying the images to the world folder")
        print("This is NOT recommended, as you are still dependent on the assets being available on Roll 20")
        print("Also, you'd be using the servers of Roll20 but not playing on their platform which is not ethically correct")
        print("Use only this option for testing purposes for example.")
    
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
        message = "\nConversion completed.\nMake sure to install the FVTT modules 'permission_viewer' and 'furnace' (see README file for more information)\n\n"
        message += "It is strongly suggested to check the sheets of the NPCs and player characters for any errors or missing information, or for adding special traits.\n"
        message += "Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros\n"
        message += "If using The Forge (https://forge-vtt.com) for hosting your Foundry games, you can now import the generated world using the Import Wizard.\n"
        message += "\nThank you for your support!"
    print(message)
