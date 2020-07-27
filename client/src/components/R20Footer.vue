<template>
  <div>
    <div :style="`min-height: ${error ? 100 : 50}px;`"></div>
    <div class="fixed-bottom bg-light">
      <hr />
      <b-alert show variant="danger" v-if="error">{{error}}</b-alert>
      <div class="float-right">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState } from "vuex";
export default { 
  computed: {
    ...mapState(["error"])
  }
}
</script>