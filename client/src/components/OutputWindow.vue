<template>
  <div class="h-100">
    <h2>Converting campaign {{ title }}</h2>

    <b-form-textarea ref="log" v-model="log" no-resize readonly rows="10"></b-form-textarea>
    
    <b-modal :visible="conversionDone" :title="modalTitle" ok-only>
        <span v-html="message"></span>
    </b-modal>
  </div>
</template>

<script>
import { mapState } from "vuex";

export default {
  data() {
      return {
          message: "",
          log: ""
      }
  },
  watch: {
      debugLog(value) {
          const textarea = this.$refs.log.$el;
          const autoScroll = textarea.scrollTop + textarea.clientHeight + 25 >= textarea.scrollHeight;
          console.log("Updated log : ", textarea.scrollTop, textarea.clientHeight, Math.ceil(textarea.scrollTop + textarea.clientHeight), textarea.scrollHeight, autoScroll);
          this.log = value;
          if (autoScroll)
            textarea.scrollTop = textarea.scrollHeight;
      }
  },
  computed: {
    ...mapState(["title", "debugLog", "conversionDone", "conversionError"]),
    modalTitle() {
        if (this.conversionError)
            return "Error converting campaign"
        else
            return "Conversion completed!"
    }
  },
  methods: {
    async startConversion() {
      const state = this.$store.state;
      const getters = this.$store.getters;
      const opt = state.options;
      const args = {
        path: getters.outputPath,
        zip_file: state.file,
        json: getters.fileType === "JSON",
        export_as_module: opt.exportAsModule,
        campaign_title: opt.title,
        description: opt.description,

        game_system: opt.gameSystem,
        gm_password: opt.gmPassword,
        player_password: opt.playerPassword,
        restrict_movement: opt.restrictMovement,
        force_hp_for_token_bar1: opt.forceHpForTokenBar1,
        force_hp_for_token_bar2: opt.forceHpForTokenBar2,
        scene_padding: opt.scenePadding,
        add_walls_around_map: opt.addWallsAroundMap,
        enable_fog: opt.enableFog,
        disable_fog: opt.disableFog,
        cleanup_scenes: opt.cleanupScenes,
        auto_doors: opt.autoDoors,
        door_color: opt.doorColor,
        secret_door_color: opt.secretDoorColor,
        disable_archived: opt.disableArchived,
        all_backgrounds_as_tiles: opt.allBackgroundsAsTiles,
        minimum_wall_length: opt.minimumWallLength,
        maximum_wall_angle: opt.maximumWallAngle,
        npc_source: opt.npcSource,
        no_compendium_overwrite: opt.noCompendiumOverwrite,
        disable_module_journal: opt.disableModuleJournal,
        disable_module_actors: opt.disableModuleActors,
        disable_module_scenes: opt.disableModuleScenes,
        disable_module_playlists: opt.disableModulePlaylists,
        disable_module_tables: opt.disableModuleTables,
        disable_module_decks: opt.disableModuleDecks,
        dont_convert_chat: opt.dontConvertChat,
        folder_as_items: opt.folderAsItems,
        dont_export_actor_items: opt.dontExportActorItems,
        no_duplicate_actor_items: opt.noDuplicateActorItems,
        use_original_image_urls: opt.useOriginalImageUrls,
        interactive: false,
        debug_page: null,
        images_as_drawings: false,
        fvtt_data_path: null,
        max_path: 255,
        overwrite: false
      };
      const result = await eel.startConversion(args)();
      this.message = result.message.replace(/\n/g, "<br/>");
      this.$store.commit("conversionError", result.error);
      this.$store.commit("conversionDone",  true);
    }
  },
  async mounted() {
    console.log("Just got mounted with options : ", this.$store.state.options);
    this.startConversion();
  }
};
</script>