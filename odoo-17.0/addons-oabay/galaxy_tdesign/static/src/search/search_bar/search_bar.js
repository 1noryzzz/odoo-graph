/** @odoo-module **/

import { SearchBar } from '@web/search/search_bar/search_bar';
import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";

import { useRef, useState } from "@odoo/owl";
const { DateTime } = luxon;
const parsers = registry.category("parsers");

const CHAR_FIELDS = ["char", "html", "many2many", "many2one", "one2many", "text"];
let nextItemId = 1;

export class FlatSearchBar extends SearchBar {
    setup() {
        this.fields = this.env.searchModel.searchViewFields;
        this.searchItems = this.env.searchModel.getSearchItems((f) => f.type === "field");
        this.root = useRef("root");

        // core state
        this.state = useState({
            expanded: [],
            focusedIndex: 0,
            query: "",
        });

        // derived state
        this.items = useState([]);
        this.subItems = {};
        //用来暂存输入框中要查询的值，包含对应的searchItemId和查询的值
        this.searchValues = {};

        this.orm = useService("orm");

        this.keepLast = new KeepLast();

        //初次调用该方法创建this.items，用于渲染搜索栏所有字段和输入框
        this.computeExpandState({ expanded: [], focusedIndex: 0, query: "", subItems: [] });

        //该方法在从form页退出到list页时起作用，可以拿到上次的搜索记录并展示
        this.getFacets()
        useBus(this.env.searchModel, "update", this.render);
    }

    //页面初始化调用创建this.items
    async computeExpandState(options = {}) {
        const query = "query" in options ? options.query : this.state.query;
        const expanded = "expanded" in options ? options.expanded : this.state.expanded;
        const focusedIndex =
            "focusedIndex" in options ? options.focusedIndex : this.state.focusedIndex;
        const subItems = "subItems" in options ? options.subItems : this.subItems;
        //新增该字段在渲染many2one字段时会起作用，用来绑定搜索框中的值
        const searchItemId = "searchItemId" in options ? options.searchItemId : null;

        const tasks = [];
        for (const id of expanded) {
            if (!subItems[id]) {
                tasks.push({ id, prom: this.computeSubItems(id, query) });
            }
        }

        const prom = this.keepLast.add(Promise.all(tasks.map((task) => task.prom)));

        if (tasks.length) {
            const taskResults = await prom;
            tasks.forEach((task, index) => {
                subItems[task.id] = taskResults[index];
            });
        }

        this.state.expanded = expanded;
        this.state.query = query;
        this.state.focusedIndex = focusedIndex;
        this.subItems = subItems;

        const trimmedQuery = this.state.query.trim();

        this.items.length = 0;

        for (const searchItem of this.searchItems) {
            const field = this.fields[searchItem.fieldName];
            const type = field.type === "reference" ? "char" : field.type;
            /** @todo do something with respect to localization (rtl) */
            const preposition = this.env._t(["date", "datetime"].includes(type) ? "at" : "for");

            let value = trimmedQuery && type === "many2one" ? trimmedQuery : ""

            const item = {
                id: nextItemId++,
                searchItemDescription: searchItem.description,
                preposition,
                searchItemId: searchItem.id,
                //many2one字段会将输入框的值与对应的item进行赋值
                label: searchItemId === searchItem.id ? trimmedQuery : "",
                operator: searchItem.operator || (CHAR_FIELDS.includes(type) ? "ilike" : "="),
                value,
                type: type,
                //将many2one和selection字段的下拉框结果由原来的同级状态改为下一级
                childs: [],
            };

            if (type === "many2one") {
                item.isParent = true;
                item.isExpanded = this.state.expanded.includes(item.searchItemId);
            }

            if (item.isExpanded) {
                item.childs.push(...this.subItems[searchItem.id]);
            }

            // if (trimmedQuery && type === "many2one" && searchItemId === searchItem.id) {
            //     $(".galaxy_search_items").find("#" + searchItemId).focus()
            // }

            this.items.push(item);

            if (type === "selection") {
                this.computeSelectionItems(item.searchItemId)
            }
        }
    }

