import request from '../utils/request.js'


// 分页查询所有路线
export const getRoadPageService = ({
	pageNum = 1,
	pageSize = 10
}) => request.post(
	'user/road/page', {
		pageSize,
		pageNum
	}
)

// 通过id获取线路
export const getRoadByIdService = (id) => request.get(`user/road/get?id=${id}`)