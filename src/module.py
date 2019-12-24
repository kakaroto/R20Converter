import json
import os
from version import version

class Module(object):
    def __init__(self, converter):
        self._converter = converter
        self._path = converter.path
        self._name = converter.name
        self._title = converter.getArgument("campaign_title")
        if self._title is None:
            self._title = converter.campaign["campaign_title"]
        self._description = converter.getArgument("description")
        self._packs = []
        
        if len(converter.journal.entities) > 0:
            converter.journal.save()
            self._packs.append(self._newPack("journal", "Handouts", "JournalEntry", "journal.db"))
        if len(converter.actors.entities) > 0:
            converter.actors.save()
            self._packs.append(self._newPack("actors", "Actors", "Actor", "actors.db"))
        if len(converter.items.entities) > 0:
            converter.items.save()
            self._packs.append(self._newPack("items", "Items", "Item", "items.db"))
        if len(converter.scenes.entities) > 0:
            converter.scenes.save()
            self._packs.append(self._newPack("scenes", "Scenes", "Scene", "scenes.db"))
        if len(converter.playlists.entities) > 0:
            converter.playlists.save()
            self._packs.append(self._newPack("playlists", "Jukebox", "Playlist", "playlists.db"))
        if len(converter.tables.entities) > 0:
            converter.tables.save()
            self._packs.append(self._newPack("tables", "Rollable Tables", "RollTable", "tables.db"))
        if len(converter.decks.entities) > 0:
            converter.decks.save()
            self._packs.append(self._newPack("decks", "Decks", "RollTable", "decks.db"))
        if len(converter.cards.entities) > 0:
            converter.cards.save()
            self._packs.append(self._newPack("cards", "Deck Cards", "Item", "cards.db"))


    def _newPack(self, name, label, entity, filename):
	    return {"name": name,
                "label": label + " (" + self._title + ")",
                "path": os.path.join("packs", filename).replace(os.path.sep, "/"),
                "module": self._name,
                "entity": entity
            }

    def toDict(self):
        return {"name": self._name,
                "title": self._title,
                "description": self._description,
                "author": "R20Converter",
                "version": version,
                "minimumCoreVersion": "0.4.3",
                "packs": self._packs
            } 

    # This is a json file, not a db file, so let's override the __str__ method
    def __str__(self):
        return json.dumps(self.toDict(), indent=2)

    def save(self):
        filename = os.path.join(self._path, "module.json")
        with open(filename, "w", encoding='utf-8') as f:
            f.write(str(self))
        return self