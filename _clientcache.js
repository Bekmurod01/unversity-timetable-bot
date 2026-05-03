"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.expandNeededPartColgroups = exports.cachedDBI_getTableAccessibleColumns_async = exports.cachedDBI_getTableAccessibleColumns = exports.cachedDBI_getColumnDef = exports.cachedDBI_getTableDef = exports.cachedDBI_async = exports.cachedDBI_sync = exports.refreshCachedDBI = exports.useCachedDBI = void 0;
var tslib_1 = require("tslib");
var React = require("react");
var asc_react_1 = require("../asc/asc_react");
var lib_date_1 = require("../asc/lib_date");
var cache_1 = require("../react/cache");
var dbi_1 = require("./dbi");
var cache_def = {
    id: 'dbi',
    parseParams: function (req, params) {
        var _a;
        var type = params.type, o = params.options;
        var dbid = params.dbid || '';
        if (typeof dbid != 'string')
            ASC.dieError('7400105945', dbid);
        var options = {
            date: o.date || '',
            needed_part: expandNeededPartColgroups(o.needed_part) || {},
            needed_combos: o.needed_combos || {},
            vt_filter: o.vt_filter || {},
            tables: o.tables || [],
            columns: o.columns || [],
            info_tables: o.info_tables || [],
            info_columns: o.info_columns || [],
            client_filter: o.client_filter || {},
        };
        var special = false;
        if (!dbid)
            special = true;
        if (options.tables.length
            || options.columns.length
            || options.info_tables.length
            || options.info_columns.length
            || Object.keys(options.client_filter).length)
            special = true;
        var vt_filter = {};
        if (type == 'maindbi') {
            vt_filter.datefrom = vt_filter.dateto = '';
            var ovt = options.vt_filter;
            if (ovt.classid || ovt.studentid || ovt.studentids)
                special = true;
            if (ovt.date) {
                vt_filter.datefrom = vt_filter.dateto = ovt.date;
            }
            if (ovt.week) {
                vt_filter.datefrom = (0, lib_date_1.week_start)(req, ovt.week);
                vt_filter.dateto = (0, lib_date_1.week_end)(req, ovt.week);
            }
            if (ovt.datefrom && ovt.dateto) {
                vt_filter.datefrom = ovt.datefrom;
                vt_filter.dateto = ovt.dateto;
            }
            if (ovt.teacherid) {
                vt_filter.teacherids = [ovt.teacherid];
                special = true;
            }
            else if ((_a = ovt.teacherids) === null || _a === void 0 ? void 0 : _a.length) {
                vt_filter.teacherids = ovt.teacherids;
                special = true;
            }
        }
        if (special) {
            return {
                groupkey: {
                    type: type,
                    dbid: dbid,
                    special: true,
                    options: options,
                },
                partkey: null,
            };
        }
        else {
            return {
                groupkey: {
                    type: type,
                    dbid: dbid,
                    special: false,
                    options: {
                        date: options.date,
                    }
                },
                partkey: {
                    options: {
                        needed_part: options.needed_part,
                        needed_combos: options.needed_combos,
                        vt_filter: vt_filter,
                    }
                }
            };
        }
    },
    fetch: function (req, group, parts) {
        return tslib_1.__awaiter(this, void 0, void 0, function () {
            var sc, groupkey, options, accessor, res, groupkey, groupdata_1, needed_combos, date_needs, global_need, _loop_1, _i, parts_1, part, needs_3, ni, date_need, _a, needs_1, need, t, _b, needs_2, need, accessor, res, _c;
            return tslib_1.__generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        sc = StructureCache.get(req, group.key.type);
                        if (!group.key.special) return [3, 2];
                        groupkey = group.key;
                        options = groupkey.options;
                        accessor = dbiAccessor(req, groupkey.type, groupkey.dbid, options);
                        return [4, accessor(tslib_1.__assign(tslib_1.__assign({}, options), { op: 'fetch' }))];
                    case 1:
                        res = _d.sent();
                        sc.fill({ res: res, needed_part: options.needed_part });
                        group.data = {
                            special_accessorRes: res,
                        };
                        ASC.changeEvents.received(group.changeEvents = res.changeEvents || {});
                        return [3, 7];
                    case 2:
                        groupkey = group.key;
                        if (!group.data)
                            group.data = {
                                data: new Map(),
                                combos: new Map(),
                            };
                        groupdata_1 = group.data;
                        if (group.old) {
                            groupdata_1.data.clear();
                            group.changeEvents = {};
                        }
                        needed_combos = dbi_1.DBITools.mergeNeededCombos.apply(dbi_1.DBITools, parts.map(function (part) { return part.key.options.needed_combos; }));
                        date_needs = [];
                        global_need = null;
                        _loop_1 = function (part) {
                            var partkey = part.key;
                            var options = partkey.options;
                            var needed_part = options.needed_part, vt_filter = options.vt_filter;
                            var _loop_2 = function (table) {
                                var _e;
                                var columns = (0, dbi_1.idsArrayUnique)(needed_part[table]);
                                var ctdef = sc.tableDefs[table];
                                if (ctdef === null)
                                    return "continue";
                                var maybe_vt = true;
                                if (ctdef) {
                                    if (!ctdef.def.vt_filter)
                                        maybe_vt = false;
                                    columns = columns.filter(function (c) { return ctdef.columns[c] !== null; });
                                }
                                if (ctdef && !ctdef.def.vt_filter) {
                                    maybe_vt = false;
                                }
                                var need = void 0;
                                if (maybe_vt && vt_filter.datefrom) {
                                    need = date_needs.find(function (need) {
                                        return need.datefrom == vt_filter.datefrom && need.dateto == vt_filter.dateto;
                                    });
                                    if (!need) {
                                        date_needs.push(need = {
                                            part: {},
                                            datefrom: vt_filter.datefrom,
                                            dateto: vt_filter.dateto,
                                        });
                                    }
                                }
                                else {
                                    if (!global_need) {
                                        global_need = {
                                            part: {},
                                            datefrom: '',
                                            dateto: '',
                                        };
                                    }
                                    need = global_need;
                                }
                                need.part = dbi_1.DBITools.mergeNeededParts(need.part, (_e = {}, _e[table] = columns, _e));
                            };
                            for (var table in needed_part) {
                                _loop_2(table);
                            }
                        };
                        for (_i = 0, parts_1 = parts; _i < parts_1.length; _i++) {
                            part = parts_1[_i];
                            _loop_1(part);
                        }
                        needs_3 = tslib_1.__spreadArray([], date_needs, true);
                        if (global_need) {
                            if (needs_3.length > 0) {
                                ni = 0;
                                date_need = needs_3[ni];
                                needs_3[ni] = tslib_1.__assign(tslib_1.__assign({}, date_need), { part: dbi_1.DBITools.mergeNeededParts(date_need.part, global_need.part) });
                                global_need = null;
                            }
                            else {
                                needs_3.push(global_need);
                            }
                        }
                        for (_a = 0, needs_1 = needs_3; _a < needs_1.length; _a++) {
                            need = needs_1[_a];
                            need.combos = {};
                            for (t in need.part) {
                                if (needed_combos[t])
                                    need.combos[t] = (0, dbi_1.idsArrayIntersect)(needed_combos[t], need.part[t]);
                            }
                        }
                        _b = 0, needs_2 = needs_3;
                        _d.label = 3;
                    case 3:
                        if (!(_b < needs_2.length)) return [3, 6];
                        need = needs_2[_b];
                        accessor = dbiAccessor(req, groupkey.type, groupkey.dbid, {
                            date: groupkey.options.date || undefined,
                            vt_filter: {
                                datefrom: need.datefrom || undefined,
                                dateto: need.dateto || undefined,
                            }
                        });
                        _c = need;
                        return [4, accessor({
                                op: 'fetch',
                                needed_part: need.part,
                                needed_combos: need.combos,
                            })];
                    case 4:
                        res = _c.res = _d.sent();
                        ASC.changeEvents.received(res.changeEvents || {});
                        sc.fill({ res: res, needed_part: need.part });
                        _d.label = 5;
                    case 5:
                        _b++;
                        return [3, 3];
                    case 6:
                        (function () {
                            var changeEvents = group.changeEvents;
                            for (var _i = 0, needs_4 = needs_3; _i < needs_4.length; _i++) {
                                var res = needs_4[_i].res;
                                if (ceMismatch(changeEvents, res.changeEvents)) {
                                    return {
                                        retry: true,
                                    };
                                }
                                changeEvents = tslib_1.__assign(tslib_1.__assign({}, changeEvents), res.changeEvents);
                            }
                            var fillData = function (key, columns, rows) {
                                var data = groupdata_1.data.get(key);
                                if (!data) {
                                    groupdata_1.data.set(key, data = {
                                        rows: rows,
                                        columns: columns,
                                    });
                                }
                                else {
                                    var data_rows = data.rows;
                                    data.rows = [];
                                    var ok = data_rows.length == rows.length;
                                    if (ok)
                                        for (var i = 0; i < rows.length; i++) {
                                            var row = rows[i];
                                            var drow = data_rows[i];
                                            if (row.id != drow.id) {
                                                ok = false;
                                                break;
                                            }
                                            data.rows.push(tslib_1.__assign(tslib_1.__assign({}, drow), row));
                                        }
                                    if (ok) {
                                        data.columns = (0, dbi_1.idsArrayMergeUnique)(data.columns || [], columns);
                                    }
                                    else {
                                        ASC.logProblem('9827644219', [key, rows, data_rows]);
                                        data.columns = columns;
                                        data.rows = rows;
                                    }
                                }
                                for (var _i = 0, _a = data.rows; _i < _a.length; _i++) {
                                    var r = _a[_i];
                                    Object.freeze(r);
                                }
                            };
                            for (var _a = 0, needs_5 = needs_3; _a < needs_5.length; _a++) {
                                var need = needs_5[_a];
                                var res = need.res;
                                for (var _b = 0, _c = res.tables; _b < _c.length; _b++) {
                                    var rt = _c[_b];
                                    var t = rt.id;
                                    {
                                        for (var _d = 0, _e = rt.combos || []; _d < _e.length; _d++) {
                                            var combo = _e[_d];
                                            var key = [t, combo.column];
                                            if (combo.subcolumn)
                                                key.push(combo.subcolumn);
                                            if (combo.subcolumn2)
                                                key.push(combo.subcolumn2);
                                            groupdata_1.combos.set(key.join('.'), combo.db);
                                        }
                                        for (var _f = 0, _g = need.combos[t] || []; _f < _g.length; _f++) {
                                            var c = _g[_f];
                                            var key = t + '.' + c;
                                            if (!groupdata_1.combos.has(key))
                                                groupdata_1.combos.set(key, null);
                                        }
                                    }
                                    if (rt.data_rows) {
                                        var rows = rt.data_rows;
                                        var columns = rt.data_columns;
                                        var tdef = sc.tableDefs[t].def;
                                        if (tdef.vt_filter) {
                                            var _h = vt_filter_data(req, tdef, { datefrom: need.datefrom, dateto: need.dateto }), vals = _h[0], row2val = _h[1];
                                            var buckets = new Map();
                                            for (var _j = 0, vals_1 = vals; _j < vals_1.length; _j++) {
                                                var val = vals_1[_j];
                                                buckets.set(val, []);
                                            }
                                            for (var _k = 0, rows_1 = rows; _k < rows_1.length; _k++) {
                                                var row = rows_1[_k];
                                                buckets.get(row2val(row)).push(row);
                                            }
                                            for (var _l = 0, vals_2 = vals; _l < vals_2.length; _l++) {
                                                var val = vals_2[_l];
                                                fillData(t + ':' + val, columns, buckets.get(val));
                                            }
                                        }
                                        else {
                                            fillData(t, columns, rows);
                                        }
                                    }
                                }
                            }
                            group.changeEvents = changeEvents;
                        })();
                        _d.label = 7;
                    case 7: return [2];
                }
            });
        });
    },
    getResult: function (req, group, part) {
        var sc = StructureCache.get(req, group.key.type);
        if (group.key.special) {
            var groupkey = group.key;
            if (!groupkey.dbid)
                return { result: null };
            var groupdata = group.data;
            if (groupdata) {
                return {
                    result: resultdbi(req, groupdata.special_accessorRes, groupkey.options, group.old),
                };
            }
            else {
                return {
                    result: mockdbi(req, groupkey.type, groupkey.dbid, groupkey.options),
                    fetch: true,
                    mock: true,
                };
            }
        }
        else {
            var groupkey_1 = group.key;
            var partkey = part.key;
            var type = groupkey_1.type, dbid = groupkey_1.dbid;
            var options_1 = tslib_1.__assign(tslib_1.__assign({}, groupkey_1.options), partkey.options);
            var groupdata_2 = group.data;
            var mock = function () {
                return {
                    result: mockdbi(req, groupkey_1.type, groupkey_1.dbid, options_1),
                    fetch: true,
                    mock: true,
                };
            };
            if (!groupdata_2) {
                return mock();
            }
            var res = {
                type: type,
                dbid: dbid,
                tables: [],
                changeEvents: group.changeEvents,
            };
            var _a = partkey.options, needed_part = _a.needed_part, needed_combos = _a.needed_combos, vt_filter = _a.vt_filter;
            var _loop_3 = function (t) {
                var ktd = sc.tableDefs[t];
                if (ktd === null)
                    return "continue";
                if (!ktd) {
                    return { value: mock() };
                }
                var def = ktd.def;
                var rt = {
                    id: t,
                    def: def,
                    cdefs: [],
                    _uial: ktd._uial,
                };
                res.tables.push(rt);
                for (var _i = 0, _b = needed_part[t]; _i < _b.length; _i++) {
                    var c = _b[_i];
                    var kcd = ktd.columns[c];
                    if (kcd === null)
                        continue;
                    if (!kcd) {
                        return { value: mock() };
                    }
                    rt.cdefs.push(kcd.def);
                }
                var columns = rt.cdefs.map(function (cdef) { return cdef.id; });
                var fillData = function (key) {
                    var _a, _b;
                    var data = groupdata_2.data.get(key);
                    if (data && (0, dbi_1.idsIsSubArray)(columns, data.columns)) {
                        if (!rt.data_rows) {
                            rt.data_rows = [];
                            rt.data_columns = columns;
                        }
                        var chunkSize = 4096;
                        if (data.rows.length <= chunkSize) {
                            (_a = rt.data_rows).push.apply(_a, data.rows);
                        }
                        else {
                            for (var i = 0; i < data.rows.length; i += chunkSize) {
                                (_b = rt.data_rows).push.apply(_b, data.rows.slice(i, i + chunkSize));
                            }
                        }
                        return true;
                    }
                    else {
                        return false;
                    }
                };
                if (def.vt_filter) {
                    var vals = vt_filter_data(req, def, vt_filter)[0];
                    for (var _c = 0, vals_3 = vals; _c < vals_3.length; _c++) {
                        var val = vals_3[_c];
                        if (!fillData(t + ':' + val))
                            return { value: mock() };
                    }
                }
                else {
                    if (!fillData(t))
                        return { value: mock() };
                }
                var _loop_4 = function (c) {
                    if (!rt.cdefs.find(function (cdef) { return cdef.id == c; }))
                        return "continue";
                    if (!groupdata_2.combos.has(t + '.' + c)) {
                        return { value: mock() };
                    }
                    groupdata_2.combos.forEach(function (db, path_str) {
                        var path = path_str.split('.');
                        if (path[0] != t)
                            return;
                        if (path[1] != c)
                            return;
                        if (!rt.combos)
                            rt.combos = [];
                        rt.combos.push({
                            column: path[1],
                            subcolumn: path[2],
                            subcolumn2: path[3],
                            db: db,
                        });
                    });
                };
                for (var _d = 0, _e = needed_combos[t] || []; _d < _e.length; _d++) {
                    var c = _e[_d];
                    var state_2 = _loop_4(c);
                    if (typeof state_2 === "object")
                        return state_2;
                }
            };
            m: for (var t in needed_part) {
                var state_1 = _loop_3(t);
                if (typeof state_1 === "object")
                    return state_1.value;
            }
            return {
                result: resultdbi(req, res, options_1, group.old),
            };
        }
    }
};
function ceMismatch(ce1, ce2) {
    for (var e in ce1) {
        var v1 = ce1[e];
        if (v1 == undefined)
            ASC.dieError('7370920523', ce1);
        if (!(e in ce2))
            continue;
        var v2 = ce2[e];
        if (v2 == undefined)
            ASC.dieError('4329860511', ce2);
        if (v1 != v2)
            return true;
    }
    return false;
}
var dbi2options = new WeakMap();
function resultdbi(req, res, options, old) {
    var dbi = dbi_1.ClientDBI.fromAccessorResult(req, res);
    dbi.old = old;
    dbi.backend = new dbi_1.ClientDBIBackend(dbi, dbiAccessor(req, res.type, res.dbid, options));
    dbi2options.set(dbi, options);
    return dbi;
}
function mockdbi(req, type, dbid, options) {
    var res = {
        type: type,
        dbid: dbid,
        tables: [],
        changeEvents: {},
    };
    var sc = StructureCache.get(req, type);
    var needed_part = options.needed_part || {};
    for (var t in needed_part) {
        var ktd = sc.tableDefs[t];
        if (ktd === null)
            continue;
        if (!ktd)
            ktd = {
                columns: {},
                def: {
                    id: t,
                }
            };
        var rt = {
            id: t,
            cdefs: [],
            def: ktd.def,
        };
        res.tables.push(rt);
        for (var _i = 0, _a = needed_part[t]; _i < _a.length; _i++) {
            var c = _a[_i];
            var kcd = ktd.columns[c];
            if (kcd === null)
                continue;
            if (!kcd) {
                kcd = { def: { id: c } };
            }
            rt.cdefs.push(kcd.def);
        }
    }
    var dbi = dbi_1.ClientDBI.fromAccessorResult(req, res);
    dbi.mock = true;
    dbi2options.set(dbi, options);
    return dbi;
}
var supported_vt_filter_cols = ['date', 'week', 'month'];
function vt_filter_data(req, tdef, vt_filter) {
    var multikey = tdef.multikey;
    var vt_col = supported_vt_filter_cols.find(function (c) { return tdef.vt_filter.includes(c); });
    var vt_multikey_index = (multikey || []).indexOf(vt_col);
    var values = [];
    var datefrom = vt_filter.datefrom, dateto = vt_filter.dateto;
    switch (vt_col) {
        case 'date':
            values = (0, lib_date_1.date_interval_array)(datefrom, dateto);
            break;
        case 'week':
            values = (0, lib_date_1.week_interval_array)(req, (0, lib_date_1.date_week)(req, datefrom), (0, lib_date_1.date_week)(req, dateto));
            break;
        case 'month':
            values = (0, lib_date_1.month_interval_array)((0, lib_date_1.date_month)(datefrom), (0, lib_date_1.date_month)(dateto));
            break;
    }
    var row2val;
    if (vt_multikey_index >= 0)
        row2val = function (row) { return row.id.split(':')[vt_multikey_index]; };
    else
        row2val = function (row) { return row[vt_col]; };
    return [values, row2val];
}
function dbiAccessor(req, type, dbid, options) {
    var _this = this;
    switch (type) {
        case 'maindbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../rpr/server/maindbi"); })];
                        case 1: return [2, (_a.sent()).mainDBIAccessor(req, parseInt(dbid), {
                                vt_filter: options.vt_filter,
                                date: options.date,
                            }, args)];
                    }
                });
            }); };
        case 'ttuidocdbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../timetable/app/server/ttdoc"); })];
                        case 1: return [2, (_a.sent()).ttuidocDBIAccessor(req, parseInt(dbid), args)];
                    }
                });
            }); };
        case 'ttdbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../timetable/server/ttdbi"); })];
                        case 1: return [2, (_a.sent()).timetableDBIAccessor(req, dbid, args)];
                    }
                });
            }); };
        case 'substdbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../substitution/server/substdbi"); })];
                        case 1: return [2, (_a.sent()).substDBIAccessor(req, dbid, args)];
                    }
                });
            }); };
        case 'licensingdbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../licensing/server/licensingdbi"); })];
                        case 1: return [2, (_a.sent()).licensingDBIAccessor(req, { vt_filter: options.vt_filter }, args)];
                    }
                });
            }); };
        case 'devdbi':
            return function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                return tslib_1.__generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4, Promise.resolve().then(function () { return require("../asc/server/devdbi"); })];
                        case 1: return [2, (_a.sent()).devDBIAccessor(req, {}, args)];
                    }
                });
            }); };
    }
    ASC.dieError('4541798467', [type, dbid]);
}
var StructureCache = (function () {
    function StructureCache(type) {
        this.type = type;
        this.tableDefs = {};
    }
    StructureCache.prototype.fill = function (params) {
        var res = params.res, needed_part = params.needed_part, columns_all = params.columns_all;
        var tableDefs = this.tableDefs;
        for (var _i = 0, _a = res.tables; _i < _a.length; _i++) {
            var rt = _a[_i];
            var t = rt.id;
            if (!rt.data_rows && !columns_all)
                continue;
            {
                var ktd = tableDefs[t];
                if (!ktd) {
                    tableDefs[t] = ktd = {
                        def: tslib_1.__assign(tslib_1.__assign({ id: t }, rt.def), { columns: undefined }),
                        _uial: rt._uial,
                        columns: {},
                    };
                }
                for (var _b = 0, _c = rt.cdefs; _b < _c.length; _b++) {
                    var cdef = _c[_b];
                    var c = cdef.id;
                    var kcd = ktd.columns[c];
                    if (!kcd) {
                        ktd.columns[c] = kcd = {
                            def: tslib_1.__assign({}, cdef)
                        };
                    }
                }
                for (var _d = 0, _e = (needed_part[t] || []); _d < _e.length; _d++) {
                    var c = _e[_d];
                    if (!ktd.columns[c])
                        ktd.columns[c] = null;
                }
                if (columns_all) {
                    ktd.columns_all = true;
                }
            }
        }
        for (var t in needed_part) {
            if (!tableDefs[t])
                tableDefs[t] = null;
        }
    };
    StructureCache.get = function (req, type) {
        return req.memoize('dbiStructureCache.' + type, function () { return new StructureCache(type); });
    };
    return StructureCache;
}());
function useWorking(working) {
    var work = (0, asc_react_1.useWorkIndicator)();
    React.useEffect(function () {
        if (working) {
            var resolve_1;
            var p = new Promise(function (r) { return resolve_1 = r; });
            work(p);
            return resolve_1;
        }
    }, [work, working]);
}
function useCachedDBI(type, dbid, options) {
    var dbi = (0, cache_1.useCacheData)({
        suspense: options.suspense,
    }, cache_def, {
        type: type,
        dbid: dbid,
        options: options,
    });
    React.useDebugValue(dbi);
    useWorking(dbi && (dbi.old || dbi.mock));
    return dbi;
}
exports.useCachedDBI = useCachedDBI;
function refreshCachedDBI(dbi) {
    return tslib_1.__awaiter(this, void 0, void 0, function () {
        var options;
        return tslib_1.__generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    options = dbi2options.get(dbi);
                    if (!options)
                        ASC.dieError('5202185508', dbi);
                    return [4, (0, cache_1.cacheGetDataAsync)({ req: dbi.req, refresh: true }, cache_def, {
                            type: dbi.type,
                            dbid: dbi.dbid,
                            options: options,
                        })];
                case 1:
                    _a.sent();
                    return [2];
            }
        });
    });
}
exports.refreshCachedDBI = refreshCachedDBI;
function cachedDBI_sync(req, type, dbid, options) {
    var suspense = options.suspense, dbi_options = tslib_1.__rest(options, ["suspense"]);
    return (0, cache_1.cacheGetDataSync)({
        req: req,
        suspense: suspense,
    }, cache_def, {
        type: type,
        dbid: dbid,
        options: dbi_options,
    });
}
exports.cachedDBI_sync = cachedDBI_sync;
function cachedDBI_async(req, type, dbid, options) {
    return (0, cache_1.cacheGetDataAsync)({
        req: req,
        refresh: options.cache === false,
    }, cache_def, {
        type: type,
        dbid: dbid,
        options: options
    });
}
exports.cachedDBI_async = cachedDBI_async;
function cachedDBI_getTableDef(req, type, table, options) {
    if (options === void 0) { options = {}; }
    var sc = StructureCache.get(req, type);
    var td = sc.tableDefs[table];
    if (!td) {
        if (td === undefined) {
            cachedDBI_getTableAccessibleColumns(req, type, table, { suspense: options.suspense });
        }
        return td;
    }
    return td.def;
}
exports.cachedDBI_getTableDef = cachedDBI_getTableDef;
function cachedDBI_getColumnDef(req, type, table, column, options) {
    if (options === void 0) { options = {}; }
    var sc = StructureCache.get(req, type);
    var td = sc.tableDefs[table];
    if (!td) {
        if (td === undefined) {
            cachedDBI_getTableAccessibleColumns(req, type, table, { suspense: options.suspense });
        }
        return td;
    }
    var cd = td.columns[column];
    if (!cd) {
        if (cd === null || td.columns_all)
            return null;
        return undefined;
    }
    return cd.def;
}
exports.cachedDBI_getColumnDef = cachedDBI_getColumnDef;
var cache_getTableAccessibleColumns_def = {
    id: 'getTableAccessibleColumns',
    parseParams: function (req, params) {
        return { groupkey: params.type, partkey: params.table };
    },
    getResult: function (req, group, part) {
        var type = group.key;
        var table = part.key;
        var sc = StructureCache.get(req, type);
        var td = sc.tableDefs[table];
        if (td === null)
            return { result: null };
        if (td === undefined)
            return {
                result: [],
                mock: true,
                fetch: true,
            };
        var columns = [];
        for (var c in td.columns) {
            if (td.columns[c])
                columns.push(c);
        }
        columns.sort();
        return {
            result: columns,
            fetch: !td.columns_all,
            mock: !td.columns_all,
        };
    },
    fetch: function (req, group, parts) {
        return tslib_1.__awaiter(this, void 0, void 0, function () {
            var type, sc, tables, needed_part, _i, tables_1, t, accessor, res;
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        type = group.key;
                        sc = StructureCache.get(req, type);
                        tables = parts.map(function (part) { return part.key; });
                        needed_part = {};
                        for (_i = 0, tables_1 = tables; _i < tables_1.length; _i++) {
                            t = tables_1[_i];
                            needed_part[t] = [];
                        }
                        accessor = dbiAccessor(req, type, '1', {});
                        return [4, accessor({
                                op: 'columns',
                                needed_part: needed_part,
                            })];
                    case 1:
                        res = _a.sent();
                        sc.fill({ res: res, needed_part: needed_part, columns_all: true });
                        console.log(res);
                        return [2];
                }
            });
        });
    }
};
function cachedDBI_getTableAccessibleColumns(req, type, table, options) {
    if (options === void 0) { options = {}; }
    return (0, cache_1.cacheGetDataSync)({ suspense: options.suspense, req: req }, cache_getTableAccessibleColumns_def, { type: type, table: table });
}
exports.cachedDBI_getTableAccessibleColumns = cachedDBI_getTableAccessibleColumns;
function cachedDBI_getTableAccessibleColumns_async(req, type, table) {
    return (0, cache_1.cacheGetDataAsync)({ req: req }, cache_getTableAccessibleColumns_def, { type: type, table: table });
}
exports.cachedDBI_getTableAccessibleColumns_async = cachedDBI_getTableAccessibleColumns_async;
var needed_part_colgroups = {
    __name: [
        'short',
        'name',
        'firstname',
        'lastname',
        'callname',
        'subname',
        'code',
    ],
    __ttitem: [
        'uniperiod',
        'endtime',
        'durationperiods',
        'subjectid',
        'classids',
        'groupnames',
        'igroupid',
        'teacherids',
        'classroomids',
    ],
    __ttitem_old: [
        'period',
        'daypart',
        'allday',
        'starttime',
        'endtime',
        'durationperiods',
        'subjectid',
        'classids',
        'groupnames',
        'igroupid',
        'teacherids',
        'classroomids',
    ],
};
function expandNeededPartColgroups(part) {
    var res = {};
    for (var t in part) {
        var cols0 = part[t];
        var cols = res[t] = [];
        for (var _i = 0, cols0_1 = cols0; _i < cols0_1.length; _i++) {
            var c = cols0_1[_i];
            var cg = needed_part_colgroups[c];
            if (cg) {
                for (var _a = 0, cg_1 = cg; _a < cg_1.length; _a++) {
                    var c_1 = cg_1[_a];
                    cols.push(c_1);
                }
            }
            else {
                cols.push(c);
            }
        }
    }
    return res;
}
exports.expandNeededPartColgroups = expandNeededPartColgroups;

