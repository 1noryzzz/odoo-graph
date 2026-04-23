/** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { isBinarySize } from "@web/core/utils/binary";
// import { ImageField } from "@web/views/fields/image/image_field";

// 这里应该是没有用了，因为rawCacheKey已经改成计算属性了
// patch(ImageField.prototype, 'galaxy_common_image_field', {
//     getUrl(previewFieldName) {
//         if (this.state.isValid && this.props.value && isBinarySize(this.props.value)) {
//             // Bugfix: 修复图片在后端被更新时，前端不会更新的问题
//             if (!this.rawCacheKey || this.rawCacheKey !== this.props.record.data.__last_update) {
//                 this.rawCacheKey = this.props.record.data.__last_update;
//             }
//         }
//         return this._super(...arguments);
//     },
// });