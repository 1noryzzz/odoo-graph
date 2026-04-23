/* =============================================================================
 * otp_interface.h – OTP interface library header file.
 *  
 * 
 * Created on 2008-11-20
 *            2009-03-12 Add C200(TOTP) API
 *			  2009-11-11 Add z201(TOTP) API
 *
 * Version:1.1
 *  
 */

#ifndef OTP_INTERFACE_H_
#define OTP_INTERFACE_H_

#ifdef WIN32
//WIN32平台
typedef unsigned __int64 uint64_t; //定义认证基数类型
#else
//非WIN32平台
#include <stdint.h>

typedef uint64_t authnum_t;
#define __stdcall
#endif

#ifdef __cplusplus
extern		"C" {
#endif

/* 返回值定义 */
#define OTP_SUCCESS					(0x00000000L) //操作成功

#define OTP_ERR_INVALID_PARAMETER	(0x00000001L) //参数无效

#define OTP_ERR_CHECK_PWD			(0x00000002L) //认证失败

#define OTP_ERR_SYN_PWD				(0x00000003L) //同步失败

#define OTP_ERR_REPLAY				(0x000000004) //动态口令被重放


/* =============================================================================
 * Function   : ET_CheckPwdz201
 * Description: OTP Z201(TOTP) 认证接口
 * Parameter  : 
 *		authkey			令牌密钥
 *      t               当前时间相对UTC Epoch秒数
 *      t0              起始参考时间相对UTC Epoch秒数(默认为0)
 *      x               TOTP变化周期(默认为60秒)
 *      drift           漂移次数
 *      authwnd		    认证范围, 通常是0-20
 *      lastsucc        前一次认证成功的相对UTC Epoch秒数(为防止重放攻击)
 *      otp				需要认证的动态口令
 *      otplen			需要认证的动态口令长度, 通常是6
 *      currsucc		认证成功后的相对UTC Epoch秒数
 *      currdft         认证成功后的当前漂移次数
 *
 * return     : 0 - 成功, 其他值为错误.
 */
int __stdcall ET_CheckPwdz201(char *authkey, uint64_t t, uint64_t t0, 
    unsigned int x, int drift, int authwnd, uint64_t lastsucc, 
    const char *otp, int otplen, uint64_t *currsucc, int *currdft);

/* =============================================================================
 * Function   : ET_Syncz201
 * Description: OTP Z201(TOTP) 同步接口
 * Parameter  : 
 *		authkey			令牌密钥，已经加密过的，需要对其进行解密
 *      t               当前时间相对UTC Epoch秒数
 *      t0              起始参考时间相对UTC Epoch秒数(默认为0)
 *      x               TOTP变化周期(默认为60秒)
 *      drift           漂移次数
 *      syncwnd         同步范围, 通常是0-20
 *      lastsucc        前一次认证成功的相对UTC Epoch秒数(为防止重放攻击)
 *      otp1            需要同步的第一个动态口令
 *      otp1len			需要同步的第一个动态口令长度, 通常是6
 *      otp2            需要同步的第二个动态口令
 *      otp2len         需要同步的第二个动态口令长度, 通常是6
 *      currsucc		认证成功后的相对UTC Epoch秒数
 *      currdft         认证成功后的当前漂移次数
 *
 * return     : 0 - 成功, 其他值为错误.
 */
int __stdcall ET_Syncz201(char *authkey, uint64_t t, uint64_t t0, 
        unsigned int x, int drift, int syncwnd, uint64_t lastsucc, 
        const char *otp1, int otp1len, const char *otp2, int otp2len, 
        uint64_t *currsucc, int *currdft);

#ifdef __cplusplus
}
#endif

#endif /* OTP_INTERFACE_H_*/

