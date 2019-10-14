from .base import DatabaseFile, Entity
from .base import DatabaseFile, Entity
import os


class Items(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "items.db")
        self._handouts = self._campaign["handouts"]
        # We can't generate them here because an Item could have cross links to another item
        # which could make it generate a new item which will try to get it added to the database
        # which hasn't been created yet. So we need to start empty and have the entities generated
        # in a separate call
        self.entities = []

    def addEntity(self, entity):
        self.entities.append(entity)
        
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
                    items.append(Item(self, handout, index, folder_id, folder_path))
                    index += 1
                elif self.findID(item, "character") != None:
                    index += 1
                    
        return items

    def genEntities(self):
        return self.addToFolder(None, None, self._campaign["journalfolder"], "items")

    def createEntities(self):
        new_entities = self.genEntities()
        self.entities.extend(new_entities)

class Item(Entity):
    def __init__(self, database, handout, index, parent, path):
        Entity.__init__(self, database, handout["id"])
        print("Creating Item : %s" % handout["name"])
        
        content = handout["notes"]
        gmnotes = handout["gmnotes"]
        if gmnotes.strip() != "":
            content += "\n<section class=\"secret\"><p>GM Notes : </p>" + gmnotes + "</section>"
        content = self.replaceCompendiumLinks(self.replaceEntityLinks(content))
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
            if self.getArgument("use_original_image_urls", False):
                avatar_filename = handout["avatar"]
            else:
                filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
                if self.getArgument("json", False):
                    (_, avatar_filename) = self.downloadResource(handout["avatar"], filename)
                else:
                    (_, avatar_filename) = self.copyZipFile(filename, filename)
        if self.getArgument("export_as_module", False):
            parent = None

        self.entity = {"_id": self._id,
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