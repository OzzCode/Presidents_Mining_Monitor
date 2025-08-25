import {
    o as u,
    v as c,
    s as l,
    t as m,
    q as V,
    k as C,
    x as v,
    br as Te,
    a7 as Z,
    w as r,
    B as n,
    a4 as g,
    ap as re,
    aq as te,
    aC as ae,
    D,
    ad as qe,
    a6 as Le,
    ar as Fe,
    ag as Ee,
    bn as Ae,
    P as k,
    Q as T,
    a0 as He,
    C as A,
    a5 as Oe,
    aZ as Be,
    aW as le,
    aX as Je,
    ac as Re,
    aU as Ue,
    aV as Ge,
    b0 as oe,
    at as ne,
    an as We,
    ah as ze,
    au as _e,
    av as Xe,
    a$ as je,
    aR as Ke,
    aY as Ze,
    aS as Qe,
    bs as Ye,
    bt as Ie,
    bu as $e,
    ba as xe,
    bv as ei,
    bw as ii,
    bx as ee,
    aB as si,
    ae as H,
    by as ie,
    aa as _,
    ab as se,
    bz as ri,
    a9 as ti,
    b4 as ai,
    aj as li,
    ak as oi,
    bA as ni
} from "./index.js";
import {B as pe} from "./BoardStockInfo.js";

const pi = {
    class: "Chip_Value overflow-hidden rounded-2px relative"
};

function ui(e, i, t, o, a, s) {
    const d = Te;
    return u(),
        c("section", {
            class: V(["Chip relative bg-$el-bg-color h-20px rounded-3px m-4px flex cursor-pointer font-semibold text-$el-text-color-primary min-w-29px border-1 border-solid border-$el-bg-color-page", t.heatmap !== null ? s.convertHeatMapToColor : t.status === "red" ? "Danger" : t.status === "orange" ? "Warning" : "Normal"])
        }, [l("div", {
            class: V(["Chip_Number", t.displayChipsNumber ? "" : "hidden"])
        }, m(t.num), 3), l("span", pi, [t.difference ? (u(),
            c("div", {
                key: 1,
                class: V(["Chip_Value__Data -ml-3px", t.badge])
            }, m(t.difference), 3)) : (u(),
            c("div", {
                key: 0,
                class: V(["Chip_Value__Data", t.badge ? "" : "text-$el-text-color-secondary"])
            }, m(t.value || t.value === 0 ? t.value : "-"), 3)), t.throttled ? (u(),
            C(d, {
                key: 2,
                class: "throttled",
                type: "success",
                "is-dot": ""
            })) : v("", !0), l("section", {
            class: V(["triangle w-0 h-0 absolute bottom-0 right-0", t.badge])
        }, null, 2)])], 2)
}

const hi = {
    name: "Chip",
    props: ["badge", "status", "num", "value", "heatmap", "throttled", "difference", "displayChipsNumber"],
    computed: {
        convertHeatMapToColor() {
            let i = 0
                , t = "";
            return this.heatmap >= 0 && (i = Math.floor((this.heatmap - 0) / 10) + 1,
                t = "Heatmap-" + (i > 11 ? 11 : i)),
                t
        },
        convertHeatMapToColorOld() {
            let i = 0
                , t = "";
            return this.heatmap >= 90 ? (i = Math.floor((this.heatmap - 90) / 10) + 1,
                t = "Hot-" + (i > 4 ? 4 : i)) : this.heatmap >= 40 ? (i = Math.floor((this.heatmap - 40) / 10) + 1,
                t = "Warm-" + (i > 4 ? 4 : i)) : this.heatmap >= 0 && (i = Math.floor((this.heatmap - 0) / 10) + 1,
                t = "Cold-" + (i > 4 ? 4 : i)),
                t
        }
    }
}
    , ue = Z(hi, [["render", ui]])
    , di = {
    class: "flex gap-10px flex-col-reverse !children:w-full !children:m-0"
};

function fi(e, i, t, o, a, s) {
    const d = re
        , w = te;
    return u(),
        C(w, {
            class: "heightAuto",
            modelValue: s.isVisible,
            "onUpdate:modelValue": i[0] || (i[0] = f => s.isVisible = f),
            center: "",
            top: "30vh",
            title: t.title || e.$t("ResetDialog.question"),
            "append-to-body": !0,
            fullscreen: !!e.less980,
            width: "400px"
        }, {
            default: r(() => [l("div", di, [n(d, {
                onClick: s.noHandler
            }, {
                default: r(() => [g(m(t.no || e.$t("ResetDialog.no")), 1)]),
                _: 1
            }, 8, ["onClick"]), n(d, {
                type: "danger",
                onClick: s.yesHandler
            }, {
                default: r(() => [g(m(t.yes || e.$t("ResetDialog.yes")), 1)]),
                _: 1
            }, 8, ["onClick"])])]),
            _: 1
        }, 8, ["modelValue", "title", "fullscreen"])
}

const ci = {
    name: "ResetChangeDialog",
    props: {
        modelValue: {
            type: Boolean,
            default: !1
        },
        title: {
            type: String,
            default: ""
        },
        yes: {
            type: String,
            default: ""
        },
        no: {
            type: String,
            default: ""
        }
    },
    emits: ["update:modelValue", "ok", "no"],
    data: () => ({
        less980: ae
    }),
    computed: {
        isVisible: {
            get() {
                return this.modelValue
            },
            set(e) {
                this.$emit("update:modelValue", e)
            }
        }
    },
    methods: {
        noHandler() {
            this.$emit("no"),
                this.isVisible = !1
        },
        yesHandler() {
            this.$emit("ok"),
                this.isVisible = !1
        }
    }
}
    , he = Z(ci, [["render", fi]])
    , gi = {
    class: "ButtonGroup"
}
    , wi = {
    class: "flex items-center gap-10px grow-1 basis-32%"
}
    , Si = {
    style: {
        float: "left"
    }
}
    , bi = {
    key: 0
}
    , vi = {
    key: 1
}
    , Pi = {
    class: "ml-10px"
}
    , Ci = {
    class: "transition-box"
}
    , yi = {
    class: "transition-box"
}
    , Mi = {
    class: "Title"
}
    , Ni = {
    class: "Value"
}
    , Vi = {
    key: 0,
    class: "BottomLeft text-$el-text-color-secondary"
}
    , Di = {
    class: "BottomRight"
}
    , ki = {
    class: "Title"
}
    , Ti = {
    class: "Value"
}
    , qi = {
    key: 0,
    class: "BottomLeft text-$el-text-color-secondary"
}
    , Li = ["dir"]
    , Fi = {
    dir: "ltr"
}
    , Ei = {
    class: "BottomRight"
}
    , Ai = {
    class: "CardTitle"
}
    , Hi = {
    class: "el-select-group__title"
}
    , Oi = {
    key: 0
}
    , Bi = {
    class: "el-select-group__title color-danger flex justify-between items-center pr-10px gap-10px"
}
    , Ji = {
    class: "ButtonGroup"
}
    , Ri = {
    class: "Title"
}
    , Ui = {
    class: "Value"
}
    , Gi = {
    key: 0,
    class: "BottomLeft text-$el-text-color-secondary"
}
    , Wi = ["onClick"]
    , zi = {
    class: "BottomRight differenceChain(chainIndex).color"
}
    , _i = {
    class: "transition-box mt-10px mb-15px"
}
    , Xi = {
    class: "text-14px text-bold"
}
    , ji = {
    class: "font-600 flex mt-10px mb-20px rounded-4px overflow-hidden border-1px border-solid border-$el-border-color children:flex children:flex-1 children:p-5px children:py-1px children:justify-center !children:border-none"
}
    , Ki = {
    class: "Chip_Value__Data"
}
    , Zi = {
    class: "ChipsBlock",
    "wipe.stop": ""
}
    , Qi = {
    key: 0
}
    , Yi = {
    key: 0,
    class: "ChipPopoverRow"
}
    , Ii = {
    class: "ValueGroup"
}
    , $i = {
    class: "Label"
}
    , xi = {
    class: "Value"
}
    , es = {
    class: "ValueGroup"
}
    , is = {
    class: "Label"
}
    , ss = {
    class: "Value"
}
    , rs = {
    key: 0,
    class: "ValueGroup"
}
    , ts = {
    class: "Label"
}
    , as = {
    class: "Value"
}
    , ls = {
    class: "Title",
    style: {
        "text-transform": "uppercase"
    }
}
    , os = {
    class: "Value"
}
    , ns = {
    key: 0,
    class: "BottomLeft text-$el-text-color-secondary"
}
    , ms = ["onClick"]
    , ps = {
    class: "BottomRight"
}
    , us = {
    key: 2,
    class: "ChipPopoverRow pb-10px"
}
    , hs = {
    class: "text-$el-text-color-primary"
}
    , ds = ["onClick"]
    , fs = {
    key: 1,
    class: "Reset text-$el-text-color-secondary"
}
    , cs = {
    class: "flex"
}
    , gs = {
    class: "status-plate flex flex-1 gap-5px items-center"
}
    , ws = ["onClick"];

