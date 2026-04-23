import App from './App'
import Navigator from './utils/navigator';
// #ifndef VUE3
import Vue from 'vue'
import './uni.promisify.adaptor'
Vue.config.productionTip = false
App.mpType = 'app'
const app = new Vue({
	...App
})
app.$mount()
// #endif

// #ifdef VUE3
import {
	createSSRApp
} from 'vue'
import pinia from './stores'
import uViewPlus from 'uview-plus';
export function createApp() {
	const app = createSSRApp(App)
	// 3. 挂载到全局属性（同样建议加 $ 前缀）
app.config.globalProperties.$Navigator = Navigator;
	app.use(uViewPlus, () => {
		return {
			options: {
				config: {
					unit: 'rpx'
				}
			}
		}
	});
	app.use(pinia);
	return {
		app
	}
}
// #endif