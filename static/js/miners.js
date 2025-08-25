const REFRESH_INTERVAL = 30;

function freshnessDot(ageSec) {
    if (ageSec == null) return '<span class="dot dot-gray" title="No data"></span>';
    if (ageSec <= 2 * REFRESH_INTERVAL) return '<span class="dot dot-green" title="Fresh"></span>';
    if (ageSec <= 5 * REFRESH_INTERVAL) return '<span class="dot dot-yellow" title="Lagging"></span>';
    return '<span class="dot dot-red" title="Stale"></span>';
}

function fmtLastSeen(lastSeenIso) {
    if (!lastSeenIso) return '—';
    try {
        return new Date(lastSeenIso).toLocaleString();
    } catch {
        return lastSeenIso;
    }
}

async function fetchMiners() {
    const res = await fetch('/api/miners');
    const payload = await res.json();
    const {miners} = payload;
    const tbody = document.getElementById('miner-table');
    tbody.innerHTML = '';
    miners.forEach(miner => {
        const tr = document.createElement('tr');
        if (miner.is_stale) tr.classList.add('stale');
        tr.innerHTML = `
      <td>${freshnessDot(miner.age_sec)} ${miner.status}</td>
      <td>${miner.model}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(miner.ip)}">${miner.ip}</a></td>
      <td>${fmtLastSeen(miner.last_seen)}</td>
      <td><a href="http://${miner.ip}/" target="_blank" rel="noopener">Web UI</a></td>
    `;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});
const FT = "9.10.1";

function $T() {
    typeof __VUE_I18N_FULL_INSTALL__ != "boolean" && (Ui().__VUE_I18N_FULL_INSTALL__ = !0),
    typeof __VUE_I18N_LEGACY_API__ != "boolean" && (Ui().__VUE_I18N_LEGACY_API__ = !0),
    typeof __INTLIFY_JIT_COMPILATION__ != "boolean" && (Ui().__INTLIFY_JIT_COMPILATION__ = !1),
    typeof __INTLIFY_DROP_MESSAGE_COMPILER__ != "boolean" && (Ui().__INTLIFY_DROP_MESSAGE_COMPILER__ = !1),
    typeof __INTLIFY_PROD_DEVTOOLS__ != "boolean" && (Ui().__INTLIFY_PROD_DEVTOOLS__ = !1)
}

const n1 = bT.__EXTEND_POINT__
    , Ni = pp(n1);
Ni(),
    Ni(),
    Ni(),
    Ni(),
    Ni(),
    Ni(),
    Ni(),
    Ni(),
    Ni();
const i1 = Xn.__EXTEND_POINT__
    , an = pp(i1)
    , Ls = {
    UNEXPECTED_RETURN_TYPE: i1,
    INVALID_ARGUMENT: an(),
    MUST_BE_CALL_SETUP_TOP: an(),
    NOT_INSTALLED: an(),
    NOT_AVAILABLE_IN_LEGACY_MODE: an(),
    REQUIRED_VALUE: an(),
    INVALID_VALUE: an(),
    CANNOT_SETUP_VUE_DEVTOOLS_PLUGIN: an(),
    NOT_INSTALLED_WITH_PROVIDE: an(),
    UNEXPECTED_ERROR: an(),
    NOT_COMPATIBLE_LEGACY_VUE_I18N: an(),
    BRIDGE_SUPPORT_VUE_2_ONLY: an(),
    MUST_DEFINE_I18N_OPTION_IN_ALLOW_COMPOSITION: an(),
    NOT_AVAILABLE_COMPOSITION_IN_LEGACY: an(),
    __EXTEND_POINT__: an()
};

function Fs(e, ...t) {
    return ko(e, null, void 0)
}

const Yh = Oa("__translateVNode")
    , Xh = Oa("__datetimeParts")
    , jh = Oa("__numberParts")
    , a1 = Oa("__setPluralRules")
    , r1 = Oa("__injectWithOption")
    , Gh = Oa("__dispose");

function Tl(e) {
    if (!Kt(e))
        return e;
    for (const t in e)
        if (vu(e, t))
            if (!t.includes("."))
                Kt(e[t]) && Tl(e[t]);
            else {
                const s = t.split(".")
                    , a = s.length - 1;
                let o = e
                    , l = !1;
                for (let u = 0; u < a; u++) {
                    if (s[u] in o || (o[s[u]] = {}),
                        !Kt(o[s[u]])) {
                        l = !0;
                        break
                    }
                    o = o[s[u]]
                }
                l || (o[s[a]] = e[t],
                    delete e[t]),
                Kt(o[s[a]]) && Tl(o[s[a]])
            }
    return e
}

function Ju(e, t) {
    const {messages: s, __i18n: a, messageResolver: o, flatJson: l} = t
        , u = Tt(s) ? s : hs(a) ? {} : {
        [e]: {}
    };
    if (hs(a) && a.forEach(p => {
            if ("locale" in p && "resource" in p) {
                const {locale: g, resource: y} = p;
                g ? (u[g] = u[g] || {},
                    Uc(y, u[g])) : Uc(y, u)
            } else
                it(p) && Uc(JSON.parse(p), u)
        }
    ),
    o == null && l)
        for (const p in u)
            vu(u, p) && Tl(u[p]);
    return u
}

function o1(e) {
    return e.type
}

function l1(e, t, s) {
    let a = Kt(t.messages) ? t.messages : {};
    "__i18nGlobal" in s && (a = Ju(e.locale.value, {
        messages: a,
        __i18n: s.__i18nGlobal
    }));
    const o = Object.keys(a);
    o.length && o.forEach(l => {
            e.mergeLocaleMessage(l, a[l])
        }
    );
    {
        if (Kt(t.datetimeFormats)) {
            const l = Object.keys(t.datetimeFormats);
            l.length && l.forEach(u => {
                    e.mergeDateTimeFormat(u, t.datetimeFormats[u])
                }
            )
        }
        if (Kt(t.numberFormats)) {
            const l = Object.keys(t.numberFormats);
            l.length && l.forEach(u => {
                    e.mergeNumberFormat(u, t.numberFormats[u])
                }
            )
        }
    }
}

function Wm(e) {
    return ae(Kn, null, e, 0)
}

const Um = "__INTLIFY_META__"
    , Ym = () => []
    , BT = () => !1;
let Xm = 0;

function jm(e) {
    return (t, s, a, o) => e(s, a, Et() || void 0, o)
}

const HT = () => {
        const e = Et();
        let t = null;
        return e && (t = o1(e)[Um]) ? {
            [Um]: t
        } : null
    }
;

function bp(e = {}, t) {
    const {__root: s, __injectWithOption: a} = e
        , o = s === void 0
        , l = e.flatJson
        , u = mu ? Se : Bs
        , p = !!e.translateExistCompatible;
    let g = Dt(e.inheritLocale) ? e.inheritLocale : !0;
    const y = u(s && g ? s.locale.value : it(e.locale) ? e.locale : io)
        ,
        v = u(s && g ? s.fallbackLocale.value : it(e.fallbackLocale) || hs(e.fallbackLocale) || Tt(e.fallbackLocale) || e.fallbackLocale === !1 ? e.fallbackLocale : y.value)
        , w = u(Ju(y.value, e))
        , C = u(Tt(e.datetimeFormats) ? e.datetimeFormats : {
            [y.value]: {}
        })
        , T = u(Tt(e.numberFormats) ? e.numberFormats : {
            [y.value]: {}
        });
    let I = s ? s.missingWarn : Dt(e.missingWarn) || Ia(e.missingWarn) ? e.missingWarn : !0
        , A = s ? s.fallbackWarn : Dt(e.fallbackWarn) || Ia(e.fallbackWarn) ? e.fallbackWarn : !0
        , R = s ? s.fallbackRoot : Dt(e.fallbackRoot) ? e.fallbackRoot : !0
        , P = !!e.fallbackFormat
        , M = os(e.missing) ? e.missing : null
        , O = os(e.missing) ? jm(e.missing) : null
        , F = os(e.postTranslation) ? e.postTranslation : null
        , $ = s ? s.warnHtmlMessage : Dt(e.warnHtmlMessage) ? e.warnHtmlMessage : !0
        , V = !!e.escapeParameter;
    const G = s ? s.modifiers : Tt(e.modifiers) ? e.modifiers : {};
    let ie = e.pluralRules || s && s.pluralRules, te;
    te = (() => {
            o && Rm(null);
            const xe = {
                version: FT,
                locale: y.value,
                fallbackLocale: v.value,
                messages: w.value,
                modifiers: G,
                pluralRules: ie,
                missing: O === null ? void 0 : O,
                missingWarn: I,
                fallbackWarn: A,
                fallbackFormat: P,
                unresolving: !0,
                postTranslation: F === null ? void 0 : F,
                warnHtmlMessage: $,
                escapeParameter: V,
                messageResolver: e.messageResolver,
                messageCompiler: e.messageCompiler,
                __meta: {
                    framework: "vue"
                }
            };
            xe.datetimeFormats = C.value,
                xe.numberFormats = T.value,
                xe.__datetimeFormatters = Tt(te) ? te.__datetimeFormatters : void 0,
                xe.__numberFormatters = Tt(te) ? te.__numberFormatters : void 0;
            const Re = IT(xe);
            return o && Rm(Re),
                Re
        }
    )(),
        Ho(te, y.value, v.value);

    function le() {
        return [y.value, v.value, w.value, C.value, T.value]
    }

    const oe = re({
        get: () => y.value,
        set: xe => {
            y.value = xe,
                te.locale = y.value
        }
    })
        , ve = re({
        get: () => v.value,
        set: xe => {
            v.value = xe,
                te.fallbackLocale = v.value,
                Ho(te, y.value, xe)
        }
    })
        , be = re(() => w.value)
        , de = re(() => C.value)
        , J = re(() => T.value);

    function ue() {
        return os(F) ? F : null
    }

    function fe(xe) {
        F = xe,
            te.postTranslation = xe
    }

    function Me() {
        return M
    }

    function Xe(xe) {
        xe !== null && (O = jm(xe)),
            M = xe,
            te.missing = O
    }

    const Be = (xe, Re, lt, vt, qt, is) => {
            le();
            let bs;
            try {
                __INTLIFY_PROD_DEVTOOLS__,
                o || (te.fallbackContext = s ? TT() : void 0),
                    bs = xe(te)
            } finally {
                __INTLIFY_PROD_DEVTOOLS__,
                o || (te.fallbackContext = void 0)
            }
            if (lt !== "translate exists" && Is(bs) && bs === Zu || lt === "translate exists" && !bs) {
                const [Ss, Hn] = Re();
                return s && R ? vt(s) : qt(Ss)
            } else {
                if (is(bs))
                    return bs;
                throw Fs(Ls.UNEXPECTED_RETURN_TYPE)
            }
        }
    ;

    function je(...xe) {
        return Be(Re => Reflect.apply($m, null, [Re, ...xe]), () => zh(...xe), "translate", Re => Reflect.apply(Re.t, Re, [...xe]), Re => Re, Re => it(Re))
    }

    function tt(...xe) {
        const [Re, lt, vt] = xe;
        if (vt && !Kt(vt))
            throw Fs(Ls.INVALID_ARGUMENT);
        return je(Re, lt, Vs({
            resolvedMessage: !0
        }, vt || {}))
    }

    function ft(...xe) {
        return Be(Re => Reflect.apply(Bm, null, [Re, ...xe]), () => Wh(...xe), "datetime format", Re => Reflect.apply(Re.d, Re, [...xe]), () => Lm, Re => it(Re))
    }

    function mt(...xe) {
        return Be(Re => Reflect.apply(Vm, null, [Re, ...xe]), () => Uh(...xe), "number format", Re => Reflect.apply(Re.n, Re, [...xe]), () => Lm, Re => it(Re))
    }

    function bt(xe) {
        return xe.map(Re => it(Re) || Is(Re) || Dt(Re) ? Wm(String(Re)) : Re)
    }

    const Ae = {
        normalize: bt,
        interpolate: xe => xe,
        type: "vnode"
    };

    function Ne(...xe) {
        return Be(Re => {
                let lt;
                const vt = Re;
                try {
                    vt.processor = Ae,
                        lt = Reflect.apply($m, null, [vt, ...xe])
                } finally {
                    vt.processor = null
                }
                return lt
            }
            , () => zh(...xe), "translate", Re => Re[Yh](...xe), Re => [Wm(Re)], Re => hs(Re))
    }

    function He(...xe) {
        return Be(Re => Reflect.apply(Vm, null, [Re, ...xe]), () => Uh(...xe), "number format", Re => Re[jh](...xe), Ym, Re => it(Re) || hs(Re))
    }

    function et(...xe) {
        return Be(Re => Reflect.apply(Bm, null, [Re, ...xe]), () => Wh(...xe), "datetime format", Re => Re[Xh](...xe), Ym, Re => it(Re) || hs(Re))
    }

    function dt(xe) {
        ie = xe,
            te.pluralRules = ie
    }

    function Y(xe, Re) {
        return Be(() => {
                if (!xe)
                    return !1;
                const lt = it(Re) ? Re : y.value
                    , vt = we(lt)
                    , qt = te.messageResolver(vt, xe);
                return p ? qt != null : ao(qt) || Cn(qt) || it(qt)
            }
            , () => [xe], "translate exists", lt => Reflect.apply(lt.te, lt, [xe, Re]), BT, lt => Dt(lt))
    }

    function W(xe) {
        let Re = null;
        const lt = Yx(te, v.value, y.value);
        for (let vt = 0; vt < lt.length; vt++) {
            const qt = w.value[lt[vt]] || {}
                , is = te.messageResolver(qt, xe);
            if (is != null) {
                Re = is;
                break
            }
        }
        return Re
    }

    function ce(xe) {
        const Re = W(xe);
        return Re ?? (s ? s.tm(xe) || {} : {})
    }

    function we(xe) {
        return w.value[xe] || {}
    }

    function _e(xe, Re) {
        if (l) {
            const lt = {
                [xe]: Re
            };
            for (const vt in lt)
                vu(lt, vt) && Tl(lt[vt]);
            Re = lt[xe]
        }
        w.value[xe] = Re,
            te.messages = w.value
    }

    function Oe(xe, Re) {
        w.value[xe] = w.value[xe] || {};
        const lt = {
            [xe]: Re
        };
        if (l)
            for (const vt in lt)
                vu(lt, vt) && Tl(lt[vt]);
        Re = lt[xe],
            Uc(Re, w.value[xe]),
            te.messages = w.value
    }

    function qe(xe) {
        return C.value[xe] || {}
    }

    function We(xe, Re) {
        C.value[xe] = Re,
            te.datetimeFormats = C.value,
            Hm(te, xe, Re)
    }

    function Ge(xe, Re) {
        C.value[xe] = Vs(C.value[xe] || {}, Re),
            te.datetimeFormats = C.value,
            Hm(te, xe, Re)
    }

    function Ue(xe) {
        return T.value[xe] || {}
    }

    function ht(xe, Re) {
        T.value[xe] = Re,
            te.numberFormats = T.value,
            zm(te, xe, Re)
    }

    function Ee(xe, Re) {
        T.value[xe] = Vs(T.value[xe] || {}, Re),
            te.numberFormats = T.value,
            zm(te, xe, Re)
    }

    Xm++,
    s && mu && (Ke(s.locale, xe => {
            g && (y.value = xe,
                te.locale = xe,
                Ho(te, y.value, v.value))
        }
    ),
        Ke(s.fallbackLocale, xe => {
                g && (v.value = xe,
                    te.fallbackLocale = xe,
                    Ho(te, y.value, v.value))
            }
        ));
    const ze = {
        id: Xm,
        locale: oe,
        fallbackLocale: ve,
        get inheritLocale() {
            return g
        },
        set inheritLocale(xe) {
            g = xe,
            xe && s && (y.value = s.locale.value,
                v.value = s.fallbackLocale.value,
                Ho(te, y.value, v.value))
        },
        get availableLocales() {
            return Object.keys(w.value).sort()
        },
        messages: be,
        get modifiers() {
            return G
        },
        get pluralRules() {
            return ie || {}
        },
        get isGlobal() {
            return o
        },
        get missingWarn() {
            return I
        },
        set missingWarn(xe) {
            I = xe,
                te.missingWarn = I
        },
        get fallbackWarn() {
            return A
        },
        set fallbackWarn(xe) {
            A = xe,
                te.fallbackWarn = A
        },
        get fallbackRoot() {
            return R
        },
        set fallbackRoot(xe) {
            R = xe
        },
        get fallbackFormat() {
            return P
        },
        set fallbackFormat(xe) {
            P = xe,
                te.fallbackFormat = P
        },
        get warnHtmlMessage() {
            return $
        },
        set warnHtmlMessage(xe) {
            $ = xe,
                te.warnHtmlMessage = xe
        },
        get escapeParameter() {
            return V
        },
        set escapeParameter(xe) {
            V = xe,
                te.escapeParameter = xe
        },
        t: je,
        getLocaleMessage: we,
        setLocaleMessage: _e,
        mergeLocaleMessage: Oe,
        getPostTranslationHandler: ue,
        setPostTranslationHandler: fe,
        getMissingHandler: Me,
        setMissingHandler: Xe,
        [a1]: dt
    };
    return ze.datetimeFormats = de,
        ze.numberFormats = J,
        ze.rt = tt,
        ze.te = Y,
        ze.tm = ce,
        ze.d = ft,
        ze.n = mt,
        ze.getDateTimeFormat = qe,
        ze.setDateTimeFormat = We,
        ze.mergeDateTimeFormat = Ge,
        ze.getNumberFormat = Ue,
        ze.setNumberFormat = ht,
        ze.mergeNumberFormat = Ee,
        ze[r1] = a,
        ze[Yh] = Ne,
        ze[Xh] = et,
        ze[jh] = He,
        ze
}

function VT(e) {
    const t = it(e.locale) ? e.locale : io
        ,
        s = it(e.fallbackLocale) || hs(e.fallbackLocale) || Tt(e.fallbackLocale) || e.fallbackLocale === !1 ? e.fallbackLocale : t
        , a = os(e.missing) ? e.missing : void 0
        , o = Dt(e.silentTranslationWarn) || Ia(e.silentTranslationWarn) ? !e.silentTranslationWarn : !0
        , l = Dt(e.silentFallbackWarn) || Ia(e.silentFallbackWarn) ? !e.silentFallbackWarn : !0
        , u = Dt(e.fallbackRoot) ? e.fallbackRoot : !0
        , p = !!e.formatFallbackMessages
        , g = Tt(e.modifiers) ? e.modifiers : {}
        , y = e.pluralizationRules
        , v = os(e.postTranslation) ? e.postTranslation : void 0
        , w = it(e.warnHtmlInMessage) ? e.warnHtmlInMessage !== "off" : !0
        , C = !!e.escapeParameterHtml
        , T = Dt(e.sync) ? e.sync : !0;
    let I = e.messages;
    if (Tt(e.sharedMessages)) {
        const V = e.sharedMessages;
        I = Object.keys(V).reduce((ie, te) => {
                const ne = ie[te] || (ie[te] = {});
                return Vs(ne, V[te]),
                    ie
            }
            , I || {})
    }
    const {__i18n: A, __root: R, __injectWithOption: P} = e
        , M = e.datetimeFormats
        , O = e.numberFormats
        , F = e.flatJson
        , $ = e.translateExistCompatible;
    return {
        locale: t,
        fallbackLocale: s,
        messages: I,
        flatJson: F,
        datetimeFormats: M,
        numberFormats: O,
        missing: a,
        missingWarn: o,
        fallbackWarn: l,
        fallbackRoot: u,
        fallbackFormat: p,
        modifiers: g,
        pluralRules: y,
        postTranslation: v,
        warnHtmlMessage: w,
        escapeParameter: C,
        messageResolver: e.messageResolver,
        inheritLocale: T,
        translateExistCompatible: $,
        __i18n: A,
        __root: R,
        __injectWithOption: P
    }
}

function qh(e = {}, t) {
    {
        const s = bp(VT(e))
            , {__extender: a} = e
            , o = {
            id: s.id,
            get locale() {
                return s.locale.value
            },
            set locale(l) {
                s.locale.value = l
            },
            get fallbackLocale() {
                return s.fallbackLocale.value
            },
            set fallbackLocale(l) {
                s.fallbackLocale.value = l
            },
            get messages() {
                return s.messages.value
            },
            get datetimeFormats() {
                return s.datetimeFormats.value
            },
            get numberFormats() {
                return s.numberFormats.value
            },
            get availableLocales() {
                return s.availableLocales
            },
            get formatter() {
                return {
                    interpolate() {
                        return []
                    }
                }
            },
            set formatter(l) {
            },
            get missing() {
                return s.getMissingHandler()
            },
            set missing(l) {
                s.setMissingHandler(l)
            },
            get silentTranslationWarn() {
                return Dt(s.missingWarn) ? !s.missingWarn : s.missingWarn
            },
            set silentTranslationWarn(l) {
                s.missingWarn = Dt(l) ? !l : l
            },
            get silentFallbackWarn() {
                return Dt(s.fallbackWarn) ? !s.fallbackWarn : s.fallbackWarn
            },
            set silentFallbackWarn(l) {
                s.fallbackWarn = Dt(l) ? !l : l
            },
            get modifiers() {
                return s.modifiers
            },
            get formatFallbackMessages() {
                return s.fallbackFormat
            },
            set formatFallbackMessages(l) {
                s.fallbackFormat = l
            },
            get postTranslation() {
                return s.getPostTranslationHandler()
            },
            set postTranslation(l) {
                s.setPostTranslationHandler(l)
            },
            get sync() {
                return s.inheritLocale
            },
            set sync(l) {
                s.inheritLocale = l
            },
            get warnHtmlInMessage() {
                return s.warnHtmlMessage ? "warn" : "off"
            },
            set warnHtmlInMessage(l) {
                s.warnHtmlMessage = l !== "off"
            },
            get escapeParameterHtml() {
                return s.escapeParameter
            },
            set escapeParameterHtml(l) {
                s.escapeParameter = l
            },
            get preserveDirectiveContent() {
                return !0
            },
            set preserveDirectiveContent(l) {
            },
            get pluralizationRules() {
                return s.pluralRules || {}
            },
            __composer: s,
            t(...l) {
                const [u, p, g] = l
                    , y = {};
                let v = null
                    , w = null;
                if (!it(u))
                    throw Fs(Ls.INVALID_ARGUMENT);
                const C = u;
                return it(p) ? y.locale = p : hs(p) ? v = p : Tt(p) && (w = p),
                    hs(g) ? v = g : Tt(g) && (w = g),
                    Reflect.apply(s.t, s, [C, v || w || {}, y])
            },
            rt(...l) {
                return Reflect.apply(s.rt, s, [...l])
            },
            tc(...l) {
                const [u, p, g] = l
                    , y = {
                    plural: 1
                };
                let v = null
                    , w = null;
                if (!it(u))
                    throw Fs(Ls.INVALID_ARGUMENT);
                const C = u;
                return it(p) ? y.locale = p : Is(p) ? y.plural = p : hs(p) ? v = p : Tt(p) && (w = p),
                    it(g) ? y.locale = g : hs(g) ? v = g : Tt(g) && (w = g),
                    Reflect.apply(s.t, s, [C, v || w || {}, y])
            },
            te(l, u) {
                return s.te(l, u)
            },
            tm(l) {
                return s.tm(l)
            },
            getLocaleMessage(l) {
                return s.getLocaleMessage(l)
            },
            setLocaleMessage(l, u) {
                s.setLocaleMessage(l, u)
            },
            mergeLocaleMessage(l, u) {
                s.mergeLocaleMessage(l, u)
            },
            d(...l) {
                return Reflect.apply(s.d, s, [...l])
            },
            getDateTimeFormat(l) {
                return s.getDateTimeFormat(l)
            },
            setDateTimeFormat(l, u) {
                s.setDateTimeFormat(l, u)
            },
            mergeDateTimeFormat(l, u) {
                s.mergeDateTimeFormat(l, u)
            },
            n(...l) {
                return Reflect.apply(s.n, s, [...l])
            },
            getNumberFormat(l) {
                return s.getNumberFormat(l)
            },
            setNumberFormat(l, u) {
                s.setNumberFormat(l, u)
            },
            mergeNumberFormat(l, u) {
                s.mergeNumberFormat(l, u)
            },
            getChoiceIndex(l, u) {
                return -1
            }
        };
        return o.__extender = a,
            o
    }
}

const yp = {
    tag: {
        type: [String, Object]
    },
    locale: {
        type: String
    },
    scope: {
        type: String,
        validator: e => e === "parent" || e === "global",
        default: "parent"
    },
    i18n: {
        type: Object
    }
};

function zT({slots: e}, t) {
    return t.length === 1 && t[0] === "default" ? (e.default ? e.default() : []).reduce((a, o) => [...a, ...o.type === Ct ? o.children : [o]], []) : t.reduce((s, a) => {
            const o = e[a];
            return o && (s[a] = o()),
                s
        }
        , {})
}

function c1(e) {
    return Ct
}

const WT = Ce({
    name: "i18n-t",
    props: Vs({
        keypath: {
            type: String,
            required: !0
        },
        plural: {
            type: [Number, String],
            validator: e => Is(e) || !isNaN(e)
        }
    }, yp),
    setup(e, t) {
        const {slots: s, attrs: a} = t
            , o = e.i18n || Ql({
            useScope: e.scope,
            __useComponent: !0
        });
        return () => {
            const l = Object.keys(s).filter(w => w !== "_")
                , u = {};
            e.locale && (u.locale = e.locale),
            e.plural !== void 0 && (u.plural = it(e.plural) ? +e.plural : e.plural);
            const p = zT(t, l)
                , g = o[Yh](e.keypath, p, u)
                , y = Vs({}, a)
                , v = it(e.tag) || Kt(e.tag) ? e.tag : c1();
            return jt(v, y, g)
        }
    }
})
    , Gm = WT;

function UT(e) {
    return hs(e) && !it(e[0])
}

function u1(e, t, s, a) {
    const {slots: o, attrs: l} = t;
    return () => {
        const u = {
            part: !0
        };
        let p = {};
        e.locale && (u.locale = e.locale),
            it(e.format) ? u.key = e.format : Kt(e.format) && (it(e.format.key) && (u.key = e.format.key),
                p = Object.keys(e.format).reduce((C, T) => s.includes(T) ? Vs({}, C, {
                    [T]: e.format[T]
                }) : C, {}));
        const g = a(e.value, u, p);
        let y = [u.key];
        hs(g) ? y = g.map((C, T) => {
                const I = o[C.type]
                    , A = I ? I({
                    [C.type]: C.value,
                    index: T,
                    parts: g
                }) : [C.value];
                return UT(A) && (A[0].key = `${C.type}-${T}`),
                    A
            }
        ) : it(g) && (y = [g]);
        const v = Vs({}, l)
            , w = it(e.tag) || Kt(e.tag) ? e.tag : c1();
        return jt(w, v, y)
    }
}

const YT = Ce({
    name: "i18n-n",
    props: Vs({
        value: {
            type: Number,
            required: !0
        },
        format: {
            type: [String, Object]
        }
    }, yp),
    setup(e, t) {
        const s = e.i18n || Ql({
            useScope: "parent",
            __useComponent: !0
        });
        return u1(e, t, s1, (...a) => s[jh](...a))
    }
})
    , qm = YT
    , XT = Ce({
    name: "i18n-d",
    props: Vs({
        value: {
            type: [Number, Date],
            required: !0
        },
        format: {
            type: [String, Object]
        }
    }, yp),
    setup(e, t) {
        const s = e.i18n || Ql({
            useScope: "parent",
            __useComponent: !0
        });
        return u1(e, t, t1, (...a) => s[Xh](...a))
    }
})
    , Km = XT;

function jT(e, t) {
    const s = e;
    if (e.mode === "composition")
        return s.__getInstance(t) || e.global;
    {
        const a = s.__getInstance(t);
        return a != null ? a.__composer : e.global.__composer
    }
}

function GT(e) {
    const t = u => {
            const {instance: p, modifiers: g, value: y} = u;
            if (!p || !p.$)
                throw Fs(Ls.UNEXPECTED_ERROR);
            const v = jT(e, p.$)
                , w = Zm(y);
            return [Reflect.apply(v.t, v, [...Jm(w)]), v]
        }
    ;
    return {
        created: (u, p) => {
            const [g, y] = t(p);
            mu && e.global === y && (u.__i18nWatcher = Ke(y.locale, () => {
                    p.instance && p.instance.$forceUpdate()
                }
            )),
                u.__composer = y,
                u.textContent = g
        }
        ,
        unmounted: u => {
            mu && u.__i18nWatcher && (u.__i18nWatcher(),
                u.__i18nWatcher = void 0,
                delete u.__i18nWatcher),
            u.__composer && (u.__composer = void 0,
                delete u.__composer)
        }
        ,
        beforeUpdate: (u, {value: p}) => {
            if (u.__composer) {
                const g = u.__composer
                    , y = Zm(p);
                u.textContent = Reflect.apply(g.t, g, [...Jm(y)])
            }
        }
        ,
        getSSRProps: u => {
            const [p] = t(u);
            return {
                textContent: p
            }
        }
    }
}

function Zm(e) {
    if (it(e))
        return {
            path: e
        };
    if (Tt(e)) {
        if (!("path" in e))
            throw Fs(Ls.REQUIRED_VALUE, "path");
        return e
    } else
        throw Fs(Ls.INVALID_VALUE)
}

function Jm(e) {
    const {path: t, locale: s, args: a, choice: o, plural: l} = e
        , u = {}
        , p = a || {};
    return it(s) && (u.locale = s),
    Is(o) && (u.plural = o),
    Is(l) && (u.plural = l),
        [t, p, u]
}

function qT(e, t, ...s) {
    const a = Tt(s[0]) ? s[0] : {}
        , o = !!a.useI18nComponentName;
    (Dt(a.globalInstall) ? a.globalInstall : !0) && ([o ? "i18n" : Gm.name, "I18nT"].forEach(u => e.component(u, Gm)),
        [qm.name, "I18nN"].forEach(u => e.component(u, qm)),
        [Km.name, "I18nD"].forEach(u => e.component(u, Km))),
        e.directive("t", GT(t))
}

function KT(e, t, s) {
    return {
        beforeCreate() {
            const a = Et();
            if (!a)
                throw Fs(Ls.UNEXPECTED_ERROR);
            const o = this.$options;
            if (o.i18n) {
                const l = o.i18n;
                if (o.__i18n && (l.__i18n = o.__i18n),
                    l.__root = t,
                this === this.$root)
                    this.$i18n = Qm(e, l);
                else {
                    l.__injectWithOption = !0,
                        l.__extender = s.__vueI18nExtend,
                        this.$i18n = qh(l);
                    const u = this.$i18n;
                    u.__extender && (u.__disposer = u.__extender(this.$i18n))
                }
            } else if (o.__i18n)
                if (this === this.$root)
                    this.$i18n = Qm(e, o);
                else {
                    this.$i18n = qh({
                        __i18n: o.__i18n,
                        __injectWithOption: !0,
                        __extender: s.__vueI18nExtend,
                        __root: t
                    });
                    const l = this.$i18n;
                    l.__extender && (l.__disposer = l.__extender(this.$i18n))
                }
            else
                this.$i18n = e;
            o.__i18nGlobal && l1(t, o, o),
                this.$t = (...l) => this.$i18n.t(...l),
                this.$rt = (...l) => this.$i18n.rt(...l),
                this.$tc = (...l) => this.$i18n.tc(...l),
                this.$te = (l, u) => this.$i18n.te(l, u),
                this.$d = (...l) => this.$i18n.d(...l),
                this.$n = (...l) => this.$i18n.n(...l),
                this.$tm = l => this.$i18n.tm(l),
                s.__setInstance(a, this.$i18n)
        },
        mounted() {
        },
        unmounted() {
            const a = Et();
            if (!a)
                throw Fs(Ls.UNEXPECTED_ERROR);
            const o = this.$i18n;
            delete this.$t,
                delete this.$rt,
                delete this.$tc,
                delete this.$te,
                delete this.$d,
                delete this.$n,
                delete this.$tm,
            o.__disposer && (o.__disposer(),
                delete o.__disposer,
                delete o.__extender),
                s.__deleteInstance(a),
                delete this.$i18n
        }
    }
}

function Qm(e, t) {
    e.locale = t.locale || e.locale,
        e.fallbackLocale = t.fallbackLocale || e.fallbackLocale,
        e.missing = t.missing || e.missing,
        e.silentTranslationWarn = t.silentTranslationWarn || e.silentFallbackWarn,
        e.silentFallbackWarn = t.silentFallbackWarn || e.silentFallbackWarn,
        e.formatFallbackMessages = t.formatFallbackMessages || e.formatFallbackMessages,
        e.postTranslation = t.postTranslation || e.postTranslation,
        e.warnHtmlInMessage = t.warnHtmlInMessage || e.warnHtmlInMessage,
        e.escapeParameterHtml = t.escapeParameterHtml || e.escapeParameterHtml,
        e.sync = t.sync || e.sync,
        e.__composer[a1](t.pluralizationRules || e.pluralizationRules);
    const s = Ju(e.locale, {
        messages: t.messages,
        __i18n: t.__i18n
    });
    return Object.keys(s).forEach(a => e.mergeLocaleMessage(a, s[a])),
    t.datetimeFormats && Object.keys(t.datetimeFormats).forEach(a => e.mergeDateTimeFormat(a, t.datetimeFormats[a])),
    t.numberFormats && Object.keys(t.numberFormats).forEach(a => e.mergeNumberFormat(a, t.numberFormats[a])),
        e
}

const ZT = Oa("global-vue-i18n");

function JT(e = {}, t) {
    const s = __VUE_I18N_LEGACY_API__ && Dt(e.legacy) ? e.legacy : __VUE_I18N_LEGACY_API__
        , a = Dt(e.globalInjection) ? e.globalInjection : !0
        , o = __VUE_I18N_LEGACY_API__ && s ? !!e.allowComposition : !0
        , l = new Map
        , [u, p] = QT(e, s)
        , g = Oa("");

    function y(C) {
        return l.get(C) || null
    }

    function v(C, T) {
        l.set(C, T)
    }

    function w(C) {
        l.delete(C)
    }

    {
        const C = {
            get mode() {
                return __VUE_I18N_LEGACY_API__ && s ? "legacy" : "composition"
            },
            get allowComposition() {
                return o
            },
            async install(T, ...I) {
                if (T.__VUE_I18N_SYMBOL__ = g,
                    T.provide(T.__VUE_I18N_SYMBOL__, C),
                    Tt(I[0])) {
                    const P = I[0];
                    C.__composerExtend = P.__composerExtend,
                        C.__vueI18nExtend = P.__vueI18nExtend
                }
                let A = null;
                !s && a && (A = lI(T, C.global)),
                __VUE_I18N_FULL_INSTALL__ && qT(T, C, ...I),
                __VUE_I18N_LEGACY_API__ && s && T.mixin(KT(p, p.__composer, C));
                const R = T.unmount;
                T.unmount = () => {
                    A && A(),
                        C.dispose(),
                        R()
                }
            },
            get global() {
                return p
            },
            dispose() {
                u.stop()
            },
            __instances: l,
            __getInstance: y,
            __setInstance: v,
            __deleteInstance: w
        };
        return C
    }
}

function Ql(e = {}) {
    const t = Et();
    if (t == null)
        throw Fs(Ls.MUST_BE_CALL_SETUP_TOP);
    if (!t.isCE && t.appContext.app != null && !t.appContext.app.__VUE_I18N_SYMBOL__)
        throw Fs(Ls.NOT_INSTALLED);
    const s = eI(t)
        , a = sI(s)
        , o = o1(t)
        , l = tI(e, o);
    if (__VUE_I18N_LEGACY_API__ && s.mode === "legacy" && !e.__useComponent) {
        if (!s.allowComposition)
            throw Fs(Ls.NOT_AVAILABLE_IN_LEGACY_MODE);
        return rI(t, l, a, e)
    }
    if (l === "global")
        return l1(a, e, o),
            a;
    if (l === "parent") {
        let g = nI(s, t, e.__useComponent);
        return g == null && (g = a),
            g
    }
    const u = s;
    let p = u.__getInstance(t);
    if (p == null) {
        const g = Vs({}, e);
        "__i18n" in o && (g.__i18n = o.__i18n),
        a && (g.__root = a),
            p = bp(g),
        u.__composerExtend && (p[Gh] = u.__composerExtend(p)),
            aI(u, t, p),
            u.__setInstance(t, p)
    }
    return p
}

function QT(e, t, s) {
    const a = $f();
    {
        const o = __VUE_I18N_LEGACY_API__ && t ? a.run(() => qh(e)) : a.run(() => bp(e));
        if (o == null)
            throw Fs(Ls.UNEXPECTED_ERROR);
        return [a, o]
    }
}

function eI(e) {
    {
        const t = st(e.isCE ? ZT : e.appContext.app.__VUE_I18N_SYMBOL__);
        if (!t)
            throw Fs(e.isCE ? Ls.NOT_INSTALLED_WITH_PROVIDE : Ls.UNEXPECTED_ERROR);
        return t
    }
}

function tI(e, t) {
    return Ku(e) ? "__i18n" in t ? "local" : "global" : e.useScope ? e.useScope : "local"
}

function sI(e) {
    return e.mode === "composition" ? e.global : e.global.__composer
}

function nI(e, t, s = !1) {
    let a = null;
    const o = t.root;
    let l = iI(t, s);
    for (; l != null;) {
        const u = e;
        if (e.mode === "composition")
            a = u.__getInstance(l);
        else if (__VUE_I18N_LEGACY_API__) {
            const p = u.__getInstance(l);
            p != null && (a = p.__composer,
            s && a && !a[r1] && (a = null))
        }
        if (a != null || o === l)
            break;
        l = l.parent
    }
    return a
}

function iI(e, t = !1) {
    return e == null ? null : t && e.vnode.ctx || e.parent
}

function aI(e, t, s) {
    $t(() => {
        }
        , t),
        hr(() => {
                const a = s;
                e.__deleteInstance(t);
                const o = a[Gh];
                o && (o(),
                    delete a[Gh])
            }
            , t)
}

function rI(e, t, s, a = {}) {
    const o = t === "local"
        , l = Bs(null);
    if (o && e.proxy && !(e.proxy.$options.i18n || e.proxy.$options.__i18n))
        throw Fs(Ls.MUST_DEFINE_I18N_OPTION_IN_ALLOW_COMPOSITION);
    const u = Dt(a.inheritLocale) ? a.inheritLocale : !it(a.locale)
        , p = Se(!o || u ? s.locale.value : it(a.locale) ? a.locale : io)
        ,
        g = Se(!o || u ? s.fallbackLocale.value : it(a.fallbackLocale) || hs(a.fallbackLocale) || Tt(a.fallbackLocale) || a.fallbackLocale === !1 ? a.fallbackLocale : p.value)
        , y = Se(Ju(p.value, a))
        , v = Se(Tt(a.datetimeFormats) ? a.datetimeFormats : {
            [p.value]: {}
        })
        , w = Se(Tt(a.numberFormats) ? a.numberFormats : {
            [p.value]: {}
        })
        , C = o ? s.missingWarn : Dt(a.missingWarn) || Ia(a.missingWarn) ? a.missingWarn : !0
        , T = o ? s.fallbackWarn : Dt(a.fallbackWarn) || Ia(a.fallbackWarn) ? a.fallbackWarn : !0
        , I = o ? s.fallbackRoot : Dt(a.fallbackRoot) ? a.fallbackRoot : !0
        , A = !!a.fallbackFormat
        , R = os(a.missing) ? a.missing : null
        , P = os(a.postTranslation) ? a.postTranslation : null
        , M = o ? s.warnHtmlMessage : Dt(a.warnHtmlMessage) ? a.warnHtmlMessage : !0
        , O = !!a.escapeParameter
        , F = o ? s.modifiers : Tt(a.modifiers) ? a.modifiers : {}
        , $ = a.pluralRules || o && s.pluralRules;

    function V() {
        return [p.value, g.value, y.value, v.value, w.value]
    }

    const G = re({
        get: () => l.value ? l.value.locale.value : p.value,
        set: W => {
            l.value && (l.value.locale.value = W),
                p.value = W
        }
    })
        , ie = re({
        get: () => l.value ? l.value.fallbackLocale.value : g.value,
        set: W => {
            l.value && (l.value.fallbackLocale.value = W),
                g.value = W
        }
    })
        , te = re(() => l.value ? l.value.messages.value : y.value)
        , ne = re(() => v.value)
        , le = re(() => w.value);

    function oe() {
        return l.value ? l.value.getPostTranslationHandler() : P
    }

    function ve(W) {
        l.value && l.value.setPostTranslationHandler(W)
    }

    function be() {
        return l.value ? l.value.getMissingHandler() : R
    }

    function de(W) {
        l.value && l.value.setMissingHandler(W)
    }

    function J(W) {
        return V(),
            W()
    }

    function ue(...W) {
        return l.value ? J(() => Reflect.apply(l.value.t, null, [...W])) : J(() => "")
    }

    function fe(...W) {
        return l.value ? Reflect.apply(l.value.rt, null, [...W]) : ""
    }

    function Me(...W) {
        return l.value ? J(() => Reflect.apply(l.value.d, null, [...W])) : J(() => "")
    }

    function Xe(...W) {
        return l.value ? J(() => Reflect.apply(l.value.n, null, [...W])) : J(() => "")
    }

    function Be(W) {
        return l.value ? l.value.tm(W) : {}
    }

    function je(W, ce) {
        return l.value ? l.value.te(W, ce) : !1
    }

    function tt(W) {
        return l.value ? l.value.getLocaleMessage(W) : {}
    }

    function ft(W, ce) {
        l.value && (l.value.setLocaleMessage(W, ce),
            y.value[W] = ce)
    }

    function mt(W, ce) {
        l.value && l.value.mergeLocaleMessage(W, ce)
    }

    function bt(W) {
        return l.value ? l.value.getDateTimeFormat(W) : {}
    }

    function Pe(W, ce) {
        l.value && (l.value.setDateTimeFormat(W, ce),
            v.value[W] = ce)
    }

    function Ae(W, ce) {
        l.value && l.value.mergeDateTimeFormat(W, ce)
    }

    function Ne(W) {
        return l.value ? l.value.getNumberFormat(W) : {}
    }

    function He(W, ce) {
        l.value && (l.value.setNumberFormat(W, ce),
            w.value[W] = ce)
    }

    function et(W, ce) {
        l.value && l.value.mergeNumberFormat(W, ce)
    }

    const dt = {
        get id() {
            return l.value ? l.value.id : -1
        },
        locale: G,
        fallbackLocale: ie,
        messages: te,
        datetimeFormats: ne,
        numberFormats: le,
        get inheritLocale() {
            return l.value ? l.value.inheritLocale : u
        },
        set inheritLocale(W) {
            l.value && (l.value.inheritLocale = W)
        },
        get availableLocales() {
            return l.value ? l.value.availableLocales : Object.keys(y.value)
        },
        get modifiers() {
            return l.value ? l.value.modifiers : F
        },
        get pluralRules() {
            return l.value ? l.value.pluralRules : $
        },
        get isGlobal() {
            return l.value ? l.value.isGlobal : !1
        },
        get missingWarn() {
            return l.value ? l.value.missingWarn : C
        },
        set missingWarn(W) {
            l.value && (l.value.missingWarn = W)
        },
        get fallbackWarn() {
            return l.value ? l.value.fallbackWarn : T
        },
        set fallbackWarn(W) {
            l.value && (l.value.missingWarn = W)
        },
        get fallbackRoot() {
            return l.value ? l.value.fallbackRoot : I
        },
        set fallbackRoot(W) {
            l.value && (l.value.fallbackRoot = W)
        },
        get fallbackFormat() {
            return l.value ? l.value.fallbackFormat : A
        },
        set fallbackFormat(W) {
            l.value && (l.value.fallbackFormat = W)
        },
        get warnHtmlMessage() {
            return l.value ? l.value.warnHtmlMessage : M
        },
        set warnHtmlMessage(W) {
            l.value && (l.value.warnHtmlMessage = W)
        },
        get escapeParameter() {
            return l.value ? l.value.escapeParameter : O
        },
        set escapeParameter(W) {
            l.value && (l.value.escapeParameter = W)
        },
        t: ue,
        getPostTranslationHandler: oe,
        setPostTranslationHandler: ve,
        getMissingHandler: be,
        setMissingHandler: de,
        rt: fe,
        d: Me,
        n: Xe,
        tm: Be,
        te: je,
        getLocaleMessage: tt,
        setLocaleMessage: ft,
        mergeLocaleMessage: mt,
        getDateTimeFormat: bt,
        setDateTimeFormat: Pe,
        mergeDateTimeFormat: Ae,
        getNumberFormat: Ne,
        setNumberFormat: He,
        mergeNumberFormat: et
    };

    function Y(W) {
        W.locale.value = p.value,
            W.fallbackLocale.value = g.value,
            Object.keys(y.value).forEach(ce => {
                    W.mergeLocaleMessage(ce, y.value[ce])
                }
            ),
            Object.keys(v.value).forEach(ce => {
                    W.mergeDateTimeFormat(ce, v.value[ce])
                }
            ),
            Object.keys(w.value).forEach(ce => {
                    W.mergeNumberFormat(ce, w.value[ce])
                }
            ),
            W.escapeParameter = O,
            W.fallbackFormat = A,
            W.fallbackRoot = I,
            W.fallbackWarn = T,
            W.missingWarn = C,
            W.warnHtmlMessage = M
    }

    return ql(() => {
            if (e.proxy == null || e.proxy.$i18n == null)
                throw Fs(Ls.NOT_AVAILABLE_COMPOSITION_IN_LEGACY);
            const W = l.value = e.proxy.$i18n.__composer;
            t === "global" ? (p.value = W.locale.value,
                g.value = W.fallbackLocale.value,
                y.value = W.messages.value,
                v.value = W.datetimeFormats.value,
                w.value = W.numberFormats.value) : o && Y(W)
        }
    ),
        dt
}

const oI = ["locale", "fallbackLocale", "availableLocales"]
    , ev = ["t", "rt", "d", "n", "tm", "te"];

function lI(e, t) {
    const s = Object.create(null);
    return oI.forEach(o => {
            const l = Object.getOwnPropertyDescriptor(t, o);
            if (!l)
                throw Fs(Ls.UNEXPECTED_ERROR);
            const u = Qt(l.value) ? {
                get() {
                    return l.value.value
                },
                set(p) {
                    l.value.value = p
                }
            } : {
                get() {
                    return l.get && l.get()
                }
            };
            Object.defineProperty(s, o, u)
        }
    ),
        e.config.globalProperties.$i18n = s,
        ev.forEach(o => {
                const l = Object.getOwnPropertyDescriptor(t, o);
                if (!l || !l.value)
                    throw Fs(Ls.UNEXPECTED_ERROR);
                Object.defineProperty(e.config.globalProperties, `$${o}`, l)
            }
        ),
        () => {
            delete e.config.globalProperties.$i18n,
                ev.forEach(o => {
                        delete e.config.globalProperties[`$${o}`]
                    }
                )
        }
}

$T();
__INTLIFY_JIT_COMPILATION__ ? Om(MT) : Om(LT);
kT(aT);
CT(Yx);
if (__INTLIFY_PROD_DEVTOOLS__) {
    const e = Ui();
    e.__INTLIFY__ = !0,
        pT(e.__INTLIFY_DEVTOOLS_GLOBAL_HOOK__)
}
const cI = {
    disable: "Disable",
    enable: "Enable",
    restart: "Restart",
    start: "Start",
    stop: "Stop"
}
    , uI = {
    no: "NO",
    warning: "Warning",
    yes: "OK"
}
    , dI = {
    best_share: {
        title: "BestShare"
    },
    boards: {
        NA: "N/A",
        allGood: "All chips are good",
        chipStatus: {
            grey: "Stable chips",
            orange: "Slow chips",
            red: "Critical chips",
            unknown: "Unknown"
        },
        chipStatusTitle: "Chip status",
        errors: "Errors",
        freq: "Frequency",
        power: "Consumption",
        status: {
            disabled: "Disabled",
            disconnected: "Disconnected",
            initializing: "Initializing",
            mining: "Mining",
            stopped: "Stopped",
            unknown: "Unknown"
        },
        tempBoard: "Board temperatures",
        tempChips: "Temperature",
        title: "Board",
        noBoard: "No board",
        undefinedChips: "Undefined chips",
        volt: "Voltage"
    },
    chartChipTemp: {
        title: "Temperature",
        chipTemp: "Temperature",
        fanDuty: "Fan duty"
    },
    chartHashrate: {
        title: "Hashrate",
        hashrate: "Hashrate",
        power: "Power",
        powerConsumption: "Power Consumption",
        watt: "W"
    },
    chartTest: {
        title: "ChartTest"
    },
    charts: {
        hours1: "1 h",
        hours12: "12 h",
        hours24: "24 h",
        hours3: "3 hours",
        hours72: "72 h",
        range: "Range:"
    },
    dev: {
        title: "DevFee"
    },
    editMode: {
        buttons: {
            cancel: "Cancel",
            exit: "Exit without saving",
            reset: "Defaults",
            save: "Save",
            select: "Save selected",
            widgets: "Widgets"
        },
        enterIcon: "Edit layout dashboard",
        footer: {
            caption: "Layout edit mode",
            hint: "you can move, scale, hide widgets"
        },
        header: "Edit mode",
        hideWidgetDialog: {
            cancel: "Cancel",
            description: "Choose which devices to hide this widget",
            header: "Hide widget?",
            submit: "Yes, hide!"
        },
        resetWidgetDialog: {
            cancel: "Cancel",
            description: "Choose which devices to make a reset",
            header: "Reset to default layouts?",
            submit: "Yes, reset!"
        },
        saveDialog: {
            cancel: "Not",
            header: "Save dashboard layout?",
            submit: "Yes, save!"
        },
        transferDescription: "After adding, you need to move down"
    },
    eff: {
        title: "Efficiency"
    },
    errors: {
        footer: "HW",
        title: "Errors"
    },
    fans: {
        title: "Cooling",
        fan: "Fan",
        duty: "Fan duty",
        block: "Block",
        temperature: "Temperature",
        "inlet-outlet": "In-Out",
        mode: "Mode:",
        auto: "Auto",
        manual: "Manual",
        immersion: "Immersion",
        missingCooler: {
            message: "This model does not use coolers",
            title: "No coolers"
        }
    },
    foundBlocks: {
        title: "FoundBlocks"
    },
    hashrate: {
        hashrateReal: "Curr:",
        hashrateIdeal: "Theor:",
        shortTitle: "HR",
        title: "Hashrate"
    },
    pools: {
        activate: "Activate",
        active: "Active",
        confirm: "Change active pool?",
        disabled: "Disabled",
        message: "The pool will be changed to: </br>",
        no: "Do not change",
        offline: "Offline",
        refund: "Refund",
        rejecting: "Rejecting",
        status: "Status",
        title: "Pools",
        unknown: "Unknown",
        user: "user",
        working: "Alive",
        yes: "Yes, change!"
    },
    power: {
        desk: "Estimated data",
        footer: "W",
        watt: "W",
        psu: "PSU",
        title: "Power"
    },
    temp: {
        desk: "Board:",
        footer: "°C | min-max",
        title: "Temperature"
    },
    widgets: {
        Average_Hashrate: "Average hashrate",
        BestShare: "BestShare",
        ChartChiptemp: "Temperature Chart",
        ChartHashrate: "Hashrate Chart",
        ChartTest: "ChartTest",
        Coolers: "Cooling",
        DEVFee: "DevFee",
        Efficiency: "Efficiency",
        Errors: "Errors",
        FoundBlocks: "FoundBlocks",
        Performance: "Performance",
        Plates: "Boards",
        Pools: "Pools",
        Power: "Power",
        Temperature: "Temperature"
    },
    widgetsDialog: {
        selectAll: "Select all",
        title: "Widgets"
    }
}
    , hI = {
    cancel: "Cancel",
    no: "No",
    save: "Save",
    yes: "Yes"
}
    , fI = {
    actionText: "Try updating this or switching to another page",
    text: "Page not found"
}
    , pI = {
    diff5: "Temperatures difference must be 5 or more",
    wrongTopProfile: "Top profile can't be lower than current profile",
    wrongMinProfile: "Min profile can't be higher than current profile",
    duplicate: "Try to add duplicate",
    error: "Error",
    inputDiapason: "Input value must be in diapason",
    noLoop: "Data is not updated",
    noLoopLogs: "Logs is not updated",
    noMethod: "Data is not updated",
    noSettings: "Error loading miner settings",
    noAutotunePresetData: "Error getting autotune preset data",
    passNotSaved: "Password not saved",
    someError: "Something went wrong"
}
    , gI = {
    modal: {
        alertBeta: "Attention! This firmware is not stable and is intended for testing purposes only.",
        releaseNote: "What's new?",
        title: "Firmware update",
        titleFileName: "Firmware file:",
        update: "Update",
        updateButton: "Flash miner",
        updateButtonFlash: "Firmware update...",
        updateCheck: "Save current miner configuration",
        updateCheckNote: "The current configuration of the device will be saved after flashing",
        updateText: "Drop file here or click to upload"
    },
    version: "Version"
}
    , mI = {
    errorMessages: {
        invalidField: "Field is invalid",
        invalidFieldWithExample: "The field is filled incorrectly. Example: ",
        invalidLength: "The length is {count} characters",
        invalidMaxLength: "The maximum length is {count} characters",
        invalidMinMaxValue: "Input value must be in range: ",
        mismatch: "Password mismatch",
        required: "Please enter value",
        warningWorkerFormat: "Contains non-standard characters",
        wrongPassword: "Password is wrong,try [admin]"
    }
}
    , vI = {
    title: "Firmware help"
}
    , bI = {
    events: {
        filter: "Filter:",
        placeHolder: "No events",
        title: "Events in 24h "
    },
    fan: {
        title: "Cooling",
        fan: "Fan",
        mode: "Mode",
        fanDuty: "Fan duty"
    },
    memory: {
        cacheMem: "Cached:",
        freemem: "Free:",
        fullMem: "TOTAL",
        inuse: "In use",
        title: "Memory"
    },
    monitoring: {
        errors: "Errors",
        hashrateAvg: "Average hashrate",
        hashrateCurrent: "Current hashrate",
        hashrateIdeal: "Theoretical hashrate",
        hashrateStock: "Stock hashrate",
        power: "Power",
        tempBoard: "Temp. board",
        tempChips: "Temp. chips",
        title: "Monitoring"
    },
    network: {
        gateway: "Gateway",
        hostname: "",
        labelIp: "IP",
        labelMask: "Netmask",
        mode: "Mode:",
        static: "Static",
        title: "Network status"
    },
    pin: "Pin",
    quickSettings: {
        UIEffects: "UI optimize",
        disable: "Disable",
        enable: "Enable",
        sidebarTheme: "Sidebar menu theme",
        themeUI: "UI theme",
        title: "Quick Actions"
    },
    systemInfo: {
        cgVersion: "CGMiner version",
        compileDate: "Created",
        filesystem: "File System Version",
        hardVersion: "Hardware Version",
        hostname: "Hostname",
        installationType: "Installation Type",
        minerFirmware: "Firmware",
        buildName: "Build name",
        buildUUID: "Build UUID",
        minerType: "Miner type",
        os: "OS",
        platform: "Platform",
        psuModel: "PSU model",
        psuSerial: "PSU serial number",
        serialNumber: "Serial Number",
        title: "System Information"
    }
}
    , yI = {
    added: "Added...",
    applied: "Restart mining",
    autotuneReset: "Reset done",
    firmwareUpdate: "Firmware is updating",
    keyDeleted: "Key deleted",
    logsClear: "Logs cleared",
    logsCopied: "Logs are copied to clipboard",
    logsNotCopied: "Unable to copy logs to clipboard",
    poolSwitch: "Active pool is changed",
    reboot: "Rebooting...",
    reset: "Reset...",
    restart: "Restarting...",
    restore: "Restore...",
    saved: "Settings have been saved",
    start: "Start",
    stop: "Stopping mining..."
}
    , xI = "N/A"
    , wI = {
    action: {
        apply: "Apply",
        lockResult: "Device successfully locked",
        lockUI: "Lock device",
        lockUIDialog: {
            button: "Lock",
            message: "Device successfully locked!",
            text: "Settings and device parameters will be inactive for editing them",
            title: "Lock device?"
        },
        reboot: "Reboot",
        restart: "Restart mining",
        restartDialog: {
            apply: {
                no: "Cancel",
                title: "Apply and restart mining?",
                yes: "Yes, restart!"
            },
            reboot: {
                no: "Cancel",
                title: "Reboot miner?",
                yes: "Yes, reboot!"
            },
            restart: {
                no: "Cancel",
                title: "Restart mining?",
                yes: "Yes, restart!"
            },
            start: {
                no: "Cancel",
                title: "Start mining?",
                yes: "Yes, start!"
            },
            stop: {
                no: "Cancel",
                title: "Stop mining?",
                yes: "Yes, stop!"
            }
        },
        save: "Save",
        start: "Start mining",
        stopped: "Stop mining",
        unlockResult: "Device unlocked",
        unlockUI: "Unlock",
        unlockUIDialog: {
            desc: "Only monitoring is available without password",
            label: "Enter the password for full access",
            tooIncorrectPassword: "Too many incorrect password attempts.",
            tryAgain: "Please try again in",
            message: "The device is unlocked!",
            password: "Password",
            title: "Unlock device?"
        }
    },
    chipsNumber: "Chip index on board",
    columnMode: "Dashboard display mode",
    gridMode: "Grid ",
    infoBarTooltip: "Infobar",
    listMode: "List"
}
    , SI = {
    noData: {
        actionText: "Please wait while the miner is starting",
        text: "No data to display"
    },
    noWidgets: {
        actionText: "Please choose widgets from the dashboard menu to show",
        text: "No widgets to display"
    }
}
    , _I = {
    no: "No, don't reset",
    question: "Reset changes?",
    yes: "Yes, reset"
}
    , kI = {
    404: "Page not found",
    Advanced: "Advanced",
    Cooling: "Cooling",
    Dashboard: "Dashboard",
    General: "General",
    Mining: "Mining",
    Network: "Network",
    Others: "Other",
    Pools: "Pools",
    Security: "Security",
    Settings: "Settings",
    System: "System",
    performance: "Performance"
}
    , CI = {
    advanced: {
        titleTab: "Advanced",
        warningDescription: "You make any changes in this section at your own risk"
    },
    change: {
        button: "Reset"
    },
    cooling: {
        auto: "Auto",
        checkSpeed: "Checking the speed of coolers",
        default: "default",
        immersive: "Immersion",
        labelMode: "Cooling mode",
        manual: "Manual",
        minFanCount: "Minimum number of fans",
        minFanCountDesc: "Necessary if not the regular number of coolers",
        targetTemp: "Target temperature",
        fanDuty: "Fan speed",
        fanDutyRange: "Limit fan speed",
        modeDesc: "Auto by default",
        silentMode: "Quiet fan mode at startup",
        title: "Temperature control",
        titleTab: "Cooling"
    },
    general: {
        backup: {
            backup: {
                button: "Create archive",
                config: "backup",
                desk: "Click ‹Create Archive› to load the tar archive from the current configuration files ",
                title: "Backup settings"
            },
            collapse: "Collapse panel",
            expand: "Expand panel",
            reset: {
                button: "Reset",
                desk: "To reset the firmware, click ‹Reset› ",
                popup: {
                    message: "After reset, miner will work on factory settings",
                    no: "Cancel",
                    title: "Confirm factory reset",
                    yes: "Yes, reset!"
                },
                title: "Reset"
            },
            resetToStock: {
                button: "Rollback to stock",
                desk: "To reset firmware to the original stock version, click ‹Rollback to stock›",
                popup: {
                    message: "After reboot, miner will work with stock firmware",
                    no: "Cancel",
                    title: "Confirm rollback firmware to stock",
                    yes: "Yes, rollback!"
                },
                title: "Rollback to stock"
            },
            restore: {
                button: "Restore",
                desk: "To restore configuration files, you can download a previously created backup archive",
                dialog: {
                    button: "Restore settings",
                    title: "Restore Settings",
                    uploadText: "Select settings file"
                },
                title: "Restore Settings"
            },
            title: "Backup and restore",
            titleDesc: "Tools for backing up and restoring device settings"
        },
        chipsNumber: "Display chips number on board",
        chipsNumberDesc: "For the convenience of working with the layout of the chips",
        enableUIEffects: "UI optimize",
        enableUIEffectsDesc: "Disables animation and interface effects",
        lang: {
            en: "English",
            fa: "فارْسِى",
            ru: "Русский",
            ua: ""
        },
        regional: {
            sidebar: "Sidebar",
            sidebarTheme: "Dark sidebar",
            sidebarThemeDesc: "Applies to light theme only",
            timezone: "Timezone",
            timezoneDesc: "Affects the timing of events and device logs",
            title: "Regional settings",
            uiLang: "Interface language",
            uiLangDesc: "Default browser language",
            uiSettings: "Appearance",
            uiTheme: "Theme",
            uiThemeDesc: "Auto - uses the theme of the operating system",
            uiThemes: {
                auto: "Auto",
                dark: "Dark",
                light: "Light"
            }
        },
        titleTab: "General"
    },
    network: {
        dhcpDesc: "Automatic network setup",
        gateway: "Gateway",
        hostname: "Hostname",
        hostnameDesc: "Displayed in the browser header",
        labelIp: "IP Address",
        labelMask: "Mask",
        networkRestore: {
            note: "If the new network settings fail, it will return the previous settings",
            title: "Check network settings"
        },
        networkTest: {
            button: "Test network",
            desk: "On the other hand, diluted with a fair amount of empathy, rational thinking speaks of the possibilities of new proposals",
            dialog: {
                button: "Start",
                netFunction: "Network tool",
                noValue: "anthill.farm",
                nslookup: "Nslookup",
                ping: "Ping",
                testPage: "Host",
                title: "Network testing",
                traceroute: "Traceroute"
            },
            title: "Network connection test"
        },
        title: "Network settings",
        titleTab: "Network"
    },
    others: {
        control: {
            checkChip: "Autofix non efficient chips every",
            fixPeriod0: "Disabled",
            fixPeriod1: "Every 30 minute",
            fixPeriod2: "Every hour",
            fixPeriod3: "Every 3 hours",
            fixPeriod4: "Every 6 hours",
            fixPeriod5: "Every 12 hours",
            fixPeriod6: "Every day",
            maxRestartAttempts: "Max restart attempts",
            minOperationalChains: "Minimum number of operational boards",
            minOperationalChainsDesc: "Stop miner when the number of operational chains is less then",
            noValue: "Not set",
            restart: "Restart mining if hash rate is lower",
            restartDesc: "The hashrate threshold is set manually",
            tempOff: "Chips critical temperature",
            tempOffDesc: "Recommended range 50-120°C, default: 90°C",
            title: "Control"
        },
        others: {
            checkBalanceDomains: "Check balance of voltage domains",
            defaultValue: "DEFAULT VALUE",
            downscalePresetOnFailure: "Downscale preset on failure",
            downscalePresetOnFailureDescription: "Automatic downscale preset in case of miner overheating or chain break error",
            isPowerSupplyModified: "Power supply is modified",
            isPowerSupplyModifiedDesc: "Modified power supply allows you to deliver more power",
            isResumeMiningAfterReboot: "Resume mining after reboot",
            maxStartupDelayTime: "Maximum delay time before mining startup",
            maxStartupDelayTimeDesc: "Range 0-300s, default: 0s",
            nominal: "RESET TO NOMINAL:",
            nominalVolt: "NOMINAL VALUE",
            offAdjustVoltageByTemp: "Adapt voltage to temperature",
            offBreak: "Check integrity of chains",
            offChips: "Preheat chips at startup",
            offPreset: "Ignore minimum voltage in presets",
            offQuickStart: "Quick start",
            offTempSensor: "Turn ON temperature sensors check",
            offVolt: "Check voltage setting",
            quietMode: "Quiet mode",
            quietModeDescription: "Coolers speed by 50% when starting or stopping the device",
            seconds: "s",
            setDefault: "RESET TO DEFAULT:",
            skipInvalidTempSensors: "Skip broken temperature sensors",
            ignoreChipTempSensors: "Ignore chip's temperature sensors",
            startVoltOffset: "Startup voltage offset",
            title: "Others",
            tunerChipHashrateThreshold: "Tuner bad chip hashrate threshold",
            autoChipThrottling: "Auto chip throttling"
        },
        titleTab: "Other"
    },
    performance: {
        advance_settings: {
            title: "Advance settings"
        },
        autoProfile: {
            downProfile: "Lower preset",
            downProfileFan: "If cooler speed is higher",
            downProfileTemp: "If temperature is higher",
            downProfileTune: "On auto-tuning failure",
            optionsHeader: "Auto-switching options",
            profileDownTemp: "Step DOWN preset if temperature is above",
            profileDownTempRange: "Must be in range",
            profileUpTemp: "Step UP preset if temperature is below",
            switch: "Autoswitch presets",
            switchDescription: "Switches depending on temperature",
            upProfile: "Raise preset",
            upProfileFan: "If cooler speed is lower",
            upProfileLimit: "Don't raise preset above",
            upProfileLimitDescription: "Profile switching upper limit",
            switcherMinProfile: "Don't lower preset below",
            switcherMinProfileDescription: "Profile switching lower limit",
            upProfileTemp: "If temperature is lower",
            watchTimer: "Condition check duration",
            watchTimerDescription: "Should be in range of 1-10 minutes",
            switcherPowerDelta: "Exceeding nominal consumption",
            switcherPowerDeltaDesc: "+% of preset nominal value",
            autochangeTopPreset: "Autochange top preset if error occurs",
            autochangeTopPresetDescription: "If not achieved, top preset will be autochanged to the last reached one",
            ignoreFanSpeed: "Ignore fan speed",
            ignoreFanSpeedDescription: "Ignore fan speed when lowering/raising preset"
        },
        board: {
            chipPopper: {
                chip: "Chip",
                chip_temp: "Chip Temp.",
                domainFreq: "Domain frequency ",
                errors: "Errors",
                freq: "Frequency",
                hashrate: "Hashrate",
                reset: "Reset chip settings",
                temperature: "Temperature",
                useGlobal: "Use chain freq",
                usingGlobal: "Using chain freq"
            },
            forAllBoard: "Apply to all boards",
            operations: "Operations",
            platePopper: {
                plateFrequency: "Frequency",
                plateVoltage: "Voltage",
                reset: "Reset chain frequency",
                useGlobal: "Use global",
                usingGlobal: "Using global"
            },
            resetAllChain: "Reset all settings",
            resetChipsToZero: "Reset chip settings",
            stockInfo: {
                title: "Stock info"
            },
            switchOff: "Switch OFF",
            switchOn: "Enabled",
            title: "Board",
            undoChanges: "Cancel changes",
            view: {
                chip_temp: "Heatmap",
                errors: "Errors",
                freq: "Frequencies",
                hashrate: "Hashrate",
                temperature: "Sensors",
                title: "Board view"
            }
        },
        freq: "GLOBAL FREQUENCY",
        nominal: "RESET TO NOMINAL:",
        nominalFreq: "NOMINAL FREQUENCY",
        nominalVolt: "NOMINAL VOLTAGE",
        profile: {
            attention: "* LC - For power supply only",
            description: "Standard power supply",
            descriptionAlt: "Modified power supply",
            limitlessProfile: "Limitless",
            longLabel: "Preset",
            noProfile: "Disable",
            shortLabel: "Preset",
            tuned: "tuned"
        },
        title: "Performance settings",
        titleTab: "Performance",
        tuneDialog: {
            active: "active",
            markAll: "Select all",
            noData: "No tuned profiles",
            reset: "Reset",
            resetAndRestart: "Reset and restart",
            title: "Profile management"
        },
        tunerLogs: "Tuner logs",
        voltage: "GLOBAL VOLTAGE"
    },
    pools: {
        address: "Pool:",
        changeIndex: "Change priority",
        desc: "The priority of pools is controlled by the order in the list, by the drag and drop method",
        name: "Worker",
        password: "Password",
        saveIndex: "Save priority",
        title: "Pool List",
        titleTab: "Pools"
    },
    security: {
        api: {
            buttonAdd: "Add new key",
            deleteConfirm: {
                desk: "After deleting, key will not be able to use",
                no: "No",
                title: "Delete Key?",
                yes: "Yes, delete!"
            },
            desk: "Описание для чего этот ключ нужен и как его использовать...",
            dialog: {
                description: "The API key must be strictly 32 characters long. Key description is required!",
                descriptionPlaceHolder: "remote management",
                keyPlaceHolder: "enter your key here",
                labelDesc: "Description",
                labelKey: "API key",
                title: "New API key"
            },
            labelPort: "",
            title: "API keys"
        },
        password: {
            desk: "Changes the administrator password to access the device",
            labelCurrPass: "Current password",
            labelNewPass: "New password",
            title: "Change password"
        },
        titleTab: "Security"
    }
}
    , AI = {
    Warranty: {
        button: "Warranty",
        buttonActivate: "Activate Warranty"
    },
    menu: {
        actions: "Actions",
        collapsedTitle: "Menu",
        dashboard: "Dashboard",
        findMiner: "Find miner",
        integration: "Integration",
        mining: "Mining",
        settings: "Settings",
        support: "Tech support",
        system: "System",
        title: "Monitoring",
        update: "Firmware update"
    }
}
    , EI = {
    collapse: "Minimize logs",
    expand: "Expand logs",
    logs: {
        clearLogs: "Clear",
        copyAll: "Copy log",
        doClearLogs: "Clear logs",
        markAll: "Select all",
        tabs: {
            autotune: "Autotune",
            miner: "Miner",
            status: "Status",
            system: "System"
        },
        title: "Logs"
    },
    model: "model",
    releaseNotes: {
        placeHolder: {
            description: "Release data server is unavailable",
            header: "No release details"
        }
    },
    report: {
        button: "Create report",
        desk: "On the other hand, diluted with a fair amount of empathy, rational thinking speaks of the possibilities of new proposals",
        dialog: {
            back: "Retry",
            button: "Create report",
            desc: "To help solve your problem faster, you need to create a diagnostic report and send it to us. Describe in detail the essence of the problem and other important information in your opinion ",
            download: "Download",
            issue: "Description of the problem",
            report: "report",
            title: "Create report"
        },
        title: "Diagnostic report"
    },
    status: {
        "auto-tuning": "Autotuning",
        d: "d",
        disconnect: "Disconnected",
        failure: "Error",
        findMiner: "Find miner",
        h: "h",
        initializing: "Initializing",
        m: "m",
        mining: "Mining",
        restarting: "Restarting",
        "shutting-down": "Shutting down",
        starting: "Starting",
        stopped: "Stopped"
    },
    version: "version"
}
    , TI = {
    link: {
        homepage: "Home page",
        support: "Firmware help",
        telegram: "Telegram channel"
    },
    tagSoon: "Coming soon",
    title: "Tech support"
}
    , II = {
    activation: {
        activateConfirm: "Are you sure to activate warranty?",
        errorUnable: "Unable to activate warranty"
    },
    badge: "Not available by warranty",
    modal: {
        agreeCheckbox: "Unlock all functions with a warranty loss",
        buttonUnLock: "Remove all restrictions",
        notReversible: "Attention! The action is not reversible!",
        p1: "This equipment is on the service center warranty. Unlocking additional functions is possible after the warranty period is completed or you can unlock them right now.",
        p2: "When unlocking additional functions - during the warranty period, you automatically deprive the warranty service",
        subtitle: "Warning warranty!",
        title: "Warning warranty!",
        unlockWarranty: "All functions are unlocked"
    }
}


