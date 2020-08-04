import os
import io
import sys
import eel
import json
import zipfile
import subprocess
from slugify import slugify
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from R20Converter import R20Converter

from tkinter import Tk
from tkinter.filedialog import askopenfilename, askdirectory

from utils import getFVTTDataPath
from version import version

try:
    import win32gui, win32con
except Exception as e:
    win32gui = win32con = None

class GUIClass:
    def __init__(self):
        eel.init("client/dist")
        self.campaign = None
        self.loadedPath = None

    def logInfo(self, msg):
        eel.logInfo(msg)() # pylint: disable=no-member
    def logWarning(self, msg):
        eel.logWarning(msg)() # pylint: disable=no-member
    def logError(self, msg):
        eel.logError(msg)() # pylint: disable=no-member

    def hideConsole(self):
        if win32gui:
            the_program_to_hide = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(the_program_to_hide , win32con.SW_HIDE)

    def start(self):
        # On windows and mac, use bundled electron
        if sys.platform in ['win32', 'win64', 'darwin']:
            return eel.start('index.html', port=0, mode="custom", custom_callback=self.PopenElectron)
        # On linux, try chrome then default
        try:
            eel.start('index.html', port=0, mode="chrome")
        except:
            eel.start('index.html', port=0, mode="default")

    def PopenElectron(self, args, urls):
        cmd = ["electron/electron"] + args + [';'.join(urls)]
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
    root = Tk()
    root.wm_attributes('-topmost', 1)
    root.withdraw()
    file_path = askopenfilename(parent=root)
    root.update()
    return None if file_path == "" else file_path

@eel.expose
def ask_folder():
    """ Ask the user to select a folder """
    root = Tk()
    root.wm_attributes('-topmost', 1)
    root.withdraw()
    folder = askdirectory(parent=root)
    root.update()
    return None if folder == "" else folder

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
        error = e
        GUI.logError(e)

    if error:
        message = "Error converting campaign : \n" + str(error)
        message += "\nPlease contact the author with the log of the error from the console window"
    else:
        message = "\nConversion completed.\nMake sure to install the FVTT modules 'permission_viewer' and 'furnace' (see README file for more information)\n\n"
        message += "It is strongly suggested to check the sheets of the NPCs and player characters for any errors or missing information, or for adding special traits.\n"
        message += "Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros\n"
        message += "\nThank you for your support!"
    GUI.logInfo(message)
    return {
        "error": error is not None,
        "message": message
    }
