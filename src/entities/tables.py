from .base import DatabaseFile, Entity
import os


class Tables(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "tables.db")
        self._tables = RollableTables(converter)
        self._decks = Decks(converter)
        self.entities = self.genEntities()

    def genEntities(self):
        return self._tables.entities + self._decks.entities

class RollableTables(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "tables.db")
        self._tables = self._campaign.get("tables", [])
        self.entities = self.genEntities()

    def genEntities(self):
        tables = []
        for index, r20table in enumerate(self._tables):
            table = Table(self, r20table, index, "tables-rollable-tables", True)
            items = r20table["items"]
            # Older exporter was creating an object of {id: item_data}, newer exports the tables and decks as arrays instead
            if isinstance(items, dict):
                items = items.values()
            if not isinstance(items, list):
                items = []
            for item_index, entry in enumerate(items):
                name = entry.get("name", "")
                img = entry.get("avatar", "")
                weight = entry.get("weight", 1)
                try:
                    weight = int(weight)
                except:
                    weight = 1
                if img != "":
                    if not self.getArgument("use_original_image_urls", False):
                        filename = os.path.join("tables", "%03d - %s" % (index, r20table["name"]), "%s.png" % name)
                        if self.getArgument("json", False):
                            (_, img) = table.downloadResource(img, filename)
                        else:
                            zip_filename = os.path.join("tables", "%03d - %s" % (index, r20table["name"]), "%03d - %s.png" % (item_index, name))
                            (_, img) = table.copyZipFile(img, zip_filename, filename)
                table.addEntry(name, img, weight)
            tables.append(table)
        return tables

class Decks(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "decks.db")
        self._decks = self._campaign.get("decks", [])
        self.entities = self.genEntities()

    def genEntities(self):
        tables = []
        for index, deck in enumerate(self._decks):
            table = Table(self, deck, index, "tables-decks", False)
            cards = deck["cards"]
            # Older exporter was creating an object of {id: item_data}, newer exports the tables and decks as arrays instead
            if isinstance(cards, dict):
                cards = cards.values()
            if not isinstance(cards, list):
                cards = []
            for card_index, card in enumerate(cards):
                name = card.get("name", "")
                img = card.get("avatar", "")
                weight = 1
                drawn = card["id"] in deck["discardPile"]
                if img != "":
                    if not self.getArgument("use_original_image_urls", False):
                        filename = os.path.join("decks", "%03d - %s" % (index, deck["name"]), "%s.png" % name)
                        if self.getArgument("json", False):
                            (_, img) = table.downloadResource(img, filename)
                        else:
                            zip_filename = os.path.join("decks", "%03d - %s" % (index, deck["name"]), "%03d - %s.png" % (card_index, name))
                            (_, img) = table.copyZipFile(img, zip_filename, filename)
                item = self._converter.cards.createItemInventory(card["id"], name, name, "loot", None)
                collection = "{}.cards".format(self._converter.name) if self.getArgument("export_as_module", False) else "Item"
                table.addEntry(name, img, weight, item, collection, drawn)

                item.entity["img"] = img
                item.entity["folder"] = Entity.normalizeID("items-" + deck["id"])
                item.entity["permission"] = table.entity["permission"]
                self._converter.cards.addEntity(item)


            tables.append(table)
        return tables

class Table(Entity):
    RESULT_TYPE_TEXT = 0
    RESULT_TYPE_ENTITY = 1
    RESULT_TYPE_COMPENDIUM = 2
    def __init__(self, database, table, index, parent, with_replacement=True):
        Entity.__init__(self, database, table["id"])
        self.logInfo("Creating Rollable Table : %s" % table["name"])
        permissions = {"default": Table.PERMISSION_OWNER if table["showplayers"] else Table.PERMISSION_NONE}
        if self.getArgument("export_as_module", False):
            parent = None
        self.entity = {
            "_id": self._id,
            "name": table["name"] or "Unnamed Table",
            "permission": permissions,
            "folder": Entity.normalizeID(parent),
            "flags": {},
            "sort": index * Entity.SORT_ORDER,
            "formula": "0",
            "replacement": with_replacement,
            "displayRoll": False,
            "results": []
        }

    def addEntry(self, name, img=None, weight=1, entity=None, collection=None, drawn=False):
        minRoll = 1
        for result in self.entity["results"]:
            minRoll = result["range"][1] + 1
        maxRoll = minRoll + weight - 1
        result_type = Table.RESULT_TYPE_TEXT
        if entity:
            result_type = Table.RESULT_TYPE_COMPENDIUM if self.getArgument("export_as_module", False) else Table.RESULT_TYPE_ENTITY
        entry = {
            "_id": self.genID(),
            "flags": {},
            "type": result_type,
            "collection": collection,
            "resultId": entity._id if entity else "",
            "text": name,
            "img": img,
            "weight": weight,
            "range": [minRoll, maxRoll],
            "drawn": drawn
        }
        self.entity["results"].append(entry)
        self.entity["formula"] = "1d{}".format(maxRoll)
        return entry
