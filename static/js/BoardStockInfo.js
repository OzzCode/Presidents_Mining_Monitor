import {
    o as u,
    k as _,
    w as m,
    s,
    v as p,
    t as a,
    x as f,
    ba as k,
    aa as v,
    ab as x,
    af as b,
    a7 as S
} from "./index.js";

const V = {
    key: 0,
    class: "flex gap-5px flex-col"
}
    , w = {
    class: "ValueGroup Medium Row"
}
    , I = {
    class: "Value !flex-grow-2"
}
    , g = {
    class: "ValueGroup Medium Row"
}
    , M = {
    class: "Value !flex-grow-2"
}
    , L = {
    class: "ValueGroup Medium Row"
}
    , y = {
    class: "Value !flex-grow-2"
}
    , B = {
    class: "ValueGroup Medium Row"
}
    , G = {
    class: "Value !flex-grow-2"
}
    , H = {
    class: "ValueGroup Medium Row"
}
    , R = {
    class: "Value !flex-grow-2"
}
    , N = {
    class: "ValueGroup Medium Row"
}
    , C = {
    class: "Value !flex-grow-2"
};

function q(o, e, F, z, D, t) {
    const h = k;
    return t.stockInfo ? (u(),
        _(h, {
            key: 0,
            placement: "top-end",
            trigger: "click",
            title: o.$t("Settings.performance.board.stockInfo.title"),
            width: 230
        }, {
            reference: m(() => e[0] || (e[0] = [s("div", {
                class: "icon-uil-info-circle cursor-pointer ml-10px"
            }, null, -1)])),
            default: m(() => {
                    var r, i, l, d, n, c;
                    return [t.stockInfo ? (u(),
                        p("section", V, [s("div", w, [e[1] || (e[1] = s("div", {
                            class: "Label"
                        }, "Board model:", -1)), s("div", I, a((r = t.stockInfo) == null ? void 0 : r.board_model), 1)]), s("div", g, [e[2] || (e[2] = s("div", {
                            class: "Label"
                        }, "Serial:", -1)), s("div", M, a((i = t.stockInfo) == null ? void 0 : i.serial), 1)]), s("div", L, [e[3] || (e[3] = s("div", {
                            class: "Label"
                        }, "Chip bin:", -1)), s("div", y, a((l = t.stockInfo) == null ? void 0 : l.chip_bin), 1)]), s("div", B, [e[4] || (e[4] = s("div", {
                            class: "Label"
                        }, "Frequency:", -1)), s("div", G, a((d = t.stockInfo) == null ? void 0 : d.freq) + " MHz", 1)]), s("div", H, [e[5] || (e[5] = s("div", {
                            class: "Label"
                        }, "Voltage:", -1)), s("div", R, a(((n = t.stockInfo) == null ? void 0 : n.volt) / 100) + " V", 1)]), s("div", N, [e[6] || (e[6] = s("div", {
                            class: "Label"
                        }, "Hashrate:", -1)), s("div", C, a(t.formatStockHashrate((c = t.stockInfo) == null ? void 0 : c.hashrate)), 1)])])) : f("", !0)]
                }
            ),
            _: 1
        }, 8, ["title"])) : f("", !0)
}

const E = {
    name: "BoardStockInfo",
    props: {
        id: Number,
        index: Number
    },
    computed: {
        ...v("system", ["chainStockInfo"]),
        ...x("settings", ["isMinerL9Series", "isMinerL7Series"]),
        stockInfo() {
            return this.chainStockInfo.find(o => this.id ? o.id === this.id : o.id === this.index + 1)
        },
        formatStockHashrate() {
            return o => {
                const e = b({
                    hashrate: o,
                    measure: this.$store.state.summary.hr_base_measure ? this.$store.state.summary.hr_base_measure : this.isMinerL9Series || this.isMinerL7Series ? "MH/s" : "GH/s"
                });
                return e.hashrate || e.hashrate === 0 ? e.hashrate.toFixed(3) + " " + e.measure : ""
            }
        }
    },
    created() {
        this.$store.dispatch("system/loadStockInfo", !0)
    },
    beforeUnmount() {
        this.$store.dispatch("system/clearScheduleTimer")
    }
}
    , T = S(E, [["render", q]]);
export {T as B};
