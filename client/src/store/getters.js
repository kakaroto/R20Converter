export default {
    fileType(state, getters) {
        if (!state.file) return null;
        if (getters.mimetype === "application/json")
            return "JSON";
        else
            return [
                "application/zip",
                "application/x-zip-compressed",
                "application/octet-stream"
            ].includes(getters.mimetype) ? "ZIP" : null;
    },
    filename(state) {
        if (state.file instanceof Blob)
            return state.file.name;
        return state.file;
    },
    mimetype(state, getters) {
        if (state.file instanceof Blob)
            return state.file.type;
        const filename = getters.filename;
        if (filename)
            return filename.endsWith(".json") ? "application/json" : filename.endsWith(".zip") ? "application/zip" : "application/random";
        return null;
    },
    outputPath(state) {
        if (!state.folder) return "";
        const type = state.options.exportAsModule ? "modules" : "worlds";
        return `${state.folder}/Data/${type}/${state.options.slug}`;
    }
}