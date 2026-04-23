<template>

	<view class="main-container-box">
		<!-- <up-swiper height="384rpx" circular indicator indicatorMode="dot" :list="bannerList">
		</up-swiper> -->
		<swiper class="swiper" circular :indicator-dots="swiper.indicatorDots" :autoplay="swiper.autoplay" :interval="swiper.interval"
				:duration="swiper.duration">
			<swiper-item v-for="item in bannerList">
				<image class="banner-image" :src="item" />
			</swiper-item >
		</swiper>
		<view class="mt-20 ml-20 mr-20 font-30 notice-text">
	     公告
		</view>
		<view class="mt-20 ml-20 mr-20 notice-custom">
			<up-notice-bar bgColor="#fff" color="rgb(55,65,81)" :text="noticeMessages" direction="column" @click="handleNotice"/>
		</view>
		<view class="mt-20 ml-20 mr-20 font-30 notice-text">
			技能评价报名
		</view>
		<view class="mt-20 ml-20 mr-20 notice-custom">	
				<view class="module-item" @click="goHrManager(item.id)" v-for="item in getProjectData" :key="item.id">
					<text>
						{{item.projectName}}
					</text>
				</view>
		</view>
		<PhoneNumber
			:visible="showLoginPopup"
			@close="showLoginPopup = false"
			@login="handleLogin"
		></PhoneNumber>
	</view>


</template>

<script setup>
import {
	ref,
	reactive,
	onMounted
} from 'vue';
import {
	getBannerListService,
	getNoticeList,
	getProjectList
} from '/apis/banner.js'
import PhoneNumber from '@/components/phoneNumber'
import {
	getImgUrl
} from '../../utils/imgUtil';
import Navigator from '../../utils/navigator';
import {getStorage,setStorage} from '../../utils/storage';
import { onPullDownRefresh } from '@dcloudio/uni-app';
import {goLogin} from  '@/utils/utils'
const noticeMessages = ref([]);
const isStart=ref(false)
onMounted(() => {
	getBannerList()
	getNotice()
	getprojectLists()
})
onPullDownRefresh(()=>{
	if(!isStart.value){
		isStart.value=true
	}else{
		isStart.value=false
		return false
	}
	uni.startPullDownRefresh();
	getBannerList()
	getNotice()
	getprojectLists()
        //监听下拉刷新动作的执行方法，每次手动下拉刷新都会执行一次
        // console.log('refresh');
        // setTimeout(function () {
        //     uni.stopPullDownRefresh();  //停止下拉刷新动画
        // }, 1000);
})

// 控制弹窗显示/隐藏
const showLoginPopup = ref(false);

// 处理登录逻辑（接收组件传递的手机号信息）
const handleLogin = (phoneData) => {
  // 这里写后续登录逻辑（如调用后端接口、存储token等）
  showLoginPopup.value = false; // 登录后关闭弹窗
};
const goHrManager=(id)=>{
	if(!goLogin()){
        return false
    }
	const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
	if(!userInfo||!userInfo.userPhone){
		showLoginPopup.value=true
	}else{
		setStorage('projectId',id)
		Navigator.switchTab('/pages/signUpList/signUpList')
	}
	
}
const bannerList = ref([])
const swiper=reactive({
	indicatorDots: true,
	autoplay: true,
	interval: 200000,
	duration: 500
})
const getProjectData = ref([])
const noticeList=ref([])
const getBannerList = async () => {
	const res = await getBannerListService()
	bannerList.value = res.data.map(item => {
		return getImgUrl(item.imageUrl)
	})
}
const getNotice = async () => {
	let newArr=[]
	const res = await getNoticeList()
	if(res.code==200){
		noticeList.value = res.data
		noticeList.value.forEach(item=>{
            newArr.push(item.noticeTitle)
		})
		noticeMessages.value=newArr
	}else{
		noticeList.value=[]
	}
}
const handleNotice=(index)=>{
	const id=noticeList.value[index].noticeId
	Navigator.navigateTo('/pages/noticeDetail/noticeDetail',{id:id})
}
const getprojectLists = async () => {
	const res = await getProjectList()
	if(res.code==200){
		getProjectData.value = res.data
	}else{
		getProjectData.value=[]
	}
	uni.stopPullDownRefresh();  
	
}


</script>

<style scoped lang="scss">
.main-container-box {
	padding-bottom: 30rpx;

	.title-item {
		padding: 20rpx 0;
	}

	.notice-custom {
		::v-deep(.u-notice-bar) {
			border-radius: 10rpx !important;
			box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.1);
		}
	}

	.notice-text {
		border-left: 10rpx solid rgb(16 185 129) !important;
		padding-left: 10rpx;
	}

	.mt-20 {
		margin-top: 20rpx;
	}

	.mr-20 {
		margin-right: 20rpx;
	}

	.ml-20 {
		margin-left: 20rpx;
	}

	.font-30 {
		font-size: 30rpx;
	}

	.module-list {
		display: flex;
		flex-direction: column;
		gap: 20rpx;
	}

	.module-item {
		background-color: #fff;
		border-radius: 10rpx;
		padding:40rpx 20rpx;
		margin-bottom: 20rpx;
		box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.1);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.module-item text {
		font-size: 28rpx;
		color: #000;
	}

	.module-icon {
		width: 60rpx;
		height: 60rpx;
	}
	.banner-image{
		width: 100% !important; 
		height: 100%;
	}
	.swiper{
		height: 400rpx;
	}
}
</style>