from .base import DatabaseFile, Entity
from .journal import Handout
from collections import OrderedDict
import re
import os
import copy

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

        if token:
            self.token_name = token.get("name", self.token_name)
            self.token_filename = token.get("imgsrc", self.token_filename)
            show_name = token.get("showname", show_name)
            all_see_name = token.get("showplayers_name", all_see_name)
            self.width = token.get("width", self.width)
            self.height = token.get("height", self.height)
            self.rotation = token.get("rotation", self.rotation)
            def parseInt(name, default):
                try:
                    val = token.get(name, default)
                    return int(val)
                except:
                    return default
            self.bar1_val = parseInt("bar1_value", self.bar1_val)
            self.bar1_max = parseInt("bar1_max", self.bar1_max)
            self.bar2_val = parseInt("bar2_value", self.bar2_val)
            self.bar2_max = parseInt("bar2_max", self.bar2_max)
            all_see_bar1 = token.get("showplayers_bar1", all_see_bar1)
            all_see_bar2 = token.get("showplayers_bar2", all_see_bar2)
            lradius = token.get("light_radius", 0)
            ldimradius = token.get("light_dimradius", 0)
            self.has_vision = self._token.get("light_hassight", False)
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

    def getDict(self):
        return {"flags": {},
                "name": self.token_name,
                "displayName": self.display_name,
                "img": self.token_filename if self.token_filename != "" else "icons/svg/mystery-man.svg",
                "width": self.width / 70.0,
                "height": self.height / 70.0,
                "scale": 1,
                "elevation": 0,
                "rotation": self.rotation,
                "lockRotation": False,
                "effects": [], #TODO : support effects. Format is : ["icons/svg/frozen.svg", "icons/svg/skull.svg"], etc..
                "hidden": False,
                "dimLight": self.emits_dim_light,
                "brightLight": self.emits_bright_light,
                "dimSight": self.dim_sight,
                "brightSight": self.bright_sight,
                "vision": self.has_vision,
                "actorId": self.actor_id,
                "actorLink": False,
                "disposition": -1,
                "displayBars": self.display_bars,
                "bar1": {"attribute": "attributes.bar1" if self.bar1_max != 0 or self.bar1_val != 0 else None,
                         "value": self.bar1_val,
                         "max": self.bar1_max
                         },
                "bar2": {"attribute": "attributes.bar2" if self.bar2_max != 0 or self.bar2_val != 0 else None,
                         "value": self.bar2_val,
                         "max": self.bar2_max
                         },
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

        avatar_filename = ""
        if character["avatar"] != "":
            if self.getArgument("use_original_image_urls", False):
                avatar_filename = character["avatar"]
            else:
                filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "avatar.png")
                if self.getArgument("json", False):
                    (_, avatar_filename) = self.downloadResource(character["avatar"], filename)
                else:
                    (_, avatar_filename) = self.copyZipFile(filename, filename)
        folder = self.findFolder(character["id"],  self._database._campaign["journalfolder"])

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
                if avatar_filename == "":
                    avatar_filename = token_filename
                if "sides" in default_token and len(default_token["sides"]) > 0:
                    randomImg = True
                    for i in range(len(default_token["sides"])):
                        filename = os.path.join("characters", "%03d - %s" % (index, character["name"]), "side_" + str(i) + ".png")
                        if self.getArgument("json", False):
                            (_, token_filename) = self.downloadResource(default_token["sides"][i], filename)
                        else:
                            (_, token_filename) = self.copyZipFile(filename, filename)
                        token_filename = token_filename.replace("side_" + str(i) + ".png", "side_*.png")
            if avatar_filename == "":
                avatar_filename = token_filename
        if token_filename == "":
            token_filename = avatar_filename
        self.token.token_filename = token_filename
        token = self.token.getDict()
        token["randomImg"] = randomImg
        if default_token:
            bar1_link = default_token.get("bar1_link", "")
            bar2_link = default_token.get("bar2_link", "")
            (_, _, hp_id) = self.getAttribute("hp")
            if bar1_link == hp_id:
                token["bar1"]["attribute"] = "attributes.hp"
            if bar2_link == hp_id:
                token["bar2"]["attribute"] = "attributes.hp"
        token["actorLink"] = not npc

        if character["archived"] and not self.getArgument("disable_archived", False):
            folder = "archived-characters-folder-id"

        self._save_bonus = self.calculateSaveBonus()
        actor_data = OrderedDict([
            ("abilities", self.createActorAbilities()),
            ("attributes", self.createActorAttributes()),
            ("details", self.createActorDetails()),
            ("skills", self.createActorSkills()),
            ("traits", self.createActorTraits()),
            ("currency", self.createActorCurrency()),
            ("spells", self.createActorSpells()),
            ("resources", self.createActorResources()),
        ])
        owned_items = []
        self.addInventory(owned_items)
        self.addTraits(owned_items)
        self.addActions(owned_items)
        self.addSpells(owned_items)

        self.entity = {"_id": self._id,
                       "name": character["name"],
                       "img": avatar_filename,
                       "permission": permissions,
                       "data": actor_data,
                       "folder": Entity.normalizeID(folder),
                       "flags": {"dnd5e": {"saveBonus": self._save_bonus},
                                 "entityorder": {"order": index}},
                       "type": "npc" if npc else "character",
                       "token": token,
                       "items": owned_items
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

    def _capitalizeAll(self, sentence):
        return " ".join(map(lambda x: x.capitalize(), sentence.split(" ")))

    def getAttribute(self, key, default=None, from_dict=None):
        if from_dict is None:
            from_dict = self._attributes
        return from_dict.get(key, (default, default, None))

    def getAttributeInt(self, key, default=0, from_dict=None):
        value = self.getAttribute(key, default, from_dict)[0]
        try:
            return int(value)
        except:
            return int(default)

    def isNPC(self):
        npc = self.getAttributeInt("npc", 0)
        try:
            return bool(npc)
        except:
            return False

    def getNPCType(self):
        npc_type = self.getAttribute("npc_type", "")[0]
        size = npc_type.split(",", 1)[0].split(" ", 1)[0].strip()
        creature_type = npc_type.split(",", 1)[0].split(" ", 1)[-1].strip()
        alignment = npc_type.split(",", 1)[-1].strip()
        return (size, creature_type, alignment)

    def parseAttributes(self):
        self._attributes = OrderedDict()
        self._repeating = OrderedDict()
        for attr in self._character["attributes"]:
            value = (attr["current"], attr["max"], attr["id"])
            if attr["name"].startswith("_reporder_repeating_"):
                pass
            elif attr["name"].startswith("repeating_"):
                (_, repeating_type, id, name) = attr["name"].split("_", 3)
                rep = self._repeating.get(repeating_type, None)
                if rep is None:
                    rep = self._repeating[repeating_type] = OrderedDict()
                    order = ""
                    for a in self._character["attributes"]:
                        if a["name"] == "_reporder_repeating_%s" % repeating_type:
                            order = a["current"]
                            break
                    for order_id in order.split(","):
                        if order_id != "":
                            rep.setdefault(order_id, {})
                rep.setdefault(id, {})[name] = value
            else:
                self._attributes[attr["name"]] = value

        #self.displayAttributes()


    def displayAttributes(self):
        print("Parsed attributes for character %s: %s" % (self._character["id"], self._character["name"]))
        keys = list(self._attributes.keys())
        keys.sort()
        for key in keys:
            attr = self._attributes[key]
            print("%s: %s%s" % (key, str(attr[0]), ("(" + str(attr[1]) + ")") if attr[1] != "" else ""))
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
            save = self.getAttributeInt(ability + "_save_bonus", 0)
            bases.append(save - mod)
        return min(bases)
        #min_base = min(bases)
        #max_base = max(bases)
        #pb = self.getAttributeInt("pb", 2)
        #if min_base + pb == max_base and bases.count(min_base) == 4 and bases.count(max_base) == 2:
        #    return min_base
        

    def createActorAbility(self, name):
        ability = self.getAttributeInt(name.lower(), 10)
        mod = self.getAttributeInt(name.lower() + "_mod", 0)
        proficiency_bonus = self.getAttributeInt("pb", 0)
        if self.isNPC():
            save = self.getAttributeInt("npc_" + name.lower()[0:3] + "_save", 0)
            proficient = (save != 0)
        else:
            save = self.getAttributeInt(name.lower() + "_save_bonus", mod)
            proficient = (save == mod + proficiency_bonus + self._save_bonus)
        return {"type": "Number",
                "label": name,
                "value": ability,
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

    def createAttributeNumber(self, name, attribute_name, default=0, extra={}):
        (current, max, _) = self.getAttribute(attribute_name, default)
        try:
            current = int(current)
        except:
            pass
        ret = {
                "type": "Number",
                "label": name,
                "value": current,
                }
        if max != "":
            ret["min"] = 0
            ret["max"] = max
        ret.update(extra)
        return ret
        
    def createAttributeString(self, name, attribute_name, default="", extra={}):
        ret = {
                "type": "String",
                "label": name,
                "value": self.getAttribute(attribute_name, default)[0]
                }
        ret.update(extra)
        return ret
    def createAttributeBoolean(self, name, attribute_name, default=False, extra={}):
        ret = {
                "type": "Boolean",
                "label": name,
                "value": self.getAttribute(attribute_name, "on" if default else "")[0] == "on",
                }
        ret.update(extra)
        return ret

    def createAttributeAC(self):
        ac = self.getAttribute("npc_ac" if self.isNPC() else "ac", 10)[0]
        
        res = {"type": "Number",
               "label": "Armor Class",
               "min": ac,
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
        return {"type": "Number",
                "label": "Hit Points",
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
        return {
                "type": "Number",
                "label": "Initiative Modifier",
                "value": init - mod,
                "mod": init
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
        return {"type": "String",
                "label": "Movement Speed",
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
        return {
                "type": "String",
                "label": "Spellcasting Ability",
                "value": spellcasting_ability
                }
    def createAttributeDeath(self):
        success = 0
        failure = 0
        for i in range(1, 4):
            if self.getAttribute("deathsave_succ%d" % i, 0)[0] == "on":
                success += 1
            if self.getAttribute("deathsave_fail%d" % i, 0)[0] == "on":
                failure += 1

        return {"type": "Number",
                "label": "Death Saves",
                "success": success,
                "failure": failure
                }

    def createActorAttributes(self):
        attributes = OrderedDict([
            ("ac", self.createAttributeAC()),
            ("hp", self.createAttributeHP()),
            ("init", self.createAttributeInitiative()),
            ("prof", self.createAttributeNumber("Proficiency", "pb", 0)),
            ("speed", self.createAttributeSpeed()),
            ("spellcasting", self.createAttributeSpellcasting()),
            ("spelldc", self.createAttributeString("Spell DC", "npc_spelldc" if self.isNPC() else "spell_save_dc", 10)),
            # Add our own bar data
            ("bar1", {"type": "Number",
                      "label": "Token Bar #1",
                      "value": self.token.bar1_val,
                      "min": 0,
                      "max": self.token.bar1_max}),
            ("bar2", {"type": "Number",
                      "label": "Token Bar #2",
                      "value": self.token.bar2_val,
                      "min": 0,
                      "max": self.token.bar2_max}),
        ])
        if not self.isNPC():
            attributes.update([
                    ("hd", self.createAttributeNumber("Hit Dice", "hit_dice", 0)),
                    ("death", self.createAttributeDeath()),
                    ("exhaustion", self.createAttributeNumber("Exhaustion Level", "exhaustion_level", 0)),
                    ("inspiration", self.createAttributeBoolean("Inspiration", "inspiration", False)),
            ])
        return attributes

    def createDetailAlignment(self):
        if self.isNPC():
            alignment = self.getNPCType()[2]
        else:
            alignment = self.getAttribute("alignment", "")[0]
        # NPCs have it all lowercase
        alignment = self._capitalizeAll(alignment)
        return {
                "type": "String",
                "label": "Alignment",
                "value": alignment
                }

    def createDetailBio(self):
        bio = self._character["bio"]
        gmnotes = self._character["gmnotes"]
        if gmnotes != "":
            bio += "\n<section class=\"secret\"><p>GM Notes : </p>" + gmnotes + "</section>"

        bio = self.replaceCompendiumLinks(self.replaceEntityLinks(bio))
        return {
                "type": "String",
                "label": "Biography",
                "value": bio
                }

    def createDetailSource(self):
        return {
                "type": "Source",
                "label": "Source Location",
                "value": self.getArgument("npc_source", "Roll 20")
                }
    def createDetailType(self):
        return {
                "type": "String",
                "label": "Creature Type",
                "value": self.getNPCType()[1]
                }
    def createDetailChallengeRating(self):
        cr = self.getAttribute("npc_challenge", 0)[0]
        try:
            cr = int(cr)
        except:
            try:
                cr = int(cr.split("/")[0]) / int(cr.split("/")[1])
            except:
                cr = 0
            
        return {
                "type": "Number",
                "label": "Challenge Rating",
                "value": cr,
                "min": 0
                }

    def createActorDetails(self):
        details =  OrderedDict([
            ("alignment", self.createDetailAlignment()),
            ("biography", self.createDetailBio()),
            ("class", self.createAttributeString("Class", "class_display", "")),
            ("race", self.createAttributeString("Race", "race_display", ""))
        ])
        if self.isNPC():
            details.update([
                    ("type", self.createDetailType()),
                    ("environment", {
                        "type": "String",
                        "label": "Environment"
                        }),
                    ("cr", self.createDetailChallengeRating()),
                    ("xp", self.createAttributeNumber("Kill Experience", "npc_xp", 0)),
                    ("source", self.createDetailSource())
                    ])
        else:
            details.update([
                    ("background", self.createAttributeString("Background", "background", "")),
                    ("level", self.createAttributeNumber("Character Level", "level", 1, {"min": 1})),
                    ("xp", self.createAttributeNumber("Experience Points", "experience", 0)),
                    ("trait", self.createAttributeString("Trait", "personality_traits", "")),
                    ("ideal", self.createAttributeString("Ideal", "ideals", "")),
                    ("bond", self.createAttributeString("Bond", "bonds", "")),
                    ("flaw", self.createAttributeString("Flaw", "flaws", ""))
                    ])
        return details

    def createActorSkill(self, label, attribute_name, ability):
        mod = self.getAttribute("npcd_" + attribute_name if self.isNPC() else attribute_name + "_bonus", "")[0]
        base_mod = self.getAttributeInt(ability + "_mod", 0)
        if mod == "":
            mod = base_mod
        value = 0

        if self.isNPC():
            prof = self.getAttributeInt("pb", 2)
            flag = self.getAttributeInt("npc_" + attribute_name + "_flag", 0)
            #print("Flag : {} - prof {}".format(flag, prof))
            flag = bool(flag)
            if flag:
                if mod == base_mod + prof:
                    value = 1
                elif mod == base_mod + prof // 2:
                    value = 0.5
                elif mod == base_mod + prof * 2:
                    value = 2
                else:
                    value = (mod - base_mod) / prof
        else:
            prof = self.getAttribute(attribute_name + "_prof", "")[0]
            prof_type = self.getAttribute(attribute_name + "_type", "")[0]
            #print("Ability : %s - prof '%s' - type : '%s'" % (ability, prof, prof_type))
            if "pb" in prof:
                value = int(prof_type) if prof_type != "" else 1
        #print("Skill %s : %d : %d" % (label, value, mod))
        return {
                "type": "Number",
                "label": label,
                "value": value,
                "ability": ability.lower()[0:3],
                "mod": mod
                }
    def createActorSkills(self):
        return OrderedDict([
            ("acr", self.createActorSkill("Acrobatics", "acrobatics", "dexterity")),
            ("ani", self.createActorSkill("Animal Handling", "animal_handling", "wisdom")),
            ("arc", self.createActorSkill("Arcana", "arcana", "intelligence")),
            ("ath", self.createActorSkill("Athletics", "athletics", "strength")),
            ("dec", self.createActorSkill("Deception", "deception", "charisma")),
            ("his", self.createActorSkill("History", "history", "intelligence")),
            ("ins", self.createActorSkill("Insight", "insight", "wisdom")),
            ("itm", self.createActorSkill("Intimidation", "intimitation", "charisma")),
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
        
    def createTraitSize(self):
        dnd5e_sizes = {
            "Gargantuan": "grg",
            "Huge": "huge",
            "Large": "lg",
            "Medium": "med",
            "Small": "sm",
            "Tiny": "tiny"
        }
        if self.isNPC():
            size = self.getNPCType()[0]
        else:
            size = self.getAttribute("size", "Medium")[0]

        return {
                "type": "String",
                "label": "Size",
                "value": dnd5e_sizes.get(size, "med")
                }

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

        return {
                "type": "String",
                "label": "Senses",
                "value": senses
                }

    def createTraitPassivePerception(self):
        pp = 10 + self.createActorSkill("Perception", "perception", "wisdom")["mod"]
        # An NPC might have overriden the PP in its senses
        if self.isNPC():
            senses = self.getAttribute("npc_senses", "")[0]
            match = re.search(r"passive perception (\d+)", senses)
            if match:
                pp = int(match.group(1))

        return {"type": "Number",
                "label": "Passive Perception",
                "value": pp
                }

    def _addKnownToArray(self, known_list, name, array, custom):
        name = self._capitalizeAll(name.strip())
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
            npc_languages = self.getAttribute("npc_languages", "")[0]
            for lang in npc_languages.split(","):
                self._addKnownToArray(known_languages, lang, languages, custom)
        else:
            proficiencies = self._repeating.get("proficiencies", {})
            for prof in proficiencies.values():
                #print("Proficienty : {} = {}".format(id, prof))
                if self.getAttribute("prof_type", "", from_dict=prof)[0] == "LANGUAGE":
                    self._addKnownToArray(known_languages, self.getAttribute("name", "", from_dict=prof)[0], languages, custom)

        return {
                "type": "Array",
                "label": "Known Languages",
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
            npc_immunities = self.getAttribute("npc_immunities", "")[0]
            self._addDamagesToArray(npc_immunities, immunities, custom)

        return {
            "type": "Array",
            "label": "Damage Immunities",
            "value": immunities,
            "custom": ", ".join(custom)
            }

    def createTraitDamageResistances(self):
        resistances = []
        custom = []
        if self.isNPC():
            npc_resistances = self.getAttribute("npc_resistances", "")[0]
            self._addDamagesToArray(npc_resistances, resistances, custom)

        return {
                "type": "Array",
                "label": "Damage Resistances",
                "value": resistances,
                "custom": ", ".join(custom)
                }
    def createTraitDamageVulnerabilities(self):
        vulnerabilities = []
        custom = []
        if self.isNPC():
            npc_vulnerabilities = self.getAttribute("npcvulnerabilities", "")[0]
            self._addDamagesToArray(npc_vulnerabilities, vulnerabilities, custom)

        return {
                "type": "Array",
                "label": "Damage Vulnerabilities",
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
            npc_immunities = self.getAttribute("npc_condition_immunities", "")[0]
            for immunity in npc_immunities.split(","):
                self._addKnownToArray(known_immunities, immunity, immunities, custom)

        return {"type": "Array",
                "label": "Condition Immunities",
                "value": immunities,
                "custom": ", ".join(custom)
                }

    def createActorTraits(self):
        return OrderedDict([
            ("size", self.createTraitSize()),
            ("senses", self.createTraitSenses()),
            ("perception", self.createTraitPassivePerception()),
            ("languages", self.createTraitLanguages()),
            ("di", self.createTraitDamageImmunities()),
            ("dr", self.createTraitDamageResistances()),
            ("dv", self.createTraitDamageVulnerabilities()),
            ("ci", self.createTraitConditionImmunities()),
        ])

    def createActorCurrency(self):
        return OrderedDict([
            ("pp", self.createAttributeNumber("Platinum", "pp", 0)),
            ("gp", self.createAttributeNumber("Gold", "gp", 0)),
            ("sp", self.createAttributeNumber("Silver", "sp", 0)),
            ("cp", self.createAttributeNumber("Copper", "cp", 0))
        ])

    def createActorSpells(self):
        spells = OrderedDict([("spell0", {
                                "type": "Number",
                                "label": "Cantrip"
                                })])
        for level in range(1, 10):
            if level == 1:
                level_str = "1st"
            elif level == 2:
                level_str = "2nd"
            elif level == 3:
                level_str = "3rd"
            else:
                level_str = "%dth" % level

            spell = self.createAttributeNumber("%s Level" % level_str, "lvl%d_slots_expended" % level, 0)
            spell["max"] = self.getAttribute("lvl%d_slots_total" % level, spell["value"])[0]
            spells["spell%d" % level]  = spell
        return spells

    def createCharacterResource(self, label, resource):
        name = self.getAttribute(resource + "_name", label)[0]
        (current, max, _) = self.getAttribute(resource, 0)
        try:
            current = int(current)
        except:
            pass
        try:
            max = int(max)
        except:
            pass
        return {"type": "String",
                "label": name,
                "sr": False,
                "lr": False,
                "value": current,
                "max": max
                }

    def createResourceLegendaryResistance(self):
        legres = 0
        for id in self._repeating.get("npctrait", {}):
            trait = self._repeating["npctrait"][id]
            name = self.getAttribute("name", "", from_dict=trait)[0]
            match = re.search(r"Legendary Resistance \((\d+)/day\)", name)
            if match:
                legres = int(match.group(1))

        return {"type": "Number",
                "label": "Legendary Resistance",
                "value": legres
                }
                    
    def createResourceLairAction(self):
        lair_actions = self._repeating.get("npcaction-l", {})
        return {"type": "Boolean",
                "label": "Lair Action",
                "value": len(lair_actions) > 0
                }

    def createActorResources(self):
        if self.isNPC():
            return OrderedDict([
                ("legact", self.createAttributeNumber("Legendary Actions", "npc_legendary_actions", 0)),
                ("legres", self.createResourceLegendaryResistance()),
                ("lair", self.createResourceLairAction())
            ])
        else:
            return OrderedDict([("primary", self.createCharacterResource("Primary Resource", "class_resource")),
                                ("secondary", self.createCharacterResource("Secondary Resource", "other_resource"))])


    def textToHtml(self, text):
        # Replace each line with <p>line</p>
        return "".join(list(map(lambda l: "<p>" + l + "</p>", text.split("\n"))))

    def createItemFromCompendium(self, compendium_item, items, description, **kwargs):
        item = copy.deepcopy(compendium_item)
        del item["_id"]
        item["id"] = len(items) + 1
        item["data"]["description"]["value"] = description
        for key in kwargs:
            valueKey = "max" if key.endswith("_max") else "value"
            item["data"][key][valueKey] = kwargs[key]

        items.append(item)
        return item

    def createItemInventory(self, items, name, description, inventory_type, **kwargs):
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Items", name)
        if compendium_item:
            return self.createItemFromCompendium(compendium_item, items, description, **kwargs)

        data = {"description": {"type": "String", "label": "Description", "value": description},
                "source": {"type": "String", "label": "Source", "value": kwargs.get("source", "")},
                "quantity": {"type": "Number", "label": "Quantity", "value": kwargs.get("quantity", 1)},
                "weight": {"type": "Number", "label": "Weight", "value": kwargs.get("weight", 1)},
                "price": {"type": "String", "label": "Price", "value": kwargs.get("price", 0)}
                }
        if inventory_type == "backpack":
            pass
        elif inventory_type == "equipment":
            data.update({"armor": {"type": "Number", "label": "Armor Value", "value": kwargs.get("armor", 0)},
                        "armorType": {"type": "String", "label": "Armor Type", "value": kwargs.get("armorType", "")},
                        "strength": {"type": "String", "label": "Required Strength", "value": kwargs.get("strength", "")},
                        "stealth": {"type": "Boolean", "label": "Stealth Disadvantage", "value": kwargs.get("stealth", False)},
                        "proficient": {"type": "Boolean", "label": "Proficient", "value": kwargs.get("proficient", False)},
                        "attuned": {"type": "Boolean", "label": "Attuned", "value": kwargs.get("attuned", False)},
                        "equipped": {"type": "Boolean", "label": "Equipped", "value": kwargs.get("equipped", True)}
                        })
        elif inventory_type == "consumable":
            data.update({"consumableType": {"type": "String", "label": "Consumable Type", "value": "potion"},
                        "charges": {"type": "Number", "label": "Charges", "value": kwargs.get("charges", 1), "max": kwargs.get("charges_max", 1)},
                        "consume": {"type": "String", "label": "Roll on Consume", "value": kwargs.get("consume", "")},
                        "autoUse": {"type": "Boolean", "label": "Consume on Use", "value": kwargs.get("autoUse", True)},
                        "autoDestroy": {"type": "Boolean", "label": "Destroy on Empty", "value": kwargs.get("autoDestroy", True)}
                        })
        elif inventory_type == "tool":
            data.update({"ability": {"type": "String", "label": "Default Ability", "value": kwargs.get("ability", "str")},
                        "proficient": {"type": "Number", "label": "Proficiency", "value": kwargs.get("proficient", 0)}
                        })
        elif inventory_type == "weapon":
            data.update({"weaponType": {"type": "String", "label": "Weapon Type", "value": kwargs.get("weaponType", "")},
                        "bonus": {"type": "String", "label": "Attack Bonus", "value": kwargs.get("bonus", "")},
                        "damage": {"type": "String", "label": "Damage Formula", "value": kwargs.get("damage", "")},
                        "damageType": {"type": "String", "label": "Damage Type", "value": kwargs.get("damageType", "")},
                        "damage2": {"type": "String", "label": "Alternate Damage", "value": kwargs.get("damage2", "")},
                        "damage2Type": {"type": "String", "label": "Alternate Type", "value": kwargs.get("damage2Type", "")},
                        "range": {"type": "String", "label": "Weapon Range", "value": kwargs.get("range", "")},
                        "properties": {"type": "String", "label": "Weapon Properties", "value": kwargs.get("properties", "")},
                        "proficient": {"type": "Boolean", "label": "Proficient", "value": kwargs.get("proficient", False)},
                        "attuned": {"type": "Boolean", "label": "Attuned", "value": kwargs.get("attuned", False)},
                        "ability": {"type": "String", "label": "Offensive Ability", "value": kwargs.get("ability", "str")}
                        })
        item = {"id": len(items) + 1,
                "flags": {},
                "name": name,
                "type": inventory_type,
                "img": self.token.token_filename,
                "data": data
                }
        items.append(item)
        return item

    def addInventory(self, items):
        inventory = self._repeating.get("inventory", {})
        for id in inventory:
            item = inventory[id]
            name = self.getAttribute("itemname", "", from_dict=item)[0]
            content = self.getAttribute("itemcontent", "", from_dict=item)[0]
            count = self.getAttributeInt("itemcount", 1, from_dict=item)
            weight = self.getAttributeInt("itemweight", 1, from_dict=item)
            mods = self.getAttribute("itemmodifiers", "", from_dict=item)[0]
            modifiers = {}
            for mod in mods.split(", "):
                if mod == "":
                    continue
                if ":" in mod:
                    key, value = mod.split(": ", 1)
                    modifiers[key.strip()] = value
                elif "+" in mod:
                    key, value = mod.split(" +", 1)
                    modifiers[key.strip()] = "+" + value
                elif "-" in mod:
                    key, value = mod.split(" -", 1)
                    modifiers[key.strip()] = "-" + value
            item_type = modifiers.get("Item Type", "")
            if item_type in ["Adventuring Gear", "Items"]:
                item = self.createItemInventory(items, name, content, "backpack", weight=weight, quantity=count)
                print("Created item : ", item)
            elif item_type == "Ammunition":
                self.createItemInventory(items, name, content, "weapon", weight=weight, quantity=count, weaponType="ammo")
            elif item_type in ["Light Armor", "Medium Armor", "Heavy Armor", "shield"]:
                armor = modifiers.get("AC", 0)
                try:
                    armor = int(armor)
                except:
                    pass
                armorType = item_type.split(" ")[0].lower()
                equipped = bool(self.getAttributeInt("equipped", 1, from_dict=item))
                self.createItemInventory(items, name, content, "equipment", weight=weight, quantity=count, armor=armor, armorType=armorType, equipped=equipped)
            elif item_type in ["Melee Weapon", "Ranged Weapon"]:
                kwargs = {
                    "properties": self.getAttribute("itemproperties", "", from_dict=item)[0],
                    "damage": modifiers.get("Damage", ""),
                    "damageType": modifiers.get("Damage Type", ""),
                    "damage2": modifiers.get("Alternate Damage", ""),
                    "damage2Type": modifiers.get("Altermate Damage Type", ""),
                    "range": modifiers.get("Range", "")
                }
                item = self.createItemInventory(items, name, content, "weapon", weight=weight, quantity=count, **kwargs)
                if item["data"]["weaponType"]["value"] == "":
                    # Don't override the weapon type if taken from compendium, set it otherwise
                    weaponType = "simpleM" if item_type == "Melee Weapon" else "simpleR",
                    item["data"]["weaponType"]["value"] = weaponType

            

    def createItemFeat(self, items, name, description, feat_type, **kwargs):
        description = self.textToHtml(description)
        compendium_item = self.findCompendiumItem("Class Features", name)
        if compendium_item:
            return self.createItemFromCompendium(compendium_item, items, description, **kwargs)
        item = {"id": len(items) + 1,
                "flags": {},
                "name": name,
                "type": "feat",
                "img": self.token.token_filename,
                "data": {
                    "description": {"type": "String", "label": "Description", "value": description},
                    "source": {"type": "String", "label": "Source", "value": kwargs.get("source", "")},
                    "featType": {"type": "String", "label": "Feat Type", "value": feat_type},
                    "requirements": {"type": "String", "label": "Requirements", "value": kwargs.get("requirements", "")},
                    "ability": {"type": "String", "label": "Ability Modifier", "value": kwargs.get("ability", "")},
                    "target": {"type": "String", "label": "Target", "value": kwargs.get("target", "")},
                    "range": {"type": "String", "label": "Range", "value": kwargs.get("range, """)},
                    "time": {"type": "String", "label": "Casting Time", "value": kwargs.get("time", "")},
                    "duration": {"type": "String", "label": "Duration", "value": kwargs.get("duration", "")},
                    "damage": {"type": "String", "label": "Ability Damage", "value": kwargs.get("damage", "")},
                    "damageType": {"type": "String", "label": "Damage Type", "value": kwargs.get("damageType", "")},
                    "save": {"type": "String", "label": "Saving Throw", "value": kwargs.get("save", "")},
                    "uses": {"type": "", "label": "Limited Uses", "value": kwargs.get("uses", 0), "max": kwargs.get("uses_max", 0)}
                    }
                }
        items.append(item)
        return item

    def addTraits(self, items):
        if self.isNPC():
            npc_traits = self._repeating.get("npctrait", {})
            for trait in npc_traits.values():
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("desc", "", from_dict=trait)[0]
                self.createItemFeat(items, name, description, "passive")

            npc_reactions = self._repeating.get("npcreaction", {})
            for trait in npc_reactions.values():
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("desc", "", from_dict=trait)[0]
                self.createItemFeat(items, "Reaction: " + name, description, "ability", requirements="Reaction")
        else:
            traits = self._repeating.get("traits", {})
            for id in traits:
                trait = traits[id]
                name = self.getAttribute("name", "", from_dict=trait)[0]
                description = self.getAttribute("description", "", from_dict=trait)[0]
                source = self.getAttribute("source", "", from_dict=trait)[0]
                source_type = self.getAttribute("source_type", "", from_dict=trait)[0]
                if source_type != "":
                    source = (source + ": " + source_type) if source != "" else source_type
                self.createItemFeat(items, name, description, "passive", source=source, requirements=source)

    def addActions(self, items):
        pass

    def addSpells(self, items):
        pass
