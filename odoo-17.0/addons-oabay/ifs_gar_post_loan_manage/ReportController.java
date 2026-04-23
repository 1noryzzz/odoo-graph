package com.oabay.web.controller.tool;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.oabay.common.core.domain.R;
import com.oabay.common.utils.http.HttpUtils;
import com.oabay.common.utils.ip.IpUtils;
import com.oabay.common.utils.StringUtils;

/**
 * 报表工具控制器
 * <p>
 * 专门服务于 oabay-ui/src/views/tool/report/index.vue 页面
 * 提供客户端IP获取和征信查询接口功能
 * </p>
 *
 * @author oabay
 */
@RestController
@RequestMapping("/tool/report")
public class ReportController
{
    /** 日志记录器 */
    private static final Logger log = LoggerFactory.getLogger(ReportController.class);

    /** 默认API环境地址 - 测试环境 */
    private static final String DEFAULT_API_HOST = "http://47.117.247.249:8080";

    /** 默认API接口路径 */
    private static final String DEFAULT_API_PATH = "/credit/query";

    /** 默认合作方编码 */
    private static final String DEFAULT_PARTNER_CODE = "yabao";

    /**
     * 获取客户端真实IP地址
     * <p>
     * 用于前端页面显示当前客户端的出口IP地址
     * 支持多级反向代理场景，能够正确获取真实客户端IP
     * </p>
     *
     * @param request HTTP请求对象，用于获取客户端IP
     * @return 统一响应结果，包含客户端IP地址
     */
    @GetMapping("/current-ip")
    public R<String> getCurrentIp(HttpServletRequest request)
    {
        log.info("收到获取客户端IP请求, 请求路径: {}", request.getRequestURI());

        // 调用工具类获取真实客户端IP（支持代理场景）
        String clientIp = IpUtils.getIpAddr(request);
        log.info("获取到客户端IP: {}", clientIp);

        return R.ok(clientIp, "获取成功");
    }

