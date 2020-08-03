export default {
    setFile(state, {file, title, slug}) {
        state.file = file;
        if (title)
            state.title = title;
        if (slug)
            state.slug = slug;
    },
    setFolder(state, value) {
        state.folder = value;
    },
    setError(state, value) {
        state.error = value;
    },
    setFoundryDirectory(state, value) {
        state.foundryDirectory = value;
    },
    setOption(state, options) {
        state.options = Object.assign({}, state.options, options);
    },
    appendLog(state, text) {
        state.debugLog += text;
    },
    conversionDone(state, value) {
        state.conversionDone = value;
    },
    conversionError(state, value) {
        state.conversionError = value;
    },
}