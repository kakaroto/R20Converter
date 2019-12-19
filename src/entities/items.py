from .base import DatabaseFile, Entity
from .base import DatabaseFile, Entity
import os
import copy

class Items(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "items.db")
        self._handouts = self._campaign["handouts"]
        # We can't generate them here because an Item could have cross links to another item
        # which could make it generate a new item which will try to get it added to the database
        # which hasn't been created yet. So we need to start empty and have the entities generated
        # in a separate call
        self.entities = []
        
    def addToFolder(self, folder_id, folder_name, folder, folder_path):
        items = []
        index = 0
        is_items_folder = folder_name and folder_name.strip() in self.getArgument("folder_as_items", [])
        for item in folder:
            if type(item) == dict:
                dirname = "%03d - %s" % (index, item["n"])
                items.extend(self.addToFolder("item" + item["id"], item["n"], item["i"], os.path.join(folder_path, dirname)))
                index += 1
            elif is_items_folder:
                handout = self.findID(item, "handout")
                if handout != None:
                    items.append(Item.createItemFromHandout(self, handout, index, folder_id, folder_path))
                    index += 1
                elif self.findID(item, "character") != None:
                    index += 1
                    
        return items

    def genEntities(self):
        return self.addToFolder(None, None, self._campaign["journalfolder"], "journal")

    def createEntities(self):
        new_entities = self.genEntities()
        self.entities.extend(new_entities)

    def addEntity(self, entity):
        self.entities.append(entity)
        entity.setPosition(len(self.entities))
        
    def createItemFromCompendium(self, id, compendium_item, **kwargs):
        return Item.createItemFromCompendium(self, id, compendium_item, **kwargs)

    def createItemInventory(self, id, name, description, inventory_type, **kwargs):
        return Item.createItemInventory(self, id, name, description, inventory_type, **kwargs)

    def createItemFeat(self, id, name, description, activation, attack, recharge, **kwargs):
        return Item.createItemFeat(self, id, name, description, activation, attack, recharge, **kwargs)

    def createItemSpell(self, id, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs):
        return Item.createItemSpell(self, id, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs)

    def createItemClass(self, id, name, description, level, **kwargs):
        return Item.createItemClass(self, id, name, description, level, **kwargs)

class Item(Entity):
    def __init__(self, database, item_id, name, item_type="loot", img=None, data={}):
        Entity.__init__(self, database, item_id)
        # Don't want to print for every item created in a character sheet
        #print("Creating %s Item : %s" % (item_type, name))
        
        self.entity = {"_id": self._id,
                "name":  name,
                "permission": {"default": Item.PERMISSION_NONE},
                "folder": None,
                "flags": {},
                "type": item_type,
                "img": img,
                "data": data,
                "sort": 0
                }

    def getName(self):
        return self.entity["name"]

    def setPosition(self, index):
        self.entity["sort"] = index * Entity.SORT_ORDER

    @staticmethod
    def createStandardData(description="", source="", activation=None, attack=None, **kwargs):
        data = {
            "description": {"value": description, "chat": "", "unidentified": ""},
            "source": source,
        }
        if activation:
            data.update(activation.getDict())
        if attack:
            data.update(attack.getDict())

        data.update(kwargs)
        return data

    @staticmethod
    def createItemFromHandout(database, handout, index, parent, path):
        item = Item(database, handout["id"], handout["name"], "loot")
        
        print("Creating Item from Handout : %s" % item.getName())

        content = handout["notes"]
        gmnotes = handout["gmnotes"]
        if gmnotes.strip() != "":
            content += "\n<section class=\"secret\"><p>GM Notes : </p>" + gmnotes + "</section>"
        content = item.replaceCompendiumLinks(item.replaceEntityLinks(content))
        permissions = {"default": Item.PERMISSION_NONE}
        for player in handout.get("inplayerjournals", []):
            if player == "all":
                permissions["default"] = Item.PERMISSION_OBSERVER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Item.PERMISSION_OBSERVER
        for player in handout.get("controlledby", []):
            if player == "all":
                permissions["default"] = Item.PERMISSION_OWNER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Item.PERMISSION_OWNER
        avatar_filename = ""
        if handout["avatar"] != "":
            if item.getArgument("use_original_image_urls", False):
                avatar_filename = handout["avatar"]
            else:
                filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
                if item.getArgument("json", False):
                    (_, avatar_filename) = item.downloadResource(handout["avatar"], filename)
                else:
                    (_, avatar_filename) = item.copyZipFile(filename, filename)
        if item.getArgument("export_as_module", False):
            parent = None

        item.entity = {
            "_id": item._id,
            "name":  handout["name"],
            "permission": permissions,
            "folder": Entity.normalizeID(parent),
            "flags": {"entityorder": {"order": index}},
            "type": "loot",
            "img": avatar_filename,
            "sort": index * Entity.SORT_ORDER,
            "data": {
                "description": {"value": content, "chat": "", "unidentified": ""},
                "source": "",
                "rarity": "",
                "quantity": 1,
                "weight": 1,
                "price": 0,
                "attuned": False,
                "equipped": False,
                "identified": True,
                "damage": {"parts": []},
            }
        }
        return item

    @staticmethod
    def createItemFromCompendium(database, id, compendium_item, **kwargs):
        item = Item(database, id, compendium_item.entity["name"])
        item.entity = copy.deepcopy(compendium_item.entity)
        item.entity["_id"] = item.getID()
        item.entity["permission"] = {"default": Item.PERMISSION_NONE}
        item.entity["folder"] = None
        if item.getArgument("no_compendium_overwrite", False) is False:
            item.entity["data"].update(kwargs)

        return item


    @staticmethod
    def createItemInventory(database, id, name, description, inventory_type, **kwargs):
        data = {
            "description": {"value": description, "chat": "", "unidentified": ""},
            "source": kwargs.get("source", ""),
            "rarity": kwargs.get("rarity", ""),
            "quantity": kwargs.get("quantity", 1),
            "weight": kwargs.get("weight", 1),
            "price": kwargs.get("price", 0),
            "attuned": kwargs.get("attuned", False),
            "equipped": kwargs.get("equipped", False),
            "identified": kwargs.get("identified", True),
            "damage": {"parts": []},
        }
        if inventory_type == "loot":
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
        return Item(database, id, name, inventory_type, None, data)

    @staticmethod
    def createItemFeat(database, id, name, description, activation, attack, recharge, **kwargs):
        kwargs.setdefault("requirements", "")
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        recharge = recharge if recharge else ItemFeatRecharge()
        kwargs.update(recharge.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "feat", None, data)

    @staticmethod
    def createItemSpell(database, id, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs):
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        components = components if components else ItemSpellComponents()
        preparation = preparation if preparation else ItemSpellPreparation()
        scaling = scaling if scaling else ItemSpellScaling()
        kwargs.setdefault("level", level)
        kwargs.setdefault("school", school)
        kwargs.update(components.getDict())
        kwargs.update(preparation.getDict())
        kwargs.update(scaling.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "spell", None, data)

        
    @staticmethod
    def createItemClass(database, id, name, description, level, **kwargs):
        data = Item.createStandardData(description, levels=level, **kwargs)
        return Item(database, id, name, "class", None, data)


