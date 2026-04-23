<template>
    <view class="info-section">
      <view class="section-title">
        <view class="title-dot"></view>
        {{ title }}
      </view>
      <slot></slot>
    </view>
  </template>
  
  <script setup>
  const props = defineProps({
    title: {
      type: String,
      required: true,
    },
  });
  </script>
  
  <style scoped>
  .info-section {
    margin-bottom: 24px;
  }
  
  .section-title {
    display: flex;
    align-items: center;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 12px;
  }
  
  .title-dot {
    width: 8px;
    height: 18px;
    background-color: #00b42a;
    margin-right: 8px;
  }
  </style>