<template>
  <!-- 弹窗遮罩层 -->
  <view v-if="visible" class="popup-container">
    <!-- 半透明背景 -->
    <view class="mask" @click="onClose"></view>

    <!-- 弹窗内容 -->
    <view class="popup-content">
      <!-- 弹窗标题 -->
      <view class="popup-title">登录账号</view>

      <!-- 登录说明 -->
      <view class="popup-desc">
        点击下方按钮获取手机号进行快捷登录
      </view>

      <!-- 获取手机号按钮 (微信小程序特有) -->
      <button class="get-phone-btn" open-type="getPhoneNumber" @getphonenumber="onGetPhoneNumber">
        <text class="btn-text">获取手机号快捷登录</text>
      </button>

      <!-- 关闭按钮 -->
      <view class="close-btn" @click="onClose">
        取消
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, defineProps, defineEmits, watch, onMounted } from 'vue';
import { login,binPhone } from '../apis/banner'
import { setStorage } from '/utils/storage.js'
// 组件属性
const props = defineProps({
  // 控制弹窗显示/隐藏
  visible: {
    type: Boolean,
    default: false
  }
});

// 组件事件
const emit = defineEmits(['close', 'login']);

// 处理关闭弹窗
const onClose = () => {
  emit('close');
};

// 处理获取手机号事件 (微信小程序)
const onGetPhoneNumber = async(e) => {
  const result=await binPhone({code:e.detail.code})
  console.log(result,'result')
  if (result?.code==200) {
    setStorage('userInfo',JSON.stringify(result.data))
    emit('login', e.detail);
      uni.showToast({
        title: '登录成功',
        icon: 'success'
      });
  }
  
  // sendEncryptedData(e)
  // 传递加密数据给父组件处理

};
// 监听弹窗关闭，可在这里添加额外的清理逻辑
watch(
  () => props.visible,
  (newVal) => {
    console.log(newVal, 'newVal')
    if (!newVal) {
      // 弹窗关闭时的处理
    }
  }, {
  deep: true,
  immediate: true
}
);
</script>

<style scoped>
.popup-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999999;
  display: flex;
  justify-content: center;
  align-items: center;
}

.mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
}

.popup-content {
  width: 600rpx;
  background-color: #fff;
  border-radius: 20rpx;
  padding: 40rpx 30rpx;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.popup-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

.popup-desc {
  font-size: 28rpx;
  color: #666;
  text-align: center;
  margin-bottom: 40rpx;
  line-height: 1.5;
}

.get-phone-btn {
  width: 100%;
  background-color: #07c160;
  color: #fff;
  border-radius: 80rpx;
  padding: 6rpx 0;
  font-size: 30rpx;
  margin-bottom: 20rpx;
}

.close-btn {
  color: #666;
  width: 100%;
  font-size: 28rpx;
  padding: 15rpx 0;
  text-align: center;
  border-radius: 80rpx;
  background-color: #f5f5f5;
  margin-top: 10rpx;
}
</style>