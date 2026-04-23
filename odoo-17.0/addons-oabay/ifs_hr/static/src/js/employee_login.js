/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.loginUserName = publicWidget.Widget.extend({
  selector: '.login-name',
  events: {
    'change': '_onLoginNameChange',
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

  _onLoginNameChange: function (ev) {
    ev.preventDefault();
    var login_name = this.$el.val();
    jsonrpc('/ifs_hr/check_need_otp', {
      login_name: login_name
    }).then((rst) => {
      if (rst) {
        $('#otp_check').val('1');
        $('#ot_password').removeClass('ot_password_invisible');
        $('#ot_password').prop('required', true)
      } else {
        $('#otp_check').val('0');
        $('#ot_password').addClass('ot_password_invisible');
        $('#ot_password').prop('required', false)
      }
    });
  },
});

publicWidget.registry.MobileLoginBtn = publicWidget.Widget.extend({
  selector: '.mobile_login_btn',
  events: {
    'click': 'submit',
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

  submit: function (ev) {
    let is_checked = $('#is_read').prop('checked')
    if (is_checked) {
      return true;
    }

    this.displayNotification({
      message: '请先阅读并同意 《用户协议》 《隐私政策》并勾选',
      type: 'warning'
    })

    return false;
  }
});