from .base import DatabaseFile, Entity
from .journal import Handout
from .items import *
from collections import OrderedDict
import re
import os
import copy
import math

DISPLAY_ATTRIBUTES = False

class Actors(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "actors.db")
        self._characters = self._campaign["characters"]
        self.entities = self.genEntities()

    def genEntities(self):
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
        self.token_filename = ""
        # Grid size in Roll20 is hardcoded to 70x70
        self.width = 70
        self.height = 70
        self.rotation = 0
        show_name = True
        all_see_name = False
        all_see_bar1 = False
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
        self.has_vision = False
        self.light_alpha = 1
        self.light_angle = 0
        self.sight_angle = 0
        self.light_color = ""
        self.mirrorX = False
        self.mirrorY = False
        self.tint = None

        if token:
            self.token_name = token.get("name", self.token_name)
            self.token_filename = token.get("imgsrc", self.token_filename)
            show_name = token.get("showname", show_name)
            all_see_name = token.get("showplayers_name", all_see_name)
            def parseInt(name, default):
                try:
                    val = token.get(name, default)
                    return int(val)
                except:
                    return default
            self.width = parseInt("width", self.width)
            self.height = parseInt("height", self.height)
            # Minimum width/height in Foundry is 0.1 so we can't have a width/height less than 10% of the 70 grid
            if self.width < 7:
                self.width = 7
            if self.height < 7:
                self.height = 7
            self.rotation = parseInt("rotation", self.rotation)
            self.bar1_val = parseInt("bar1_value", self.bar1_val)
            self.bar1_max = parseInt("bar1_max", self.bar1_max)
            self.bar2_val = parseInt("bar2_value", self.bar2_val)
            self.bar2_max = parseInt("bar2_max", self.bar2_max)
            all_see_bar1 = token.get("showplayers_bar1", all_see_bar1)
            all_see_bar2 = token.get("showplayers_bar2", all_see_bar2)
            (ldimradius, lradius) = self.getLightRadius(token)
            self.has_vision = self.hasSight(token)
            self.light_angle = self.lightAngle(token)
            self.sight_angle = self.sightAngle(token)
            self.light_color = self.lightColor(token)
            self.light_alpha = self.lightOpacity(token)
            self.setupLighting(lradius, ldimradius)
            self.mirrorX = bool(token.get("fliph", self.mirrorX))
            self.mirrorY = bool(token.get("flipv", self.mirrorY))
            self.tint = self.color(token.get("tint_color", "transparent"), None, True)

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
        (dim, bright) = self.computeLighting(light_radius, light_dimradius, self.width, self.height, scale, scale_units, grid_size)
        if self.emitsLight(self._token):
            self.emits_light = True
            self.emits_dim_light = dim
            self.emits_bright_light = bright
        legacy = self._token.get("legacy_lighting_enabled", True)
        if legacy:
            multiplier = self._token.get("light_multiplier", 1)
            try:
                multiplier = float(multiplier)
            except:
                multiplier = 1
        else:
            multiplier = 1
        self.dim_sight = dim * multiplier
        self.bright_sight = bright * multiplier
        # But if you have sight but no vision, then FVTT won't show you anything, even if
        # you're next to a bright source of light, so we set dim sight to 1 ft in that case
        if self.dim_sight == 0 and self.bright_sight == 0 and self.hasSight(self._token):
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
                    token_radius = float(scale) * token_radius / grid_size
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

    @staticmethod
    def hasSight(token):
        legacy = token.get("legacy_lighting_enabled", True)
        if legacy:
            return token.get("light_hassight", False)
        else:
            return token.get("has_low_light_vision", False) or token.get("has_bright_light_vision", False)

    @staticmethod
    def sightAngle(token):
        legacy = token.get("legacy_lighting_enabled", True)
        angle = 0
        if legacy:
            angle = token.get("light_losangle", angle)
        else:
            if token.get("has_limit_field_of_vision", False):
                angle = token.get("limit_field_of_vision_total", angle)
            else:
                return 0
        
        try:
            return int(angle)
        except:
            return 0

    @staticmethod
    def emitsLight(token):
        legacy = token.get("legacy_lighting_enabled", True)
        if legacy:
            return token.get("light_otherplayers", False)
        else:
            return token.get("emits_low_light", False) or token.get("emits_bright_light", False)

    @staticmethod
    def lightAngle(token):
        legacy = token.get("legacy_lighting_enabled", True)
        angle = 0
        if legacy:
            angle = token.get("light_angle", 0)
        else:
            if token.get("has_directional_bright_light", False):
                angle = token.get("directional_bright_light_total", 0)
            else:
                return 0
        try:
            return int(angle)
        except:
            return 0

    @staticmethod
    def lightColor(token):
        return token.get("lightColor", "transparent")

    @staticmethod
    def lightOpacity(token):
        return token.get("dim_light_opacity", 1)

    @staticmethod
    def getLightRadius(token):
        legacy = token.get("legacy_lighting_enabled", True)
        if legacy:
            lradius = token.get("light_radius", 0)
            dradius = token.get("light_dimradius", 0)
        else:
            lradius = 0
            dradius = 0
            if token.get("emits_low_light", False):
                dradius = token.get("low_light_distance", 0)
            if token.get("emits_bright_light", False):
                lradius = token.get("bright_light_distance", 0)
        try:
            lradius = float(lradius)
        except ValueError:
            lradius = 0
        try:
            dradius = float(dradius)
        except ValueError:
            dradius = 0
        return (dradius, lradius)

    def getDict(self):
        # Roll20 light/sight angles are going downward, FVTT's are going upward... do some magic
        if self.sight_angle != 0 or self.light_angle != 0:
            rotation = (self.rotation + 180) % 360
            lockRotation = (self.rotation == 0)
        else:
            rotation = self.rotation
            lockRotation = False
        if rotation == 360:
            rotation = 0

        def roundTenthStep(v):
            return int(v * 10) / 10
        img = self.token_filename if self.token_filename != "" else "icons/svg/mystery-man.svg"
        # Use proper icon for torches
        if self._token and ((img == "/images/editor/torch.svg") or (img == "icons/svg/mystery-man.svg" and self._token.get("imgsrc", "") == "/images/editor/torch.svg")):
            img = "icons/svg/fire.svg"
        return {"flags": {},
                "name": self.token_name or "Unnamed token",
                "displayName": self.display_name,
                "img": img,
                "width": roundTenthStep(self.width / 70.0),
                "height": roundTenthStep(self.height / 70.0),
                "mirrorX": self.mirrorX,
                "mirrorY": self.mirrorY,
		        "alpha": 1,
                "scale": 1,
                "elevation": 0,
                "rotation": rotation,
                "lockRotation": lockRotation,
                "effects": [], #TODO : support effects. Format is : ["icons/svg/frozen.svg", "icons/svg/skull.svg"], etc..
                "hidden": False,
                "dimLight": roundTenthStep(self.emits_dim_light),
                "brightLight": roundTenthStep(self.emits_bright_light),
                "dimSight": roundTenthStep(self.dim_sight),
                "brightSight": roundTenthStep(self.bright_sight),
                "sightAngle": self.sight_angle,
                "lightAngle": self.light_angle,
                "lightAlpha": self.light_alpha,
                "lightAnimation": {
                    "speed": 5,
                    "intensity": 5,
			        "reverse": False
                },
                "light": {
                    "dim": roundTenthStep(self.emits_dim_light),
                    "bright": roundTenthStep(self.emits_bright_light),
                    "angle": self.light_angle,
                    "color": self.light_color,
                    "alpha": self.light_alpha,
                    "animation": {
                        "speed": 5,
                        "intensity": 5,
                        "reverse": False
                    },
                    "coloration": 1,
                    "gradual": True,
                    "luminosity": 0.5,
                    "saturation": 0,
                    "contrast": 0,
                    "shadows": 0,
                    "darkness": {
                        "min": 0,
                        "max": 1
                    }
                },
                "vision": self.has_vision,
                "actorId": self.actor_id,
                "actorLink": False,
                "disposition": -1,
                "displayBars": self.display_bars,
                "bar1": {"attribute": "attributes.bar1" if self.bar1_max != 0 or self.bar1_val != 0 else None},
                "bar2": {"attribute": "attributes.bar2" if self.bar2_max != 0 or self.bar2_val != 0 else None},
                "tint": self.tint,
                "actorData": {
                    "data": {
                        "attributes": {
                            "bar1": {
                                "value": self.bar1_val,
                                "max": self.bar1_max
                                 },
                            "bar2": {
                                "value": self.bar2_val,
                                "max": self.bar2_max
                                }
                            }
                        }
                    }
                }

