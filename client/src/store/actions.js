export default {
    async setFile({ commit }, file) {
        const filename = file instanceof Blob ? file.name : file;
        const filetype = filename.endsWith(".json") ? "JSON" : "ZIP"
        const error = await eel.loadCampaign(filetype, filename)();
        if (error) {
            commit('setFile', {});
            return commit('setError', error);
        }
        commit('setError', null);
        const title = await eel.getCampaignTitle(filetype, filename)();
        const slug = await eel.getCampaignSlug(filetype, filename)();
        commit('setFile', {file, title, slug});
    },
    async setFolder({ commit }, folder) {
        if (folder) {
            const exists = await eel.does_folder_exist(folder)();
            if (!exists) {
                commit('setFolder', null);
                return commit('setError', "Selected folder must exist");
            }
        }
        commit('setError', null);
        commit('setFolder', folder);
    },
    async setOption({ commit }, options) {
        commit('setOption', options);
    }
}