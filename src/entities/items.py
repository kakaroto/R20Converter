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
        return self.addToFolder(None, None, self._campaign["journalfolder"], "items")

    def createEntities(self):
        new_entities = self.genEntities()
        self.entities.extend(new_entities)

    def addEntity(self, entity):
        self.entities.append(entity)
        
    def createItemFromCompendium(self, compendium_item, **kwargs):
        return Item.createItemFromCompendium(self, compendium_item, **kwargs)

    def createItemInventory(self, name, description, inventory_type, **kwargs):
        return Item.createItemInventory(self, name, description, inventory_type, **kwargs)

    def createItemFeat(self, name, description, feat_type, **kwargs):
        return Item.createItemFeat(self, name, description, feat_type, **kwargs)

    def createItemSpell(self, name, description, spell_type, school, level, **kwargs):
        return Item.createItemSpell(self, name, description, spell_type, school, level, **kwargs)

class Item(Entity):
    def __init__(self, database, item_id, name, item_type="backpack", img=None, data={}):
        Entity.__init__(self, database, item_id)
        print("Creating %s Item : %s" % (item_type, name))
        
        self.entity = {"_id": self._id,
                "name":  name,
                "permission": {"default": Item.PERMISSION_NONE},
                "folder": None,
                "flags": {},
                "type": item_type,
                "img": img,
                "data": data
                }

    def addToOwnedList(self, items):
        del self.entity["_id"]
        del self.entity["permission"]
        del self.entity["folder"]
        self.entity["id"] = len(items) + 1
        items.append(self.entity)


    @staticmethod
    def createItemFromHandout(database, handout, index, parent, path):
        item = Item(database, handout["id"], handout["name"], "backpack")
        
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

        item.entity = {"_id": item._id,
                "name":  handout["name"],
                "permission": permissions,
                "folder": Entity.normalizeID(parent),
                "flags": {"entityorder": {"order": index}},
                "type": "backpack",
                "img": avatar_filename,
                "data": {"description": {"type": "String", "label": "Description", "value": content},
                        "source": {"type": "String", "label": "Source", "value": ""},
                        "quantity": {"type": "Number", "label": "Quantity", "value": 1},
                        "weight": {"type": "Number", "label": "Weight", "value": 1},
                        "price": {"type": "String", "label": "Price", "value": 0}
                        }
                }
        return item

    @staticmethod
    def createItemFromCompendium(database, compendium_item, **kwargs):
        item = Item(database, None, compendium_item["name"])
        item.entity = copy.deepcopy(compendium_item)
        item.entity["_id"] = item.getID()
        item.entity["permission"] = {"default": Item.PERMISSION_NONE}
        item.entity["folder"] = None
        if item.getArgument("no_compendium_overwrite", False) is False:
            for key in kwargs:
                valueKey = "max" if key.endswith("_max") else "value"
                item.entity["data"][key][valueKey] = kwargs[key]

        return item


    @staticmethod
    def createItemInventory(database, name, description, inventory_type, **kwargs):
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
        return Item(database, None, name, inventory_type, None, data)

    @staticmethod
    def createItemFeat(database, name, description, feat_type, **kwargs):
        data = {
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
        return Item(database, None, name, "feat", None, data)

    @staticmethod
    def createItemSpell(database, name, description, spell_type, school, level, **kwargs):
        data = {
            "description": {"type": "String", "label": "Description", "value": description},
            "source": {"type": "String", "label": "Source", "value": kwargs.get("source", "")},
            "spellType": {"type": "String", "label": "Spell Type", "value": spell_type},
            "level": {"type": "Number", "label": "Spell Level", "value": level},
            "school": {"type": "String", "label": "Spell School", "value": school},
            "components": {"type": "String", "label": "Spell Components", "value": kwargs.get("components", "")},
            "materials": {"type": "String", "label": "Materials", "value": kwargs.get("materials", "")},
            "target": {"type": "String", "label": "Target", "value": kwargs.get("target", "")},
            "range": {"type": "String", "label": "Range", "value": kwargs.get("range", "")},
            "time": {"type": "String", "label": "Casting Time", "value": kwargs.get("time", "")},
            "duration": {"type": "String", "label": "Duration", "value": kwargs.get("duration", "")},
            "damage": {"type": "String", "label": "Spell Damage", "value": kwargs.get("damage", "")},
            "damageType": {"type": "String", "label": "Damage Type", "value": kwargs.get("damageType", "")},
            "save": {"type": "String", "label": "Saving Throw", "value": kwargs.get("save", "")},
            "concentration": {"type": "Boolean", "label": "Requires Concentration", "value": kwargs.get("concentration", False)},
            "ritual": {"type": "Boolean", "label": "Cast as Ritual", "value": kwargs.get("ritual", False)},
            "ability": {"type": "String", "label": "Spellcasting Ability", "value": kwargs.get("ability", "")},
            "prepared": {"type": "Boolean", "label": "Prepared Spell", "value": kwargs.get("prepared", False)}
        }
        return Item(database, None, name, "spell", None, data)