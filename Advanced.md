
Here is some advanced information which has mostly all become irrelevant with the addition of the new GUI.


## Command line use

If using the command line interface, to start the conversion, run the R20Converter application giving it two arguments (in this order) : the world directory to create, and the zip file. 

Don't forget that the directory name needs to be url-friendly, so don't use spaces (see [http://foundryvtt.com/pages/hosting.html#where-do-i-put-my-content](http://foundryvtt.com/pages/hosting.html#where-do-i-put-my-content)). Also note that image paths are dependent on the world directory name, so you cannot rename the directory after the conversion is done.

## Examples

Using the new graphical user interface, these examples have become irrelevant, but for those who want to use the command line interface, here are some examples of use that can be useful. Note that the command line interface does have a few small extra options which are not availabel through the graphical user interface.

Here's the simplest example to convert the campaign from the file "The Lost Mine of Phandelver.zip" into the world directory "lmop"

```
windows\R20Converter.exe "lmop" "The Lost Mine of Phandelver.zip"
```

Here's another example with a bit more options given to it in order to fine tune the converted result.

```
./src/R20Converter.py "C:\FVTT\Data\worlds\CoS" "C:\Downloads\Curse of Strahd.zip" --door-color #ff0000 --enable-fog --restrict-movement --gm-password "strahd-is-my-hero" --player-password "prepare-to-die"
```

In the above example, the script (which is run on linux) will convert the "Curse of Strahd.zip" campaign (from the C:\Downloads directory) into the directory "CoS" (in the FVTT worlds directory) and will automatically replace all walls from the dynamic lighting layer which are red (RGB color #ff0000) into doors, will enable Exploration Fog on all maps, make all walls restrict movement (even if the page settings in Roll20 did not have the "restrict movement" option enabled) and will set the GM and player passwords to the values provided.

Finally, here's a more complex command which uses many of the available options

```
windows\R20Converter.exe "STSS" "Stranger Things.zip" --campaign-title "Stranger Things Starter Set" --description "Get your fireballs ready as you investigate the mysterious castle and battle the ferocious Demogorgon. Prepare for just about anything, because the game just got stranger" --auto-doors --enable-fog --restrict-movement --npc-source "PHB" --minimum-wall-length 35 --maximum-wall-angle 30 --fvtt-data-path "C:\FVTT\Data" --add-walls-around-map --cleanup-scenes
```

In this last example, we convert the "Stranger Things.zip" file into the STSS directory, we set the campaign title to "Stranger Things Starter Set", replace the default world description, ask the script to automatically detect doors and secret doors from the dynamic lighting walls, and make sure that small walls get removed if they are less than 35 pixels long, are contiguous to other walls and don't have an angle of over 30 degrees with the neighboring walls (this can be very useful in dropping the number of walls in cave-like maps where the Roll20 team made thousands of walls instead of a few hundred). Finally we give it the path to the FVTT Data directory so it can auto-import spells, items and class features, we ask for walls to be added around each map and for any elements (tiles, walls, tokens) that are outside the bounds of the map to be removed.

## Full options

If you run the application with the `--help` option, you will get the full list of available options to you. For convenience, here is the usage of the program : 
```
usage: R20Converter.py [-h] [--json] [--export-as-module]
                       [--campaign-title CAMPAIGN_TITLE]
                       [--description DESCRIPTION] [--gm-password GM_PASSWORD]
                       [--player-password PLAYER_PASSWORD]
                       [--restrict-movement] [--force-hp-for-token-bar1]
                       [--force-hp-for-token-bar2] [--add-walls-around-map]
                       [--enable-fog] [--disable-fog] [--cleanup-scenes]
                       [--interactive] [--auto-doors]
                       [--door-color DOOR_COLOR]
                       [--secret-door-color SECRET_DOOR_COLOR]
                       [--disable-archived] [--all-backgrounds-as-tiles]
                       [--minimum-wall-length MINIMUM_WALL_LENGTH]
                       [--maximum-wall-angle MAXIMUM_WALL_ANGLE]
                       [--debug-page DEBUG_PAGE]
                       [--fvtt-data-path FVTT_DATA_PATH]
                       [--npc-source NPC_SOURCE] [--no-compendium-overwrite]
                       [--images-as-drawings] [--disable-module-journal]
                       [--disable-module-actors] [--disable-module-scenes]
                       [--disable-module-playlists] [--disable-module-tables]
                       [--disable-module-decks] [--dont-convert-chat]
                       [--folder-as-items FOLDER_AS_ITEMS]
                       [--dont-export-actor-items]
                       [--no-duplicate-actor-items]
                       [--use-original-image-urls] [--max-path MAX_PATH]
                       destination-directory exported.zip

R20Converter v0.8

positional arguments:
  destination-directory
                        The destination directory in Data/worlds/ or
                        Data/modules/
  exported.zip          The exported ZIP file from R20Exporter

optional arguments:
  -h, --help            show this help message and exit
  --json                Use campaign.json as input instead of a ZIP file
                        (playlist will be empty due to audio tracks being
                        accessible only when logged into Roll20)
  --export-as-module    Export the campaign as a module (instead of a world)
                        with Compendium packs for all
                        handouts/characters/scenes/playlists
  --campaign-title CAMPAIGN_TITLE
                        Override the Campaign title
  --description DESCRIPTION
                        World Desription
  --gm-password GM_PASSWORD
                        Default GM password
  --player-password PLAYER_PASSWORD
                        Default player password
  --restrict-movement   Force all walls to restrict movement
  --force-hp-for-token-bar1
                        Forces the use of HP attribute for all tokens' first
                        bar
  --force-hp-for-token-bar2
                        Forces the use of HP attribute for all tokens' second
                        bar
  --add-walls-around-map
                        Add 4 walls to enclose the map and cut off
                        view/movement to the side table
  --enable-fog          Enable Fog Exploration on all Scenes with Dynamic
                        Lighting regardless of Advanced Fog of War setting
  --disable-fog         Disable Fog Exploration on all Scenes with Dynamic
                        Lighting regardless of Advanced Fog of War setting
  --cleanup-scenes      Remove any tiles, tokens or walls that are outside of
                        a scene's boundary
  --interactive         Ask questions about decisions to be made during the
                        conversion process.
  --auto-doors          Automatically detect doors and set them as such.
  --door-color DOOR_COLOR
                        Sets the color of the dynamic lighting walls to
                        convert into doors. For example, set it to '#ff0000'
                        for Red walls.
  --secret-door-color SECRET_DOOR_COLOR
                        Sets the color of the dynamic lighting walls to
                        convert into secret doors
  --disable-archived    Disable the automatic move of archived
                        scenes/handouts/characters to an Archived folder.
  --all-backgrounds-as-tiles
                        Set all page backgrounds as tiles.
  --minimum-wall-length MINIMUM_WALL_LENGTH
                        Minimum distance for walls (in pixels). If a wall is
                        smaller and part of a longer chain of walls, it will
                        get merged with the adjacent wall. This is useful if
                        there are a lot of small/jagged walls or freehand-
                        drawn walls (Default: 0 (disabled))
  --maximum-wall-angle MAXIMUM_WALL_ANGLE
                        Maximum angle (in degrees) between walls before they
                        are merged (when using --minimum-wall-distance
                        option). This is to prevent small walls at high angles
                        (a small triangle or U shape) from being merged and
                        becoming a line that cuts through the map. The angle
                        is calculated with every point in the wall that is
                        skipped, so a circle drawn with small lines and small
                        angles will not be removed. Note that the angle here
                        is related to a straight line, so a maximum angle of
                        30 means an angle between 150 and 210 degrees between
                        the 3 points (Default: 30)
  --debug-page DEBUG_PAGE
                        Only convert a specific page. Useful for debugging
  --fvtt-data-path FVTT_DATA_PATH
                        Path to the FVTT Data directory (used for importing
                        items and spells from dnd5e system)
  --npc-source NPC_SOURCE
                        Source reference for NPC actors (displayed in the
                        character sheet)
  --no-compendium-overwrite
                        If enabled, items, feats and spells found in the
                        Compendium will not be overwritten with custom
                        description/damage/etc.. from the Roll20 data
  --images-as-drawings  Set all images on the scene as textured drawings
                        instead of tiles (requires Furnace to function
                        properly)
  --disable-module-journal
                        Disable conversion of Journal entries in the module
                        (requires --export-as-module)
  --disable-module-actors
                        Disable conversion of Actors in the module (requires
                        --export-as-module)
  --disable-module-scenes
                        Disable conversion of Scenes in the module (requires
                        --export-as-module)
  --disable-module-playlists
                        Disable conversion of Playlists in the module
                        (requires --export-as-module)
  --disable-module-tables
                        Disable conversion of rollable tables in the module
                        (requires --export-as-module)
  --disable-module-decks
                        Disable conversion of card decks in the module
                        (requires --export-as-module)
  --dont-convert-chat   Disable converting the chat and leave the chat log
                        empty
  --folder-as-items FOLDER_AS_ITEMS
                        Converts each entry in a journal folder into items.
                        Useful for 'Magic Items' folders. Can be passed
                        multiple times to convert more than one folder.
  --dont-export-actor-items
                        Items from actors will be exported as individual
                        Entity Items. This option disables that behavior and
                        no items will be created.
  --no-duplicate-actor-items
                        This option causes items with the same name from
                        different actors to be exported under a single item.
                        The first processed actor with the item of that name
                        gets their item in the item entities.
  --use-original-image-urls
                        Do not copy images to the world folder but use Roll20
                        URL instead. (NOT recommended)
  --max-path MAX_PATH   Set the maximum allowed length for the asset's
                        absolute file paths. Most File Systems will have a
                        limit of 256 characters, but you can set it to lower
                        (or higher) if you plan on moving the worlds directory
                        to a different FVTT path. Files that don't fit will be
                        written in an 'assets' directory instead of the usual
                        hierarchy.

Convert Roll20 campaigns into Foundry VTT worlds or modules.
```


# Build instructions

## Windows
- Install Python 3.8 32 bits (see path set in `build_windows.bat`)
- Run `pip install requests pillow python-slugify eel cx_freeze`
- Download the Electron app from https://github.com/electron/electron/releases and extract under the directory `electron`
- Run `build_windows.bat`

## Mac OS X
- Install python using pyenv (official one doesn't work)
- Kill yourself
- Resurect
- Uninstall python from pyenv and reinstall it by recompiling it with tcl-tk compilation flags : https://stackoverflow.com/questions/60469202/unable-to-install-tkinter-with-pyenv-pythons-on-macos
- Wait! Add `--enable-framework` to the configure flags for python and recompile it again
- No, wait! that still doesn't work, forget all that and just install the official python 3.8 which is the only one that works with wxPython: https://www.python.org/downloads/mac-osx/
- `pip install requests pillow python-slugify`
- Install the custom `eel` package in your pyenv with `pip install -U git+https://github.com/kakaroto/Eel.git@master`
- Install the custom `cx_Freeze` package with `pip install -U git+https://github.com/marcelotduarte/cx_Freeze.git@master`
- Realize you need to recompile gevent too, so... : `pip install -I --no-binary :all: gevent`
- Download the Electron app from https://github.com/electron/electron/releases
- Use `cp -R` and not `cp -r` otherwise symlinks get dereferenced, and your 120MB Electron.app becomes 550MB
- Curse at your computer and at those who use Macs
- Go to system settings, security, privacy, automation, and allow Terminal to send events to Finder
- Run `npm run build` in the client subdirectory
- Run `rm -rf build && python setup.py bdist_mac`
- run `codesign --remove-signature build/*.app/Content/MacOS/Python`
- Run `python setup.py bdist_dmg`
- Breathe really hard and unclench your fists then don't look back