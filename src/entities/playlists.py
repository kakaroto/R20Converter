from .base import DatabaseFile, Entity
from .journal import Handout
import os

class Playlists(DatabaseFile):
    def __init__(self, converter):
        DatabaseFile.__init__(self, converter, "playlists.db")
        self.entities = self.genEntities()

    def addToFolder(self, folder_id, folder, folder_path):
        handouts = []
        index = 0
        for item in folder:
            if type(item) == dict:
                dirname = "%03d - %s" % (index, item["n"])
                handouts.extend(self.addToFolder("handout" + item["id"], item["i"], os.path.join(folder_path, dirname)))
                index += 1
            else:
                handout = self.findID(item, "handout")
                if handout != None:
                    handouts.append(Handout(self, handout, index, folder_id, folder_path))
                    index += 1
                elif self.findID(item, "character") != None:
                    index += 1
                    
        return handouts

    def genEntities(self):
        playlists = []
        root_playlist = {"id": "root-playlist",
                         "n": "Root Playlist",
                         "s": "",
                         "i": []
                         }
        root_playlist_has_items = False
        for index, item in enumerate(self._campaign["jukeboxfolder"]):
            if type(item) == dict:
                folder = "%03d - %s" % (index, item["n"])
                playlists.append(Playlist(self, item, folder))
                # Need to add empty items to keep order in the playlist for finding the files in the zip
                root_playlist["i"].append("")
            else:
                root_playlist["i"].append(item)
                root_playlist_has_items = True

        if root_playlist_has_items:
            playlists.append(Playlist(self, root_playlist))

        return playlists

class Playlist(Entity):
    def __init__(self, database, playlist, folder_name=""):
        Entity.__init__(self, database, playlist["id"])
        modes = {"s": 1, # Shuffle
                 "a": 2, # All at once
                 "o": 0, # Play Once
                 "b": 0, # Loop
                 }
        sounds = []
        sound_id = 1
        print("creating playlist %s" % playlist["n"])
        for index, track_id in enumerate(playlist["i"]):
            track = self.findID(track_id, "track")
            if track:
                mp3_file = "%03d - %s.mp3" % (index, track["title"])
                filename = os.path.join("jukebox", folder_name, mp3_file)
                dest = os.path.join("audio", folder_name, mp3_file)
                if self.getArgument("json", False):
                    print("Cannot download Jukebox Track from campaign.json file")
                    mp3_path = ""
                else:
                    (_, mp3_path) = self.copyZipFile(filename, dest)
                if mp3_path != "":
                    sounds.append({"id": sound_id,
                                   "flags": {},
                                   "path": mp3_path,
                                   "repeat": track["loop"],
                                   "volume": track["volume"] / 100.0,
                                   "name": track["title"],
                                   "playing": track["playing"]
                                   })
                    sound_id += 1

        self.entity = {"_id": self._id,
                       "name": playlist["n"],
                       "permission": {"default": 0},
                       "flags": {},
                       "sounds": sounds,
                       "mode": modes.get(playlist["s"], -1), # Default to soundboard only for the root folder
                       "playing": False
                       }