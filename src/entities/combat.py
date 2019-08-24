from .base import DatabaseFile, Entity
from .scenes import Scene

class Combat(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "combat.db")
        self.entities = self.genEntities()

    def genEntities(self):
        encounters = []
        per_page = {}
        for order in self._campaign["turnorder"]:
            per_page.setdefault(order.get("_pageid", self._campaign["playerpageid"]), []).append(order)
        for page in per_page:
            active = (page == self._campaign["playerpageid"])
            encounters.append(Encounter(self, "roll20-initiative-" + page, per_page[page], page, active))
        return encounters

class Encounter(Entity):
    def __init__(self, database, id, turnorder, page_id, active):
        Entity.__init__(self, database, id)
        combatants = []
        combatant_id = 1
        for token in turnorder:
            page_tokens = Scene.token_ids.get(page_id, {})
            token_id = page_tokens.get(token["id"], None)
            if token_id:
                hidden = False
                page = self.findID(page_id, "page")
                if page:
                    graphic = Scene.findItemByID(page, token["id"], "graphics")
                    hidden = (graphic and graphic["layer"] == "gmlayer")
                try:
                    initiative = int(token["pr"])
                except ValueError:
                    initiative = None
                combatants.append({"id": combatant_id,
                                   "flags": {},
                                   "tokenId": token_id,
                                   "initiative": initiative,
                                   "hidden": hidden})
                combatant_id += 1

        self.entity = {"_id": self._id,
                       "flags": {},
                       "scene": Entity.normalizeID(page_id),
                       "combatants": combatants,
                       "active": active,
                       "round":0,
                       "turn":0}