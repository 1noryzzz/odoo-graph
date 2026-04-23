/** @odoo-module alias=ifs.gar.invite.franchisee **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.idcardImgWidget = publicWidget.Widget.extend({
  selector: '.n_idcard_container',
  events: {
    'click .idcard_img': '_selectIdcardImg',
  },

  /**
   * @override
   */
  start() {
    var self = this;
    var $idcard_front_image = $("input[name='idcard_front_image']");
    var $idcard_back_image = $("input[name='idcard_back_image']");

    $idcard_front_image.change(function () {
      if ($idcard_back_image[0].files[0]) {
        self._retrieve_idcard_info();
      }

      var windowURL = window.URL || window.webkitURL;
      var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
      $('#idcard_front_image').attr("src", dataURL);
    });

    $idcard_back_image.change(function () {
      if ($idcard_front_image[0].files[0]) {
        self._retrieve_idcard_info();
      }

      var windowURL = window.URL || window.webkitURL;
      var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
      $('#idcard_back_image').attr("src", dataURL);
    });

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

  _retrieve_idcard_info: function () {
    $.ajax({
      url: '/ifs_gar_invite/new/franchisee/register/retrieve_idcard',
      data: new FormData($('#idcardForm')[0]),
      type: "POST",
      contentType: false,
      processData: false,
      success: function (data) {
        if (data.indexOf('error') != -1) {
          alert($.parseJSON(data).errorMsg);
        } else {
          let idcard_info = $.parseJSON(data)
          $("input[name='name']").attr('value', idcard_info.name)
          $("input[name='gender']").attr('value', idcard_info.gender)
          $("input[name='birthday']").attr('value', idcard_info.birthday)
          $("input[name='card_no']").attr('value', idcard_info.card_no)
          $("input[name='family_address']").attr('value', idcard_info.family_address)
          $("input[name='idcard_expiry_date']").attr('value', idcard_info.idcard_expiry_date)
          $("input[name='authority']").attr('value', idcard_info.authority)
  
          $(".galaxy-btn-primary").removeAttr("disabled")
        }
      },
    })
  },

  _selectIdcardImg: function (e) {
    var $idcard_front_image = $("input[name='idcard_front_image']");
    var $idcard_back_image = $("input[name='idcard_back_image']");

    if ($(e.currentTarget).attr("id") == 'idcard_front_image') {
      $idcard_front_image.click();
    } else if ($(e.currentTarget).attr("id") == 'idcard_back_image') {
      $idcard_back_image.click();
    }
  },
});