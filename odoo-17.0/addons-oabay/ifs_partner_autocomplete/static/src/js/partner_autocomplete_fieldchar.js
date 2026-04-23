/** @odoo-module **/

import { PartnerAutoCompleteCharField } from '@partner_autocomplete/js/partner_autocomplete_fieldchar';
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { jsonrpc } from "@web/core/network/rpc_service";


patch(PartnerAutoCompleteCharField.prototype, {
    autocomplete(value) {
        var TYC_ID = 'cca11660ccec11ecafbc9185dcf5bdaf'
        //暂不可用，此处应该向天眼查发送一个请求，从响应中得到一个‘TYCID’的cookie再放到header中去请求
        // var resp = $.ajax({
        //     url: 'https://www.tianyancha.com/',
        //     type: 'GET',
        //     xhrFields: {
        //         withCredentials: true // 包括跨域请求的 Cookie
        //     },
        //     success: function (data, status, xhr) {
        //         TYC_ID = xhr.getResponseHeader('Set-Cookie');
        //     },
        //     error: function(xhr, status, error) {
        //         console.error('Error:', error);
        //     }
        // })
        // console.log("+++++++", TYC_ID)
        // console.log("+++++++", resp)

        if(TYC_ID) {
            var url = 'https://capi.tianyancha.com/cloud-tempest/search/suggest/v5?_=' + Date.now();
            var data = $.ajax({
                async: false,
                url: url,
                dataType: 'json',
                contentType: 'application/json',
                type: 'post',
                timeout: this._timeout,
                headers: {
                    'X-Tycid': '22b14130b99d11ee8d15abfa902effa1',
                    'Version':'TYC-Web'
                },
                data: JSON.stringify({
                    // 'key': value,
                    // 'pageNum': 1,
                    // 'pageSize': 20,
                    // 'referer': 'search',
                    // 'sessionNo': Date.now(),
                    // 'sortType': '0',
                    'keyword': value
                }),
                success: function (result) {
                    return result.data;
                },
            }).responseJSON.data;
            return data;
        }
    },

    get sources() {        
        return [
            {
                options: async (request) => {
                    // Lazyload jsvat only if the component is being used.
                    await loadJS("/partner_autocomplete/static/lib/jsvat.js");
                    if (this.validateSearchTerm(request) && request !== '') {
                        var suggestions = await this.autocomplete(request);
                        suggestions?.forEach((suggestion) => {
                            suggestion.classList = "partner_autocomplete_dropdown_char";
                            suggestion.name = suggestion.comName === undefined ? suggestion.name : suggestion.comName;
                            suggestion.label = suggestion.name.replaceAll('<em>', '').replaceAll('</em>', '');
                            // suggestion.description=suggestion.matchType;
                            suggestion.regStatus = suggestion.regStatus == null ? '' : suggestion.regStatus;
                            suggestion.description = suggestion.taxCode;
                            suggestion.logo = suggestion.logo === "https://img5.tianyancha.com/null@!f_200x200" ? "" : suggestion.logo
                        });
                        if (!suggestions) suggestions = []
                        return suggestions;
                    }
                    else {
                        return [];
                    }
                },
                optionTemplate: "partner_autocomplete.DropdownOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        ];
    },

    async onSelect(option) {
        console.log(option);
        console.log("===============================");
        console.log(Object.getPrototypeOf(option));
        console.log("===============================");
        const data = Object.getPrototypeOf(option); //await this.partnerAutocomplete.getCreateData(Object.getPrototypeOf(option));

        jsonrpc('/autocomplete/contact',
            {'keyword':data.taxCode}).then((response) => {
                var email = response.email;
                var phone = response.phone;
                var street = response.street;
                console.log(response)
                const result = {
                    'name': data.comName.replace(/<[^>]+>/g, ""),
                    'company_registry': data.taxCode,
                    'email': email, //data.company.emailList?.[0] || null,
                    'phone': phone,//data.company.phoneInfoList?.[0]?.number || null,
                    'logo': data.logo || null,
                    'street': street //data.company.regLocation?.replace(/<[^>]+>/g, "") || null,
                };
        
                if (this.props.record.resModel === 'res.company') {
                    Object.assign(result, {
                        'vat': data.taxCode,
                        'website': data.websites?.split("\t")[0],
                    });
                }
        
                this.props.record.update(result);
        })
    }
});


