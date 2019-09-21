#!/usr/bin/python

import os, sys, argparse, json

class DatabaseFile(object):
    def __init__(self, path, filename=None):
        self._path = path
        self._filename = filename
        self.load()

    def __str__(self):
        return "\n".join(map(str, self.entities))

    def load(self):
        if self._filename is not None:
            full_path = os.path.join(self._path, "data", self._filename)
        else:
            full_path = self._path
        self.entities = {}
        with open(full_path, "r", encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                new_entity = json.loads(line)
                self.entities[new_entity["_id"]] = new_entity


class Differ(object):
    def __init__(self, args):
        self.args = args

        if args.world:
            worlds = [self.load_world(args.left), self.load_world(args.right)]
            self.diff_json("", worlds[0], worlds[1])
        elif args.json:
            with open(os.path.join(args.left), "r", encoding='utf-8') as f:
                left = json.load(f)
            with open(os.path.join(args.right), "r", encoding='utf-8') as f:
                right = json.load(f)
            self.diff_json("", left, right)
        else:
            left = DatabaseFile(args.left).entities
            right = DatabaseFile(args.right).entities
            self.diff_json("", left, right)

    def load_world(self, path):
        with open(os.path.join(path, "world.json"), "r", encoding='utf-8') as f:
            world = {"world": json.load(f)}
        for db in ["users", "sessions", "folders", "items", "scenes", "journal", "actors", "playlists", "combat", "settings", "chat"]:
            print("Loading %s" % db)
            world[db] = DatabaseFile(path, db + ".db").entities

        return world

    def diff_json(self, path, left, right):
        if type(left) == float and int(left) == left:
            left = int(left)
        if type(right) == float and int(right) == right:
            right = int(right)

        if type(left) != type(right):
            print("%s: type mismatch between left and right elements : %s != %s" % (path, type(left), type(right)))
        elif type(left) == dict:
            for key in left:
                if key in right:
                    self.diff_json(os.path.join(path, key), left[key], right[key])
                else:
                    print("%s: Key %s only in left json" % (path, key))
            for key in right:
                if key not in left:
                    print("%s: Key %s only in right json" % (path, key))
        elif type(left) == list:
            if len(left) != len(right):
                print("%s: Left and right lists have different length : %s != %s" % (path, len(left), len(right)))
            else:
                for i in range(len(left)):
                    self.diff_json(os.path.join(path, str(i)), left[i], right[i])
        elif type(left) == str:
            if left != right:
                print("%s: Strings are different" % path)
        else:
            if left != right:
                try:
                    print("%s: Values are different : '%s'(%s) != '%s'(%s)" % (path, str(left), type(left), str(right), type(right)))
                except:
                    print("%s: non-printable values are different : ''(%s) != ''(%s)" % (path, type(left), type(right)))

                    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FVTT Database Differ", epilog="Compare databases from two worlds.")
    parser.add_argument("--world", action="store_true", help="If set, will diff world directories instead of DB files")
    parser.add_argument("--json", action="store_true", help="If set, will diff json files")
    parser.add_argument("left", metavar="first-world", help="The first world's directory in public/worlds/")
    parser.add_argument("right", metavar="second-world", help="The secnd world's directory in public/worlds/")
    args = parser.parse_args()

    diff = Differ(args)
        
