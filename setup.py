import sys
from cx_Freeze import setup, Executable

sys.path.append("src")
# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = {
    "build_exe": {
        "packages": [],
        "includes": ["bottle_websocket"],
        "excludes": ["PySide2", "PyQt5"],
        "include_files": [
            ("Changelog.md", "Changelog.md"),
            ("README.md", "README.md"),
            ("README.html", "README.html"),
            ("templates", "templates"),
            ("client/dist", "client/dist")
        ]
    },
    "bdist_mac": {
        "iconfile": "client/public/logo.icns",
        "include_resources": [("Electron.app", "Electron.app")]
    },
    "bdist_dmg": {
        "volume_label": "R20Converter-0.9",
        "applications_shortcut": True
    }
}
                
# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"
    buildOptions["build_exe"]["include_files"].append(("electron", "electron"))
    buildOptions["build_exe"]["includes"].append("tkinter")
    buildOptions["build_exe"]["excludes"].append("wx")
    buildOptions["build_exe"]["excludes"].append("numpy")
if sys.platform == "darwin":
    buildOptions["build_exe"]["includes"].append("wx")
    buildOptions["build_exe"]["excludes"].append("tkinter")

executables = [
    Executable('src/main.py', base=base, targetName = 'R20Converter', icon = "client/public/logo.ico")
]

setup(name='R20Converter',
      version = '0.9',
      description = 'Convert a Roll 20 Campaign into a Foundry VTT world',
      options = buildOptions,
      executables = executables
      )
