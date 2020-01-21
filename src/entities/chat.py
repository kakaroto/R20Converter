import json
from .base import DatabaseFile, Entity
from .users import User

class ChatLog(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "chat.db")
        self._archive = self._campaign.get("chat_archive", [])
        self.entities = self.genEntities()

    def genEntities(self):
        messages = []
        for msg_group in self._archive:
            for msg_id in msg_group.keys():
                try:
                    messages.append(ChatMessage(self, msg_id, msg_group[msg_id]))
                except Exception as e:
                    print("Error converting Chat message ", e)
        return messages

class ChatMessage(Entity):
    TYPE_OTHER = 0
    TYPE_OOC = 1
    TYPE_IC = 2
    TYPE_EMOTE = 3
    TYPE_WHISPER = 4
    TYPE_ROLL = 5
    def __init__(self, database, id, message):
        Entity.__init__(self, database, id)
        roll_type = ChatMessage.TYPE_OOC
        whispers = []
        content = message["content"]
        sound = None
        roll = None
        if message["type"] == "whisper":
            if message["target"] == "gm":
                whispers = self.getGMWhispers()
            else:
                whispers.append(Entity.normalizeID(message["target"]))
            roll_type = ChatMessage.TYPE_WHISPER
        elif message["type"] == "whisper":
            roll_type = ChatMessage.TYPE_EMOTE
        elif message["type"] == "rollresult" or message["type"] == "gmrollresult":
            roll_type = ChatMessage.TYPE_ROLL
            content = message["origRoll"]
            sound = "sounds/dice.wav"
            r20roll = json.loads(message["content"])
            roll = Roll(content, r20roll)
            if message["type"] == "gmrollresult":
                whispers = self.getGMWhispers()
        if message.get("rolltemplate", None) is not None:
            raise Exception("Roll templates not supported yet")
        self.entity = {
            "_id": self._id,
            "flags": {},
            "type": roll_type,
            "user": Entity.normalizeID(message["playerid"]),
            "timestamp": {"$$date": message[".priority"]},
            "content": content,
            "speaker": {"alias": message["who"]},
            "whisper": whispers,
        } 
        if sound:
            self.entity["sound"] = sound
        if roll:
            self.entity["roll"] = json.dumps(roll.toJSON())

    def getGMWhispers(self):
        whispers = []
        for i in self._converter.users.entities:
            if i.entity["role"] == User.ROLE_GM:
                whispers.append(i._id)
        return whispers

class Roll:
    def __init__(self, formula, r20roll):
        self.formula = formula
        self.total = r20roll["total"]
        self.parts = []
        for roll in r20roll["rolls"]:
            if roll["type"] == "R":
                dice = {
                    'class': 'Die',
                    'faces': roll["sides"],
                    "formula": "{}d{}".format(roll["dice"], roll["sides"]),
                    "options": {},
                    "rolls": []
                }
                for result in roll["results"]:
                    die = {"roll": result["v"]}
                    if result.get("d", False):
                        die["discarded"] = True
                    dice["rolls"].append(die)
                self.parts.append(dice)
            elif roll["type"] == "M":
                self.parts.append(roll["expr"])
            elif roll["type"] == "L" or roll["type"] == "C":
                pass # text
            else:
                raise Exception("Unknown roll type %s" % str(roll))

    def toJSON(self):
        return {
            'class': 'Roll',
            'formula': self.formula,
            'parts': self.parts,
            'total': self.total
        }
    