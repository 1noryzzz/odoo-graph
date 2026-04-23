/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

const PAYMENT_CODE = "payment_code";
const MERCHANT_CODE = "merchant_code";
const TOKEN = "token";

// 收银台起始页
publicWidget.registry.cashierTemplateWidget = publicWidget.Widget.extend({
  selector: '#idcardForm',
  events: {
    'click .cashier-btn': '_onPasswordInput',
    'click .close_img': '_onCloseInput',
    'click #cashier_expand': '_onExpand',
    'click #quota_content_null': '_onApplyGuide',
    'click #quota_content_has': '_onBindAccount',
    'click .wechat_pay': '_onWechatPay',
    'click .know-btn': '_onKnowBtn',
  },

  start() {
    let merchant_code = $('#merchantCode').text();
    sessionStorage.setItem(MERCHANT_CODE, merchant_code);

    let payment_code = $('#paymentCode').text();
    sessionStorage.setItem(PAYMENT_CODE, payment_code);

    $('.cashier-btn').click();
  },

  _onCloseInput: function () {
    var password_input = $('#password_input');

    $('#password-input-1').val('');
    $('#password-input-2').val('');
    $('#password-input-3').val('');
    $('#password-input-4').val('');
    $('#password-input-5').val('');
    $('#password-input-6').val('');
    $("#error_text").text('');
    password_input.removeClass('input_display');
    password_input.addClass('input_no_display');
  },

  _onPasswordInput: function () {
    var password_input = $('#password_input');
    var digit1 = $('#password-input-1');

    password_input.removeClass('input_no_display');
    password_input.addClass('input_display');
    digit1.prop('disabled', false).focus();
  },

  _onExpand: function () {
    var cashier_expand = $('#cashier_expand');
    var wechat_pay = $('.wechat_pay');

    if (this.degree === 1) {
      cashier_expand.removeClass('cashier_expand');
      wechat_pay.css({
        'display': 'none'
      })
      this.degree = 0;
    } else {
      cashier_expand.addClass('cashier_expand');
      wechat_pay.css({
        'display': 'flex'
      })
      this.degree = 1;
    }
  },

  _onApplyGuide: function () {
    // window.location.href = "/bfp_transition/entry_guide";
  },

  _onBindAccount: function () {
    var original_info = JSON.parse($('#original_info').val())
    // window.location.href = "/bfp_transition/account_binding?original_info=" + original_info;
  },

  _onWechatPay: function () {
    // 直接跳转到微信支付
    console.log('weeeeeeeeeexxxxx')
  },

  _onKnowBtn: function () {
    uni.navigateBack();
  },

});

// 密码输入框
publicWidget.registry.passwordInputWidget = publicWidget.Widget.extend({
  selector: '.password_input_wrap',

  start() {
    var password = {}
    $(document).ready(function () {
      // 监听输入事件，自动将光标移到下一个输入框
      $('.password-input').on('input', function () {
        if (this.value.length === this.maxLength) {
          password[parseInt($(this).attr('id').split('-')[2])] = $(this).val()
          $(this).val('●')
          if (parseInt($(this).attr('id').split('-')[2]) !== 6) {
            $(this).prop('disabled', true)
            $(this).next('.password-input').prop('disabled', false).focus();
          }
        }
      });

      // 监听删除事件，自动将光标前移
      $('.password-input').on('keydown', function (e) {
        if (e.keyCode === 8 && this.value.length === 0) {
          if (parseInt($(this).attr('id').split('-')[2]) !== 1) {
            password[parseInt($(this).attr('id').split('-')[2]) - 1] = ''
            $(this).prop('disabled', true)
            $(this).prev('.password-input').val('').prop('disabled', false).focus();
          }
        } else if (e.keyCode === 8 && parseInt($(this).attr('id').split('-')[2]) === 6) {
          password[6] = ''
          $("#error_text").text('');
        }
      });

      // 当第六个输入框输入完毕后，发送请求
      $('#password-input-6').on('input', function (e) {
        if (e.keyCode !== 8 && this.value.length !== 0) {
          let data = Object.values(password).join('');
          let merchant_code = sessionStorage.getItem(MERCHANT_CODE);
          let payment_code = sessionStorage.getItem(PAYMENT_CODE);

          jsonrpc('/openapi/payment/verify_password', {
            merchant_code,
            password: data
          }).then((res) => {
            if (res.is_success) {
              jsonrpc('/openapi/payment/result', {
                payment_code
              }).then((resp) => {
                const urlType = resp.url_type;
                const afterPayment = resp.after_payment;
                if (urlType) {
                  if (urlType === "wxmini") {
                    uni.reLaunch({
                      url: afterPayment
                    });
                  } else {
                    window.location.href = afterPayment;
                  }
                } else {
                  window.location.href = `/openapi/page/error?err_msg=${resp.alert_msg}`;
                }
              });

            } else {
              $("#error_text").text(res.msg);
              $("#error_text").addClass('error_text');
            }
          });
        }
      });
    });

    return this._super(...arguments);
  },
});