    async getFacets() {
        const facets = this.env.searchModel.facets.filter(function(f) {
            return f.type === 'field'
        })
        if (facets) {
            for (var facet of facets) {
                const item = this.items.find((i) => i.searchItemId === facet.groupId)
                item.label = facet.values[0]
                if (item.type === "date" || item.type === "datetime") {
                    item.value = DateTime.fromFormat(facet.values[0], "yyyy-MM-dd HH:mm:ss", { zone: "utc" })
                } else {
                    item.value = facet.values[0]
                }
                this.searchValues[facet.groupId] = facet.values[0]
            }
            this.onClickSearch()
        }
    }

    //selection字段的下拉框中的结果加到item中
    async computeSelectionItems(searchItemId) {
        const index = this.items.findIndex((i) => i.searchItemId === searchItemId);
        const searchItem = this.searchItems.find((i) => i.id === searchItemId);
        const field = this.fields[searchItem.fieldName];
        const options = field.selection;
        for (const [value, label] of options) {
            this.items[index].childs.push({
                id: nextItemId++,
                searchItemDescription: searchItem.description,
                searchItemId: searchItem.id,
                label: label,
                operator: searchItem.operator || "=",
                value: value,
            });
        }
    }

    //selection下拉框点击事件
    onChangeChild(searchItemId, ev) {
        const value = ev.target.value
        this.searchValues[searchItemId] = value
    }

    //修改后的输入框绑定的事件，如果是many2one字段会立即展开下拉框
    onNewSearchInput(ev) {
        const query = ev.target.value;
        this.searchValues[ev.target.id] = query
        for (const item of this.items) {
            if (item.type === "many2one" && item.searchItemId == ev.target.id) {
                this.computeExpandState({ query, expanded:[item.searchItemId], searchItemId: item.searchItemId});
            }
        }
    }

    //many2one下拉框点击事件
    onClickChild(searchItemId, label) {
        this.searchValues[searchItemId] = label
        this.onClickSearch()
    }

    //日期类型时间改变绑定的事件
    onDateTimeChanged(searchItemId, type, date) {
        if (date) {
            let dateFormat;
            if (type === 'date') {
                dateFormat= date.toFormat("yyyy-MM-dd")
            } else {
                dateFormat= date.toFormat("yyyy-MM-dd HH:mm:ss")
            }
            this.searchValues[searchItemId] = dateFormat
            const item = this.items.find((i) => i.searchItemId === searchItemId);
            item.value = date
        } else {
            if (this.searchValues.hasOwnProperty(searchItemId)) {
                delete this.searchValues[searchItemId];
            }
        }
    }

    //输入框绑定的键盘点击事件
    onNewSearchKeydown(ev) {
        if (ev.key === "Enter") {
            this.onClickSearch();
        }
    }

    //搜索按钮绑定的点击事件
    onClickSearch() {
        //清空旧搜索条件
        this.env.searchModel.clearQuery()
        for (const item of this.items) {
            let searchValue = this.searchValues[item.searchItemId]
            const type = item.type
            
            if (searchValue && searchValue.trim()) {
                const trimmedQuery = searchValue.trim()
                const parser = parsers.contains(type) ? parsers.get(type) : (str) => str;
                let value;
                try {
                    switch (type) {
                        case "date": {
                            value = item.value;
                            break;
                        }
                        case "datetime": {
                            value = item.value;
                            break;
                        }
                        case "many2one": {
                            value = trimmedQuery;
                            break;
                        }
                        default: {
                            value = parser(trimmedQuery);
                        }
                    }
                } catch (_e) {
                    continue;
                }
                item.label = trimmedQuery
                item.value = value
                this.selectExpandItem(item)
            } else {
                item.label = ""
                item.value = ""
            }
        }
    }

    selectExpandItem(item) {
        if (!item.unselectable) {
            const { searchItemId, label, operator, value } = item;
            this.env.searchModel.addAutoCompletionValues(searchItemId, { label, operator, value });
        }
    }
}

FlatSearchBar.components = {
    ...SearchBar.components,
    DatePicker, 
    DateTimePicker
};

FlatSearchBar.template = "Flat.SearchBar";