# R20Converter

This application converts a Roll20 campaign into a Foundry VTT world or module.

It will automate the entire conversion process and most(*) of your campaign will be setup just the way it was in Roll 20

(*) Your chat log will not be converted (yet) and things such as decks, tables and macros will not be converted either as those features are not yet available in Foundry VTT. You also need to be using the OGL character sheet ("D&D 5e by Roll20") though partial support for the Shaped sheet is available. 

## How to use

### Windows

This package comes with an executable for Windows in the `windows` subdirectory. Simply double click it to open the User Interface, then Browse for the ZIP file that was exported and for the public directory of your FVTT installation (you can also just direct it to the FVTT installation directory itself and it will adjust the path automatically) then enter a name for your world directory.

Select the options you would like to use, then press the "Convert Campaign" button. You can always keep your mouse still on one of the options to see a tooltip with more information on what each option does.


### Linux

If using Linux, you can run it with `python3 src/R20Converter.py` in a terminal. Use the --help option to see which options are available to you during conversion.

Dependencies for the GUI, you need to install `pysimplegui`, `pysimpleguiqt` and `pyside2`.

`pip3 install requests pysimplegui pysimpleguiqt pyside2`


## Campaign Conversion

To convert a campaign, you first need to have your Roll 20 campaign exported. To do so, use the [R20Exporter](https://github.com/kakaroto/R20Exporter) script and follow its README instructions on how to use it.

Once you have your campaign exported as a zip file, you can start the conversion process. Note that you do not need to extract the campaign's zip file; R20Converter will work directly with the zip file itself to do the conversion.

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
./src/R20Converter.py "C:\FVTT\resources\app\public\worlds\CoS" "C:\Downloads\Curse of Strahd.zip" --door-color #ff0000 --enable-fog --restrict-movement --gm-password "strahd-is-my-hero" --player-password "prepare-to-die"
```

In the above example, the script (which is run on linux) will convert the "Curse of Strahd.zip" campaign (from the C:\Downloads directory) into the directory "CoS" (in the FVTT worlds directory) and will automatically replace all walls from the dynamic lighting layer which are red (RGB color #ff0000) into doors, will enable Exploration Fog on all maps, make all walls restrict movement (even if the page settings in Roll20 did not have the "restrict movement" option enabled) and will set the GM and player passwords to the values provided.

Finally, here's a more complex command which uses many of the available options

```
windows\R20Converter.exe "STSS" "Stranger Things.zip" --campaign-title "Stranger Things Starter Set" --description "Get your fireballs ready as you investigate the mysterious castle and battle the ferocious Demogorgon. Prepare for just about anything, because the game just got stranger" --auto-doors --enable-fog --restrict-movement --npc-source "PHB" --minimum-wall-length 35 --maximum-wall-angle 30 --fvtt-public-path "C:\FVTT\resources\app\public" --add-walls-around-map --cleanup-scenes
```

In this last example, we convert the "Stranger Things.zip" file into the STSS directory, we set the campaign title to "Stranger Things Starter Set", replace the default world description, ask the script to automatically detect doors and secret doors from the dynamic lighting walls, and make sure that small walls get removed if they are less than 35 pixels long, are contiguous to other walls and don't have an angle of over 30 degrees with the neighboring walls (this can be very useful in dropping the number of walls in cave-like maps where the Roll20 team made thousands of walls instead of a few hundred). Finally we give it the path to the FVTT public directory so it can auto-import spells, items and class features, we ask for walls to be added around each map and for any elements (tiles, walls, tokens) that are outside the bounds of the map to be removed.

## Full options

If you run the application with the `--help` option, you will get the full list of available options to you. For convenience, here is the usage of the program : 
```
usage: R20Converter.py [-h] [--json] [--export-as-module]
                       [--campaign-title CAMPAIGN_TITLE]
                       [--description DESCRIPTION] [--gm-password GM_PASSWORD]
                       [--player-password PLAYER_PASSWORD]
                       [--restrict-movement] [--add-walls-around-map]
                       [--enable-fog] [--disable-fog] [--cleanup-scenes]
                       [--interactive] [--auto-doors]
                       [--door-color DOOR_COLOR]
                       [--secret-door-color SECRET_DOOR_COLOR]
                       [--disable-archived]
                       [--minimum-wall-length MINIMUM_WALL_LENGTH]
                       [--maximum-wall-angle MAXIMUM_WALL_ANGLE]
                       [--debug-page DEBUG_PAGE]
                       [--fvtt-public-path FVTT_PUBLIC_PATH]
                       [--npc-source NPC_SOURCE] [--no-compendium-overwrite]
                       [--images-as-drawings] [--disable-module-journal]
                       [--disable-module-actors] [--disable-module-scenes]
                       [--disable-module-playlists]
                       [--folder-as-items FOLDER_AS_ITEMS]
                       [--dont-export-actor-items]
                       [--no-duplicate-actor-items]
                       [--use-original-image-urls] [--max-path MAX_PATH]
                       destination-directory exported.zip

R20Converter v0.6

positional arguments:
  destination-directory
                        The destination directory in public/worlds/ or
                        public/modules/
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
  --fvtt-public-path FVTT_PUBLIC_PATH
                        Path to the FVTT public directory (used for importing
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

## Final steps

When the script is done, if you hadn't converted the campaign into the appropriate folder (`worlds` or `modules`) of your FVTT public directory, then copy the generated directory to the resources/app/public/worlds directory in your FVTT installation and load the world in FVTT. 

And you're done!

The converted world will automatically enable the [entityorder](https://github.com/kakaroto/fvtt-module-entityorder), [permission_viewer](https://github.com/kakaroto/fvtt-module-permission-viewer) and [Furnace](https://github.com/kakaroto/fvtt-module-furnace) FVTT modules in the generated world. The `entityorder` FVTT module is required in order to see the journals appearing in the correct order while the Furnace module is only really required if you use the `--images-as-drawings` option. 

If you use D&D Beyond, check out [Beyond20](https://beyond20.here-for-more.info), another project of mine which lets you roll from monster stat blocks and character sheets directly in D&D Beyond and get the result in your VTT application.