import json
import os

class World(object):
    def __init__(self, converter):
        self._path = converter.path
        self._title = converter.getArgument("campaign_title")
        if self._title is None:
            self._title = converter.campaign["campaign_title"]
        self._description = converter.getArgument("description")

    def toDict(self):
        return {"name": self._title,
                "description": self._description,
                "system": "dnd5e",
                "coreVersion": "0.3.5",
                "systemVersion": 0.61,
                "packs": [],
                "scripts": [],
                "styles": []
                }

    # This is a json file, not a db file, so let's override the __str__ method
    def __str__(self):
        return json.dumps(self.toDict(), indent=2)

    def save(self):
        filename = os.path.join(self._path, "world.json")
        with open(filename, "w") as f:
            f.write(str(self))
        return self