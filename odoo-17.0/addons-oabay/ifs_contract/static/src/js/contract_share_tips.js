/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

const SIGN_TOKEN = "sign_token";

// 收银台起始页
publicWidget.registry.contractShareLinkWidget = publicWidget.Widget.extend({
  selector: '.sign_before_main',
  events: {
    'click .share-contract-btn': '_onShowTips',
    'click .icon-close': '_onCloseTips',
  },

  start() {
    const token = $('#token').val();
    sessionStorage.setItem(SIGN_TOKEN, token);
  },

  _onShowTips: function () {
    const token = $('#token').val();
    jsonrpc('/contract/generate/share_qrcode', {
      token
    }).then((res) => {
      if (res.is_success) {
        this.copyToClipboard(res.url);
        $('#qrcodeImg').attr('src', `data:image/png;base64,${res.qrCodeSrc}`);
        $('.share_tip_display').addClass('active');
      }
    });
  },

  _onCloseTips: function () {
    $('.share_tip_display').removeClass('active');
  },

  async copyToClipboard(content) {
    const tips = "链接已复制到剪贴板";

    const self = this;
    const clipboardObj = navigator.clipboard;
    if (clipboardObj) {
      try {
        await clipboardObj.writeText(content);
      } catch (err) {
        if (err.name === "NotAllowedError") {
          self.toast("复制到剪贴板失败,请先授予读写剪贴板的权限");
        }

        return;
      }
      self.toast(tips);

    } else {
      const input = document.createElement('input');
      input.setAttribute('readonly', 'readonly');
      input.setAttribute('value', content);
      document.body.appendChild(input);
      input.setSelectionRange(0, 9999);
      input.select();
      let isSuccess = document.execCommand('copy');
      document.body.removeChild(input);
      if (isSuccess) {
        self.toast(tips);
      }
    }
  },

  toast(message) {
    this.showToast(message);
    setTimeout(() => this.hideToast(), 1500);
  },

  showToast(message) {
    $(".toast").text(message);
    $(".toast").addClass("show");
  },

  hideToast() {
    $(".toast").removeClass("show");
  }
});