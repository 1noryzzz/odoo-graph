odoo.define('wechat.integrate.buttons', function (require) {
  "use strict";

  var core = require('web.core');
  var ListController = require('web.ListController');
  var KanbanController = require('web.KanbanController');
  var ListView = require('web.ListView');
  var KanbanView = require('web.KanbanView');
  var viewRegistry = require('web.view_registry');

  var _t = core._t;

  var _call_wechat_sync = function (self, start_index) {
    var state = self.model.get(self.handle);
    return self._rpc({
      model: self.modelName,
      method: 'wechat_sync',
      args: [start_index],
      kwargs: {
        context: state.getContext()
      },
    }).then((rst) => {
      self.displayNotification(rst);
      if (rst.type === 'success') {
        self.trigger_up('reload');
      } else if (rst.action === 'continue') {
        self.trigger_up('reload');
        return _call_wechat_sync(self, start_index + rst.synced_line);
      }
    });
  };

  var WechatIntegrateListController = ListController.extend({
    buttons_template: 'WechatIntegrateListView.buttons',
    events: _.extend({}, ListController.prototype.events, {
      'click .o_list_button_sync': '_onWechatSync',
    }),

    /*
     * @override
     */
    renderButtons: function ($node) {
      if ($node && $node.prop('class') === 'modal-footer') {
        return;
      }
      this._super.apply(this, arguments);
    },

    _onWechatSync: function (event) {
      var self = this;
      return _call_wechat_sync(self, 0);
    },
  });

  var WechatIntegrateListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
      Controller: WechatIntegrateListController,
    }),

    /**
     * @override
     */
    _extractParamsFromAction: function (action) {
      var params = this._super.apply(this, arguments);
      params.hasActionMenus = (params.hasActionMenus || action.target === 'new');
      return params;
    },
  });

  viewRegistry.add('wechat_integrate_tree', WechatIntegrateListView);

  var WechatIntegrateKanbanController = KanbanController.extend({
    buttons_template: 'WechatIntegrateKanbanView.buttons',
    events: _.extend({}, KanbanController.prototype.events, {
      'click .o-kanban-button-sync': '_onWechatSync',
    }),

    /*
     * @override
     */
    renderButtons: function ($node) {
      if ($node && $node.prop('class') === 'modal-footer') {
        return;
      }
      this._super.apply(this, arguments);
      if (!this.quickCreateEnabled) {
        this.$buttons.find('.o-kanban-button-new').hide();
        this.$buttons.find('.o-kanban-button-sync').removeClass('btn-secondary')
        this.$buttons.find('.o-kanban-button-sync').addClass('btn-primary')
      }
    },

    _onWechatSync: function (event) {
      var self = this;
      return _call_wechat_sync(self, 0);
    },
  });

  var WechatIntegrateKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
      Controller: WechatIntegrateKanbanController,
    }),
  });

  viewRegistry.add('wechat_integrate_kanban', WechatIntegrateKanbanView);
});