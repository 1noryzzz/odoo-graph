/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.phoneCheck = publicWidget.Widget.extend({
  selector: '.reset_password_phone_check',
  events: {
    'click': '_onPhoneCheckClick',
  },

  /**
   * @override
   */
  start() {
    return this._super(...arguments);
  },
  /**
   * @override
   */
  destroy() {
    this._super(...arguments);
  },

  //--------------------------------------------------------------------------
  // Handlers
  //--------------------------------------------------------------------------

  _onPhoneCheckClick: function (ev) {
    ev.preventDefault();
    var login_phone = $('.reset_password_login').val();
    jsonrpc('/ifs_hr/check_login_phone', {
      login_phone: login_phone,
    }).then((rst) => {
      if (rst) {
        $('#phone').attr("disabled", true )
        $('.reset_password_send_checkcode').prop('disabled', false)
        $('.phone_check').addClass('invisible_input_password');
        $('.send_checkcode').removeClass('invisible_input_password');
        $('.checkcode_ckeck').removeClass('invisible_input_password');
      }
    });
  },
});

publicWidget.registry.sendCheckcode = publicWidget.Widget.extend({
  selector: '.reset_password_send_checkcode',
  events: {
    'click': '_onSendCheckcodeClick',
  },

  /**
   * @override
   */
  start() {
    return this._super(...arguments);
  },
  /**
   * @override
   */
  destroy() {
    this._super(...arguments);
  },

  //--------------------------------------------------------------------------
  // Handlers
  //--------------------------------------------------------------------------

  _onSendCheckcodeClick: function (ev) {
    ev.preventDefault();
    var login_phone = $('.reset_password_login').val();
    jsonrpc('/ifs_hr/send_check_code', {
      login_phone: login_phone,
    }).then(() => {
      var timeClock;
      var timer_num = 60;
      $('.reset_password_send_checkcode').prop('disabled', true)
      timeClock = setInterval(function () {
        timer_num--;
        $('.reset_password_send_checkcode').html(timer_num);

        if (timer_num == 0) {
          clearInterval(timeClock);
          $('.reset_password_send_checkcode').html('验证码发送');
          $('.reset_password_send_checkcode').prop('disabled', false)
        }
      }, 1000)
    });
  },
});

publicWidget.registry.CheckcodeCheck = publicWidget.Widget.extend({
  selector: '.reset_password_checkcode_ckeck',
  events: {
    'click': '_onCheckcodeCheckClick',
  },

  /**
   * @override
   */
  start() {
    return this._super(...arguments);
  },
  /**
   * @override
   */
  destroy() {
    this._super(...arguments);
  },

  //--------------------------------------------------------------------------
  // Handlers
  //--------------------------------------------------------------------------

  _onCheckcodeCheckClick: function (ev) {
    ev.preventDefault();
    var login_phone = $('.reset_password_login').val();
    var checkcode = $('.reset_password_checkcode').val();
    jsonrpc('/ifs_hr/check_code_check', {
      login_phone: login_phone,
      checkcode: checkcode,
    }).then((rst) => {
      if (rst) {
        $('.send_checkcode').addClass('invisible_input_password');
        $('.checkcode_ckeck').addClass('invisible_input_password');
        $('.input_password').removeClass('invisible_input_password');
        $('.input_password_again').removeClass('invisible_input_password');
        $('.galaxy-btn-primary').removeClass('invisible_input_password');
      }
    });
  },
});