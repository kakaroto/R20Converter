from .base import DatabaseFile, Entity
import json

class SettingsDB(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "settings.db")
        self.entities = [Setting(self, "core.moduleConfiguration", {"permission_viewer":True}),
                         Setting(self, "dnd5e.systemMigrationVersion", "1.2.4"),
                         Setting(self, "permission_viewer.migrated", "1"),
                         Setting(self, "core.permissions", {})]

class Setting(Entity):
    def __init__(self, database, key, value):
        Entity.__init__(self, database, key)
        self.entity = {"_id": self._id,
                       "key": key,
                       "value": json.dumps(value)}
