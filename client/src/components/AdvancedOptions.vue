<template>
  <div>
    <b-form>
      <div>
        <p>Congratulations, you are done with all the hard questions!</p>
        <p>You can use the options below to fine tune the resulting world, or you can trust in the default selections and start the conversion right away.</p>
      </div>
      <div role="tablist">
        <b-card no-body class="mb-1">
          <b-card-header header-tag="header" class="p-1" role="tab">
            <b-button block v-b-toggle.fine-tune-settings variant="info">Fine Tune Settings</b-button>
          </b-card-header>
          <b-collapse id="fine-tune-settings" accordion="settings-accordion" role="tabpanel">
            <b-card-body>
              <boolean-option
                label="Restrict movement"
                description="Force all the walls to restrict movement, regardless of the page setting in Roll20"
                v-model="form.restrictMovement"
              />

              <b-form-group
                label="Fog of War Exploration"
                label-cols
                label-align="right"
                description="Enable or Disable Fog of War Exploration in all scenes with dynamic layers regardless of the Advanced Fog of War setting in Roll20"
              >
                <b-form-select v-model="form.fog" :options="fogOptions"></b-form-select>
              </b-form-group>

              <boolean-option
                label="Set HP for token Bar 1"
                description="Force Bar 1 of all tokens to represent the character's HP attribute"
                v-model="form.forceHpForTokenBar1"
              />

              <boolean-option
                label="Set HP for token Bar 2"
                description="Force Bar 2 of all tokens to represent the character's HP attribute"
                v-model="form.forceHpForTokenBar2"
              />
              <boolean-option
                label="Add walls around the map"
                description="Add 4 walls to enclose the map and cut off view/movement to the side table"
                v-model="form.addWallsAroundMap"
              />
              <boolean-option
                label="Clean up the scenes"
                description="Remove any tiles, tokens or walls that are outside of a scene's boundary"
                v-model="form.cleanupScenes"
              />
              <boolean-option
                label="Don't convert chat history"
                description="Disable converting the chat and leave the chat log empty"
                v-model="form.dontConvertChat"
              />
              <boolean-option
                label="Automatically detect doors from walls"
                description="Automatically detect which walls represent doors or secret doors based on the occurence of that wall's color in the dynamic layer"
                v-model="form.autoDoors"
              />
              <b-form-group
                label="Custom Door Color"
                label-cols
                label-align="right"
                description="Sets the exact color string of the dynamic lighting walls to convert into doors. For example, set it to '#ff0000' to consider Red walls as doors."
                :disabled="form.autoDoors"
              >
                <b-form-input v-model="form.doorColor" placeholder="#ff0000"></b-form-input>
              </b-form-group>
              <b-form-group
                label="Custom Secret Door Color"
                label-cols
                label-align="right"
                description="Sets the exact color string of the dynamic lighting walls to convert into secret doors."
                :disabled="form.autoDoors"
              >
                <b-form-input v-model="form.secretDoorColor" placeholder="#0000ff"></b-form-input>
              </b-form-group>

              <b-form-group label="Minimum Wall Length" label-cols label-align="right">
                <template v-slot:description>
                  <p>Minimum distance for walls (in pixels).</p>
                  <p></p>
                  <p>If a wall is smaller and part of a longer chain of walls, it will get merged with the adjacent wall.</p>
                  <p>This is useful if there are a lot of small/jagged walls or freehand-drawn walls such as in large caves (Set to 0 to disable it)</p>
                </template>
                <b-form-spinbutton v-model="form.minimumWallLength" min="0" max="70"></b-form-spinbutton>
              </b-form-group>

              <b-form-group label="Maximum Wall Angle" label-cols label-align="right">
                <template v-slot:description>
                  <p>Maximum angle (in degrees) between walls before they are merged (when above option is used).</p>
                  <p>This is to prevent small walls at high angles (a small triangle or U shape) from being merged and becoming a line that cuts through the map.</p>
                  <p>The angle is calculated with every point in the wall that is skipped, so a circle drawn with small lines and small angles will not be removed.</p>
                  <p>Note that the angle here is related to a straight line, so a maximum angle of 30 means an angle between 150 and 210 degrees between the 3 points.</p>
                </template>
                <b-form-spinbutton v-model="form.maximumWallAngle" min="0" max="90"></b-form-spinbutton>
              </b-form-group>

              <b-form-group
                label="Export Folder contents as Loot Items"
                label-cols
                label-align="right"
                description="Converts each entry in a journal folder into items. Useful for 'Magic Items' folders."
              >
                <b-form-select
                  v-model="selectedFolderAsItems"
                  :options="form.folderAsItems"
                  :select-size="4"
                ></b-form-select>
                <div>
                  <b-button class="m-2" v-b-modal.add-folder-as-items>Add Folder</b-button>
                  <b-button
                    class="m-2"
                    @click="removeFolderAsItem"
                    :disabled="!selectedFolderAsItems"
                  >Remove selection</b-button>
                </div>
                <b-modal
                  title="Export folder contents as Items"
                  id="add-folder-as-items"
                  @ok="addFolderAsItem"
                  @hide="folderItemsNameToAdd = ''"
                >
                  Enter the name of the folder you want to export all of its handouts into Items
                  <b-form-input v-model="folderItemsNameToAdd"></b-form-input>
                </b-modal>
              </b-form-group>
            </b-card-body>
          </b-collapse>
        </b-card>

        <b-card no-body class="mb-1">
          <b-card-header header-tag="header" class="p-1" role="tab">
            <b-button block v-b-toggle.advanced-settings variant="info">Advanced Settings</b-button>
          </b-card-header>
          <b-collapse id="advanced-settings" accordion="settings-accordion" role="tabpanel">
            <b-card-body>
              <b-form-group
                label="NPC Source"
                label-cols
                label-align="right"
                description="Source reference for NPC actors (displayed in the character sheet)"
              >
                <b-form-input v-model="form.npcSource"></b-form-input>
              </b-form-group>
              <boolean-option
                label="Export actor items into individual item entities"
                description="Items from actors will be exported as individual Entity Items."
                v-model="form.exportActorItems"
              />
              <boolean-option
                label="Don't create duplicate actor items"
                description="This option causes items with the same name from different actors to be exported under a single item. The first processed actor with the item of that name gets their item in the item entities (remember that a Dragon's Bite attack is not the same as a spider's Bite attack)."
                v-model="form.noDuplicateActorItems"
              />
              <boolean-option
                label="Trust FVTT Compendiums more than Roll20 sheet data"
                description="If enabled, items, feats and spells found in the Game System's Compendiums will not be overwritten with custom description/damage/etc.. from the Roll20 data."
                v-model="form.noCompendiumOverwrite"
              />
              <boolean-option
                label="Set all backgrounds as tiles"
                description="Sets all page map images as tiles rather than setting them as the scene's background"
                v-model="form.allBackgroundsAsTiles"
              />
              <boolean-option
                label="Don't use an Archived folder"
                description="Disable the automatic move of archived scenes/handouts/characters to an Archived folder."
                v-model="form.disableArchived"
                v-if="!exportAsModule"
              />
              <boolean-option
                label="Disable Journal Conversion"
                description="Disable conversion of Journal entries in the compendium module"
                v-model="form.disableModuleJournal"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Disable Actors Conversion"
                description="Disable conversion of Actor entries in the compendium module"
                v-model="form.disableModuleActors"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Disable Scenes Conversion"
                description="Disable conversion of Scenes entries in the compendium module"
                v-model="form.disableModuleScenes"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Disable Playlists Conversion"
                description="Disable conversion of Playlists entries in the compendium module"
                v-model="form.disableModulePlaylists"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Disable Tables Conversion"
                description="Disable conversion of Tables entries in the compendium module"
                v-model="form.disableModuleTables"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Disable Decks Conversion"
                description="Disable conversion of Decks entries in the compendium module"
                v-model="form.disableModuleDecks"
                v-if="exportAsModule"
              />
              <boolean-option
                label="Use original image URLs for path"
                description="Do not copy images to the world folder but use the original Roll20 URL instead. (NOT recommended due to CORS issues and image resolution paths)"
                v-model="form.useOriginalImageUrls"
              />
            </b-card-body>
          </b-collapse>
        </b-card>
      </div>
    </b-form>
  </div>
