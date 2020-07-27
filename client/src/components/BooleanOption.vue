
<template>
  <b-form-group
    :label="label"
    label-cols
    label-align="right"
    :description="description"
  >
    <div>
      <b-badge @click="toggle()" :variant="this.value ? 'primary' : 'secondary'" pill>{{ badge || (value ? enabled : disabled) }}</b-badge>
      <b-form-checkbox switch v-model="boolValue" class="float-right"></b-form-checkbox>
    </div>
  </b-form-group>
</template>

<script>
export default {
    props: {
        label: String,
        description: String,
        value: Boolean,
        enabled: {
            type: String,
            default: "Enabled"
        },
        disabled: {
            type: String,
            default: "Disabled"
        },
        badge: String
    },
    computed: {
        boolValue: {
            get() {
                return this.value;
            },
            set(value) {
                this.$emit('input', value)
            }
        }
    },
    methods: {
        toggle() {
            this.boolValue = !this.boolValue;
        }
    }
}
</script>