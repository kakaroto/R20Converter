import Vue from 'vue'
import Vuex from 'vuex'

import state from "./state"
import mutations from "./mutations"
import actions from "./actions"
import getters from "./getters"
import r20converter from './plugins/r20converter'

Vue.use(Vuex)

export default new Vuex.Store({
    state,
    mutations,
    actions,
    getters,
    plugins: [r20converter]
});