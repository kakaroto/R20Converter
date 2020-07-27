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
        :description="`Leave empty to use the suggested name for your ${exportType.toLowerCase()} : ${slug}`"
      >
        <b-form-input v-model="form.slug" required :placeholder="slug"></b-form-input>
      </b-form-group>

      <b-form-group
        :label="`${exportType} title :`"
        label-cols
        label-align="right"
        :description="`Leave empty to use the suggested title from your campaign : ${title}`"
      >
        <b-form-input v-model="form.title" :placeholder="title"></b-form-input>
      </b-form-group>

      <b-form-group :label="`${exportType} Description :`" label-align="right" label-cols>
        <b-form-textarea
          v-model="form.description"
          placeholder="Enter a description for your campaign..."
          rows="3"
        ></b-form-textarea>
      </b-form-group>

      <b-form-group label="GM Access Key" label-align="right" label-cols>
        <b-form-input v-model="form.gmPassword"></b-form-input>
      </b-form-group>
      <b-form-group label="Player Access Key" label-align="right" label-cols>
        <b-form-input v-model="form.playerPassword"></b-form-input>
      </b-form-group>
    </b-form>
    <r20-footer>
        <b-button @click="$emit('previous')" class="mr-3">Back</b-button>
        <b-button @click="next()" :disabled="Boolean(error || !folder)" variant="info">Next Step</b-button>
    </r20-footer>
  </div>
</template>

<script>
import { mapState } from "vuex";
import BooleanOption from "./BooleanOption.vue";
import R20Footer from "./R20Footer.vue";

export default {
  components: {
    BooleanOption,
    R20Footer
  },
  data() {
    return {
      form: {
        slug: "",
        title: "",
        description: "",
        gmPassword: "",
        playerPassword: ""
      }
    };
  },
  methods: {
    async browse() {
      this.folder = await eel.ask_folder()();
    },
    async next() {
      this.$store.dispatch("setOption", {
        slug: this.form.slug || this.slug,
        title: this.form.title || this.title,
        description: this.form.description,
        gmPassword: this.form.gmPassword,
        playerPassword: this.form.playerPassword
      });
      this.$emit("next");
    }
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
    ...mapState(["title", "slug", "foundryDirectory", "error"])
  }
};
</script>