</template>

<script>
import BooleanOption from "./BooleanOption.vue";

export default {
  components: {
    BooleanOption
  },
  data() {
    return {
      form: {
        restrictMovement: true,
        forceHpForTokenBar1: true,
        forceHpForTokenBar2: false,
        addWallsAroundMap: true,
        cleanupScenes: true,
        autoDoors: true,
        dontConvertChat: false,
        fog: "enable",

        doorColor: "",
        secretDoorColor: "",
        disableArchived: false,
        allBackgroundsAsTiles: false,
        minimumWallLength: 0,
        maximumWallAngle: 30,
        npcSource: "Roll 20",
        noCompendiumOverwrite: false,
        disableModuleJournal: false,
        disableModuleActors: false,
        disableModuleScenes: false,
        disableModulePlaylists: false,
        disableModuleTables: false,
        disableModuleDecks: false,
        folderAsItems: ["Magic Items"],
        exportActorItems: false,
        noDuplicateActorItems: false,
        useOriginalImageUrls: false
      },
      fogOptions: [
        { value: "", text: "Keep Roll20 settings" },
        { value: "enable", text: "Enable Fog of War" },
        { value: "disable", text: "Disable Fog of War" }
      ],
      selectedFolderAsItems: "",
      folderItemsNameToAdd: ""
    };
  },
  computed: {
    exportAsModule() {
      return this.$store.state.options.exportAsModule;
    }
  },
  methods: {
    addFolderAsItem() {
      if (!this.folderItemsNameToAdd) return;
      this.form.folderAsItems.push(this.folderItemsNameToAdd);
    },
    removeFolderAsItem() {
      this.form.folderAsItems = this.form.folderAsItems.filter(
        f => f !== this.selectedFolderAsItems
      );
      this.selectedFolderAsItems = "";
    }
  },
  destroyed() {
    this.$store.dispatch("setOption", {
      restrictMovement: this.form.restrictMovement,
      forceHpForTokenBar1: this.form.forceHpForTokenBar1,
      forceHpForTokenBar2: this.form.forceHpForTokenBar2,
      addWallsAroundMap: this.form.addWallsAroundMap,
      cleanupScenes: this.form.cleanupScenes,
      autoDoors: this.form.autoDoors,
      dontConvertChat: this.form.dontConvertChat,

      // Advanced Options
      enableFog: this.form.fog === "enable",
      disableFog: this.form.fog === "disable",
      doorColor: this.form.doorColor || null,
      secretDoorColor: this.form.secretDoorColor || null,
      disableArchived: this.form.disableArchived,
      allBackgroundsAsTiles: this.form.allBackgroundsAsTiles,
      minimumWallLength: this.form.minimumWallLength,
      maximumWallAngle: this.form.maximumWallAngle,
      npcSource: this.form.npcSource,
      noCompendiumOverwrite: this.form.noCompendiumOverwrite,
      disableModuleJournal: this.form.disableModuleJournal,
      disableModuleActors: this.form.disableModuleActors,
      disableModuleScenes: this.form.disableModuleScenes,
      disableModulePlaylists: this.form.disableModulePlaylists,
      disableModuleTables: this.form.disableModuleTables,
      disableModuleDecks: this.form.disableModuleDecks,
      folderAsItems: this.form.folderAsItems,
      dontExportActorItems: !this.form.exportActorItems, // Use inverse of option for the UI
      noDuplicateActorItems: this.form.noDuplicateActorItems,
      useOriginalImageUrls: this.form.useOriginalImageUrls
    });
  }
};
</script>