export default function (store) {
    function writeStdout(text) {
        console.log(text);
        store.commit('appendLog', text);
    }
    eel.expose(writeStdout, 'writeStdout');
}
