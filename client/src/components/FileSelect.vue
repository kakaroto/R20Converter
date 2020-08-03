<template>
  <div>
    <div>
      Please select the file you exported with
      <a
        href="https://github.com/kakaroto/R20Exporter"
        target="_blank"
      >R20Exporter</a>.
    </div>
    <b-form-group
      label="Exported campaign file :"
      label-for="filename"
      label-cols
      label-align="right"
      description="Select the ZIP file or JSON file export of your Roll20 campaign."
      class="m-3"
    >
      <b-input-group class="mb-3">
        <b-form-input v-model="file" :state="validFile"></b-form-input>
        <b-input-group-append>
          <b-button @click="browse">Browse</b-button>
        </b-input-group-append>
      </b-input-group>
    </b-form-group>
    <div v-if="validFile">You have selected a {{fileType}} file.</div>
    <div v-else>Please select a valid file to continue</div>
  </div>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  data() {
    return {};
  },
  computed: {
    file: {
      get() {
        return this.$store.state.file;
      },
      set(value) {
        this.$store.dispatch("setFile", value);
      }
    },
    validFile() {
      return !!this.fileType;
    },
    ...mapGetters(["fileType"])
  },
  methods: {
    async browse() {
      this.file = await eel.ask_file()();
    }
  }
};
</script>