import {
	defineStore
} from 'pinia';
import {
	ref
} from 'vue';

export const useUserStore = defineStore('user', () => {
	const userInfo = ref({})

	const token = ref('')

	const setUserInfo = (info) => {
		userInfo.value = info
	}

	const setToken = (newValue) => {
		token.value = newValue
	}

	return {
		token,
		setToken,
		userInfo,
		setUserInfo
	}
}, {
	persist: {
		storage: {
			setItem(key, value) {
				uni.setStorageSync(key, value)
			},
			getItem(key) {
				return uni.getStorageSync(key)
			},
		}
	}
});