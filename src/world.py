import json
import os

class World(object):
    def __init__(self, converter):
        self._path = converter.path
        self._name = os.path.basename(os.path.dirname(os.path.join(self._path, ".")))
        self._title = converter.getArgument("campaign_title")
        if self._title is None:
            self._title = converter.campaign["campaign_title"]
        self._description = converter.getArgument("description")

    def toDict(self):
        return {"id": self._name,
                "name": self._name,
                "title": self._title,
                "description": self._description,
                "system": "dnd5e",
                "coreVersion": "0.4.2",
                "systemVersion": 0.73,
                "packs": [],
                "scripts": [],
                "styles": [],
                "unavailable": 0,
                "languages": []
                }

    # This is a json file, not a db file, so let's override the __str__ method
    def __str__(self):
        return json.dumps(self.toDict(), indent=2)

    def save(self):
        filename = os.path.join(self._path, "world.json")
        with open(filename, "w", encoding='utf-8') as f:
            f.write(str(self))
        return self