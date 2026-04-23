/** @odoo-module alias=ifs.gar.entry **/

import publicWidget from "@web/legacy/js/public/public_widget";

//franchisee
// publicWidget.registry.franchiseeRegisterProgressbar = publicWidget.Widget.extend({
//   selector: '.franchisee_register_main .progressbar',
//   events: {},

//   /**
//    * @override
//    */
//   start() {
//     this._renderStep();

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _renderStep: function () {
//     const self = this;
//     let is_prev_step = true;
//     $.get({
//       url: '/ifs_gar_entry/franchisee/register/steps',
//       success: function (entry_steps) {
//         let $ul = $("<ul></ul>");
//         eval(entry_steps).forEach(function (step) {
//           let $li = $("<li></li>");
//           if (step == self.$el.data("currentStep")) {
//             is_prev_step = false;
//             $li.addClass('current');
//           } else {
//             if (is_prev_step) {
//               $li.addClass('done');
//             }
//           }
//           $ul.append($li);
//         })

//         self.$el.append($ul)
//       }
//     })
//   },
// });


publicWidget.registry.businessLicenseImg = publicWidget.Widget.extend({
  selector: '#business_license',
  events: {
    'click': '_selectBusinessLicense',
  },

  /**
   * @override
   */
  start() {
    $("input[name='business_license']").change(function () {
      $.ajax({
        url: '/ifs_gar_entry/franchisee/register/business_license_ocr',
        data: new FormData($('#businessForm')[0]),
        type: "POST",
        contentType: false,
        processData: false,
        success: function (data) {
          if (data.indexOf('error') != -1) {
            alert($.parseJSON(data).errorMsg);
          } else {
            $(".galaxy-btn-primary").removeAttr("disabled")
          }
        }
      })
      var windowURL = window.URL || window.webkitURL;
      var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
      $('#business_license').attr("src", dataURL)
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

  _selectBusinessLicense: function () {
    $("input[name='business_license']").click();
  },
});


publicWidget.registry.idcardImg = publicWidget.Widget.extend({
  selector: '.o_idcard_container',
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
      url: '/ifs_gar_entry/franchisee/register/retrieve_idcard_info',
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


publicWidget.registry.industrySelect = publicWidget.Widget.extend({
  selector: 'select[name="industry"]',
  events: {
    'change': '_onchangeIndustry',
  },

  /**
   * @override
   */
  start() {
    this._getAllIndustry();

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
  _onchangeIndustry: function () {
    $(".galaxy-btn-primary").removeAttr("disabled")
  },

  _getAllIndustry: function () {
    this.orm.call(
      'ifs.partner.franchisee',
      'get_industry',
      [],
    ).then(function (data) {
      data.forEach(item => $('select[name="industry"]')
        .append("<option value='" + item[0] + "'>" + item[1] + "</option>"))
    });
  },
});

publicWidget.registry.franchiseeSign = publicWidget.Widget.extend({
  selector: '.sign_main .sign',
  events: {
    'click': '_toSignPage',
  },

  /**
   * @override
   */
  start() {
    // this._getAllIndustry();

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

  _toSignPage: function () {
    if ($('.sign_inform_checkbox input[type="checkbox"]').is(':checked')) {
      location.href='/ifs_gar_entry/franchisee/register/to_sign_page';
    } else {
      alert('请先勾选本人已阅读并确认签署');
    }
  },
});


// publicWidget.registry.galaxyBtnPrimary = publicWidget.Widget.extend({
//   selector: '#galaxy_btn_primary',
//   events: {
//     'click': '_getBusinessRegistration',
//   },

//   /**
//    * @override
//    */
//   start() {
//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _getBusinessRegistration: function () {
//     let credit_no = $("input[name='credit_no']").val()
//     if (credit_no) {
//       this._rpc({
//         model: 'res.company.business.registration',
//         method: 'get_business_registration',
//         args: ["", credit_no],
//       }).then(function (data) {
//         $('#ck_credit_no').text(data.credit_no);
//         $('#ck_company_name').text(data.company_name);
//         $('#ck_legal_person').text(data.legal_person);
//         $('#ck_capital').text(data.capital);
//         $('#ck_establish_date').text(data.establish_date);
//         $('#ck_address').text(data.address);

//         $("input[value='发送邀请']").removeAttr("disabled");
//       })
//     }
//   },
// });

// publicWidget.registry.merchantRegisterProgressbar = publicWidget.Widget.extend({
//   selector: '.merchant_register_main .merchant_progressbar',
//   events: {},

//   /**
//    * @override
//    */
//   start() {
//     this._renderStep();

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _renderStep: function () {
//     const self = this;
//     let is_prev_step = true;
//     $.get({
//       url: '/ifs_gar_invite/merchant/register/steps',
//       success: function (entry_steps) {
//         let $ul = $("<ul></ul>");
//         eval(entry_steps).forEach(function (step) {
//           let $li = $("<li></li>");
//           if (step == self.$el.data("currentStep")) {
//             is_prev_step = false;
//             $li.addClass('current');
//           } else {
//             if (is_prev_step) {
//               $li.addClass('done');
//             }
//           }
//           $ul.append($li);
//         })

//         self.$el.append($ul)
//       }
//     })
//   },
// });

// publicWidget.registry.doorhead_picture = publicWidget.Widget.extend({
//   selector: '#doorhead_picture',
//   events: {
//     'click': '_selectPicture',
//   },

//   /**
//    * @override
//    */
//   start() {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").change(function () {
//       $(".galaxy-btn-primary").removeAttr("disabled")
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $("img[name='"+field+"']").attr("src", dataURL)
//     });
//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },
//   _selectPicture: function () {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").click();
//   },
// });

// publicWidget.registry.indoor_picture = publicWidget.Widget.extend({
//   selector: '#indoor_picture',
//   events: {
//     'click': '_selectPicture',
//   },

//   /**
//    * @override
//    */
//   start() {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").change(function () {
//       $(".galaxy-btn-primary").removeAttr("disabled")
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $("img[name='"+field+"']").attr("src", dataURL)
//     });
//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },
//   _selectPicture: function () {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").click();
//   },
// });

// publicWidget.registry.selfie_picture = publicWidget.Widget.extend({
//   selector: '#selfie_picture',
//   events: {
//     'click': '_selectPicture',
//   },

//   /**
//    * @override
//    */
//   start() {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").change(function () {
//       $(".galaxy-btn-primary").removeAttr("disabled")
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $("img[name='"+field+"']").attr("src", dataURL)
//     });
//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },
//   _selectPicture: function () {
//     var field = this.$el.attr('name')
//     $("input[name='"+field+"']").click();
//   },
// });


// publicWidget.registry.merchantBusinessLicenseImg = publicWidget.Widget.extend({
//   selector: '#merchant_business_license',
//   events: {
//     'click': '_selectBusinessLicense',
//   },

//   /**
//    * @override
//    */
//   start() {
//     $("input[type='file']").change(function () {
//       $.ajax({
//         url: '/ifs_gar_invite/merchant/register/business_license_ocr',
//         data: new FormData($('#businessForm')[0]),
//         type: "POST",
//         contentType: false,
//         processData: false,
//         success: function (data) {
//           if (data.indexOf('error') != -1) {
//             alert($.parseJSON(data).errorMsg);
//           } else {
//             $(".galaxy-btn-primary").removeAttr("disabled")
//           }
//         }
//       })
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#merchant_business_license').attr("src", dataURL)
//     });
//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _selectBusinessLicense: function () {
//     $("input[type='file']").click();
//   },
// });

// publicWidget.registry.merchantIdcardImg = publicWidget.Widget.extend({
//   selector: '.merchant_idcard_content',
//   events: {
//     'click .idcard_img': '_selectIdcardImg',
//   },

//   /**
//    * @override
//    */
//   start() {
//     var self = this;
//     var $idcard_front_image = $("input[name='idcard_front_image']");
//     var $idcard_back_image = $("input[name='idcard_back_image']");

//     $idcard_front_image.change(function () {
//       if ($idcard_back_image[0].files[0]) {
//         self._retrieve_idcard_info();
//       }

//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#idcard_front_image').attr("src", dataURL);
//     });

//     $idcard_back_image.change(function () {
//       if ($idcard_front_image[0].files[0]) {
//         self._retrieve_idcard_info();
//       }

//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#idcard_back_image').attr("src", dataURL);
//     });

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _retrieve_idcard_info: function () {
//     $.ajax({
//       url: '/ifs_gar_invite/merchant/register/retrieve_idcard_info',
//       data: new FormData($('#idcardForm')[0]),
//       type: "POST",
//       contentType: false,
//       processData: false,
//       success: function (data) {
//         if (data.indexOf('error') != -1) {
//           alert($.parseJSON(data).errorMsg);
//         } else {
//           let idcard_info = $.parseJSON(data)
//           $("input[name='name']").attr('value', idcard_info.name)
//           $("input[name='gender']").attr('value', idcard_info.gender)
//           $("input[name='birthday']").attr('value', idcard_info.birthday)
//           $("input[name='card_no']").attr('value', idcard_info.card_no)
//           $("input[name='family_address']").attr('value', idcard_info.family_address)
//           $("input[name='idcard_expiry_date']").attr('value', idcard_info.idcard_expiry_date)
//           $("input[name='authority']").attr('value', idcard_info.authority)
  
//           $(".galaxy-btn-primary").removeAttr("disabled")
//         }
//       },
//     })
//   },

//   _selectIdcardImg: function (e) {
//     var $idcard_front_image = $("input[name='idcard_front_image']");
//     var $idcard_back_image = $("input[name='idcard_back_image']");

//     if ($(e.currentTarget).attr("id") == 'idcard_front_image') {
//       $idcard_front_image.click();
//     } else if ($(e.currentTarget).attr("id") == 'idcard_back_image') {
//       $idcard_back_image.click();
//     }
//   },
// });


// publicWidget.registry.merchantSign = publicWidget.Widget.extend({
//   selector: '.merchant_sign_main .merchant_sign',
//   events: {
//     'click': '_toSignPage',
//   },

//   /**
//    * @override
//    */
//   start() {
//     this._getAllIndustry();

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _toSignPage: function () {
//     if ($('.sign_inform_checkbox input[type="checkbox"]').is(':checked')) {
//       location.href='/ifs_gar_invite/merchant/register/to_sign_page';
//     } else {
//       alert('请先勾选本人已阅读并确认签署');
//     }
//   },
// });

// publicWidget.registry.DepositLicenseImg = publicWidget.Widget.extend({
//   selector: '#deposit_license',
//   events: {
//     'click': '_selectDepositLicense',
//   },

//   /**
//    * @override
//    */
//   start() {
//     $("input[name='deposit_license']").change(function () {
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#deposit_license').attr("src", dataURL)
//     });

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _selectDepositLicense: function () {
//     $("input[name='deposit_license']").click();
//   },
// });

// publicWidget.registry.ReceptionImg = publicWidget.Widget.extend({
//   selector: '#reception',
//   events: {
//     'click': '_selectReceptionImg',
//   },

//   /**
//    * @override
//    */
//   start() {
//     $("input[name='reception']").change(function () {
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#reception').attr("src", dataURL)
//     });

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _selectReceptionImg: function () {
//     $("input[name='reception']").click();
//   },
// });

// publicWidget.registry.OfficeAreaImg = publicWidget.Widget.extend({
//   selector: '#office_area',
//   events: {
//     'click': '_selectOfficeAreaImg',
//   },

//   /**
//    * @override
//    */
//   start() {
//     $("input[name='office_area']").change(function () {
//       var windowURL = window.URL || window.webkitURL;
//       var dataURL = windowURL.createObjectURL($(this)[0].files[0]);
//       $('#office_area').attr("src", dataURL)
//     });

//     return this._super(...arguments);
//   },
//   /**
//    * @override
//    */
//   destroy() {
//     this._super(...arguments);
//   },

//   //--------------------------------------------------------------------------
//   // Handlers
//   //--------------------------------------------------------------------------

//   _selectOfficeAreaImg: function () {
//     $("input[name='office_area']").click();
//   },
// });