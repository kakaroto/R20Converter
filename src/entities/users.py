from .base import DatabaseFile, Entity

class Users(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "users.db")
        self._players = self._campaign["players"]
        self._known_gm = self._campaign.get("account_id", self._players[0]["d20userid"])
        self.entities = self.genEntities()

    def genEntities(self):
        users = []
        for player in self._players:
            if self._campaign["playerspecificpages"] and player["id"] in self._campaign["playerspecificpages"]:
                scene = self._campaign["playerspecificpages"][player["id"]]
            else:
                scene = self._campaign["playerpageid"]
            is_gm = player["d20userid"] == self._known_gm
            users.append(User(self, player, len(users), is_gm, scene))
        return users

    def getGM(self):
        for user in self.entities:
            if user.entity["permission"] == 4:
                return user
        return self.entities[0]

class User(Entity):
    ROLE_PLAYER = 1
    ROLE_GM = 4
    def __init__(self, database, player, index, is_gm=False, scene=None):
        Entity.__init__(self, database, player["id"])
        hotbar = {}
        macrobar = player.get("macrobar", [])
        if macrobar == "":
            macrobar = []
        for index, macro in enumerate(macrobar):
            if macro == "":
                continue
            if isinstance(macro, str):
                (macro_src, macro_id, _) = (macro +"||").split("|", 2)
                macro = {"src": macro_src, "id": macro_id}
            hotbar[str(index + 1)] = Entity.normalizeID(macro["id"])
        self.entity = {"_id": self._id,
                       "name": player["displayname"],
                       "flags":{},
                       "color": self.color(player["color"]),
                       "scene": Entity.normalizeID(scene),
                       "permission": 0,
                       "permissions": {},
                       "sort": index * Entity.SORT_ORDER,
                       "hotbar": hotbar
                       }
        print("Creating User : %s (%s)" % (self.entity["name"], "GM" if is_gm else "Player"))
        
        self.setGM(is_gm)

    def setGM(self, gm):
        self.entity["role"] = User.ROLE_GM if gm else User.ROLE_PLAYER
        self.entity["password"] = self.getArgument("gm_password" if gm else "player_password", "")