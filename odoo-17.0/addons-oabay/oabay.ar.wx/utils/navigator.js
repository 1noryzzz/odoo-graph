/**
 * 页面跳转工具类
 * 支持 navigateTo, redirectTo, reLaunch, switchTab, navigateBack
 */
import {getStorage} from './storage.js'
export default class Navigator {
    /**
     * 保留当前页面，跳转到应用内的某个页面
     * @param {string} url 跳转路径，如 '/pages/detail/detail'
     * @param {object} params 传递的参数对象，如 {id: 1, name: 'test'}
     */
    static navigateTo(url, params = {}) {
     const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
      if(!userInfo.userPhone){
        this.login()
        return false
      }
      const fullUrl = this.handleUrl(url, params);
      console.log(fullUrl,'fullUrlfullUrl')
      uni.navigateTo({
        url: fullUrl,
        fail: (err) => {
          console.error('navigateTo 失败:', err);
          // 处理跳转失败（如页面栈溢出）
          if (err.errMsg.includes('page stack overflow')) {
            this.reLaunch(url, params);
          }
        }
      });
    }
  
    /**
     * 关闭当前页面，跳转到应用内的某个页面
     * @param {string} url 跳转路径
     * @param {object} params 传递的参数对象
     */
    static redirectTo(url, params = {}) {
        const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
      if(!userInfo.userPhone){
        this.login()
        return false
      }
      const fullUrl = this.handleUrl(url, params);
      uni.redirectTo({
        url: fullUrl,
        fail: (err) => console.error('redirectTo 失败:', err)
      });
    }
  
    /**
     * 关闭所有页面，打开到应用内的某个页面
     * @param {string} url 跳转路径
     * @param {object} params 传递的参数对象
     */
    static reLaunch(url, params = {}) {
        const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
        if(!userInfo.userPhone){
        this.login()
        return false
      }
      const fullUrl = this.handleUrl(url, params);
      uni.reLaunch({
        url: fullUrl,
        fail: (err) => console.error('reLaunch 失败:', err)
      });
    }
  
    /**
     * 跳转到 tabBar 页面，并关闭其他所有非 tabBar 页面
     * @param {string} url tabBar页面路径（必须在app.json的tabBar中配置）
     */
    static switchTab(url) {
      // switchTab不支持带参数，强制清空参数
      const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
      if(!userInfo.userPhone){
        this.login()
        return false
      }
      uni.switchTab({
        url: url.split('?')[0],
        fail: (err) => console.error('switchTab 失败:', err)
      });
    }
  
    /**
     * 关闭当前页面，返回上一页面或多级页面
     * @param {number} delta 返回的页面数，默认1
     */
    static navigateBack(delta = 1) {
        const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
        if(!userInfo.userPhone){
        this.login()
        return false
      }
      uni.navigateBack({
        delta,
        fail: (err) => console.error('navigateBack 失败:', err)
      });
    }
  
    /**
     * 处理URL和参数，拼接成完整路径
     * @param {string} url 基础路径
     * @param {object} params 参数对象
     * @returns {string} 完整路径
     */
    static handleUrl(url, params) {
      if (!params || Object.keys(params).length === 0) {
        return url;
      }
  
      // 拼接参数
      const paramsStr = Object.entries(params)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
  
      // 处理已有参数的情况
      return url.includes('?') 
        ? `${url}&${paramsStr}` 
        : `${url}?${paramsStr}`;
    }
     /**
     * 未登录返回登录页
     * @param {string} url 基础路径
     * @param {object} params 参数对象
     * @returns {string} 完整路径
     */
     static login() {
        uni.reLaunch({
          url: '/pages/login/index',
          fail: (err) => console.error('reLaunch 失败:', err)
        });
      }
  }
  