/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatBoolean } from "@web/views/fields/formatters";   // 这里用来保证加载顺序

const formatters = registry.category("formatters");

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

export function formatHexadecimal(value, options = {}) {
    if (value === false) {
        return "";
    }

    return `0x${Math.abs(value).toString(16).toUpperCase()}`;
}

/**
 * Returns a string representing a percent value, from a float.  The idea is that
 * we sometimes want to display something like 5% instead of 0.05
 *
 * @param {number | false} value
 * @param {Object} [options]
 * @returns {string}
 */
export function formatPercent(value, options = {}) {
    if (value === false) {
        return "";
    }

    value = value < 0 ? 0 : value;
    let percent = parseFloat(value * 100.00);
    return `${percent}%`;
}

/**
 * Returns a string representing a time value, from a float.  The idea is that
 * we sometimes want to display something like 1:45 instead of 1.75, or 0:15
 * instead of 0.25.
 *
 * @param {number | false} value
 * @param {Object} [options]
 * @param {boolean} [options.noLeadingZeroHour] if true, format like 1:30 otherwise, format like 01:30
 * @param {boolean} [options.displaySeconds] if true, format like ?1:30:00 otherwise, format like ?1:30
 * @returns {string}
 */
export function formatFloatTimeMs(value, options = {displaySeconds: true}) {
    if (value === false) {
        return "";
    }
    const isNegative = value < 0;
    value = Math.abs(value);

    let hour = Math.floor(value / 60);
    const milliSecLeft = Math.round(value * 60000) - hour * 3600000;
    // Although looking quite overkill, the following lines ensures that we do
    // not have float issues while still considering that 59s is 00:00.
    let min = milliSecLeft / 60000;
    if (options.displaySeconds) {
        min = Math.floor(min);
    } else {
        min = Math.round(min);
    }
    if (min === 60) {
        min = 0;
        hour = hour + 1;
    }
    min = String(min).padStart(2, "0");
    if (!options.noLeadingZeroHour) {
        hour = String(hour).padStart(2, "0");
    }
    let sec = "";
    let ms = "";
    if (options.displaySeconds) {
        sec = ":" + String(Math.floor((milliSecLeft % 60000) / 1000)).padStart(2, "0");
        ms = "." + String(Math.floor(milliSecLeft % 1000)).padStart(3, "0");
    }
    return `${isNegative ? "-" : ""}${hour === "00" ? "" : hour + ':'}${min}${sec}${ms}`;
}

/**
 * Returns a string representing the value of the python properties field
 * or a properties definition field (see fields.py@Properties).
 *
 * @param {array|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 */
export function formatProperties(value, field) {
    if (!value || !value.length) {
        return "";
    }
    if (field.property) {
        return value.filter((property) => property["name"] === field.property).map((property) => property["value"]).join(", ");
    } else {
        return value.map((property) => property["string"] + ": " + property["value"]).join(", ");
    }
    
}

formatters
    .add("percent", formatPercent)
    .add("float_time_ms", formatFloatTimeMs)
    .add("properties", formatProperties, {force: true});
