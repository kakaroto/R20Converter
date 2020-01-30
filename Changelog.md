# Changelog

## v0.8

- Port database format to FVTT 0.4.4/0.4.5
- Convert Roll20 macros into chat macros 
- Restore each user's macro hotbar to match their macrobar on Roll20
- Add support for converting the chat log
- Convert roll templates for the OGL sheet so character sheet rolls from chat will appear as they did on Roll20, including tooltip support
- Enables [Chat Autoloader](https://gitlab.com/moerills-fvtt-modules/chat-autoloader) FVTT module by default (module by @Moerill).
- Fix permissions for actors that are in player's journal to limited instead of observer, to better match the behavior on Roll20
- Add support for horizontal mirroring of tokens
- Add checks against invalid roll tables and decks
- Prevent NPC weapons that match loot item names (such as a shovel or torches that deal 1 damage) from becoming loot and removing their damage values
- Make the 'Auto Doors' option enabled by default in the GUI

## v0.7

- Port Core data to 0.4.x
- Port Actor data to 0.4.x
- Port Item data to 0.4.x
- Port Command line options/behavior and GUI to use 0.4.x data and auto discover of FVTT data path on the system
- Fix some scenes that could have drawings with an invalid author if the player that drew it was deleted from the campaign
- Add support for flipped tiles without needing to use drawings
- Add support for sort order of entities using core feature without the use of entityorder module
- Better support for shaped sheet character conversions
- Add support for lair and regional effects for NPCs
- Nearly rewrote the entire character sheet data migration making it much more stable and reliable and accurate in how character data is converted
- Use rollable table names for multi-sided tokens to name the actor side filenames more accurately
- Add support for roll tables
- Add support for converting decks into Items and associated Roll Tables
- Add option to force all scene backgrounds to be converted into tiles
- Add option to force all token bars (bar 1 or bar 2 or both) to be linked to the actor HP
- Lock all tiles/drawings from the map layer

## v0.6.4

- Fix various small crashes related to character sheets having invalid data

## v0.6.3

- Fix a crash when importing a spell/item from SRD compendiums that are cross linked from a journal entry

## v0.6.2

- Fix a crash when converting with --export-as-module and --no-duplicate-actor-items options together

## v0.6.1

- Fix crash if an Roll 20 item's modifiers is badly formatted
- Fix error in FVTT if a converted character didn't have a class name set.

## v0.6

- Add --folder-as-items option to allow conversion of a handouts folder into items
- Add proper support for drawings, using the FVTT drawings database (Fixes unicode character conversions)
- Add --images-as-drawings option to convert all Roll20 graphics into drawings instead of tiles
- Add support for flipped graphics
- Character items will also be exported as Items in the sidebar for re-use.
- Fix many small issue in how actor items, weapons, traits, feats were getting converted
- Add experimental support for the Shaped Sheet template
- Fix conversion of worlds with unicode characters in their name
- Show conversion errors in the GUI if a crash happens
- Split languages and armor proficiencies if written as a single proficiency in Roll20, separated by commas
- Fix path separator issue in module creation so a module generated on windows will work on a linux system
- Fix a bug where if a scene name starts with '/', it would not write its asset files in the correct path
- Add ability to disable conversion of specific packs when exporting to a module
- Add protection against long file paths so all resources can be accessed on the filesystem
- Convert orphaned handouts which do not show in the journal folder data but appear on the root journal.
- Add character classes to actor conversion
- Add personality traits/bonds/flaws/ideals to the character Bio
- Fix actor's XP, item attacks and damages
- Fix NPC damage mods getting doubled when an attack is considered a weapon (due to FVTT adding the str/dex modifier)
- Fix a character imported from Roll20 compendium having its token emit light by default
- Update to FVTT 0.3.8 database schema 

## v0.5

- Add character apperance/backstory/treasure/allies to the BIO
- Add option to export the campaign as a module
- Add a simple GUI 
- Add --cleanup-scenes option to clean walls/tokens/tiles outside of the map boundaries

## v0.4

- Added actor conversion support
- Split off from R20Exporter
- Update to FVTT 0.3.5 database schema
- Port to Python 3 for better internationalization/unicode support
- Add --json option to parse a campaign.json and download the resources directly
- Fix issue with fonts not loading properly
- Add --walls-around-map option

## v0.3

- Add support for multisided tokens
- Add folder and entity order
- Fix HP bar on tokens

## v0.2

- Add fonts for proper text conversions
- Add minimum wall length and maximum angle options
- Add option to override title
- Add option to disable conversion of archived handouts/actors/scenes

## v0.1

- Initial release
- Support for converting scenes, tokens, journal entries, combat and jukebox entities
- Add internationalization support and Windows support
