from .base import DatabaseFile, Entity

class Folders(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "folders.db")
        self._preserve_order = self.getArgument("preserve_folder_order", False)
        self.entities = self.genEntities()
        
    def addJournalFolder(self, folder, parent, index, depth=0):
        folders = []
        is_items_folder = folder["n"].strip() in self.getArgument("folder_as_items", [])
        has_characters = False
        has_handouts = False
        has_items = is_items_folder
            
        for item in folder["i"]:
            if isinstance(item, dict):
                # Found a folder
                folder_id = folder["id"]
                if depth >= 2:
                    print("Folder '%s' has a depth of %d. Dropping it to parent" % (item["n"], depth))
                    folder_id = parent
                (children, child_handouts, child_characters, child_items) = self.addJournalFolder(item, folder_id, index + 1 + len(folders), depth + 1)
                folders.extend(children)
                has_characters |= child_characters
                has_handouts |= child_handouts
                has_items |= child_items
            else:
                if self.findID(item, "character") != None:
                    has_characters = True
                elif self.findID(item, "handout") != None:
                    has_handouts = True
                else:
                    print("Unknown ID in Journal folder: %s"  % item)

        # By default, an empty folder would appear in the journal
        if has_handouts or (not has_characters and not has_items):
            has_handouts = True
            folders.append(Folder(self, "handout" + folder["id"], folder["n"], "JournalEntry", ("handout" + parent) if parent else None, index))
        if has_characters:
            folders.append(Folder(self, "character" + folder["id"], folder["n"], "Actor", ("character" + parent) if parent else None, index))
        if has_items:
            folders.append(Folder(self, "item" + folder["id"], folder["n"], "Item", ("item" + parent) if parent else None, index))
        return (folders, has_handouts, has_characters, has_items)

    def ensureFolder(self, id, name, folder_type, parent=None):
        for folder in self.entities:
            if folder.getID(False) == id:
                return folder
        return self.addFolder(id, name, folder_type, parent)

    def addFolder(self, id, name, folder_type, parent=None):
        folder = Folder(self, id, name, folder_type, parent)
        self.entities.append(folder)
        return folder

    def genEntities(self):
        folders = []
        for item in self._campaign["journalfolder"]:
            if isinstance(item, dict):
                (children, _, _, _) = self.addJournalFolder(item, None, len(folders))
                folders.extend(children)

        if not self.getArgument("disable_archived", False):
            for page in self._campaign["pages"]:
                if page["archived"]:
                    folders.append(Folder(self, "archived-scenes-folder-id", "Archived Scenes", "Scene", None, len(folders)))
                    break
            for handout in self._campaign["handouts"]:
                if handout["archived"]:
                    folders.append(Folder(self, "archived-handouts-folder-id", "Archived Handouts", "JournalEntry", None, len(folders)))
                    break
            for character in self._campaign["characters"]:
                if character["archived"]:
                    folders.append(Folder(self, "archived-characters-folder-id", "Archived Actors", "Actor", None, len(folders)))
                    break
        return folders
    

class Folder(Entity):
    def __init__(self, database, id, name, folder_type, parent, index=None):
        Entity.__init__(self, database, id)
        # TODO: add hierarchy for journal
        #if folder_type == "JournalEntry" and parent is not None:
        #    name = "|_ " + name
        #    parent = None
        self.entity = {"_id": self._id,
                       "name": name,
                       "flags": {},
                       "type": folder_type,
                       "color": "",
                       "parent": Entity.normalizeID(parent),
                       "sort": 100000 * (index if index else 1)
                       }