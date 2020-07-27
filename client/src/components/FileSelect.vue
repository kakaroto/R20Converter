<template>
  <div>
    <div>
      Please select the file you exported with
      <a
        href="https://github.com/kakaroto/R20Exporter"
        target="_blank"
      >R20Exporter</a>.
      You can either select the ZIP exported file or the JSON exported file.
    </div>
    <b-form-group
      label="Exported campaign file (ZIP or JSON) :"
      label-for="filename"
      label-cols
      description
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
    <r20-footer>
      <b-button @click="$emit('next')" :disabled="!validFile" variant="info">Next Step</b-button>
    </r20-footer>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
import R20Footer from "./R20Footer.vue";

export default {
  components: {
    R20Footer
  },
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