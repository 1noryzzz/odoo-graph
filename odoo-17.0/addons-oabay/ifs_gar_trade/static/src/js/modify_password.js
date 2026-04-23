/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {
  jsonrpc
} from "@web/core/network/rpc_service";

publicWidget.registry.modifyPasswordWidget = publicWidget.Widget.extend({
  selector: '#modifyPasswordForm',
  events: {
    'click #pwd_confirm_btn': '_onModifyPassword',
    'click .know-btn': '_onKnowBtn',
    'keyup input[name="password"]': '_keyup',
    'keyup input[name="confirm_password"]': '_keyup',
  },

  _onModifyPassword: function () {
    const password = $("input[name='password']").val();
    const confirm_password = $("input[name='confirm_password']").val();
    const merchant_code = $('#merchant_code').text();
    if (password !== confirm_password) {
      $("#setting_error_tips").addClass('cashier_mask');
      $("#setting_error_tips").removeClass('input_no_display');
      return
    }
    jsonrpc('/openapi/trade/modify_password', {
      merchant_code: merchant_code,
      password: password
    }).then((result) => {
      $("#setting_pwd_tips").addClass('setting_pwd_tips');
      $("#setting_pwd_tips").removeClass('input_no_display');
      $('.validate_error_text_info').text(result.msg);
      if (result.is_success) {
        $('img[name="setting_img"]').attr('src', '/ifs_gar_trade/static/img/agree.png');
      } else {
        $('img[name="setting_img"]').attr('src', '/ifs_gar_trade/static/img/disagree.png');
      }
      setTimeout(function () {
        $("#setting_pwd_tips").addClass('input_no_display');
        $("#setting_pwd_tips").removeClass('setting_pwd_tips');
        console.log('跳转到小程序');
        uni.reLaunch({
          url: '/pages/home/index'
        });
      }, 2000);
    });
  },

  _onKnowBtn: function () {
    console.log('click=============');
    uni.navigateBack();
  },

  _keyup: function () {
    const password = $("input[name='password']").val();
    const confirm_password = $("input[name='confirm_password']").val();
    if (password && confirm_password) {
      $('#pwd_confirm_btn').prop('disabled', false);
    } else {
      $('#pwd_confirm_btn').prop('disabled', true);
    }
  },

});