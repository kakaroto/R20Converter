from .base import DatabaseFile, Entity
import os


class Journal(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "journal.db")
        self._handouts = self._campaign["handouts"]
        self.entities = self.genEntities()

    def addToFolder(self, folder_id, folder, folder_path):
        handouts = []
        index = 0
        for item in folder:
            if isinstance(item, dict):
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
                    
        # Look for orphan handouts and add them to the root folder
        if folder_id is None:
            handout_ids = [h.getID(False) for h in handouts]
            zip_index = 0
            zip_path = os.path.join(folder_path, "Orphaned Handouts")
            for handout in self._handouts:
                if handout["id"] not in handout_ids:
                    self.logInfo("Found Orphaned handout, adding to root; ", end='')
                    handouts.append(Handout(self, handout, index, folder_id, folder_path, zip_path, zip_index))
                    index += 1
                    zip_index += 1

        return handouts

    def genEntities(self):
        return self.addToFolder(None, self._campaign["journalfolder"], "journal")

# TODO: handle Archived handouts differently?
class Handout(Entity):
    def __init__(self, database, handout, index, parent, path, zip_path=None, zip_index=None):
        Entity.__init__(self, database, handout["id"])
        self.logInfo("Creating Handout : %s" % handout["name"])
        zip_path = path if zip_path is None else zip_path
        zip_index = index if zip_index is None else zip_index
        content = handout["notes"]
        gmnotes = handout["gmnotes"]
        if gmnotes.strip() != "":
            content += "\n<section class=\"secret\"><p>GM Notes : </p>" + gmnotes + "</section>"
        content = self.replaceCompendiumLinks(self.replaceEntityLinks(content))
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
            if self.getArgument("use_original_image_urls", False):
                avatar_filename = handout["avatar"]
            else:
                filename = os.path.join(path, "%03d - %s" % (index, handout["name"]), "avatar.png")
                if self.getArgument("json", False):
                    (_, avatar_filename) = self.downloadResource(handout["avatar"], filename)
                else:
                    zip_filename = os.path.join(zip_path, "%03d - %s" % (zip_index, handout["name"]), "avatar.png")
                    (_, avatar_filename) = self.copyZipFile(zip_filename, filename)
        if handout["archived"] and not self.getArgument("disable_archived", False):
            parent = "archived-handouts-folder-id"
        if self.getArgument("export_as_module", False):
            parent = None
        self.entity = {"_id": self._id,
                       "name": handout["name"],
                       "permission": permissions,
                       "folder": Entity.normalizeID(parent),
                       "flags": {"R20Converter": 
                                 {"handout-order" : index, 
                                  "handout-archived": handout["archived"]}
                                 },
                       "sort": index * Entity.SORT_ORDER,
                       "entryTime": 0,
                       "content": content,
                       "img": avatar_filename
                       }
