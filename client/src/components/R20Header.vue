<template>
  <div class="sticky-top">
    <b-card no-body class="overflow-hidden m-2">
      <b-row no-gutters>
        <b-col cols="1">
          <b-card-img src="/logo.png" alt="Logo" class="rounded-0"></b-card-img>
        </b-col>
        <b-col cols="11">
          <b-card-body :title="`R20Converter ${version}`">
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
  props: ["version"]
};
</script>