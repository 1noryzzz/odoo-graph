<template>
    <view class="launch-page">
      <!-- 加载动画 -->
      <view class="loading-container">
        <view class="loader"></view>
        <text class="loading-text">{{ loadingText }}</text>
      </view>
    </view>
  </template>
  
  <script setup>
  import { onMounted, ref } from 'vue'
  import { login } from '../../apis/banner'
import { setStorage } from '../../utils/storage.js'
  const loadingText = ref('验证中...')
  import Navigator from '../../utils/navigator';
  onMounted(async () => {
    uni.login({
    provider: 'weixin',
    success: function (loginRes) {
        login({
            code:loginRes.code,
        }).then(res=>{
          console.log('33333',res.data)
            setStorage('userInfo',JSON.stringify(res.data))
            loadingText.value = '加载成功'
            // Navigator.reLaunch('/pages/index/index')
		
            uni.reLaunch({
              url: "/pages/index/index",
              fail: (err) => console.error('reLaunch 失败:', err)
            });
            // if(res.data?.userPhone){
            //   Navigator.reLaunch('/pages/index/index')
            // }else{
            //   Navigator.reLaunch('/pages/login/index')
            // }
            
            
        }).catch((res)=>{
            loadingText.value = res.msg || '加载失败'
        });
    }
    });
  })
  </script>
  
  <style scoped>
  .launch-page {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #fff;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }
  
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 30rpx;
  }
  
  /* 加载动画 */
  .loader {
    width: 60rpx;
    height: 60rpx;
    border: 6rpx solid #eee;
    border-top-color: #07c160;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  .loading-text {
    font-size: 28rpx;
    color: #666;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  </style>