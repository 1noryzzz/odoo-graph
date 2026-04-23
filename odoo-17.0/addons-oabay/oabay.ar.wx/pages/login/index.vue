<template>
    <view class="content">
      <view class="login-box">
        <view class="login-logo">
          <image class="login-image" src="/static/logo.jpg"></image>
        </view>
        
        <!-- 微信小程序获取手机号按钮 -->
        <button 
          open-type="getPhoneNumber" 
          @getphonenumber="onWechatGetPhoneNumber"
          class="login-btn"
        >
         登录
        </button>
        <view class="confirm-agree">
            <view class="is-agree" @click="handleDisagree"><image src="/static/agree.png" v-if="agreeStatus"></image></view >
                <text  class="text-color"> 我已认真阅读并同意</text > <text  class="text-color-b" @click="handleJump('user')">《用户协议》</text> <text class="text-color">及</text ><text  class="text-color-b" @click="handleJump('auth')">《隐私政策》</text>
        </view>
      </view>
    </view>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue';
    import { login,binPhone } from '../../apis/banner'
    import {
	onLoad
} from '@dcloudio/uni-app'
  import Navigator from '../../utils/navigator';
  import { setStorage,getStorage } from '../../utils/storage.js'
  // 响应式状态
  const loading = ref(false);
  const agreeStatus = ref(false);
  
  // 生命周期钩子
  onLoad(() => {
    const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
    if(userInfo?.userPhone){
        Navigator.reLaunch('/pages/index/index')
    }
  });
  
  // 微信小程序获取手机号回调
  const onWechatGetPhoneNumber = async(e) => {
    if (!agreeStatus.value) {
      uni.showToast({
        title: '请确认同意用户协议',
        icon: 'none'
      });
      return false;
    }
    uni.showLoading({ title: '请求中...', mask: true });
    binPhone({code:e.detail.code}).then(result=>{
        uni.hideLoading();
        if (result?.code==200) {
            setStorage('userInfo',JSON.stringify(result.data))
            uni.showToast({
                title: '登录成功',
                icon: 'success'
            });
            Navigator.reLaunch('/pages/index/index')
        }
        })
    };

  // 切换同意状态
  const handleDisagree = () => {
    agreeStatus.value = !agreeStatus.value;
  };
  const  handleJump=(type)=>{
    let url=type=='user'?'/pages/user/userAgreement':'/pages/user/privacyPolicy'
    uni.navigateTo({
        url: url,
      });
  }
  </script>
  
  <style lang="scss" scoped>
  .login-bg {
    width: 100vw;
    min-height: 100vh;
    position: absolute;
    top: 0;
    left: 0;
  }
  
  .login-box {
    position: relative;
    top: 300rpx;
  
    .login-logo {
      width: 100%;
      text-align: center;
      .login-image {
        display: inline-block;
        transform: scale(0.5);
        transform-origin: center center;
      }
    }
  
    .login-btn {
      width: 680rpx;
      height: 100rpx;
      background: #3ea290;
      border-radius: 55rpx;
      font-weight: 500;
      font-size: 32rpx;
      color: #F8D078;
      margin: 199rpx auto 0;
      line-height: 100rpx;
      text-align: center;
      font-style: normal;
    }
  }
  
  .text-color {
    font-weight: 400;
    font-size: 22rpx;
    color: #A7A9B7;
    line-height: 30rpx;
    text-align: left;
    font-style: normal;
    padding: 0 15rpx;
  }
  
  .text-color-b {
    font-weight: 500;
    font-size: 22rpx;
    color: #333333;
    line-height: 30rpx;
    text-align: left;
    font-style: normal;
  }
  
  .is-agree {
    width: 40rpx;
    height: 40rpx;
    border: 2rpx solid #ccc;
    border-radius: 50%;
    position: relative;
    image {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
    }
  }
  
  .f22 {
    margin-top: 75rpx;
  }
  .confirm-agree{
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-left: 35rpx;
    margin-top: 35rpx;
    color: #999;
    text{
        margin-left: 10rpx;
    }
  }
  
  </style>
  