import os
import platform
import json

def getFVTTDataPath():
    path = os.environ.get("FOUNDRY_VTT_DATA_PATH", None)
    if path is None:
        system = platform.system()
        if system == "Windows":
            path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")), "FoundryVTT")
        elif system == "Darwin":
            os.path.join(os.path.expanduser("~/Library/Application Support"), "FoundryVTT")
        else:
            path = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "FoundryVTT")
            if not os.path.exists(path):
                path = os.path.join(os.path.expanduser("~"), "FoundryVTT")
            if not os.path.exists(path):
                path = os.path.join("/local", "FoundryVTT")
    
    try:
        with open(os.path.join(path, "Config", "options.json"), "r", encoding='utf-8') as f:
            options = json.load(f)
            dataPath = options.get("dataPath", None)
            if dataPath:
                path = dataPath
    except:
        pass

    return path

def logInfo(msg):
    print(msg)
def logWarning(msg):
    print(msg)
def logError(msg):
    print(msg)