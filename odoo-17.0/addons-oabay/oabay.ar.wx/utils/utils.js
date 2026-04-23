
import {getStorage} from './storage.js'
/**
 * 从身份证号提取出生年月日
 * @param {string} idCard - 身份证号码
 * @returns {string} 格式为YYYY-MM-DD的出生日期
 * @throws {Error} 当身份证号无效时抛出错误
 */
function extractBirthday(idCard) {
    console.log(idCard,'idCardidCard')
    // 去除可能的空格
    idCard = idCard.replace(/\s+/g, '')
    
    // 验证身份证号长度
    if (idCard.length === 15) {
        // 15位身份证：6位地区码 + 6位出生日期(yyMMdd) + 3位顺序码
        const year = '19' + idCard.substr(6, 2);
        const month = idCard.substr(8, 2);
        const day = idCard.substr(10, 2);
        return `${year}-${month}-${day}`;
    } else if (idCard.length === 18) {
        // 18位身份证：6位地区码 + 8位出生日期(yyyyMMdd) + 3位顺序码 + 1位校验码
        const year = idCard.substr(6, 4);
        const month = idCard.substr(10, 2);
        const day = idCard.substr(12, 2);
        return `${year}-${month}-${day}`;
    } else {
        throw new Error('无效的身份证号长度');
    }
}

/**
 * 验证身份证号中的日期是否有效
 * @param {string} idCard - 身份证号码
 * @returns {boolean} 日期是否有效
 */
function validateBirthday(idCard) {
    try {
        const dateStr = extractBirthday(idCard);
        const date = new Date(dateStr);
        return !isNaN(date.getTime());
    } catch {
        return false;
    }
}
/**
 * 判断是否登录
 */
function goLogin() {
	const userInfo =getStorage('userInfo')?JSON.parse(getStorage('userInfo')): {}
	 if(!userInfo.userPhone){
		  uni.reLaunch({
			url: '/pages/login/index',
			fail: (err) => console.error('reLaunch 失败:', err)
		  });
	   return false
	 }
     return true
}
// 导出函数
export { extractBirthday, validateBirthday,goLogin };
