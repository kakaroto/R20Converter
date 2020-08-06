<template>
  <div id="app">
    <r20-Header :version="version" />
    <b-card class="mb-1 overflow-hidden">
      <transition :enter-active-class="animateEnter" :leave-active-class="animateExit">
        <file-select v-if="step === 0" @next="next" />
        <main-options v-else-if="step === 1" @next="next" @previous="previous" />
        <advanced-options v-else-if="step === 2" @next="next" @previous="previous" />
        <output-window v-else />
      </transition>
    </b-card>
    <r20-footer>
      <b-button @click="previous" v-if="step > 0 && step < 3">Back</b-button>
      <b-button
        v-if="step < 3"
        class="m-3"
        @click="next"
        :disabled="nextDisabled"
        :variant="step === 2 ? 'success' : 'info'"
      >
        <span v-if="step < 2">Next Step</span>
        <span v-else>Start Conversion</span>
      </b-button>
      <b-button 
        v-else
        class="m-3"
        @click="close"
        :disabled="!conversionDone"
        :variant="conversionDone ? (conversionError ? 'danger' : 'success') : 'primary'">
        <span v-if="!conversionDone">
            <b-spinner small class="mr-1"></b-spinner>Conversion in progress...</span>
        <span v-else>Exit</span>
      </b-button>
    </r20-footer>
  </div>
</template>

<script>
import R20Header from "./components/R20Header.vue";
import MainOptions from "./components/MainOptions.vue";
import AdvancedOptions from "./components/AdvancedOptions.vue";
import FileSelect from "./components/FileSelect.vue";
import OutputWindow from "./components/OutputWindow.vue";
import R20Footer from "./components/R20Footer.vue";

import { mapGetters, mapState } from "vuex";

export default {
  name: "App",
  components: {
    R20Header,
    MainOptions,
    AdvancedOptions,
    FileSelect,
    OutputWindow,
    R20Footer
  },
  data() {
    return {
      version: "",
      foundryDirectory: null,
      step: 0,
      goingBack: false
    };
  },
  computed: {
    ...mapState(["error", "folder", "conversionDone", "conversionError"]),
    animateEnter() {
      const animation = this.goingBack ? "slideInLeft" : "slideInRight";
      return `animate__animated animate__fast animate__${animation} position-fixed`;
    },
    animateExit() {
      const animation = this.goingBack ? "slideOutRight" : "slideOutLeft";
      return `animate__animated animate__fast animate__${animation} position-fixed`;
    },
    validFile() {
      return !!this.fileType;
    },
    nextDisabled() {
      if (this.step === 0) return !this.fileType;
      if (this.step === 1) return Boolean(this.error || !this.folder);
      return false;
    },
    ...mapGetters(["fileType"])
  },
  methods: {
    next() {
      this.goingBack = false;
      this.step++;
    },
    previous() {
      this.goingBack = true;
      this.step--;
    },
    close() {
      window.close();
    }
  },
  async created() {
    this.version = await eel.getVersion()();
    const dir = await eel.getFoundryDirectory()();
    this.$store.commit("setFoundryDirectory", dir);
    if (dir) this.$store.dispatch("setFolder", dir);
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
