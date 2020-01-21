from .base import DatabaseFile, Entity

class Macros(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "macros.db")
        self._macros = self._campaign.get("macros", [])
        self._img_path = None
        self.entities = self.genEntities()

    def genEntities(self):
        return [Macro(self, macro, index) for index, macro in enumerate(self._macros)]

class Macro(Entity):
    def __init__(self, database, macro, index):
        Entity.__init__(self, database, macro["id"])
        if self._database._img_path is None:
            (_, img_path) = self.downloadResource("https://lh3.googleusercontent.com/swEnBHMCVeDnhj21txjMIFqAiP09T7l0-XlWE0lnrnp5tOVYUJ8yAvWocECizn71qLo=s180-rw", "macros/roll20_macro.png")
            if img_path != "":
                self._database._img_path = img_path
            else:
                self._database._img_path = "icons/svg/dice-target.svg"
        permissions = {"default": Macro.PERMISSION_NONE, Entity.normalizeID(macro["player_id"]): Macro.PERMISSION_OWNER}
        for player in macro.get("visibleto", "").split(","):
            if player == "all":
                permissions["default"] = Macro.PERMISSION_OBSERVER
            elif player != "":
                player_id = Entity.normalizeID(player)
                permissions[player_id] = Macro.PERMISSION_OBSERVER
        self.entity = {
            "_id":self._id,
            "name": macro["name"],
            "permission": permissions,
            "type": "chat",
            "sort": index * Entity.SORT_ORDER,
            "flags":{},
            "scope": "global",
            "command": macro["action"],
            "author": Entity.normalizeID(macro["player_id"]),
            # Roll 20 icon from "Roll20 for android" Android store app
            "img": self._database._img_path,
            "actorIds": []
        } 