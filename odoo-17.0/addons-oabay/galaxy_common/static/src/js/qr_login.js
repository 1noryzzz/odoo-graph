odoo.define('inair_common.qr.login', function (require) {
    "use strict";
  
    var Widget = require('web.Widget');
  
    var QrLogin = Widget.extend({
      className: 'odoo o_qr_login d-print-none',
      events: _.extend({}, Widget.prototype.events, {
        'click .list-group-item-action': '_change_provider_action_clicked',
      }),
  
      init: function (parent, state, options) {
        this._super(parent);
        this.website_domain = options.website_domain;
        this.qr_area_id = options.qr_area_id;
        this.qr_providers = options.qr_providers;
        this.current_provider = options.current_provider;
        this._change_provider_action_clicked = _.debounce(this._change_provider_action_clicked, 300, true);
      },
  
      _change_current_provider: function(provider_action_name) {
        var self = this;
        self.is_found = false;
        $.each(this.qr_providers, function (index, data) {
          if (!self.is_found && (data.action_name) === provider_action_name) {
            self.current_provider = data;
            self.is_found = true;
            self._show_qr_code();
          }
        });
  
        if (!self.is_found && this.qr_providers.length > 0) {
          self.current_provider = this.qr_providers[0];
          self.is_found = true;
          self._show_qr_code();
        }
      },
  
      _change_provider_action_clicked: function (event) {
        event.preventDefault();
        this._change_current_provider($(event.currentTarget).attr('tag'));
      },
  
      _show_qr_code: function () {
        return false;
      },
  
      start: function () {
        var default_provider = window.location.hash;
        if (default_provider === '') {
          default_provider = this.qr_providers[0].action_name;
        } else {
          var param_index = default_provider.indexOf('?');
          default_provider = default_provider.substring(1, param_index === -1 ? 100 : param_index);
        }
        this._change_current_provider(default_provider);
        $('.list-group-item-action').click(this._change_provider_action_clicked.bind(this));
  
        return this._super();
      },
    });
  
    return {
      QrLogin: QrLogin,
    };
  });