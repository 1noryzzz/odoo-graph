import request from '../utils/request.js'


// 新增收集表单
export const saveTableService = ({
	name,
	phone,
	info
}) => request.post('user/table/save', {
	name,
	phone,
	info
})