function Ss(e, i, t, o, a, s) {
    const d = Oe
        , w = re
        , f = Be
        , y = le
        , P = Je
        , M = Re
        , R = Ue
        , U = Ge
        , de = oe
        , Q = ne
        , q = We
        , fe = ze
        , ce = _e
        , ge = Xe
        , we = te
        , E = qe
        , G = je
        , Se = mi
        , Y = Ke
        , O = me
        , be = Ze
        , I = Le
        , ve = Qe
        , W = Ye
        , Pe = Ie
        , Ce = $e
        , $ = xe
        , ye = ei
        , Me = ue
        , Ne = pe
        , Ve = he
        , z = Fe
        , De = ii
        , ke = Ee("touch");
    return D((u(),
        c("div", null, [n(I, {
            class: "mb-20px",
            shadow: "hover"
        }, {
            header: r(() => [l("header", null, [l("span", null, m(e.$t("Settings.performance.title")), 1), e.isWarrantyLimitation ? (u(),
                C(d, {
                    key: 0,
                    effect: "light",
                    placement: "right",
                    content: e.$t("Warranty.badge"),
                    "show-after": 500
                }, {
                    default: r(() => i[33] || (i[33] = [l("div", {
                        class: "icon-uil-shield-check text-15px bg-$el-color-danger"
                    }, null, -1)])),
                    _: 1
                }, 8, ["content"])) : v("", !0)]), l("div", gi, [s.isChangedWrap ? (u(),
                C(w, {
                    key: 0,
                    class: "Reset",
                    type: "primary",
                    plain: "",
                    size: "small",
                    onClick: i[0] || (i[0] = p => s.showResetDialog("wrap"))
                }, {
                    default: r(() => [i[34] || (i[34] = l("div", {
                        class: "icon-uil-refresh bg-current text-15px"
                    }, null, -1)), l("span", null, m(e.$t("Settings.change.button")), 1)]),
                    _: 1
                })) : v("", !0)])]),
            default: r(() => [s.performance ? (u(),
                C(be, {
                    key: 0,
                    class: "!-mb-20px",
                    model: s.performance.wrap,
                    rules: a.rules,
                    ref: "performance.wrap",
                    "label-position": "top",
                    onValidate: s.validate
                }, {
                    default: r(() => [n(E, {
                        class: "mt-10px",
                        gutter: 20
                    }, {
                        default: r(() => [n(M, {
                            span: 24,
                            xs: 24,
                            sm: 24,
                            md: 24
                        }, {
                            default: r(() => [n(P, {
                                prop: "isPowerSupplyModified"
                            }, {
                                default: r(() => [n(y, null, {
                                    icon: r(() => i[35] || (i[35] = [l("div", {
                                        class: "icon-uil-bolt"
                                    }, null, -1)])),
                                    header: r(() => [g(m(e.$t("Settings.others.others.isPowerSupplyModified")), 1)]),
                                    description: r(() => [g(m(e.$t("Settings.others.others.isPowerSupplyModifiedDesc")), 1)]),
                                    default: r(() => [n(f, {
                                        modelValue: s.performance.wrap.isPowerSupplyModified,
                                        "onUpdate:modelValue": i[1] || (i[1] = p => s.performance.wrap.isPowerSupplyModified = p),
                                        onChange: s.changeModedPSU,
                                        disabled: e.isWarrantyLimitation
                                    }, null, 8, ["modelValue", "onChange", "disabled"])]),
                                    _: 1
                                })]),
                                _: 1
                            })]),
                            _: 1
                        }), n(M, {
                            md: s.performance.wrap.profile && !e.isMinerAnyX17Series ? 14 : 24,
                            xs: 24,
                            sm: 24
                        }, {
                            default: r(() => [n(P, {
                                class: "mb-10px rounded-$el-border-radius-base overflow-hidden",
                                prop: "profile"
                            }, {
                                default: r(() => [n(y, null, Ae({
                                    icon: r(() => [i[36] || (i[36] = l("div", {
                                        class: "icon-uil-dashboard"
                                    }, null, -1))]),
                                    header: r(() => [g(m(e.$t("Settings.performance.profile.longLabel")), 1)]),
                                    default: r(() => [l("section", wi, [n(U, {
                                        class: "SelectProfile w-full sm:-ml-40%",
                                        modelValue: s.performance.wrap.profile,
                                        "onUpdate:modelValue": i[2] || (i[2] = p => s.performance.wrap.profile = p),
                                        onChange: s.changeProfile,
                                        disabled: e.isWarrantyLimitation,
                                        size: "small"
                                    }, {
                                        default: r(() => [(u(!0),
                                            c(k, null, T(s.performance.wrap.profiles, p => (u(),
                                                C(R, {
                                                    value: p.value,
                                                    label: p.value ? p.label + (p.isTuned ? "  ✓ " + e.$t("Settings.performance.profile.tuned") : "") : e.$t("Settings.performance.profile.noProfile"),
                                                    key: p.value,
                                                    disabled: p.modded_psu_required && !s.performance.wrap.isPowerSupplyModified
                                                }, {
                                                    default: r(() => [l("span", Si, [l("span", null, m(p.value ? p.label : e.$t("Settings.performance.profile.noProfile")), 1), l("span", null, m(p.isTuned ? "   ✓ " + e.$t("Settings.performance.profile.tuned") : ""), 1)])]),
                                                    _: 2
                                                }, 1032, ["value", "label", "disabled"]))), 128))]),
                                        _: 1
                                    }, 8, ["modelValue", "onChange", "disabled"]), n(d, {
                                        effect: "light",
                                        placement: "top",
                                        content: e.$t("Settings.performance.tuneDialog.title"),
                                        "show-after": 500,
                                        disabled: !!a.less980
                                    }, {
                                        default: r(() => [e.isWarrantyLimitation ? v("", !0) : (u(),
                                            C(de, {
                                                key: 0,
                                                class: "-my-4px",
                                                onClick: i[3] || (i[3] = p => a.dialogAutotuneIsVisible = !0)
                                            }, {
                                                default: r(() => i[37] || (i[37] = [l("div", {
                                                    class: "icon-uil-sliders-v-alt"
                                                }, null, -1)])),
                                                _: 1
                                            }))]),
                                        _: 1
                                    }, 8, ["content", "disabled"])]), n(we, {
                                        modelValue: a.dialogAutotuneIsVisible,
                                        "onUpdate:modelValue": i[6] || (i[6] = p => a.dialogAutotuneIsVisible = p),
                                        top: "15vh",
                                        "append-to-body": !0,
                                        fullscreen: !!a.less600,
                                        title: e.$t("Settings.performance.tuneDialog.title"),
                                        "close-on-click-modal": !a.isLoadingAutotune,
                                        "close-on-press-escape": !a.isLoadingAutotune,
                                        width: "480px",
                                        onOpen: s.getAutotune,
                                        onClose: s.noChecked
                                    }, {
                                        footer: r(() => [n(w, {
                                            class: "w-full",
                                            type: s.isCheckedCurrentProfile && !s.isChanges ? "danger" : "primary",
                                            size: "default",
                                            onClick: s.tuneReset,
                                            loading: a.isLoadingAutotune,
                                            disabled: a.isLoadingAutotune || !a.checkedTunedProfilesList.length
                                        }, {
                                            default: r(() => [i[40] || (i[40] = l("div", {
                                                class: "icon-uil-refresh"
                                            }, null, -1)), l("span", null, m(e.$t("Settings.performance.tuneDialog." + (s.isCheckedCurrentProfile && !s.isChanges ? "resetAndRestart" : "reset"))), 1)]),
                                            _: 1
                                        }, 8, ["type", "onClick", "loading", "disabled"])]),
                                        default: r(() => [s.performance.wrap.tunedCounter === 0 ? D((u(),
                                            c("div", bi, [g(m(e.$t("Settings.performance.tuneDialog.noData")), 1)])), [[z, a.isLoadingAutotune]]) : D((u(),
                                            c("div", vi, [n(Q, {
                                                modelValue: a.checkAll,
                                                "onUpdate:modelValue": i[4] || (i[4] = p => a.checkAll = p),
                                                border: "",
                                                indeterminate: a.isIndeterminate,
                                                onChange: s.handleCheckAllChange
                                            }, {
                                                default: r(() => [g(m(e.$t("Settings.performance.tuneDialog.markAll")), 1)]),
                                                _: 1
                                            }, 8, ["modelValue", "indeterminate", "onChange"]), n(q, {
                                                class: "!my-10px"
                                            }), n(ge, {
                                                style: He(a.less600 ? "height:calc(100dvh - 250px)" : "height:300px")
                                            }, {
                                                default: r(() => [n(ce, {
                                                    modelValue: a.checkedTunedProfilesList,
                                                    "onUpdate:modelValue": i[5] || (i[5] = p => a.checkedTunedProfilesList = p),
                                                    onChange: s.handleTunedProfileChange
                                                }, {
                                                    default: r(() => [(u(!0),
                                                        c(k, null, T(s.getTunedProfiles, p => (u(),
                                                            C(Q, {
                                                                label: p.name,
                                                                key: p.name,
                                                                border: ""
                                                            }, {
                                                                default: r(() => [l("span", null, [i[39] || (i[39] = l("div", {
                                                                    class: "icon-uil-bolt-alt bg-$el-color-primary"
                                                                }, null, -1)), l("span", Pi, m(p.label + "  ✓ " + e.$t("Settings.performance.profile.tuned")), 1), p.value === s.performance.wrap.activeProfile ? (u(),
                                                                    C(fe, {
                                                                        key: 0,
                                                                        class: "ml-auto",
                                                                        size: "small"
                                                                    }, {
                                                                        default: r(() => i[38] || (i[38] = [g("Active")])),
                                                                        _: 1
                                                                    })) : v("", !0)])]),
                                                                _: 2
                                                            }, 1032, ["label"]))), 128))]),
                                                    _: 1
                                                }, 8, ["modelValue", "onChange"])]),
                                                _: 1
                                            }, 8, ["style"])])), [[z, a.isLoadingAutotune]])]),
                                        _: 1
                                    }, 8, ["modelValue", "fullscreen", "title", "close-on-click-modal", "close-on-press-escape", "onOpen", "onClose"])]),
                                    _: 2
                                }, [s.performance.wrap.isPowerSupplyModified ? {
                                    name: "description",
                                    fn: r(() => [g(m(e.$t("Settings.performance.profile.descriptionAlt")), 1)]),
                                    key: "1"
                                } : {
                                    name: "description",
                                    fn: r(() => [g(m(e.$t("Settings.performance.profile.description")), 1)]),
                                    key: "0"
                                }]), 1024)]),
                                _: 1
                            })]),
                            _: 1
                        }, 8, ["md"]), D(n(M, {
                            span: 10,
                            xs: 24,
                            sm: 24,
                            md: 10
                        }, {
                            default: r(() => [n(P, {
                                class: "mb-10px",
                                prop: "switching"
                            }, {
                                default: r(() => [n(y, null, {
                                    icon: r(() => i[41] || (i[41] = [l("div", {
                                        class: "icon-uil-arrow-random"
                                    }, null, -1)])),
                                    header: r(() => [g(m(e.$t("Settings.performance.autoProfile.switch")), 1)]),
                                    description: r(() => [g(m(e.$t("Settings.performance.autoProfile.switchDescription")), 1)]),
                                    default: r(() => [n(f, {
                                        modelValue: s.performance.wrap.isSwitching,
                                        "onUpdate:modelValue": i[7] || (i[7] = p => s.performance.wrap.isSwitching = p),
                                        onChange: s.changeIsSwitching,
                                        disabled: e.isWarrantyLimitation
                                    }, null, 8, ["modelValue", "onChange", "disabled"])]),
                                    _: 1
                                })]),
                                _: 1
                            })]),
                            _: 1
                        }, 512), [[A, s.performance.wrap.profile]])]),
                        _: 1
                    }), n(Y, {
                        class: "-mb-20px"
                    }, {
                        default: r(() => [D(l("div", Ci, [n(q, {
                            class: "!mt-10px",
                            "content-position": "left"
                        }, {
                            default: r(() => [g(m(e.$t("Settings.performance.autoProfile.optionsHeader")), 1)]),
                            _: 1
                        }), n(E, {
                            gutter: 20
                        }, {
                            default: r(() => [n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "switcherStepUpTemp",
                                    ref: "switcherStepUpTemp"
                                }, {
                                    default: r(() => [n(y, null, {
                                        icon: r(() => i[42] || (i[42] = [l("div", {
                                            class: "icon-uil-arrow-to-bottom transform rotate-180"
                                        }, null, -1)])),
                                        header: r(() => [g(m(e.$t("Settings.performance.autoProfile.upProfileTemp")), 1)]),
                                        description: r(() => [g(m(`${e.$t("Settings.performance.autoProfile.profileDownTempRange")} ${a.minPresetTemperature - a.diffPresetSwitcherTemperature} - ${a.maxPresetTemperature - a.diffPresetSwitcherTemperature} °C`), 1)]),
                                        default: r(() => [n(G, {
                                            modelValue: s.performance.wrap.switcherStepUpTemp,
                                            "onUpdate:modelValue": i[8] || (i[8] = p => s.performance.wrap.switcherStepUpTemp = p),
                                            maxlength: "3",
                                            onInput: i[9] || (i[9] = p => (s.change("wrap", "switcherStepUpTemp"),
                                                s.validateField("switcherStepDownTemp"))),
                                            disabled: e.isWarrantyLimitation,
                                            size: "small"
                                        }, {
                                            append: r(() => i[43] || (i[43] = [g("°C")])),
                                            _: 1
                                        }, 8, ["modelValue", "disabled"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                }, 512)]),
                                _: 1
                            }), n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "switcherTopProfile",
                                    ref: "switcherTopProfile"
                                }, {
                                    default: r(() => [n(y, null, {
                                        icon: r(() => i[44] || (i[44] = [l("div", {
                                            class: "icon-uil-arrow-to-bottom transform rotate-180"
                                        }, null, -1)])),
                                        header: r(() => [g(m(e.$t("Settings.performance.autoProfile.upProfileLimit")), 1)]),
                                        description: r(() => [g(m(e.$t("Settings.performance.autoProfile.upProfileLimitDescription")), 1)]),
                                        default: r(() => [n(U, {
                                            class: "w-full",
                                            modelValue: s.performance.wrap.switcherTopProfile,
                                            "onUpdate:modelValue": i[10] || (i[10] = p => s.performance.wrap.switcherTopProfile = p),
                                            onChange: i[11] || (i[11] = p => s.change("wrap", "switcherTopProfile")),
                                            disabled: e.isWarrantyLimitation,
                                            size: "small"
                                        }, {
                                            default: r(() => [(u(!0),
                                                c(k, null, T(s.profilesOnlyList, p => (u(),
                                                    C(R, {
                                                        value: p.name,
                                                        label: p.label,
                                                        disabled: p.value - s.performance.wrap.profile < 0,
                                                        key: p.value
                                                    }, null, 8, ["value", "label", "disabled"]))), 128))]),
                                            _: 1
                                        }, 8, ["modelValue", "disabled"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                }, 512)]),
                                _: 1
                            })]),
                            _: 1
                        }), n(E, {
                            gutter: 20
                        }, {
                            default: r(() => [n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "switcherStepDownTemp",
                                    ref: "switcherStepDownTemp"
                                }, {
                                    default: r(() => [n(y, null, {
                                        icon: r(() => i[45] || (i[45] = [l("div", {
                                            class: "icon-uil-arrow-to-bottom"
                                        }, null, -1)])),
                                        header: r(() => [g(m(e.$t("Settings.performance.autoProfile.downProfileTemp")), 1)]),
                                        description: r(() => [g(m(`${e.$t("Settings.performance.autoProfile.profileDownTempRange")} ${a.minPresetTemperature} - ${a.maxPresetTemperature} °C`), 1)]),
                                        default: r(() => [n(G, {
                                            modelValue: s.performance.wrap.switcherStepDownTemp,
                                            "onUpdate:modelValue": i[12] || (i[12] = p => s.performance.wrap.switcherStepDownTemp = p),
                                            maxlength: "3",
                                            onInput: i[13] || (i[13] = p => (s.change("wrap", "switcherStepDownTemp"),
                                                s.validateField("switcherStepUpTemp"))),
                                            disabled: e.isWarrantyLimitation,
                                            size: "small"
                                        }, {
                                            append: r(() => i[46] || (i[46] = [g("°C")])),
                                            _: 1
                                        }, 8, ["modelValue", "disabled"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                }, 512)]),
                                _: 1
                            }), n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "switcherMinProfile",
                                    ref: "switcherMinProfile"
                                }, {
                                    default: r(() => [n(y, null, {
                                        icon: r(() => i[47] || (i[47] = [l("div", {
                                            class: "icon-uil-arrow-to-bottom transform"
                                        }, null, -1)])),
                                        header: r(() => [g(m(e.$t("Settings.performance.autoProfile.switcherMinProfile")), 1)]),
                                        description: r(() => [g(m(e.$t("Settings.performance.autoProfile.switcherMinProfileDescription")), 1)]),
                                        default: r(() => [n(U, {
                                            class: "w-full",
                                            modelValue: s.performance.wrap.switcherMinProfile,
                                            "onUpdate:modelValue": i[14] || (i[14] = p => s.performance.wrap.switcherMinProfile = p),
                                            onChange: i[15] || (i[15] = p => s.change("wrap", "switcherMinProfile")),
                                            disabled: e.isWarrantyLimitation,
                                            size: "small"
                                        }, {
                                            default: r(() => [(u(!0),
                                                c(k, null, T(s.profilesOnlyList, p => (u(),
                                                    C(R, {
                                                        value: p.name,
                                                        label: p.label,
                                                        disabled: p.value - s.performance.wrap.profile > 0,
                                                        key: p.value
                                                    }, null, 8, ["value", "label", "disabled"]))), 128))]),
                                            _: 1
                                        }, 8, ["modelValue", "disabled"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                }, 512)]),
                                _: 1
                            })]),
                            _: 1
                        }), n(E, {
                            gutter: 20
                        }, {
                            default: r(() => [n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "switcherParamCheckDuration"
                                }, {
                                    default: r(() => [n(y, null, {
                                        icon: r(() => i[48] || (i[48] = [l("div", {
                                            class: "icon-uil-clock"
                                        }, null, -1)])),
                                        header: r(() => [g(m(e.$t("Settings.performance.autoProfile.watchTimer")), 1)]),
                                        description: r(() => [g(m(e.$t("Settings.performance.autoProfile.watchTimerDescription")), 1)]),
                                        default: r(() => [n(Se, {
                                            class: "!w-200px",
                                            modelValue: s.performance.wrap.switcherParamCheckDuration,
                                            "onUpdate:modelValue": i[16] || (i[16] = p => s.performance.wrap.switcherParamCheckDuration = p),
                                            min: 1,
                                            max: 10,
                                            onChange: i[17] || (i[17] = p => s.change("wrap", "switcherParamCheckDuration")),
                                            size: "small"
                                        }, null, 8, ["modelValue"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                })]),
                                _: 1
                            }), e.hasPsuPowerReading ? (u(),
                                C(M, {
                                    key: 0,
                                    span: 12,
                                    sm: 12,
                                    xs: 24
                                }, {
                                    default: r(() => [n(P, {
                                        class: "mb-10px",
                                        prop: "switcherParamPowerDelta",
                                        ref: "switcherParamPowerDelta"
                                    }, {
                                        default: r(() => [n(y, null, {
                                            icon: r(() => i[49] || (i[49] = [l("div", {
                                                class: "icon-uil-power"
                                            }, null, -1)])),
                                            header: r(() => [g(m(e.$t("Settings.performance.autoProfile.switcherPowerDelta")), 1)]),
                                            description: r(() => [g(m(e.$t("Settings.performance.autoProfile.switcherPowerDeltaDesc")), 1)]),
                                            default: r(() => [n(G, {
                                                modelValue: s.performance.wrap.switcherParamPowerDelta,
                                                "onUpdate:modelValue": i[18] || (i[18] = p => s.performance.wrap.switcherParamPowerDelta = p),
                                                maxlength: "2",
                                                size: "small",
                                                disabled: e.isWarrantyLimitation,
                                                onInput: i[19] || (i[19] = p => s.change("wrap", "switcherParamPowerDelta"))
                                            }, {
                                                append: r(() => i[50] || (i[50] = [g("%")])),
                                                _: 1
                                            }, 8, ["modelValue", "disabled"])]),
                                            _: 1
                                        })]),
                                        _: 1
                                    }, 512)]),
                                    _: 1
                                })) : v("", !0), n(M, {
                                span: 12,
                                sm: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px"
                                }, {
                                    default: r(() => [n(y, null, {
                                        header: r(() => [l("span", null, m(e.$t("Settings.performance.autoProfile.autochangeTopPreset")), 1)]),
                                        description: r(() => [l("span", null, m(e.$t("Settings.performance.autoProfile.autochangeTopPresetDescription")), 1)]),
                                        default: r(() => [n(f, {
                                            modelValue: s.performance.wrap.autochangeTopPreset,
                                            "onUpdate:modelValue": i[20] || (i[20] = p => s.performance.wrap.autochangeTopPreset = p),
                                            onChange: i[21] || (i[21] = p => s.change("wrap", "autochangeTopPreset")),
                                            disabled: e.isWarrantyLimitation
                                        }, null, 8, ["modelValue", "disabled"])]),
                                        _: 1
                                    })]),
                                    _: 1
                                })]),
                                _: 1
                            }), s.isCoolingModeAuto ? (u(),
                                C(M, {
                                    key: 1,
                                    span: 12,
                                    sm: 12,
                                    xs: 24
                                }, {
                                    default: r(() => [n(P, {
                                        class: "mb-10px"
                                    }, {
                                        default: r(() => [n(y, null, {
                                            header: r(() => [l("span", null, m(e.$t("Settings.performance.autoProfile.ignoreFanSpeed")), 1)]),
                                            description: r(() => [l("span", null, m(e.$t("Settings.performance.autoProfile.ignoreFanSpeedDescription")), 1)]),
                                            default: r(() => [n(f, {
                                                modelValue: s.performance.wrap.ignoreFanSpeed,
                                                "onUpdate:modelValue": i[22] || (i[22] = p => s.performance.wrap.ignoreFanSpeed = p),
                                                onChange: i[23] || (i[23] = p => s.change("wrap", "ignoreFanSpeed")),
                                                disabled: e.isWarrantyLimitation
                                            }, null, 8, ["modelValue", "disabled"])]),
                                            _: 1
                                        })]),
                                        _: 1
                                    })]),
                                    _: 1
                                })) : v("", !0)]),
                            _: 1
                        })], 512), [[A, s.performance.wrap.profile && s.performance.wrap.isSwitching]])]),
                        _: 1
                    }), n(Y, null, {
                        default: r(() => [D(l("div", yi, [n(q, {
                            class: "!my-10px"
                        }), n(E, {
                            class: "-mb-20px",
                            gutter: 20
                        }, {
                            default: r(() => [n(M, {
                                span: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "globalVolt.value"
                                }, {
                                    default: r(() => [n(O, {
                                        modelValue: s.performance.wrap.globalVolt.value,
                                        "onUpdate:modelValue": i[25] || (i[25] = p => s.performance.wrap.globalVolt.value = p),
                                        min: s.performance.wrap.globalVolt.min,
                                        max: !e.isMinerAnyX19Series && !e.isMinerAnyX21Series || s.performance.wrap.isPowerSupplyModified ? s.performance.wrap.globalVolt.max : s.performance.wrap.globalVolt.stock_max,
                                        step: s.performance.wrap.globalVolt.step,
                                        onChange: i[26] || (i[26] = p => s.change("wrap", "globalVolt", "value")),
                                        disabled: e.isWarrantyLimitation
                                    }, {
                                        topLeft: r(() => [l("div", Mi, m(e.$t("Settings.performance.voltage")), 1)]),
                                        topRight: r(() => [l("div", Ni, [l("span", null, m(s.performance.wrap.globalVolt.value / e.voltModifier), 1), i[51] || (i[51] = l("span", null, "V", -1))])]),
                                        bottomLeft: r(() => [s.differenceGlobal("globalVolt") == 0 ? (u(),
                                            c("div", Vi, m(e.$t("Settings.performance.nominalVolt")), 1)) : e.isWarrantyLimitation ? v("", !0) : (u(),
                                            c("div", {
                                                key: 1,
                                                class: "BottomLeft text-$el-color-primary",
                                                style: {
                                                    cursor: "pointer"
                                                },
                                                onClick: i[24] || (i[24] = p => s.setToNominal("globalVolt"))
                                            }, m(e.$t("Settings.performance.nominal")) + " " + m(s.performance.wrap.globalVolt.nominal / e.voltModifier) + " V", 1))]),
                                        bottomRight: r(() => [l("div", Di, m(s.differenceGlobal("globalVolt") / e.voltModifier) + " V", 1)]),
                                        _: 1
                                    }, 8, ["modelValue", "min", "max", "step", "disabled"])]),
                                    _: 1
                                })]),
                                _: 1
                            }), n(M, {
                                span: 12,
                                xs: 24
                            }, {
                                default: r(() => [n(P, {
                                    class: "mb-10px",
                                    prop: "globalFreq.value"
                                }, {
                                    default: r(() => [n(O, {
                                        modelValue: s.performance.wrap.globalFreq.value,
                                        "onUpdate:modelValue": i[28] || (i[28] = p => s.performance.wrap.globalFreq.value = p),
                                        min: s.performance.wrap.globalFreq.min,
                                        max: s.performance.wrap.globalFreq.max,
                                        step: s.performance.wrap.globalFreq.step,
                                        onChange: i[29] || (i[29] = p => s.change("wrap", "globalFreq", "value")),
                                        disabled: e.isWarrantyLimitation
                                    }, {
                                        topLeft: r(() => [l("div", ki, m(e.$t("Settings.performance.freq")), 1)]),
                                        topRight: r(() => [l("div", Ti, [l("span", null, m(s.performance.wrap.globalFreq.value), 1), i[52] || (i[52] = l("span", null, "MHz", -1))])]),
                                        bottomLeft: r(() => [s.differenceGlobal("globalFreq") == 0 ? (u(),
                                            c("div", qi, m(e.$t("Settings.performance.nominalFreq")), 1)) : e.isWarrantyLimitation ? v("", !0) : (u(),
                                            c("div", {
                                                key: 1,
                                                class: "BottomLeft text-$el-color-primary",
                                                style: {
                                                    cursor: "pointer"
                                                },
                                                onClick: i[27] || (i[27] = p => s.setToNominal("globalFreq"))
                                            }, [l("span", {
                                                dir: e.langDir
                                            }, [g(m(e.$t("Settings.performance.nominal")) + " ", 1), l("span", Fi, m(s.performance.wrap.globalFreq.nominal) + " MHz", 1)], 8, Li)]))]),
                                        bottomRight: r(() => [l("div", Ei, m(s.differenceGlobal("globalFreq")) + " MHz", 1)]),
                                        _: 1
                                    }, 8, ["modelValue", "min", "max", "step", "disabled"])]),
                                    _: 1
                                })]),
                                _: 1
                            })]),
                            _: 1
                        })], 512), [[A, s.isEnableEditChips]])]),
                        _: 1
                    })]),
                    _: 1
                }, 8, ["model", "rules", "onValidate"])) : v("", !0)]),
            _: 1
        }), s.performance && !e.isLoadingChains ? (u(),
            C(E, {
                key: 0,
                class: "PlateBlock",
                gutter: 20
            }, {
                default: r(() => [(u(!0),
                    c(k, null, T(s.performance.wrap.chains, (p, h) => (u(),
                        C(M, {
                            key: "index" + h,
                            xl: e.isMinerS19AProSeries ? 8 : 12,
                            lg: e.isMinerS19ProSeries || e.isMinerS19126Series || e.isMinerS19HydroSeries || e.isMinerS19ProHydroSeries || e.isMinerS19ProHydro120Series || e.isMinerS19ProPlusHydroSeries || e.isMinerS19XPHydroSeries || e.isMinerS19JSeries || e.isMinerS19JPlusSeries || e.isMinerS19JProSeries || e.isMinerS19JProPlusSeries || e.isMinerS19JProASeries || e.isMinerS19XPSeries || e.isMinerS19JXPSeries || e.isMinerS19AProSeries || e.isMinerS19KProSeries || e.isMinerS21Series || e.isMinerS21PlusSeries || e.isMinerS21PlusHydroSeries || e.isMinerS21HydroSeries || e.isMinerS21ImmersionSeries || e.isMinerS21XPHydroSeries || e.isMinerS21XPImmersionSeries || e.isMinerL9Series || e.isMinerL7Series ? 12 : 8,
                            md: e.isMinerS19ProSeries || e.isMinerS19126Series || e.isMinerS19HydroSeries || e.isMinerS19ProHydroSeries || e.isMinerS19ProHydro120Series || e.isMinerS19ProPlusHydroSeries || e.isMinerS19XPHydroSeries || e.isMinerS19JSeries || e.isMinerS19JPlusSeries || e.isMinerS19JProSeries || e.isMinerS19JProPlusSeries || e.isMinerS19JProASeries ? 24 : e.isMinerS19Series || e.isMinerS19ISeries || e.isMinerS19ASeries || e.isMinerS19AProSeries || e.isMinerS19KProSeries || e.isMinerS19XPSeries || e.isMinerS19JXPSeries || e.isMinerS19PlusSeries || e.isMinerS1988Series || e.isMinerS21Series || e.isMinerS21PlusSeries || e.isMinerS21PlusHydroSeries || e.isMinerS21ProSeries || e.isMinerS21HydroSeries || e.isMinerS21ImmersionSeries || e.isMinerS21XPHydroSeries || e.isMinerS21XPImmersionSeries || e.isMinerL9Series || e.isMinerL7Series ? 12 : 8,
                            sm: e.isMinerS19ProSeries || e.isMinerS19126Series || e.isMinerS19HydroSeries || e.isMinerS19ProHydroSeries || e.isMinerS19ProHydro120Series || e.isMinerS19ProPlusHydroSeries || e.isMinerS19XPHydroSeries || e.isMinerS19JSeries || e.isMinerS19JPlusSeries || e.isMinerS19JProSeries || e.isMinerS19JProPlusSeries || e.isMinerS19JProASeries || e.isMinerS19Series || e.isMinerS19ISeries || e.isMinerS19ASeries || e.isMinerS19AProSeries || e.isMinerS19KProSeries || e.isMinerS19XPSeries || e.isMinerS19JXPSeries || e.isMinerS19PlusSeries || e.isMinerS1988Series || e.isMinerS21Series || e.isMinerS21PlusSeries || e.isMinerS21PlusHydroSeries || e.isMinerS21HydroSeries || e.isMinerS21ImmersionSeries || e.isMinerS21XPHydroSeries || e.isMinerS21XPImmersionSeries || e.isMinerL9Series || e.isMinerL7Series ? 24 : 12,
                            xs: 24
                        }, {
                            default: r(() => [n(I, {
                                class: V(["PlateCard", [s.isDisconnectedPlate(h) ? "Offline" : "", s.isFailurePlate(h) ? "Danger" : "", s.isChainEdited(h) ? "Edited" : ""]]),
                                "body-style": "padding:'30px'",
                                shadow: "hover"
                            }, {
                                header: r(() => [n(Ce, {
                                    class: "cursor-pointer",
                                    trigger: "click",
                                    placement: "bottom-start"
                                }, {
                                    dropdown: r(() => [n(Pe, null, {
                                        default: r(() => [l("div", Hi, m(e.$t("Settings.performance.board.view.title")), 1), (u(!0),
                                            c(k, null, T(Object.keys(a.views), b => (u(),
                                                C(W, {
                                                    key: b
                                                }, {
                                                    default: r(() => [n(ve, {
                                                        modelValue: a.activeView,
                                                        "onUpdate:modelValue": i[30] || (i[30] = N => a.activeView = N),
                                                        value: b
                                                    }, {
                                                        default: r(() => [g(m(e.$t("Settings.performance.board.view." + b)), 1)]),
                                                        _: 2
                                                    }, 1032, ["modelValue", "value"])]),
                                                    _: 2
                                                }, 1024))), 128)), n(q, {
                                            class: "!my-10px"
                                        }), s.performance.wrap.profile ? v("", !0) : (u(),
                                            c("div", Oi, [D(l("div", {
                                                class: "el-select-group__title"
                                            }, m(e.$t("Settings.performance.board.operations")), 513), [[A, !e.isWarrantyLimitation]]), e.isWarrantyLimitation ? v("", !0) : (u(),
                                                C(W, {
                                                    key: 0,
                                                    onClick: b => s.setChipsToGlobal(h)
                                                }, {
                                                    default: r(() => [g(m(e.$t("Settings.performance.board.resetChipsToZero")), 1)]),
                                                    _: 2
                                                }, 1032, ["onClick"])), e.isWarrantyLimitation ? v("", !0) : (u(),
                                                C(W, {
                                                    key: 1,
                                                    class: "!text-$el-color-primary",
                                                    onClick: b => s.setChipsToGlobal(h) + s.toggleChainGlobalFrequency(h, !0)
                                                }, {
                                                    default: r(() => [g(m(e.$t("Settings.performance.board.resetAllChain")), 1)]),
                                                    _: 2
                                                }, 1032, ["onClick"])), e.isWarrantyLimitation ? v("", !0) : (u(),
                                                C(q, {
                                                    key: 2,
                                                    class: "!my-10px"
                                                }))])), l("div", Bi, [l("span", null, m(e.$t("Settings.performance.board.switchOn")), 1), n(f, {
                                            "model-value": !p.disabled,
                                            onChange: b => {
                                                p.disabled = !p.disabled,
                                                    s.toggleChainDisable(h)
                                            }
                                        }, null, 8, ["model-value", "onChange"])])]),
                                        _: 2
                                    }, 1024)]),
                                    default: r(() => [l("span", Ai, [g(m(e.$t("Settings.performance.board.title")) + " " + m(h + 1), 1), i[53] || (i[53] = l("i", {
                                        class: "text-$el-color-primary el-icon-arrow-down el-icon--right"
                                    }, null, -1)), i[54] || (i[54] = l("div", {
                                        class: "icon-uil-angle-down bg-$el-color-primary"
                                    }, null, -1))])]),
                                    _: 2
                                }, 1024), l("div", Ji, [n($, {
                                    trigger: "click",
                                    placement: "bottom-end",
                                    width: "290",
                                    disabled: !s.isEnableEditChips || e.isWarrantyLimitation
                                }, {
                                    reference: r(() => [n(w, {
                                        class: "PlateFreq !text-$el-color-text-primary relative overflow-hidden",
                                        size: "small"
                                    }, {
                                        default: r(() => [l("section", {
                                            class: V(["triangle w-0 h-0 absolute bottom-0 right-0", s.differenceChain(h).color])
                                        }, null, 2), l("span", {
                                            class: V(s.differenceChain(h).color)
                                        }, m(p.freq || s.performance.wrap.globalFreq.value), 3), i[55] || (i[55] = l("span", {
                                            style: {
                                                padding: "0px 4px"
                                            }
                                        }, "Mhz /", -1)), l("small", {
                                            class: V(s.differenceChain(h).color)
                                        }, m(p.freq ? s.differenceChain(h).value : "Global"), 3)]),
                                        _: 2
                                    }, 1024)]),
                                    default: r(() => [n(O, {
                                        modelValue: p.freq || s.performance.wrap.globalFreq.value,
                                        min: s.performance.wrap.globalFreq.min,
                                        max: s.performance.wrap.globalFreq.max,
                                        step: s.performance.wrap.globalFreq.step,
                                        "onUpdate:modelValue": b => s.checkChainFrequencySliderInput(h, b),
                                        disabled: e.isWarrantyLimitation
                                    }, {
                                        topLeft: r(() => [l("div", Ri, m(e.$t("Settings.performance.board.platePopper.plateFrequency")), 1)]),
                                        topRight: r(() => [l("div", Ui, [l("span", {
                                            class: V(s.differenceChain(h).color)
                                        }, m(p.freq || s.performance.wrap.globalFreq.value), 3), i[56] || (i[56] = l("span", null, "MHz", -1))])]),
                                        bottomLeft: r(() => [p.freq === 0 ? (u(),
                                            c("div", Gi, m(e.$t("Settings.performance.board.platePopper.usingGlobal")), 1)) : e.isWarrantyLimitation ? v("", !0) : (u(),
                                            c("div", {
                                                key: 1,
                                                class: "BottomLeft text-$el-color-primary",
                                                style: {
                                                    cursor: "pointer"
                                                },
                                                onClick: b => s.toggleChainGlobalFrequency(h, !0)
                                            }, m(e.$t("Settings.performance.board.platePopper.useGlobal")), 9, Wi))]),
                                        bottomRight: r(() => [l("div", zi, m(s.differenceChain(h).value), 1)]),
                                        _: 2
                                    }, 1032, ["modelValue", "min", "max", "step", "onUpdate:modelValue", "disabled"])]),
                                    _: 2
                                }, 1032, ["disabled"])])]),
                                default: r(() => [l("main", null, [D(l("div", _i, [n(E, {
                                    gutter: 10
                                }, {
                                    default: r(() => [(u(!0),
                                        c(k, null, T(a.chipsByStatusFreqControlButtons, (b, N) => (u(),
                                            C(M, {
                                                key: N,
                                                span: 8
                                            }, {
                                                default: r(() => [n(w, {
                                                    class: "w-full ButtonFreqControl",
                                                    type: b.status === "red" ? "danger" : b.status === "orange" ? "primary" : "",
                                                    size: "small",
                                                    plain: "",
                                                    onClick: x => s.setByStatus(h, b.status, b.step),
                                                    disabled: !s.chipsByStatus(h, b.status) || e.isWarrantyLimitation
                                                }, {
                                                    default: r(() => [l("span", null, m(s.chipsByStatus(h, b.status)), 1), n(q, {
                                                        class: "!border-color-current-color opacity-25",
                                                        direction: "vertical"
                                                    }), l("section", null, [l("span", Xi, m(b.label) + " ", 1), i[57] || (i[57] = l("span", null, "Mhz", -1))])]),
                                                    _: 2
                                                }, 1032, ["type", "onClick", "disabled"])]),
                                                _: 2
                                            }, 1024))), 128))]),
                                    _: 2
                                }, 1024)], 512), [[A, a.activeView !== "chip_temp" && !s.performance.wrap.profile]]), D(l("section", ji, [(u(),
                                    c(k, null, T(12, b => l("div", {
                                        key: b,
                                        class: V(`Heatmap-${b < 10 ? "" + b : b}`)
                                    }, [l("span", Ki, m((b - 1) * 10 + "°"), 1)], 2)), 64))], 512), [[A, a.activeView === "chip_temp"]]), n(q, {
                                    class: "!my-10px whitespace-nowrap children:font-semibold"
                                }, {
                                    default: r(() => [g(m(e.$t("Settings.performance.board.chipPopper." + a.activeView)) + " - " + m(a.views[a.activeView]), 1)]),
                                    _: 1
                                }), D((u(),
                                    c("div", Zi, [(u(!0),
                                        c(k, null, T(e.columnsOnBoard, (b, N) => (u(),
                                            c("div", {
                                                class: V(["ChipsColumn", e.chainTopology[N]])
                                            }, [(u(!0),
                                                c(k, null, T(s.splitDomainsPerColumns(h)[N], (x, L) => (u(),
                                                    c("div", {
                                                        class: V(["ChipsDomain", {
                                                            active: a.activeDomain !== null && a.activeDomain.split(".")[0] === h && a.activeDomain.split(".")[1] === N && a.activeDomain.split(".")[2] === L
                                                        }]),
                                                        key: L
                                                    }, [(u(!0),
                                                        c(k, null, T(x, (S, B) => (u(),
                                                            c("div", {
                                                                key: B
                                                            }, [n($, {
                                                                placement: "top",
                                                                visible: a.activeChipMenu === h + "." + S.index,
                                                                ref_for: !0,
                                                                ref: `pop${h}.${S.index}`,
                                                                "popper-class": s.chipPopoverTitleClass(h, S.index),
                                                                "popper-options": {
                                                                    gpuAcceleration: !1
                                                                },
                                                                width: "300",
                                                                onHide: s.resetView,
                                                                onShow: F => s.openChipPopup(h, s.getAbsoluteDomainIndex(N, L), B),
                                                                disabled: !s.isEnableEditChips
                                                            }, {
                                                                reference: r(() => [D(n(Me, {
                                                                    value: a.activeView === "freq" ? S.config || "chain" : s.platesChip(h, S.index)[a.activeView === "temperature" ? "temp" : a.activeView],
                                                                    badge: S.isChanged ? "Edit" : S.config ? "Fixed" : "",
                                                                    displayChipsNumber: e.displayChipsNumber,
                                                                    num: S.index + 1,
                                                                    chain: h,
                                                                    throttled: s.platesChip(h, S.index).throttled,
                                                                    heatmap: a.activeView === "chip_temp" ? s.platesChip(h, S.index).chip_temp : null,
                                                                    status: s.platesChip(h, S.index).status,
                                                                    difference: S.isChanged && a.activeView === "freq" ? S.difference.value : null,
                                                                    onClick: F => (s.chipClick(h + "." + S.index),
                                                                        s.highlightDomain(h + "." + N + "." + L))
                                                                }, null, 8, ["value", "badge", "displayChipsNumber", "num", "chain", "throttled", "heatmap", "status", "difference", "onClick"]), [[De, `pop${h}.${S.index}`]])]),
                                                                default: r(() => [a.activeChipMenu === h + "." + S.index ? (u(),
                                                                    c("div", Qi, [l("div", {
                                                                        class: "ChipPopoverTitle mb-10px",
                                                                        onClick: i[31] || (i[31] = F => (a.activeChipMenu = null,
                                                                            a.activeDomain = null))
                                                                    }, [l("span", null, m(e.$t("Settings.performance.board.chipPopper.chip")) + ": " + m(S.index + 1), 1), i[58] || (i[58] = l("div", {
                                                                        class: "icon-uil-times bg-$el-bg-color"
                                                                    }, null, -1))]), e.minerDataIsNull ? v("", !0) : (u(),
                                                                        c("div", Yi, [l("div", Ii, [l("div", $i, m(e.$t("Settings.performance.board.chipPopper.hashrate")), 1), l("div", xi, m(s.platesChip(h, S.index).hashrate + " " + a.views.hashrate), 1)]), l("div", es, [l("div", is, m(e.$t("Settings.performance.board.chipPopper.errors")), 1), l("div", ss, m(s.platesChip(h, S.index).errors + " " + a.views.errors), 1)]), s.platesChip(h, S.index).temp ? (u(),
                                                                            c("div", rs, [l("div", ts, m(e.$t("Settings.performance.board.chipPopper.temperature")), 1), l("div", as, m((s.platesChip(h, S.index).temp || "") + " " + a.views.temperature), 1)])) : v("", !0)])), e.minerDataIsNull ? v("", !0) : (u(),
                                                                        C(q, {
                                                                            key: 1,
                                                                            class: "!my-10px"
                                                                        })), l("div", null, [n(O, {
                                                                        modelValue: S.config || p.freq || s.performance.wrap.globalFreq.value,
                                                                        "is-changed": S.isChanged,
                                                                        min: s.performance.wrap.globalFreq.min,
                                                                        max: s.performance.wrap.globalFreq.max,
                                                                        step: s.performance.wrap.globalFreq.step,
                                                                        "onUpdate:modelValue": F => s.checkChipSliderInput(S, h, s.getAbsoluteDomainIndex(N, L), B, F),
                                                                        disabled: e.isWarrantyLimitation
                                                                    }, {
                                                                        topLeft: r(() => [l("div", ls, m(e.$t("Settings.performance.board.chipPopper.freq")), 1)]),
                                                                        topRight: r(() => [l("div", os, [l("span", null, m(S.config || p.freq || s.performance.wrap.globalFreq.value), 1), i[59] || (i[59] = l("span", null, "MHz", -1))])]),
                                                                        bottomLeft: r(() => [S.config === 0 ? (u(),
                                                                            c("div", ns, m(e.$t("Settings.performance.board.chipPopper.usingGlobal")), 1)) : e.isWarrantyLimitation ? v("", !0) : (u(),
                                                                            c("div", {
                                                                                key: 1,
                                                                                class: "BottomLeft text-$el-color-primary",
                                                                                style: {
                                                                                    cursor: "pointer"
                                                                                },
                                                                                onClick: F => s.toggleChipGlobal(h, s.getAbsoluteDomainIndex(N, L), B, !0)
                                                                            }, m(e.$t("Settings.performance.board.chipPopper.useGlobal")), 9, ms))]),
                                                                        bottomRight: r(() => [l("div", ps, m(S.difference.value), 1)]),
                                                                        _: 2
                                                                    }, 1032, ["modelValue", "is-changed", "min", "max", "step", "onUpdate:modelValue", "disabled"])]), n(q, {
                                                                        class: "!my-10px"
                                                                    }), e.isWarrantyLimitation ? v("", !0) : (u(),
                                                                        c("div", us, [l("span", hs, [g(m(e.$t("Settings.performance.board.chipPopper.domainFreq")), 1), !e.isWarrantyLimitation && s.hasDomainModifiedChip(h, s.getAbsoluteDomainIndex(N, L)) ? (u(),
                                                                            c("div", {
                                                                                key: 0,
                                                                                class: "Reset text-$el-color-primary",
                                                                                onClick: F => s.resetDomainToChainFrequency(h, s.getAbsoluteDomainIndex(N, L))
                                                                            }, m(e.$t("Settings.performance.board.chipPopper.useGlobal")), 9, ds)) : (u(),
                                                                            c("div", fs, m(e.$t("Settings.performance.board.chipPopper.usingGlobal")), 1))]), l("span", null, [n(ye, null, {
                                                                            default: r(() => [n(w, {
                                                                                class: "btn-row btn-row-left",
                                                                                size: "small",
                                                                                onClick: F => s.changeDomainFreq(h, s.getAbsoluteDomainIndex(N, L), "minus")
                                                                            }, {
                                                                                default: r(() => i[60] || (i[60] = [l("i", {
                                                                                    class: "icon-uil-minus"
                                                                                }, null, -1)])),
                                                                                _: 2
                                                                            }, 1032, ["onClick"]), n(w, {
                                                                                class: "btn-row btn-row-right",
                                                                                size: "small",
                                                                                onClick: F => s.changeDomainFreq(h, s.getAbsoluteDomainIndex(N, L), "plus")
                                                                            }, {
                                                                                default: r(() => i[61] || (i[61] = [l("i", {
                                                                                    class: "icon-uil-plus"
                                                                                }, null, -1)])),
                                                                                _: 2
                                                                            }, 1032, ["onClick"])]),
                                                                            _: 2
                                                                        }, 1024)])]))])) : v("", !0)]),
                                                                _: 2
                                                            }, 1032, ["visible", "popper-class", "onHide", "onShow", "disabled"])]))), 128))], 2))), 128))], 2))), 256))])), [[ke, void 0, "s"]])]), l("footer", cs, [l("section", gs, [l("span", {
                                    class: V(["text-15px", [s.getPlateStatusIcon(h).icon, {
                                        "animate-pulse": s.isInitializingPlate(h)
                                    }]])
                                }, null, 2), l("span", null, m(s.getPlateStatusText(h)), 1)]), s.isChainEdited(h) ? (u(),
                                    c("section", {
                                        key: 0,
                                        class: "cursor-pointer text-$el-color-primary flex gap-5px items-center",
                                        onClick: b => s.showResetDialog("chain", h)
                                    }, [i[62] || (i[62] = l("div", {
                                        class: "icon-uil-refresh text-15px bg-$el-color-primary"
                                    }, null, -1)), i[63] || (i[63] = l("span", null, "Reset", -1)), n(q, {
                                        class: "!mx-10px",
                                        direction: "vertical"
                                    })], 8, ws)) : v("", !0), s.isDisconnectedPlate(h) ? v("", !0) : (u(),
                                    C(Ne, {
                                        key: 1,
                                        index: h
                                    }, null, 8, ["index"]))])]),
                                _: 2
                            }, 1032, ["class"])]),
                            _: 2
                        }, 1032, ["xl", "lg", "md", "sm"]))), 128))]),
                _: 1
            })) : v("", !0), n(Ve, {
            modelValue: a.resetDialog.isVisible,
            "onUpdate:modelValue": i[32] || (i[32] = p => a.resetDialog.isVisible = p),
            title: a.resetDialog.title,
            onOk: s.handleReset
        }, null, 8, ["modelValue", "title", "onOk"])])), [[z, e.isLoadingGet || e.isLoadingPut]])
}

const K = {
    hashrate: "GH/s",
    errors: "Err",
    chip_temp: "°C",
    temperature: "°C",
    freq: "MHz"
};
ee.indexOf("21") === -1 && ee !== "l9" && delete K.chip_temp;
const X = 25
    , j = 90
    , J = 5
    , bs = {
    name: "performance",
    props: ["badge", "status", "num", "value", "unit"],
    components: {
        IconButton: oe,
        ElCheckboxExtend: ne,
        CustomBlock: le,
        ResetChangeDialog: he,
        ElSliderExtend: me,
        Chip: ue,
        BoardStockInfo: pe
    },
    data() {
        const e = (d, w, f) => {
                this[this.formName].wrap.profile && this[this.formName].wrap.isSwitching && this[this.formName].wrap[d.dependsOn] ? w ? f() : f(new Error(ie.message())) : f()
            }
            , i = (d, w, f) => {
                this[this.formName].wrap.profile && this[this.formName].wrap.isSwitching && isNaN(Number(w)) ? f(new Error(ni.message())) : f()
            }
            , t = (d, w, f) => {
                this[this.formName].wrap.profile && this[this.formName].wrap.isSwitching ? !w || w >= d.min && w <= d.max ? f() : f(new Error(`${this.$t("Errors.inputDiapason")} ${d.min} - ${d.max}`)) : f()
            }
            , o = (d, w, f) => {
                this[this.formName].wrap.profile && this[this.formName].wrap.isSwitching && !isNaN(this[this.formName].wrap.switcherStepUpTemp) && !isNaN(this[this.formName].wrap.switcherStepDownTemp) ? this[this.formName].wrap.switcherStepUpTemp <= this[this.formName].wrap.switcherStepDownTemp - J ? f() : f(new Error(d.field === "switcherStepDownTemp" ? this.$t("Errors.diff5") : "")) : f()
            }
            , a = (d, w, f) => {
                const y = this[this.formName].wrap.profile
                    , P = this.performance.wrap.profiles.find(M => M.name === w);
                y && this[this.formName].wrap.isSwitching ? P && P.value - y >= 0 ? f() : f(new Error) : f()
            }
            , s = (d, w, f) => {
                const y = this[this.formName].wrap.profile
                    , P = this.performance.wrap.profiles.find(M => M.name === w);
                y && this[this.formName].wrap.isSwitching ? P && y - P.value >= 0 ? f() : f(new Error) : f()
            }
        ;
        return {
            minPresetTemperature: X,
            maxPresetTemperature: j,
            diffPresetSwitcherTemperature: J,
            less600: si,
            less980: ae,
            formName: "performance",
            dialogAutotuneIsVisible: !1,
            isIndeterminate: !1,
            isLoadingAutotune: !1,
            checkedTunedProfilesList: [],
            checkAll: !1,
            rules: {
                switcherTopProfile: [{
                    validator: e,
                    dependsOn: "isSwitching"
                }, {
                    validator: a,
                    message: H.global.t("Errors.wrongTopProfile")
                }],
                switcherMinProfile: [{
                    validator: e,
                    dependsOn: "isSwitching"
                }, {
                    validator: s,
                    message: H.global.t("Errors.wrongMinProfile")
                }],
                switcherStepUpTemp: [{
                    validator: e,
                    dependsOn: "switcherStepDownTemp"
                }, {
                    validator: i
                }, {
                    validator: t,
                    min: X - J,
                    max: j - J
                }, {
                    validator: o
                }],
                switcherStepDownTemp: [{
                    validator: e,
                    dependsOn: "switcherStepUpTemp"
                }, {
                    validator: i
                }, {
                    validator: t,
                    min: X,
                    max: j
                }, {
                    validator: o
                }],
                switcherParamPowerDelta: [{
                    required: !0,
                    message: ie.message()
                }, {
                    validator: i
                }, {
                    validator: t,
                    min: 0,
                    max: 50
                }]
            },
            isSwitchingPresent: null,
            switchingPresentData: null,
            switchingPresentDataList: ["switcherTopProfile", "switcherMinProfile"],
            chipsTimer: null,
            chipsTimeout: 5e3,
            chipsByStatusFreqControlButtons: [{
                status: "grey",
                label: "+5",
                step: 5
            }, {
                status: "orange",
                label: "-5",
                step: 5
            }, {
                status: "red",
                label: "-10",
                step: 10
            }],
            chipNumVisible: "flex",
            views: K,
            activeView: "hashrate",
            prevView: "",
            activeChipMenu: null,
            activeDomain: null,
            resetDialog: {
                title: "",
                action: "",
                actionArgument: null,
                isVisible: !1
            }
        }
    },
    computed: {
        ..._("settings", ["isLoadingGet", "isLoadingPut", "isLoadingChains", "changes", "validation", "oldData"]),
        ...se("settings", ["voltModifier", "chainTopology", "chipsPerDomain", "domainsPerColumn", "columnsOnBoard", "isMinerS21Series", "isMinerS21ProSeries", "isMinerS21PlusSeries", "isMinerS21PlusHydroSeries", "isMinerS21HydroSeries", "isMinerS21ImmersionSeries", "isMinerS21XPSeries", "isMinerS21XPHydroSeries", "isMinerS21XPImmersionSeries", "isMinerS19Series", "isMinerS19PlusSeries", "isMinerS19ProSeries", "isMinerS19126Series", "isMinerS19HydroSeries", "isMinerS19ProHydroSeries", "isMinerS19ProHydro120Series", "isMinerS19ProPlusHydroSeries", "isMinerS19XPHydroSeries", "isMinerS19ISeries", "isMinerS19JSeries", "isMinerS19JPlusSeries", "isMinerS19JProSeries", "isMinerS19JProASeries", "isMinerS19JProPlusSeries", "isMinerS19ASeries", "isMinerS19AProSeries", "isMinerS19KProSeries", "isMinerS19XPSeries", "isMinerS19JXPSeries", "isMinerS1988Series", "isMinerAnyX21Series", "isMinerAnyX19Series", "isMinerAnyX17Series", "isMinerL9Series", "isMinerL7Series"]),
        ..._("summary", ["plates", "chainChips", "emulatedPlates", "hasPsuPowerReading"]),
        ...se("summary", ["minerDataIsNull", "isEmulateStatus"]),
        ..._("ui", ["isWarrantyLimitation", "displayChipsNumber", "langDir", "isDebug"]),
        performance: {
            get() {
                return this.$store.state.settings.performance
            },
            set(e) {
                this.$store.commit("settings/performance", e)
            }
        },
        profilesOnlyList() {
            return this.performance.wrap.profiles.filter(e => e.name !== "disabled")
        },
        collectionProfiles() {
            return ri(this.performance.wrap.profiles, "value")
        },
        isEnableEditChips() {
            return !this.performance.wrap.profile || this.collectionProfiles[this.performance.wrap.profile].isTuned
        },
        getTunedProfiles() {
            return this[this.formName].wrap.profiles.filter(e => !!e.isTuned)
        },
        isCheckedCurrentProfile() {
            const e = this.getTunedProfiles.find(i => i.value === this[this.formName].wrap.activeProfile);
            return e ? !!this.checkedTunedProfilesList.find(i => i === e.name) : !1
        },
        isChanges() {
            return Object.keys(this.changes).some(e => this.changes[e].length)
        },
        isChanged() {
            return this.changes[this.formName].length
        },
        isChangedWrap() {
            let e = !1;
            for (let i of this.changes[this.formName])
                if (i.indexOf("wrap") > -1) {
                    e = !0;
                    break
                }
            return e
        },
        isChangedControl() {
            let e = !1;
            for (let i of this.changes[this.formName])
                if (i.indexOf("control") > -1) {
                    e = !0;
                    break
                }
            return e
        },
        isChangedMisc() {
            let e = !1;
            for (let i of this.changes[this.formName])
                if (i.indexOf("misc") > -1) {
                    e = !0;
                    break
                }
            return e
        },
        isCoolingModeAuto() {
            return this.$store.state.settings.cooling.mode === "auto"
        }
    },
    mounted() {
        !this.isLoadingGet && this.$refs[this.formName + ".wrap"] && this.validateForm(),
            this.getAutotune(),
        this.minerDataIsNull && (this.views = {
            freq: "MHz"
        },
            this.activeView = "freq"),
            this.updateChips()
    },
    beforeUnmount() {
        clearTimeout(this.chipsTimer)
    },
    methods: {
        ...ti("settings", ["getChains", "toggleChange", "toggleValid", "resetChange", "copyPresetSettingsToPerformance"]),
        updateChips() {
            this.chipsTimer = setTimeout(() => {
                    this.getChains(),
                        this.updateChips()
                }
                , this.chipsTimeout)
        },
        splitDomainsPerColumns(e) {
            const i = [];
            let t = 0
                , o = 0;
            if (this.domainsPerColumn[0] === -1)
                return [this.performance.wrap["chips" + e]];
            for (let a = 0; a < this.domainsPerColumn.length; a++) {
                const s = [];
                t = o,
                    o += this.domainsPerColumn[a];
                for (let d = t; d < o; d++)
                    s.push(this.performance.wrap["chips" + e][d]);
                i.push(s)
            }
            return i
        },
        getAbsoluteDomainIndex(e, i) {
            let t = i;
            for (let o = 0; o < e; o++)
                t += this.domainsPerColumn[o];
            return t
        },
        showResetDialog(e, i) {
            this.resetDialog = {
                title: "",
                action: i || i === 0 ? "resetChain" : "reset",
                actionArgument: i || i === 0 ? i : "wrap",
                isVisible: !0
            }
        },
        handleReset() {
            this[this.resetDialog.action](this.resetDialog.actionArgument)
        },
        async getAutotune() {
            if (!(this.isLoadingAutotune || !this[this.formName] || !this[this.formName].wrap.profiles.length)) {
                this.isLoadingAutotune = !0;
                try {
                    const e = await this.$APIv1.get("/autotune/presets");
                    let i = 0;
                    for (const [t, o] of this[this.formName].wrap.profiles.entries()) {
                        const a = e.data[t].status === "tuned";
                        o.isTuned = a,
                        a && i++
                    }
                    this[this.formName].wrap.tunedCounter = i
                } catch {
                    ai(H.global.t("Errors.noAutotunePresetData"))
                } finally {
                    this.isLoadingAutotune = !1
                }
            }
        },
        handleCheckAllChange(e) {
            this.isIndeterminate = !1,
                this.checkedTunedProfilesList = e ? this.getTunedProfiles.map(i => i.name) : []
        },
        handleTunedProfileChange(e) {
            this.checkAll = e.length === this.getTunedProfiles.length,
                this.isIndeterminate = e.length ? e.length < this.getTunedProfiles.length : !1
        },
        async tuneReset() {
            if (this.isLoadingAutotune)
                return;
            this.isLoadingAutotune = !0;
            const e = this[this.formName].wrap.profiles
                , i = this.isCheckedCurrentProfile && !this.isChanges;
            try {
                if (await this.$APIv1.post("/autotune/reset", {
                    presets: this.checkedTunedProfilesList,
                    restart: i
                }),
                    i)
                    this.$store.dispatch("auth/rebootLock");
                else {
                    let t = 0;
                    this[this.formName].wrap.profiles = e.map(o => (this.checkedTunedProfilesList.find(a => a === o.name) && (o.isTuned = !1),
                    o.isTuned && t++,
                        o)),
                        this[this.formName].wrap.tunedCounter = t,
                        this.dialogAutotuneIsVisible = !1
                }
                li({
                    message: H.global.t("Messages.autotuneReset"),
                    type: "success",
                    showClose: !0
                })
            } catch (t) {
                oi(t)
            } finally {
                this.isLoadingAutotune = !1
            }
        },
        noChecked() {
            this.checkAll = !1,
                this.isIndeterminate = !1,
                this.checkedTunedProfilesList = []
        },
        change(e, i, t) {
            let o = this[this.formName][e][i]
                , a = this.oldData[this.formName][e][i];
            t && (o = o[t],
                a = a[t]);
            let s = o !== a;
            this.toggleChange({
                tabName: this.formName,
                propName: e + "." + i + (t ? "." + t : ""),
                value: s
            })
        },
        reset(e) {
            this.isSwitchingPresent = null,
                this.switchingPresentData = null,
                this.resetChange([this.formName, e]),
            e === "wrap" && this.copyPresetSettingsToPerformance(this.performance.wrap.profile)
        },
        validate(e, i) {
            this.toggleValid({
                tabName: this.formName,
                propName: e,
                value: i
            })
        },
        validateForm() {
            this.$refs[this.formName + ".wrap"].validate()
        },
        changeModedPSU(e) {
            if (this.change("wrap", "isPowerSupplyModified"),
                !e) {
                const i = this.performance.wrap.profiles.findIndex(t => t.modded_psu_required);
                i > -1 && i <= this.performance.wrap.profile - 1 && (this.performance.wrap.profile = i,
                    this.changeProfile())
            }
        },
        changeProfile() {
            if (this.change("wrap", "profile"),
                this.activeChipMenu = null,
                this.copyPresetSettingsToPerformance(this.performance.wrap.profile),
                this[this.formName].wrap.profile) {
                const e = ["globalVolt", "globalFreq", "chains"];
                for (let a = 0; a < this.performance.wrap.chains.length; a++)
                    e.push("chips" + a);
                const i = [];
                this[this.formName].wrap.chains.forEach(a => {
                        i.push(a.disabled)
                    }
                );
                for (const a of e)
                    this[this.formName].wrap[a] = JSON.parse(JSON.stringify(this.oldData[this.formName].wrap[a]));
                i.forEach((a, s) => {
                        this[this.formName].wrap.chains[s].disabled = a
                    }
                );
                const t = this[this.formName].wrap.profile !== this.oldData[this.formName].wrap.profile
                    , o = this.$store.state.settings.changes;
                o.performance = t ? ["wrap.profile"] : [],
                    this.$store.commit("settings/changes", o),
                this.isSwitchingPresent !== null && (this[this.formName].wrap.isSwitching = JSON.parse(JSON.stringify(this.isSwitchingPresent)),
                    this.isSwitchingPresent = null),
                    this.changeIsSwitching()
            } else
                this.isSwitchingPresent = JSON.parse(JSON.stringify(this[this.formName].wrap.isSwitching)),
                    this[this.formName].wrap.isSwitching = !1,
                    this.changeIsSwitching()
        },
        changeIsSwitching() {
            this.change("wrap", "isSwitching"),
                this[this.formName].wrap.isSwitching ? (this.setSwitchingToPresentData(),
                this[this.formName].wrap.profile && (this[this.formName].wrap.switcherTopProfile || (this.setSwitcherTopProfile(),
                    this.change("wrap", "switcherTopProfile")),
                this[this.formName].wrap.switcherMinProfile || (this.setSwitcherMinProfile(),
                    this.change("wrap", "switcherMinProfile"))),
                    this.validateField("switcherTopProfile"),
                    this.validateField("switcherMinProfile")) : this.setSwitchingToOldData()
        },
        setSwitchingToPresentData() {
            if (this.switchingPresentData) {
                for (let e of this.switchingPresentDataList)
                    this[this.formName].wrap[e] = JSON.parse(JSON.stringify(this.switchingPresentData[e])),
                        this.change("wrap", e);
                this.switchingPresentData = null,
                    this.validateForm()
            }
        },
        setSwitchingToOldData() {
            this.switchingPresentData = {};
            for (let e of this.switchingPresentDataList)
                this.switchingPresentData[e] = JSON.parse(JSON.stringify(this[this.formName].wrap[e])),
                    this[this.formName].wrap[e] = JSON.parse(JSON.stringify(this.oldData[this.formName].wrap[e])),
                    this.change("wrap", e);
            this.validateForm()
        },
        setSwitcherTopProfile() {
            const e = this[this.formName].wrap.profiles.length - 1;
            this[this.formName].wrap.switcherTopProfile = this[this.formName].wrap.profiles[e].name
        },
        setSwitcherMinProfile() {
            this[this.formName].wrap.switcherMinProfile = this[this.formName].wrap.profiles[1].name
        },
        validateField(e) {
            this.$refs[e].validate()
        },
        differenceGlobal(e) {
            const i = this[this.formName].wrap[e]
                , t = i.value - i.nominal;
            return (t > 0 ? "+" : "") + t
        },
        setToNominal(e) {
            const i = this[this.formName].wrap[e];
            i.value = i.nominal
                this.change("wrap", e, "value")
        },
        getPlateStatusText(e) {
            const i = this.plates.find(t => (t == null ? void 0 : t.id) === e + 1);
            return i ? i.status.state !== "failure" ? H.global.t("Dashboard.boards.status." + i.status.state) : i.status.description : H.global.t("Dashboard.boards.status.disconnected")
        },
        getPlateStatusIcon(e) {
            const i = this.plates.find(t => (t == null ? void 0 : t.id) === e + 1);
            if (!i)
                return {
                    icon: "icon-uil-times-circle"
                };
            switch (i.status.state) {
                case "initializing":
                case "mining":
                    return {
                        icon: "icon-uil-bolt-alt bg-$el-color-primary"
                    };
                case "stopped":
                    return {
                        icon: "icon-uil-pause-circle bg-$color-text-regular"
                    };
                case "failure":
                    return {
                        icon: "icon-uil-exclamation-triangle bg-$el-color-white"
                    };
                case "disabled":
                    return {
                        icon: "icon-uil-times-circle bg-$color-text-regular"
                    };
                case "unknown":
                    return {
                        icon: "icon-uil-times-circle bg-$color-text-regular"
                    };
                default:
                    return {
                        icon: "bg-$color-text-regular"
                    }
            }
        },
        isInitializingPlate(e) {
            const i = this.plates.find(t => (t == null ? void 0 : t.id) === e + 1);
            return (i == null ? void 0 : i.status.state) === "initializing"
        },
        isDisconnectedPlate(e) {
            const i = this.plates.find(t => (t == null ? void 0 : t.id) === e + 1);
            return !i || (i.status.state) === "disconnected"
        },
        isFailurePlate(e) {
            const i = this.plates.find(t => (t == null ? void 0 : t.id) === e + 1);
            return (i == null ? void 0 : i.status.state) === "failure"
        },
        differenceChain(e) {
            const i = this[this.formName].wrap.chains[e]
                , t = i.freq - this[this.formName].wrap.globalFreq.value
                , o = i.voltage - this[this.formName].wrap.globalVolt.value;
            let a = "default"
                , s = "default";
            return i.isChanged && (a = t > 0 ? "warning" : "danger",
                s = o > 0 ? "warning" : "danger"),
                {
                    value: i.freq ? (t > 0 ? "+" : "") + t + "MHz" : "Global",
                    voltage: i.voltage ? (o > 0 ? "+" : "") + o / this.voltModifier + "V" : "Global",
                    color: a,
                    colorVoltage: s
                }
        },
        checkChainFrequencySliderInput(e, i) {
            const t = this[this.formName].wrap.globalFreq.value
                , o = this[this.formName].wrap.chains[e];
            o.freq ? o.freq !== i && (o.freq = i,
                this.changeChain(e)) : t !== i && (o.freq = i,
                this.changeChain(e))
        },
        checkChainVoltageSliderInput(e, i) {
            const t = this[this.formName].wrap.globalVolt.value
                , o = this[this.formName].wrap.chains[e];
            o.voltage ? o.voltage !== i && (o.voltage = i,
                this.changeChain(e)) : t !== i && (o.voltage = i,
                this.changeChain(e))
        },
        changeChain(e) {
            const i = this[this.formName].wrap.chains[e]
                , t = i.freq !== this.oldData[this.formName].wrap.chains[e].freq
                , o = i.voltage !== this.oldData[this.formName].wrap.chains[e].voltage;
            let a;
            typeof this.oldData[this.formName].wrap.chains[e].voltage < "u" ? a = t || o : a = t,
                i.isChanged = a,
                this.toggleChange({
                    tabName: this.formName,
                    propName: "wrap.chains" + e,
                    value: a
                })
        },
        toggleChainGlobalFrequency(e, i) {
            const t = this[this.formName].wrap.chains[e]
                , o = this[this.formName].wrap.globalFreq.value;
            t.freq = i ? 0 : o,
                this.changeChain(e)
        },
        toggleChainGlobalVoltage(e, i) {
            const t = this[this.formName].wrap.chains[e]
                , o = this[this.formName].wrap.globalVolt.value;
            t.voltage = i ? 0 : o,
                this.changeChain(e)
        },
        resetChainFreq(e) {
            let i = this.oldData[this.formName].wrap.chains[e];
            i = JSON.parse(JSON.stringify(i)),
                this[this.formName].wrap.chains[e].freq = i.freq,
                this.changeChain(e)
        },
        resetChain(e) {
            let i = this.oldData[this.formName].wrap.chains[e];
            i = JSON.parse(JSON.stringify(i)),
                this[this.formName].wrap.chains[e] = i,
                this.changeChain(e);
            const t = this[this.formName].wrap["chips" + e];
            for (const [o, a] of t.entries())
                for (let [s] of a.entries())
                    this.resetChip(e, o, s)
        },
        hasDomainModifiedChip(e, i) {
            const t = this[this.formName].wrap["chips" + e][i];
            for (let o = 0; o < t.length; o++)
                if (t[o].config !== 0)
                    return !0;
            return !1
        },
        saveCurrentView() {
            console.log("saveCurrentView:", this.activeView),
                this.prevView = this.activeView
        },
        openChipPopup(e, i, t) {
            this.saveCurrentView(),
                this.setChipDifference(e, i, t)
        },
        resetView() {
            console.log("reset view:", this.prevView),
            this.prevView && (this.activeView = this.prevView)
        },
        resetDomainToChainFrequency(e, i) {
            console.log("resetDomainToChainFrequency", this.prevView),
            this.activeView !== "freq" && (this.prevView = this.activeView,
                this.activeView = "freq");
            const t = this[this.formName].wrap["chips" + e][i];
            for (let o = 0; o < t.length; o++) {
                const a = t[o];
                a.config = 0,
                    this.changeChip(e, i, o)
            }
        },
        changeDomainFreq(e, i, t) {
            console.log("changeDomainFreq", this.prevView),
            this.activeView !== "freq" && (this.prevView = this.activeView,
                this.activeView = "freq");
            const a = this[this.formName].wrap.chains[e].freq || this[this.formName].wrap.globalFreq.value
                , s = this[this.formName].wrap["chips" + e][i];
            for (let d = 0; d < s.length; d++) {
                const w = s[d];
                w.config = this.chipFreqValue(w.config || a, this[this.formName].wrap.globalFreq.step, t === "plus"),
                    this.changeChip(e, i, d)
            }
        },
        isChainEdited(e) {
            let i = !1;
            for (let t of this.changes[this.formName])
                if (t.indexOf("wrap.chains" + e) > -1) {
                    i = !0;
                    break
                }
            return i
        },
        platesChip(e, i) {
            const o = (this.isEmulateStatus ? this.emulatedPlates : this.chainChips).find(a => (a == null ? void 0 : a.id) === e + 1);
            return o && o.chips[i] ? o.chips[i] : {
                hashrate: "---",
                errors: "---",
                freq: "---",
                status: "grey"
            }
        },
        chipsByStatus(e, i) {
            this.isEmulateStatus ? this.emulatedPlates : this.plates;
            const t = this.plates.find(o => (o == null ? void 0 : o.id) === e + 1);
            return t ? t.chip_statuses[i] : 0
        },
        setByStatus(e, i, t) {
            this.activeView !== "freq" && (this.activeView = "freq");
            const a = this[this.formName].wrap.chains[e].freq || this[this.formName].wrap.globalFreq.value
                , s = (this.isEmulateStatus ? this.emulatedPlates : this.chainChips).find(d => d.id === e + 1);
            if (s)
                for (const [d, w] of s.chips.entries()) {
                    const f = Math.floor(d / this.chipsPerDomain)
                        , y = d % this.chipsPerDomain
                        , P = this[this.formName].wrap["chips" + e][f][y];
                    w.status === i && (P.config = this.chipFreqValue(P.config || a, t, i === "grey"),
                        this.changeChip(e, f, y))
                }
        },
        chipFreqValue(e, i, t) {
            i = Number(i),
                e = Number(e),
                e = t ? e + i : e - i;
            const o = Number(this[this.formName].wrap.globalFreq.min)
                , a = Number(this[this.formName].wrap.globalFreq.max);
            return e < o && (e = o),
            e > a && (e = a),
                e
        },
        checkChipSliderInput(e, i, t, o, a) {
            const s = this[this.formName].wrap.globalFreq.value
                , w = this[this.formName].wrap.chains[i].freq || s;
            e.config ? e.config !== a && (e.config = a,
                this.changeChip(i, t, o)) : w !== a && (e.config = a,
                this.changeChip(i, t, o))
        },
        changeChip(e, i, t) {
            const o = this[this.formName].wrap["chips" + e][i][t]
                , a = this.oldData[this.formName].wrap["chips" + e][i][t]
                , s = o.config !== a.config;
            o.isChanged = s,
                this.toggleChange({
                    tabName: this.formName,
                    propName: "wrap.chains" + e + "." + i + "." + t,
                    value: s
                }),
                this.setChipDifference(e, i, t)
        },
        setChipDifference(e, i, t) {
            const o = this[this.formName].wrap["chips" + e][i][t]
                , a = this.oldData[this.formName].wrap["chips" + e][i][t].config
                , d = this[this.formName].wrap.chains[e].freq || this[this.formName].wrap.globalFreq.value
                , w = (o.config || d) - (a || d);
            let f = "default";
            o.isChanged && (f = w > 0 ? "danger" : "warning"),
                o.difference = {
                    value: o.config ? (w >= 0 ? "+" : "") + w : "Chain",
                    color: f
                }
        },
        setChipsToGlobal(e) {
            for (const [i, t] of this[this.formName].wrap["chips" + e].entries())
                for (let [o] of t.entries())
                    this.toggleChipGlobal(e, i, o, !0)
        },
        toggleChipGlobal(e, i, t, o) {
            const s = this[this.formName].wrap.chains[e].freq || this[this.formName].wrap.globalFreq.value
                , d = this[this.formName].wrap["chips" + e][i][t];
            d.config = o ? 0 : s,
                this.changeChip(e, i, t)
        },
        resetChip(e, i, t) {
            let o = this.oldData[this.formName].wrap["chips" + e][i][t];
            o = JSON.parse(JSON.stringify(o)),
                this[this.formName].wrap["chips" + e][i][t] = o,
                this.changeChip(e, i, t)
        },
        toggleChainDisable(e) {
            this.toggleChange({
                tabName: this.formName,
                propName: `wrap.chains.${e}.disabled`,
                value: this[this.formName].wrap.chains[e].disabled !== this.oldData[this.formName].wrap.chains[e].disabled
            })
        },
        chipPopoverTitleClass(e, i) {
            const t = this.platesChip(e, i);
            return t.status === "red" ? "ChipPopover Danger" : t.status === "orange" ? "ChipPopover Warning" : "ChipPopover"
        },
        chipClick(e) {
            this.isEnableEditChips && (this.activeChipMenu === e ? this.activeChipMenu = null : this.activeChipMenu = e)
        },
        highlightDomain(e) {
            this.activeChipMenu === null ? this.activeDomain = null : this.activeDomain = e
        }
    },
    watch: {
        minerDataIsNull(e) {
            e ? (this.views = {
                freq: "MHz"
            },
                this.activeView = "freq") : this.views = K
        }
    }
}
    , ys = Z(bs, [["render", Ss]]);
export {ys as default};
