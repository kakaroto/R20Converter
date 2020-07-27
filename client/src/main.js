import Vue from 'vue'
import { BootstrapVue } from 'bootstrap-vue'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'

import App from './App.vue'
import store from './store'

Vue.use(BootstrapVue);
/*
Vue.config.productionTip = false;
Vue.config.devtools = true;
*/
new Vue({
  render: h => h(App),
  store: store,
}).$mount('#app')
