"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.client_req = exports.EduRequest_Client = exports.EduRequest = void 0;
var tslib_1 = require("tslib");
var lib_date_1 = require("./lib_date");
var EduRequest = (function () {
    function EduRequest() {
        this.props = null;
        this.edupage = '';
        this.lang = '';
        this.firstDayOfWeek = 1;
        this.weekendDays = [];
        this.school_country = '';
        this.school_state = '';
        this.schoolyear_turnover = '';
        this.custom_turnover = {};
        this.loggedUser = '';
        this.loggedUserRights = [];
        this.sort_name_col = 'FSL';
        this.edupageLangs = null;
        this.ttlangasc = null;
        this.aiLangs = {};
        this._memoize_cache = new Map();
        this.yield_time = 0;
    }
    EduRequest.prototype.initRequest = function (props) {
        this.props = props;
        for (var _i = 0, _a = [
            'edupage',
            'lang',
            'firstDayOfWeek',
            'weekendDays',
            'school_country',
            'school_state',
            'schoolyear_turnover',
            'custom_turnover',
            'loggedUser',
            'loggedUserRights',
            'parent_studentid',
            'sort_name_col',
            'jsmodulemode',
        ]; _i < _a.length; _i++) {
            var c = _a[_i];
            var v = props[c];
            if (v !== undefined)
                this[c] = v;
        }
    };
    EduRequest.prototype.getSchoolYear = function (date) {
        if (date === void 0) { date = this.timezone_date(); }
        if (!date || !this.schoolyear_turnover)
            ASC.dieError('8130146806');
        var year = parseInt(date.substr(0, 4));
        if (date < this.schoolYear_turnOver(year))
            year--;
        return year;
    };
    EduRequest.prototype.getSchoolYear_auto = function () {
        return this.props.year_auto || this.getSchoolYear();
    };
    EduRequest.prototype.getSchoolYear_auto_date = function () {
        return this.props.year_auto_date || this.timezone_date();
    };
    EduRequest.prototype.getSchoolYearName = function (year) {
        if (!year)
            return '';
        if (this.schoolYear_turnOver(year + 1) <= (year + 1) + '-02-01')
            return '' + year;
        else
            return year + '/' + (year + 1);
    };
    EduRequest.prototype.schoolYear_turnOver = function (year) {
        return this.custom_turnover[year] || (year + '-' + this.schoolyear_turnover);
    };
    EduRequest.prototype.schoolYear_turnOver_end = function (year) {
        return (0, lib_date_1.date_delta)(this.schoolYear_turnOver(year + 1), -1);
    };
    EduRequest.prototype.isAdmin = function () {
        return this.loggedUser == 'Admin';
    };
    EduRequest.prototype.isUcitel = function () {
        if (this.loggedUser.substr(0, 6) == 'Ucitel')
            return this.loggedUser.substr(6);
        return '';
    };
    EduRequest.prototype.isStudent = function () {
        if (this.loggedUser.substr(0, 7) == 'Student')
            return this.loggedUser.substr(7);
        return '';
    };
    EduRequest.prototype.isStudentOrParent = function () {
        return this.isStudent() || this.props.parent_studentid || '';
    };
    EduRequest.prototype.isParent = function () {
        if (this.loggedUser.substr(0, 5) == 'Rodic')
            return this.loggedUser.substr(5);
        return '';
    };
    EduRequest.prototype.isGuest = function () {
        if (this.loggedUser.substr(0, 5) == 'Guest')
            return this.loggedUser.substr(5);
        return '';
    };
    EduRequest.prototype.isAscAdmin = function () {
        return !!this.props.ascadmin;
    };
    EduRequest.prototype.isAscDebug = function () {
        return !!this.props.ascdebug;
    };
    EduRequest.prototype.isDevelopEdupage = function (mode) {
        if (mode === void 0) { mode = ''; }
        var d = this.props.ascdevelop;
        if (!d)
            return false;
        switch (mode) {
            case '': return true;
            case 'junior': return !!d.junior;
            case 'senior': return !d.junior;
        }
        ASC.dieError('8779618679', mode);
    };
    EduRequest.prototype.isAscDevelop = function () {
        return this.isDevelopEdupage();
    };
    EduRequest.prototype.isApp = function () {
        return !!this.props.app;
    };
    EduRequest.prototype.hasRight = function (right) {
        if (this.isAdmin()) {
            return !['limited'].includes(right);
        }
        return this.loggedUserRights.includes(right);
    };
    EduRequest.prototype.jeZUS = function () {
        return !!this.props.jeZUS;
    };
    EduRequest.prototype.jeSUS = function () {
        return !!this.props.jeSUS;
    };
    EduRequest.prototype.jeSportovyKlub = function () {
        return !!this.props.jeSportovyKlub;
    };
    EduRequest.prototype.jeCVC = function () {
        return !!this.props.jeCVC;
    };
    EduRequest.prototype.jeMS = function () {
        return !!this.props.jeMS;
    };
    EduRequest.prototype.isAgenda = function () {
        return !!this.props.isAgenda;
    };
    EduRequest.prototype.jeFirma = function () {
        return !!this.props.jeFirma;
    };
    EduRequest.prototype.jeNemeckaSkolaSkdFirma = function () {
        return !!this.props.jeNemeckaSkolaSkdFirma;
    };
    EduRequest.prototype.isCustomer = function () {
        return !!this.props.isCustomer;
    };
    EduRequest.prototype.uiError = function (errNumber, msg, info) {
        if (typeof msg !== 'string')
            ASC.dieError('8358216710');
        console.error('Error', errNumber);
        if (msg)
            console.log(msg);
        if (info !== undefined)
            console.log(info);
        var e = new Error('' + errNumber);
        e['errNumber'] = errNumber;
        e['msg'] = msg;
        throw e;
    };
    EduRequest.prototype.ls = function (i) {
        if (this.edupageLangs && this.edupageLangs[i]) {
            return this.edupageLangs[i];
        }
        return ASC.ls(i);
    };
    EduRequest.prototype.lsf = function (i, replace) {
        if (this.edupageLangs && this.edupageLangs[i]) {
            i = this.edupageLangs[i];
        }
        return ASC.lsf(i, replace);
    };
    EduRequest.prototype.ttls = function (i) {
        if (this.ttlangasc && this.ttlangasc[i]) {
            return this.ttlangasc[i];
        }
        return ASC.ttls(i);
    };
    EduRequest.prototype.ttlsf = function (i, replace) {
        var s = this.ttls(i);
        for (var k in replace) {
            s = s.replace('%' + k, replace[k]);
        }
        return s;
    };
    EduRequest.prototype.uls = function (i, lf) {
        switch (lf) {
            case 'tt': return this.ttls(i);
        }
        return this.ls(i);
    };
    EduRequest.prototype.localize = function (s) {
        for (var i = 0; i < 10; i++) {
            var m = /\{(?:|([a-z]{2}):)([0-9]{4,5})\}/g.exec(s);
            if (!m)
                break;
            s = s.replace(m[0], this.uls(parseInt(m[2]), m[1]));
        }
        return s;
    };
    EduRequest.prototype.ails = function (s, params) {
        if (!s)
            ASC.dieError('1993235492', s);
        var t = this.aiLangs[s];
        if (!t) {
            t = s.split('|')[0];
            if (t[2] == ':')
                t = t.slice(3);
        }
        if (!t)
            ASC.dieError('3849862994', [s, t]);
        if (t.includes('{')) {
            if (params) {
                t = t.replace(/\{([a-zA-Z0-9_]+)\}/g, function (match, field) {
                    var val = params[field];
                    return (val === undefined || val === null) ? match : String(val);
                });
            }
        }
        return t;
    };
    EduRequest.prototype.timezone_date = function (time) {
        if (time === void 0) { time = undefined; }
        return this.timezone_datetime(time).substr(0, 10);
    };
    EduRequest.prototype.timezone_datetime = function (time) {
        if (time === void 0) { time = undefined; }
        var d = typeof time == 'number' ? new Date(time * 1000) : new Date();
        var parts;
        try {
            var df = new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: 'numeric',
                day: 'numeric',
                hour: 'numeric',
                minute: 'numeric',
                second: 'numeric',
                hour12: false,
                timeZone: this.props.ttdemo_user ? undefined : this.props.timezone,
            });
            var s = df.format(d);
            parts = /(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)\D+(\d+)/.exec(s);
            parts[4] %= 24;
        }
        catch (e) {
            parts = [
                0,
                d.getMonth() + 1,
                d.getDate(),
                d.getFullYear(),
                d.getHours(),
                d.getMinutes(),
                d.getSeconds()
            ];
        }
        function zpl(i, len) {
            var s = '' + parts[i];
            while (s.length < len)
                s = '0' + s;
            return s;
        }
        return zpl(3, 4) + '-'
            + zpl(1, 2) + '-'
            + zpl(2, 2)
            + ' '
            + zpl(4, 2) + ':'
            + zpl(5, 2) + ':'
            + zpl(6, 2);
    };
    EduRequest.prototype.timezone_datetime2int = function (datetime) {
        return Math.floor((0, lib_date_1.datetime_sql2js)(datetime).getTime() / 1000);
    };
    EduRequest.prototype.substdbi = function (dbid, options) {
        if (options === void 0) { options = {}; }
        return tslib_1.__awaiter(this, void 0, Promise, function () {
            var _this = this;
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4, Promise.resolve().then(function () { return require("../rpr/dbi"); })];
                    case 1: return [2, (_a.sent()).ClientDBI.newInstance(this, function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                            return tslib_1.__generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0: return [4, Promise.resolve().then(function () { return require("../substitution/server/substdbi"); })];
                                    case 1: return [2, (_a.sent()).substDBIAccessor(null, dbid, args)];
                                }
                            });
                        }); }, options)];
                }
            });
        });
    };
    EduRequest.prototype.ttuidocdbi = function (ttgpid, options) {
        if (options === void 0) { options = {}; }
        return tslib_1.__awaiter(this, void 0, Promise, function () {
            var _this = this;
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4, Promise.resolve().then(function () { return require("../rpr/dbi"); })];
                    case 1: return [2, (_a.sent()).ClientDBI.newInstance(this, function (args) { return tslib_1.__awaiter(_this, void 0, void 0, function () {
                            return tslib_1.__generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0: return [4, Promise.resolve().then(function () { return require("../timetable/app/server/ttdoc"); })];
                                    case 1: return [2, (_a.sent()).ttuidocDBIAccessor(null, ttgpid, args)];
                                }
                            });
                        }); }, options)];
                }
            });
        });
    };
    EduRequest.prototype.memoize = function (key, supplier) {
        var vp = this._memoize_cache.get(key);
        if (!vp) {
            vp = supplier();
            this._memoize_cache.set(key, vp);
        }
        return vp;
    };
    EduRequest.prototype.waitSuspense = function (func) {
        return tslib_1.__awaiter(this, void 0, Promise, function () {
            var e_1;
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 1, , 3]);
                        return [2, func()];
                    case 1:
                        e_1 = _a.sent();
                        if (typeof (e_1 === null || e_1 === void 0 ? void 0 : e_1.then) != 'function')
                            throw e_1;
                        return [4, e_1];
                    case 2:
                        _a.sent();
                        return [3, 3];
                    case 3: return [3, 0];
                    case 4: return [2];
                }
            });
        });
    };
    EduRequest.prototype.suspendCall = function (func) {
        return Promise.resolve().then(func);
    };
    EduRequest.prototype.yield = function () {
        return tslib_1.__awaiter(this, void 0, void 0, function () {
            var t;
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        t = Date.now();
                        if (!this.yield_time) {
                            this.yield_time = t + Math.round(40 + Math.random() * 10);
                        }
                        if (t < this.yield_time)
                            return [2];
                        this.yield_time = 0;
                        return [4, new Promise(function (resolve) { return setTimeout(resolve, 4 + Math.random() * 2); })];
                    case 1:
                        _a.sent();
                        return [2];
                }
            });
        });
    };
    return EduRequest;
}());
exports.EduRequest = EduRequest;
var EduRequest_Client = (function (_super) {
    tslib_1.__extends(EduRequest_Client, _super);
    function EduRequest_Client() {
        var _this = this;
        var _a;
        _this = _super.call(this) || this;
        _this.lib_date = new lib_date_1.Lib_date(_this);
        var req_props = ASC.req_props;
        _super.prototype.initRequest.call(_this, req_props || {});
        if (!req_props) {
            if (window && !((_a = window.MobileAppBridge) === null || _a === void 0 ? void 0 : _a.isActive())) {
                ASC.sendErrorJS('9883465806', new Error().stack);
            }
        }
        return _this;
    }
    EduRequest_Client.prototype.maindbi = function (year, options) {
        var _a;
        return tslib_1.__awaiter(this, void 0, Promise, function () {
            return tslib_1.__generator(this, function (_b) {
                switch (_b.label) {
                    case 0: return [4, Promise.resolve().then(function () { return require('../rpr/clientcache'); })];
                    case 1: return [2, (_b.sent()).cachedDBI_async(this, 'maindbi', ASC.strVal(year), tslib_1.__assign(tslib_1.__assign({}, options), { cache: (_a = options.cache) !== null && _a !== void 0 ? _a : false }))];
                }
            });
        });
    };
    EduRequest_Client.prototype.timetabledbi = function (num, options) {
        if (options === void 0) { options = {}; }
        return tslib_1.__awaiter(this, void 0, Promise, function () {
            return tslib_1.__generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4, Promise.resolve().then(function () { return require('../rpr/clientcache'); })];
                    case 1: return [2, (_a.sent()).cachedDBI_async(this, 'ttdbi', num, options)];
                }
            });
        });
    };
    return EduRequest_Client;
}(EduRequest));
exports.EduRequest_Client = EduRequest_Client;
exports.client_req = new EduRequest_Client();
ASC.req = exports.client_req;

