#!/usr/bin/python

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
        Folders(self, self.args.preserve_folder_order).save()
        Journal(self).save()
        Scenes(self).save()

        EmptyDB(self, "sessions").save()
        EmptyDB(self, "combat").save()
        EmptyDB(self, "settings").save()
        EmptyDB(self, "chat").save()
        EmptyDB(self, "playlists").save()
        EmptyDB(self, "items").save()

        EmptyDB(self, "actors").save()


class DatabaseFile(object):
    def __init__(self, converter, filename):
        self._converter = converter
        self._path = converter.path
        self._filename = filename
        self._campaign = converter.campaign

    def findID(self, id, where=None):
        return self._converter.findID(id, where)

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
        url = urllib.pathname2url(filename.replace(" ", "_"))
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
    
    def copyImage(self, file, destination):
        (dest_filename, config_path) = self.getDestinationPaths(destination)
        with open(dest_filename, "wb") as f:
            f.write(file.read())
        return (dest_filename, config_path)

    def copyZipImage(self, filename, destination):
        zipfile = self._database._converter.getZipFile(filename)
        return self.copyImage(zipfile, destination)

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
    def __init__(self, converter, preserve_order):
        DatabaseFile.__init__(self, converter, "folders.db")
        self._preserve_order = preserve_order
        
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
            filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
            (_, avatar_filename) = self.copyZipImage(filename, filename)
        self.entity = {"_id": self._id,
                       "name": handout["name"],
                       "permission": permissions,
                       "folder": Entity.normalizeID(parent),
                       "flags":{"r20-handout-order" : index, "r20-handout-archived": handout["archived"]},
                       "entryTime": 0,
                       "content": content,
                       "img": avatar_filename
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

    def __init__(self, database, page, index, active_page):
        Entity.__init__(self, database, page["id"])
        name = page["name"] if page["name"] != "" else "Untitled"
        # Snapping increment gets set to 0 if grid is disabled
        orig_grid_size = 70 * (page["snapping_increment"] if page["showgrid"] else 1)
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
                filename = os.path.join(zip_page_path, "graphics", bg["id"] + ".png")
                dest = os.path.join("scenes", "backgrounds", name + ".png")
                try:
                    (_, bg_image) = self.copyZipImage(filename, dest)
                except Exception as e:
                    print "Couldn't copy background image for page '%s' : %s" % (name, e)
                    bg_image = bg["imgsrc"]
                    bg = None
                break
        if not bg:
            print "Page '%s' doesn't have a recognizable map background" % name

        filename = os.path.join(zip_page_path, "thumbnail.png")
        dest = os.path.join("scenes", "thumbs", name + ".png")
        (thumb_filename, thumb_image) = self.copyZipImage(filename, dest)
        im = Image.open(thumb_filename)
        im.thumbnail((300, 100))
        im.save(thumb_filename)
        
        tile_id = 1
        map_tiles = []
        objects_tiles = []
        token_id = 1
        tokens = []
        wall_id = 1
        walls = []
        light_id = 1
        lights = []
        for zid in page["zorder"]:
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

            if graphic:
                # If reprents, then it's a token, not a tile
                filename = os.path.join(zip_page_path, "graphics", graphic["id"] + ".png")
                dest = os.path.join("scenes", "tiles", name, "tile_" + str(tile_id) + ".png")
                (_, tile_image) = self.copyZipImage(filename, dest)
            elif text and text["text"] != "":
                dest = os.path.join("scenes", "tiles", name, "text_" + str(tile_id) + ".png")
                (dest_filename, tile_image) = self.getDestinationPaths(dest)
                color = self.color(text["color"], "#ffffff", True)
                (tile_width, tile_height) = self.createTextImage(text["text"], text["font_family"],
                                                       text["font_size"], color, dest_filename)
            elif path and layer != "walls":
                drawing_width = tile_width / path["scaleX"]
                drawing_height = tile_height / path["scaleY"]
                dest = os.path.join("scenes", "tiles", name, "path_" + str(tile_id) + ".png")
                (dest_filename, tile_image) = self.getDestinationPaths(dest)
                outline = self.color(path["stroke"], "#ffffff", True)
                fill = self.color(path["fill"], "#ffffff", True)
                line_width = path["stroke_width"]
                (drawing_width, drawing_height) = self.createPathImage(drawing_width, drawing_height, line_width, outline, fill,
                                                                       path["path"], dest_filename)
                tile_width = drawing_width * path["scaleX"]
                tile_height = drawing_height * path["scaleY"]
            elif path and layer == "walls":
                drawing_width = tile_width / path["scaleX"]
                drawing_height = tile_height / path["scaleY"]
                # path's left/top position is for the center of the image
                left = (left - (tile_width / 2))
                top = (top - (tile_height / 2))
                (polygon, circle, _, _) = self.pathToPolygonList(path["path"], 0, 0)
                if circle:
                    print "Circle in the dynamic layer! Not supported!"
                    continue
                previous_point = None
                for point in polygon:
                    if previous_point is None:
                        previous_point = point
                        continue
                    wall = {"id": wall_id,
                            "flags": {},
                            "c": [
                            margin_left + (left + previous_point[0]) * grid_multiplier,
                            margin_top + (top + previous_point[1]) * grid_multiplier,
                            margin_left + (left + point[0]) * grid_multiplier,
                            margin_top + (top + point[1]) * grid_multiplier,
                            ],
                            "move": page["lightrestrictmove"],
                            "sense": 1,
                            "door": 0,
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
                       "fogExploration": page["adv_fow_enabled"],
                       "globalLight": page["lightglobalillum"],
                       "tiles": tiles,
                       "tokens": tokens,
                       "walls": walls,
                       "lights": lights,
                       "sounds": [],
                       "templates": [],
                       "notes": []
                       }

    def findItemByID(self, page, id, type):
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R20Converter", epilog="Convert Roll20 campaigns into Foundry VTT worlds.")
    parser.add_argument("path", metavar="destination-directory", help="The destination directory in public/worlds/")
    parser.add_argument("zip_file", metavar="exported.zip", help="The exported ZIP file from R20Exporter")
    parser.add_argument("--description", default="Imported from Roll20 using R20Converter", help="World Desription")
    parser.add_argument("--preserve-folder-order", action="store_true", help="Prefix folder names with numbers to preserve their order")
    args = parser.parse_args()

    if os.path.exists(args.path):
        print "Destination directory must not exist"
        sys.exit(-1)

    if args.preserve_folder_order:
        print "This option is not yet supported"
        sys.exit(-1)
        
    converter = R20Converter(args)
    converter.convert()
        
