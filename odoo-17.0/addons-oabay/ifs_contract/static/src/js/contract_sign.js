/** @odoo-module alias=ifs.contract.sign.form **/

import core from 'web.core';
import FormView from 'web.FormView';
import FormController from 'web.FormController';
import FormRenderer from 'web.FormRenderer';
import view_registry from 'web.view_registry';
import { useBus } from "@web/core/utils/hooks";

var BaseSettingRenderer = FormRenderer.extend({
  events: _.extend({}, FormRenderer.prototype.events, {
  }),

  init: function () {
    this._super.apply(this, arguments);
    useBus(this.env.bus, "ifs.contract.info/signed", event => {
        console.log(event);
    });
  },
});

var BaseSettingController = FormController.extend({
  custom_events: _.extend({}, FormController.prototype.custom_events, {
  }),
  init: function () {
    this._super.apply(this, arguments);
    // this.disableAutofocus = true;
    this.renderer.activeSettingTab = this.initialState.context.module;
    // discardingDef is used to ensure that we don't ask twice the user if
    // he wants to discard changes, when 'canBeDiscarded' is called several
    // times "in parallel"
    this.discardingDef = null;
  },

  //--------------------------------------------------------------------------
  // Handlers
  //--------------------------------------------------------------------------

});

var BaseSettingView = FormView.extend({
  jsLibs: [],

  config: _.extend({}, FormView.prototype.config, {
    // Model: BaseSettingsModel,
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
  }),
});

view_registry.add('contract_sign', BaseSettingView);
