<template>
	<view class="container">
		<view class="title">
			<view class="left">
				{{props.title}}
			</view>
			<view class="more" @click="clickMore">
				更多<up-icon name="arrow-right-double"></up-icon>
			</view>
		</view>
		<view class="content">
			<imgItem :data="item" v-for="item in props.itemList" :key="item.id"></imgItem>
		</view>

	</view>
</template>

<script setup>
	import imgItem from './imgItem.vue';

	const props = defineProps({
		title: {
			type: String,
			required: true
		},
		redictUrl: String,
		itemList: Array
	})


	const clickMore = () => {
		uni.navigateTo({
			url: `${props.redictUrl}?title=${props.title}`
		})
	}
</script>
<style scoped lang="scss">
	.container {
		display: flex;
		flex-direction: column;
		border-radius: 20rpx;
		padding: 0 20rpx;

		.title {
			display: flex;
			justify-content: space-between;
			align-items: center;

			.left {
				font-size: 36rpx;
				color: #f75858;
				font-weight: 700;
				margin: 20rpx 0;
			}

			.more {
				background-color: rgb(246, 245, 244);
				padding: 10rpx 20rpx;
				font-size: 26rpx;
				// border: 2rpx solid rgb(225, 225, 223);
				text-align: center;
				color: rgb(103, 102, 100);
				border-radius: 60rpx;
				display: flex;
			}
		}

		.content {
			display: flex;
			justify-content: space-between;
			margin-bottom: 20rpx;
			flex-wrap: wrap;
		}
	}
</style>