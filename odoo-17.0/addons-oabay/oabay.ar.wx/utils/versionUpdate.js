/**
 * 微信小程序版本强制更新
 * @param {Boolean} isForce - 是否强制更新（默认true）
 */
export const checkWxVersionUpdate = (isForce = true) => {
    // 仅在微信小程序环境执行
    if (uni.getSystemInfoSync().platform !== 'devtools' && !/mp-weixin/.test(uni.getSystemInfoSync().envVersion)) {
      return;
    }
  
    // 获取微信小程序更新管理器
    const updateManager = uni.getUpdateManager();
  
    // 检测到有新版本
    updateManager.onCheckForUpdate((res) => {
      if (res.hasUpdate) {
        console.log('检测到新版本，准备更新');
      }
    });
  
    // 新版本下载完成
    updateManager.onUpdateReady(() => {
      uni.showModal({
        title: '版本更新',
        content: '检测到新版本已下载完成，请重启小程序以使用最新版本',
        showCancel: !isForce, // 强制更新时隐藏取消按钮
        success: (res) => {
          if (res.confirm) {
            // 应用新版本并重启
            updateManager.applyUpdate();
          }
        }
      });
    });
  
    // 新版本下载失败
    updateManager.onUpdateFailed(() => {
      uni.showModal({
        title: '更新失败',
        content: '新版本下载失败，请检查网络后重新进入小程序',
        showCancel: false,
        success: () => {
          // 下载失败时，若为强制更新，可提示用户退出重进
          if (isForce) {
            uni.showToast({
              title: '请退出小程序重新进入',
              icon: 'none',
              duration: 3000
            });
          }
        }
      });
    });
  };