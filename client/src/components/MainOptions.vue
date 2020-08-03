<template>
  <div>
    <div v-if="foundryDirectory !== null" class="mb-2">
      Foundry VTT Data directory was found in
      <code>{{foundryDirectory}}</code> and was automatically selected.
    </div>
    <b-form>
      <b-form-group
        label="Destination Directory :"
        label-cols
        label-align="right"
        description="Select the directory where the new world and assets will be created"
      >
        <b-input-group class="mb-3">
          <b-form-input v-model="folder" :state="!!folder"></b-form-input>
          <b-input-group-append>
            <b-button @click="browse">Browse</b-button>
          </b-input-group-append>
        </b-input-group>
      </b-form-group>

      <boolean-option
        label="Convert into a Compendium ?"
        description="A Compendium conversion will create a Foundry module which needs to be enabeld in your existing worlds to access its entities"
        :badge="exportType"
        v-model="exportAsModule"
      />

      <b-form-group
        :label="`${exportType} URL name :`"
        label-align="right"
        label-cols
        :description="`Leave empty to use the suggested name for your ${exportType.toLowerCase()} : ${defaultSlug}`"
      >
        <b-form-input v-model="slug" required :placeholder="defaultSlug"></b-form-input>
      </b-form-group>

      <div v-if="!!folder" class="border border-info mx-5 mb-2">
        Final {{exportType}} path is :
        <code>{{finalPath}}</code>
      </div>

      <b-form-group
        :label="`${exportType} title :`"
        label-cols
        label-align="right"
        :description="`Leave empty to use the suggested title from your campaign : ${defaultTitle}`"
      >
        <b-form-input v-model="title" :placeholder="defaultTitle"></b-form-input>
      </b-form-group>

      <b-form-group :label="`${exportType} Description :`" label-align="right" label-cols>
        <b-form-textarea
          v-model="description"
          placeholder="Enter a description for your campaign..."
          rows="3"
        ></b-form-textarea>
      </b-form-group>

      <b-form-group label="GM Access Key" label-align="right" label-cols>
        <b-form-input v-model="gmPassword"></b-form-input>
      </b-form-group>
      <b-form-group label="Player Access Key" label-align="right" label-cols>
        <b-form-input v-model="playerPassword"></b-form-input>
      </b-form-group>
    </b-form>
  </div>
</template>

<script>
import { mapState } from "vuex";
import BooleanOption from "./BooleanOption.vue";

export default {
  components: {
    BooleanOption
  },
  data() {
    return {
      slug: "",
      title: "",
      description: "",
      gmPassword: "",
      playerPassword: ""
    };
  },
  methods: {
    async browse() {
      this.folder = await eel.ask_folder()();
    },
    async checkDestinationFolder() {
        const exists = await eel.does_folder_exist(this.finalPath)() || await eel.does_file_exist(this.finalPath)();
        if (exists) {
            this.$store.commit('setError', `Final destination folder ${this.finalPath} must not exist.`);
        } else {
            this.$store.commit('setError', null);
        }
    }
  },
  watch: {
      finalPath() {
          this.checkDestinationFolder()
      },
  },
  computed: {
    folder: {
      get() {
        return this.$store.state.folder;
      },
      set(value) {
        this.$store.dispatch("setFolder", value);
      }
    },
    exportAsModule: {
      get() {
        return this.$store.state.options.exportAsModule;
      },
      set(value) {
        this.$store.dispatch("setOption", { exportAsModule: value });
      }
    },
    exportType() {
      return this.exportAsModule ? "Compendium" : "World";
    },
    finalPath() {
      return `${this.folder}/Data/${this.exportAsModule ? "modules" : "worlds"}/${this.slug || this.defaultSlug}`;
    },
    ...mapState(["foundryDirectory", "error"]),
    ...mapState({
      defaultSlug: "slug",
      defaultTitle: "title"
    })
  },
  mounted() {
    this.checkDestinationFolder()
  },
  destroyed() {
    this.$store.dispatch("setOption", {
      slug: this.slug || this.defaultSlug,
      title: this.title || this.defaultTitle,
      description: this.description,
      gmPassword: this.gmPassword,
      playerPassword: this.playerPassword
    });
  }
};
</script>