/** @odoo-module alias=galaxy_tdesign.SidebarMenu **/
import { session } from "@web/session";

export function closeSidebar() {
  $("#closeSidebar").hide();
  $("#openSidebar").show();
  $("#sidebar_panel").css({ 'display': 'none' });

  //remove class in action-manager
  var action_manager = $(".o_action_manager");
  action_manager.removeClass("sidebar_margin");
  action_manager.addClass("sidebar_close");

  //remove class in top_heading
  var top_head = $(".top_heading");
  top_head.removeClass("sidebar_margin");
  top_head.addClass("sidebar_close");
};

export function openSidebar() {
  $("#openSidebar").hide();
  $("#closeSidebar").show();
  $("#sidebar_panel").css({ 'display': 'block' });

  //add class in action-manager
  var action_manager = $(".o_action_manager");
  action_manager.removeClass("sidebar_close");
  action_manager.addClass("sidebar_margin");

  //add class in top_heading
  var top_head = $(".top_heading");
  top_head.removeClass("sidebar_close");
  top_head.addClass("sidebar_margin");
};

$(document).on("click", "#closeSidebar", function (event) {
  closeSidebar();
});
$(document).on("click", "#openSidebar", function (event) {
  openSidebar();
});
$(document).on("click", ".sidebar a", function (event) {
  var menu = $(".sidebar a");
  var $this = $(this);
  var id = $this.data("id");
  $("header").removeClass().addClass(id);
  menu.removeClass("active");
  $this.addClass("active");

  if ($(".top_heading.sidebar_margin").css('margin-left') === '0px') {
    closeSidebar();
  }
});
$(document).on("click", "#appMenu", function (event) {
  if (session.main_menu_style !== 'expandonce') {
    var nextNode = $(this).next();
    var menu_icon = $(this).find("#menu_icon");
    if (nextNode.hasClass("menu_passive")) {
      menu_icon.removeClass("menu_fold");
      nextNode.removeClass("menu_passive");
    } else {
      menu_icon.addClass("menu_fold");
      nextNode.addClass("menu_passive");
    }}
  
});