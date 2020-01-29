Hooks.on('ready', () => {
  Hooks.on('renderChatMessage', (message, html, data) => {
    html.find(".roll20-rolltemplate span.showtip").hover((event) => {
      let tooltip = event.currentTarget;
      console.log("Hovered on element. ", tooltip);
    });
  });
});