    /**
     * 征信查询接口
     * <p>
     * 实现RSA+AES混合加密的征信查询功能：
     * 1. 生成随机AES-256密钥
     * 2. 使用AES密钥加密业务数据
     * 3. 使用服务端RSA公钥加密AES密钥
     * 4. 使用客户端RSA私钥进行签名
     * 5. 转发加密请求到征信API
     * 6. 返回API响应结果
     * </p>
     *
     * @param params 前端传来的查询参数，包含：
     *               - privateKey: 客户端RSA私钥（用于签名）
     *               - publicKey: 服务端RSA公钥（用于加密AES密钥）
     *               - apiHost: API地址（可选，有默认值）
     *               - apiPath: API路径（可选，有默认值）
     *               - partnerCode: 合作方编码（可选，有默认值）
     *               - name: 姓名
     *               - certtype: 证件类型
     *               - certno: 证件号码
     *               - qryreason: 查询原因
     *               - qrystrategy: 查询策略
     *               - clientip: 客户端IP
     * @return 统一响应结果，包含征信API的响应数据
     */
    @PostMapping("/credit/query")
    public R<Object> creditQuery(@RequestBody JSONObject params)
    {
        log.info("收到征信查询请求, 参数: {}", params);

        try
        {
            // ========== 1. 获取配置参数 ==========
            // 从请求参数中获取加密所需的密钥和API配置
            String privateKeyStr = params.getString("privateKey");     // 客户端RSA私钥
            String publicKeyStr = params.getString("publicKey");       // 服务端RSA公钥
            String apiHost = params.getString("apiHost");              // API地址
            String apiPath = params.getString("apiPath");              // API路径
            String partnerCode = params.getString("partnerCode");       // 合作方编码

            // ========== 2. 参数校验 ==========
            // 密钥为必填项，若未提供则返回错误
            if (StringUtils.isAnyBlank(privateKeyStr, publicKeyStr))
            {
                log.error("缺少必填参数：客户端RSA私钥或服务端RSA公钥");
                return R.fail("缺少必填参数：客户端RSA私钥或服务端RSA公钥");
            }

            // API配置使用默认值（当前端未提供时）
            apiHost = StringUtils.isBlank(apiHost) ? DEFAULT_API_HOST : apiHost;
            apiPath = StringUtils.isBlank(apiPath) ? DEFAULT_API_PATH : apiPath;
            partnerCode = StringUtils.isBlank(partnerCode) ? DEFAULT_PARTNER_CODE : partnerCode;

            // ========== 3. 获取业务参数 ==========
            String name = params.getString("name");                     // 姓名
            String certtype = params.getString("certtype");           // 证件类型
            String certno = params.getString("certno");               // 证件号码
            String qryreason = params.getString("qryreason");        // 查询原因
            String qrystrategy = params.getString("qrystrategy");    // 查询策略
            String clientip = params.getString("clientip");          // 客户端IP

            // ========== 4. 业务参数校验 ==========
            // 姓名和证件号码为必填项
            if (StringUtils.isAnyBlank(certno, name))
            {
                log.error("缺少必填业务参数：姓名或证件号码");
                return R.fail("缺少必填参数");
            }

            // ========== 5. 构建业务数据 ==========
            // 构造发送给征信API的业务数据JSON
            JSONObject businessData = new JSONObject();
            businessData.put("certno", certno);                                      // 证件号码
            businessData.put("certtype", StringUtils.isBlank(certtype) ? "0" : certtype);  // 证件类型，默认身份证
            businessData.put("name", name);                                          // 姓名
            businessData.put("qryreason", StringUtils.isBlank(qryreason) ? "02" : qryreason);  // 查询原因，默认贷款审批
            businessData.put("qrystrategy", StringUtils.isBlank(qrystrategy) ? "21" : qrystrategy);  // 查询策略，默认标准查询
            businessData.put("clientip", StringUtils.isBlank(clientip) ? IpUtils.getIpAddr() : clientip);  // 客户端IP

            String businessDataJson = businessData.toJSONString();
            log.info("业务数据JSON: {}", businessDataJson);

            // ========== 6. AES加密 ==========
            // 生成随机AES-256密钥，用于加密业务数据
            KeyGenerator keyGen = KeyGenerator.getInstance("AES");
            keyGen.init(256);  // AES-256位密钥
            SecretKey aesKey = keyGen.generateKey();
            byte[] aesKeyBytes = aesKey.getEncoded();

            // 使用 AES 密钥加密业务数据
            byte[] encryptedData = aesEncrypt(businessDataJson, aesKeyBytes);
            String encryptedDataBase64 = encodeBase64(encryptedData);

            // ========== 7. RSA 加密 AES 密钥 ==========
            // 使用服务端 RSA 公钥加密 AES 密钥，确保 AES 密钥传输安全
            byte[] encryptedAesKey = rsaEncrypt(aesKeyBytes, publicKeyStr);
            String encryptedAesKeyBase64 = encodeBase64(encryptedAesKey);

            // ========== 8. RSA 数字签名 ==========
            // 使用客户端 RSA 私钥对原始业务数据 JSON 进行签名，确保数据完整性
            byte[] signatureBytes = rsaSign(businessDataJson.getBytes(StandardCharsets.UTF_8), privateKeyStr);
            String signatureBase64 = encodeBase64(signatureBytes);

            // ========== 9. 构建最终请求体 ==========
            // 构造符合征信API规范的请求参数
            JSONObject requestBody = new JSONObject();
            requestBody.put("aesKey", encryptedAesKeyBase64);     // 加密后的AES密钥
            requestBody.put("data", encryptedDataBase64);         // 加密后的业务数据
            requestBody.put("signature", signatureBase64);        // 数据签名
            requestBody.put("partnerCode", partnerCode);          // 合作方编码
            requestBody.put("capabilityCode", "shentong");        // 数据签名

            String requestJson = requestBody.toJSONString();
            String apiUrl = apiHost + apiPath;  // 完整API地址
            log.info("发送到征信API的请求: {}", requestJson);
            log.info("API地址: {}", apiUrl);

            // ========== 10. 发送请求到征信API ==========
            String response = HttpUtils.sendPost(apiUrl, requestJson, "application/json");
            log.info("征信API响应: {}", response);

            // ========== 11. 处理响应 ==========
            if (StringUtils.isBlank(response))
            {
                log.error("征信API响应为空");
                return R.fail("征信API响应为空");
            }

            // 解析API响应并返回
            JSONObject responseMap = JSON.parseObject(response);

            // 返回结果包含响应数据、加密后的请求体和解析后的征信数据
            JSONObject result = new JSONObject();
            result.put("response", responseMap);
            result.put("requestJson", requestJson);

            // 解析 response.data.data 中的内嵌JSON，取其中的data字段
            try
            {
                String innerDataStr = responseMap.getJSONObject("data") != null ? responseMap.getJSONObject("data").getString("data") : null;
                if (StringUtils.isNotBlank(innerDataStr))
                {
                    JSONObject innerData = JSON.parseObject(innerDataStr);
                    result.put("creditData", innerData.get("data"));
                }
            }
            catch (Exception e)
            {
                log.warn("解析征信数据内嵌JSON失败", e);
            }

            return R.ok(result, "查询成功");
        }
        catch (Exception e)
        {
            // 捕获加密/网络等异常，记录日志并返回错误信息
            log.error("征信查询异常", e);
            return R.fail("征信查询异常: " + e.getMessage());
        }
    }

