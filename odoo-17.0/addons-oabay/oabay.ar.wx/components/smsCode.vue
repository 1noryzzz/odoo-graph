<template>
    <view class="sms-verification">
      <!-- 手机号输入框 -->
      <view class="input-group phone-input">
        <u-icon name="phone" class="input-icon" color="#606266" size="20"></u-icon>
        <u-input
          v-model="phone"
          type="number"
          placeholder="请输入手机号"
          border="none"
          class="input-field"
          @input="handlePhoneInput"
          :focus="phoneFocus"
          @focus="phoneFocus = true"
          @blur="phoneFocus = false"
        ></u-input>
        <u-icon 
          v-if="phone && !phoneFocus" 
          name="close-circle" 
          class="clear-icon" 
          color="#c0c4cc" 
          size="18"
          @click="phone = ''"
        ></u-icon>
      </view>
  
      <!-- 验证码区域 -->
      <view class="input-group code-input">
        <u-input
          v-model="code"
          type="number"
          maxlength="4"
          placeholder="请输入验证码"
          border="none"
          class="input-field code-field"
          @change="handleCodeInput"
          :focus="codeFocus"
          @focus="codeFocus = true"
          @blur="codeFocus = false"
        ></u-input>
        <u-icon 
          v-if="code && !codeFocus" 
          name="close-circle" 
          class="clear-icon" 
          color="#c0c4cc" 
          size="18"
          @click="code = ''"
        ></u-icon>
        
        <!-- 发送按钮 -->
         <view class="send-box">
            <u-button
            :text="buttonText"
            :disabled="isDisabled"
            @click="sendCode"
            class="send-btn"
            :class="{ active: !isDisabled && phoneValid }"
            size="mini"
            shape="circle"
            ></u-button>
        </view >
      </view>
  
      <!-- 错误提示 -->
      <u-toast ref="uToast" />
    </view>
  </template>
  
  <script setup>
  import { ref, watch, onUnmounted, computed } from 'vue';
  
  // 组件属性
  const props = defineProps({
    // 验证码长度
    codeLength: {
      type: Number,
      default: 4
    },
    // 倒计时秒数
    countDown: {
      type: Number,
      default: 60
    },
    // 手机号验证规则
    phoneReg: {
      type: RegExp,
      default: () => /^1[3-9]\d{9}$/
    }
  });
  
  // 组件事件
  const emit = defineEmits(['codeChange', 'codeComplete', 'sendCode']);
  
  // 响应式变量
  const phone = ref('');
  const code = ref('');
  const isDisabled = ref(true);
  const buttonText = ref('获取验证码');
  const remainingTime = ref(0);
  const phoneFocus = ref(false);
  const codeFocus = ref(false);
  let timer = null;
  
  // 手机号验证状态
  const phoneValid = computed(() => {
    return props.phoneReg.test(phone.value);
  });
  
  // 监听手机号变化，更新按钮状态
  watch(phone, (newVal) => {
    isDisabled.value = !phoneValid.value || remainingTime.value > 0;
  });
  
  // 处理手机号输入
  const handlePhoneInput = (val) => {
    // 过滤非数字字符
    phone.value = val.replace(/\D/g, '');
  };
  
  // 处理验证码输入
  const handleCodeInput = (val) => {
    // 过滤非数字并限制长度
    code.value = val.replace(/\D/g, '').slice(0, props.codeLength);
    emit('codeChange', code.value);
    
    // 输入完成时触发
    if (code.value.length === props.codeLength) {
      emit('codeComplete', code.value);
    }
  };
  
  // 发送验证码
  const sendCode = () => {
    if (!phoneValid.value) {
      uni.showToast({ title: '请输入正确的手机号', type: 'error' });
      return;
    }
    console.log(4444)
    // 触发父组件的发送逻辑
    emit('sendCode', phone.value, (success) => {
      if (success) {
        startCountDown();
        uni.showToast({ title: '验证码已发送', type: 'success' });
      } else {
        uni.showToast({ title: '发送失败，请重试', type: 'error' });
      }
    });
  };
  
  // 开始倒计时
  const startCountDown = () => {
    remainingTime.value = props.countDown;
    isDisabled.value = true;
    buttonText.value = `${remainingTime.value}s后重发`;
    
    timer = setInterval(() => {
      remainingTime.value--;
      buttonText.value = `${remainingTime.value}s后重发`;
      
      if (remainingTime.value <= 0) {
        resetCountDown();
      }
    }, 1000);
  };
  
  // 重置倒计时
  const resetCountDown = () => {
    clearInterval(timer);
    timer = null;
    remainingTime.value = 0;
    buttonText.value = '获取验证码';
    isDisabled.value = !phoneValid.value;
  };
  
  // 组件卸载时清理定时器
  onUnmounted(() => {
    if (timer) {
      clearInterval(timer);
    }
  });
  
  // 暴露清空方法供父组件调用
  defineExpose({
    clearAll: () => {
      phone.value = '';
      code.value = '';
      resetCountDown();
    }
  });
  </script>
  
  <style scoped lang="scss">
  .sms-verification {
    width: 100%;
    box-sizing: border-box;
  }
  
  // 输入框组样式
  .input-group {
    display:flex;
    align-items:center;
    height:80rpx;
    padding:0 24rpx;
    margin-bottom:32rpx;
    border-radius:24rpx;
    background-color:#e3e9f7b3;
    transition:all 0.3s ease;
    
    &.phone-input {
      margin-top: 20rpx;
      border: 1px solid #eee;
    }
    
    // 聚焦状态
    &:has(.input-field:focus) {
    //   box-shadow:0 0 0 2px rgba(55, 142, 255, 0.2);
    //   border: 1px solid #378eff;
    }
  }
  
  // 输入框图标
  .input-icon {
    flex-shrink: 0;
  }
  
  // 输入框
  .input-field {
    flex: 1;
    height: 100%;
    font-size: 32rpx;
    color: #303133;
    
    &::placeholder {
      color: #c0c4cc;
      font-size: 30rpx;
    }
  }
  
  // 清除图标
  .clear-icon {
    margin-left: 16rpx;
    cursor: pointer;
    transition: color 0.2s;
    
    &:hover {
      color: #909399;
    }
  }
  
  // 验证码区域特殊样式
  .code-input {
    position: relative;
    display: flex;
    border: 1px solid #eee;
  }
  
  .code-field {
     // 给按钮留出空间
     flex: 1;
  }
  .send-box{
    width: 180rpx;
  }
  // 发送按钮样式
  .send-btn {
    // position: absolute;
    // right: 24rpx;
    // top: 50%;
    // transform: translateY(-50%);
    width: 180rpx !important;
    height: 72rpx;
    font-size: 28rpx;
    background-color: #e5e6eb;
    color: #909399;
    transition: all 0.3s ease;
    
    &.active {
      background: linear-gradient(135deg, #378eff 0%, #526fff 100%);
      color: #ffffff;
      box-shadow: 0 8rpx 24rpx rgba(55, 142, 255, 0.3);
      
      &:hover {
        opacity: 0.9;
        transform: translateY(-50%) scale(1.02);
      }
      
      &:active {
        transform: translateY(-50%) scale(0.98);
      }
    }
    
    &:disabled {
      opacity: 0.8;
      cursor: not-allowed;
    }
  }
  </style>