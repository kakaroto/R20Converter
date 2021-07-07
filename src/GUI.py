import os
import io
import sys
import eel
import json
import zipfile
import subprocess
import platform
from slugify import slugify
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from R20Converter import R20Converter

if platform.system() == 'Darwin':
    import wx
    useWx = True
else:
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename, askdirectory
    useWx = False

from utils import getFVTTDataPath
from version import version

class GUIClass:
    def __init__(self):
        path = "client/dist"
        if not os.path.exists(path) and platform.system() == "Darwin":
            path = os.path.join(os.path.dirname(sys.executable), "client/dist")
        eel.init(path)
        self.campaign = None
        self.loadedPath = None

    def logInfo(self, msg):
        eel.logInfo(msg)() # pylint: disable=no-member
    def logWarning(self, msg):
        eel.logWarning(msg)() # pylint: disable=no-member
    def logError(self, msg):
        eel.logError(msg)() # pylint: disable=no-member

    def start(self):
        # On windows and mac, use bundled electron
        if platform.system() in ['Windows', 'Darwin']:
            return eel.start('index.html', port=0, mode="custom", custom_callback=self.PopenElectron)

        # On linux, try chrome then default
        try:
            eel.start('index.html', port=0, mode="chrome")
        except:
            eel.start('index.html', port=0, mode="default")

    def PopenElectron(self, args, urls):
        if platform.system() == 'Darwin':
            path = "Electron.app"
            if not os.path.exists(path):
                path = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Resources", "Electron.app")
            cmd = ["open", "-a", path, "--args"]
        else:
            cmd = ["electron/electron"]
        cmd += args + [';'.join(urls)]
        return subprocess.Popen(cmd)

    def loadCampaign(self, file_type, path):
        if path == self.loadedPath:
            return
        if file_type == "JSON":
            with open(path, "r", encoding='utf-8') as f:
                self.campaign = json.load(f)
        else:
            zip = zipfile.ZipFile(path, "r")
            self.campaign = json.load(zip.open("campaign.json".replace(os.path.sep, "/")))
        self.loadedPath = path


GUI = GUIClass()

@eel.expose
def getVersion():
    return version


@eel.expose
def ask_file():
    """ Ask the user to select a file """
    if useWx:
        app = wx.App(None)
        dialog = wx.FileDialog(None, 'Browse Campaign', wildcard="Campaign File(*.json; *.zip)|*.json;*.zip", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        app.SetTopWindow(dialog)
        style = dialog.GetWindowStyle()
        dialog.SetWindowStyle(style | wx.STAY_ON_TOP)
        if platform.system() == 'Darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "R20Converter-{}" to true' '''.format(version))
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
        else:
            path = None
        dialog.Destroy()
    else:
        root = Tk()
        root.wm_attributes('-topmost', 1)
        root.withdraw()
        file_path = askopenfilename(parent=root)
        path = None if file_path == "" else file_path
    return path

@eel.expose
def ask_folder():
    """ Ask the user to select a folder """
    if useWx:
        app = wx.App(None)
        dialog = wx.DirDialog(None, 'Browse folder', "", style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        app.SetTopWindow(dialog)
        style = dialog.GetWindowStyle()
        dialog.SetWindowStyle(style | wx.STAY_ON_TOP)
        if platform.system() == 'Darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "R20Converter-{}" to true' '''.format(version))
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
        else:
            path = None
        dialog.Destroy()
    else:
        root = Tk()
        root.wm_attributes('-topmost', 1)
        root.withdraw()
        folder = askdirectory(parent=root)            
        root.update()
        path = None if folder == "" else folder
    return path

@eel.expose
def does_file_exist(file_path):
    """ Checks if a file exists """
    return os.path.isfile(file_path)


@eel.expose
def does_folder_exist(path):
    """ Checks if a folder exists """
    return os.path.isdir(path)

@eel.expose
def loadCampaign(file_type, path):
    try:
        GUI.loadCampaign(file_type, path)
        return None
    except Exception as e:
        return str(e)
@eel.expose
def getCampaignTitle(file_type, path):
    try:
        GUI.loadCampaign(file_type, path)
        title = GUI.campaign["campaign_title"]
        return title
    except:
        return None
@eel.expose
def getCampaignSlug(file_type, path):
    title = getCampaignTitle(file_type, path)
    if title:
        return slugify(title)
    return None

@eel.expose
def getFoundryDirectory():
    path = getFVTTDataPath()
    return path if os.path.isdir(path) else None

@eel.expose
def slugifyString(name):
    return slugify(name)

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

@eel.expose
def startConversion(args):
    error = None
    try:
        converter = R20Converter(AttrDict(args), logger=GUI)
        converter.convert()
    except Exception as e:
        try:
            import traceback
            error = traceback.format_exc()
        except:
            error = str(e)
        GUI.logError(e)

    if error:
        message = "Error converting campaign with R20Converter v" + version + ": \n" + error
        message += "\nPlease contact the author with the log of the error from the console window"
    else:
        message = "\nConversion completed.\n\n"
        message += "It is strongly suggested to check the sheets of the NPCs and player characters for any errors or missing information, or for adding special traits.\n"
        message += "Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros\n"
        message += "If using <a href='https://forge-vtt.com/setup' target='_blank'>The Forge</a> for hosting your Foundry games, you can now import the generated world using the Import Wizard.\n"
        message += "\nThank you for your support!"
    GUI.logInfo(message)
    return {
        "error": error is not None,
        "message": message
    }
