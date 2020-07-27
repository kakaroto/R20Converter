<template>
  <div id="app">
    <Header :version="version" />
    <b-card class="mb-1">
        <file-select v-if="step === 0" @next="step++" />
        <main-options v-else-if="step === 1"
            @next="step++" @previous="step--" />
        <advanced-options v-else-if="step === 2" @next="step++" @previous="step--" />
        <output-window v-else />
    </b-card>
  </div>
</template>

<script>
import Header from "./components/Header.vue";
import MainOptions from "./components/MainOptions.vue";
import AdvancedOptions from "./components/AdvancedOptions.vue";
import FileSelect from "./components/FileSelect.vue";
import OutputWindow from "./components/OutputWindow.vue";

import { mapState } from 'vuex'

export default {
  name: "App",
  components: {
    Header,
    MainOptions,
    AdvancedOptions,
    FileSelect,
    OutputWindow
  },
  data() {
    return {
      version: "",
      foundryDirectory: null,
      step: 0
    };
  },
  computed: {
      ...mapState(["error"])
  },
  methods: {
  },
  async created() {
    this.version = await eel.getVersion()();
    const dir = await eel.getFoundryDirectory()()
    this.$store.commit('setFoundryDirectory', dir);
    if (dir)
        this.$store.dispatch('setFolder', dir);
  }
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
