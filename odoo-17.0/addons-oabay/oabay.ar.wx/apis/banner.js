import request from '../utils/request.js'
//登陆

// export const login = (params) => request.get(`app/signup/login?code=${params.code}`)
export const login = (params) => {
	return request({
		url: `app/signup/login?code=${params.code}`,
		method: 'GET',
		loading: false,
	})
}
export const binPhone = (params) => {
	return request({
		url: `app/signup/binPhone`,
		method: 'POST',
		data:params,
		loading: false,
	})
}

export const getBannerListService = () => {
	return request({
		url: `app/banner/list`,
		method: 'GET',
		loading: false,
	})
}

//获取公告
export const getNoticeList = () => {
	return request({
		url: `app/notice/getNoticeList`,
		method: 'GET',
		loading: false,
	})
}
//获取公告详情
export const getDetailById = (params) => {
	return request({
		url: `app/notice/getDetailById?noticeId=${params.noticeId}`,
		method: 'GET',
		loading: false,
	})
}
//获取项目列表
export const getProjectList = () => {
	return request({
		url: `app/signup/getProjectList`,
		method: 'GET',
		loading: false,
	})
}
export const saveSignUp = (params) => {
	return request({
		url: `app/signup/signUp`,
		method: 'POST',
		data:params,
		loading: false,
	})
}
//获取报名列表
export const mySignUpList = () => {
	return request({
		url: `app/signup/mySignUpList`,
		method: 'GET',
		loading: false,
	})
}
//获取学校
export const selectBySchoolName = (schoolName) => {
	return request({
		url: `app/signup/selectBySchoolName?schoolName=${schoolName}`,
		method: 'GET',
		loading: false,
	})
}
//支付
export const getPayInfo = (params) => {
	return request({
		url: `app/signup/getPayInfo?orderNo=${params.orderNo}`,
		method: 'GET',
		loading: false,
	})
}
//缴费列表
export const myPayList = () => {
	return request({
		url: `app/signup/myPayList`,
		method: 'GET',
		loading: false,
	})
}
//订单详情
export const myOrderDetail = (id) => {
	return request({
		url: `app/signup/myOrderDetail?id=${id}`,
		method: 'GET',
		loading: false,
	})
}
//用户详情
export const userDetail = () => {
	return request({
		url: `app/signup/getUserInfo`,
		method: 'GET',
		loading: false,
	})
}
//修改用户信息
export const updateUserInfo = (data) => {
	return request({
		url: `app/signup/updateUserInfo`,
		method: 'post',
		data,
		loading: false,
	})
}
//发送信息
export const getSmsCode = (data) => {
	console.log(data,'dataaa')
	return request({
		url: `app/signup/smsCode?basePhone=${data.basePhone}`,
		method: 'get',
		loading: false,
	})
}
export const updateSignUp = (params) => {
	return request({
		url: `app/signup/save`,
		method: 'POST',
		data:params,
		loading: false,
	})
}

//修改发票信息
export const updateInvoiceInfo = (data) => {
	return request({
		url: `app/signup/updateInvoiceInfo`,
		method: 'post',
		data,
		loading: false,
	})
}
