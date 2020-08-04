export default function (store) {
    function logInfo(text) {
        console.log(text);
        store.commit('appendLog', text + "\n");
    }
    eel.expose(logInfo, 'logInfo');
    eel.expose(logInfo, 'logWarning');
    eel.expose(logInfo, 'logError');
}
