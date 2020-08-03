import os
import io
import eel
import json
import zipfile
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

class ForwardToFunctionStream(io.TextIOBase):
    def write(self, string):
        eel.writeStdout(string)() # pylint: disable=no-member
        return len(string)

class GUIClass:
    def __init__(self):
        eel.init("client/dist")
        self.campaign = None
        self.loadedPath = None

    def hideConsole(self):
        if win32gui:
            the_program_to_hide = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(the_program_to_hide , win32con.SW_HIDE)

    def start(self):
        stdout = ForwardToFunctionStream()
        stderr = ForwardToFunctionStream()
        with redirect_stderr(stderr):
            with redirect_stdout(stdout):
                browsers = ["chrome", "edge", "electron"]
                found_browser = False
                for browser in browsers:
                    eel_browser = getattr(eel, browser, None)
                    if eel_browser is None:
                        continue
                    path = eel_browser.find_path()
                    if path is True or path is not None:
                        try:
                            eel.start('index.html', port=0, mode=browser)
                            found_browser = True
                            break
                        except:
                            pass
                if not found_browser:
                    eel.start('index.html', port=0, mode=browser)

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


@eel.expose
def getVersion():
    return version


@eel.expose
def ask_file():
    """ Ask the user to select a file """
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = askopenfilename(parent=root)
    root.update()
    return None if file_path == "" else file_path

@eel.expose
def ask_folder():
    """ Ask the user to select a folder """
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
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
        print("loadCampaign: Exception ", str(e))
        return str(e)
@eel.expose
def getCampaignTitle(file_type, path):
    try:
        GUI.loadCampaign(file_type, path)
        title = GUI.campaign["campaign_title"]
        return title
    except Exception as e:
        print("Exception in getCampaignTitle ", str(e))
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
    print("Starting conversion. Received arguments : ", args)
    error = None
    try:
        converter = R20Converter(AttrDict(args))
        converter.convert()
    except Exception as e:
        error = e
        print(e)
        try:
            import traceback
            traceback.print_exc()
        except:
            pass

    if error:
        message = "Error converting campaign : \n" + str(error)
        message += "\nPlease contact the author with the log of the error from the console window"
    else:
        message = "\nConversion completed.\nMake sure to install the FVTT modules 'permission_viewer' and 'furnace' (see README file for more information)\n\n"
        message += "It is strongly suggested to check the sheets of the NPCs and player characters for any errors or missing information, or for adding special traits.\n"
        message += "Some things may not have been carried over, especially to-hit, damage, AC or saving throw modifiers or more complicated weapon or spell macros\n"
        message += "\nThank you for your support!"
    print(message)
    return {
        "error": error is not None,
        "message": message
    }

GUI = GUIClass()