class Actor(Entity):    
    def __init__(self, database, character, index):
        Entity.__init__(self, database, character["id"])
        self._character = character
        tables = self._database._campaign.get("tables", [])

        self.logInfo("Creating Character : %s" % character["name"])
        self.parseAttributes()
        permissions = {"default": Handout.PERMISSION_NONE}
        for player in character.get("inplayerjournals", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_LIMITED
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_LIMITED
        for player in character.get("controlledby", []):
            if player == "all":
                permissions["default"] = Handout.PERMISSION_OWNER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Handout.PERMISSION_OWNER

        npc = self.isNPC()

        self._avatar_filename = None
        base_path = os.path.join("characters", "%03d - %s" % (index, character["name"]))
        if character["avatar"] != "":
            if self.getArgument("use_original_image_urls", False):
                self._avatar_filename = character["avatar"]
            else:
                filename = os.path.join(base_path, "avatar.png")
                if self.getArgument("json", False):
                    (_, self._avatar_filename) = self.downloadResource(character["avatar"], filename)
                else:
                    (_, self._avatar_filename) = self.copyZipFile(filename, filename)
                if self._avatar_filename == "":
                    self._avatar_filename = None
        default_token = character["defaulttoken"] if character["defaulttoken"] != "" else None
        self.token = Token(self._id, character["name"], default_token)
        token_filename = ""
        randomImg = False
        if default_token and default_token.get("imgsrc", "") != "":
            if self.getArgument("use_original_image_urls", False):
                token_filename = default_token["imgsrc"]
            else:
                filename = os.path.join(base_path, "token.png")
                if self.getArgument("json", False):
                    (_, token_filename) = self.downloadResource(default_token["imgsrc"], filename)
                else:
                    (_, token_filename) = self.copyZipFile(filename, filename)
                if self._avatar_filename is None:
                    self._avatar_filename = token_filename
                if "sides" in default_token and len(default_token["sides"]) > 0:
                    randomImg = True
                    side_names = None
                    for table in tables:
                        if table["name"] == character["name"]:
                            table_items = table["items"]
                            # Older exporter was creating an object of {id: item_data}, newer exports the tables and decks as arrays instead
                            if isinstance(table_items, dict):
                                table_items = table_items.values()
                            if not isinstance(table_items, list):
                                table_items = []
                            side_names = {}
                            for side in default_token["sides"]:
                                match = [i for i in table_items if i["avatar"] == side]
                                if len(match) > 0:
                                    side_names[side] = match[0]["name"]
                                else:
                                    side_names = None
                                    break
                            else:
                                break

                    for i in range(len(default_token["sides"])):
                        zip_filename = os.path.join(base_path, "side_" + str(i) + ".png")
                        if side_names:
                            side_img = default_token["sides"][i]
                            filename = os.path.join(base_path, "sides", side_names[side_img] + ".png")
                        else:
                            filename = os.path.join(base_path, "sides", "side_" + str(i) + ".png")
                        if self.getArgument("json", False):
                            (_, token_filename) = self.downloadResource(default_token["sides"][i], filename)
                        else:
                            (_, token_filename) = self.copyZipFile(zip_filename, filename)
                        token_filename = os.path.dirname(token_filename) + "/*.png"
            if self._avatar_filename is None:
                self._avatar_filename = token_filename
        if token_filename is None:
            token_filename = self._avatar_filename
        self.token.token_filename = token_filename

        token = self.token.getDict()
        if default_token:
            bar1_link = default_token.get("bar1_link", "")
            bar2_link = default_token.get("bar2_link", "")
            (_, _, hp_id) = self.getAttribute("hp")
            # Some NPCs will not have any bar values set, just the bar_link
            for attr in self._character["attributes"]:
                try:
                    (current, max, id) = (attr["current"], attr["max"], attr["id"])
                except:
                    continue
                if bar1_link == id:
                    try:
                        self.token.bar1_val = int(current)
                    except ValueError:
                        pass
                    try:
                        self.token.bar1_max = int(max)
                    except ValueError:
                        pass
                elif bar2_link == id:
                    try:
                        self.token.bar2_val = int(current)
                    except ValueError:
                        pass
                    try:
                        self.token.bar2_max = int(max)
                    except ValueError:
                        pass
            token = self.token.getDict()
            if bar1_link == hp_id or self.getArgument("force_hp_for_token_bar1", False):
                token["bar1"]["attribute"] = "attributes.hp"
            if bar2_link == hp_id or self.getArgument("force_hp_for_token_bar2", False):
                token["bar2"]["attribute"] = "attributes.hp"
        token["randomImg"] = randomImg
        token["actorLink"] = not npc
        del token["effects"]
        del token["hidden"]
        del token["elevation"]
        if token["actorLink"]:
            del token["actorData"]["data"]

        actor_data = {}
        owned_items = []
        actor_type = "npc" if npc else "character"
        if self._converter.game_system == "dnd5e":
            self._save_bonus = self.calculateSaveBonus()
            self._actor_abilities = self.createActorAbilities()
            actor_data = OrderedDict([
                ("abilities", self._actor_abilities),
                ("attributes", self.createActorAttributes()),
                ("details", self.createActorDetails()),
                ("skills", self.createActorSkills()),
                ("traits", self.createActorTraits()),
                ("currency", self.createActorCurrency()),
                ("spells", self.createActorSpells()),
                ("resources", self.createActorResources()),
                ("bonuses", self.createActorBonuses()),
            ])
            self.addClasses(owned_items)
            self.addTraits(owned_items)
            self.addSpells(owned_items)
            # Add actions before inventory so attack items get added first
            self.addActions(owned_items)
            self.addInventory(owned_items)
        else:
            templates = self._converter.system_templates
            if actor_type not in templates:
                if "character" in templates:
                    actor_type = "character"
                else:
                    types = list(templates.keys())
                    actor_type = types[0] if len(types) > 0 else actor_type
            actor_data = templates.get(actor_type, {})
            compendium_actor = self.findCompendiumActor(character["name"])
            if compendium_actor:
                actor_type = compendium_actor.entity["type"]
                actor_data = compendium_actor.entity.get("data", compendium_actor.entity.get("system", None))
                owned_items = compendium_actor.entity["items"]

        if self.getArgument("export_as_module", False):
            folder = None
        elif character["archived"] and not self.getArgument("disable_archived", False):
            folder = "archived-characters-folder-id"
        else:
            folder = self.findFolder(character["id"],  self._database._campaign["journalfolder"])

        self.entity = {"_id": self._id,
                       "name": self.getName(),
                       "img": self._avatar_filename,
                       "permission": permissions,
                       "data": actor_data,
                       "folder": Entity.normalizeID(folder),
                       "flags": {},
                       "sort": index * Entity.SORT_ORDER,
                       "type": actor_type,
                       "token": token,
                       "items": owned_items,
                       "effects": []
                       }

    def getName(self):
        return self._character["name"] or "Unknown Actor"

    def findFolder(self, id, folder, folder_id=None):
        for item in folder:
            if isinstance(item, dict):
                ret = self.findFolder(id, item["i"], "character" + item["id"])
                if ret:
                    return ret
            else:
                if item == id:
                    return folder_id
        return None

    def _capitalizeAll(self, sentence):
        return " ".join(map(lambda x: x.capitalize(), sentence.split(" ")))

    def getAttribute(self, key, default=None, from_dict=None):
        if from_dict is None:
            from_dict = self._attributes
        if self._shaped:
            shaped_key = self._convertAttributeName(key)
            if shaped_key != key and shaped_key in from_dict:
                #self.logInfo("Replacing {} with shaped key {}".format(key, shaped_key))
                key = shaped_key
        return from_dict.get(key, (default, default, None))

    def toInt(self, value, default):
        try:
            return int(value)
        except ValueError:
            return int(default)

    def getAttributeInt(self, key, default=0, from_dict=None):
        value = self.getAttribute(key, default, from_dict)[0]
        return self.toInt(value, default)

    def getAttributeBool(self, key, default=False, from_dict=None):
        value = str(self.getAttribute(key, default, from_dict)[0]).lower()
        return not (value == "0" or value == "" or value == "false" or value == "no")

    def getRepeatingAttributes(self, key):
        if self._shaped:
            shaped_key = self._convertRepeatingAttributeName(key)
            if shaped_key != key and shaped_key in self._repeating:
                #self.logInfo("Replacing Repeating {} with shaped key {}".format(key, shaped_key))
                key = shaped_key
        return self._repeating.get(key, {})

    def isNPC(self):
        npc = self.getAttributeInt("npc", 0)
        try:
            return bool(npc)
        except ValueError:
            return False

    def getNPCType(self):
        if self._shaped:
            creature_type = self.getAttribute("type", "")[0]
            size = self.getAttribute("size", "")[0]
            alignment = self.getAttribute("alignment", "")[0]
        else:
            npc_type = self.getAttribute("npc_type", "")[0]
            size = npc_type.split(",", 1)[0].split(" ", 1)[0].strip()
            creature_type = npc_type.split(",", 1)[0].split(" ", 1)[-1].strip()
            alignment = npc_type.split(",", 1)[-1].strip()
        return (size, creature_type, alignment)

    def getChallengeRating(self):
        cr = self.getAttribute("npc_challenge", 0)[0]
        try:
            cr = int(cr)
        except ValueError:
            try:
                cr = int(cr.split("/")[0]) / int(cr.split("/")[1])
            except ValueError:
                cr = 0
        return cr

    def getProficiencyBonus(self):
        if self.isNPC():
            cr = self.getChallengeRating()
            return int(math.ceil(cr + 7) / 4)
        else:
            return self.getAttributeInt("pb", 2)

    def parseAttributes(self):
        self._attributes = OrderedDict()
        self._repeating = OrderedDict()
        self._shaped = False
        for attr in self._character["attributes"]:
            try:
                value = (attr["current"], attr["max"], attr["id"])
            except:
                # Apparently, it's possible to have an attribute with no current value???
                continue
            if attr["name"].startswith("_reporder_repeating_"):
                pass
            elif attr["name"].startswith("repeating_"):
                try:
                    (_, repeating_type, id, name) = attr["name"].split("_", 3)
                except:
                    # Apparently, it's also possible to have attributes that aren't repeating but start with the string "repeating_".
                    continue
                rep = self._repeating.get(repeating_type, None)
                if rep is None:
                    rep = self._repeating[repeating_type] = OrderedDict()
                    order = ""
                    try:
                        for a in self._character["attributes"]:
                            if a["name"] == "_reporder_repeating_%s" % repeating_type:
                                order = a["current"]
                                break
                    except:
                        pass
                    for order_id in order.split(","):
                        if order_id != "":
                            rep.setdefault(order_id, {})
                rep.setdefault(id, {})[name] = value
            else:
                self._attributes[attr["name"]] = value
                if attr["name"] == "character_sheet" and value[0].startswith("Shaped"):
                    self._shaped = True

        if DISPLAY_ATTRIBUTES:
            self.displayAttributes()


    def displayAttributes(self):
        self.logInfo("Parsed attributes for character %s: %s" % (self._character["id"], self._character["name"]))
        keys = list(self._attributes.keys())
        keys.sort()
        for key in keys:
            attr = self._attributes[key]
            self.logInfo("%s: %s%s" % (key, str(attr[0]), ("(" + str(attr[1]) + ")") if attr[1] != "" else ""))
        self.logInfo("Repeated attributes for character %s: %s" % (self._character["id"], self._character["name"]))
        for _type in self._repeating:
            self.logInfo("\n\n****** %s ******" % _type)
            for item in self._repeating[_type]:
                self.logInfo("\n************************\n\t%s" % item)
                items = self._repeating[_type][item]
                keys = list(items.keys())
                keys.sort()
                for key in keys:
                    attr = items[key]
                    self.logInfo("\t\t%s: %s%s" % (key, str(attr[0]), ("(" + str(attr[1]) + ")") if attr[1] != "" else ""))
        

    def calculateSaveBonus(self):
        if self.isNPC():
            return 0

        bases = []
        for ability in ["strength", "dexterity", "constitution",
                        "intelligence", "wisdom", "charisma"]:
            mod = self.getAttributeInt(ability + "_mod", 0)
            if self.isNPC():
                save = self.getAttributeInt("npc_" + ability[0:3] + "_save", 0)
            else:
                save = self.getAttributeInt(ability + "_save_bonus", 0)
            bases.append(save - mod)
        return min(bases)
        #min_base = min(bases)
        #max_base = max(bases)
        #pb = self.getProficiencyBonus()
        #if min_base + pb == max_base and bases.count(min_base) == 4 and bases.count(max_base) == 2:
        #    return min_base

    def createActorAbility(self, name):
        ability = self.getAttributeInt(name.lower(), 10)
        mod = self.getAttributeInt(name.lower() + "_mod", 0)
        proficiency_bonus = self.getProficiencyBonus()
        if self.isNPC():
            save = self.getAttributeInt("npc_" + name.lower()[0:3] + "_save", 0)
        else:
            save = self.getAttributeInt(name.lower() + "_save_bonus", mod)
        proficient = (save >= mod + proficiency_bonus + self._save_bonus)

        return {
            "value": ability,
            "min": 3,
            "proficient": 1 if proficient else 0,
            "mod": mod,
            "save": save,
            "bonuses": {
                "check": "",
                "save": ""
            },
        }

    def createActorAbilities(self):
        return OrderedDict([("str", self.createActorAbility("Strength")),
                            ("dex", self.createActorAbility("Dexterity")),
                            ("con", self.createActorAbility("Constitution")),
                            ("int", self.createActorAbility("Intelligence")),
                            ("wis", self.createActorAbility("Wisdom")),
                            ("cha", self.createActorAbility("Charisma"))
                            ])

    def createAttributeNumber(self, name, attribute_name, default=0, extra={}, from_dict=None):
        (current, max, _) = self.getAttribute(attribute_name, default, from_dict=from_dict)
        try:
            current = int(current)
        except ValueError:
            pass
        try:
            max = int(max)
        except ValueError:
            pass
        ret = {"value": current}
        if max != "":
            ret["min"] = 0
            ret["max"] = max
        ret.update(extra)
        return ret

    def createAttributeBoolean(self, name, attribute_name, default=False, extra={}):
        value = self.getAttributeBool(attribute_name, "on" if default else "")
        if len(extra) == 0:
            return value
        ret = {"value": value}
        ret.update(extra)
        return ret

    def createAttributeAC(self):
        ac = self.getAttributeInt("npc_ac" if self.isNPC() else "ac", 10)
        
        res = {
            "flat": ac,
            "calc": "flat",
            "formula": ""
        }
        # dnd5e 2.1.x doesn't like using a non formula in the formula field
        # causing the acto
        #  if self.isNPC():
        #    res["formula"] = self.getAttribute("npc_actype", "")[0]
        return res

    def createAttributeHP(self):
        hp = self.getAttribute("hp", 10)
        if self.isNPC():
            if hp[2] == None:
                hp = self.getAttribute("npc_hpbase", "10")
                value = str(hp[0]).split(" ")[0]
                max = value
            else:
                value = hp[1]
                max = hp[1]
            formula = self.getAttribute("npc_hpformula", "")[0]
        else:
            value = hp[0]
            max = hp[1]
            formula = ""
        try:
            value = int(value)
        except:
            pass
        try:
            max = int(max)
        except:
            pass
        return {
            "value": value,
            "min": 0,
            "max": max,
            "temp": 0,
            "tempmax": 0,
            "formula": formula
        }

    def createAttributeInitiative(self):
        mod = self.getAttributeInt("dexterity_mod", 0)
        init = self.getAttributeInt("initiative_bonus", 0)
        jack = self.getAttributeInt("jack_bonus", 0)
        bonus = init - mod - jack
        return {
            "value": bonus,
            "bonus": bonus,
            "mod": mod,
            "prof": 1 if jack != 0 else 0,
            "total": init
        }

    def createAttributeMovement(self):
        speed = self.getAttribute("npc_speed" if self.isNPC() else "speed", "30 ft")[0]
        if type(speed) == int:
            speed = "%d ft" % speed
        parts = speed.replace("ft.", "ft").split(",", 1)
        if len(parts) > 1:
            speed = parts[0].strip()
            special = parts[1].strip()
        else:
            speed = parts[0].strip()
            special = ""

        movement = {
            "walk": 30,
            "units": "ft",
            "hover": "hover" in special
        }
        match = re.search(r"(\d+)", speed)
        if match:
            movement["walk"] = int(match.group(1))

        for movementType in ["burrow", "climb", "fly", "swim"]:
            movement[movementType] = 0
            match = re.search(movementType + r"\s+(\d+)", special)
            if match:
                movement[movementType] = int(match.group(1))

        return movement
    def createAttributeSenses(self):
        senses = {
            "darkvision": 0,
            "blindsight": 0,
            "tremorsense": 0,
            "truesight": 0,
            "units": "ft",
            "special": ""
        }
        if self.isNPC():
            try:
                senseTypes = ["darkvision", "blindsight", "tremorsense", "truesight"]
                npc_senses = self.getAttribute("npc_senses", "")[0].lower()
                for senseType in senseTypes:
                    senses[senseType] = 0
                    match = re.search(senseType + r"\s+(\d+)", npc_senses)
                    if match:
                        senses[senseType] = int(match.group(1))
                # Find special senses
                npc_senses = self.getAttribute("npc_senses", "")[0].split(",")
                npc_senses = list(map(lambda x: x.strip(), npc_senses))
                for i, sense in enumerate(npc_senses):
                    if sense.strip().startswith("passive perception"):
                        npc_senses.pop(i)
                        continue
                    for senseType in senseTypes:
                        if senseType in sense.lower():
                            npc_senses.pop(i)
                            break
                senses["special"] = ", ".join(npc_senses)
            except:
                pass

        return senses


    def getSpellcastingAbility(self):
        attribute = self.getAttribute("spellcasting_ability", "")[0]
        return ItemAbility.fromString(attribute)

    def createAttributeDeath(self):
        success = 0
        failure = 0
        if self._shaped:
            success = self.getAttributeInt("death_saving_throw_successes", 0)
            failure = self.getAttributeInt("death_saving_throw_failures", 0)
        else:
            for i in range(1, 4):
                if self.getAttribute("deathsave_succ%d" % i, 0)[0] == "on":
                    success += 1
                if self.getAttribute("deathsave_fail%d" % i, 0)[0] == "on":
                    failure += 1

        return {
            "success": success,
            "failure": failure
        }
    def createAttributeHitDice(self):
        if self._shaped:
            hd_d4 = self.getAttribute("hd_d4", 0)
            hd_d6 = self.getAttribute("hd_d6", 0)
            hd_d8 = self.getAttribute("hd_d8", 0)
            hd_d10 = self.getAttribute("hd_d10", 0)
            hd_d12 = self.getAttribute("hd_d12", 0)
            d4, d4_max = self.toInt(hd_d4[0], 0), self.toInt(hd_d4[1], 0)
            d6, d6_max = self.toInt(hd_d6[0], 0), self.toInt(hd_d6[1], 0)
            d8, d8_max = self.toInt(hd_d8[0], 0), self.toInt(hd_d8[1], 0)
            d10, d10_max = self.toInt(hd_d10[0], 0), self.toInt(hd_d10[1], 0)
            d12, d12_max = self.toInt(hd_d12[0], 0), self.toInt(hd_d12[1], 0)
            current = d4 + d6 + d8 + d10 + d12
            max = d4_max + d6_max + d8_max + d10_max + d12_max
        else:
            current, max, _ = self.getAttribute("hit_dice", 0)
            
        return {
            "value": current,
            "max": max
        }

    def createActorAttributes(self):
        attributes = OrderedDict([
            ("ac", self.createAttributeAC()),
            ("hp", self.createAttributeHP()),
            ("init", self.createAttributeInitiative()),
            ("prof", self.getProficiencyBonus()),
            ("movement", self.createAttributeMovement()),
            ("senses", self.createAttributeSenses()),
            ("spellcasting", self.getSpellcastingAbility()),
            ("spelldc", self.getAttributeInt("npc_spelldc" if self.isNPC() else "spell_save_dc", 10)),
            ("spellLevel", 0),
            # Add our own bar data
            ("bar1", {"value": self.token.bar1_val,
                      "min": 0,
                      "max": self.token.bar1_max}),
            ("bar2", {"value": self.token.bar2_val,
                      "min": 0,
                      "max": self.token.bar2_max}),
        ])
        if not self.isNPC():
            attributes.update([
                    ("hd", self.createAttributeHitDice()),
                    ("death", self.createAttributeDeath()),
                    ("exhaustion", self.getAttributeInt("exhaustion_level", 0)),
                    ("inspiration", self.createAttributeBoolean("Inspiration", "inspiration", False)),
            ])
        return attributes

    def createDetailAlignment(self):
        if self.isNPC():
            alignment = self.getNPCType()[2]
        else:
            alignment = self.getAttribute("alignment", "")[0]
        # NPCs have it all lowercase
        return self._capitalizeAll(alignment)

    def createDetailBio(self):
        bio = self._character["bio"]
        gmnotes = self._character["gmnotes"]
        for (attrib, label) in [("character_backstory", "Character Backstory"),
                                ("additional_feature_and_traits", "Additional Features and Traits"),
                                ("allies_and_organizations", "Allies & Organizations"),
                                ("treasure", "Treasure"),
                                ("miscellaneous_notes", "Miscellaneous Notes"),
                                ("miscellaneous_notes_2", "Miscellaneous Notes")]:
            content = self.getAttribute(attrib, "")[0]
            if content.strip() != "":
                bio += "\n<hr><section><p><strong>" + label + " :</strong> </p>" + self.textToHtml(content) + "</section>"
        if gmnotes.strip() != "":
            bio += "\n<hr><section class=\"secret\"><p><strong>GM Notes :</strong> </p>" + gmnotes + "</section>"

        bio = self.replaceCompendiumLinks(self.replaceEntityLinks(bio))
        return {
            "value": bio,
            "public": ""
        }

    def createDetailXP(self):
        max_per_level = [0, 300, 900, 2700,
                         6500, 14000, 23000,
                         34000, 48000, 64000,
                         85000, 100000, 120000,
                         140000, 165000, 195000,
                         225000, 265000, 305000, 355000]
        (current, max, _) = self.getAttribute("experience", 0)
        try:
            current = int(current)
        except ValueError:
            if "/" in current:
                try:
                    current = int(current.split("/")[0].replace(",", "").replace(".", ""))
                except:
                    pass
            if current == "":
                current = 0
        level = self.getAttributeInt("level", 1)
        try:
            max = max_per_level[level]
            prev = max_per_level[level - 1]
        except:
            max = 0
            prev = 0
        try:
            percent = 100 * (current - prev) / (max - prev)
        except:
            percent = 0

        return {
            "min": 0,
            "value": current,
            "max": max,
            "pct": percent
        }

    def createActorDetails(self):
        details =  OrderedDict([
            ("alignment", self.createDetailAlignment()),
            ("biography", self.createDetailBio()),
            ("class", self.getAttribute("class_display", "")[0]),
            ("race", self.getAttribute("race_display", "")[0])
        ])
        if self.isNPC():
            details.update([
                    ("type", {"value": self.getNPCType()[1], "subtype": "", "swarm": "", "custom": ""}),
                    ("environment", ""),
                    ("cr", self.getChallengeRating()),
                    ("xp", self.createAttributeNumber("Kill Experience", "npc_xp", 0)),
                    ("source", self.getArgument("npc_source", "Roll 20")),
                    ("spellLevel", 0)
                    ])
        else:
            details.update([
                    ("background", self.getAttribute("background", "")[0]),
                    ("originalClass", ""),
                    ("level", self.createAttributeNumber("Character Level", "level", 1, {"min": 1, "max": 20})),
                    ("xp", self.createDetailXP()),
                    ("appearance", self.getAttribute("character_appearance", "")[0]),
                    ("trait", self.getAttribute("personality_traits", "")[0]),
                    ("ideal", self.getAttribute("ideals", "")[0]),
                    ("bond", self.getAttribute("bonds", "")[0]),
                    ("flaw", self.getAttribute("flaws", "")[0])
                    ])
        return details

    def createActorSkill(self, label, attribute_name, ability):
        base_mod = self.getAttributeInt(ability + "_mod", 0)
        if self.isNPC():
            mod = self.getAttributeInt("npcd_" + attribute_name, -999)
            if mod == -999:
                mod = self.getAttributeInt("npc_" + attribute_name, base_mod)
        else:
            mod = self.getAttributeInt(attribute_name + "_bonus", base_mod)
        prof = self.getProficiencyBonus()

        if mod >= base_mod + prof * 2:
            value = 2
        elif mod >= base_mod + prof:
            value = 1
        elif mod >= base_mod + prof // 2:
            value = 0.5
        else:
            value = 0

        bonus = mod - (base_mod + prof * value)
        passive = mod + 10

        # An NPC might have overriden the PP in its senses
        if label == "Perception" and self.isNPC():
            senses = self.getAttribute("npc_senses", "")[0]
            try:
                match = re.search(r"passive perception (\d+)", senses)
                if match:
                    passive = int(match.group(1))
            except:
                pass

        return {
            "value": value,
            "ability": ability.lower()[0:3],
            "mod": mod,
            "bonuses": {
                "check": bonus,
                "passive": (passive - mod - 10)
            },
        }
    def createActorSkills(self):
        skills = OrderedDict([
            ("acr", self.createActorSkill("Acrobatics", "acrobatics", "dexterity")),
            ("ani", self.createActorSkill("Animal Handling", "animal_handling", "wisdom")),
            ("arc", self.createActorSkill("Arcana", "arcana", "intelligence")),
            ("ath", self.createActorSkill("Athletics", "athletics", "strength")),
            ("dec", self.createActorSkill("Deception", "deception", "charisma")),
            ("his", self.createActorSkill("History", "history", "intelligence")),
            ("ins", self.createActorSkill("Insight", "insight", "wisdom")),
            ("itm", self.createActorSkill("Intimidation", "intimidation", "charisma")),
            ("inv", self.createActorSkill("Investigation", "investigation", "intelligence")),
            ("med", self.createActorSkill("Medicine", "medicine", "wisdom")),
            ("nat", self.createActorSkill("Nature", "nature", "intelligence")),
            ("prc", self.createActorSkill("Perception", "perception", "wisdom")),
            ("prf", self.createActorSkill("Performance", "performance", "charisma")),
            ("per", self.createActorSkill("Persuasion", "persuasion", "charisma")),
            ("rel", self.createActorSkill("Religion", "religion", "intelligence")),
            ("slt", self.createActorSkill("Sleight of Hand", "sleight_of_hand", "dexterity")),
            ("ste", self.createActorSkill("Stealth", "stealth", "dexterity")),
            ("sur", self.createActorSkill("Survival", "survival", "wisdom"))
        ])
        if self._shaped:
            skill_keys = {
                "acrobatics": "acr",
                "animalhandling": "ani",
                "arcana": "arc",
                "athletics": "ath",
                "deception": "dec",
                "history" : "his",
                "insight" : "ins",
                "intimidation" : "itm",
                "investigation" : "inv",
                "medicine": "med",
                "nature": "nat",
                "perception": "prc",
                "performance": "prf",
                "persuasion": "per",
                "religion": "rel",
                "sleightofhand": "slt",
                "stealth": "ste",
                "survival": "sur",

            }
            prof = self.getProficiencyBonus()
            for skill in self.getRepeatingAttributes("skill").values():
                if len(skill) == 0:
                    continue
                storage_name = self.getAttribute("storage_name", None, from_dict=skill)[0]
                name = self.getAttribute("name", storage_name, from_dict=skill)[0]
                ability = self.getAttribute("ability", "str", from_dict=skill)[0]
                ability_key = self.getAttribute("ability_key", ability, from_dict=skill)[0]
                mod = self.getAttributeInt("total_with_sign", 0, from_dict=skill)
                base_mod = 0
                if ability_key and ability_key != "0":
                    ability_key = ability_key.lower()[0:3]
                    if ability_key in self._actor_abilities:
                        base_mod = self._actor_abilities[ability_key]["mod"]
                    
                if mod >= base_mod + prof * 2:
                    value = 2
                elif mod >= base_mod + prof:
                    value = 1
                elif mod >= base_mod + prof // 2:
                    value = 0.5
                else:
                    value = 0

                bonus = (base_mod + prof * value) - mod

                passive = mod = self.getAttributeInt("passive", mod + 10, from_dict=skill)
                if name is not None:
                    key = name.lower()
                    if type(storage_name) == str:
                        key = skill_keys.get(storage_name.lower(), key)
                    # An NPC might have overriden the PP in its senses
                    if key == "prc" and self.isNPC():
                        senses = self.getAttribute("npc_senses", "")[0]
                        try:
                            match = re.search(r"passive perception (\d+)", senses)
                            if match:
                                passive = int(match.group(1))
                        except:
                            pass
                    skills.update([(key, {
                        "value": value,
                        "ability": ability.lower()[0:3],
                        "bonus": bonus,
                        "mod": mod,
                        "passive": passive
                    })])
        return skills
        
    def createTraitSize(self):
        dnd5e_sizes = {
            "gargantuan": "grg",
            "huge": "huge",
            "large": "lg",
            "medium": "med",
            "small": "sm",
            "tiny": "tiny"
        }
        if self.isNPC():
            size = self.getNPCType()[0]
        else:
            size = self.getAttribute("size", "Medium")[0]
        if type(size) == int or type(size) == float:
            dnd5e_sizes_float = {
                4: "grg",
                3: "huge",
                2: "lg",
                1: "med",
                1: "sm",
                0.5: "tiny"
            }
            return dnd5e_sizes_float.get(size, "med")

        return dnd5e_sizes.get(size.lower(), "med")

    def _addKnownToArray(self, known_list, name, array, custom):
        name = self._capitalizeAll(name.strip())
        if name == "":
            return
        known = known_list.get(name, None)
        if known:
            array.append(known)
        elif custom is not None:
            custom.append(name)

    def createTraitLanguages(self):
        known_languages = { 'Aarakocra': 'aarakocra',
                            'Abyssal': 'abyssal',
                            'Aquan': 'aquan',
                            'Auran': 'auran',
                            'Celestial': 'celestial',
                            'Common': 'common',
                            'Deep Speech': 'deep',
                            'Draconic': 'draconic',
                            'Druidic': 'druidic',
                            'Dwarvish': 'dwarvish',
                            'Elvish': 'elvish',
                            'Giant': 'giant',
                            'Gith': 'gith',
                            'Gnoll': 'gnoll',
                            'Gnomish': 'gnomish',
                            'Goblin': 'goblin',
                            'Halfling': 'halfling',
                            'Ignan': 'ignan',
                            'Infernal': 'infernal',
                            'Orc': 'orc',
                            'Primordial': 'primordial',
                            'Sylvan': 'sylvan',
                            'Terran': 'terran',
                            "Thieves' Cant": 'cant',
                            'Undercommon': 'undercommon'
                            }

        languages = []
        custom = []
        if self.isNPC():
            character_languages = self.getAttribute("npc_languages", "")[0]
        else:
            character_languages = self.getAttribute("languages", "")[0]
            for prof in self.getRepeatingAttributes("proficiencies").values():
                #self.logInfo("Proficienty : {} = {}".format(id, prof))
                if self.getAttribute("prof_type", "", from_dict=prof)[0] == "LANGUAGE":
                    language = self.getAttribute("name", "", from_dict=prof)[0]
                    for lang in language.split(","):
                        self._addKnownToArray(known_languages, lang, languages, custom)
        if type(character_languages) == str:
            character_languages = character_languages.split(",")
        for lang in character_languages:
            self._addKnownToArray(known_languages, lang, languages, custom)

        return {
            "value": languages,
            "custom": ", ".join(custom)
        }

    def _addDamagesToArray(self, damages, damages_array, custom):
        known_damages = {'Acid': 'acid',
                        'Bludgeoning': 'bludgeoning',
                        'Cold': 'cold',
                        'Fire': 'fire',
                        'Force': 'force',
                        'Lightning': 'lightning',
                        'Necrotic': 'necrotic',
                        'Piercing': 'piercing',
                        'Poison': 'poison',
                        'Psychic': 'psychic',
                        'Radiant': 'radiant',
                        'Slashing': 'slashing',
                        'Thunder': 'thunder'
                        }
        # When they add 'piercing, bludgeoning, and slashing from non magical weapons",
        # they separate it with a ';' from the rest of the list
        sections = damages
        if isinstance(damages, str):
            sections = damages.split(";")
        for i, damage in enumerate(sections):
            if isinstance(damage, dict) and damage.get("special", None) is not None:
                damage = damage["special"]
            if not isinstance(damage, str):
                continue
            if i == 0:
                for damage2 in damage.split(","):
                    self._addKnownToArray(known_damages, damage2, damages_array, custom)
            else:
                self._addKnownToArray(known_damages, damage, damages_array, custom)

    def createTraitDamageImmunities(self):
        immunities = []
        custom = []
        if self.isNPC():
            damage_immunities = self.getAttribute("npc_immunities", "")[0]
        else:
            damage_immunities = self.getAttribute("damage_immunities", "")[0]
        self._addDamagesToArray(damage_immunities, immunities, custom)

        return {
            "value": immunities,
            "custom": ", ".join(custom)
        }

    def createTraitDamageResistances(self):
        resistances = []
        custom = []
        if self.isNPC():
            damage_resistances = self.getAttribute("npc_resistances", "")[0]
        else:
            damage_resistances = self.getAttribute("damage_resistances", "")[0]
        self._addDamagesToArray(damage_resistances, resistances, custom)

        return {
            "value": resistances,
            "custom": ", ".join(custom)
        }
    def createTraitDamageVulnerabilities(self):
        vulnerabilities = []
        custom = []
        if self.isNPC():
            damage_vulnerabilities = self.getAttribute("npc_vulnerabilities", "")[0]
        else:
            damage_vulnerabilities = self.getAttribute("damage_vulnerabilities", "")[0]
        self._addDamagesToArray(damage_vulnerabilities, vulnerabilities, custom)

        return {
            "value": vulnerabilities,
            "custom": ", ".join(custom)
        }

    def createTraitConditionImmunities(self):
        known_immunities = {'Blinded': 'blinded',
                            'Charmed': 'charmed',
                            'Deafened': 'deafened',
                            'Diseased': 'diseased',
                            'Exhaustion': 'exhaustion',
                            'Frightened': 'frightened',
                            'Grappled': 'grappled',
                            'Inacapacitated': 'incapacitated',
                            'Invisible': 'invisible',
                            'Paralyzed': 'paralyzed',
                            'Petrified': 'petrified',
                            'Poisoned': 'poisoned',
                            'Prone': 'prone',
                            'Restrained': 'restrained',
                            'Stunned': 'stunned',
                            'Unconscious': 'unconscious'
                            }

        immunities = []
        custom = []
        if self.isNPC():
            condition_immunities = self.getAttribute("npc_condition_immunities", "")[0]
        else:
            condition_immunities = self.getAttribute("condition_immunities", "")[0]
        for immunity in condition_immunities.split(","):
            self._addKnownToArray(known_immunities, immunity, immunities, custom)

        return {
            "value": immunities,
            "custom": ", ".join(custom)
        }

    def createTraitArmorProficiencies(self):
        known_profs = {
            "Light": "lgt",
            "Light Armor": "lgt",
            "Medium Armor": "med",
            "Medium": "med",
            "Heavy": "hvy",
            "Heavy Armor": "hvy",
            "Shields": "shl"
        }

        proficiencies = []
        custom = []
        for prof in self.getRepeatingAttributes("proficiencies").values():
            #self.logInfo("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "ARMOR":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)
        if self._shaped:
            prof_name = self.getAttribute("proficiencies", "")[0]
            for proficiency in prof_name.split(","):
                self._addKnownToArray(known_profs, proficiency, proficiencies, None)

        return {
            "value": proficiencies,
            "custom": ", ".join(custom)
        }
    def createTraitWeaponProficiencies(self):
        known_profs = {
            "Simple Weapons": "sim",
            "Martial Weapons": "mar"
        }

        proficiencies = []
        custom = []
        for prof in self.getRepeatingAttributes("proficiencies").values():
            #self.logInfo("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "WEAPON":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)
        if self._shaped:
            prof_name = self.getAttribute("proficiencies", "")[0]
            for proficiency in prof_name.split(","):
                self._addKnownToArray(known_profs, proficiency, proficiencies, None)

        return {
            "value": proficiencies,
            "custom": ", ".join(custom)
        }

    def createTraitToolProficiencies(self):
        known_profs = {
            "Artisan's Tools": "art",
            "Disguise Kit": "disg",
            "Forgery Kit": "forg",
            "Gaming Set": "game",
            "Herbalism Kit": "herb",
            "Musical Instrument": "music",
            "Navigator's Tools": "navg",
            "Poisoner's Kit": "pois",
            "Thieves' Tools": "thief",
            "Vehicle (Land or Water)": "vehicle"
        }

        proficiencies = []
        custom = []
        for prof in self.getRepeatingAttributes("proficiencies").values():
            #self.logInfo("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "TOOL":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)
        for prof in self.getRepeatingAttributes("tool").values():
            proficiency = self.getAttribute("toolname", "", from_dict=prof)[0]
            self._addKnownToArray(known_profs, proficiency, proficiencies, custom)
        if self._shaped:
            prof_name = self.getAttribute("proficiencies", "")[0]
            for proficiency in prof_name.split(","):
                self._addKnownToArray(known_profs, proficiency, proficiencies, None)

        return {
            "value": proficiencies,
            "custom": ", ".join(custom)
        }

    def createActorTraits(self):
        traits =  OrderedDict([
            ("size", self.createTraitSize()),
            ("languages", self.createTraitLanguages()),
            ("di", self.createTraitDamageImmunities()),
            ("dr", self.createTraitDamageResistances()),
            ("dv", self.createTraitDamageVulnerabilities()),
            ("ci", self.createTraitConditionImmunities()),
        ])
        
        if not self.isNPC():
            traits.update([
                    ("armorProf", self.createTraitArmorProficiencies()),
                    ("toolProf", self.createTraitToolProficiencies()),
                    ("weaponProf", self.createTraitWeaponProficiencies())
                    ])
        return traits

    def createActorCurrency(self):
        if self._shaped:
            currencies = OrderedDict()
            for currency in self.getRepeatingAttributes("currency").values():
                acronym = self.getAttribute("acronym", None, from_dict=currency)[0]
                # Apparently, you could get a boolean acronym 
                if type(acronym) == str:
                    currencies.update([(acronym.lower(), self.getAttributeInt("quantity", 0, from_dict=currency))])
            return currencies
        else:
            return OrderedDict([
                ("pp", self.getAttributeInt("pp", 0)),
                ("gp", self.getAttributeInt("gp", 0)),
                ("ep", self.getAttributeInt("ep", 0)),
                ("sp", self.getAttributeInt("sp", 0)),
                ("cp", self.getAttributeInt("cp", 0))
            ])

    def createActorSpells(self):
        spells = OrderedDict([("spell0", {"value": 0, "max": 0})])
        for level in range(1, 10):
            current = self.getAttribute("lvl%d_slots_expended" % level, 0)[0]
            max = self.getAttribute("lvl%d_slots_total" % level, current)[0]
            spells["spell%d" % level]  = {"value": current, "max": max, "override": None}
        spells["pact"] = {"value": 0, "override": None}
        return spells

    def createCharacterResource(self, label, resource, from_dict=None):
        name = self.getAttribute(resource + "_name", label, from_dict=from_dict)[0]
        (current, max, _) = self.getAttribute(resource, 0, from_dict=from_dict)
        try:
            current = int(current)
        except ValueError:
            current = 0
        try:
            max = int(max)
        except ValueError:
            max = 0
        return {
            "label": name,
            "sr": False,
            "lr": False,
            "value": current,
            "max": max
        }

    def createResourceLegendaryResistance(self):
        legres = 0
        for trait in self.getRepeatingAttributes("npctrait").values():
            name = self.getAttribute("name", "", from_dict=trait)[0]
            match = re.search(r"Legendary Resistance \((\d+)/[Dd]ay\)", name)
            if match:
                legres = int(match.group(1))

        return {
            "value": legres,
            "max": legres
        }
    def createResourceLegendaryActions(self):
        legact = self.getAttributeInt("npc_legendary_actions", 0)
        return {
            "value": legact,
            "max": legact
        }
                    
    def createResourceLairAction(self):
        lair_actions = self.getRepeatingAttributes("npcaction-l")
        value = len(lair_actions) > 0
        return {
            "value": value,
            "initiative": 20 if value else 0
        }
    def createActorResources(self):
        if self.isNPC():
            return OrderedDict([
                ("legact", self.createResourceLegendaryActions()),
                ("legres", self.createResourceLegendaryResistance()),
                ("lair", self.createResourceLairAction())
            ])
        else:
            resources = OrderedDict([("primary", self.createCharacterResource("Primary Resource", "class_resource")),
                                    ("secondary", self.createCharacterResource("Secondary Resource", "other_resource")),
                                    ("tertiary", self.createCharacterResource("Tertiary Resource", "R20Converter-attribute-wont-exist"))])
            if self._shaped:
                index = 0
                for utility in self.getRepeatingAttributes("utility").values():
                    if len(utility) == 0:
                        continue
                    if index == 0:
                        key, name = "primary", "Primary Resource"
                    elif index == 1:
                        key, name = "secondary", "Secondary Resource"
                    elif index == 2:
                        key, name = "tertiary", "Tertiary Resource"
                    else:
                        key, name = str(index), "Resource " + str(index)
                    name = self.getAttribute("name", name, from_dict=utility)[0]
                    recharge = self.getAttribute("recharge", "", from_dict=utility)[0]
                    resource = self.createCharacterResource(name, "uses", from_dict=utility)
                    if recharge == "SHORT_REST" or recharge == "SHORT_OR_LONG_REST":
                        resource["sr"] = True
                    if recharge == "LONG_REST" or recharge == "SHORT_OR_LONG_REST":
                        resource["lr"] = True
                    resources.update([(key, resource)])
                    index += 1
                for ammo in self.getRepeatingAttributes("ammo").values():
                    if len(ammo) == 0:
                        continue
                    if index == 0:
                        key, name = "primary", "Primary Resource"
                    elif index == 1:
                        key, name = "secondary", "Secondary Resource"
                    elif index == 2:
                        key, name = "tertiary", "Tertiary Resource"
                    else:
                        key, name = str(index), "Resource " + str(index)
                    name = self.getAttribute("name", name, from_dict=ammo)[0]
                    resource = self.createCharacterResource(name, "uses", from_dict=ammo)
                    resources.update([(key, resource)])
                    index += 1
            else:
                index = 2
                for resource in self.getRepeatingAttributes("resource").values():
                    if len(resource) == 0:
                        continue
                    for side in ["left", "right"]:
                        name = self.getAttribute("resource_" + side + "_name", "", from_dict=resource)[0]
                        res = self.createCharacterResource(name, "resource_" + side, from_dict=resource)
                        if res["label"] != "" or res["value"] != 0 or res["max"] != 0:
                            if index == 2:
                                key, name = "tertiary", "Tertiary Resource"
                            else:
                                key, name = "resource" + str(index), "Resource " + str(index)
                            if res["label"] == "":
                                res["label"] = name
                            resources.update([(key, res)])
                            index += 1
            return resources

    def createActorBonuses(self):
        # Unused for now
        return {
            "mwak": {
                "attack": "",
                "damage": ""
            },
            "rwak": {
                "attack": "",
                "damage": ""
            },
            "msak": {
                "attack": "",
                "damage": ""
            },
            "rsak": {
                "attack": "",
                "damage": ""
            },
            "abilities": {
                "check": "",
                "save": str(self._save_bonus) if self._save_bonus != 0 else "",
                "skill": ""
            },
            "spell": {
                "dc": ""
            }
        }


    def exportItem(self, item, folder_prefix, force=False):
        if not force and self.getArgument("dont_export_actor_items", False):
            return
        if self.getArgument("export_as_module", False):
            folder_id = None
        else:
            folder_name = "%s (%s)" % (folder_prefix, "NPC" if self.isNPC() else "PC")
            folder = self._converter.folders.ensureFolder(folder_name, folder_name, "Item")
            folder_id = folder.getID()
        name = item.getName()
        if self.getArgument("no_duplicate_actor_items", False):
            for i in self._converter.items.entities:
                if i.entity["folder"] == folder_id and i.entity["name"] == name:
                    return
        else:
            item.entity["name"] = "%s (%s)" % (name, self.getName())
        item.entity["folder"] = folder_id
        self._converter.items.addEntity(item)

    def createItemInventory(self, items, name, description, inventory_type, attributes,
                            activity=None, attack=None, specific=None, **kwargs):
        name = name if name != "" else "<no name>"
        description = Entity.textToHtml(description)
        compendium_item = self.findCompendiumItem("Items", name)
        item = self._converter.items.createItemInventory(None, name, description, inventory_type, attributes,
                                                        activity, attack, specific, **kwargs)
        # Prevent a weapon (torch, shovel) from being transformed into loot and losing its damage/attack properties
        if compendium_item and (compendium_item.entity["type"] != "loot" or inventory_type == "loot"):
            item = self._converter.items.createItemFromCompendium(None, compendium_item, item.entity["data"])
        else:
            item.entity["img"] = compendium_item.entity["img"] if compendium_item else self._avatar_filename
        owned_item = item.addToOwnedList(items)

        if inventory_type == "loot":
            folder_prefix = "Loot"
        elif inventory_type == "equipment":
            folder_prefix = "Equipment"
        elif inventory_type == "consumable":
            folder_prefix = "Comsumables"
        elif inventory_type == "tool":
            folder_prefix = "Tools"
        elif inventory_type == "weapon":
            folder_prefix = "Weapons"
        else:
            folder_prefix = "Inventory"
        self.exportItem(item, folder_prefix)
        return owned_item

    def addInventoryItem(self, items, item):
        name = self.getAttribute("itemname", "", from_dict=item)[0]
        content = self.getAttribute("itemcontent", "", from_dict=item)[0]
        count = self.getAttributeInt("itemcount", 1, from_dict=item)
        weight = self.getAttributeInt("itemweight", 1, from_dict=item)
        mods = self.getAttribute("itemmodifiers", "", from_dict=item)[0]
        modifiers = {}
        for mod in mods.split(","):
            if mod == "":
                continue
            # In case the mods aren't properly formatted, let's not crash here, kthxbye
            try:
                if ":" in mod:
                    key, value = mod.split(":", 1)
                    modifiers[key.strip()] = value.strip()
                elif "+" in mod:
                    key, value = mod.split(" +", 1)
                    modifiers[key.strip()] = "+" + value
                elif "-" in mod:
                    key, value = mod.split(" -", 1)
                    modifiers[key.strip()] = "-" + value
                else:
                    modifiers[mod.strip()] = mod
            except:
                pass
        item_type = modifiers.get("Item Type", "Gear")
        armor = modifiers.get("AC", 0)
        damage = modifiers.get("Damage", "")
        damage_type = modifiers.get("Damage Type", "").lower()
        damage2 = modifiers.get("Alternate Damage", "")
        damage2_type = modifiers.get("Altermate Damage Type", "").lower()
        if damage2 == "":
            damage2 = modifiers.get("Secondary Damage", "")
            damage2_type = modifiers.get("Secondary Damage Type", "").lower()
        weapon_range = modifiers.get("Range", "")

        activation = ItemActivation()
        attack = ItemAttack()
        attributes = ItemInventoryAttributes()

        attributes.weight = weight
        attributes.quantity = count
        attributes.equipped = self.getAttributeBool("equipped", True, from_dict=item)

        if damage != "" or damage_type != "":
            attack.damages.addDamage(damage, damage_type.lower())
        if damage2 != "" or damage2_type != "":
            attack.damages.addDamage(damage2, damage2_type.lower())

        # Convert range
        self._parseRange(activation, weapon_range)

        if item_type in ["Light Armor", "Medium Armor", "Heavy Armor", "Shield"] or armor != 0:
            equipment = ItemEquipment()
            equipment.proficient = False
            try:
                equipment.ac  = int(armor)
            except ValueError:
                pass
            armor_type = item_type.split(" ")[0].lower()
            if armor_type == "light":
                equipment.type = ItemEquipment.LIGHT_ARMOR
            elif armor_type == "medium":
                equipment.type = ItemEquipment.MEDIUM_ARMOR
            elif armor_type == "heavy":
                equipment.type = ItemEquipment.HEAVY_ARMOR
            elif armor_type == "shield":
                equipment.type = ItemEquipment.SHIELD
            if self._shaped:
                equipment.proficient = armor_type in self.getAttribute("proficiencies", "")[0]
            for prof in self.getRepeatingAttributes("proficiencies").values():
                if self.getAttribute("prof_type", "", from_dict=prof)[0] == "ARMOR":
                    prof_name = self.getAttribute("name", "", from_dict=prof)[0].lower()
                    for proficiency in prof_name.split(","):
                        if proficiency == item_type.lower() or proficiency == armor_type:
                            equipment.proficient = True
                            break
            self.createItemInventory(items, name, content, "equipment", attributes, activation, attack, equipment)
        elif item_type in ["Melee Weapon", "Ranged Weapon", "Ammunition"] or len(attack.damages.damages) > 0:
            weapon = ItemWeapon()
            properties = self.getAttribute("itemproperties", "", from_dict=item)[0]
            for prop in properties.split(","):
                weapon.properties.addFromString(prop.strip())

            compendium_item = self.findCompendiumItem("Items", name)
            if compendium_item is not None and compendium_item.entity["type"] == "weapon":
                weapon.type = compendium_item.entity["data"]["weaponType"]
            elif "Improvised Weapon" in properties:
                weapon.type = ItemWeapon.IMPROVISED
            elif item_type == "Ammunition":
                weapon.type = ItemWeapon.AMMUNITION
            elif item_type == "Melee Weapon":
                weapon.type = ItemWeapon.SIMPLE_MELEE
            elif item_type == "Ranged Weapon":
                weapon.type = ItemWeapon.SIMPLE_RANGED
            else:
                weapon.type = ItemWeapon.IMPROVISED

            weapon.proficient = False
            if self._shaped:
                proficiencies = self.getAttribute("proficiencies", "")[0].lower()
                for proficiency in proficiencies.split(","):
                    if proficiency.startswith(name.lower()) or \
                        (proficiency.startswith("simple") and weapon.type.startswith("simple")) or \
                        (proficiency.startswith("martial") and weapon.type.startswith("martial")):
                        weapon.proficient = True
                        break
            for prof in self.getRepeatingAttributes("proficiencies").values():
                if self.getAttribute("prof_type", "", from_dict=prof)[0] == "WEAPON":
                    prof_name = self.getAttribute("name", "", from_dict=prof)[0].lower()
                    for proficiency in prof_name.split(","):
                        if proficiency.startswith(name.lower()) or \
                            (proficiency.startswith("simple") and weapon.type.startswith("simple")) or \
                            (proficiency.startswith("martial") and weapon.type.startswith("martial")):
                            weapon.proficient = True
                            break

            self.createItemInventory(items, name, content, "weapon", attributes, activation, attack, weapon)
        else:
            if item_type not in ["Adventuring Gear", "Items", "Gear"]:
                self.logWarning("Unknown item properties : {} = {}".format(name, modifiers))
            self.createItemInventory(items, name, content, "loot", attributes)

    def addInventory(self, items):
        for item in self.getRepeatingAttributes("inventory").values():
            if len(item) == 0 or \
                (self.getAttributeBool("hasattack", False, from_dict=item) and \
                     self.getAttribute("itemattackid", "", from_dict=item)[0] != ""):
                continue
            self.addInventoryItem(items, item)
        if self._shaped:
            for item in self.getRepeatingAttributes("armor").values():
                if len(item) == 0:
                    continue
                name = self.getAttribute("name", "", from_dict=item)[0]
                content = self.getAttribute("content", "", from_dict=item)[0]
                count = self.getAttributeInt("uses", 1, from_dict=item)
                weight = self.getAttributeInt("weight", 0, from_dict=item)
                activation = ItemActivation()
                attack = ItemAttack()
                attributes = ItemInventoryAttributes()
                equipment = ItemEquipment()
                attributes.weight = weight
                attributes.quantity = count
                attributes.equipped = self.getAttributeBool("worn", True, from_dict=item)
                equipment.proficient = False
                equipment.ac  = self.getAttributeInt("ac_total", 10, from_dict=item)
                armor_type = self.getAttribute("type", "", from_dict=item)[0].split("_")[0].lower()
                if armor_type == "light":
                    equipment.type = ItemEquipment.LIGHT_ARMOR
                elif armor_type == "medium":
                    equipment.type = ItemEquipment.MEDIUM_ARMOR
                elif armor_type == "heavy":
                    equipment.type = ItemEquipment.HEAVY_ARMOR
                elif armor_type == "shield":
                    equipment.type = ItemEquipment.SHIELD
                str_requirement = self.getAttribute("strength_requirements", "", from_dict=item)[0]
                if str_requirement == "Str 13":
                    equipment.strength = 13
                elif str_requirement == "Str 15":
                    equipment.strength = 15
                if self.getAttribute("ac_ability", "", from_dict=item)[0] == "DEX_MAX_X":
                    equipment.dexterity = 2
                equipment.proficient = armor_type in self.getAttribute("proficiencies", "")[0]
                self.createItemInventory(items, name, content, "equipment", attributes, activation, attack, equipment)


    def createItemFeat(self, items, name, description, activation=None, attack=None, recharge=None, **kwargs):
        name = name if name != "" else "<no name>"
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Class Features", name)
        item = self._converter.items.createItemFeat(None, name, description, activation, attack, recharge, **kwargs)
        if compendium_item and compendium_item.entity["type"] != "loot":
            item = self._converter.items.createItemFromCompendium(None, compendium_item, item.entity["data"])
        else:
            item.entity["img"] = compendium_item.entity["img"] if compendium_item else self._avatar_filename
        owned_item = item.addToOwnedList(items)
        self.exportItem(item, "Abilities & Feats")
        return owned_item

    def _descriptionToString(self, desc):
        if isinstance(desc, str):
            return desc
        if isinstance(desc, list):
            description = ""
            for line in desc:
                description += self._descriptionToString(line) + "\n"
            return description
        if isinstance(desc, dict) and desc.get("entries", None):
            return self._descriptionToString(desc["entries"])
        return ""

    def addTraits(self, items):
        if self._shaped:
            # Shaped sheet doesn't have a name+description only trait, so we handle traits and reactions
            # as we do other sheet actions
            return
        if self.isNPC():
            npc_traits = self.getRepeatingAttributes("npctrait")
            for trait in npc_traits.values():
                if len(trait) == 0:
                    continue
                name = self.getAttribute("name", "", from_dict=trait)[0]
                desc = self.getAttribute("desc", "", from_dict=trait)[0]
                description = self.getAttribute("description", "", from_dict=trait)[0]
                description = self._descriptionToString(description or desc)
                self.createItemFeat(items, name, description, None, None, None)

            npc_reactions = self.getRepeatingAttributes("npcreaction")
            for trait in npc_reactions.values():
                if len(trait) == 0:
                    continue
                name = self.getAttribute("name", "", from_dict=trait)[0]
                desc = self.getAttribute("desc", "", from_dict=trait)[0]
                description = self.getAttribute("description", "", from_dict=trait)[0] or desc
                activation = ItemActivation(ItemActivation.REACTION, 1)
                self.createItemFeat(items, name, description, activation, None, None)
        else:
            traits = self.getRepeatingAttributes("traits")
            for trait in traits.values():
                if len(trait) == 0:
                    continue
                name = self.getAttribute("name", "", from_dict=trait)[0]
                desc = self.getAttribute("desc", "", from_dict=trait)[0]
                description = self.getAttribute("description", "", from_dict=trait)[0] or desc
                source = self.getAttribute("source", "Racial", from_dict=trait)[0]
                source_type = self.getAttribute("source_type", "", from_dict=trait)[0]
                self.createItemFeat(items, name, description, None, None, None, source=source, requirements=source_type)

    def addNPCAction(self, items, action, activation_type):
        name = self.getAttribute("name", "", from_dict=action)[0]
        name_display = self.getAttribute("name_display", "", from_dict=action)[0]
        desc = self.getAttribute("desc", "", from_dict=action)[0]
        description = self.getAttribute("description", "", from_dict=action)[0] or desc
        tohit = self.getAttributeInt("attack_tohit", 0, from_dict=action)
        onhit = self.getAttribute("attack_onhit", "", from_dict=action)[0]
        atk_range = self.getAttribute("attack_range", "", from_dict=action)[0]
        atk_target = self.getAttribute("attack_target", "one target", from_dict=action)[0]
        has_attack = False
        proficient = True

        activation = ItemActivation()
        attack = ItemAttack()

        if self._shaped:
            atk_target = self._capitalizeAll(atk_target.replace("_", " "))
            self._parseShapedAttacks(attack, action)
            has_attack = (attack.type == ItemAttack.MELEE_WEAPON or attack.type == ItemAttack.RANGED_WEAPON)
            proficient = self.getAttributeBool("proficiency", True, from_dict=action)
            reachrange = "reach" if attack.type == ItemAttack.MELEE_WEAPON else "range"
            atk_range = self.getAttribute(reachrange, "", from_dict=action)[0]
            if has_attack and tohit != "":
                attack_type = "Melee" if attack.type == ItemAttack.MELEE_WEAPON else "Ranged"
                attack_type += "Weapon Attack"
                tohitrange = "{} to hit, {} {}".format(tohit, self._capitalizeAll(reachrange), atk_range)
            else:
                onhit = ""
        else:
            attack_flag = self.getAttributeBool("attack_flag", False, from_dict=action)
            atktype = self.getAttribute("attack_type", "Melee", from_dict=action)[0]
            attack_type = self.getAttribute("attack_type_display", atktype + " Weapon Attack", from_dict=action)[0]
            tohitrange = self.getAttribute("attack_tohitrange", "", from_dict=action)[0]
            dmg = self.getAttribute("attack_damage", "", from_dict=action)[0]
            dmg2 = self.getAttribute("attack_damage2", "", from_dict=action)[0]
            dmg_type = self.getAttribute("attack_damagetype", "", from_dict=action)[0]
            dmg2_type = self.getAttribute("attack_damagetype2", "", from_dict=action)[0]

            match = re.search(r"DC (\d+) (.*?) saving throw", description)
            if match:
                attack.save.ability = ItemAbility.fromString(match.group(2))
                if attack.save.ability != ItemAbility.NONE:
                    attack.save.dc = int(match.group(1))
                    attack.save.scaling = "flat"
                    attack.type = ItemAttack.SAVE
            if attack_flag:
                has_attack = True
                attack.type = ItemAttack.MELEE_WEAPON if atktype == "Melee" else ItemAttack.RANGED_WEAPON
                if dmg != "":
                    attack.damages.addDamage(dmg, dmg_type.lower())
                if dmg2 != "":
                    attack.damages.addDamage(dmg2, dmg2_type.lower())
                proficiency_bonus = self.getProficiencyBonus()
                for ability in ["str", "dex", "con", "wis", "int", "cha"]:
                    mod = self._actor_abilities[ability]["mod"]
                    if mod + proficiency_bonus == tohit:
                        attack.ability = ItemAbility.fromString(ability)
                        break
                else:
                    # TODO: FVTT 0.4.3 so far will still force strength ability to get added
                    # even if ability is set to EMPTY
                    attack.ability = ItemAbility.STRENGTH
                    attack.bonus = tohit - self._actor_abilities["str"]["mod"]
            else:
                atktype = "None"
        
        # Build description
        description_block = "<p><strong>" + name_display + "</strong>"
        if onhit:
            description_block += "<em>" + attack_type + " </em>" + tohitrange + ". <em>Hit : </em>" + onhit
        if description != "":
            description_block += ".</p><p>" + description
        description_block += "</p>"

        # Convert range
        self._parseRange(activation, atk_range)

        # Convert Target
        self._parseTarget(activation, atk_target)

        activation.cost = 1
        activation.activation = activation_type

        is_weapon = has_attack and not proficient
        is_feat = activation_type != ItemActivation.ACTION
        weapon_type = None
        compendium_item = self.findCompendiumItem("Items", name)
        if compendium_item is not None:
            if compendium_item.entity["type"] == "feat":
                is_feat = True
            elif compendium_item.entity["type"] == "weapon":
                is_weapon = True
                weapon_type = compendium_item.entity["data"]["weaponType"]

        if is_feat is False and (has_attack or is_weapon):
            attributes = ItemInventoryAttributes()
            attributes.equipped = True
            weapon = ItemWeapon()
            weapon.proficient = proficient
            weapon.type = weapon_type if is_weapon else ItemWeapon.NATURAL
            self.createItemInventory(items, name, description_block, "weapon", attributes,
                                    activation, attack, weapon)
        else:
            self.createItemFeat(items, name, description_block, activation, attack, None)

    def addPCAction(self, items, action):
        # Skip attacks based on existing spells
        spellid = self.getAttribute("spellid", "", from_dict=action)[0]
        if spellid != "":
            return
        name = self.getAttribute("atkname", "", from_dict=action)[0]
        description = self.getAttribute("atk_desc", "", from_dict=action)[0]
        atk_range = self.getAttribute("atkrange", "", from_dict=action)[0]

        activation = ItemActivation()
        attack = ItemAttack()
        has_attack = False
        proficient = True

        if self._shaped:
            self._parseShapedAttacks(attack, action)
            has_attack = (attack.type == ItemAttack.MELEE_WEAPON or attack.type == ItemAttack.RANGED_WEAPON)
            proficient = self.getAttributeBool("proficiency", True, from_dict=action)
            reachrange = "reach" if attack.type == ItemAttack.MELEE_WEAPON else "range"
            atk_range = self.getAttribute(reachrange, "", from_dict=action)[0]
        else:
            atkmagic = self.getAttributeInt("atkmagic", 0, from_dict=action)
            if self.getAttribute("atkflag", "1", from_dict=action)[0] != "0":
                has_attack = True
                proficient = self.getAttributeBool("atkprofflag", True, from_dict=action)
                atk_attr = self.getAttribute("atkattr_base", "strength", from_dict=action)[0]
                attack.ability = ItemAbility.fromString(atk_attr)
                attack.bonus = self.getAttributeInt("atkmod", 0, from_dict=action)
                if atkmagic != 0:
                    attack.bonus += atkmagic
                attack.type = ItemAttack.MELEE_WEAPON

            for prefix in ["dmg", "dmg2"]:
                if self.getAttributeBool(prefix + "flag", prefix == "dmg", from_dict=action):
                    dmg_base = self.getAttribute(prefix + "base", "", from_dict=action)[0]
                    dmg_type = self.getAttribute(prefix + "type", "", from_dict=action)[0]
                    dmg_attr = self.getAttribute(prefix + "attr", "strength" if prefix == "dmg" else "", from_dict=action)[0]
                    dmg_mod = self.getAttributeInt(prefix + "mod", 0, from_dict=action)
                    if dmg_attr == "spell":
                        ability = self.getSpellcastingAbility()
                    else:
                        ability = ItemAbility.fromString(dmg_attr)
                    dmg = dmg_base
                    if ability != ItemAbility.NONE:
                        dmg += ("" if dmg == "" else " + ") + "@abilities.{}.mod".format(ability)
                    if dmg_mod != 0:
                        dmg += ("" if dmg == "" else " + ") + str(dmg_mod)
                    if prefix == "dmg" and atkmagic != 0:
                        dmg += ("" if dmg == "" else " + ") + str(atkmagic)
                    if dmg != "" or dmg_type != "":
                        attack.damages.addDamage(dmg, dmg_type.lower())
                        if attack.type == ItemAttack.EMPTY:
                            attack.type = ItemAttack.UTILITY

            if self.getAttributeBool("saveflag", False, from_dict=action):
                saveattr = self.getAttribute("saveattr", "strength", from_dict=action)[0]
                savedc = self.getAttribute("savedc", "spell", from_dict=action)[0]
                saveflat = self.getAttributeInt("saveflat", 10, from_dict=action)
                attack.save.ability = ItemAbility.fromString(saveattr)
                if attack.type == ItemAttack.EMPTY:
                    attack.type = ItemAttack.SAVE
                if "saveflat" in savedc:
                    attack.save.dc = saveflat
                elif "spell_save_dc" in savedc:
                    attack.save.dc = self.getAttributeInt("spell_save_dc", 10)
                else:
                    ability = ItemAbility.fromString(savedc)
                    if attack.save.ability != ItemAbility.NONE:
                        mod = self._actor_abilities[attack.save.ability]["mod"]
                        attack.save.dc = 10 + int(mod) + self.getProficiencyBonus()

        # Convert range
        self._parseRange(activation, atk_range)
        
        if atk_range != "" or attack.type != ItemAttack.EMPTY:
            activation.cost = 1
            activation.activation = ItemActivation.ACTION
            
        is_weapon = ("itemid" in action) or (has_attack and not proficient)
        is_feat = False
        weapon_type = None
        compendium_item = self.findCompendiumItem("Items", name)
        if compendium_item is not None:
            if compendium_item.entity["type"] == "feat":
                is_feat = True
            elif compendium_item.entity["type"] == "weapon":
                is_weapon = True
                weapon_type = compendium_item.entity["data"]["weaponType"]

        if is_feat is False and (has_attack or is_weapon):
            attributes = ItemInventoryAttributes()
            attributes.equipped = True
            weapon = ItemWeapon()
            weapon.proficient = proficient
            weapon.type = weapon_type if is_weapon else ItemWeapon.SIMPLE_MELEE
            itemid = self.getAttribute("itemid", "", from_dict=action)[0]
            if itemid != "":
                item = self.getRepeatingAttributes("inventory").get(itemid, {})
                attributes.weight = self.getAttributeInt("itemweight", 1, from_dict=item)
                attributes.quantity = self.getAttributeInt("itemcount", 1, from_dict=item)
                properties = self.getAttribute("itemproperties", "", from_dict=item)[0]
                for prop in properties.split(","):
                    weapon.properties.addFromString(prop.strip())
                if description == "":
                    description = self.getAttributeInt("itemcontent", "", from_dict=item)

            self.createItemInventory(items, name, description, "weapon", attributes,
                                    activation, attack, weapon)
        else:
            self.createItemFeat(items, name, description, activation, attack, None)


    def addActions(self, items):
        if self.isNPC():
            npc_actions = self.getRepeatingAttributes("npcaction")
            for action in npc_actions.values():
                if len(action) > 0:
                    self.addNPCAction(items, action, ItemActivation.ACTION)

            npc_legendary_actions = self.getRepeatingAttributes("npcaction-l")
            for action in npc_legendary_actions.values():
                if len(action) > 0:
                    self.addNPCAction(items, action, ItemActivation.LEGENDARY)

            if self._shaped:
                npc_reactions = self.getRepeatingAttributes("reaction")
                for action in npc_reactions.values():
                    if len(action) > 0:
                        self.addNPCAction(items, action, ItemActivation.REACTION)
                        
                npc_lair_actions = self.getRepeatingAttributes("lairaction")
                for action in npc_lair_actions.values():
                    if len(action) > 0:
                        self.addNPCAction(items, action, ItemActivation.LAIR)

                regional_effects = self.getRepeatingAttributes("regionaleffect")
                for action in regional_effects.values():
                    if len(action) > 0:
                        self.addNPCAction(items, action, ItemActivation.SPECIAL)
        
        # This is mostly for non NPCs if they manually added a custom attack
        # otherwise, most will be filtered out as they'd match existing inventory
        # items or existing spells
        actions = self.getRepeatingAttributes("attack")
        if self._shaped:
            actions.update(self.getRepeatingAttributes("trait"))
            actions.update(self.getRepeatingAttributes("feat"))
            actions.update(self.getRepeatingAttributes("racialtrait"))
            actions.update(self.getRepeatingAttributes("classfeature"))
            actions.update(self.getRepeatingAttributes("offense"))
            actions.update(self.getRepeatingAttributes("utility"))
        for action in actions.values():
            if len(action) == 0:
                continue
            self.addPCAction(items, action)


    def createItemSpell(self, items, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs):
        name = name if name != "" else "<no name>"
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Spells", name)
        item = self._converter.items.createItemSpell(None, name, description,  activation, attack,
                                                    level, school, components, preparation, scaling, **kwargs)

        if compendium_item and compendium_item.entity["type"] != "loot":
            item = self._converter.items.createItemFromCompendium(None, compendium_item, item.entity["data"])
        else:
            item.entity["img"] = compendium_item.entity["img"] if compendium_item else self._avatar_filename
        owned_item = item.addToOwnedList(items)
        self.exportItem(item, "Spells")
        return owned_item

    def addSpells(self, items):
        for level in range(10):
            spells = self.getRepeatingAttributes("spell-{}".format(level if level > 0 else "cantrip"))
            for spell in spells.values():
                if len(spell) == 0:
                    continue
                name = self.getAttribute("spellname", "", from_dict=spell)[0]
                description = self.getAttribute("spelldescription", "", from_dict=spell)[0]
                higherlevel = self.getAttribute("spellathigherlevels", "", from_dict=spell)[0]
                school = self.getAttribute("spellschool", "Abjuration", from_dict=spell)[0].lower()
                hldie = self.getAttribute("spellhldie", "", from_dict=spell)[0]
                hldice = self.getAttribute("spellhldietype", "", from_dict=spell)[0]
                hlbonus = self.getAttribute("spellhlbonus", "", from_dict=spell)[0]
                hlprogression = self.getAttribute("spell_damage_progression", "", from_dict=spell)[0]

                target = self.getAttribute("spelltarget", "", from_dict=spell)[0]
                spellrange = self.getAttribute("spellrange", "", from_dict=spell)[0]
                castingtime = self.getAttribute("spellcastingtime", "", from_dict=spell)[0]
                duration = self.getAttribute("spellduration", "", from_dict=spell)[0]
                atktype = self.getAttribute("spellattack", "None", from_dict=spell)[0]
                materials = self.getAttribute("spellcomp_materials", "", from_dict=spell)[0]
                innate = self.getAttribute("innate", "", from_dict=spell)[0]
                spell_innate = self.getAttribute("spell_innate", "", from_dict=spell)[0]
                concentration = self.getAttributeBool("spellconcentration", "", from_dict=spell)
                ritual = self.getAttributeBool("spellritual", "", from_dict=spell)
                prepared = self.getAttributeBool("spellprepared", 0, from_dict=spell)

                activation = ItemActivation()
                attack = ItemAttack()
                components = ItemSpellComponents()
                preparation = ItemSpellPreparation()
                scaling = ItemSpellScaling()
                if self._shaped:
                    castingtime = self._capitalizeAll(castingtime.replace("_", " "))
                    duration = self._capitalizeAll(duration.replace("_", " "))
                    if "self" in spellrange.lower():
                        target = spellrange
                    self._parseShapedAttacks(attack, spell)
                    if attack.type == ItemAttack.MELEE_WEAPON:
                        attack.type = ItemAttack.MELEE_SPELL
                    elif attack.type == ItemAttack.RANGED_WEAPON:
                        attack.type = ItemAttack.RANGED_SPELL
                else:
                    dmg = self.getAttribute("spelldamage", "", from_dict=spell)[0]
                    dmg2 = self.getAttribute("spelldamage2", "", from_dict=spell)[0]
                    dmg_type = self.getAttribute("spelldamagetype", "", from_dict=spell)[0]
                    dmg_type2 = self.getAttribute("spelldamagetype2", "", from_dict=spell)[0]
                    add_mod = self.getAttribute("spelldmgmod", "", from_dict=spell)[0]
                    healing = self.getAttribute("spellhealing", "", from_dict=spell)[0]
                    save = self.getAttribute("spellsave", "", from_dict=spell)[0]
                    savedc = self.getAttribute("spell_save_dc", "")[0]
                    spell_ability = self.getAttribute("spell_ability", "", from_dict=spell)[0]

                    add_mod = self.getAttributeBool("spelldmgmod", "", from_dict=spell)
                    if dmg != "":
                        if add_mod:
                            dmg += "+ @mod"
                        attack.damages.addDamage(dmg, dmg_type.lower())
                    if dmg2 != "":
                        if add_mod:
                            dmg2 += "+ @mod"
                        attack.damages.addDamage(dmg2, dmg_type2.lower() if dmg_type2 != "" else dmg_type.lower())
                    if healing != "":
                        if add_mod:
                            healing += "+ @mod"
                        attack.damages.addDamage(healing, "healing")

                        
                    # Convert Attack type  
                    attack.ability = ItemAbility.fromString(spell_ability)
                    attack.save.ability = ItemAbility.fromString(save)
                    if attack.save.ability != ItemAbility.NONE:
                        try:
                            attack.save.dc = int(savedc)
                        except:
                            mod = self._actor_abilities[attack.save.ability]["mod"]
                            attack.save.dc = 10 + int(mod) + self.getProficiencyBonus()

                    if atktype == "Ranged":
                        attack.type = ItemAttack.RANGED_SPELL
                    elif atktype == "Melee":
                        attack.type = ItemAttack.MELEE_SPELL
                    elif attack.save.ability != ItemAbility.NONE:
                        attack.type = ItemAttack.SAVE
                    elif healing != "":
                        attack.type = ItemAttack.HEALING
                    else:
                        attack.type = ItemAttack.UTILITY


                # Convert casting time/condition
                castingtime = castingtime.lower()
                match = re.search(r"^\s*(\d+)?\s*(.*)", castingtime)
                if match:
                    if match.group(1):
                        activation.cost = int(match.group(1))
                    castingtime = match.group(2)
                else:
                    activation.cost = 1
                match = re.search(r"^\s*(action|bonus action|reaction|legendary|legendary action|lair|lair action|minutes?|hours?|days?)\s*,?\s*(.*)", castingtime)
                if match:
                    castingtime = match.group(1)
                    activation.condition = match.group(2) or ""
                    if castingtime == "action":
                        activation.activation = ItemActivation.ACTION
                    elif castingtime ==  "bonus action":
                        activation.activation = ItemActivation.BONUS_ACTION
                    elif castingtime == "reaction":
                        activation.activation = ItemActivation.REACTION
                    elif "legendary" in castingtime:
                        activation.activation = ItemActivation.LEGENDARY
                    elif "lair" in castingtime:
                        activation.activation = ItemActivation.LAIR
                    elif "minute" in castingtime:
                        activation.activation = ItemActivation.MINUTE
                    elif "hour" in castingtime:
                        activation.activation = ItemActivation.HOUR
                    elif "day" in castingtime:
                        activation.activation = ItemActivation.DAY
                    else:
                        activation.activation = ItemActivation.SPECIAL

                # Convert preparation mode and innate spellcasting/uses
                if self.isNPC():
                    preparation.mode = ItemSpellPreparation.PREPARED_SPELL
                    preparation.prepared = True
                else:
                    preparation.mode = ItemSpellPreparation.PREPARED_SPELL
                    preparation.prepared = prepared
                innate = innate if innate != "" else spell_innate
                if innate != "":
                    preparation.mode = ItemSpellPreparation.INNATE_SPELLCASTING
                    preparation.prepared = True
                    if activation.condition == "":
                        activation.condition = innate
                    match = re.search(r"(\d)(?:/(day|short|long))?", innate.lower())
                    if match:
                        activation.uses.uses = int(match.group(1))
                        activation.uses.max = int(match.group(1))
                        if match.group(2) == "day":
                            activation.uses.per = ItemUses.PER_DAY
                        elif match.group(2) == "short":
                            activation.uses.per = ItemUses.PER_SHORT_REST
                        elif match.group(2) == "long":
                            activation.uses.per = ItemUses.PER_LONG_REST
                    if "at will" in innate.lower():
                        preparation.mode = ItemSpellPreparation.ALWAYS_AVAILABLE

                # Convert spell school
                school = self._parseSpellSchool(school)

                # Convert Duration
                self._parseDuration(activation, duration)
                
                # Convert range
                self._parseRange(activation, spellrange)

                # Convert Target
                self._parseTarget(activation, target)

                # Convert higher level casting
                if higherlevel != "":
                    description += "\n<strong>Higher Level.</strong>" + higherlevel
                    scaling.mode = ItemSpellScaling.LEVEL if level > 0 else ItemSpellScaling.CANTRIP
                hldie = str(hldie)
                hlbonus = str(hlbonus)
                if hldie == "0":
                    hldie = ""
                    hldice = ""
                if hlbonus == "0":
                    hlbonus == ""
                if hldie != "" or hldice != "" or hlbonus != "":
                    scaling.formula = hldie + hldice + ((" + " + hlbonus) if hlbonus != "" else "")
                    scaling.mode = ItemSpellScaling.LEVEL if level > 0 else ItemSpellScaling.CANTRIP
                if hlprogression == "Cantrip Dice":
                    scaling.mode = ItemSpellScaling.CANTRIP

                # Convert Components and materials
                if self._shaped:
                    comps = self.getAttribute("components", "", from_dict=spell)[0]
                    if "_V" in comps:
                        components.v = True
                    if "_S" in comps:
                        components.s = True
                    if "_M" in comps:
                        components.m = True
                else:
                    if self.getAttributeInt("spellcomp_v", 1, from_dict=spell) != 0:
                        components.v = True
                    if self.getAttributeInt("spellcomp_s", 1, from_dict=spell) != 0:
                        components.s = True
                    if self.getAttributeInt("spellcomp_m", 1, from_dict=spell) != 0:
                        components.m = True
                components.concentration = concentration
                components.ritual = ritual
                components.materials = materials
                components.consumed = "consume" in materials
                cost = re.search(r"(\d+) (?:g|s|c)p", materials)
                if cost:
                    components.cost = int(cost.group(1))
                self.createItemSpell(items, name, description, activation, attack,
                                    level, school, components, preparation, scaling)

    def createItemClass(self, items, name, level, subclass="", **kwargs):
        name = name if name != "" else "<unknown class>"
        compendium_item = self.findCompendiumItem("Classes", name)
        item = self._converter.items.createItemClass(None, name, name, level, subclass, **kwargs)
        if compendium_item and compendium_item.entity["type"] != "loot":
            del item.entity["data"]["saves"]
            del item.entity["data"]["skills"]
            del item.entity["data"]["spellcasting"]
            item = self._converter.items.createItemFromCompendium(None, compendium_item, item.entity["data"])
        else:
            item.entity["img"] = compendium_item.entity["img"] if compendium_item else self._avatar_filename
        return item.addToOwnedList(items)

    def addClasses(self, items):
        if not self.isNPC():
            if self._shaped:
                classes = self.getRepeatingAttributes("class")
                for pc_class in classes.values():
                    if len(pc_class) == 0:
                        continue
                    name = self.getAttribute("name", "", from_dict=pc_class)[0]
                    level = self.getAttributeInt("level", 1, from_dict=pc_class)
                    self.createItemClass(items, name, level)
            else:
                pc_class = self.getAttribute("class", "")[0]
                base_level = self.getAttribute("base_level", "1")[0]
                subclass = self.getAttribute("subclass", "")[0]
                self.createItemClass(items, pc_class, base_level, subclass)
                for i in range(3):
                    flag = self.getAttributeInt("multiclass%d_flag" % (i + 1), 0)
                    if bool(flag):
                        pc_class = self.getAttribute("multiclass%d" % (i + 1), "")[0]
                        level = self.getAttribute("multiclass%d_lvl" % (i + 1), "1")[0]
                        subclass = self.getAttribute("multiclass%d_subclass" % (i + 1), "")[0]
                        self.createItemClass(items, pc_class, level, subclass)

    def _parseShapedAttacks(self, attack, repeating):
        save = ""
        savedc = ""
        atktype = "None"
        
        for prefix in ["attack", "other", "saving_throw", "heal"]:
            toggle_name = prefix + ("_toggle" if prefix != "other" else "_damage_toggle")
            toggle = self.getAttributeBool(toggle_name, False, from_dict=repeating)
            if not toggle:
                continue
            if prefix == "attack":
                attack.bonus = self.getAttributeInt("attack_bonus", 0, from_dict=repeating)
                ability = self.getAttribute("attack_ability", "", from_dict=repeating)[0]
                attack.ability = ItemAbility.fromString(ability)
                attack_type = self.getAttribute("attack_type", "", from_dict=repeating)[0]
                atktype = "Ranged" if "RANGED" in attack_type else "Melee"
            elif prefix == "saving_throw":
                save = self.getAttribute("saving_throw_vs_ability", "", from_dict=repeating)[0]
                savedc = self.getAttribute("saving_throw_dc", "", from_dict=repeating)[0]
                attack.save.ability = ItemAbility.fromString(save)
                if attack.save.ability != ItemAbility.NONE:
                    try:
                        attack.save.dc = int(savedc)
                    except:
                        mod = self._actor_abilities[attack.save.ability]["mod"]
                        attack.save.dc = 10 + int(mod) + self.getProficiencyBonus()
            if prefix == "heal":
                damages = [""]
            else:
                damages = ["_damage", "_second_damage"]
            for i, dmg_prefix in enumerate(damages):
                if i > 0:
                    if not self.getAttributeBool(prefix + dmg_prefix + "_condition", False, from_dict=repeating):
                        continue
                dice = self.getAttributeInt(prefix + dmg_prefix + "_dice", 0, from_dict=repeating)
                die = self.getAttribute(prefix + dmg_prefix + "_die", "", from_dict=repeating)[0]
                bonus = self.getAttribute(prefix + dmg_prefix + "_bonus", "", from_dict=repeating)[0]
                ability = self.getAttribute(prefix + dmg_prefix + "_ability", "", from_dict=repeating)[0]
                dtype = self.getAttribute(prefix + dmg_prefix + "_type", "", from_dict=repeating)[0]
                mod = ItemAbility.fromString(ability)
                value = ""
                if dice > 0 and die != "":
                    value += str(dice) + die
                if mod != ItemAbility.NONE:
                    value += ("" if value == "" else " + ") + "@abilities.{}.mod".format(mod)
                if bonus != "":
                    value += ("" if value == "" else " + ") + str(bonus)
                if prefix == "heal":
                    dtype = "healing"
                if value != "" or dtype != "":
                    attack.damages.addDamage(value, dtype)

        if atktype == "Ranged":
            attack.type = ItemAttack.RANGED_WEAPON
        elif atktype == "Melee":
            attack.type = ItemAttack.MELEE_WEAPON
        elif attack.save.ability != ItemAbility.NONE:
            attack.type = ItemAttack.SAVE
        elif "healing" in map(lambda dmgs: dmgs[1], attack.damages.damages):
            attack.type = ItemAttack.HEALING
        elif len(attack.damages.damages) > 0:
            attack.type = ItemAttack.UTILITY
        else:
            attack.type = ItemAttack.EMPTY

            
        attack.save.ability = ItemAbility.fromString(save)
        if attack.save.ability != ItemAbility.NONE:
            try:
                attack.save.dc = int(savedc)
            except:
                try:
                    mod = self._actor_abilities[attack.save.ability]["mod"]
                    attack.save.dc = 10 + int(mod) + self.getProficiencyBonus()
                except:
                    pass

    def _parseDuration(self, activation, duration):
        duration = duration.lower()
        match = re.search(r"(\d+)", duration)
        if match:
            activation.duration.duration = int(match.group(1))
        if "instant" in duration:
            activation.duration.units = ItemDuration.INSTANTANEOUS
        elif "turn" in duration:
            activation.duration.units = ItemDuration.TURN
        elif "min" in duration:
            activation.duration.units = ItemDuration.MINUTE
        elif "round" in duration:
            activation.duration.units = ItemDuration.ROUND
        elif "hour" in duration:
            activation.duration.units = ItemDuration.HOUR
        elif "day" in duration:
            activation.duration.units = ItemDuration.DAY
        elif "year" in duration:
            activation.duration.units = ItemDuration.YEAR
        elif "until" in duration or "permanent" in duration:
            activation.duration.units = ItemDuration.PERMANENT
        else:
            activation.duration.units = ItemDuration.SPECIAL

    def _parseTarget(self, activation, target):
        target = target.lower()
        match = re.search(r"(\d+)", target)
        if match:
            activation.target.range.range = int(match.group(1))
        if "ft" in target or "feet" in target or "foot" in target:
            activation.target.range.units = ItemRange.FEET
        elif "mi" in target or "mile" in target:
            activation.target.range.units = ItemRange.MILES
        elif "self" in target:
            activation.target.range.units = ItemRange.SELF
        elif "touch" in target:
            activation.target.range.units = ItemRange.TOUCH

        if "sphere" in target:
            activation.target.type = ItemTarget.SPHERE
        elif "radius" in target:
            activation.target.type = ItemTarget.RADIUS
        elif "cylinder" in target:
            activation.target.type = ItemTarget.CYLINDER
        elif "cone" in target:
            activation.target.type = ItemTarget.CONE
        elif "line" in target:
            activation.target.type = ItemTarget.LINE
        elif "cube" in target:
            activation.target.type = ItemTarget.CUBE
        elif "wall" in target:
            activation.target.type = ItemTarget.WALL
        elif "creature" in target:
            activation.target.type = ItemTarget.CREATURE
        elif "object" in target:
            activation.target.type = ItemTarget.OBJECT
        elif "willing" in target or "ally" in target:
            activation.target.type = ItemTarget.ALLY
        elif "enemy" in target:
            activation.target.type = ItemTarget.ENEMY
        elif "space" in target:
            activation.target.type = ItemTarget.SPACE
        elif "self" in target:
            activation.target.type = ItemTarget.SELF

    def _parseSpellSchool(self, school):
        school = school.upper()
        if school == "ABJURATION":
            return ItemSpellSchool.ABJURATION
        if school == "CONJURATION":
            return  ItemSpellSchool.CONJURATION
        if school == "DIVINATION":
            return  ItemSpellSchool.DIVINATION
        if school == "ENCHANTMENT":
            return  ItemSpellSchool.ENCHANTMENT
        if school == "EVOCATION":
            return  ItemSpellSchool.EVOCATION
        if school == "ILLUSION":
            return  ItemSpellSchool.ILLUSION
        if school == "NECROMANCY":
            return  ItemSpellSchool.NECROMANCY
        if school == "TRANSMUTATION":
            return  ItemSpellSchool.TRANSMUTATION
        # Default to abjuration
        return  ItemSpellSchool.ABJURATION

    def _parseRange(self, activation, range):
        range = range.lower()
        match = re.search(r"(\d+)(?:\s*/\s*(\d+))?", range)
        if match:
            activation.range.range = int(match.group(1))
            if match.group(2):
                activation.range.max = int(match.group(2))
        if "self" in range:
            activation.range.units = ItemRange.SELF
        elif "touch" in range:
            activation.range.units = ItemRange.TOUCH
        elif "ft" in range or "feet" in range or "foot" in range:
            activation.range.units = ItemRange.FEET
        elif "mi" in range or "mile" in range:
            activation.range.units = ItemRange.MILES

    def _convertAttributeName(self, name):
        SHAPED_EQUIVALENCE = {
            "npc": "is_npc",
            "npc_challenge": "challenge",
            "npc_ac": "AC",
            "npc_actype": "ac_note",
            "npc_hpbase": "hp_srd",
            "npc_hpformula": "hp_formula",
            "ac": "AC",
            "hp": "HP",
            "npc_speed": "speed_string",
            "speed": "speed_string",
            "spellcasting_ability": "spell_ability",
            "npc_spelldc": "spell_save_DC",
            "spell_save_dc": "spell_save_DC",
            "character_appearance": "appearance",
            "character_backstory": "backstory",
            "class_display": "class_and_level",
            "race_display": "race",
            "experience": "xp",
            "npc_xp": "xp",
            "npc_senses": "senses_string",
            "npc_languages": "languages",
            "npc_immunities": "damage_immunities",
            "npc_resistances": "damage_resistances",
            "npc_vulnerabilities": "damage_vulnerabilities",
            "npc_condition_immunities": "condition_immunities",

            "initiative_bonus": "initiative",
            "strength_save_bonus": "strength_saving_throw_mod_with_sign",
            "dexterity_save_bonus": "dexterity_saving_throw_mod_with_sign",
            "constitution_save_bonus": "constitution_saving_throw_mod_with_sign",
            "intelligence_save_bonus": "intelligence_saving_throw_mod_with_sign",
            "wisdom_save_bonus": "wisdom_saving_throw_mod_with_sign",
            "charisma_save_bonus": "charisma_saving_throw_mod_with_sign",
            "npc_str_save_flag": "strength_saving_throw_proficient",
            "npc_dex_save_flag": "dexterity_saving_throw_proficient",
            "npc_con_save_flag": "constitution_saving_throw_proficient",
            "npc_int_save_flag": "intelligence_saving_throw_proficient",
            "npc_wis_save_flag": "wisdom_saving_throw_proficient",
            "npc_cha_save_flag": "charisma_saving_throw_proficient",
            "npc_str_save": "strength_saving_throw_mod_with_sign",
            "npc_dex_save": "dexterity_saving_throw_mod_with_sign",
            "npc_con_save": "constitution_saving_throw_mod_with_sign",
            "npc_int_save": "intelligence_saving_throw_mod_with_sign",
            "npc_wis_save": "wisdom_saving_throw_mod_with_sign",
            "npc_cha_save": "charisma_saving_throw_mod_with_sign",

            "npc_acrobatics_flag": "acrobatics",
            "npc_acrobatics": "acrobatics",
            "npcd_acrobatics": "acrobatics",
            "npc_animal_handling_flag": "animalhandling",
            "npc_animal_handling": "animalhandling",
            "npcd_animal_handling": "animalhandling",
            "npc_arcana_flag": "arcana",
            "npc_arcana": "arcana",
            "npcd_arcana": "arcana",
            "npc_athletics_flag": "athletics",
            "npc_athletics": "athletics",
            "npcd_athletics": "athletics",
            "npc_deception_flag": "deception",
            "npc_deception": "deception",
            "npcd_deception": "deception",
            "npc_history_flag": "history",
            "npc_history": "history",
            "npcd_history": "history",
            "npc_insight_flag": "insight",
            "npc_insight": "insight",
            "npcd_insight": "insight",
            "npc_intimidation_flag": "intimidation",
            "npc_intimidation": "intimidation",
            "npcd_intimidation": "intimidation",
            "npc_investigation_flag": "investigation",
            "npc_investigation": "investigation",
            "npcd_investigation": "investigation",
            "npc_medicine_flag": "medicine",
            "npc_medicine": "medicine",
            "npcd_medicine": "medicine",
            "npc_nature_flag": "nature",
            "npc_nature": "nature",
            "npcd_nature": "nature",
            "npc_perception_flag": "perception",
            "npc_perception": "perception",
            "npcd_perception": "perception",
            "npc_performance_flag": "performance",
            "npc_performance": "performance",
            "npcd_performance": "performance",
            "npc_persuasion_flag": "persuasion",
            "npc_persuasion": "persuasion",
            "npcd_persuasion": "persuasion",
            "npc_religion_flag": "religion",
            "npc_religion": "religion",
            "npcd_religion": "religion",
            "npc_sleight_of_hand_flag": "sleightofhand",
            "npc_sleight_of_hand": "sleightofhand",
            "npcd_sleight_of_hand": "sleightofhand",
            "npc_stealth_flag": "stealth",
            "npc_stealth": "stealth",
            "npcd_stealth": "stealth",
            "npc_survival_flag": "survival",
            "npc_survival": "survival",
            "npcd_survival": "survival",
            "lvl1_slots_total": "spell_level_1_slots",
            "lvl2_slots_total": "spell_level_2_slots",
            "lvl3_slots_total": "spell_level_3_slots",
            "lvl4_slots_total": "spell_level_4_slots",
            "lvl5_slots_total": "spell_level_5_slots",
            "lvl6_slots_total": "spell_level_6_slots",
            "lvl7_slots_total": "spell_level_7_slots",
            "lvl8_slots_total": "spell_level_8_slots",
            "lvl9_slots_total": "spell_level_9_slots",
            "lvl1_slots_expended": "spell_level_1_slots_expended",
            "lvl2_slots_expended": "spell_level_2_slots_expended",
            "lvl3_slots_expended": "spell_level_3_slots_expended",
            "lvl4_slots_expended": "spell_level_4_slots_expended",
            "lvl5_slots_expended": "spell_level_5_slots_expended",
            "lvl6_slots_expended": "spell_level_6_slots_expended",
            "lvl7_slots_expended": "spell_level_7_slots_expended",
            "lvl8_slots_expended": "spell_level_8_slots_expended",
            "lvl9_slots_expended": "spell_level_9_slots_expended",

            "npc_legendary_actions": "legendary_action_amount",
            "legendary_flag": "legendary_action_amount",

            "spellname": "name",
            "spellcomp": "components",
            "spellconcentration": "concentration",
            "spelldescription": "content",
            "spellathigherlevels": "higher_level",
            "spellduration": "duration",
            "spelllevel": "spelllevel",
            "spellcomp_materials": "materials",
            "spellrange": "range",
            "spellsave": "saving_throw_vs_ability",
            "spellschool": "school",
            "spellcastingtime": "casting_time",
            "spellprepared": "is_prepared",
            "spell_ability": "attack_ability",
            "spellattack": "attack_type",

            "name": "name",
            "name_display": "name",
            "description": "content",
            "desc": "content",
            "attack_tohit": "to_hit",
            "attack_range": "range",
            "attack_onhit": "attack_damage_string",

            "itemname": "name",
            "itemcontent": "content",
            "itemcount": "uses",
            "itemweight": "weight",
            "equipped": "carried",

            "atkname": "name",
            "atk_desc": "content",
            "atkprofflag": "proficiency",
            "atkflag": "attack_toggle"
        }
        return SHAPED_EQUIVALENCE.get(name, name)

    def _convertRepeatingAttributeName(self, name):
        SHAPED_EQUIVALENCE = {
            'npctrait': 'trait',
            'npcaction': 'action',
            'npcaction-l': 'legendaryaction',
            'spell-cantrip': 'spell0',
            'spell-1':'spell1',
            'spell-2':'spell2',
            'spell-3':'spell3',
            'spell-4':'spell4',
            'spell-5': 'spell5',
            'spell-6': 'spell6',
            'spell-7':'spell7',
            'spell-8': 'spell8',
            'spell-9':'spell9',
            'npcreaction': 'reaction',
            'inventory': 'equipment',
            'spell-cantrip': 'spell0',
        }
        return SHAPED_EQUIVALENCE.get(name, name)