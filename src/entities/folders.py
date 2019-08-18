from .base import DatabaseFile, Entity

class Folders(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "folders.db")
        self._preserve_order = self.getArgument("preserve_folder_order", False)
        self.entities = self.genEntities()
        
    def addJournalFolder(self, folder, parent, index, depth=0):
        folders = []
        has_characters = False
        has_handouts = False
        for item in folder["i"]:
            if type(item) == dict:
                # Found a folder
                folder_id = folder["id"]
                if depth >= 2:
                    print("Folder '%s' has a depth of %d. Dropping it to parent" % (item["n"], depth))
                    folder_id = parent
                (children, child_handouts, child_characters) = self.addJournalFolder(item, folder_id, index + 1 + len(folders), depth + 1)
                folders.extend(children)
                has_characters |= child_characters
                has_handouts |= child_handouts
            else:
                if self.findID(item, "character") != None:
                    has_characters = True
                elif self.findID(item, "handout") != None:
                    has_handouts = True
                else:
                    print("Unknown ID in Journal folder: %s"  % item)

        # By default, an empty folder would appear in the journal
        if has_handouts or not has_characters:
            has_handouts = True
            folders.append(Folder(self, "handout" + folder["id"], folder["n"], "JournalEntry", ("handout" + parent) if parent else None, index))
        if has_characters:
            folders.append(Folder(self, "character" + folder["id"], folder["n"], "Actor", ("character" + parent) if parent else None, index))
        return (folders, has_handouts, has_characters)

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
            if type(item) == dict:
                (children, _, _) = self.addJournalFolder(item, None, len(folders))
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
                       "type": folder_type,
                       "parent": Entity.normalizeID(parent),
                       "sort": 100000 * (index if index else 1)
                       }