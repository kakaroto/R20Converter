from .base import DatabaseFile, Entity
from .actors import Token

try:
    from PIL import Image
except:
    pass

import os
import math

class PATH_TYPE:
    POLYGON = 0
    CIRCLE = 1
    RECTANGLE = 2
    FREEHAND = 3


class Scenes(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "scenes.db")
        self._pages = self._campaign["pages"]
        self.entities = self.genEntities()

    def genEntities(self):
        debug_page = self.getArgument("debug_page", None)
        if debug_page:
            debug_scene = None
            for index, page in enumerate(self._pages):
                if page["name"] == debug_page:
                    debug_scene = Scene(self, page, index, page["id"])
                    break
            return [debug_scene]
        return [Scene(self, page, index, self._campaign["playerpageid"]) for index, page in enumerate(self._pages)]

class Scene(Entity):
    GRID_TYPES = {"square": 1, "hex": 2, "hexr": 4}
    PAD_X = 5
    PAD_Y = 5

    token_ids = {}

    def __init__(self, database, page, index, active_page):
        Entity.__init__(self, database, page["id"])
        self._page = page

        name = page["name"] if page["name"] != "" else "Untitled"
        # Replace / path characters in the name to avoid issues with os.path.join
        safe_name = name.replace("/", "_").replace(os.path.sep, "_")
        # On windows, if second letter is ':' then it thinks it's a path and os.path.join will ignore the first paths
        # so os.path.join("scenes", "backgrounds", "c:my scene", "image.png") gets written in the root
        if safe_name[1:2] == ":":
            safe_name = safe_name[0] + "_" + safe_name[2:]
        print("Creating Scene : %s" % name)
        # Snapping increment gets set to 0 if grid is disabled
        orig_grid_size = 70 * (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
        # Page grid size is hardcoded to 70px in Roll20
        width = 70 * page["width"]
        height = 70 * page["height"]

        # FVTT doesn't allow grid sizes < 50, so we need to double (or triple) everything
        # if that's the case, and adjust our width/height, margins, and tile positions accordingly
        grid_size = orig_grid_size
        grid_multiplier = 1
        if grid_size < 50:
            grid_multiplier = 50.0 / orig_grid_size
            grid_size = 50

        margin_left = math.ceil(width * grid_multiplier / grid_size * 0.25) * grid_size
        margin_top = math.ceil(height * grid_multiplier / grid_size * 0.25) * grid_size
        grid_type = self.GRID_TYPES[page["grid_type"]]
        if not page["showgrid"]:
            grid_type = 0
        map_layer = [g for g in page["graphics"] if g["layer"] == "map"]

        zip_page_path = os.path.join("pages", "%03d - %s" % (index, name))
        bg = None
        bg_image = ""
        for m in map_layer:
            if self.getArgument("all_backgrounds_as_tiles", False):
                break
            if m["imgsrc"] != "" and m["width"] == width and m["height"] == height and not m["flipv"] and not m["fliph"]:
                bg = m
                if self.getArgument("use_original_image_urls", False):
                    bg_image = bg["imgsrc"]
                    break
                else:
                    filename = os.path.join(zip_page_path, "graphics", bg["id"] + ".png")
                    dest = os.path.join("scenes", "backgrounds", safe_name + ".png")
                    if self.getArgument("json", False):
                        (_, bg_image) = self.downloadResource(bg["imgsrc"], dest)
                    else:
                        (_, bg_image) = self.copyZipFile(filename, dest)
                    if bg_image == "":
                        print("Couldn't copy background image for page '%s'" % (name))
                        bg = None
                    else:
                        break
        else:
            if len(map_layer) > 0:
                print("Background does not match scene dimensions 100%. Will be set as a tile instead")

        if self.getArgument("use_original_image_urls", False):
            thumb_image = page["thumbnail"]
        else:
            filename = os.path.join(zip_page_path, "thumbnail.png")
            dest = os.path.join("scenes", "thumbs", safe_name + ".png")
            if self.getArgument("json", False):
                (thumb_filename, thumb_image) = self.downloadResource(page["thumbnail"], dest)
            else:
                (thumb_filename, thumb_image) = self.copyZipFile(filename, dest)
            try:
                im = Image.open(thumb_filename)
                im.thumbnail((300, 100))
                im.save(thumb_filename)
            except Exception as e:
                print("Unable to create thumbnail : %s" % e)
        
        map_tiles = []
        objects_tiles = []
        tokens = []
        walls = []
        lights = []
        drawings = []
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

        # Try to figure out what colors are the doors/secret doors
        door_color =  self.getArgument("door_color", None)
        secret_door_color = self.getArgument("secret_door_color", None)
        if self.getArgument("auto_doors", False) or self.getArgument("interactive", False):
            wall_colors = {}
            for zid in ids_to_display:
                path = self.findItemByID(page, zid, "paths")
                if path is None or path["layer"] != "walls":
                    continue
                wall_colors.setdefault(path["stroke"], 0)
                wall_colors[path["stroke"]] += len(path["path"]) - 1

            if len(wall_colors) > 1:
                print("In the page, walls are available in these colors : ")
                for index, color in enumerate(wall_colors):
                    print("%d: %s (%d lines)" % (index + 1, color, wall_colors[color]))
                print("")
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
                        print("Secret door color automatically chosen as : %s" % secret_door_color)
                    print("Door color automatically chosen as : %s" % door_color)
                elif self.getArgument("interactive", False):
                    choice = -1
                    while choice < 0 or choice > len(wall_colors):
                        choice = input("Select which color is a door (0 for none) : ")
                        try:
                            choice = int(choice)
                        except ValueError:
                            choice = -1
                    if choice > 0:
                        door_color = wall_colors.keys()[choice-1]
                    if len(wall_colors) > 2:
                        choice = -1
                        while choice < 0 and choice > len(wall_colors):
                            choice = input("Select which color is a door (0 for none) : ")
                            try:
                                choice = int(choice)
                            except ValueError:
                                choice = -1
                        if choice > 0:
                            secret_door_color = wall_colors.keys()[choice-1]
                        
        if self.getArgument("add_walls_around_map", False):
            positions = [
                ((0, 0), (width, 0)),
                ((width, 0), (width, height)),
                ((width, height), (0, height)),
                ((0, height), (0, 0))
            ]
            for (x0, x1) in positions:
                wall = {"_id": self.genID(),
                        "flags": {},
                        "c": [
                                int(margin_left + x0[0] * grid_multiplier),
                                int(margin_top + x0[1] * grid_multiplier),
                                int(margin_left + x1[0] * grid_multiplier),
                                int(margin_top + x1[1] * grid_multiplier),
                        ],
                        "move": 1,
                        "sense": 1,
                        "door": 0
                        }
                walls.append(wall)
                
        total_walls = len(walls)
        for zid in ids_to_display:
            graphic = self.findItemByID(page, zid, "graphics")
            text = self.findItemByID(page, zid, "texts")
            path = self.findItemByID(page, zid, "paths")
            obj = graphic or text or path
            if obj is None or (graphic is not None and graphic["imgsrc"] == ""):
                continue
            tile_image = None
            layer = obj["layer"]
            left = obj["left"]
            top = obj["top"]
            tile_width = obj["width"]
            tile_height = obj["height"]
            rotation = obj["rotation"]
            tiles = (map_tiles if layer == "map" else objects_tiles)

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
                        dest = os.path.join("scenes", "tokens", safe_name, "token_" + str(len(tokens)) + ".png")
                        if self.getArgument("json", False):
                            (_, token_image) = self.downloadResource(graphic["imgsrc"], dest)
                        else:
                            (_, token_image) = self.copyZipFile(filename, dest)
                    token.token_filename = token_image

                    # We drop the token object and make it into the dict
                    token = token.getDict()
                    bar1_link = graphic["bar1_link"]
                    bar2_link = graphic["bar2_link"]
                    char = self.findID(char_id, "character")
                    if char:
                        hp_id = "unknown"
                        npc = False
                        for attr in char["attributes"]:
                            if attr["name"] == "hp":
                                hp_id = attr["id"]
                            elif attr["name"] == "npc":
                                npc = True if attr["current"] == "1" else False
                        if bar1_link == hp_id or self.getArgument("force_hp_for_token_bar1", False):
                            token["bar1"]["attribute"] = "attributes.hp"
                        if bar2_link == hp_id or self.getArgument("force_hp_for_token_bar2", False):
                            token["bar2"]["attribute"] = "attributes.hp"
                        token["actorLink"] = not npc
                    token["_id"] = self.genID()
                    token["hidden"] = (layer == "gmlayer")
                    x = (left - (tile_width / 2))
                    y = (top - (tile_height / 2))
                    token["x"] = margin_left + x * grid_multiplier
                    token["y"] = margin_top + y * grid_multiplier
                    # Token size is in grid units, so we use snapping_increment instead of grid_multiplier
                    token["width"] = token["width"] / (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
                    token["height"] = token["height"] / (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
                    # Store the token id mapping for the Combat database
                    page_tokens = self.token_ids.setdefault(page["id"], {})
                    page_tokens[graphic["id"]] = token["_id"]
                    if not self._needsCleanup(x, y, tile_width, tile_height, width, height):
                        tokens.append(token)
                else:
                    if self.getArgument("use_original_image_urls", False):
                        tile_image = graphic["imgsrc"]
                    else:
                        filename = os.path.join(zip_page_path, "graphics", graphic["id"] + ".png")
                        if self.isDrawing(graphic):
                            basename = "drawing_" + str(len(drawings))
                        else:
                            basename = "tile_" + str(len(tiles))
                        dest = os.path.join("scenes", "tiles", safe_name, basename + ".png")
                        if self.getArgument("json", False):
                            (_, tile_image) = self.downloadResource(graphic["imgsrc"], dest)
                        else:
                            (_, tile_image) = self.copyZipFile(filename, dest)
            elif graphic and layer == "walls" and graphic["light_otherplayers"]:
                # NOTE: We ignore tokens in the dynamic layer that are not emitting light.
                (dim, bright) = Token.computeLighting(graphic["light_radius"], graphic["light_dimradius"],
                                                      tile_width, tile_height,
                                                      page["scale_number"], page["scale_units"], orig_grid_size)
                if dim > 0 or bright > 0:
                    try:
                        angle = int(graphic["light_angle"])
                        if angle == 0:
                            angle = 360
                    except:
                        angle = 360
                    try:
                        rotation = graphic["rotation"]
                    except:
                        rotation = 0
                    if angle != 360:
                        rotation = (rotation + 180) % 360
                    light = {"_id": self.genID(),
                             "flags": {},
                             "t": "l",
                             # light object get placed at the center of the graphic
                             "x": int(margin_left + left * grid_multiplier),
                             "y": int(margin_top + top * grid_multiplier),
                             "dim": dim,
                             "bright": bright,
                             "angle": angle,
                             "rotation": rotation
                             }
                    x = (left - (tile_width / 2))
                    y = (top - (tile_height / 2))
                    # Check if light spills into the scene even if the graphic itself is outside of it
                    if not self._needsCleanup(x, y, tile_width, tile_height, width, height):
                        lights.append(light)
            elif text and text["text"].strip() != "":
                # NOTE: We ignore text items without any text.. there's a lot of those...
                # graphic's left/top position is for the rotation point (center of image)
                x = (left - (tile_width / 2))
                y = (top - (tile_height / 2))
                # Drawing author can't be null or empty string, so give an invalid id instead
                drawing = {"_id": self.genID(),
                            "flags": {},
                            "x": int(margin_left + x * grid_multiplier),
                            "y": int(margin_top + y * grid_multiplier),
                            "z": 10 * len(drawings),
                            "width": int(tile_width * grid_multiplier),
                            "height": int(tile_height * grid_multiplier),
                            "rotation": rotation,
                            "hidden": layer == "gmlayer" or layer == "walls",
                            "locked": layer == "map",
                            "author": Entity.normalizeID(text["controlledby"]) or "GM"
                }
                drawing = self.createTextDrawing(drawing, text)
                drawings.append(drawing)
            elif path and layer != "walls":
                tile_width = tile_width * path["scaleX"]
                tile_height = tile_height * path["scaleY"]
                x = (left - (tile_width / 2))
                y = (top - (tile_height / 2))
                drawing = {"_id": self.genID(),
                            "flags": {},
                            "x": int(margin_left + x * grid_multiplier),
                            "y": int(margin_top + y * grid_multiplier),
                            "z": 10 * len(drawings),
                            "width": int(tile_width * grid_multiplier),
                            "height": int(tile_height * grid_multiplier),
                            "rotation": rotation,
                            "hidden": layer == "gmlayer" or layer == "walls",
                            "locked": layer == "map",
                            "author": Entity.normalizeID(path["controlledby"]) or "GM"
                }
                drawing = self.createPathDrawing(drawing, path)
                drawings.append(drawing)
            elif path and layer == "walls":
                drawing_width = tile_width * path["scaleX"]
                drawing_height = tile_height * path["scaleY"]
                # path's left/top position is for the center of the image
                left = (left - (drawing_width / 2))
                top = (top - (drawing_height / 2))
                (polygon, path_type, _, _) = self.pathToPolygonList(path["path"], 0, 0)
                if path_type == PATH_TYPE.CIRCLE:
                    print("Circle in the dynamic layer! Not supported!")
                    continue
                previous_point = None
                previous_point_idx = 0
                total_walls += len(polygon) - 1
                for point_idx, point in enumerate(polygon):
                    # Convert x/y positions according to the scaling factor
                    point = (point[0] * path["scaleX"], point[1] * path["scaleY"])
                    if previous_point is None:
                        previous_point = point
                        previous_point_idx = point_idx
                        continue
                    # Finally, the Pythagore theorem from school is useful in real life
                    wall_length = math.sqrt(math.pow(point[0] - previous_point[0], 2) + math.pow(point[1] - previous_point[1], 2))
                    min_angle = 180.0 - self.getArgument("maximum_wall_angle")
                    #print("Wall length : %.2f" % wall_length)
                    if wall_length < self.getArgument("minimum_wall_length", 0):
                        #print("Wall is too small, skipping.")
                        next_idx = point_idx + 1
                        # Don't skip if it's the last point of the polygon
                        if next_idx != len(polygon):
                            next_point = polygon[next_idx]
                            angles = []
                            for idx in range(previous_point_idx + 1, point_idx+1):
                                old_point = (polygon[idx][0] * path["scaleX"], polygon[idx][1] * path["scaleY"])
                                angles.append(self.getPointsAngle(previous_point, old_point, next_point))
                            if min(angles) >= min_angle:
                                continue
                    door_type = 1 if path["stroke"] == door_color else (2 if path["stroke"] == secret_door_color else 0)
                    wall_a = [left + previous_point[0],
                                top + previous_point[1]]
                    wall_b = [left + point[0],
                                top + point[1]]
                    wall = {"_id": self.genID(),
                            "flags": {},
                            "c": [
                                    int(margin_left + wall_a[0] * grid_multiplier),
                                    int(margin_top + wall_a[1] * grid_multiplier),
                                    int(margin_left + wall_b[0] * grid_multiplier),
                                    int(margin_top + wall_b[1] * grid_multiplier),
                            ],
                            "move": 1 if page["lightrestrictmove"] or self.getArgument("restrict_movement", False) else 0,
                            "sense": 1,
                            "door": door_type
                            }
                    if door_type != 0:
                        wall["ds"] = 0
                    wall_x = min(wall_a[0], wall_b[0])
                    wall_y = min(wall_a[1], wall_b[1])
                    wall_width = max(wall_a[0], wall_b[0]) - wall_x
                    wall_height = max(wall_a[1], wall_b[1]) - wall_y
                    if not self._needsCleanup(wall_x, wall_y, wall_width, wall_height, width, height):
                        walls.append(wall)
                    previous_point = point
                    previous_point_idx = point_idx
                

            if tile_image:
                # graphic's left/top position is for the rotation point (center of image)
                x = (left - (tile_width / 2))
                y = (top - (tile_height / 2))
                if not self._needsCleanup(x, y, tile_width, tile_height, width, height):
                    if self.isDrawing(graphic):
                        drawing = {"_id": self.genID(),
                                    "flags": {
                                        "furnace": {
                                            "fillType": 3,
                                            "textureAlpha": 1,
                                            "mirrorVert": obj["flipv"],
                                            "mirrorHoriz": obj["fliph"],
                                        }
                                    },
                                    "x": int(margin_left + x * grid_multiplier),
                                    "y": int(margin_top + y * grid_multiplier),
                                    "z": 10 * len(drawings),
                                    "width": int(tile_width * grid_multiplier),
                                    "height": int(tile_height * grid_multiplier),
                                    "rotation": rotation,
                                    "hidden": layer == "gmlayer" or layer == "walls",
                                    "locked": layer == "map",
                                    "author": Entity.normalizeID(obj["controlledby"]) or "GM", # invalid user (or export-as-module) will be invalid author, which means all GM
                                    "type": "r",
                                    "fillType": 2,
                                    "fillColor": "#ffffff",
                                    "fillAlpha": 0,
                                    "strokeColor": "#ffffff",
                                    "strokeAlpha": 0,
                                    "strokeWidth": 0,
                                    "texture": tile_image,
                                    "fontFamily": "Signika",
                                    "fontSize": 45,
                                    "text": "",
                                    "textAlpha": 1,
                                    "textColor": "#ffffff",
                                    "bezierFactor": 0,
                                    "points": [],
                                }
                        drawings.append(drawing)
                    else:
                        if graphic["flipv"]:
                            y = y + tile_height
                            tile_height *= -1
                        if graphic["fliph"]:
                            x = x + tile_width
                            tile_width *= -1
                        tile = {"_id": self.genID(),
                                "flags": {},
                                "img": tile_image,
                                "width": int(tile_width * grid_multiplier),
                                "height": int(tile_height * grid_multiplier),
                                "scale": 1, # Also seems unused
                                "x": int(margin_left + x * grid_multiplier),
                                "y": int(margin_top + y * grid_multiplier),
                                "z": 10 * len(tiles),
                                "rotation": rotation,
                                "locked": layer == "map",
                                "hidden": layer == "gmlayer" or layer == "walls"
                                }
                        tiles.append(tile)
                
                    
        if len(walls) != total_walls:
            print("With a minimum wall length of %d pixels and a maximum angle between continuous walls of %d degrees, the total number of walls was decreased from %d to %d walls." % (self.getArgument("minimum_wall_length", 0), self.getArgument("maximum_wall_angle", 0), total_walls, len(walls)))
        tiles = map_tiles + objects_tiles

        folder = None
        if page["archived"] and not self.getArgument("disable_archived", False):
            folder = "archived-scenes-folder-id"
        if self.getArgument("export_as_module", False):
            folder = None
        self.entity = {"_id": self._id,
                       "name": name,
                       "permission": {"default": 0},
                       "folder": Entity.normalizeID(folder),
                       "flags": {},
                       "sort": page.get("placement", 0) * Entity.SORT_ORDER,
                       "navOrder": page.get("placement", 0),
                       "description": "",
                       "navigation": not page["archived"],
                       "active": active_page == page["id"],
                       "img": bg_image,
                       "initial": None,
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
                       "gridDistance": page["scale_number"] if float(page["scale_number"]) >= 1 else 1,
                       "gridUnits": page["scale_units"] if float(page["scale_number"]) >= 1 else ("(" + str(page["scale_number"]) + " " + page["scale_units"] + ")"),
                       "tokenVision": page["showlighting"] and page["lightenforcelos"],
                       "fogExploration": not self.getArgument("disable_fog", False) and (self.getArgument("enable_fog", False) or page["adv_fow_enabled"]),
                       "globalLight": page["lightglobalillum"],
                       "tiles": tiles,
                       "tokens": tokens,
                       "walls": walls,
                       "lights": lights,
                       "drawings": drawings,
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

    def _needsCleanup(self, x, y, obj_width, obj_height, width, height):
        if not self.getArgument("cleanup_scenes", False):
            return False
        if x + obj_width < 0 or x > width or y + obj_height < 0 or y > height:
            return True
        return False

    def isDrawing(self, graphic):
        if self.getArgument("images_as_drawings", False):
            return True
        return False

    def pathToPolygonList(self, path, width, height):
        polygon = []
        (w, h) = (width, height)
        def add_point(x, y, w, h):
            w = w if w > x else math.ceil(x)
            h = h if h > y else math.ceil(y)
            polygon.append((x, y))
            return (int(w), int(h))
        path_type = PATH_TYPE.POLYGON
        for point in path:
            if point[0] == "M": # First Point
                (w, h) = add_point(point[1], point[2], w, h)
            elif point[0] == "L": # A line
                (w, h) = add_point(point[1], point[2], w, h)
            elif point[0] == "Q": # Freehand
                (w, h) = add_point(point[1], point[2], w, h)
                (w, h) = add_point(point[3], point[4], w, h)
                path_type = PATH_TYPE.FREEHAND
            elif point[0] == "C": # Circle
                path_type = PATH_TYPE.CIRCLE
            else:
                print("Unknown path type: %s" % str(point))
        if path_type == PATH_TYPE.POLYGON and len(path) == 5 and \
            path[0][1] == 0 and path[0][2] == 0 and \
            path[1][1] == width and path[1][2] == 0 and \
            path[2][1] == width and path[2][2] == height and \
            path[3][1] == 0 and path[3][2] == height and \
            path[4][1] == 0 and path[4][2] == 0:
            path_type = PATH_TYPE.RECTANGLE
        return (polygon, path_type, w, h)

    # Get angle between points P1, P2, P3 with the angle at P2 being returned in degrees
    def getPointsAngle(self, p1, p2, p3):
        # Let's do some trigonometry! the law of cosinus: c^2 = a^2 + b^2 - 2ab*cos(C)
        a = math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))
        b = math.sqrt(math.pow(p2[0] - p3[0], 2) + math.pow(p2[1] - p3[1], 2))
        c = math.sqrt(math.pow(p1[0] - p3[0], 2) + math.pow(p1[1] - p3[1], 2))
    	#print("Points : (%.2f, %.2f) - (%.2f, %.2f) - (%.2f, %.2f)" % (p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]))
        #print("Lengths : %.2f - %.2f - %2.f" % (a, b, c))
        # Now to get the angle : C = acos((a^2 + b^2 - c^2) / 2ab)
        if a == 0 or b == 0:
            # Avoid a division by 0
            angle = 180
        else:
            # Looks like we need to clamp it to [-1, 1] because of floating point rounding, I got a -1.00000000004 once which gave "math domain error" exception
            cos_c = (math.pow(a, 2) + math.pow(b, 2) - math.pow(c, 2)) / (2 * a * b)
            clamped = min(max(cos_c, -1), 1)
            angle = math.degrees(math.acos(clamped))
        #print("Angle is : %.2f" % angle )
        return angle

    def createTextDrawing(self, drawing, text):
        color = self.color(text["color"], "#ffffff", True)
        drawing.update({"type": "t",
                        "fillType": 1,
                        "fillColor": color,
                        "fillAlpha": 1.0,
                        "strokeColor": "#000000",
                        "strokeAlpha": 1.0,
                        "strokeWidth": 1,
                        "texture": None,
                        "fontFamily": text["font_family"],
                        "fontSize": text["font_size"],
                        "text": text["text"],
                        "textAlpha": 1,
                        "textColor": color,
                        "bezierFactor": 0,
                        "points": [],
                    })
        return drawing

    def createPathDrawing(self, drawing, path):
        outline = self.color(path["stroke"], "#ffffff", True)
        fill = self.color(path["fill"], "#ffffff", True)
        line_width = path["stroke_width"]
        scaleX = path["scaleX"]
        scaleY = path["scaleY"]
        (points, path_type, _, _) = self.pathToPolygonList(path["path"], path["width"], path["height"])
        if path_type == PATH_TYPE.CIRCLE:
            drawing_type = "e"
            points = []
        elif path_type == PATH_TYPE.RECTANGLE:
            drawing_type = "r"
            points = []
        elif path_type == PATH_TYPE.FREEHAND:
            drawing_type = "f"
        else:
            drawing_type = "p"

        if scaleX != 1 or scaleY != 1:
            points = [(x * scaleX, y * scaleY) for (x, y) in points]

        drawing.update({"type": drawing_type,
                        "fillType": 0 if fill is None else 1,
                        "fillColor": fill,
                        "fillAlpha": 1.0,
                        "strokeColor": outline,
                        "strokeAlpha": 1.0,
                        "strokeWidth": line_width,
                        "texture": None,
                        "fontFamily": "Signika",
                        "fontSize": 45,
                        "text": "",
                        "textAlpha": 1,
                        "textColor": "#ffffff",
                        "bezierFactor": 0.5 if drawing_type == "f" else 0,
                        "points": points,
                    })
        return drawing