// This file serves as a replacement for the eel interface when testing using vue-cli serve
// It will only return static content for testing the UI with no functionality
const eel = {
    makeCB(name, result) {
        eel[name] = (...args) => {
            return async () => {
                if (typeof(result) === "function")
                    return result(...args)
                return result
            }
        }
    },
    fakeEel: false,
    __exposed: {},
    expose(f) {
        eel.__exposed[f.name] = f;
    }
}
eel.makeCB("getVersion", "0.9-dev");
eel.makeCB("getFoundryDirectory", "C:/FakePath/FoundryVTT");
eel.makeCB("loadCampaign", (file_type, path) => {eel.__exposed.logInfo("Campaign loaded\n"); return null;})
eel.makeCB("getCampaignTitle", (file_type, path) => {return "Lost Mine of Phandelver"})
eel.makeCB("getCampaignSlug", (file_type, path) => {return "lmop"})
eel.makeCB("ask_file", "lmop.json")
eel.makeCB("ask_folder", "C:/Foo/Bar/Data")
eel.makeCB("does_file_exist", (p) => p && p.endsWith(".json"))
eel.makeCB("does_folder_exist", (p) => {
    console.log("Folder:", p)
    return p && p.startsWith("C:") && p.endsWith("FoundryVTT")
})
eel.makeCB("slugifyString", (s) => `__${s}__`);
eel.makeCB('startConversion', async (options) => {
    console.log("Starting conversion with options : ", options);
    eel.__exposed.logInfo("Hello world\n")
    await new Promise(r => setTimeout(r, 2000))
    return {error: false, message: "All done!\nCongratulations!\nGood night!"}
})
//setInterval(() => eel.__exposed.logInfo(`One more line ${Math.random()}\n`), 500)