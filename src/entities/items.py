from .base import DatabaseFile, Entity
from .base import DatabaseFile, Entity
import os
import copy

class Items(DatabaseFile):
    def __init__(self, converter, filename="items.db"):
        DatabaseFile.__init__(self, converter, filename)
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
            if isinstance(item, dict):
                dirname = "%03d - %s" % (index, item["n"])
                items.extend(self.addToFolder("item" + item["id"], item["n"], item["i"], os.path.join(folder_path, dirname)))
                index += 1
            elif is_items_folder:
                handout = self.findID(item, "handout")
                if handout != None:
                    items.append(Item.createItemFromHandout(self, handout, index, folder_id, folder_name, folder_path))
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
        
    def createItemFromCompendium(self, id, compendium_item, custom_data=None):
        return Item.createItemFromCompendium(self, id, compendium_item, custom_data)

    def createItemInventory(self, id, name, description, inventory_type, attributes,
                            activation=None, attack=None, specific=None, **kwargs):
        if inventory_type == "loot":
            return Item.createItemLoot(self, id, name, description, attributes, **kwargs)
        elif inventory_type == "weapon":
            return Item.createItemWeapon(self, id, name, description, activation, attack, attributes, specific, **kwargs)
        elif inventory_type == "equipment":
            return Item.createItemEquipment(self, id, name, description, activation, attack, attributes, specific, **kwargs)
        elif inventory_type == "consumable":
            return Item.createItemWeapon(self, id, name, description, activation, attack, attributes, specific, **kwargs)
        elif inventory_type == "tool":
            return Item.createItemTool(self, id, name, description, attributes, specific, **kwargs)
        elif inventory_type == "backpack":
            return Item.createItemBackpack(self, id, name, description, attributes, specific, **kwargs)
        else:
            raise Exception("Unknown Inventory type")
        

    def createItemFeat(self, id, name, description, activation, attack, recharge, **kwargs):
        return Item.createItemFeat(self, id, name, description, activation, attack, recharge, **kwargs)

    def createItemSpell(self, id, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs):
        return Item.createItemSpell(self, id, name, description, activation, attack,
                        level, school, components, preparation, scaling, **kwargs)

    def createItemClass(self, id, name, description, level, subclass, **kwargs):
        return Item.createItemClass(self, id, name, description, level, subclass, **kwargs)

