/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TransitionSuccessBtn = publicWidget.Widget.extend({
  selector: '.pay_return_btn',
  events: {
    'click .transition_success_btn': '_onReturnPay',
    'click .transition_fail_btn': '_onReturnPay',
  },

  _onReturnPay: function () {
    // 跳转到其他页面
    let afterPayment = $('#afterPayment').text();
    let urlType = $('#urlType').text();
    if (urlType === "wxmini") {
      uni.reLaunch({
        url: afterPayment
      });
    } else {
      window.location.href = afterPayment;
    }
  },
});