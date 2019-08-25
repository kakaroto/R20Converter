from .base import DatabaseFile, Entity
from .actors import Token

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import os
import math



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

        if grid_multiplier * width > 10000 or grid_multiplier * height > 10000:
            print("******** WARNING ***********")
            print("Your scene has a size of over 10k pixels in one dimension")
            print("It will most probably not work properly in FVTT until 0.3.1 is released")
            print("")

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
            if m["imgsrc"] != "" and m["width"] == width and m["height"] == height:
                bg = m
                if self.getArgument("use_original_image_urls", False):
                    bg_image = bg["imgsrc"]
                else:
                    filename = os.path.join(zip_page_path, "graphics", bg["id"] + ".png")
                    dest = os.path.join("scenes", "backgrounds", name + ".png")
                    if self.getArgument("json", False):
                        (_, bg_image) = self.downloadResource(bg["imgsrc"], dest)
                    else:
                        (_, bg_image) = self.copyZipFile(filename, dest)
                    if bg_image == "":
                        print("Couldn't copy background image for page '%s'" % (name))
                        bg = None
        if not bg:
            print("Background does not match scene dimensions 100%. Will be set as a tile instead")

        if self.getArgument("use_original_image_urls", False):
            thumb_image = page["thumbnail"]
        else:
            filename = os.path.join(zip_page_path, "thumbnail.png")
            dest = os.path.join("scenes", "thumbs", name + ".png")
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
                wall = {"id": wall_id,
                        "flags": {},
                        "c": [
                                margin_left + x0[0] * grid_multiplier,
                                margin_top + x0[1] * grid_multiplier,
                                margin_left + x1[0] * grid_multiplier,
                                margin_top + x1[1] * grid_multiplier,
                        ],
                        "move": 1,
                        "sense": 1,
                        "door": 0,
                        "t": "w",
                        "s": 0
                        }
                wall_id += 1
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
                    # Token size is in grid units, so we use snapping_increment instead of grid_multiplier
                    token["width"] = token["width"] / (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
                    token["height"] = token["height"] / (page["snapping_increment"] if page["snapping_increment"] > 0 else 1)
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
                    light = {"id": light_id,
                             "flags": {},
                             "t": "l",
                             # light object get placed at the center of the graphic, so no need to calculate upper-left corner position
                             "x": margin_left + left * grid_multiplier,
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
                self.createTextImage(text["text"], text["font_family"], text["font_size"], color, dest_filename)
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
                    if door_type != 0:
                        wall["ds"] = 0
                    wall_id += 1
                    walls.append(wall)
                    previous_point = point
                    previous_point_idx = point_idx
                

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
                
                    
        if len(walls) != total_walls:
            print("With a minimum wall length of %d pixels and a maximum angle between continuous walls of %d degrees, the total number of walls was decreased from %d to %d walls." % (self.getArgument("minimum_wall_length", 0), self.getArgument("maximum_wall_angle", 0), total_walls, len(walls)))
        tiles = map_tiles + objects_tiles

        folder = None
        if page["archived"] and not self.getArgument("disable_archived", False):
            folder = "archived-scenes-folder-id"
        self.entity = {"_id": self._id,
                       "name": name,
                       "permission": {"default": 0},
                       "folder": Entity.normalizeID(folder),
                       "flags": {"R20Converter":
                                     {"page-position": page.get("placement", 0)},
                                 "entityorder": {"order": page.get("placement", 0)}},
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
                       "gridDistance": page["scale_number"] if float(page["scale_number"]) >= 1 else 1,
                       "gridUnits": page["scale_units"] if float(page["scale_number"]) >= 1 else ("(" + str(page["scale_number"]) + " " + page["scale_units"] + ")"),
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
        # Don't know why they added a quote around the font family name for shadows into light
        font_family = font_family.replace("\"", "")
        # If running from the windows directory alone, there won't be a 'src' directory anymore
        parent = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if not os.path.exists(os.path.join(parent, "fonts")):
            parent = os.path.abspath(os.path.join(parent, ".."))
        font_dir = os.path.join(parent, "fonts")
        try:
            try:
                # Check if the text is ASCII, otherwise, if it has unicode characters, default back to LiberationSans
                text.encode('ascii')
                is_unicode = False
            except UnicodeEncodeError:
                is_unicode = True
            if font_family == "Arial" or is_unicode:
                font_family = "LiberationSans-Regular"
            font = ImageFont.truetype(os.path.join(font_dir, font_family + ".ttf"), font_size)
            #print("Loaded font ", font_family)
        except:
            #print("Error loading font ", font_family)
            try:
                font = ImageFont.truetype(os.path.join(font_dir, "LiberationSans-Regular.ttf"), font_size)
            except:
                font = ImageFont.load_default()
                print("Error loading fonts. Loading default font!")

        size = font.getsize(text)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw_size = draw.textsize(text, font=font)
        if draw_size != size:
            img = Image.new("RGBA", draw_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

        draw.text((0, 0), text, rgb, font=font)
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
                print("Unknown path type: %s" % str(point))
        return (polygon, circle, w, h)

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
