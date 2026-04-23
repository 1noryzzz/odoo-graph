<template>
    <view class="info-item">
      <view class="item-label">{{ label }}</view>
      <view class="item-value">{{ value }}</view>
    </view>
  </template>
  
  <script setup>
  const props = defineProps({
    label: {
      type: String,
      required: true,
    },
    value: {
      type: String,
      default: '',
    },
  });
  </script>
  
  <style scoped>
  .info-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #e5e5e5;
  }
  
  .item-label {
    color: #666;
  }
  
  .item-value {
    color: #333;
  }
  </style>