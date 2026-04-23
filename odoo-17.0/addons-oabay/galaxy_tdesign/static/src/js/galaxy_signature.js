/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { useService } from "@web/core/utils/hooks";
import { GalaxyMobileSignature } from "./mobile_signature.js";
import { jsonrpc } from "@web/core/network/rpc_service";

export class GalaxySignatureForm extends Component {
    static template = "galaxy_tdesign.galaxy_signature"
    static components = { GalaxyMobileSignature }

    setup() {
        this.rootRef = useRef("root");
        this.rpc = useService("rpc");

        this.csrfToken = odoo.csrf_token;
        this.state = useState({
            error: false,
            success: false,
        });
        this.signature = useState({ name: this.props.defaultName });
        this.nameAndSignatureProps = {
            signature: this.signature,
            fontColor: this.props.fontColor || "black",
        };
        if (this.props.signatureRatio) {
            this.nameAndSignatureProps.displaySignatureRatio = this.props.signatureRatio;
        }
        if (this.props.signatureType) {
            this.nameAndSignatureProps.signatureType = this.props.signatureType;
        }
        if (this.props.mode) {
            this.nameAndSignatureProps.mode = this.props.mode;
        }

        // Correctly set up the signature area if it is inside a modal
        onMounted(() => {
            this.signature.resetSignature();
        });
    }

    get sendLabel() {
        return this.props.sendLabel || _t("Accept & Sign");
    }

    /**
    * Handles click on the submit button.
    *
    * This will get the current name and signature and validate them.
    * If they are valid, they are sent to the server, and the reponse is
    * handled. If they are invalid, it will display the errors to the user.
    *
    * @returns {Promise}
    */
    async onClickSubmit() {
        const name = this.signature.name;
        const signature = this.signature.getSignatureImage()[1];
        const data = await this.rpc(this.props.callUrl, { name, signature });
        if (data.force_refresh) {
            if (data.redirect_url) {
                redirect(data.redirect_url);
            } else {
                window.location.reload();
            }
            // do not resolve if we reload the page
            return new Promise(() => { });
        }
        this.state.error = data.error || false;
        this.state.success = !data.error && {
            message: data.message,
            redirectUrl: data.redirect_url,
            redirectMessage: data.redirect_message,
        };
    }

    _onClickSignSubmit() {
        var self = this;

        self.disabledSubmitBtn();

        if (this.signature.isSignatureEmpty) {
            return;
        }

        const name = this.signature.name;
        const signature = this.signature.getSignatureImage()[1];

        return jsonrpc(this.props.callUrl, {
            'name': name,
            'signature': signature,
        }).then(function (data) {
            if (data.error) {
                self.$('.o_galaxy_sign_error_msg').remove();
                self.$controls.prepend(renderToElement('galaxy_tdesign.galaxy_signature_error', { widget: data }));
                self.enableSubmitBtn();
            } else if (data.success) {
                var $success = renderToElement('galaxy_tdesign.galaxy_signature_success', { widget: data });
                self.$el.empty().append($success);
            }
            if (data.force_refresh) {
                if (data.redirect_url) {
                    window.location = data.redirect_url;
                } else {
                    window.location.reload();
                }
                // no resolve if we reload the page
                return new Promise(function () { });
            }
        }, function (err) {
            self.enableSubmitBtn();
        });
    }

    disabledSubmitBtn() {
        $('.o_galaxy_sign_submit').attr("disabled", true);
        $('.o_galaxy_sign_submit').contents().each(function () {
            if (this.nodeType === Node.TEXT_NODE) {
                $(this).replaceWith("请稍候…");
            }
        });
        $('#galaxySignBtnIcon').attr("src", "/galaxy_tdesign/static/src/img/loading.png");
        $('#galaxySignBtnIcon').addClass("loading");
    }

    enableSubmitBtn() {
        $('.o_galaxy_sign_submit').attr("disabled", false);
        $('.o_galaxy_sign_submit').contents().each(function () {
            if (this.nodeType === Node.TEXT_NODE) {
                $(this).replaceWith("同意 & 签名");
            }
        });
        $('#galaxySignBtnIcon').attr("src", "/galaxy_tdesign/static/src/img/check.png");
        $('#galaxySignBtnIcon').removeClass("loading");
    }

    _onClearSign() {
        this.signature.resetSignature();
    }
}

registry.category("public_components").add("galaxy_tdesign.signature_form", GalaxySignatureForm);