// publicWidget.registry.mainResultWidget = publicWidget.Widget.extend({
//   selector: '.main_result',

//   start() {
//     let urlType = $('#urlType').text();
//     let afterPayment = $('#afterPayment').text();
//     if (urlType === 'wxmini') {
//       uni.navigateTo({
//         url: afterPayment
//       });
//     } else {
//       window.location.href = afterPayment;
//     }
//   }

// });

publicWidget.registry.forgetPwdWidget = publicWidget.Widget.extend({
  selector: '#forgetPwd',
  events: {
    click: '_onClick'
  },

  _onClick() {
    let merchant_code = sessionStorage.getItem(MERCHANT_CODE);

    jsonrpc('/openapi/merchant/chpwd/tips', {
      merchant_code
    }).then((res) => {
      if (res.is_success) {
        window.location.href = res.change_url
      } else {
        window.location.href = '/openapi/page/error?err_msg=' + res.alert_msg
      }
    });
  }
});

publicWidget.registry.iconCloseWidget = publicWidget.Widget.extend({
  selector: '.icon-close',
  events: {
    click: '_onClickClose'
  },

  _onClickClose() {
    $('#qrMask').removeClass('display');
  }
});

publicWidget.registry.informShareBtnWidget = publicWidget.Widget.extend({
  selector: '#informShareBtn',
  events: {
    click: '_onClick'
  },

  start() {
    let merchant_code = $('#merchantCode').text();
    sessionStorage.setItem(MERCHANT_CODE, merchant_code);

    let token = $('#token').text();
    sessionStorage.setItem(TOKEN, token);
  },

  _onClick() {
    let token = sessionStorage.getItem(TOKEN);

    jsonrpc('/openapi/merchant/generate/qrcode', {
      token
    }).then((res) => {
      if (res.is_success) {
        $('#qrcodeImg').attr('src', `data:image/png;base64,${res.qrCodeSrc}`);
        $('#qrMask').addClass('display');
      } else {
        window.location.href = `/openapi/page/error?err_msg=${res.alert_msg}`
      }
    });
  }
});

publicWidget.registry.informNextBtnWidget = publicWidget.Widget.extend({
  selector: '#informNextBtn',
  events: {
    click: '_onClick'
  },

  start() {
    let merchant_code = $('#merchantCode').text();
    sessionStorage.setItem(MERCHANT_CODE, merchant_code);

    let token = $('#token').text();
    sessionStorage.setItem(TOKEN, token);
  },

  _onClick() {
    let token = sessionStorage.getItem(TOKEN);
    window.location.href = `/openapi/payment/ocr/matchFace?token=${token}`;
  }
});

publicWidget.registry.faceFailRecheckBtnWidget = publicWidget.Widget.extend({
  selector: '#face_fail_recheck_btn',
  events: {
    'click': '_recheck',
  },

  _recheck: function () {
    let token = sessionStorage.getItem(TOKEN);
    window.location.href = `/openapi/payment/ocr/matchFace?token=${token}`;
  },
});

