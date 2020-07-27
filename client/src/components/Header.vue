<template>
  <div class="sticky-top">
    <b-card no-body class="overflow-hidden m-2">
      <b-row no-gutters>
        <b-col cols="1">
          <b-card-img src="https://media.discordapp.net/attachments/695361362813124698/736801108864925716/r20converter_logo.png?width=563&height=563" alt="Image" class="rounded-0"></b-card-img>
        </b-col>
        <b-col cols="11">
          <b-card-body :title="version_string">
            <b-card-text>
              Convert your Roll20 campaign into a Foundry VTT world or a compendium module
              <a
                href="https://github.com/kakaroto/R20Converter/blob/master/README.md"
                target="_blank"
                class="float-right"
              >Help?</a>
            </b-card-text>
          </b-card-body>
        </b-col>
      </b-row>
    </b-card>
  </div>
</template>

<script>
export default {
  props: ["version"],
  computed: {
    version_string() {
      return `R20Converter ${this.version}`;
    }
  }
};
</script>