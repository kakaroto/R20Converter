import os
import base64
import json
import re
import urllib
import errno
import hashlib
import requests

class DatabaseFile(object):
    def __init__(self, converter, filename):
        self._converter = converter
        self._path = converter.path
        self._filename = filename
        self._campaign = converter.campaign
        self.entities = []
  
    def findID(self, id, where=None):
        if where == "handout" or where is None:
            matches = [item for item in self._campaign["handouts"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "page" or where is None:
            matches = [item for item in self._campaign["pages"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "character" or where is None:
            matches = [item for item in self._campaign["characters"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "player" or where is None:
            matches = [item for item in self._campaign["players"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        if where == "track" or where is None:
            matches = [item for item in self._campaign["jukebox"] if item["id"] == id]
            if len(matches) > 0:
                return matches[0]
        return None


    def getArgument(self, name, default=None):
        return self._converter.getArgument(name, default)

    def __str__(self):
        return "\n".join(map(str, self.entities))

    def getDirectoryName(self):
        if self.getArgument("export_as_module", False):
            return "packs"
        else:
            return "data"
    def save(self, full_path=None):
        if full_path is None:
            full_path = os.path.join(self._path, self.getDirectoryName(), self._filename)
        with open(full_path, "w", encoding='utf-8') as f:
            f.write(str(self))
        return self

    def load(self, full_path=None):
        if full_path is None:
            full_path = os.path.join(self._path, self.getDirectoryName(), self._filename)
        self.entities = []
        with open(full_path, "r", encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                self.entities.append(json.loads(line))


class Entity(object):
    PERMISSION_NONE = 0
    PERMISSION_DEFAULT = -1
    PERMISSION_LIMITED = 1
    PERMISSION_OBSERVER = 2
    PERMISSION_OWNER = 3
    # Ensures ids are unique accross all entities
    id_database = {}
    resource_cache = {}

    def __init__(self, database, id):
        self._database = database
        self._original_id = id
        self._id = self.normalizeID(id)

    def getID(self, normalized=True):
        return self._id if normalized else self._original_id

    def findID(self, id, where=None):
        return self._database.findID(id, where)

    def getArgument(self, name, default=None):
        return self._database.getArgument(name, default)

    def replaceEntityLinks(self, content):
        return re.sub('<a ([^>]*)href=[\'"]http://journal.roll20.net/([^/]+)/([^\'"]+)[\'"]([^>]*)>(.*?)</a>', self._foundJournal, content)

    def replaceCompendiumLinks(self, content):
        return re.sub('<a ([^>]*)href=[\'"]https?://roll20.net/compendium/dnd5e/([^\'"]+)(?:(?:%3[aA])|:)([^\'"]+)[\'"]([^>]*)>(.*?)</a>', self._foundCompendium, content)

    def findCompendiumItem(self, compendium, item_name):
        converter = self._database._converter
        if converter.hasSystemPacks():
            items = []
            if compendium == "Spells":
                db = converter.packs.get("spells", None)
                if db:
                    items = db.entities
            elif compendium == "Items":
                db = converter.packs.get("items", None)
                if db:
                    items = db.entities
            elif compendium == "Classes":
                db = converter.packs.get("classes", None)
                if db:
                    items = db.entities
            elif compendium == "Class Features":
                db = converter.packs.get("classfeatures", None)
                if db:
                    items = db.entities
            for item in items:
                if "name" in item and item["name"] == item_name:
                    return item
        return None

    def _foundCompendium(self, match):
        converter = self._database._converter
        item_id = None
        before_href = match.group(1)
        compendium = match.group(2)
        name = urllib.parse.unquote(match.group(3))
        name = name.split("#")[0].split("?")[0]
        after_href = match.group(4)
        text = match.group(5)
        if self.getArgument("export_as_module", False):
            return "@Item[" + name + "]"
        if compendium == "Spells":
            folder = "D&D 5e Spells (SRD)"
            folder_id = "r20converter-dnd5e-spells"
        elif compendium == "Items":
            folder = "D&D 5e Items (SRD)"
            folder_id = "r20converter-dnd5e-items"
        item = self.findCompendiumItem(compendium, name)
        if item:
            item_id = name
            converter.folders.ensureFolder(folder_id, folder, "Item")
            entity = Entity(converter.items, item_id)
            entity.entity = item
            entity.entity["_id"] = entity.getID()
            entity.entity["folder"] = Entity.normalizeID(folder_id)
            converter.items.addEntity(entity)
        if item_id:
            return self.replaceEntityLinks('<a %shref="http://journal.roll20.net/item/%s"%s>%s</a>' % (before_href, item_id, after_href, text))
        else:
            print("Could not find compendium item of type '%s' and name '%s'" % (compendium, name))
            return match.group(0)
        

    def _foundJournal(self, match):
        before_href = match.group(1)
        journal = match.group(2)
        id = match.group(3)
        after_href = match.group(4)
        text = match.group(5)
        if journal in ["handout", "character", "item"]:
            icon = {"handout": "fa-book-open", "character": "fa-user", "item": "fa-suitcase"}[journal]
            entity = {"handout": "JournalEntry", "character": "Actor", "item": "Item"}[journal]
            return '<a class="entity-link" data-entity=%s data-id=%s %s%s><i class="fas %s"></i>%s</a>' % (entity, self.normalizeID(id), before_href, after_href, icon, text)
        else:
            return match.group(0)

    @staticmethod
    def strToID(id_str):
        new_str = hashlib.sha256(id_str.encode()).hexdigest()
        return base64.b64encode(new_str[-12:].encode()).decode()

    @staticmethod
    def normalizeID(id):
        if id is None:
            return None
        if id in Entity.id_database:
            return Entity.id_database[id]
        normalized_id = Entity.strToID(id)
        index = 0
        while normalized_id in Entity.id_database.values():
            print("Found an ID conflict for %s=%s\n%s" % (id, normalized_id, str(Entity.id_database)))
            new_id = "%s%d" % (id, index)
            normalized_id = Entity.strToID(new_id)
            index += 1
        Entity.id_database[id] = normalized_id
        return normalized_id

    # Used to fix the sometimes broken color codes in R20
    @staticmethod
    def color(val, default="#c0c0c0", allow_transparent=False):
        if allow_transparent and val == "transparent":
            return None
        m = re.match(r"rgb\((\d+), (\d+), (\d+)\)", val)
        if m:
            return "#%02x%02x%02x" % tuple(map(int, m.groups()))
        if not val.startswith("#") or len(val) < 4:
            return default
        val = val[1:]
        try:
            if len(val) < 6:
                rgb = tuple(int(val[i:i+1], 16) * 16 for i in (0, 1, 2))
            else:
                rgb = tuple(int(val[i:i+2], 16) for i in (0, 2, 4))
            return "#%02x%02x%02x" % rgb
        except:
            return default

    @staticmethod
    def urlsafe(filename):
        url = urllib.parse.quote(filename.replace(os.path.sep, "/").replace(" ", "_"))
        url.replace("/", os.path.sep)
        # Url encoded characters won't resolve, since the URL would become invalid, so we replace them
        return re.sub("%([0-9A-F]{2})", "_\\1", url)

    def getDirectoryName(self):
        world_dir_name = os.path.basename(os.path.dirname(os.path.join(self._database._path, ".")))
        if self.getArgument("export_as_module", False):
            directory = "modules"
        else:
            directory = "worlds"
        return os.path.join(directory, world_dir_name)

    def getDestinationPaths(self, destination):
        index = 1
        # Remove leading, trailing and duplicate spaces in the destination name
        destination = re.sub(" +", " ", destination).strip()
        destination_safe = self.urlsafe(destination)
        while True:
            dest_filename = os.path.join(self._database._path, destination_safe)
            # Check for conflicts
            if os.path.exists(dest_filename):
                splitext = os.path.splitext(destination)
                new_destination = "".join([splitext[0], "_%d_" % index, splitext[1]])
                destination_safe = self.urlsafe(new_destination)
                index += 1
            else:
                break

        try:
            os.makedirs(os.path.dirname(dest_filename))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        config_path = os.path.join(self.getDirectoryName(), destination_safe)
        return (dest_filename, config_path.replace(os.path.sep, "/"))
    
    def fixImageUrl(self, url):
        if url == "":
            return ""
        if not url.startswith("http"):
            url = "https://app.roll20.net/" + url
        # all Roll20 URLs use thumb/med/max/original for the filename but the actual image
        # loaded depends on the size. If we don't grab the original image, then maps will be
        # of much lower resolution than they should be.
        # Also remove the '?number' at the end of URLs because they seem unnecessary and they
        # break FVTT which doesn't recognize the URL as having a valid extension.
        url = re.sub(r"/(thumb|med|max)\.", r"/original.", url)
        return url

    def downloadResource(self, url, destination):
        (dest_filename, config_path) = self.getDestinationPaths(destination)
        url = self.fixImageUrl(url)
        content = Entity.resource_cache.get(url, None)
        if content is None:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    content = r.content
                    Entity.resource_cache[url] = content
            except:
                pass
        if content is not None:
            with open(dest_filename, "wb") as f:
                f.write(content)
            return (dest_filename, config_path)
        else:
            print("ERROR: Can't download URL : %s" % url)
            return (None, "")

    def copyFile(self, file, destination):
        (dest_filename, config_path) = self.getDestinationPaths(destination)
        with open(dest_filename, "wb") as f:
            f.write(file.read())
        return (dest_filename, config_path)

    def copyZipFile(self, filename, destination):
        try:
            zipfile = self._database._converter.getZipFile(filename)
            return self.copyFile(zipfile, destination)
        except Exception as e:
            print("Error copying file '%s' from Zip: %s" % (filename, e))
            return (None, "")

    def __str__(self):
        return json.dumps(self.entity)

class EmptyDB(DatabaseFile):
    def __init__(self, converter, name):
        DatabaseFile.__init__(self, converter, name + ".db")