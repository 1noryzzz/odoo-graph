/** @odoo-module **/

import { parseInteger, parseFloat } from "@web/views/fields/parsers";
import { registry } from "@web/core/registry";


// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------


export function parseHexadecimal(value) {
    if (!value && value === "") {
        return false;
    }

    let start_with = value.slice(0, 2);
    if (start_with != "0x") {
        return parseInteger(value);
    } else {
        return parseInt(value.slice(2), 16);
    }
}

export class InvalidPercentError extends Error {}
/**
 * Try to extract a float from a string. The localization is considered in the process.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parsePercent(value) {
    if (!value && value === "") {
        return false;
    }

    let last_char = value[value.length - 1];
    if (last_char != "%") {
        let parsed_value = parseFloat(value);
        if (parsed_value < 0 || parsed_value > 1) {
            throw new InvalidPercentError(`"${value}" 不是一个有效的百分比`);
        }
        return parsed_value;
    } else{
        let parsed_value = parseFloat(value.slice(0, -1));
        if (parsed_value < 0 || parsed_value > 100) {
            throw new InvalidPercentError(`"${value}" 不是一个有效的百分比`);
        }
        return parsed_value / 100.00;
    }
}

/**
 * Try to extract a float time from a string. The localization is considered in the process.
 * The float time can have two formats: float or integer:integer.
 *
 * @param {string} value
 * @returns {number} a float
 */
export function parseFloatTimeMs(value) {
    let sign = 1;
    if (value[0] === "-") {
        value = value.slice(1);
        sign = -1;
    }
    const values = value.split(":");
    if (values.length > 2) {
        throw new InvalidNumberError(`"${value}" is not a correct number`);
    }
    if (values.length === 1) {
        return sign * parseFloat(value);
    }
    
    let hour = 0;
    let minutes = 0;
    let second = 0;
    let milliSec = 0;
    let msValues = [];
    if (values.length === 2) {
        minutes = parseInteger(values[0]);
        msValues = values[1].split(".");
        second = parseInteger(msValues[0]);
    } else {
        hour = parseInteger(values[0]);
        minutes = parseInteger(values[1]);
        msValues = values[2].split(".");
        second = parseInteger(msValues[0]);
    }

    if (msValues.length === 2) {
        milliSec = parseInteger(msValues[1]);
    }
    return sign * (hour * 60 + minutes + second / 60 + milliSec / 60000);
}

registry
    .category("parsers")
    .add("percent", parsePercent)
    .add("float_time_ms", parseFloatTimeMs)
