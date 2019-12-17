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
        self.light_angle = 360
        self.sight_angle = 360

        if token:
            self.token_name = token.get("name", self.token_name)
            self.token_filename = token.get("imgsrc", self.token_filename)
            show_name = token.get("showname", show_name)
            all_see_name = token.get("showplayers_name", all_see_name)
            def parseInt(name, default):
                try:
                    val = token.get(name, default)
                    return int(val)
                except ValueError:
                    return default
            self.width = parseInt("width", self.width)
            self.height = parseInt("height", self.height)
            self.rotation = parseInt("rotation", self.rotation)
            self.bar1_val = parseInt("bar1_value", self.bar1_val)
            self.bar1_max = parseInt("bar1_max", self.bar1_max)
            self.bar2_val = parseInt("bar2_value", self.bar2_val)
            self.bar2_max = parseInt("bar2_max", self.bar2_max)
            all_see_bar1 = token.get("showplayers_bar1", all_see_bar1)
            all_see_bar2 = token.get("showplayers_bar2", all_see_bar2)
            lradius = token.get("light_radius", 0)
            ldimradius = token.get("light_dimradius", 0)
            self.has_vision = self._token.get("light_hassight", False)
            self.light_angle = parseInt("light_angle", self.light_angle)
            self.sight_angle = parseInt("light_losangle", self.sight_angle)
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
        if self._token.get("light_otherplayers", False):
            self.emits_light = True
            self.emits_dim_light = dim
            self.emits_bright_light = bright
        multiplier = self._token.get("light_multiplier", 1)
        try:
            multiplier = float(multiplier)
        except:
            multiplier = 1
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
        except ValueError:
            g_light_radius = ""
        try:
            g_light_dimradius = float(light_dimradius)
        except ValueError:
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
            except ValueError:
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
        # Roll20 light/sight angles are going downward, FVTT's are going upward... do some magic
        if self.sight_angle != 360 or self.light_angle != 360:
            rotation = (self.rotation + 180) % 360
            lockRotation = (self.rotation == 0)
        else:
            rotation = self.rotation
            lockRotation = False
        return {"flags": {},
                "name": self.token_name,
                "displayName": self.display_name,
                "img": self.token_filename if self.token_filename != "" else "icons/svg/mystery-man.svg",
                "width": self.width / 70.0,
                "height": self.height / 70.0,
                "scale": 1,
                "elevation": 0,
                "rotation": rotation,
                "lockRotation": lockRotation,
                "effects": [], #TODO : support effects. Format is : ["icons/svg/frozen.svg", "icons/svg/skull.svg"], etc..
                "hidden": False,
                "dimLight": self.emits_dim_light,
                "brightLight": self.emits_bright_light,
                "dimSight": self.dim_sight,
                "brightSight": self.bright_sight,
                "sightAngle": self.sight_angle,
                "lightAngle": self.light_angle,
                "vision": self.has_vision,
                "actorId": self.actor_id,
                "actorLink": False,
                "disposition": -1,
                "displayBars": self.display_bars,
                "bar1": {"attribute": "attributes.bar1" if self.bar1_max != 0 or self.bar1_val != 0 else None},
                "bar2": {"attribute": "attributes.bar2" if self.bar2_max != 0 or self.bar2_val != 0 else None},
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

        print("Creating Character : %s" % character["name"])
        self.parseAttributes()
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

        self._avatar_filename = ""
        if character["avatar"] != "":
            if self.getArgument("use_original_image_urls", False):
                self._avatar_filename = character["avatar"]
            else:
                filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "avatar.png")
                if self.getArgument("json", False):
                    (_, self._avatar_filename) = self.downloadResource(character["avatar"], filename)
                else:
                    (_, self._avatar_filename) = self.copyZipFile(filename, filename)

        default_token = character["defaulttoken"] if character["defaulttoken"] != "" else None
        self.token = Token(self._id, character["name"], default_token)
        token_filename = ""
        randomImg = False
        if default_token and default_token.get("imgsrc", "") != "":
            if self.getArgument("use_original_image_urls", False):
                token_filename = default_token["imgsrc"]
            else:
                filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "token.png")
                if self.getArgument("json", False):
                    (_, token_filename) = self.downloadResource(default_token["imgsrc"], filename)
                else:
                    (_, token_filename) = self.copyZipFile(filename, filename)
                if self._avatar_filename == "":
                    self._avatar_filename = token_filename
                if "sides" in default_token and len(default_token["sides"]) > 0:
                    randomImg = True
                    for i in range(len(default_token["sides"])):
                        filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "side_" + str(i) + ".png")
                        if self.getArgument("json", False):
                            (_, token_filename) = self.downloadResource(default_token["sides"][i], filename)
                        else:
                            (_, token_filename) = self.copyZipFile(filename, filename)
                        token_filename = token_filename.replace("side_" + str(i) + ".png", "side_*.png")
            if self._avatar_filename == "":
                self._avatar_filename = token_filename
        if token_filename == "":
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
            if bar1_link == hp_id:
                token["bar1"]["attribute"] = "attributes.hp"
            if bar2_link == hp_id:
                token["bar2"]["attribute"] = "attributes.hp"
        token["randomImg"] = randomImg
        token["actorLink"] = not npc
        del token["effects"]
        del token["hidden"]
        if token["actorLink"]:
            del token["actorData"]["data"]

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
        ])
        owned_items = []
        self.addClasses(owned_items)
        self.addTraits(owned_items)
        self.addSpells(owned_items)
        # Add actions before inventory so attack items get added first
        self.addActions(owned_items)
        self.addInventory(owned_items)

        if self.getArgument("export_as_module", False):
            folder = None
        elif character["archived"] and not self.getArgument("disable_archived", False):
            folder = "archived-characters-folder-id"
        else:
            folder = self.findFolder(character["id"],  self._database._campaign["journalfolder"])

        self.entity = {"_id": self._id,
                       "name": character["name"],
                       "img": self._avatar_filename,
                       "permission": permissions,
                       "data": actor_data,
                       "folder": Entity.normalizeID(folder),
                       "flags": {"dnd5e": {"saveBonus": self._save_bonus}},
                       "sort": index * Entity.SORT_ORDER,
                       "type": "npc" if npc else "character",
                       "token": token,
                       "items": owned_items
                       }

    def getName(self):
        return self._character["name"]

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

    def _capitalizeAll(self, sentence):
        return " ".join(map(lambda x: x.capitalize(), sentence.split(" ")))

    def getAttribute(self, key, default=None, from_dict=None):
        if from_dict is None:
            from_dict = self._attributes
        if self._shaped:
            shaped_key = self._convertAttributeName(key)
            if shaped_key != key and shaped_key in from_dict:
                #print("Replacing {} with shaped key {}".format(key, shaped_key))
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

    def getRepeatingAttributes(self, key):
        if self._shaped:
            shaped_key = self._convertRepeatingAttributeName(key)
            if shaped_key != key and shaped_key in self._repeating:
                #print("Replacing Repeating {} with shaped key {}".format(key, shaped_key))
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
                (_, repeating_type, id, name) = attr["name"].split("_", 3)
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
        print("Parsed attributes for character %s: %s" % (self._character["id"], self._character["name"]))
        keys = list(self._attributes.keys())
        keys.sort()
        for key in keys:
            attr = self._attributes[key]
            print("%s: %s%s" % (key, str(attr[0]), ("(" + str(attr[1]) + ")") if attr[1] != "" else ""))
        print("Repeated attributes for character %s: %s" % (self._character["id"], self._character["name"]))
        for _type in self._repeating:
            print("\n\n****** %s ******" % _type)
            for item in self._repeating[_type]:
                print("\n************************\n\t%s" % item)
                items = self._repeating[_type][item]
                keys = list(items.keys())
                keys.sort()
                for key in keys:
                    attr = items[key]
                    print("\t\t%s: %s%s" % (key, str(attr[0]), ("(" + str(attr[1]) + ")") if attr[1] != "" else ""))
        

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
        proficient = (save == mod + proficiency_bonus + self._save_bonus)
        return {"value": ability,
                "min": 3,
                "proficient": 1 if proficient else 0,
                "mod": mod,
                "save": save
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
        value = self.getAttribute(attribute_name, "on" if default else "")[0]
        enabled = (value == "on") or (value == "1")
        if len(extra) == 0:
            return enabled
        ret = {"value": enabled}
        ret.update(extra)
        return ret

    def createAttributeAC(self):
        ac = self.getAttribute("npc_ac" if self.isNPC() else "ac", 10)[0]
        
        res = {
            "min": 0,
            "value": ac
        }
        if self.isNPC():
            res["formula"] = self.getAttribute("npc_actype", "")[0]
        return res

    def createAttributeHP(self):
        hp = self.getAttribute("hp", 10)
        if self.isNPC():
            if hp[2] == None:
                hp = self.getAttribute("npc_hpbase", 10)
            value = hp[1]
            max = hp[1]
            formula = self.getAttribute("npc_hpformula", "")[0]
        else:
            value = hp[0]
            max = hp[1]
            formula = ""
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

    def createAttributeSpeed(self):
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
        return {
            "value": speed,
            "special": special
        }
    def createAttributeSpellcasting(self):
        spellcasting_ability = ""
        attribute = self.getAttribute("spellcasting_ability", None)[0]
        if attribute:
            match = re.search(r"@{(.*)}", attribute)
            if match:
                spellcasting_ability = match.group(1)[0:3].lower()
            else:
                spellcasting_ability = attribute[0:3].lower()
        if spellcasting_ability not in ["str", "dex", "con", "int", "wis", "cha"]:
            spellcasting_ability = ""
        return spellcasting_ability

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
            ("speed", self.createAttributeSpeed()),
            ("spellcasting", self.createAttributeSpellcasting()),
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
        for (attrib, label) in [("personality_traits", "Personality Traits"),
                                ("ideals", "Ideals"),
                                ("bonds", "Bonds"),
                                ("flaws", "Flaws"),
                                ("character_appearance", "Character Appearance"),
                                ("character_backstory", "Character Backstory"),
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
                    ("type", self.getNPCType()[1]),
                    ("environment", ""),
                    ("cr", self.getChallengeRating()),
                    ("xp", self.createAttributeNumber("Kill Experience", "npc_xp", 0)),
                    ("source", self.getArgument("npc_source", "Roll 20"))
                    ])
        else:
            details.update([
                    ("background", self.getAttribute("background", "")[0]),
                    ("level", self.createAttributeNumber("Character Level", "level", 1, {"min": 1, "max": 20})),
                    ("xp", self.createDetailXP()),
                    ("trait", self.getAttribute("personality_traits", "")[0]),
                    ("ideal", self.getAttribute("ideals", "")[0]),
                    ("bond", self.getAttribute("bonds", "")[0]),
                    ("flaw", self.getAttribute("flaws", "")[0])
                    ])
        return details

    def createActorSkill(self, label, attribute_name, ability):
        base_mod = self.getAttributeInt(ability + "_mod", 0)
        mod = self.getAttributeInt("npcd_" + attribute_name if self.isNPC() else attribute_name + "_bonus", base_mod)
        prof = self.getProficiencyBonus()

        if mod >= base_mod + prof * 2:
            value = 2
        elif mod >= base_mod + prof:
            value = 1
        elif mod >= base_mod + prof // 2:
            value = 0.5
        else:
            value = 0

        bonus = (base_mod + prof * value) - mod
        passive = mod + 10

        # An NPC might have overriden the PP in its senses
        if label == "Perception" and self.isNPC():
            senses = self.getAttribute("npc_senses", "")[0]
            match = re.search(r"passive perception (\d+)", senses)
            if match:
                passive = int(match.group(1))

        return {
            "value": value,
            "ability": ability.lower()[0:3],
            "bonus": bonus,
            "mod": mod,
            "passive": passive
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
                storage_name = self.getAttribute("storage_name", None, from_dict=skill)[0]
                name = self.getAttribute("name", storage_name, from_dict=skill)[0]
                ability = self.getAttribute("ability", "str", from_dict=skill)[0]
                ability_key = self.getAttribute("ability_key", ability, from_dict=skill)[0]
                mod = self.getAttributeInt("total_with_sign", 0, from_dict=skill)
                base_mod = 0
                if ability_key:
                    base_mod = self._actor_abilities[ability_key.lower()[0:3]]["mod"]
                    
                if mod >= base_mod + prof * 2:
                    value = 2
                elif mod >= base_mod + prof:
                    value = 1
                elif mod >= base_mod + prof // 2:
                    value = 0.5
                else:
                    value = 0

                bonus = (base_mod + prof * value) - mod

                passive = mod + 10
                if name is not None:
                    key = name.lower()
                    if type(storage_name) == str:
                        key = skill_keys.get(storage_name.lower(), key)
                    # An NPC might have overriden the PP in its senses
                    if key == "prc" and self.isNPC():
                        senses = self.getAttribute("npc_senses", "")[0]
                        match = re.search(r"passive perception (\d+)", senses)
                        if match:
                            passive = int(match.group(1))
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

        return dnd5e_sizes.get(size.lower(), "med")

    def createTraitSenses(self):
        if self.isNPC():
            npc_senses = self.getAttribute("npc_senses", "")[0].split(",")
            npc_senses = list(map(lambda x: x.strip(), npc_senses))
            for i, sense in enumerate(npc_senses):
                if sense.strip().startswith("passive perception"):
                    npc_senses.pop(i)
                    break
            senses = ", ".join(npc_senses)
        else:
            senses = ""

        return senses

    def _addKnownToArray(self, known_list, name, array, custom):
        name = self._capitalizeAll(name.strip())
        if name == "":
            return
        known = known_list.get(name, None)
        if known:
            array.append(known)
        else:
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
                #print("Proficienty : {} = {}".format(id, prof))
                if self.getAttribute("prof_type", "", from_dict=prof)[0] == "LANGUAGE":
                    language = self.getAttribute("name", "", from_dict=prof)[0]
                    for lang in language.split(","):
                        self._addKnownToArray(known_languages, lang, languages, custom)
        for lang in character_languages.split(","):
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
        sections = damages.split(";")
        for i, damage in enumerate(sections):
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
            "Light Armor": "lgt",
            "Medium Armor": "med",
            "Heavy Armor": "hvy",
            "Shields": "shl"
        }

        proficiencies = []
        custom = []
        for prof in self.getRepeatingAttributes("proficiencies").values():
            #print("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "ARMOR":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)

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
            #print("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "WEAPON":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)

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
            #print("Proficienty : {} = {}".format(id, prof))
            if self.getAttribute("prof_type", "", from_dict=prof)[0] == "TOOL":
                prof_name = self.getAttribute("name", "", from_dict=prof)[0]
                for proficiency in prof_name.split(","):
                    self._addKnownToArray(known_profs, proficiency, proficiencies, custom)

        return {
            "value": proficiencies,
            "custom": ", ".join(custom)
        }

    def createActorTraits(self):
        traits =  OrderedDict([
            ("size", self.createTraitSize()),
            ("senses", self.createTraitSenses()),
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
                name = self.getAttribute("name", "", from_dict=currency)[0]
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
            spells["spell%d" % level]  = {"value": current, "max": max}
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

    def createItemInventory(self, items, name, description, inventory_type, **kwargs):
        name = name if name != "" else "<no name>"
        description = Entity.textToHtml(description)
        compendium_item = self.findCompendiumItem("Items", name)
        if compendium_item and compendium_item.entity["type"] == inventory_type:
            kwargs["description"] = description
            item = self._converter.items.createItemFromCompendium(None, compendium_item, **kwargs)
        else:
            item = self._converter.items.createItemInventory(None, name, description, inventory_type, **kwargs)
            item.entity["img"] = self._avatar_filename
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

    def addInventory(self, items):
        for item in self.getRepeatingAttributes("inventory").values():
            if self.getAttributeInt("hasattack", 0, from_dict=item) == 1:
                continue
            name = self.getAttribute("itemname", "", from_dict=item)[0]
            content = self.getAttribute("itemcontent", "", from_dict=item)[0]
            count = self.getAttributeInt("itemcount", 1, from_dict=item)
            weight = self.getAttributeInt("itemweight", 1, from_dict=item)
            mods = self.getAttribute("itemmodifiers", "Item Type: Items", from_dict=item)[0]
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
                except:
                    pass
            item_type = modifiers.get("Item Type", "")
            armor = modifiers.get("AC", 0)
            damage = modifiers.get("Damage", "")
            damage_type = modifiers.get("Damage Type", "").lower()
            damage2 = modifiers.get("Alternate Damage", "")
            damage2_type = modifiers.get("Altermate Damage Type", "").lower()
            if damage2 == "":
                damage2 = modifiers.get("Secondary Damage", "")
                damage2_type = modifiers.get("Secondary Damage Type", "").lower()
            weapon_range = modifiers.get("Range", "")

            if item_type in ["Light Armor", "Medium Armor", "Heavy Armor", "Shield"] or armor != 0:
                try:
                    armor = int(armor)
                except ValueError:
                    pass
                armor_type = item_type.split(" ")[0].lower()
                if armor_type not in ["light", "medium", "heavy", "shielf"]:
                    armor_type = "bonus"
                kwargs = {
                    "armor": armor,
                    "armorType": armor_type,
                    "equipped": bool(self.getAttributeInt("equipped", 1, from_dict=item)),
                    "proficient": False,
                }
                for prof in self.getRepeatingAttributes("proficiencies").values():
                    if self.getAttribute("prof_type", "", from_dict=prof)[0] == "ARMOR":
                        prof_name = self.getAttribute("name", "", from_dict=prof)[0].lower()
                        for proficiency in prof_name.split(","):
                            if proficiency == item_type.lower() or proficiency == armor_type:
                                kwargs["proficient"] = True
                self.createItemInventory(items, name, content, "equipment", weight=weight, quantity=count, **kwargs)
            elif item_type in ["Melee Weapon", "Ranged Weapon", "Ammunition"] or damage != "":
                kwargs = {
                    "properties": self.getAttribute("itemproperties", "", from_dict=item)[0],
                    "damage": damage,
                    "damageType": damage_type,
                    "damage2": damage2,
                    "damage2Type": damage2_type,
                    "range": weapon_range,
                    "ability": "dex" if item_type == "Ranged Weapon" else "str"
                }
                item = self.createItemInventory(items, name, content, "weapon", weight=weight, quantity=count, **kwargs)
                if item["data"]["weaponType"]["value"] == "":
                    # Don't override the weapon type if taken from compendium, set it otherwise
                    if item_type == "Ammunition":
                        weaponType="ammo"
                    elif item_type == "Melee Weapon":
                        weaponType = "simpleM"
                    elif item_type == "Ranged Weapon":
                        weaponType = "simpleR"
                    else:
                        weaponType = "improv"

                    item["data"]["weaponType"]["value"] = weaponType
                weaponType = item["data"]["weaponType"]["value"]
                
                proficient = False
                for prof in self.getRepeatingAttributes("proficiencies").values():
                    if self.getAttribute("prof_type", "", from_dict=prof)[0] == "WEAPON":
                        prof_name = self.getAttribute("name", "", from_dict=prof)[0].lower()
                        for proficiency in prof_name.split(","):
                            if proficiency.startswith(name.lower()) or \
                                (proficiency.startswith("simple") and weaponType.startswith("simple")) or \
                                (proficiency.startswith("martial") and weaponType.startswith("martial")):
                                proficient = True
                                break

                item["data"]["proficient"]["value"] = proficient
            else:
                if item_type not in ["Adventuring Gear", "Items", "Gear"]:
                    print("Unknown item properties : ", name, modifiers)
                self.createItemInventory(items, name, content, "loot", weight=weight, quantity=count)


    def createItemFeat(self, items, name, description, activation, attack, recharge, **kwargs):
        name = name if name != "" else "<no name>"
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Class Features", name)
        if compendium_item:
            kwargs["description"] = description
            kwargs.update(activation.getDict() if activation else {})
            kwargs.update(attack.getDict() if attack else{})
            kwargs.update(recharge.getDict() if recharge else {})
            item = self._converter.items.createItemFromCompendium(None, compendium_item, **kwargs)
        else:
            item = self._converter.items.createItemFeat(None, name, description, activation, attack, recharge, **kwargs)
            item.entity["img"] = self._avatar_filename
        owned_item = item.addToOwnedList(items)
        self.exportItem(item, "Abilities & Feats")
        return owned_item

    def addTraits(self, items):
        if self.isNPC():
            npc_traits = self.getRepeatingAttributes("npctrait")
            for trait in npc_traits.values():
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("desc", "", from_dict=trait)[0]
                self.createItemFeat(items, name, description, None, None, None)

            npc_reactions = self.getRepeatingAttributes("npcreaction")
            for trait in npc_reactions.values():
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("desc", "", from_dict=trait)[0]
                activation = ItemActivation(ItemActivation.REACTION, 1)
                self.createItemFeat(items, name, description, activation, None, None)
        else:
            traits = self.getRepeatingAttributes("traits")
            for trait in traits.values():
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("description", "", from_dict=trait)[0]
                source = self.getAttribute("source", "Racial", from_dict=trait)[0]
                source_type = self.getAttribute("source_type", "", from_dict=trait)[0]
                self.createItemFeat(items, name, description, None, None, None, source=source, requirements=source_type)

    def addNPCAction(self, items, action, legendary):
        name = self.getAttribute("name", "", from_dict=action)[0]
        name_display = self.getAttribute("name_display", "", from_dict=action)[0]
        attack_type = self.getAttribute("attack_type_display", "", from_dict=action)[0]
        tohitrange = self.getAttribute("attack_tohitrange", "", from_dict=action)[0]
        onhit = self.getAttribute("attack_onhit", "", from_dict=action)[0]
        description = self.getAttribute("description", "", from_dict=action)[0]
        dmg = self.getAttribute("attack_damage", "", from_dict=action)[0]
        dmg2 = self.getAttribute("attack_damage2", "", from_dict=action)[0]
        dmg_type = self.getAttribute("attack_damagetype", "", from_dict=action)[0]
        dmg2_type = self.getAttribute("attack_damagetype2", "", from_dict=action)[0]
        tohit = self.getAttributeInt("attack_tohit", 0, from_dict=action)
        atk_range = self.getAttribute("attack_range", "", from_dict=action)[0]
        atk_target = self.getAttribute("attack_target", "", from_dict=action)[0]
        description_block = "<strong>" + name_display + "</strong>"
        if dmg != "":
            description_block += "<em>" + attack_type + " </em>" + tohitrange + ". <em>Hit : </em>" + onhit
        if description != "":
            description_block += ". " + description
        match = re.search(r"DC (\d+) (.*?) saving throw", description)
        save = ""
        if match:
            save = match.group(2).lower()[0:3]
        atk_ability = "str"
        proficiency_bonus = self.getProficiencyBonus()
        for ability in ["strength", "dexterity", "constitution", "wisdom", "intelligence", "charisma"]:
            mod = self.getAttributeInt(ability.lower() + "_mod", 0)
            if mod + proficiency_bonus == tohit:
                atk_ability = ability[0:3]
                break
        compendium_item = self.findCompendiumItem("Items", name)
        if (compendium_item is not None and "weaponType" in compendium_item.entity["data"]) or (dmg2 != "" and save == ""):
            # Let's make this into a weapon attack due to alternate damage
            # using attack_damage includes the modifier which FVTT adds already for weapon attacks
            dmg = self.getAttribute("attack_crit", "", from_dict=action)[0]
            dmg2 = self.getAttribute("attack_crit2", "", from_dict=action)[0]
            kwargs = {
                    "weaponType": "natural",
                    "damage": dmg,
                    "damageType": dmg_type.lower(),
                    "damage2": dmg2,
                    "damage2Type": dmg2_type.lower(),
                    "range": atk_range,
                    "ability": atk_ability,
                    "proficient": True
            }
            self.createItemInventory(items, name, description_block, "weapon", **kwargs)
        else:
            kwargs = {
                    "ability": atk_ability,
                    "target": atk_target,
                    "range": atk_range,
                    "damage": dmg,
                    "damageType": dmg_type.lower(),
                    "save": save
            }

            feat_type = "attack" if dmg != "" else "ability"
            if legendary:
                feat_type = "legendary"
                name = "[Legendary]" + name
            #self.createItemFeat(items, name, description_block, feat_type, **kwargs)

    def addPCAction(self, items, attack):
        name = self.getAttribute("atkname", "", from_dict=attack)[0]
        description = self.getAttribute("atk_desc", "", from_dict=attack)[0]
        dmg = dmg_type = dmg_attr = dmg2 = dmg2_type = dmg2_attr = atk_attr = atk_range = saveattr = ""

        if self._shaped:
            atkmagic = ""
            if self.getAttributeInt("attack_toggle", 1, from_dict=attack) != 0:
                atk_attr = self.getAttribute("attack_ability", "strength", from_dict=attack)[0].lower()
            atk_range = self.getAttribute("range", "", from_dict=attack)[0]
            if atk_range == "":
                atk_range = self.getAttribute("reach", "", from_dict=attack)[0]
            for prefix in ["attack", "attack_second", "other", "heal", "saving_throw"]:
                toggle_name = "attack_toggle" if prefix.startswith("attack") else (prefix + "_damage_toggle")
                toggle = bool(self.getAttributeInt(toggle_name, 0, from_dict=attack))
                if not toggle:
                    continue
                dice = self.getAttribute(prefix + "_damage_dice", "", from_dict=attack)[0]
                die = self.getAttribute(prefix + "_damage_die", "", from_dict=attack)[0]
                bonus = self.getAttribute(prefix + "_damage_bonus", "", from_dict=attack)[0]
                ab = self.getAttribute(prefix + "_damage_ability", "", from_dict=attack)[0]
                dtype = self.getAttribute(prefix + "_damage_type", "", from_dict=attack)[0]
                mod = 0
                try:
                    if ab != "":
                        mod = self._actor_abilities[ab.lower()[0:3]]["mod"]
                except:
                    pass
                value = "{}{}{}{}".format(dice, die, "" if mod == 0 else " + {}".format(mod), "" if bonus else " + {}".format(bonus))
                if prefix == "attack" or prefix == "saving_throw":
                    dmg = value
                    dmg_type = dtype
                    dmg_attr = ab
                elif prefix == "other" or prefix == "attack_second":
                    dmg2 = value
                    dmg2_type = dtype
                    dmg2_attr = ab
                elif prefix == "heal":
                    dmg = value
                    dmg_type = "healing"
                    dmg_attr = ab
        else:
            if self.getAttribute("dmgflag", "1", from_dict=attack)[0] != "0":
                dmg = self.getAttribute("dmgbase", "", from_dict=attack)[0]
                dmg_type = self.getAttribute("dmgtype", "", from_dict=attack)[0]
                dmg_attr = self.getAttribute("dmgattr", "strength", from_dict=attack)[0]
            if self.getAttribute("dmg2flag", "0", from_dict=attack)[0] != "0":
                dmg2 = self.getAttribute("dmg2base", "", from_dict=attack)[0]
                dmg2_type = self.getAttribute("dmg2type", "", from_dict=attack)[0]
                dmg2_attr = self.getAttribute("dmg2attr", "", from_dict=attack)[0]
            if self.getAttribute("atkflag", "1", from_dict=attack)[0] != "0":
                atk_attr = self.getAttribute("atkattr_base", "strength", from_dict=attack)[0]
            proficient = str(self.getAttribute("atkprofflag", "1", from_dict=attack)[0]) != "0"
            atk_range = self.getAttribute("atkrange", "", from_dict=attack)[0]
            atkmagic = self.getAttribute("atkmagic", "", from_dict=attack)[0]
            if atkmagic != "" and dmg != "":
                dmg = "%s + %s" % (dmg, atkmagic)
            if self.getAttribute("saveflag", "0", from_dict=attack)[0] != "0":
                saveattr = self.getAttribute("saveattr", "", from_dict=attack)[0]
        atk_ability = ""
        dmg_ability = ""
        dmg2_ability = ""
        for ability in ["strength", "dexterity", "constitution", "wisdom", "intelligence", "charisma"]:
            if ability in str(atk_attr):
                atk_ability = ability[0:3]
            if ability in str(dmg_attr):
                dmg_ability = ability[0:3]
            if ability in str(dmg2_attr):
                dmg2_ability = ability[0:3]
        save = saveattr.lower()[0:3]
        if dmg2_ability != "":
            dmg2 += " + {}".format(self._actor_abilities[dmg2_ability]["mod"])
        # If second damage but no ability for the first damage, then it can't be a weapon attack
        if dmg2 != "" and dmg_ability == "":
            dmg += " + " + dmg2
            dmg2 = ""
        if (dmg2 != "" or atkmagic != "" or "itemid" in attack) and (save == "" or not proficient):
            # Let's make this into a weapon attack due to alternate damage, or if not proficient
            kwargs = {
                    "weaponType": "simpleM",
                    "bonus": atkmagic,
                    "damage": dmg,
                    "damageType": dmg_type.lower(),
                    "damage2": dmg2,
                    "damage2Type": dmg2_type.lower(),
                    "range": atk_range,
                    "ability": atk_ability,
                    "proficient": proficient
            }
            self.createItemInventory(items, name, description, "weapon", **kwargs)
        else:
            if dmg_ability != "":
                dmg += " + {}".format(self._actor_abilities[dmg_ability]["mod"])
            kwargs = {
                    "ability": atk_ability,
                    "target": "",
                    "range": atk_range,
                    "damage": dmg,
                    "damageType": dmg_type.lower(),
                    "save": save
            }
            #self.createItemFeat(items, name, description, "attack" if atk_ability != "" else "passive", **kwargs)


    def addActions(self, items):
        if self.isNPC():
            npc_actions = self.getRepeatingAttributes("npcaction")
            npc_legendary_actions = self.getRepeatingAttributes("npcaction-l")
            for action in npc_actions.values():
                self.addNPCAction(items, action, False)
            for action in npc_legendary_actions.values():
                self.addNPCAction(items, action, True)
        
        # This is mostly for non NPCs if they manually added a custom attack
        # otherwise, most will be filtered out as they'd match existing inventory
        # items or existing spells
        attacks = self.getRepeatingAttributes("attack")
        for attack in attacks.values():
            # Skip existing spells and items
            if "spellid" in attack:
                continue
            self.addPCAction(items, attack)
        if self._shaped:
            attacks = self.getRepeatingAttributes("offense")
            attacks.update(self.getRepeatingAttributes("attacher"))
            attacks.update(self.getRepeatingAttributes("classfeature"))
            for attack in attacks.values():
                self.addPCAction(items, attack)


    def createItemSpell(self, items, name, description, spell_type, school, level, **kwargs):
        name = name if name != "" else "<no name>"
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Spells", name)
        if compendium_item:
            kwargs["description"] = description
            item = self._converter.items.createItemFromCompendium(None, compendium_item, **kwargs)
        else:
            item = self._converter.items.createItemSpell(None, name, description, spell_type, school, level, **kwargs)
            item.entity["img"] = self._avatar_filename
        owned_item = item.addToOwnedList(items)
        self.exportItem(item, "Spells")
        return owned_item

    def addSpells(self, items):
        for level in range(10):
            spells = self.getRepeatingAttributes("spell-{}".format(level if level > 0 else "cantrip"))
            for spell in spells.values():
                name = self.getAttribute("spellname", "", from_dict=spell)[0]
                description = self.getAttribute("spelldescription", "", from_dict=spell)[0]
                higherlevel = self.getAttribute("spellathigherlevels", "", from_dict=spell)[0]
                school = self.getAttribute("spellschool", "Abjuration", from_dict=spell)[0].lower()
                save = self.getAttribute("spellsave", "", from_dict=spell)[0]

                dmg = self.getAttribute("spelldamage", "", from_dict=spell)[0]
                dmg2 = self.getAttribute("spelldamage2", "", from_dict=spell)[0]
                dmg_type = self.getAttribute("spelldamagetype", "", from_dict=spell)[0]
                healing = self.getAttribute("spellhealing", "", from_dict=spell)[0]
                spell_ability = self.getAttribute("spell_ability", "", from_dict=spell)[0]

                output = self.getAttribute("spelloutput", "", from_dict=spell)[0]
                target = self.getAttribute("spelltarget", "", from_dict=spell)[0]
                spellrange = self.getAttribute("spellrange", "", from_dict=spell)[0]
                castingtime = self.getAttribute("spellcastingtime", "", from_dict=spell)[0]
                duration = self.getAttribute("spellduration", "", from_dict=spell)[0]
                materials = self.getAttribute("spellcomp_materials", "", from_dict=spell)[0]
                innate = self.getAttribute("innate", "", from_dict=spell)[0]
                spell_innate = self.getAttribute("spell_innate", "", from_dict=spell)[0]
                concentration = self.getAttribute("spellconcentration", "", from_dict=spell)[0] != ""
                ritual = self.getAttribute("spellritual", "", from_dict=spell)[0] != ""
                prepared = self.getAttributeInt("spellprepared", 0, from_dict=spell)

                if self._shaped:
                    prepared = prepared == "Yes"
                    castingtime = self._capitalizeAll(castingtime.replace("_", " "))
                    duration = self._capitalizeAll(duration.replace("_", " "))
                    dmg = dmg2 = dmg_type = healing = ""
                    for prefix in ["attack", "attack_second", "other", "heal", "saving_throw"]:
                        toggle_name = "attack_toggle" if prefix.startswith("attack") else (prefix + "_damage_toggle")
                        toggle = bool(self.getAttributeInt(toggle_name, 0, from_dict=spell))
                        if not toggle:
                            continue
                        dice = self.getAttribute(prefix + "_damage_dice", "", from_dict=spell)[0]
                        die = self.getAttribute(prefix + "_damage_die", "", from_dict=spell)[0]
                        bonus = self.getAttribute(prefix + "_damage_bonus", "", from_dict=spell)[0]
                        ab = self.getAttribute(prefix + "_damage_ability", "", from_dict=spell)[0]
                        dtype = self.getAttribute(prefix + "_damage_type", "", from_dict=spell)[0]
                        mod = 0
                        try:
                            if ab != "":
                                mod = self._actor_abilities[ab.lower()[0:3]]["mod"]
                        except:
                            pass
                        value = "{}{}{}{}".format(dice, die, "" if mod == 0 else " + {}".format(mod), "" if bonus else " + {}".format(bonus))
                        if prefix == "attack" or prefix == "saving_throw":
                            dmg = value
                            dmg_type = dtype
                        elif prefix == "other" or prefix == "attack_second":
                            dmg2 = value
                        elif prefix == "heal":
                            healing = value
                else:
                    prepared = bool(prepared)
                if self.isNPC():
                    prepared = True

                save = save.lower()[0:3]
                school = "trs" if school == "transmutation" else school[0:3]
                if save != "":
                    spell_type = "save"
                elif healing != "":
                    spell_type = "heal"
                    dmg = healing
                    dmg_type = "healing"
                elif output == "ATTACK":
                    spell_type = "attack"
                else:
                    spell_type = "utility"
                if dmg2 != "":
                    dmg += "+ {}".format(dmg2)
                if higherlevel != "":
                    description += "\n<strong>Higher Level.</strong>" + higherlevel
                use_ability = "" # spell casting ability
                for ability in ["strength", "dexterity", "constitution", "wisdom", "intelligence", "charisma"]:
                    if ability in spell_ability:
                        use_ability = ability[0:3]
                        break
                components = []
                if self._shaped:
                    comps = self.getAttribute("components", "", from_dict=spell)[0]
                    if "_V" in comps:
                        components.append("V")
                    if "_S" in comps:
                        components.append("S")
                    if "_M" in comps:
                        components.append("M")
                else:
                    if self.getAttributeInt("spellcomp_v", 1, from_dict=spell) != 0:
                        components.append("V")
                    if self.getAttributeInt("spellcomp_s", 1, from_dict=spell) != 0:
                        components.append("S")
                    if self.getAttributeInt("spellcomp_m", 1, from_dict=spell) != 0:
                        components.append("M")
                if innate != "" or spell_innate != "":
                    name += " (" + (innate if innate != "" else spell_innate) + ")"
                kwargs = {
                    "target": target,
                    "range": spellrange,
                    "time": castingtime,
                    "duration": duration,
                    "damage": dmg,
                    "damageType": dmg_type.lower(),
                    "save": save,
                    "ability": use_ability,
                    "materials": materials,
                    "components": ", ".join(components),
                    "concentration": concentration,
                    "ritual": ritual,
                    "prepared": prepared
                }
                self.createItemSpell(items, name, description, spell_type, school, level, **kwargs)

    def createItemClass(self, items, name, level, subclass=""):
        name = name if name != "" else "<unknown class>"
        compendium_item = self.findCompendiumItem("Classes", name)
        kwargs = {"subclass": subclass}
        if compendium_item:
            kwargs["levels"] = level
            item = self._converter.items.createItemFromCompendium(None, compendium_item, **kwargs)
        else:
            item = self._converter.items.createItemClass(None, name, name, level, **kwargs)
            item.entity["img"] = self._avatar_filename
        return item.addToOwnedList(items)

    def addClasses(self, items):
        if not self.isNPC():
            if self._shaped:
                classes = self.getRepeatingAttributes("class")
                for pc_class in classes.values():
                    name = self.getAttribute("name", "", from_dict=pc_class)[0]
                    level = self.getAttributeInt("level", "", from_dict=pc_class)
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

            "name": "name",
            "namedisplay": "name",
            "description": "content",
            "desc": "content",
            "attacktohit": "attackbonus",
            "attackdamage": "",
            "attackdamagetype": "attackdamagetype",
            "attackdamage2": "",
            "attackdamagetype2": "seconddamageability",
            "attackrange": "reach",

            "itemname": "name",
            "itemcontent": "content",
            "itemcount": "uses",
            "itemweight": "weight",

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