# Generic item variables

class ItemAbility:
    NONE = ""
    STRENGTH = "str"
    DEXTERITY = "dex"
    CONSITUTION = "con"
    INTELLIGENCE = "int"
    WISDOM = "wis"
    CHARISMA = "cha"

    @staticmethod
    def fromString(string):
        abbr = string.lower()[0:3]
        if abbr in ["str", "dex", "con", "wis", "int", "cha"]:
            return abbr
        return ItemAbility.NONE

        
class ItemDamage:
    def __init__(self, versatile=""):
        self.damages = []
        self.versatile = versatile

    def addDamage(self, formula, type):
        self.damages.append((formula, type))

    def getDict(self):
        return {
            "damage": {
                "parts": self.damages,
                "versatile": self.versatile
            }
        }
    
class ItemSave:
    def __init__(self, ability=ItemAbility.NONE, dc=None):
        self.ability = ability
        self.dc = dc

    def getDict(self):
        return {
            "save": {
                "ability": self.ability,
                 "dc": self.dc
            }
        }

class ItemAttack:
    EMPTY = ""
    MELEE_WEAPON = "mwak"
    RANGED_WEAPON = "rwak"
    MELEE_SPELL = "msak"
    RANGED_SPELL = "rsak"
    SAVE = "save"
    HEALING = "heal"
    ABILITY = "abil"
    UTILITY = "util"
    OTHER = "other"

    def __init__(self, type=EMPTY, ability=ItemAbility.NONE, damages=None, save=None,
                 bonus=0, formula="", critical=None, chatFlavor=""):
        self.type = type
        self.ability = ability
        self.damages = damages if damages else ItemDamage()
        self.save = save if save else ItemSave()
        self.bonus = bonus
        self.formula = formula
        self.critical = critical
        self.chatFlavor = chatFlavor

    def getDict(self):
        attack = {
            "actionType": self.type,
            "ability": self.ability,
            "attackBonus": self.bonus,
            "critical": self.critical,
            "formula": self.formula,
            "chatFlavor": self.chatFlavor
        }
        attack.update(self.damages.getDict())
        attack.update(self.save.getDict())
        return attack

class ItemRange:
    EMPTY = ""
    NONE = "none"
    SELF = "self"
    TOUCH = "touch"
    FEET = "ft"
    MILES = "mi"
    SPECIAL = "spec"
    ANY = "any"

    def __init__(self, range="", max="", units=EMPTY):
        self.range = range
        self.max = max
        self.units = units

    def getDict(self):
        return {
            "range": {
                "value": self.range,
                "long": self.max,
                "units": self.units
            }
        }

