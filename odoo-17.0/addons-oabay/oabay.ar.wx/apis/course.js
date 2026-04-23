import request from '../utils/request.js'


// 分页查询所有课程
export const getCoursePageService = ({
	pageNum = 1,
	pageSize = 10,
	info
}) => request.post(
	'user/course/page', {
		info,
		pageSize,
		pageNum
	}
)


// 通过id获取课程
export const getCourseByIdService = (id) => request.get(`user/course/get?id=${id}`)