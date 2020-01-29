import json
import os
import shutil

class World(object):
    def __init__(self, converter):
        self._converter = converter
        self._path = converter.path
        self._name = converter.name
        self._title = converter.getArgument("campaign_title")
        if self._title is None:
            self._title = converter.campaign["campaign_title"]
        self._description = converter.getArgument("description")
        self._copy_templates = len(converter.chat.entities) > 0
            

    def toDict(self):
        return {"id": self._name,
                "name": self._name,
                "title": self._title,
                "description": self._description,
                "system": "dnd5e",
                "coreVersion": "0.4.5",
                "systemVersion": 0.8,
                "packs": [],
                "scripts":  ["templates/roll20-templates.js"] if self._copy_templates else [],
                "styles": ["templates/roll20-templates.css"] if self._copy_templates else [],
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

        if self._copy_templates:
            path = os.path.join(self._path, "templates")
            os.makedirs(path)
            shutil.copy("templates/roll20-templates.css", path)
            shutil.copy("templates/roll20-templates.js", path)

        return self