class ItemTarget:
    EMPTY = ""
    NONE = "none"
    SELF = "self"
    CREATURE = "creature"
    ALLY = "ally"
    ENEMY = "enemy"
    OBJECT = "object"
    SPACE = "space"
    RADIUS = "radius"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CONE = "cone"
    SQUARE = "square"
    CUBE = "cube"
    LINE = "line"
    WALL = "wall"

    def __init__(self, type=EMPTY, range=None):
        self.range = range if range else ItemRange()
        self.type = type

    def getDict(self):
        range = self.range.getDict()["range"]
        return {
            "target": {
                "value": range["value"],
                "units": range["units"],
                "type": self.type
            }
        }
        
class ItemDuration:
    NONE = ""
    INSTANTANEOUS = "inst"
    TURN = "turn"
    ROUND = "round"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    PERMANENT = "perm"
    SPECIAL = "spec"

    def __init__(self, duration=0, units=NONE):
        self.duration = duration
        self.units = units

    def getDict(self):
        return {
            "duration": {
                "value": self.duration,
                "units": self.units
            }
        }
        
class ItemUses:
    PER_NONE = ""
    PER_SHORT_REST = "sr"
    PER_LONG_REST = "lr"
    PER_DAY = "day"
    PER_CHARGES = "charges"

    def __init__(self, uses=0, max=0, per=PER_NONE):
        self.uses = uses
        self.max = max
        self.per = per

    def getDict(self):
        return {
            "uses": {
                "value": self.uses,
                "max": self.max,
                "per": self.per
            }
        }

class ItemActivation:
    EMPTY = ""
    NONE = "none"
    ACTION = "action"
    BONUS_ACTION = "bonus"
    REACTION = "reaction"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    SPECIAL = "special"
    LEGENDARY = "legendary"
    LAIR = "lair"

    def __init__(self, activation=EMPTY, cost=0, condition="",
                 target=None, range=None, duration=None, uses=None):
        self.activation = activation
        self.cost = cost
        self.condition = condition
        self.target = target if target else ItemTarget()
        self.range = range if range else ItemRange()
        self.duration = duration if duration else ItemDuration()
        self.uses = uses if uses else ItemUses()

    def getDict(self):
        activation = {
            "activation": {
                "type": self.activation,
                "cost": self.cost,
                "condition": self.condition
            }
        }
        activation.update(self.target.getDict())
        activation.update(self.range.getDict())
        activation.update(self.duration.getDict())
        activation.update(self.uses.getDict())
        return activation


# Feat specific item variables

class ItemFeatRecharge:
    def __init__(self, recharges=0, charged=False):
        self.recharges = recharges
        self.charged = charged

    def getDict(self):
        return {
            "recharge": {
                "value": self.recharges,
                "charged": self.charged
            }
        }

# Spell specific item variables

class ItemSpellSchool:
    ABJURATION = "abj"
    CONJURATION = "con"
    DIVINATION = "div"
    ENCHANTMENT = "enc"
    EVOCATION = "evo"
    ILLUSION = "ill"
    NECROMANCY = "nec"
    TRANSMUTATION = "trs"

class ItemSpellComponents:
    def __init__(self, concentration=False, ritual=False,
                 v=False, s=False, m=False, materials="",
                 consumed=False, cost=0, supply=0):
        self.concentration = concentration
        self.ritual = ritual
        self.v = v
        self.s = s
        self.m = m
        self.materials = materials
        self.consumed = consumed
        self.cost = cost
        self.supply = supply

    def getDict(self):
        return {
            "components": {
                "concentration": self.concentration,
                "ritual": self.ritual,
                "vocal": self.v,
                "somatic": self.s,
                "material": self.m,
                "value": ""
            },
            "materials": {
                "value": self.materials,
                "consumed": self.consumed,
                "cost": self.cost,
                "supply": self.supply
            }
        }
    
class ItemSpellScaling:
    NONE = "none"
    CANTRIP = "cantrip"
    LEVEL = "level"

    def __init__(self, mode=NONE, formula=""):
        self.mode = mode
        self.formula = formula

    def getDict(self):
        return {
            "scaling": {
                "mode": self.mode,
                "formula": self.formula
            }
        }

class ItemSpellPreparation:
    NONE = ""
    PREPARED_SPELL = "prepared"
    INNATE_SPELLCASTING = "innate"
    ALWAYS_AVAILABLE = "always"
    PACT_MAGIC = "pact"

    def __init__(self, mode=NONE, prepared=False):
        self.mode = mode
        self.prepared = prepared

    def getDict(self):
        return {
            "preparation": {
                "mode": self.mode,
                "prepared": self.prepared
            }
        }


# standard = ["description", "source", "actionType", "ability", "attackBonus", "critical", "formula", "chatFlavor", "damage", "save", "activation", "target", "range", "duration", "uses"]
# Object.keys(item.data.data).filter(k => !standard.includes(k) && !item.data.data[k]._deprecated)