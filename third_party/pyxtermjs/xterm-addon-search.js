!function (e, t) {
    "object" == typeof exports && "object" == typeof module ? module.exports = t() : "function" == typeof define && define.amd ? define([], t) : "object" == typeof exports ? exports.SearchAddon = t() : e.SearchAddon = t()
}(self, (() => (() => {
    "use strict";
    var e = {
        345: (e, t) => {
            Object.defineProperty(t, "__esModule", {value: !0}), t.forwardEvent = t.EventEmitter = void 0, t.EventEmitter = class {
                constructor() {
                    this._listeners = [], this._disposed = !1
                }

                get event() {
                    return this._event || (this._event = e => (this._listeners.push(e), {
                        dispose: () => {
                            if (!this._disposed) for (let t = 0; t < this._listeners.length; t++) if (this._listeners[t] === e) return void this._listeners.splice(t, 1)
                        }
                    })), this._event
                }

                fire(e, t) {
                    const i = [];
                    for (let e = 0; e < this._listeners.length; e++) i.push(this._listeners[e]);
                    for (let s = 0; s < i.length; s++) i[s].call(void 0, e, t)
                }

                dispose() {
                    this.clearListeners(), this._disposed = !0
                }

                clearListeners() {
                    this._listeners && (this._listeners.length = 0)
                }
            }, t.forwardEvent = function (e, t) {
                return e((e => t.fire(e)))
            }
        }, 859: (e, t) => {
            function i(e) {
                for (const t of e) t.dispose();
                e.length = 0
            }

            Object.defineProperty(t, "__esModule", {value: !0}), t.getDisposeArrayDisposable = t.disposeArray = t.toDisposable = t.MutableDisposable = t.Disposable = void 0, t.Disposable = class {
                constructor() {
                    this._disposables = [], this._isDisposed = !1
                }

                dispose() {
                    this._isDisposed = !0;
                    for (const e of this._disposables) e.dispose();
                    this._disposables.length = 0
                }

                register(e) {
                    return this._disposables.push(e), e
                }

                unregister(e) {
                    const t = this._disposables.indexOf(e);
                    -1 !== t && this._disposables.splice(t, 1)
                }
            }, t.MutableDisposable = class {
                constructor() {
                    this._isDisposed = !1
                }

                get value() {
                    return this._isDisposed ? void 0 : this._value
                }

                set value(e) {
                    var t;
                    this._isDisposed || e === this._value || (null === (t = this._value) || void 0 === t || t.dispose(), this._value = e)
                }

                clear() {
                    this.value = void 0
                }

                dispose() {
                    var e;
                    this._isDisposed = !0, null === (e = this._value) || void 0 === e || e.dispose(), this._value = void 0
                }
            }, t.toDisposable = function (e) {
                return {dispose: e}
            }, t.disposeArray = i, t.getDisposeArrayDisposable = function (e) {
                return {dispose: () => i(e)}
            }
        }
    }, t = {};

    function i(s) {
        var r = t[s];
        if (void 0 !== r) return r.exports;
        var o = t[s] = {exports: {}};
        return e[s](o, o.exports, i), o.exports
    }

    var s = {};
    return (() => {
        var e = s;
        Object.defineProperty(e, "__esModule", {value: !0}), e.SearchAddon = void 0;
        const t = i(345), r = i(859), o = " ~!@#$%^&*()+`-=[]{}|\\;:\"',./<>?";

        class n extends r.Disposable {
            constructor(e) {
                var i;
                super(), this._highlightedLines = new Set, this._highlightDecorations = [], this._selectedDecoration = this.register(new r.MutableDisposable), this._linesCacheTimeoutId = 0, this._onDidChangeResults = this.register(new t.EventEmitter), this.onDidChangeResults = this._onDidChangeResults.event, this._highlightLimit = null !== (i = null == e ? void 0 : e.highlightLimit) && void 0 !== i ? i : 1e3
            }

            activate(e) {
                this._terminal = e, this.register(this._terminal.onWriteParsed((() => this._updateMatches()))), this.register(this._terminal.onResize((() => this._updateMatches()))), this.register((0, r.toDisposable)((() => this.clearDecorations())))
            }

            _updateMatches() {
                var e;
                this._highlightTimeout && window.clearTimeout(this._highlightTimeout), this._cachedSearchTerm && (null === (e = this._lastSearchOptions) || void 0 === e ? void 0 : e.decorations) && (this._highlightTimeout = setTimeout((() => {
                    const e = this._cachedSearchTerm;
                    this._cachedSearchTerm = void 0, this.findPrevious(e, Object.assign(Object.assign({}, this._lastSearchOptions), {
                        incremental: !0,
                        noScroll: !0
                    }))
                }), 200))
            }

            clearDecorations(e) {
                this._selectedDecoration.clear(), (0, r.disposeArray)(this._highlightDecorations), this._highlightDecorations = [], this._highlightedLines.clear(), e || (this._cachedSearchTerm = void 0)
            }

            findNext(e, t) {
                if (!this._terminal) throw new Error("Cannot use addon until it has been loaded");
                this._lastSearchOptions = t, (null == t ? void 0 : t.decorations) && (void 0 !== this._cachedSearchTerm && e === this._cachedSearchTerm || this._highlightAllMatches(e, t));
                const i = this._findNextAndSelect(e, t);
                return this._fireResults(t), this._cachedSearchTerm = e, i
            }

            _highlightAllMatches(e, t) {
                if (!this._terminal) throw new Error("Cannot use addon until it has been loaded");
                if (!e || 0 === e.length) return void this.clearDecorations();
                t = t || {}, this.clearDecorations(!0);
                const i = [];
                let s, r = this._find(e, 0, 0, t);
                for (; r && ((null == s ? void 0 : s.row) !== r.row || (null == s ? void 0 : s.col) !== r.col) && !(i.length >= this._highlightLimit);) s = r, i.push(s), r = this._find(e, s.col + s.term.length >= this._terminal.cols ? s.row + 1 : s.row, s.col + s.term.length >= this._terminal.cols ? 0 : s.col + 1, t);
                for (const e of i) {
                    const i = this._createResultDecoration(e, t.decorations);
                    i && (this._highlightedLines.add(i.marker.line), this._highlightDecorations.push({
                        decoration: i, match: e, dispose() {
                            i.dispose()
                        }
                    }))
                }
            }

            _find(e, t, i, s) {
                var r;
                if (!this._terminal || !e || 0 === e.length) return null === (r = this._terminal) || void 0 === r || r.clearSelection(), void this.clearDecorations();
                if (i > this._terminal.cols) throw new Error(`Invalid col: ${i} to search in terminal of ${this._terminal.cols} cols`);
                let o;
                this._initLinesCache();
                const n = {startRow: t, startCol: i};
                if (o = this._findInLine(e, n, s), !o) for (let i = t + 1; i < this._terminal.buffer.active.baseY + this._terminal.rows && (n.startRow = i, n.startCol = 0, o = this._findInLine(e, n, s), !o); i++) ;
                return o
            }

            _findNextAndSelect(e, t) {
                var i;
                if (!this._terminal || !e || 0 === e.length) return null === (i = this._terminal) || void 0 === i || i.clearSelection(), this.clearDecorations(), !1;
                const s = this._terminal.getSelectionPosition();
                this._terminal.clearSelection();
                let r = 0, o = 0;
                s && (this._cachedSearchTerm === e ? (r = s.end.x, o = s.end.y) : (r = s.start.x, o = s.start.y)), this._initLinesCache();
                const n = {startRow: o, startCol: r};
                let l = this._findInLine(e, n, t);
                if (!l) for (let i = o + 1; i < this._terminal.buffer.active.baseY + this._terminal.rows && (n.startRow = i, n.startCol = 0, l = this._findInLine(e, n, t), !l); i++) ;
                if (!l && 0 !== o) for (let i = 0; i < o && (n.startRow = i, n.startCol = 0, l = this._findInLine(e, n, t), !l); i++) ;
                return !l && s && (n.startRow = s.start.y, n.startCol = 0, l = this._findInLine(e, n, t)), this._selectResult(l, null == t ? void 0 : t.decorations, null == t ? void 0 : t.noScroll)
            }

            findPrevious(e, t) {
                if (!this._terminal) throw new Error("Cannot use addon until it has been loaded");
                this._lastSearchOptions = t, (null == t ? void 0 : t.decorations) && (void 0 !== this._cachedSearchTerm && e === this._cachedSearchTerm || this._highlightAllMatches(e, t));
                const i = this._findPreviousAndSelect(e, t);
                return this._fireResults(t), this._cachedSearchTerm = e, i
            }

            _fireResults(e) {
                if (null == e ? void 0 : e.decorations) {
                    let e = -1;
                    if (this._selectedDecoration.value) {
                        const t = this._selectedDecoration.value.match;
                        for (let i = 0; i < this._highlightDecorations.length; i++) {
                            const s = this._highlightDecorations[i].match;
                            if (s.row === t.row && s.col === t.col && s.size === t.size) {
                                e = i;
                                break
                            }
                        }
                    }
                    this._onDidChangeResults.fire({resultIndex: e, resultCount: this._highlightDecorations.length})
                }
            }

            _findPreviousAndSelect(e, t) {
                var i;
                if (!this._terminal) throw new Error("Cannot use addon until it has been loaded");
                if (!this._terminal || !e || 0 === e.length) return null === (i = this._terminal) || void 0 === i || i.clearSelection(), this.clearDecorations(), !1;
                const s = this._terminal.getSelectionPosition();
                this._terminal.clearSelection();
                let r = this._terminal.buffer.active.baseY + this._terminal.rows - 1, o = this._terminal.cols;
                const n = !0;
                this._initLinesCache();
                const l = {startRow: r, startCol: o};
                let h;
                if (s && (l.startRow = r = s.start.y, l.startCol = o = s.start.x, this._cachedSearchTerm !== e && (h = this._findInLine(e, l, t, !1), h || (l.startRow = r = s.end.y, l.startCol = o = s.end.x))), h || (h = this._findInLine(e, l, t, n)), !h) {
                    l.startCol = Math.max(l.startCol, this._terminal.cols);
                    for (let i = r - 1; i >= 0 && (l.startRow = i, h = this._findInLine(e, l, t, n), !h); i--) ;
                }
                if (!h && r !== this._terminal.buffer.active.baseY + this._terminal.rows - 1) for (let i = this._terminal.buffer.active.baseY + this._terminal.rows - 1; i >= r && (l.startRow = i, h = this._findInLine(e, l, t, n), !h); i--) ;
                return this._selectResult(h, null == t ? void 0 : t.decorations, null == t ? void 0 : t.noScroll)
            }

            _initLinesCache() {
                const e = this._terminal;
                this._linesCache || (this._linesCache = new Array(e.buffer.active.length), this._cursorMoveListener = e.onCursorMove((() => this._destroyLinesCache())), this._resizeListener = e.onResize((() => this._destroyLinesCache()))), window.clearTimeout(this._linesCacheTimeoutId), this._linesCacheTimeoutId = window.setTimeout((() => this._destroyLinesCache()), 15e3)
            }

            _destroyLinesCache() {
                this._linesCache = void 0, this._cursorMoveListener && (this._cursorMoveListener.dispose(), this._cursorMoveListener = void 0), this._resizeListener && (this._resizeListener.dispose(), this._resizeListener = void 0), this._linesCacheTimeoutId && (window.clearTimeout(this._linesCacheTimeoutId), this._linesCacheTimeoutId = 0)
            }

            _isWholeWord(e, t, i) {
                return (0 === e || o.includes(t[e - 1])) && (e + i.length === t.length || o.includes(t[e + i.length]))
            }

            _findInLine(e, t, i = {}, s = !1) {
                var r;
                const o = this._terminal, n = t.startRow, l = t.startCol, h = o.buffer.active.getLine(n);
                if (null == h ? void 0 : h.isWrapped) return s ? void (t.startCol += o.cols) : (t.startRow--, t.startCol += o.cols, this._findInLine(e, t, i));
                let a = null === (r = this._linesCache) || void 0 === r ? void 0 : r[n];
                a || (a = this._translateBufferLineToStringWithWrap(n, !0), this._linesCache && (this._linesCache[n] = a));
                const [c, d] = a, _ = this._bufferColsToStringOffset(n, l), u = i.caseSensitive ? e : e.toLowerCase(),
                    f = i.caseSensitive ? c : c.toLowerCase();
                let g = -1;
                if (i.regex) {
                    const t = RegExp(u, "g");
                    let i;
                    if (s) for (; i = t.exec(f.slice(0, _));) g = t.lastIndex - i[0].length, e = i[0], t.lastIndex -= e.length - 1; else i = t.exec(f.slice(_)), i && i[0].length > 0 && (g = _ + (t.lastIndex - i[0].length), e = i[0])
                } else s ? _ - u.length >= 0 && (g = f.lastIndexOf(u, _ - u.length)) : g = f.indexOf(u, _);
                if (g >= 0) {
                    if (i.wholeWord && !this._isWholeWord(g, f, e)) return;
                    let t = 0;
                    for (; t < d.length - 1 && g >= d[t + 1];) t++;
                    let s = t;
                    for (; s < d.length - 1 && g + e.length >= d[s + 1];) s++;
                    const r = g - d[t], l = g + e.length - d[s], h = this._stringLengthToBufferSize(n + t, r);
                    return {term: e, col: h, row: n + t, size: this._stringLengthToBufferSize(n + s, l) - h + o.cols * (s - t)}
                }
            }

            _stringLengthToBufferSize(e, t) {
                const i = this._terminal.buffer.active.getLine(e);
                if (!i) return 0;
                for (let e = 0; e < t; e++) {
                    const s = i.getCell(e);
                    if (!s) break;
                    const r = s.getChars();
                    r.length > 1 && (t -= r.length - 1);
                    const o = i.getCell(e + 1);
                    o && 0 === o.getWidth() && t++
                }
                return t
            }

            _bufferColsToStringOffset(e, t) {
                const i = this._terminal;
                let s = e, r = 0, o = i.buffer.active.getLine(s);
                for (; t > 0 && o;) {
                    for (let e = 0; e < t && e < i.cols; e++) {
                        const t = o.getCell(e);
                        if (!t) break;
                        t.getWidth() && (r += 0 === t.getCode() ? 1 : t.getChars().length)
                    }
                    if (s++, o = i.buffer.active.getLine(s), o && !o.isWrapped) break;
                    t -= i.cols
                }
                return r
            }

            _translateBufferLineToStringWithWrap(e, t) {
                var i;
                const s = this._terminal, r = [], o = [0];
                let n = s.buffer.active.getLine(e);
                for (; n;) {
                    const l = s.buffer.active.getLine(e + 1), h = !!l && l.isWrapped;
                    let a = n.translateToString(!h && t);
                    if (h && l) {
                        const e = n.getCell(n.length - 1);
                        e && 0 === e.getCode() && 1 === e.getWidth() && 2 === (null === (i = l.getCell(0)) || void 0 === i ? void 0 : i.getWidth()) && (a = a.slice(0, -1))
                    }
                    if (r.push(a), !h) break;
                    o.push(o[o.length - 1] + a.length), e++, n = l
                }
                return [r.join(""), o]
            }

            _selectResult(e, t, i) {
                const s = this._terminal;
                if (this._selectedDecoration.clear(), !e) return s.clearSelection(), !1;
                if (s.select(e.col, e.row, e.size), t) {
                    const i = s.registerMarker(-s.buffer.active.baseY - s.buffer.active.cursorY + e.row);
                    if (i) {
                        const o = s.registerDecoration({
                            marker: i,
                            x: e.col,
                            width: e.size,
                            backgroundColor: t.activeMatchBackground,
                            layer: "top",
                            overviewRulerOptions: {color: t.activeMatchColorOverviewRuler}
                        });
                        if (o) {
                            const s = [];
                            s.push(i), s.push(o.onRender((e => this._applyStyles(e, t.activeMatchBorder, !0)))), s.push(o.onDispose((() => (0, r.disposeArray)(s)))), this._selectedDecoration.value = {
                                decoration: o,
                                match: e,
                                dispose() {
                                    o.dispose()
                                }
                            }
                        }
                    }
                }
                if (!i && (e.row >= s.buffer.active.viewportY + s.rows || e.row < s.buffer.active.viewportY)) {
                    let t = e.row - s.buffer.active.viewportY;
                    t -= Math.floor(s.rows / 2), s.scrollLines(t)
                }
                return !0
            }

            _applyStyles(e, t, i) {
                e.classList.contains("xterm-find-result-decoration") || (e.classList.add("xterm-find-result-decoration"), t && (e.style.outline = `1px solid ${t}`)), i && e.classList.add("xterm-find-active-result-decoration")
            }

            _createResultDecoration(e, t) {
                const i = this._terminal, s = i.registerMarker(-i.buffer.active.baseY - i.buffer.active.cursorY + e.row);
                if (!s) return;
                const o = i.registerDecoration({
                    marker: s,
                    x: e.col,
                    width: e.size,
                    backgroundColor: t.matchBackground,
                    overviewRulerOptions: this._highlightedLines.has(s.line) ? void 0 : {color: t.matchOverviewRuler, position: "center"}
                });
                if (o) {
                    const e = [];
                    e.push(s), e.push(o.onRender((e => this._applyStyles(e, t.matchBorder, !1)))), e.push(o.onDispose((() => (0, r.disposeArray)(e))))
                }
                return o
            }
        }

        e.SearchAddon = n
    })(), s
})()));
//# sourceMappingURL=xterm-addon-search.js.map