publicWidget.registry.chpwdConfirmBtnWidget = publicWidget.Widget.extend({
  selector: '#chpwdConfirmBtn',
  events: {
    click: '_onClick'
  },

  _onClick() {
    const newPassword = $("input[name='newPassword']").val();
    const newPasswordConfirm = $("input[name='newPasswordConfirm']").val();

    if (newPassword === "") {
      $("#trade_chpwd_tips").addClass('trade_chpwd_tips');
      $("#trade_chpwd_tips").removeClass('input_no_display');
      $('#trade_chpwd_tips .validate_text_info').text('新密码不能为空');
      $("#chpwdConfirmBtn").prop('disabled', true)
      setTimeout(function () {
        $("#trade_chpwd_tips").addClass('input_no_display');
        $("#trade_chpwd_tips").removeClass('trade_chpwd_tips');
        $("#chpwdConfirmBtn").prop('disabled', false)
      }, 3000);
    } else if (newPasswordConfirm === "") {
      $("#trade_chpwd_tips").addClass('trade_chpwd_tips');
      $("#trade_chpwd_tips").removeClass('input_no_display');
      $('#trade_chpwd_tips .validate_text_info').text('确认密码不能为空');
      $("#chpwdConfirmBtn").prop('disabled', true)
      setTimeout(function () {
        $("#trade_chpwd_tips").addClass('input_no_display');
        $("#trade_chpwd_tips").removeClass('trade_chpwd_tips');
        $("#chpwdConfirmBtn").prop('disabled', false)
      }, 3000);
    } else if (newPassword !== newPasswordConfirm) {
      $("#trade_chpwd_tips").addClass('trade_chpwd_tips');
      $("#trade_chpwd_tips").removeClass('input_no_display');
      $('#trade_chpwd_tips .validate_text_info').text('密码不一致');
      $("#chpwdConfirmBtn").prop('disabled', true)
      setTimeout(function () {
        $("#trade_chpwd_tips").addClass('input_no_display');
        $("#trade_chpwd_tips").removeClass('trade_chpwd_tips');
        $("#chpwdConfirmBtn").prop('disabled', false)
      }, 3000);
    } else {
      const params = new URLSearchParams(window.location.search);
      let token = params.get('token')
      window.location.href = "/openapi/payment/set_password?token=" + token + "&password=" + newPassword;
    }
  }
});

publicWidget.registry.informWidget = publicWidget.Widget.extend({
  selector: '#inform',
  events: {},

  start() {
    uni.getEnv((res) => {
      if (!res.miniprogram) {
        $("#nextText").removeAttr("hidden");
        $("#informNextBtn").removeAttr("hidden");
      }
    });
  }
});

publicWidget.registry.tradeChpwdTipsWidget = publicWidget.Widget.extend({
  selector: '#trade_chpwd_tips',
  events: {
    click: '_onClick'
  },

  _onClick() {
    $("#trade_chpwd_tips").addClass('input_no_display');
    $("#trade_chpwd_tips").removeClass('trade_chpwd_tips');
    $("#chpwdConfirmBtn").prop('disabled', false)
  }
});

// 收银台测试-前置信息补充
publicWidget.registry.TestContainer = publicWidget.Widget.extend({
  selector: '.test_container',
  events: {
    'click #skip_btn': '_onSkipBtn',
  },

  _onSkipBtn: function () {
    var access_token = $('#access_token').val();
    var merchant_code = $('#merchant_code').val();
    var merchant_credit_no = $('#merchant_credit_no').val();
    var pay_order_code = $('#pay_order_code').val();
    var amount = $('#amount').val();
    var longitude = $('#longitude').val();
    var latitude = $('#latitude').val();
    var supplier_code1 = $('#supplier_code1').val();
    var order_code1 = $('#order_code1').val();
    var order_amount1 = $('#order_amount1').val();
    var supplier_code2 = $('#supplier_code2').val();
    var order_code2 = $('#order_code2').val();
    var order_amount2 = $('#order_amount2').val();
    jsonrpc('/bfp_transition/skip_cashier', {
      access_token: access_token,
      merchant_code: merchant_code,
      merchant_credit_no: merchant_credit_no,
      pay_order_code: pay_order_code,
      amount: amount,
      longitude: longitude,
      latitude: latitude,
      supplier_code1: supplier_code1,
      order_code1: order_code1,
      order_amount1: order_amount1,
      supplier_code2: supplier_code2,
      order_code2: order_code2,
      order_amount2: order_amount2,
    }).then((result) => {
      if (result) {
        window.location.href = "/bfp_transition/pay_cashier?pay_data=" + result.pay_data;
      }
    });
  },
});