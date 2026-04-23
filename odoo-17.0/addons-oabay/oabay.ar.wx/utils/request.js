// 引入Vuex store
import {getStorage,clearStorage} from './storage.js'
import Navigator from './navigator';
// 请求超时时间
const timeout = 30000;

/**
 * 请求接口参数
 * @param {String} url  接口地址
 * @param {String} method  请求方法 post/get
 * @param {Object} data 请求参数
 * @param {Object} header 请求头 
 * @param {boolean} loading 加载动画
 */
export default function(options) {
  const url = options.url;
  const method = options.method || "GET";
  const data = options.data || {};
  
  // 从Vuex获取token
   const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
  const header = {
    "content-type":options.header?options.header['content-type']: "application/json",
    "id":userInfo.id||'',
  }

  // Vue2中获取环境变量
  const baseUrl ='https://talentmakestomorrow.cn/signup/' + url;
  
  return new Promise((resolve, reject) => {
    // if (options.loading === true) {
    //   uni.showLoading({
    //     title: '加载中',
    //     mask: true
    //   })
    // }
    uni.request({
      url: baseUrl,
      method: method,
      header: header,
      data: data,
      timeout: timeout,
      success(response) {
        const resData = response.data;
        if (resData.code == "200") {
          resolve(resData);
        } else {
          if (resData.code === "104") {
            // 处理104错误
          } else if (resData.code === "11016" || resData.code === "11011") { // token过期或无效
            console.log("token接口请求是异常")
            // userLogin()
            // repeatRequest(baseUrl, method, options.header, data, resolve, reject)
          }else if (resData.code === 401) { // token过期或无效

            clearStorage('token',null)
            Navigator.reLaunch(
              '/pages/transition/transition'
            )
            // repeatRequest(baseUrl, method, options.header, data, resolve, reject)
          } else {
            uni.showToast({
              title: resData.msg,
              icon: 'none',
              duration: 4000
            })
    
            resolve(resData);
          }
        }
      },
      fail(error) {
        if (error.errMsg.indexOf("request:fail") !== -1) {
          uni.showToast({
            title: "网络异常",
            icon: "none",
            duration: 4000
          })
        } else {
          uni.showToast({
            title: "未知异常",
            icon: "none",
            duration: 4000
          })
        }
        reject(error);
      },
      complete() {
        console.log('complete')
        // uni.hideToast();
        // if (options.loading === true) {
        //   uni.hideLoading();
        // }
      }
    })
  }).catch(() => {})
}

