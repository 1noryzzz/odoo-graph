odoo.define('wechat.integrate.login', function (require) {
  "use strict";

  var QrLogin = require('inair_common.qr.login').QrLogin;

  QrLogin.include({
    className: 'odoo o_wechat_login d-print-none',

    _show_qr_code: function () {
      if (this._super())
        return true;

      if (this.current_provider.action_name === 'wechat_work') {
        window.WwLogin({
          id: this.qr_area_id,
          appid: this.current_provider.appid,
          agentid: this.current_provider.agentid,
          redirect_uri: this.current_provider.redirect_uri,
          state: this.current_provider.state,
          href: this.website_domain + '/wechat/static/src/css/qr_code.css',
        });
        return true;
      } else if (this.current_provider.action_name === 'wechat_offiaccount') {
        new WxLogin({
          self_redirect: false,
          id: this.qr_area_id,
          appid: this.current_provider.appid,
          scope: this.current_provider.scope,
          redirect_uri: this.current_provider.redirect_uri,
          state: this.current_provider.state,
          style: "black",
          href: this.website_domain + '/wechat/static/src/css/qr_code.css',
        });
        return true;
      }

      return false;
    },
  });
});