class Item(Entity):
    def __init__(self, database, item_id, name, item_type="loot", img=None, data={}):
        Entity.__init__(self, database, item_id)
        # Don't want to print for every item created in a character sheet
        #self.logInfo("Creating %s Item : %s" % (item_type, name))
        
        self.entity = {"_id": self._id,
                "name":  name,
                "permission": {"default": Item.PERMISSION_NONE},
                "folder": None,
                "flags": {},
                "type": item_type,
                "img": img,
                "data": data,
                "sort": 0,
                "effects": []
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
    def createItemFromHandout(database, handout, index, parent, source, path):
        item = Item(database, handout["id"], handout["name"], "loot")
        
        item.logInfo("Creating Item from Handout : %s" % item.getName())

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
        avatar_filename = None
        if handout["avatar"] != "":
            if item.getArgument("use_original_image_urls", False):
                avatar_filename = handout["avatar"]
            else:
                filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
                if item.getArgument("json", False):
                    (_, avatar_filename) = item.downloadResource(handout["avatar"], filename)
                else:
                    (_, avatar_filename) = item.copyZipFile(filename, filename)
                if avatar_filename == "":
                    avatar_filename = None
        if item.getArgument("export_as_module", False):
            parent = None

        attributes = ItemInventoryAttributes()
        data = Item.createStandardData(content, source, **attributes.getDict())
        item.entity = {
            "_id": item._id,
            "name":  handout["name"],
            "permission": permissions,
            "folder": Entity.normalizeID(parent),
            "flags": {},
            "type": "loot",
            "img": avatar_filename,
            "sort": index * Entity.SORT_ORDER,
            "data": data
        }
        return item

    @staticmethod
    def createItemFromCompendium(database, id, compendium_item, custom_data=None):
        item = Item(database, id, compendium_item.entity["name"])
        item.entity = copy.deepcopy(compendium_item.entity)
        item.entity["_id"] = item.getID()
        item.entity["permission"] = {"default": Item.PERMISSION_NONE}
        item.entity["folder"] = None
        if custom_data and item.getArgument("no_compendium_overwrite", False) is False:
            item.entity["data"].update(custom_data)

        return item


    @staticmethod
    def createItemLoot(database, id, name, description, attributes, **kwargs):
        source = kwargs.pop("source", "")
        attributes = attributes if attributes else ItemInventoryAttributes()
        kwargs.update(attributes.getDict())
        data = Item.createStandardData(description, source, **kwargs)
        return Item(database, id, name, "loot", None, data)

    @staticmethod
    def createItemWeapon(database, id, name, description, activation, attack, attributes, weapon, **kwargs):
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        attributes = attributes if attributes else ItemInventoryAttributes()
        weapon = weapon if weapon else ItemWeapon()
        kwargs.update(ItemConsume().getDict()) 
        kwargs.update(ItemObject().getDict()) 
        kwargs.update(attributes.getDict())
        kwargs.update(weapon.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "weapon", None, data)

    @staticmethod
    def createItemEquipment(database, id, name, description, activation, attack, attributes, equipment, **kwargs):
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        attributes = attributes if attributes else ItemInventoryAttributes()
        equipment = equipment if equipment else ItemEquipment()
        kwargs.update(ItemConsume().getDict()) 
        kwargs.update(ItemObject().getDict()) 
        kwargs.update(attributes.getDict())
        kwargs.update(equipment.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "equipment", None, data)

    @staticmethod
    def createItemConsumable(database, id, name, description, activation, attack, attributes, consumable, **kwargs):
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        attributes = attributes if attributes else ItemInventoryAttributes()
        consumable = consumable if consumable else ItemConsumable()
        kwargs.update(ItemConsume().getDict()) 
        kwargs.update(attributes.getDict())
        kwargs.update(consumable.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "consumable", None, data)

    @staticmethod
    def createItemTool(database, id, name, description, attributes, tool, **kwargs):
        source = kwargs.pop("source", "")
        attributes = attributes if attributes else ItemInventoryAttributes()
        tool = tool if tool else ItemTool()
        kwargs.update(attributes.getDict())
        kwargs.update(tool.getDict())
        data = Item.createStandardData(description, source, None, None, **kwargs)
        return Item(database, id, name, "tool", None, data)

    @staticmethod
    def createItemBackpack(database, id, name, description, attributes, backpack, **kwargs):
        source = kwargs.pop("source", "")
        attributes = attributes if attributes else ItemInventoryAttributes()
        backpack = backpack if backpack else ItemBackpack()
        kwargs.update(attributes.getDict())
        kwargs.update(backpack.getDict())
        data = Item.createStandardData(description, source, None, None, **kwargs)
        return Item(database, id, name, "backpack", None, data)

    @staticmethod
    def createItemFeat(database, id, name, description, activation, attack, recharge, **kwargs):
        kwargs.setdefault("requirements", "")
        source = kwargs.pop("source", "")
        activation = activation if activation else ItemActivation()
        attack = attack if attack else ItemAttack()
        recharge = recharge if recharge else ItemFeatRecharge()
        kwargs.update(ItemConsume().getDict()) 
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
        kwargs.update(ItemConsume().getDict()) 
        kwargs.update(components.getDict())
        kwargs.update(preparation.getDict())
        kwargs.update(scaling.getDict())
        data = Item.createStandardData(description, source, activation, attack, **kwargs)
        return Item(database, id, name, "spell", None, data)

        
    @staticmethod
    def createItemClass(database, id, name, description, level, subclass, **kwargs):
        classData = ItemClass(name, level, subclass)
        kwargs.update(classData.getDict())
        data = Item.createStandardData(description, **kwargs)
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
        string = str(string).lower()
        abbr = string[0:3]
        if abbr in ["str", "dex", "con", "wis", "int", "cha"]:
            return abbr

        # Use case of "@{strength_mod}" for example
        for ability in ["strength", "dexterity", "constitution", "wisdom", "intelligence", "charisma"]:
            if ability in string:
                return ability[0:3]
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
    def __init__(self, ability=ItemAbility.NONE, dc=None, scaling=None):
        self.ability = ability
        self.dc = dc
        self.scaling = scaling if scaling else "spell"

    def getDict(self):
        return {
            "save": {
                "ability": self.ability,
                "dc": self.dc,
                "scaling": self.scaling
            }
        }

        
# Unused
class ItemConsume:
    def __init__(self):
        pass

    def getDict(self):
        return {
            "consume": {
                "type": "",
                "target": None,
                "amount": None
            }
        }
# Unused
class ItemObject:
    def __init__(self):
        pass

    def getDict(self):
        return {
            "armor": {
                "value": 10
            },
            "hp": {
                "value": 0,
                "max": 0,
                "dt": None,
                "conditions": ""
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
        data = {
            "actionType": self.type,
            "ability": self.ability,
            "attackBonus": self.bonus,
            "formula": self.formula,
            "chatFlavor": self.chatFlavor,
            "critical": {
                "threshold": self.critical,
                "damage": None
            }
        }
        data.update(self.damages.getDict())
        data.update(self.save.getDict())
        return data

class ItemRange:
    EMPTY = ""
    NONE = "none"
    SELF = "self"
    TOUCH = "touch"
    FEET = "ft"
    MILES = "mi"
    SPECIAL = "spec"
    ANY = "any"

    def __init__(self, range=None, max=None, units=EMPTY):
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

    def __init__(self, type=EMPTY, range=None, width=None):
        self.range = range if range else ItemRange()
        self.width = width
        self.type = type

    def getDict(self):
        range = self.range.getDict()["range"]
        return {
            "target": {
                "value": range["value"],
                "width": self.width,
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
        data = {
            "activation": {
                "type": self.activation,
                "cost": self.cost,
                "condition": self.condition
            }
        }
        data.update(self.target.getDict())
        data.update(self.range.getDict())
        data.update(self.duration.getDict())
        data.update(self.uses.getDict())
        return data


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

    def __init__(self, mode=PREPARED_SPELL, prepared=False):
        self.mode = mode
        self.prepared = prepared

    def getDict(self):
        return {
            "preparation": {
                "mode": self.mode,
                "prepared": self.prepared
            }
        }

# Physical Item specific attributes
class ItemInventoryAttributes:
    def __init__(self, rarity="", quantity=1, weight=1, price=0,
                equipped=False, identified=True, attunement=0):
        self.rarity = rarity
        self.quantity = quantity
        self.weight = weight
        self.price = price
        self.attunement = attunement
        self.equipped = equipped
        self.identified = identified

    def getDict(self):
        return {
            "rarity": self.rarity,
            "quantity": self.quantity,
            "weight": self.weight,
            "price": self.price,
            "attunement": self.attunement,
            "equipped": self.equipped,
            "identified": self.identified
        }


# Weapon specific item variables

class ItemWeaponProperties:
    AMMUNITION = "amm"
    FINESSE = "fin"
    FIREARM = "fir"
    FOCUS = "foc"
    HEAVY = "hvy"
    LIGHT = "lgt"
    REACH = "rch"
    RELOAD = "rel"
    RETURNING = "ret"
    SPECIAL = "spc"
    THROWN = "thr"
    TWO_HANDED = "two"
    VERSATILE = "ver"

    def __init__(self):
        self.properties = []

    def addProperty(self, weapon_property):
        self.properties.append(weapon_property)

    def addFromString(self, string):
        string = string.lower()
        if string == "ammunication":
            self.addProperty(self.AMMUNITION)
        elif string == "finesse":
            self.addProperty(self.FINESSE)
        elif string == "firearm":
            self.addProperty(self.FIREARM)
        elif string == "focus":
            self.addProperty(self.FOCUS)
        elif string == "heavy":
            self.addProperty(self.HEAVY)
        elif string == "light":
            self.addProperty(self.LIGHT)
        elif string == "reach":
            self.addProperty(self.REACH)
        elif string == "reload":
            self.addProperty(self.RELOAD)
        elif string == "returning":
            self.addProperty(self.RETURNING)
        elif string == "special":
            self.addProperty(self.SPECIAL)
        elif string == "thrown":
            self.addProperty(self.THROWN)
        elif string == "two-handed":
            self.addProperty(self.TWO_HANDED)
        elif string == "versatile":
            self.addProperty(self.VERSATILE)

    def getDict(self):
        data = {
            "properties": { }
        }
        all_properties = ["amm", "hvy", "fin", "fir", "foc", "lgt", "rch", "rel", "ret", "spc", "thr", "two", "ver"]
        for prop in all_properties:
            data["properties"].update({
                prop: prop in self.properties
            })
        return data

class ItemWeapon:
    AMMUNITION = "ammo"
    IMPROVISED = "improv"
    MARTIAL_MELEE = "martialM"
    MARTIAL_RANGED = "martialR"
    NATURAL = "natural"
    SIMPLE_MELEE = "simpleM"
    SIMPLE_RANGED = "simpleR"

    def __init__(self, _type=NATURAL, proficient=True, properties=None):
        self.type = _type
        self.proficient = proficient
        self.properties = properties if properties else ItemWeaponProperties()


    def getDict(self):
        data = {
            "weaponType": self.type,
            "baseItem": "",
            "proficient": self.proficient
        }
        data.update(self.properties.getDict())
        return data

# Consumable specific item variables

class ItemConsumableUses(ItemUses):
    def __init__(self, uses=0, max=0, per=ItemUses.PER_NONE, autoDestroy=True, autoUse=True):
        ItemUses.__init__(self, uses, max, per)
        self.autoDestroy = autoDestroy
        self.autoUse = autoUse

    def getDict(self):
        data = super().getDict()
        data["uses"].update({
            "autoUse": self.autoUse,
            "autoDestroy": self.autoDestroy
        })
        return data

class ItemConsumable:
    POISON = "poison"
    POTION = "potion"
    ROD = "rod"
    SCROLL = "scroll"
    TRINKET = "trinket"
    WAND = "wand"

    def __init__(self, _type=TRINKET, uses=None):
        self.type = _type
        self.uses = uses if uses else ItemConsumableUses()

    def getDict(self):
        data = {
            "consumableType": self.type,
        }
        data.update(self.uses.getDict())
        return data

# Equipment specific item variables
class ItemEquipment:
    CLOTHING = "clothing"
    HEAVY_ARMOR = "heavy"
    LIGHT_ARMOR = "light"
    MAGICAL_BONUS = "bonus"
    MEDIUM_ARMOR = "medium"
    NATURAL_ARMOR = "natural"
    SHIELD = "shield"
    TRINKET = "trinket"

    def __init__(self, _type=CLOTHING, dexterity=0, ac=10, strength=0, stealth=False, proficient=True):
        self.type = _type
        self.dexterity = dexterity
        self.ac = ac
        self.strength = strength
        self.stealth = stealth
        self.proficient = proficient

    def getDict(self):
        return {
            "armor": {
                "type": self.type,
                "dex": self.dexterity,
                "value": self.ac
            },
            "baseItem": "",
            "speed": {
                "value": None,
                "conditions": ""
            },
            "strength": self.strength,
            "stealth": self.stealth,
            "proficient": self.proficient
        }
        

# Tool specific item variables
class ItemTool:
    def __init__(self, ability=ItemAbility.NONE, proficiency=0, flavor=""):
        self.proficiency = proficiency
        self.ability = ability
        self.flavor = flavor

    def getDict(self):
        return {
            "proficient": self.proficiency,
            "ability": self.ability,
            "chatFlavor": self.flavor,
            "toolType": "",
            "baseItem": "",
            "bonus": ""
        }

# Tool specific item variables
class ItemBackpack:
    ITEMS = "items"
    WEIGHT = "weight"
    
    def __init__(self, _type=ITEMS, capacity=0, weightless=False, cp=0, sp=0, ep=0, gp=0, pp=0):
        self.type = _type
        self.capacity = capacity
        self.weightless = weightless
        self.cp = cp
        self.sp = sp
        self.ep = ep
        self.gp = gp
        self.pp = pp

    def getDict(self):
        return {
            "capacity": {
                "type": self.type,
                "value": self.capacity,
                "weightless": self.weightless
            },
            "currency": {
                "cp": self.cp,
                "sp": self.sp,
                "ep": self.ep,
                "gp": self.gp,
                "pp": self.pp
            }
        }

# Class specific item variables
class ItemClass:
    def __init__(self, name, level, subclass, hitdice=None):
        self.level = level
        self.subclass = subclass
        self.hitdice = hitdice
        if self.hitdice is None:
            cl = name.strip().lower()
            if cl in ["artificer", "bard", "cleric", "druid", "monk", "rogue", "warlock"]:
                self.hitdice = "d8"
            elif cl in ["fighter", "paladin", "ranger"]:
                self.hitdice = "d10"
            elif cl == "barbarian":
                self.hitdice = "d12"
            else: # name == "sorcerer" or name == "wizard" or default:
                self.hitdice = "d6"

    def getDict(self):
        return {
            "levels": self.level,
            "subclass": self.subclass,
            "hitDice": self.hitdice,
            "hitDiceUsed": 0,
            "saves": [],
            "skills": {
                "number": 2,
                "choices": [],
                "value": []
            },
            "spellcasting": {
                "progression": "none",
                "ability": ""
            }
        }