
<template>
    <b-form-group
    :label="label"
    label-cols
    label-align="right"
    :description="description"
    >
    <b-form-input v-model="stringValue" :placeholder="placeholder"></b-form-input>
    </b-form-group>
</template>

<script>
export default {
    props: {
        label: String,
        description: String,
        value: String,
        placeholder: String
    },
    computed: {
        stringValue: {
            get() {
                return this.value;
            },
            set(value) {
                this.$emit('input', value)
            }
        }
    }
}
</script>