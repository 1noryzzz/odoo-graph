/** @odoo-module alias=galaxy.migrate16 **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { loadJS } from "@web/core/assets";

await loadJS("/galaxy_migrate_16/static/src/js/picker.min.js");
// loadJS("/galaxy_migrate_16/static/src/js/picker.css");
var first = []; /* 省，直辖市 */
var second = []; /* 市 */
var third = []; /* 镇 */
var selectedIndex = [0, 0, 0]; /* 默认选中的地区 */
var checked = [0, 0, 0]; /* 已选选项 */
var picker = undefined;
var self = undefined;
publicWidget.registry.picker5 = publicWidget.Widget.extend({
  selector: '.picker5',
  events: {
    'click':'_show'
  },

  /**
   * @override
   */
  start() {
    self = this;
    this._renderStep();
    
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
  async getStateList(){
    await this._rpc({
      route: '/getstate',
      params: {},
      method: 'GET'
    }).then(function (res) {
      first = res;
    });
    if(first.length>0){
      await this._rpc({
        route: '/getcity',
        params: {
          'id': first[0].value
        },
        method: 'GET'
      }).then(function (res) {
        second = res;
      });
    }
    if(second.length>0){
      await this._rpc({
        route: '/getarea',
        params: {
          'id': second[0].value
        },
        method: 'GET'
      }).then(function (res) {
        third = res;
      });
    }
  },

  async getcityList(provinceId) {
    await this._rpc({
      route: '/getcity',
      params: {
        'id': provinceId
      },
      method: 'GET'
    }).then(function (res) {
      second = res;
      picker.refillColumn(1, second);
      picker.refillColumn(2, []);
    });


    if(second.length>0){
      await self.getAreaList(second[0].value)
    }
  },

  async getAreaList(area_id) {
    await this._rpc({
      route: '/getarea',
      params: {
        'id': area_id
      },
      method: 'GET'
    }).then(function (res) {
      third = res;
      picker.refillColumn(2, third);
      picker.scrollColumn(2, 0)
    });
  },

  async _renderStep() {
    await self.getStateList();
    picker = new Picker({
      data: [first, second, third],
      selectedIndex: selectedIndex,
      title: '选择您的职业',
      msg:"填写职业，让对方更了解您"
    });
    
    picker.on('picker.select', function (selectedVal, selectedIndex) {
      var text1 = first[selectedIndex[0]].text;
      var text2 = '';
      var text3 = '';
      if(second.length>0){
        text2 = second[selectedIndex[1]].text;
      }
      if(third.length>0){
        text3 = third[selectedIndex[2]] ? third[selectedIndex[2]].text : '';
      }
    
      var value = text1 + ' ' + text2 + ' ' + text3;
      console.log(value);
      // self.$el.html(value);
      self.$el.val(value);
    });


    
    picker.on('picker.change', function (index, selectedIndex) {
      if (index === 0){
        firstChange();
      } else if (index === 1) {
        secondChange();
      }
    
      function firstChange() {
        checked[0] = selectedIndex;
        var firstCity = first[selectedIndex];
        second=[];
        third=[];
        picker.refillColumn(1, []);
        picker.scrollColumn(1, 0);
        picker.refillColumn(2, []);
        picker.scrollColumn(2, 0);
        self.getcityList(firstCity.value);

      }
    
      function secondChange() {
        self.getAreaList(second[selectedIndex].value);
      }
      
    });
    console.log("picker>>>>",picker);
    // var pickerEl = document.getElementsByClassName('picker')[0];
    // var pickerPanelEl = document.getElementsByClassName('picker-panel')[0]
    // var pickerFooter = document.getElementsByClassName('picker-footer')[0];
    var pickerEl = picker.pickerEl;
    var pickerPanelEl = picker.panelEl;
    var oldTitleEl = pickerPanelEl.children[0];
    var pickerFooter = pickerPanelEl.children[2];
    pickerPanelEl.style.height = 'auto';
    
    pickerFooter.style.height = 'auto';
    var button = document.createElement("button");
    button.appendChild(document.createTextNode('确认'));
    button.classList.add('picker-btn');
     
    button.classList.add('confirm');
    button.classList.add('confirm-hook');

    button.addEventListener('click',function() {
      picker.confirmEl.click();
    })
    pickerFooter.appendChild(button);


    var options = picker.options;
    var newTitleEl = document.createElement("div");
    newTitleEl.classList.add('picker-choose');
    newTitleEl.classList.add('choose-hook');

    var titleBoxEl = document.createElement("div");
    var titleBEl = document.createElement("div");
    var titleMsgEl = document.createElement("div");
    titleBEl.appendChild(document.createTextNode(options.title));
    if(options.msg!=null && options.msg !=undefined){
      titleMsgEl.appendChild(document.createTextNode(options.msg));
    }else{
      titleMsgEl.appendChild(document.createTextNode(""));
    }
    titleBoxEl.appendChild(titleBEl);
    titleBoxEl.appendChild(titleMsgEl);
    newTitleEl.appendChild(titleBoxEl);
    titleBoxEl.classList.add("picker-title-box")
    titleBEl.classList.add("picker-box-title");
    titleMsgEl.classList.add("picker-msg");

    var pickerCencel = document.createElement("i");
    // pickerCencel.classList.add("o_facet_remove");
    pickerCencel.classList.add("picker-close");
    pickerCencel.classList.add("oi");

    pickerCencel.addEventListener("click",function(){
      picker.cancelEl.click();
    })
    newTitleEl.appendChild(pickerCencel);
    newTitleEl.classList.add("picker-panel-box");
    pickerPanelEl.replaceChild(newTitleEl,oldTitleEl);
  },
  _show:function(){
    if(picker != undefined){
      picker.show();
    }
  }
});