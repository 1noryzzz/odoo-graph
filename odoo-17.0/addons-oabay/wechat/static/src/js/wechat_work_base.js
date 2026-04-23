odoo.define('wechat.work.base', function (require) {
  "use strict";

  var Widget = require('web.Widget');
  var session = require('web.session');

  var WechatWorkBase = Widget.extend({
    className: 'odoo o_qr_login d-print-none',
    events: _.extend({}, Widget.prototype.events, {
      'click .list-group-item-action': '_change_provider_action_clicked',
    }),

    init: function (parent, state, options) {
      this.options = options;
      wx.config({
        beta: true,
        debug: false,
        appId: this.options.app_id,
        timestamp: this.options.timestamp,
        nonceStr: this.options.nonce_str,
        signature: this.options.signature,
        jsApiList: this.options.apilist
      });
    },

    _retrieve_external_user_id: function () {
      wx.ready(function () {

        wx.invoke('getCurExternalContact', {}, function (res) {
          console.log(res);
          if (res.err_msg == "getCurExternalContact:ok") {
            userId = res.userId;
            alert(userId);
          } else {
            alert(res.err_msg);
          }
        });
      });
    },

    start: function () {
      var self = this;
      wx.ready(function () {
        wx.agentConfig({
          corpid: self.options.app_id,
          agentid: self.options.agent_id,
          timestamp: self.options.timestamp,
          nonceStr: self.options.nonce_str,
          signature: self.options.agent_signature,
          jsApiList: self.options.apilist,
          success: function (res) {
            console.log('invoke getCurExternalContact');
            wx.invoke('getCurExternalContact', {}, function (res) {
              console.log(res);
              if (res.err_msg == "getCurExternalContact:ok") {
                session.rpc('/wechat/work/retrieve_answer_token', {
                  external_user_open_id: res.userId,
                }).then((rst) => {
                  //$('.oe_website_login_container').text('https://www.sztxtr.com/physical/result_detail_dev/?answer_token=' + rst.answer_token);
                  window.location.href='https://www.sztxtr.com/physical/result_detail_dev/?answer_token=' + rst.answer_token;
                  //alert(rst.answer_token);
                });
              } else {
                alert(res.err_msg);
              }
            });
          },
          fail: function (res) {
            console.log(res);
            if (res.errMsg.indexOf('function not exist') > -1) {
              alert('版本过低请升级')
            } else {
              alert(res.errMsg);
            }
          }
        });
      });
    },
  });

  return {
    WechatWorkBase: WechatWorkBase
  };
});