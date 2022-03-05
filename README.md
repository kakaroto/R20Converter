# Introduction

R20Converter is a Windows/Linux/Mac application that does the entire conversion from a Roll20 campaign (exported with [R20Exporter](https://github.com/kakaroto/R20Exporter)) into a [Foundry VTT](http://foundryvtt.com) world.

This tool is currently only available to my [Patreon subscribers](https://patreon.com/kakaroto).

You can see it in action here : https://youtu.be/fngH2te2TJE

This repository is used for keeping track of issues and feature requests.

# R20Converter

This application converts a Roll20 campaign into a Foundry VTT world or module.

It will automate the entire conversion process and all(*) of your campaign will be setup just the way it was in Roll 20

(*) While macros will be converted, they will be sent as chat message only, since inline rolls and other Roll20 specific macros are not supported in Foundry VTT. You also need to be using the OGL character sheet ("D&D 5e by Roll20") or the Shaped Sheet template for conversion of characters to work. **This tool does not convert other character sheets, meaning that non-dnd5e games will have blank character sheets for actors and NPCs (though if a NPC of the same name exists in the system's compendiums, it will be imported from the game system compendium)**.

![image](https://user-images.githubusercontent.com/27990/156877520-f350e333-4fd3-4dc4-9234-298818cf3231.png)

## How to use
Follow the instructions from the demo video to see it in action and how to use it : 

- Quick overview: https://youtu.be/fngH2te2TJE
- Detailed instructions : https://youtu.be/xAPS6NXZ0uM

[![R20Converter 0.9 demo](https://user-images.githubusercontent.com/27990/82268394-dcd11980-993c-11ea-967f-c780814506cd.png)](https://youtu.be/xAPS6NXZ0uM)

### Windows

This package comes with an executable for Windows. Simply open the R20converter.exe application and follow the instructions on screen to select your exported zip and convert it.

### Mac OS X

Open the R20Converter application and follow the instructions.

### Linux

If using Linux, you will need `Python 3.6` or later to use R20Converter.

You can run it with `python3 src/main.py` in a terminal. Use the --help option to see which options are available to you during conversion.

Required dependencies are : `requests`, `pillow`, `python-slugify` and for the GUI `eel`
 
`sudo pip3 install requests pillow python-slugify eel`

If you are running raspbian on a Raspberry Pi, you may also need to run the command `sudo apt-get install libopenjp2-7` to install one of the dependencies.
In order to run the Graphics User Interface, you will also need to have python-tk installed. That one can be installed from your distribution's package manager using `sudo apt install python3-tk` or `sudo dnf install python3-tkinter`.
Installing Google Chrome's browser is also recommended.

If no arguments are provided and the appropriate dependencies are installed, the program will launch in GUI mode.


## Campaign Conversion

To convert a campaign, you first need to have your Roll 20 campaign exported. To do so, use the [R20Exporter](https://github.com/kakaroto/R20Exporter) extension and follow its README instructions on how to use it.

Once you have your campaign exported as a ZIP file or a JSON file, you can start the conversion process. Note that you do not need to extract the campaign's zip file; R20Converter will work directly with the zip file itself to do the conversion.

You need to select your output directory. This should ideally be your existing local Foundry VTT installation. If you do not have Foundry installed locally, you can select any empty directory instead.

## Final steps

When the script is done, your campaign will be converted and available to use in Foundry VTT.

The converted world will automatically enable the [permission_viewer](https://github.com/kakaroto/fvtt-module-permission-viewer) FVTT module in the generated world. It is suggested to have that module installed.

The `permission viewer` FVTT module is helpful for those coming from Roll 20 to see which handouts/character sheets are shared with whom.

If you use D&D Beyond, check out [Beyond20](https://beyond20.here-for-more.info), another project of mine which lets you roll from monster stat blocks and character sheets directly in D&D Beyond and get the result in your VTT application.

If you use [The Forge](https://forge-vtt.com) for hosting your Foundry VTT games, then you can import your world folder using the Import Wizard. 

