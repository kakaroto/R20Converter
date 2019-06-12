#!/usr/bin/python
# -*- coding: utf-8 -*-

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

import json
import base64
import zipfile
import argparse
import urllib
import math
import re
import sys
import os
import errno

class R20Converter(object):
    def __init__(self, args):
        self.args = args
        self.path = args.path
        self.zip = zipfile.ZipFile(args.zip_file, "r")
        self.campaign = json.load(self.getZipFile("campaign.json"))

    def findID(self, id, where=None):
        if where == "handout" or where is None:
            matches = [item for item in self.campaign["handouts"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "page" or where is None:
            matches = [item for item in self.campaign["pages"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "character" or where is None:
            matches = [item for item in self.campaign["characters"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "player" or where is None:
            matches = [item for item in self.campaign["players"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "track" or where is None:
            matches = [item for item in self.campaign["jukebox"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        return None

    def getZipFile(self, filename):
        return self.zip.open(filename)

    def getArgument(self, name, default=None):
        return vars(self.args).get(name, default)

    def convert(self):
        print "*** Converting Campaign '%s' ***" % self.campaign["campaign_title"]
        os.makedirs(self.path)
        os.makedirs(os.path.join(self.path, "data"))
        os.makedirs(os.path.join(self.path, "scenes"))

        World(self).save()
        Users(self).save()
        Folders(self).save()
        Journal(self).save()
        Actors(self).save()
        Scenes(self).save()
        Combat(self).save()
        Playlists(self).save()

        EmptyDB(self, "sessions").save()
        EmptyDB(self, "settings").save()
        EmptyDB(self, "chat").save()
        EmptyDB(self, "items").save()


class DatabaseFile(object):
    def __init__(self, converter, filename):
        self._converter = converter
        self._path = converter.path
        self._filename = filename
        self._campaign = converter.campaign

    def findID(self, id, where=None):
        return self._converter.findID(id, where)

    def getArgument(self, name, default=None):
        return self._converter.getArgument(name, default)

    def getEntries(self):
        raise NotImplemented

    def __str__(self):
        entries = self.getEntries()
        lines = ""
        for entry in entries:
            lines += str(entry) + "\n"
        return lines

    def save(self):
        filename = os.path.join(self._path, "data", self._filename)
        with open(filename, "w") as f:
            f.write(str(self))
        
        return None

class Entity(object):
    # Ensures ids are unique accross all entities
    id_database = {}

    def __init__(self, database, id):
        self._database = database
        self._id = self.normalizeID(id)

    def findID(self, id, where=None):
        return self._database.findID(id, where)

    def getArgument(self, name, default=None):
        return self._database.getArgument(name, default)

    @staticmethod
    def normalizeID(id):
        if id is None:
            return None
        if id in Entity.id_database:
            return Entity.id_database[id]
        normalized_id = base64.b64encode(hex(hash(id))[-12:])
        index = 0
        while normalized_id in Entity.id_database.values():
            print("Found an ID conflict for %s=%s\n%s" % (id, normalized_id, str(Entity.id_database)))
            new_id = "%s%d" % (id, index)
            normalized_id = base64.b64encode(hex(hash(new_id))[-12:])
            index += 1
        Entity.id_database[id] = normalized_id
        return normalized_id

    # Used to fix the sometimes broken color codes in R20
    @staticmethod
    def color(val, default="#c0c0c0", allow_transparent=False):
        if allow_transparent and val == "transparent":
            return None
        m = re.match("rgb\((\d+), (\d+), (\d+)\)", val)
        if m:
            return "#%02x%02x%02x" % tuple(map(int, m.groups()))
        if not val.startswith("#") or len(val) < 4:
            return default
        val = val[1:]
        lv = len(val)
        try:
            if len(val) < 6:
                rgb = tuple(int(val[i:i+1], 16) * 16 for i in (0, 1, 2))
            else:
                rgb = tuple(int(val[i:i+2], 16) for i in (0, 2, 4))
            return "#%02x%02x%02x" % rgb
        except:
            return default

    @staticmethod
    def urlsafe(filename):
        url = urllib.pathname2url(filename.replace(" ", "_").replace(u"’", "_"))
        # Url encoded characters won't resolve, since the URL would become invalid, so we replace them
        return re.sub("%([0-9A-F]{2})", "_\\1", url)

    def getDestinationPaths(self, destination):
        index = 1
        destination_safe = self.urlsafe(destination)
        while True:
            dest_filename = os.path.join(self._database._path, destination_safe)
            # Check for conflicts
            if os.path.exists(dest_filename):
                splitext = os.path.splitext(destination)
                new_destination = "".join(splitext[0], "_%d_" % index, splitext[1])
                destination_safe = self.urlsafe(destination)
                index += 1
            else:
                break

        try:
            os.makedirs(os.path.dirname(dest_filename))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        world_dir_name = os.path.dirname(os.path.join(self._database._path, "."))
        config_path = os.path.join("worlds", world_dir_name, destination_safe)
        return (dest_filename, config_path)
    
    def copyFile(self, file, destination):
        (dest_filename, config_path) = self.getDestinationPaths(destination)
        with open(dest_filename, "wb") as f:
            f.write(file.read())
        return (dest_filename, config_path)

    def copyZipFile(self, filename, destination):
        try:
            zipfile = self._database._converter.getZipFile(filename)
            return self.copyFile(zipfile, destination)
        except Exception as e:
            print "Error copying file '%s' from Zip: %s" % (filename, e)
            return (None, "")

    def __str__(self):
        return json.dumps(self.entity)

class EmptyDB(DatabaseFile):
    def __init__(self, converter, name):
        DatabaseFile.__init__(self, converter, name + ".db")

    def getEntries(self):
        return []

class World(object):
    def __init__(self, converter):
        self._path = converter.path
        self._title = converter.campaign["campaign_title"]
        self._description = converter.getArgument("description")

    def toDict(self):
        return {"name": self._title,
                "description": self._description,
                "system": "dnd5e",
                "coreVersion": "0.3.0",
                "systemVersion": 0.5,
                "packs": [],
                "scripts": [],
                "styles": []
                }

    # This is a json file, not a db file, so let's override the __str__ method
    def __str__(self):
        return json.dumps(self.toDict(), indent=2)

    def save(self):
        filename = os.path.join(self._path, "world.json")
        with open(filename, "w") as f:
            f.write(str(self))

class Users(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "users.db")
        self._players = self._campaign["players"]

    def getEntries(self):
        users = [User(self, player) for player in self._players]
        users[0].setGM(True)
        return users

class User(Entity):
    def __init__(self, database, player):
        Entity.__init__(self, database, player["id"])
        self.entity = {"_id": self._id,
                       "name": player["displayname"],
                       "permission":1,
                       "flags":{},
                       "password":"",
                       "color": self.color(player["color"])
                       }
    def setGM(self, gm):
        self.entity["permission"] = 4 if gm else 1

class Folders(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "folders.db")
        self._preserve_order = self.getArgument("preserve_folder_order", False)
        
    def addFolder(self, folder, parent):
        folders = []
        has_characters = False
        has_handouts = False
        for item in folder["i"]:
            if type(item) == dict:
                # Found a folder
                (children, child_handouts, child_characters) = self.addFolder(item, folder["id"])
                folders.extend(children)
                has_characters |= child_characters
                has_handouts |= child_handouts
            else:
                if self.findID(item, "character") != None:
                    has_characters = True
                elif self.findID(item, "handout") != None:
                    has_handouts = True
                else:
                    print "Unknown ID in Journal folder: %s"  % item

        # By default, an empty folder would appear in the journal
        if has_handouts or not has_characters:
            has_handouts = True
            folders.append(Folder(self, "handout" + folder["id"], folder["n"], "JournalEntry", ("handout" + parent) if parent else None ))
        if has_characters:
            folders.append(Folder(self, "character" + folder["id"], folder["n"], "Actor", ("character" + parent) if parent else None))
        return (folders, has_handouts, has_characters)

    def getEntries(self):
        parent = None
        folders = []
        create_root_folder = False
        for item in self._campaign["journalfolder"]:
            if type(item) == dict:
                (children, _, _) = self.addFolder(item, None)
                folders.extend(children)
            else:
                if self.findID(item, "handout") != None:
                    create_root_folder = True

        for page in self._campaign["pages"]:
            if page["archived"]:
                folders.append(Folder(self, "archived-scenes-folder-id", "Archived Scenes", "Scene", None))
                break
        if create_root_folder:
            #name = "%sRoot Folder" % (("%03d - " % index) if self._preserve_order else "")
            folders.append(Folder(self, "root-handouts-folder-id", "Root folder", "JournalEntry", None))
        return folders
    

class Folder(Entity):
    def __init__(self, database, id, name, folder_type, parent):
        Entity.__init__(self, database, id)
        # TODO: add hierarchy for journal
        if folder_type == "JournalEntry":
            parent = None
        self.entity = {"_id": self._id,
                       "name": name, 
                       "type": folder_type,
                       "parent": Entity.normalizeID(parent)
                       }

class Journal(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "journal.db")
        self._handouts = self._campaign["handouts"]

    def addToFolder(self, folder_id, folder, folder_path):
        handouts = []
        index = 0
        for item in folder:
            if type(item) == dict:
                dirname = "%03d - %s" % (index, item["n"])
                handouts.extend(self.addToFolder("handout" + item["id"], item["i"], os.path.join(folder_path, dirname)))
                index += 1
            else:
                handout = self.findID(item, "handout")
                if handout != None:
                    handouts.append(Handout(self, handout, index, folder_id, folder_path))
                    index += 1
                elif self.findID(item, "character") != None:
                    index += 1
                    
        return handouts

    def getEntries(self):
        return self.addToFolder("root-handouts-folder-id", self._campaign["journalfolder"], "journal")

# TODO: handle Archived handouts differently?
class Handout(Entity):
    PERMISSION_NONE = 0
    PERMISSION_DEFAULT = -1
    PERMISSION_LIMITED = 1
    PERMISSION_OBSERVER = 2
    PERMISSION_OWNER = 3
    def __init__(self, database, handout, index, parent, path):
        Entity.__init__(self, database, handout["id"])
        print "Creating Handout : %s" % handout["name"]
        # TODO: Replace cross-link journals with @Journ
        content = handout["notes"]
        gmnotes = handout["gmnotes"]
        if gmnotes != "":
            content += "\n<section class=\"secret\"><p>GM Notes : </p>" + gmnotes + "</section>"
        permissions = {"default": Handout.PERMISSION_NONE}
        for player in handout.get("inplayerjournals", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_OBSERVER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_OBSERVER
        for player in handout.get("controlledby", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_OWNER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_OWNER
        avatar_filename = ""
        if handout["avatar"] != "":
            if self.getArgument("use_original_image_urls", False):
                avatar_filename = handout["avatar"]
            else:
                filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
                (_, avatar_filename) = self.copyZipFile(filename, filename)
        self.entity = {"_id": self._id,
                       "name": handout["name"],
                       "permission": permissions,
                       "folder": Entity.normalizeID(parent),
                       "flags":{"r20-handout-order" : index, "r20-handout-archived": handout["archived"]},
                       "entryTime": 0,
                       "content": content,
                       "img": avatar_filename
                       }


class Actors(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "actors.db")
        self._characters = self._campaign["characters"]

    def getEntries(self):
        return [Actor(self, character, index) for index, character in enumerate(self._characters)]

class Token(Entity):
    DISPLAY_NONE = 0
    DISPLAY_CONTROL = 10
    DISPLAY_OWNER_HOVER = 20
    DISPLAY_HOVER = 30
    DISPLAY_OWNER = 40
    DISPLAY_ALWAYS = 50
    def __init__(self, actor_id, name, token=None):
        self._token = token
        self.actor_id = actor_id
        # Create default token
        self.token_name = name
        self.token_filename = "icons/svg/mystery-man.svg"
        # Grid size in Roll20 is hardcoded to 70x70
        self.width = 70
        self.height = 70
        self.rotation = 0
        show_name = True
        all_see_name = False
        show_bar1 = True
        all_see_bar1 = False
        show_bar2 = True
        all_see_bar2 = False
        self.bar1_val = 0
        self.bar1_max = 0
        self.bar1_attr = ""
        self.bar2_val = 0
        self.bar2_max = 0
        self.bar2_attr = ""
        self.dim_sight = 0
        self.bright_sight = 0
        self.emits_dim_light = 0
        self.emits_bright_light = 0
        self.emits_light = False

        if token:
            self.token_name = token.get("name", self.token_name)
            self.token_filename = token.get("imgsrc", self.token_filename)
            show_name = token.get("showname", show_name)
            all_see_name = token.get("showplayers_name", all_see_name)
            self.width = token.get("width", self.width)
            self.height = token.get("height", self.height)
            self.rotation = token.get("rotation", self.rotation)
            self.bar1_val = token.get("bar1_value", self.bar1_val)
            if self.bar1_val == "":
                self.bar1_val = 0
            self.bar1_max = token.get("bar1_max", self.bar1_max)
            if self.bar1_max == "":
                self.bar1_max = 0
            self.bar2_val = token.get("bar2_value", self.bar2_val)
            if self.bar2_val == "":
                self.bar2_val = 0
            self.bar2_max = token.get("bar2_max", self.bar2_max)
            if self.bar2_max == "":
                self.bar2_max = 0
            all_see_bar1 = token.get("showplayers_bar1", all_see_bar1)
            all_see_bar2 = token.get("showplayers_bar2", all_see_bar2)
            lradius = token.get("light_radius", 0)
            ldimradius = token.get("light_dimradius", 0)
            self.setupLighting(lradius, ldimradius)

        if self.bar1_max > 0 or self.bar2_max > 0:
            all_see_bars = all_see_bar1 or all_see_bar2
            self.display_bars = self.DISPLAY_ALWAYS if all_see_bars else self.DISPLAY_OWNER
        else:
            self.display_bars = self.DISPLAY_NONE

        if show_name:
            self.display_name = self.DISPLAY_ALWAYS if all_see_name else self.DISPLAY_OWNER
        else:
            self.display_name = self.DISPLAY_NONE

    def setupLighting(self, light_radius, light_dimradius, scale=5, scale_units="ft", grid_size=70):
        # We don't check for light_hassight because R20 has to set it for NPC tokens to False
        # otherwise they get performance issues
        (dim, bright) = self.computeLighting(light_radius, light_dimradius, self.width, self.height)
        if self._token.get("light_otherplayers", True):
            self.emits_light = True
            self.emits_dim_light = dim
            self.emits_bright_light = bright
        multiplier = self._token.get("light_multiplier", 1)
        self.dim_sight = dim * multiplier
        self.bright_sight = bright * multiplier
        # But if you have sight but no vision, then FVTT won't show you anything, even if
        # you're next to a bright source of light, so we set dim sight to 1 ft in that case
        if self.dim_sight == 0 and self.bright_sight == 0 and self._token.get("light_hassight", True):
            self.dim_sight = 1


    @staticmethod
    def computeLighting(light_radius, light_dimradius, width, height, scale=5, scale_units="ft", grid_size=70):
        try:
            g_light_radius = float(light_radius)
        except:
            g_light_radius = ""
        try:
            g_light_dimradius = float(light_dimradius)
        except:
            g_light_dimradius = 0.25 * g_light_radius if g_light_radius != "" else ""
        if g_light_radius != "":
            # The way light works in R20 is weird, the light_radius is from the edges of the token, but the
            # light_dimradius is the 'start of dim' also from the edges of the token, but light starts from
            # the center of the token. So a 5x5 token that emits light for 20 ft and has a start of 5 ft
            # is going to emit bright light for 25 ft from the center with dim starting 10 ft from the center
            # A non-square token is considered a square of the bigger dimension for the purposes of light radiuses
            # if no dimradius is specified, then it's 25% from the bright light.
            try:
                token_radius = width if width > height else height
                # Transform tile width into feet
                if scale_units == "ft":
                    token_radius = float(scale_number) * token_radius / grid_size
                else:
                    token_radius = 0
            except:
                token_radius = 0
            light_radius = token_radius + g_light_radius
            if light_radius < 0:
                light_radius = 0
            start_of_dim = token_radius + g_light_dimradius
            # Negative in FVTT is darkness, R20 doesn't support that
            bright = light_radius - (start_of_dim if start_of_dim < light_radius else 0)
            dim = light_radius
            return (dim, bright)
        return (0, 0)

    def getDict(self):
        return {"flags": {},
                "name": self.token_name,
                "displayName": self.display_name,
                "img": self.token_filename,
                "width": self.width / 70.0,
                "height": self.height / 70.0,
                "scale": 1,
                "elevation": 0,
                "rotation": self.rotation,
                "effects": [], #TODO : support effects. Format is : ["icons/svg/frozen.svg", "icons/svg/skull.svg"], etc..
                "hidden": False,
                "dimLight": self.emits_dim_light,
                "brightLight": self.emits_bright_light,
                "dimSight": self.dim_sight,
                "brightSight": self.bright_sight,
                "actorId": self.actor_id,
                "actorLink": False,
                "disposition": -1,
                "displayBars": self.display_bars,
                "bar1": {"attribute": "attributes.bar1" if self.bar1_max > 0 else "",
                         "value": self.bar1_val,
                         "max": self.bar1_max
                         },
                "bar2": {"attribute": "attributes.bar2" if self.bar2_max > 0 else "",
                         "value": self.bar2_val,
                         "max": self.bar2_max
                         }
                }

class Actor(Entity):    
    def __init__(self, database, character, index):
        Entity.__init__(self, database, character["id"])
        self._character = character

        print "Creating Character : %s" % character["name"]
        permissions = {"default": Handout.PERMISSION_NONE}
        for player in character.get("inplayerjournals", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_OBSERVER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_OBSERVER
        for player in character.get("controlledby", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_OWNER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_OWNER

        npc = self.isNPC()
        bio = character["bio"]
        avatar_filename = ""
        if character["avatar"] != "":
            if self.getArgument("use_original_image_urls", False):
                avatar_filename = character["avatar"]
            else:
                filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "avatar.png")
                (_, avatar_filename) = self.copyZipFile(filename, filename)
        folder = self.findFolder(character["id"],  self._database._campaign["journalfolder"])

        default_token = character["defaulttoken"] if character["defaulttoken"] != "" else None
        token = Token(self._id, character["name"], default_token).getDict()
        if default_token and default_token.get("imgsrc", "") != "":
            if self.getArgument("use_original_image_urls", False):
                token_filename = default_token["imgsrc"]
            else:
                filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "token.png")
                (_, token_filename) = self.copyZipFile(filename, filename)
            token["img"] = token_filename
            if avatar_filename == "":
                avatar_filename = token_filename
            bar1_link = token.get("bar1_link", "")
            bar2_link = token.get("bar2_link", "")
            (_, _, hp_id) = self.getAttribute("hp")
            if bar1_link == hp_id:
                token["bar1"]["attribute"] = "attributes.hp"
            if bar2_link == hp_id:
                token["bar2"]["attribute"] = "attributes.hp"
        token["actorLink"] = not npc

        self.entity = {"_id": self._id,
                       "name": character["name"],
                       "img": avatar_filename,
                       "permission": permissions,
                       "data": {"abilities" : self.createActorAbilities(),
                                "attributes" : self.createActorAttributes(),
                                "details" : self.createActorDetails(bio),
                                "skills" : self.createActorSkills(),
                                "traits" : self.createActorTraits(),
                                "currency" : self.createActorCurrency(),
                                "spells" : self.createActorSpells(),
                                "resources" : self.createActorResources(),
                                },
                       "folder": Entity.normalizeID(folder),
                       "flags": {},
                       "type": "npc" if npc else "character",
                       "token": token,
                       "items": []
                       }

    def findFolder(self, id, folder, folder_id=None):
        for item in folder:
            if type(item) == dict:
                ret = self.findFolder(id, item["i"], "character" + item["id"])
                if ret:
                    return ret
            else:
                if item == id:
                    return folder_id
        return None

    def getAttribute(self, key, default=None):
        for attr in self._character["attributes"]:
            if attr["name"] == key:
                return (attr["current"], attr["max"], attr["id"])
        return (default, default, None)

    def isNPC(self):
        npc = self.getAttribute("npc", "0")
        try:
            return bool(int(npc[0]))
        except:
            return False

    def createActorAbility(self, name):
        ability = self.getAttribute(name.lower(), 10)
        mod = self.getAttribute(name.lower() + "_mod", 0)
        if self.isNPC():
            save = self.getAttribute(name.lower() + "_save_bonus", mod)
            proficient = (save[0] == mod[0])
        else:
            save = self.getAttribute("npc_" + name.lower()[0:3] + "_save", "")
            proficient = (save[0] != "")
        return {"type": "Number",
                "label": name,
                "value": ability[0],
                "min": 3,
                "proficient": 1 if proficient else 0
                }

    def createActorAbilities(self):
        return {"str": self.createActorAbility("Strength"),
                "dex": self.createActorAbility("Dexterity"),
                "con": self.createActorAbility("Constitution"),
                "int": self.createActorAbility("Intelligence"),
                "wis": self.createActorAbility("Wisdom"),
                "cha": self.createActorAbility("Charisma")
                }

    def createActorAttributes(self):
        attributes = {
            "ac": {
                "type": "Number",
                "label": "Armor Class",
                "min": 0,
                "value": 0
                },
            "hp": {
                "type": "Number",
                "label": "Hit Points",
                "value": 10,
                "min": 0,
                "max": 10,
                "temp": 0,
                "tempmax": 0
                },
            "init": {
                "type": "Number",
                "label": "Initiative Modifier",
                "value": 0
                },
            "prof": {
                "type": "Number",
                "label": "Proficiency",
                "value": 0
                },
            "speed": {
                "type": "String",
                "label": "Movement Speed",
                "value": "30 ft",
                "special": ""
                },
            "spellcasting": {
                "type": "String",
                "label": "Spellcasting Ability",
                "value": ""
                },
            "spelldc": {
                "type": "String",
                "label": "Spell DC"
                }
            }
        if not self.isNPC():
            attributes.update({
                    "hd": {
                        "type": "Number",
                        "label": "Hit Dice",
                        "value": 1,
                        "min": 0
                        },
                    "death": {
                        "type": "Number",
                        "label": "Death Saves",
                        "success": 0,
                        "failure": 0
                        },
                    "exhaustion": {
                        "type": "Number",
                        "label": "Exhaustion Level",
                        "value": 0
                        },
                    "inspiration": {
                        "type": "Boolean",
                        "label": "Inspiration",
                        "value": False
                        }
                    })
        return attributes

    def createActorDetails(self, bio):
        details = {
            "alignment": {
                "type": "String",
                "label": "Alignment",
                "value": ""
                },
            "biography": {
                "type": "String",
                "label": "Biography",
                "value": bio
                },
            "class": {
                "type": "String",
                "label": "Class"
                },
            "race": {
                "type": "String",
                "label": "Race",
                "value": ""
                }
            }
        if self.isNPC():
            details.update({
                    "type": {
                        "type": "String",
                        "label": "Creature Type"
                        },
                    "environment": {
                        "type": "String",
                        "label": "Environment"
                        },
                    "cr": {
                        "type": "Number",
                        "label": "Challenge Rating",
                        "value": 1,
                        "min": 0
                        },
                    "xp": {
                        "type": "Number",
                        "label": "Kill Experience"
                        },
                    "source": {
                        "type": "Source",
                        "label": "Source Location"
                        }
                    })
        else:
            details.update({
                    "background": {
                        "type": "String",
                        "label": "Background",
                        "value": ""
                        },
                    "level": {
                        "type": "Number",
                        "label": "Character Level",
                        "value": 1,
                        "min": 1
                        },
                    "xp": {
                        "type": "Number",
                        "label": "Experience Points",
                        "value": 0,
                        "min": 0,
                        "max": 300
                        },
                    "trait": {
                        "type": "String",
                        "label": "Trait"
                        },
                    "ideal": {
                        "type": "String",
                        "label": "Ideal"
                        },
                    "bond": {
                        "type": "String",
                        "label": "Bond"
                        },
                    "flaw": {
                        "type": "String",
                        "label": "Flaw"
                        }
                    })
        return details

    def createActorSkills(self):
        return {
            "acr": {
                "type": "Number",
                "label": "Acrobatics",
                "value": 0,
                "ability": "dex"
                },
            "ani": {
                "type": "Number",
                "label": "Animal Handling",
                "value": 0,
                "ability": "wis"
                },
            "arc": {
                "type": "Number",
                "label": "Arcana",
                "value": 0,
                "ability": "int"
                },
            "ath": {
                "type": "Number",
                "label": "Athletics",
                "value": 0,
                "ability": "str"
                },
            "dec": {
                "type": "Number",
                "label": "Deception",
                "value": 0,
                "ability": "cha"
                },
            "his": {
                "type": "Number",
                "label": "History",
                "value": 0,
                "ability": "int"
                },
            "ins": {
                "type": "Number",
                "label": "Insight",
                "value": 0,
                "ability": "wis"
                },
            "itm": {
                "type": "Number",
                "label": "Intimidation",
                "value": 0,
                "ability": "cha"
                },
            "inv": {
                "type": "Number",
                "label": "Investigation",
                "value": 0,
                "ability": "int"
                },
            "med": {
                "type": "Number",
                "label": "Medicine",
                "value": 0,
                "ability": "wis"
                },
            "nat": {
                "type": "Number",
                "label": "Nature",
                "value": 0,
                "ability": "int"
                },
            "prc": {
                "type": "Number",
                "label": "Perception",
                "value": 0,
                "ability": "wis"
                },
            "prf": {
                "type": "Number",
                "label": "Performance",
                "value": 0,
                "ability": "cha"
                },
            "per": {
                "type": "Number",
                "label": "Persuasion",
                "value": 0,
                "ability": "cha"
                },
            "rel": {
                "type": "Number",
                "label": "Religion",
                "value": 0,
                "ability": "int"
                },
            "slt": {
                "type": "Number",
                "label": "Sleight of Hand",
                "value": 0,
                "ability": "dex"
                },
            "ste": {
                "type": "Number",
                "label": "Stealth",
                "value": 0,
                "ability": "dex"
                },
            "sur": {
                "type": "Number",
                "label": "Survival",
                "value": 0,
                "ability": "wis"
                }
            }
    def createActorTraits(self):
        return {
            "size": {
                "type": "String",
                "label": "Size",
                "value": "med"
                },
            "senses": {
                "type": "String",
                "label": "Senses",
                "value": ""
                },
            "perception": {
                "type": "Number",
                "label": "Passive Perception",
                "value": 0
                },
            "languages": {
                "type": "String",
                "label": "Known Languages"
                },
            "di": {
                "type": "Array",
                "label": "Damage Immunities"
                },
            "dr": {
                "type": "Array",
                "label": "Damage Resistances"
                },
            "dv": {
                "type": "Array",
                "label": "Damage Vulnerabilities"
                },
            "ci": {
                "type": "Array",
                "label": "Condition Immunities"
                }
            }
    def createActorCurrency(self):
        return {
            "pp": {
                "type": "Number",
                "label": "Platinum",
                "value": 0
                },
            "gp": {
                "type": "Number",
                "label": "Gold",
                "value": 0
                },
            "sp": {
                "type": "Number",
                "label": "Silver",
                "value": 0
                },
            "cp": {
                "type": "Number",
                "label": "Copper",
                "value": 0
                }
            }

    def createActorSpells(self):
        return {
            "spell0": {
                "type": "Number",
                "label": "Cantrip"
                },
            "spell1": {
                "type": "Number",
                "label": "1st Level"
                },
            "spell2": {
                "type": "Number",
                "label": "2nd Level"
                },
            "spell3": {
                "type": "Number",
                "label": "3rd Level"
                },
            "spell4": {
                "type": "Number",
                "label": "4th Level"
                },
            "spell5": {
                "type": "Number",
                "label": "5th Level"
                },
            "spell6": {
                "type": "Number",
                "label": "6th Level"
                },
            "spell7": {
                "type": "Number",
                "label": "7th Level"
                },
            "spell8": {
                "type": "Number",
                "label": "8th Level"
                },
            "spell9": {
                "type": "Number",
                "label": "9th Level"
                }
            }
    def createActorResources(self):
        if self.isNPC():
            return {
                "legact": {
                    "type": "Number",
                    "label": "Legendary Actions"
                    },
                "legres": {
                    "type": "Number",
                    "label": "Legendary Resistance"
                    },
                "lair": {
                    "type": "Boolean",
                    "label": "Lair Action"
                    }
                }
        else:
            return {
                "primary": {
                    "type": "String",
                    "label": "Primary Resource",
                    "sr": False,
                    "lr": False,
                    "value": 0,
                    "max": 0
                    },
                "secondary": {
                    "type": "String",
                    "label": "Secondary Resource",
                    "sr": False,
                    "lr": False,
                    "value": 0,
                    "max": 0
                    }
                }

class Scenes(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "scenes.db")
        self._pages = self._campaign["pages"]

    def getEntries(self):
        return [Scene(self, scene, index, self._campaign["playerpageid"]) for index, scene in enumerate(self._pages)]

class Scene(Entity):
    GRID_TYPES = {"square": 1, "hex": 2, "hexr": 4}
    PAD_X = 5
    PAD_Y = 5

    token_ids = {}

    def __init__(self, database, page, index, active_page):
        Entity.__init__(self, database, page["id"])
        self._page = page

        name = page["name"] if page["name"] != "" else "Untitled"
        print "Creating Scene : %s" % name
        # Snapping increment gets set to 0 if grid is disabled
        orig_grid_size = 70 * (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
        # FVTT doesn't allow grid sizes < 50, so we need to double (or triple) everything
        # if that's the case, and adjust our width/height, margins, and tile positions accordingly
        grid_size = orig_grid_size
        grid_multiplier = 1
        while grid_size < 50:
            grid_multiplier += 1
            grid_size = orig_grid_size * grid_multiplier
        # Page grid size is hardcoded to 70px in Roll20
        width = 70 * page["width"]
        height = 70 * page["height"]
        margin_left = math.ceil(width * grid_multiplier / grid_size * 0.25) * grid_size
        margin_top = math.ceil(height * grid_multiplier / grid_size * 0.25) * grid_size
        grid_type = self.GRID_TYPES[page["grid_type"]]
        if not page["showgrid"]:
            grid_type = 0
        map_layer = [g for g in page["graphics"] if g["layer"] == "map"]
        obj_layer = [g for g in page["graphics"] if g["layer"] == "objects"]
        gm_layer = [g for g in page["graphics"] if g["layer"] == "gmalyer"]
        light_layer = [g for g in page["graphics"] if g["layer"] == "walls"]

        zip_page_path = os.path.join("pages", "%03d - %s" % (index, name))
        bg = None
        bg_image = ""
        for m in map_layer:
            if m["width"] == width and m["height"] == height:
                bg = m
                if self.getArgument("use_original_image_urls", False):
                    bg_image = bg["imgsrc"]
                else:
                    filename = os.path.join(zip_page_path, "graphics", bg["id"] + ".png")
                    dest = os.path.join("scenes", "backgrounds", name + ".png")
                    (_, bg_image) = self.copyZipFile(filename, dest)
                    if bg_image == "":
                        print "Couldn't copy background image for page '%s' : %s" % (name, e)
                        bg = None
        if not bg:
            print "Page '%s' doesn't have a recognizable map background" % name

        if self.getArgument("use_original_image_urls", False):
            thumb_image = page["thumbnail"]
        else:
            filename = os.path.join(zip_page_path, "thumbnail.png")
            dest = os.path.join("scenes", "thumbs", name + ".png")
            (thumb_filename, thumb_image) = self.copyZipFile(filename, dest)
            try:
                im = Image.open(thumb_filename)
                im.thumbnail((300, 100))
                im.save(thumb_filename)
            except Exception as e:
                print "Unable to create thumbnail : %s" % e
        
        tile_id = 1
        map_tiles = []
        objects_tiles = []
        token_id = 1
        tokens = []
        wall_id = 1
        walls = []
        light_id = 1
        lights = []
        # Some graphics/paths/texts don't appear in the zorder (if drawn by other players?),
        # so let's add them at the end in the order they should appear, map, objects, gm and wall layers.
        ids_to_display = page["zorder"]
        ids_to_display.extend([i["id"] for i in self.filterItems("graphics", "map", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("graphics", "objects", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("graphics", "gmlayer", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("graphics", "walls", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("texts", "map", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("texts", "objects", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("texts", "gmlayer", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("paths", "map", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("paths", "objects", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("paths", "gmlayer", ids_to_display)])
        ids_to_display.extend([i["id"] for i in self.filterItems("paths", "walls", ids_to_display)])

        # Try to figure out wh
        door_color = None
        secret_door_color = None
        if self.getArgument("auto_doors", False) or self.getArgument("interactive", False):
            wall_colors = {}
            for zid in ids_to_display:
                path = self.findItemByID(page, zid, "paths")
                if path is None or path["layer"] != "walls":
                    continue
                wall_colors.setdefault(path["stroke"], 0)
                wall_colors[path["stroke"]] += len(path["path"]) - 1

            if len(wall_colors) > 1:
                print "In the page, walls are available in these colors : "
                for index, color in enumerate(wall_colors):
                    print "%d: %s (%d lines)" % (index + 1, color, wall_colors[color])
                print ""
                if self.getArgument("auto_doors", False):
                    lowest = None
                    second_lowest = None
                    for index, color in enumerate(wall_colors):
                        if lowest == None or wall_colors[color] < wall_colors[lowest]:
                            second_lowest = lowest
                            lowest = color
                        elif second_lowest == None or wall_colors[color] < wall_colors[second_lowest]:
                            second_lowest = color
                    door_color = lowest
                    if len(wall_colors) > 2:
                        secret_door_color = lowest
                        door_color = second_lowest
                        print "Secret door color automatically chosen as : %s" % secret_door_color
                    print "Door color automatically chosen as : %s" % door_color
                elif self.getArgument("interactive", False):
                    choice = -1
                    while choice < 0 and choice > len(wall_colors):
                        choice = raw_input("Select which color is a door (0 for none) : ")
                        try:
                            choice = int(choice)
                        except:
                            choice = -1
                    if choice > 0:
                        door_color = wall_colors.keys()[choice-1]
                    if len(wall_colors) > 2:
                        choice = -1
                        while choice < 0 and choice > len(wall_colors):
                            choice = raw_input("Select which color is a door (0 for none) : ")
                            try:
                                choice = int(choice)
                            except:
                                choice = -1
                        if choice > 0:
                            secret_door_color = wall_colors.keys()[choice-1]
                        
                

        for zid in ids_to_display:
            graphic = self.findItemByID(page, zid, "graphics")
            text = self.findItemByID(page, zid, "texts")
            path = self.findItemByID(page, zid, "paths")
            obj = graphic or text or path
            if obj is None:
                continue
            tile_image = None
            layer = obj["layer"]
            left = obj["left"]
            top = obj["top"]
            tile_width = obj["width"]
            tile_height = obj["height"]
            rotation = obj["rotation"]

            if graphic and layer != "walls" and (bg is None or graphic != bg):
                # The character might have been deleted, but the graphic still represents a token
                char_id = graphic["represents"]
                emits_light = graphic["light_otherplayers"]
                shows_name = graphic["showname"] and graphic["name"] != ""
                
                # This is a token, not a tile
                if char_id != "" or emits_light or shows_name:
                    token = Token(Entity.normalizeID(char_id), "", graphic)
                    # Redo the dim/bright depending on the token size in this map
                    token.setupLighting(graphic["light_radius"], graphic["light_dimradius"], 
                                        page["scale_number"], page["scale_units"], orig_grid_size)

                    if self.getArgument("use_original_image_urls", False):
                        token_image = graphic["imgsrc"]
                    else:
                        filename = os.path.join(zip_page_path, "graphics", graphic["id"] + ".png")
                        dest = os.path.join("scenes", "tokens", name, "token_" + str(token_id) + ".png")
                        (_, token_image) = self.copyZipFile(filename, dest)
                    token.token_filename = token_image

                    # We drop the token object and make it into the dict
                    token = token.getDict()
                    bar1_link = graphic["bar1_link"]
                    bar2_link = graphic["bar2_link"]
                    char = self.findID(char_id, "character")
                    if char:
                        hp_id = "unknown"
                        npc = True
                        for attr in char["attributes"]:
                            if attr["name"] == "hp":
                                hp_id = attr["id"]
                            elif attr["name"] == "npc":
                                npc = True if attr["current"] == "1" else False
                        if bar1_link == hp_id:
                            token["bar1"]["attribute"] = "attributes.hp"
                        if bar2_link == hp_id:
                            token["bar2"]["attribute"] = "attributes.hp"
                        token["actorLink"] = not npc
                    token["id"] = token_id
                    token["hidden"] = (layer == "gmlayer")
                    x = (left - (tile_width / 2))
                    y = (top - (tile_height / 2))
                    token["x"] = margin_left + x * grid_multiplier
                    token["y"] = margin_top + y * grid_multiplier
                    token["width"] *= grid_multiplier
                    token["height"] *= grid_multiplier
                    # Store the token id mapping for the Combat database
                    page_tokens = self.token_ids.setdefault(page["id"], {})
                    page_tokens[graphic["id"]] = token_id
                    token_id += 1
                    tokens.append(token)
                else:
                    if self.getArgument("use_original_image_urls", False):
                        tile_image = graphic["imgsrc"]
                    else:
                        filename = os.path.join(zip_page_path, "graphics", graphic["id"] + ".png")
                        dest = os.path.join("scenes", "tiles", name, "tile_" + str(tile_id) + ".png")
                        (_, tile_image) = self.copyZipFile(filename, dest)
            elif graphic and layer == "walls" and graphic["light_otherplayers"]:
                # NOTE: We ignore tokens in the dynamic layer that are not emitting light.
                (dim, bright) = Token.computeLighting(graphic["light_radius"], graphic["light_dimradius"],
                                                      tile_width, tile_height,
                                                      page["scale_number"], page["scale_units"], orig_grid_size)
                if dim > 0 or bright > 0:
                    light = {"id": light_id,
                             "flags": {},
                             "t": "l",
                             # light object get placed at the center of the graphic, so no need to calculate upper-left corner position
                             "x":  margin_left + left * grid_multiplier,
                             "y": margin_top + top * grid_multiplier,
                             "dim": dim,
                             "bright": bright
                             }
                    light_id += 1
                    lights.append(light)
            elif text and text["text"] != "":
                # NOTE: We ignore text items without any text.. there's a lot of those...
                dest = os.path.join("scenes", "tiles", name, "text_" + str(tile_id) + ".png")
                (dest_filename, tile_image) = self.getDestinationPaths(dest)
                color = self.color(text["color"], "#ffffff", True)
                (tile_width, tile_height) = self.createTextImage(text["text"], text["font_family"],
                                                       text["font_size"], color, dest_filename)
            elif path and layer != "walls":
                dest = os.path.join("scenes", "tiles", name, "path_" + str(tile_id) + ".png")
                (dest_filename, tile_image) = self.getDestinationPaths(dest)
                outline = self.color(path["stroke"], "#ffffff", True)
                fill = self.color(path["fill"], "#ffffff", True)
                line_width = path["stroke_width"]
                (drawing_width, drawing_height) = self.createPathImage(tile_width, tile_height, line_width, outline, fill,
                                                                       path["path"], dest_filename)
                tile_width = drawing_width * path["scaleX"]
                tile_height = drawing_height * path["scaleY"]
            elif path and layer == "walls":
                drawing_width = tile_width * path["scaleX"]
                drawing_height = tile_height * path["scaleY"]
                # path's left/top position is for the center of the image
                left = (left - (drawing_width / 2))
                top = (top - (drawing_height / 2))
                (polygon, circle, _, _) = self.pathToPolygonList(path["path"], 0, 0)
                if circle:
                    print "Circle in the dynamic layer! Not supported!"
                    continue
                previous_point = None
                for point in polygon:
                    # Convert x/y positions according to the scaling factor
                    point = (point[0] * path["scaleX"], point[1] * path["scaleY"])
                    if previous_point is None:
                        previous_point = point
                        continue
                    door_type = 1 if path["stroke"] == door_color else (2 if path["stroke"] == secret_door_color else 0)
                    wall = {"id": wall_id,
                            "flags": {},
                            "c": [
                            margin_left + (left + previous_point[0]) * grid_multiplier,
                            margin_top + (top + previous_point[1]) * grid_multiplier,
                            margin_left + (left + point[0]) * grid_multiplier,
                            margin_top + (top + point[1]) * grid_multiplier,
                            ],
                            "move": 1 if page["lightrestrictmove"] or self.getArgument("restrict_movement", False) else 0,
                            "sense": 1,
                            "door": door_type,
                            "t": "w",
                            "s": 0
                            }
                    wall_id += 1
                    walls.append(wall)
                    previous_point = point
                

            if tile_image:
                # graphic's left/top position is for the rotation point (center of image)
                x = (left - (tile_width / 2))
                y = (top - (tile_height / 2))
                tile = {"id": tile_id,
                        "flags": {},
                        "img": tile_image,
                        "width": tile_width * grid_multiplier,
                        "height": tile_height * grid_multiplier,
                        "scale": 1, # Also seems unused
                        "x": margin_left + x * grid_multiplier,
                        "y": margin_top + y * grid_multiplier,
                        "z": 10 * tile_id, # Z is currently unusedm the order in the list is what counts
                        "rotation": rotation,
                        "hidden": layer == "gmlayer" or layer == "walls"
                        }
                tile_id += 1
                (map_tiles if layer == "map" else objects_tiles).append(tile)
                
                    
        tiles = map_tiles + objects_tiles

        self.entity = {"_id": self._id,
                       "name": name,
                       "permission": {"default": 0},
                       "folder": Entity.normalizeID("archived-scenes-folder-id") if page["archived"] else None,
                       "flags": {"r20-page-position": page["placement"]},
                       "description": "",
                       "navigation": not page["archived"],
                       "active": active_page == page["id"],
                       "img": bg_image,
                       "thumb": thumb_image,
                       "width": width * grid_multiplier,
                       "height": height * grid_multiplier,
                       "backgroundColor": self.color(page["background_color"]),
                       "gridType": grid_type,
                       "grid": grid_size,
                       "shiftX": 0,
                       "shiftY": 0,
                       "gridColor": self.color(page["gridcolor"]),
                       "gridAlpha": page["grid_opacity"],
                       "gridDistance": page["scale_number"],
                       "gridUnits": page["scale_units"],
                       "tokenVision": page["showlighting"] and page["lightenforcelos"],
                       "fogExploration": not self.getArgument("disable_fog", False) and (self.getArgument("enable_fog", False) or page["adv_fow_enabled"]),
                       "globalLight": page["lightglobalillum"],
                       "tiles": tiles,
                       "tokens": tokens,
                       "walls": walls,
                       "lights": lights,
                       "sounds": [],
                       "templates": [],
                       "notes": []
                       }

    def filterItems(self, type, layer=None, exclude=None):
        return [i for i in self._page[type] if (layer is None or i["layer"] == layer) and (exclude is None or i["id"] not in exclude)]

    @staticmethod
    def findItemByID(page, id, type):
        for g in page[type]:
            if g["id"] == id:
                return g
        return None

    def createTextImage(self, text, font_family, font_size, color, filename):
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        try:
            font = ImageFont.truetype(font_family + ".ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()                

        size = font.getsize(text)
        size = (size[0] + self.PAD_X*2, size[1] + self.PAD_Y*2)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((self.PAD_X, self.PAD_Y), text, rgb, font=font)
        img.save(filename)
        return img.size

    # Taken from https://stackoverflow.com/questions/32504246/draw-ellipse-in-python-pil-with-line-thickness
    def draw_ellipse(self, image, bounds, width=1, outline='white', antialias=4):
        """Improved ellipse drawing function, based on PIL.ImageDraw."""

        # Use a single channel image (mode='L') as mask.
        # The size of the mask can be increased relative to the imput image
        # to get smoother looking results. 
        mask = Image.new(
            size=[int(dim * antialias) for dim in image.size],
            mode='L', color='black')
        draw = ImageDraw.Draw(mask)

        # draw outer shape in white (color) and inner shape in black (transparent)
        for offset, fill in (width/-2.0, 'white'), (width/2.0, 'black'):
            left, top = [(value + offset) * antialias for value in bounds[:2]]
            right, bottom = [(value - offset) * antialias for value in bounds[2:]]
            draw.ellipse((left, top, right, bottom), fill=fill)

        # downsample the mask using PIL.Image.LANCZOS 
        # (a high-quality downsampling filter).
        mask = mask.resize(image.size, Image.LANCZOS)
        # paste outline color to input image through the mask
        image.paste(outline, mask=mask)

    def pathToPolygonList(self, path, width, height):
        polygon = []
        (w, h) = (width, height)
        def add_point(x, y, w, h):
            w = w if w > x else math.ceil(x)
            h = h if h > y else math.ceil(y)
            polygon.append((x, y))
            return (int(w), int(h))
        circle = False
        for point in path:
            type = point[0]
            if point[0] == "M": # First Point
                (w, h) = add_point(point[1], point[2], w, h)
            elif point[0] == "L": # A line
                (w, h) = add_point(point[1], point[2], w, h)
            elif point[0] == "Q": # Freehand
                (w, h) = add_point(point[1], point[2], w, h)
                (w, h) = add_point(point[3], point[4], w, h)
            elif point[0] == "C": # Circle
                circle = True
            else:
                print "Unknown path type: %s" % str(point)
        return (polygon, circle, w, h)

    def createPathImage(self, width, height, line_width, outline, fill, path, filename):
        (polygon, circle, w, h) = self.pathToPolygonList(path, width, height)
        polygon = [(x + self.PAD_X, y + self.PAD_Y) for (x, y) in polygon]
        width = w + line_width + self.PAD_X * 2
        height = h + line_width + self.PAD_Y * 2
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if circle:
            draw.ellipse((self.PAD_X, self.PAD_Y, w, h), fill, outline)
            if outline:
                self.draw_ellipse(img, (self.PAD_X, self.PAD_Y, w, h), line_width, outline)
        else:
            if fill:
                draw.polygon(polygon, fill)
            if outline:
                draw.line(polygon, outline, line_width)
        img.save(filename)
        return img.size



class Combat(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "combat.db")

    def getEntries(self):
        encounters = []
        per_page = {}
        for order in self._campaign["turnorder"]:
            per_page.setdefault(order["_pageid"], []).append(order)
        for page in per_page:
            active = (page == self._campaign["playerpageid"])
            encounters.append(Encounter(self, "roll20-initiative-" + page, per_page[page], page, active))
        return encounters

class Encounter(Entity):
    def __init__(self, database, id, turnorder, page_id, active):
        Entity.__init__(self, database, id)
        combatants = []
        combatant_id = 1
        for token in turnorder:
            page_tokens = Scene.token_ids.get(page_id, {})
            token_id = page_tokens.get(token["id"], None)
            if token_id:
                hidden = False
                page = self.findID(page_id, "page")
                if page:
                    graphic = Scene.findItemByID(page, token["id"], "graphics")
                    hidden = (graphic and graphic["layer"] == "gmlayer")
                try:
                    initiative = float(token["pr"])
                except:
                    initiative = None
                combatants.append({"id": combatant_id,
                                   "flags": {},
                                   "tokenId": token_id,
                                   "initiative": initiative,
                                   "hidden": hidden})
                combatant_id += 1

        self.entity = {"_id": self._id,
                       "flags": {},
                       "scene": Entity.normalizeID(page_id),
                       "combatants": combatants,
                       "active": active,
                       "round":0,
                       "turn":0}

class Playlists(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "playlists.db")

    def addToFolder(self, folder_id, folder, folder_path):
        handouts = []
        index = 0
        for item in folder:
            if type(item) == dict:
                dirname = "%03d - %s" % (index, item["n"])
                handouts.extend(self.addToFolder("handout" + item["id"], item["i"], os.path.join(folder_path, dirname)))
                index += 1
            else:
                handout = self.findID(item, "handout")
                if handout != None:
                    handouts.append(Handout(self, handout, index, folder_id, folder_path))
                    index += 1
                elif self.findID(item, "character") != None:
                    index += 1
                    
        return handouts

    def getEntries(self):
        playlists = []
        root_playlist = {"id": "root-playlist",
                         "n": "Root Playlist",
                         "s": "",
                         "i": []
                         }
        root_playlist_has_items = False
        for index, item in enumerate(self._campaign["jukeboxfolder"]):
            if type(item) == dict:
                folder = "%03d - %s" % (index, item["n"])
                playlists.append(Playlist(self, item, folder))
                # Need to add empty items to keep order in the playlist for finding the files in the zip
                root_playlist["i"].append("")
            else:
                root_playlist["i"].append(item)
        if len(root_playlist["i"]) > 0:
            playlists.append(Playlist(self, root_playlist))

        return playlists

class Playlist(Entity):
    def __init__(self, database, playlist, folder_name=""):
        Entity.__init__(self, database, playlist["id"])
        modes = {"s": 1, # Shuffle
                 "a": 2, # All at once
                 "o": 0, # Play Once
                 "b": 0, # Loop
                 }
        sounds = []
        sound_id = 1
        print "creating playlist %s" % (playlist["n"])
        for index, track_id in enumerate(playlist["i"]):
            track = self.findID(track_id, "track")
            if track:
                mp3_file = "%03d - %s.mp3" % (index, track["title"])
                filename = os.path.join("jukebox", folder_name, mp3_file)
                dest = os.path.join("audio", folder_name, mp3_file)
                (_, mp3_path) = self.copyZipFile(filename, dest)
                if mp3_path != "":
                    sounds.append({"id": sound_id,
                                   "flags": {},
                                   "path": mp3_path,
                                   "repeat": track["loop"],
                                   "volume": track["volume"] / 100.0,
                                   "name": track["title"],
                                   "playing": track["playing"]
                                   })
                    sound_id += 1

        self.entity = {"_id": self._id,
                       "name": playlist["n"],
                       "permission": {"default": 0},
                       "flags": {},
                       "sounds": sounds,
                       "mode": modes.get(playlist["s"], -1), # Default to soundboard only for the root folder
                       "playing": False
                       }
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R20Converter", epilog="Convert Roll20 campaigns into Foundry VTT worlds.")
    parser.add_argument("path", metavar="destination-directory", help="The destination directory in public/worlds/")
    parser.add_argument("zip_file", metavar="exported.zip", help="The exported ZIP file from R20Exporter")
    parser.add_argument("--description", default="Imported from Roll20 using R20Converter", help="World Desription")
    parser.add_argument("--preserve-folder-order", action="store_true", help="Prefix folder names with numbers to preserve their order")
    parser.add_argument("-r", "--restrict-movement", action="store_true", help="Force all walls to restrict movement")
    parser.add_argument("--enable-fog", action="store_true", help="Enable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
    parser.add_argument("--disable-fog", action="store_true", help="Disable Fog Exploration on all Scenes with Dynamic Lighting regardless of Advanced Fog of War setting")
    parser.add_argument("--interactive", action="store_true", help="Ask questions about decisions to be made during the conversion process.")
    parser.add_argument("--use-original-image-urls", action="store_true", help="Do not copy images to the world folder but use Roll20 URL instead. (NOT recommended)")
    parser.add_argument("--auto-doors", action="store_true", help="Automatically detect doors and set them as such.")
    args = parser.parse_args()

    if os.path.exists(args.path):
        print "Destination directory must not exist"
        sys.exit(-1)

    if args.preserve_folder_order:
        print "This option is not yet supported"
        sys.exit(-1)

    if args.use_original_image_urls:
        print "*** WARNING ***"
        print "You have decided to use direct image URLs instead of copying the images to the world folder"
        print "This is NOT recommended, as you are still dependent on the assets being available on Roll 20"
        print "Also, you'd be using the servers of Roll20 but not playing on their platform which is not ethically correct"
        print "Use only this option for testing purposes for examples."
        
    converter = R20Converter(args)
    converter.convert()
        