    /**
     * AES加密
     * <p>
     * 使用AES/ECB/PKCS5Padding模式对数据进行加密
     * AES是一种对称加密算法，加密效率高，适合加密大量数据
     * </p>
     *
     * @param data 待加密的字符串数据
     * @param key  AES密钥字节数组
     * @return 加密后的字节数组
     * @throws Exception 加密过程中的异常
     */
    private byte[] aesEncrypt(String data, byte[] key) throws Exception
    {
        // 创建AES密钥规范
        SecretKeySpec keySpec = new SecretKeySpec(key, "AES");
        // 创建AES加密器，ECB模式 + PKCS5填充
        Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
        // 初始化为加密模式
        cipher.init(Cipher.ENCRYPT_MODE, keySpec);
        // 执行加密
        return cipher.doFinal(data.getBytes("UTF-8"));
    }

    /**
     * RSA公钥加密
     * <p>
     * 使用服务端RSA公钥加密AES密钥
     * RSA是非对称加密算法，用于安全传输对称密钥
     * 只有持有对应私钥的服务端才能解密获取AES密钥
     * </p>
     *
     * @param data        待加密的数据（这里是AES密钥）
     * @param publicKeyStr Base64编码的服务端RSA公钥字符串
     * @return 加密后的字节数组
     * @throws Exception 加密过程中的异常
     */
    private byte[] rsaEncrypt(byte[] data, String publicKeyStr) throws Exception
    {
        // 解码Base64格式的公钥
        byte[] keyBytes = Base64.getDecoder().decode(publicKeyStr);
        // 创建X509编码密钥规范
        X509EncodedKeySpec spec = new X509EncodedKeySpec(keyBytes);
        // 创建RSA密钥工厂
        KeyFactory factory = KeyFactory.getInstance("RSA");
        // 生成公钥对象
        PublicKey publicKey = factory.generatePublic(spec);
        // 创建RSA加密器，PKCS1Padding填充
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        // 初始化为加密模式
        cipher.init(Cipher.ENCRYPT_MODE, publicKey);
        // 执行加密
        return cipher.doFinal(data);
    }

    /**
     * RSA私钥签名
     * <p>
     * 使用客户端RSA私钥对加密数据进行签名
     * 确保数据的完整性和不可否认性
     * 服务端可用对应的公钥验证签名
     * </p>
     *
     * @param data           待签名的数据（加密后的业务数据）
     * @param privateKeyStr  Base64编码的客户端RSA私钥字符串
     * @return 签名后的字节数组
     * @throws Exception 签名过程中的异常
     */
    private byte[] rsaSign(byte[] data, String privateKeyStr) throws Exception
    {
        // 解码Base64格式的私钥
        byte[] keyBytes = Base64.getDecoder().decode(privateKeyStr);
        // 创建PKCS8编码密钥规范
        PKCS8EncodedKeySpec spec = new PKCS8EncodedKeySpec(keyBytes);
        // 创建RSA密钥工厂
        KeyFactory factory = KeyFactory.getInstance("RSA");
        // 生成私钥对象
        PrivateKey privateKey = factory.generatePrivate(spec);
        // 创建签名对象，使用SHA256WithRSA算法
        Signature signature = Signature.getInstance("SHA256WithRSA");
        // 初始化为签名模式
        signature.initSign(privateKey);
        // 更新要签名的数据
        signature.update(data);
        // 执行签名
        return signature.sign();
    }

    /**
     * Base64 编码工具方法
     * <p>
     * 将字节数组转换为 Base64 编码的字符串
     * 用于消除重复代码
     * </p>
     *
     * @param data 待编码的字节数组
     * @return Base64 编码的字符串
     */
    private String encodeBase64(byte[] data)
    {
        return Base64.getEncoder().encodeToString(data);
    }
}
