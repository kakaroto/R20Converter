Hooks.on('init', () => {
  const tipsy = $(`<div class="roll20-tooltip tipsy tipsy-n"><div class="tipsy-arrow"></div><div class="tipsy-inner"></div></div>`);
  const inner = tipsy.find(".tipsy-inner");
  tipsy.hide();
  $("body").append(tipsy);
  Hooks.on('renderChatMessage', (message, html, data) => {
    html.find(".roll20-rolltemplate span.showtip").hover((event) => {
      const span = event.currentTarget;
      const tooltip = span.attributes["original-title"].value;
      if (event.type === "mouseenter") {
        inner.html(tooltip);
        tipsy.show();
        const rect = span.getBoundingClientRect();
        tipsy.css({top: rect.top + rect.height, left: rect.left + rect.width / 2 - tipsy[0].getBoundingClientRect().width / 2});
      } else {
        tipsy.hide();
      }
    });
  });
});