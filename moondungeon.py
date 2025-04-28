#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dungeon ⇄ Moon Config Editor —  v0.9
Author  : ChatGPT  ·  2025-04-29

New since 0.8
────────────
• Enemy tab radio-row lets you flip between  *Moon → Enemies*  and
  *Enemy → Moons*  (mirrors the dungeon tab behaviour).
• Interior/Day/Night panes now list the **full union of enemies** found in
  the file, not just the ones already present in that category.
• No previous functionality removed; only additive tweaks & small refactors.

Requires :  ttkbootstrap  →  pip install ttkbootstrap
"""

###############################################################################
# -------------------------------- PARSER -------------------------------------
###############################################################################
import os, re, sys, platform, tkinter as tk
from collections import OrderedDict
from tkinter import filedialog, messagebox

SECTION_RE_DUNGEON = re.compile(r"\[Dungeon:\s*(.+?)\s*\]")
SECTION_RE_MOON    = re.compile(r"\[Moon:\s*(.+?)\s*\]")

ADD_LINE_SUFFIX    = " - Add Dungeon by Planet Name ="
SCRAP_LINE_SUFFIX  = " - Scrap List ="

ENEMY_SUFFIXES = {                       # type  → suffix
    "interior": " - Interior Enemy List =",
    "day"     : " - Daytime Enemy List =",
    "night"   : " - Nighttime Enemy List =",
}

def parse_cfg(path):
    """
    Returns:
        dmap :  OrderedDict{ dungeon : OrderedDict{moon   : weight} }
        smap :  OrderedDict{  moon   : OrderedDict{scrap   : weight} }
        emap :  OrderedDict{  moon   : {type : OrderedDict{enemy : weight}} }
        moons:  OrderedDict{  moon   : bool }
        lines:  list(str)  original file lines
    """
    dmap, smap, emap, moons = OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict()
    cur_dun = cur_moon = None

    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    for ln in lines:
        mdun = SECTION_RE_DUNGEON.match(ln)
        mmoo = SECTION_RE_MOON.match(ln)

        if mdun:
            cur_dun, cur_moon = mdun.group(1).strip(), None
            dmap.setdefault(cur_dun, OrderedDict())
            continue

        if mmoo:
            cur_moon, cur_dun = mmoo.group(1).strip(), None
            moons[cur_moon] = True
            smap.setdefault(cur_moon, OrderedDict())
            emap.setdefault(cur_moon, {t: OrderedDict() for t in ENEMY_SUFFIXES})
            continue

        # dungeon ⇄ moon
        if cur_dun and ADD_LINE_SUFFIX in ln:
            val = ln.split("=", 1)[1].strip()
            if val.lower().startswith("default values"):
                continue
            for pair in (p.strip() for p in val.split(",") if p.strip()):
                if ":" not in pair:
                    continue
                moon, w = map(str.strip, pair.split(":", 1))
                dmap[cur_dun][moon] = w
                moons.setdefault(moon, False)

        # moon ⇄ scrap
        if cur_moon and SCRAP_LINE_SUFFIX in ln:
            val = ln.split("=", 1)[1].strip()
            if val.lower().startswith("default value"):
                continue
            for pair in (p.strip() for p in val.split(",") if p.strip()):
                if ":" not in pair:
                    continue
                scrap, w = map(str.strip, pair.split(":", 1))
                smap[cur_moon][scrap] = w

        # moon ⇄ enemies
        if cur_moon:
            for etype, suf in ENEMY_SUFFIXES.items():
                if suf in ln:
                    val = ln.split("=", 1)[1].strip()
                    if val.lower().startswith("default value"):
                        break
                    for pair in (p.strip() for p in val.split(",") if p.strip()):
                        if ":" not in pair:
                            continue
                        enemy, w = map(str.strip, pair.split(":", 1))
                        emap[cur_moon][etype][enemy] = w
                    break

    return dmap, smap, emap, moons, lines


def build_add_line(dungeon, mapping, indent=""):
    key = f"{dungeon}{ADD_LINE_SUFFIX} "
    val = ",".join(f"{m}:{w}" for m, w in mapping.items()) or "Default Values Were Empty"
    return f"{indent}{key}{val}\n"


def build_scrap_line(moon, mapping, indent=""):
    key = f"{moon}{SCRAP_LINE_SUFFIX} "
    val = ",".join(f"{s}:{w}" for s, w in mapping.items()) or "Default value was empty"
    return f"{indent}{key}{val}\n"


def build_enemy_line(moon, etype, mapping, indent=""):
    key = f"{moon}{ENEMY_SUFFIXES[etype]} "
    val = ",".join(f"{e}:{w}" for e, w in mapping.items()) or "Default value was empty"
    return f"{indent}{key}{val}\n"


def write_cfg(orig_lines, dmap, smap, emap, out_path):
    """Re-emit every original line, rewriting only mapping lines."""
    new_lines               = []
    cur_dun = cur_moon      = None
    dun_indent = moon_indent = ""

    for ln in orig_lines:
        mdun = SECTION_RE_DUNGEON.match(ln)
        mmoo = SECTION_RE_MOON.match(ln)

        if mdun:
            cur_dun, cur_moon = mdun.group(1).strip(), None
            dun_indent        = ""
            new_lines.append(ln)
            continue
        if mmoo:
            cur_moon, cur_dun = mmoo.group(1).strip(), None
            moon_indent       = ""
            new_lines.append(ln)
            continue

        if cur_dun and not dun_indent and ln.strip():
            dun_indent = ln[: len(ln) - len(ln.lstrip())]
        if cur_moon and not moon_indent and ln.strip():
            moon_indent = ln[: len(ln) - len(ln.lstrip())]

        if cur_dun and ADD_LINE_SUFFIX in ln and cur_dun in dmap:
            new_lines.append(build_add_line(cur_dun, dmap[cur_dun], dun_indent))
            cur_dun = None
            continue

        if cur_moon and SCRAP_LINE_SUFFIX in ln and cur_moon in smap:
            new_lines.append(build_scrap_line(cur_moon, smap[cur_moon], moon_indent))
            cur_moon = None
            continue

        if cur_moon:
            replaced = False
            for etype, suf in ENEMY_SUFFIXES.items():
                if suf in ln and etype in emap.get(cur_moon, {}):
                    new_lines.append(build_enemy_line(cur_moon, etype,
                                                      emap[cur_moon][etype],
                                                      moon_indent))
                    replaced = True
                    break
            if replaced:
                cur_moon = None
                continue

        new_lines.append(ln)

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(new_lines)

###############################################################################
# -------------------------------- UI  ----------------------------------------
###############################################################################
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

FONT_FAMILY = "Segoe UI"
FONT_SIZE   = 13

BTN_W        = 26          # default pill width
BTN_W_ENEMY  = 20          # slimmer pill for enemy names
CLR_ORANGE   = "#eb8600"
CLR_PURPLE   = "#714cff"

class ScrollPane(ttkb.Frame):
    """Reusable canvas+frame scroller."""
    def __init__(self, master, width=260, **kw):
        super().__init__(master, **kw)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        bg = master.winfo_toplevel().style.colors.dark
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, width=width)
        self.inner  = ttkb.Frame(self.canvas)

        self.scr_y  = ttkb.Scrollbar(self, orient="vertical",
                                     command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scr_y.set)
        self.win_id = self.canvas.create_window((0, 0), window=self.inner,
                                                anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scr_y.grid(row=0, column=1, sticky="ns")

        self.inner.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self.win_id, width=e.width))

        self._bind_wheel()

    def _sync(self, *_):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_wheel(self):
        sys_plat = platform.system()
        if sys_plat == "Windows":
            on = lambda *_: self.canvas.bind_all(
                    "<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
            off = lambda *_: self.canvas.unbind_all("<MouseWheel>")
        elif sys_plat == "Darwin":
            on = lambda *_: self.canvas.bind_all(
                    "<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta), "units"))
            off = lambda *_: self.canvas.unbind_all("<MouseWheel>")
        else:  # X11
            on = lambda *_: (self.canvas.bind_all("<Button-4>",
                    lambda e: self.canvas.yview_scroll(-1, "units")),
                    self.canvas.bind_all("<Button-5>",
                    lambda e: self.canvas.yview_scroll( 1, "units")))
            off = lambda *_: (self.canvas.unbind_all("<Button-4>"),
                              self.canvas.unbind_all("<Button-5>"))

        self.canvas.bind("<Enter>", on)
        self.canvas.bind("<Leave>", off)

# -----------------------------------------------------------------------------


class ConfigEditor(ttkb.Window):
    """Main application window."""
    def __init__(self):
        super().__init__(themename="darkly")

        # ───────── Window basics
        self.title("Dungeon ⇄ Moon Config Editor")
        self.geometry("1480x860")
        self.minsize(1180, 670)
        self.style.configure(".", font=(FONT_FAMILY, FONT_SIZE))

        # ───────── Data
        self.cfg_path  = None
        self.lines     = []
        self.dmap      = OrderedDict()
        self.smap      = OrderedDict()
        self.emap      = OrderedDict()
        self.enemy_un  = {t: set() for t in ENEMY_SUFFIXES}
        self.all_enemies = set()
        self.moons     = OrderedDict()

        self.rel_mode  = tk.StringVar(value="moon")      # dungeon tab toggle
        self.view      = tk.StringVar(value="dungeon")   # active tab
        self.enemy_cat = tk.StringVar(value="interior")  # interior/day/night
        self.enemy_mode = tk.StringVar(value="moon")     # moon vs enemy primary

        # ───────── Custom styles
        self._create_styles()

        # ───────── Menu + layout
        self._build_menu()
        self._build_layout()

        self.bind_all("<F2>", lambda *_: self._toggle_mode())

    # ════════════════════════════════════════════════════════════════════════
    #   STYLE
    # ════════════════════════════════════════════════════════════════════════
    def _create_styles(self):
        s = self.style
        s.configure("MoonSolid.TButton",
                    background=CLR_ORANGE, foreground="white",
                    bordercolor=CLR_ORANGE, relief="flat")
        s.configure("DungeonSolid.TButton",
                    background=CLR_PURPLE, foreground="white",
                    bordercolor=CLR_PURPLE, relief="flat")
        s.configure("MoonOutline.TButton",
                    foreground=CLR_ORANGE, bordercolor=CLR_ORANGE,
                    background=s.colors.bg, relief="ridge")
        s.configure("DungeonOutline.TButton",
                    foreground=CLR_PURPLE, bordercolor=CLR_PURPLE,
                    background=s.colors.bg, relief="ridge")
        s.configure("MidMoon.TButton",
                    foreground=CLR_PURPLE, bordercolor=CLR_PURPLE,
                    background=s.colors.bg, relief="ridge")
        s.configure("MidDungeon.TButton",
                    foreground=CLR_ORANGE, bordercolor=CLR_ORANGE,
                    background=s.colors.bg, relief="ridge")

    # ════════════════════════════════════════════════════════════════════════
    #   MENU
    # ════════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        mb = tk.Menu(self)

        fm = tk.Menu(mb, tearoff=False)
        fm.add_command(label="Open…",      accelerator="Ctrl+O", command=self.open_cfg)
        fm.add_command(label="Save As…",   accelerator="Ctrl+S", command=self.save_cfg)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.destroy)
        mb.add_cascade(label="File", menu=fm)

        self.config(menu=mb)
        self.bind_all("<Control-o>", lambda *_: self.open_cfg())
        self.bind_all("<Control-s>", lambda *_: self.save_cfg())

    # ════════════════════════════════════════════════════════════════════════
    #   LAYOUT
    # ════════════════════════════════════════════════════════════════════════
    def _build_layout(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(0, weight=1)

        # ── LEFT panel (primary list) ───────────────────────────────────────
        left = ttkb.Frame(self, padding=6)
        left.grid(row=0, column=0, sticky="nsw")
        left.rowconfigure(2, weight=1)

        self.radiobox = ttkb.Frame(left)
        self.radiobox.grid(row=0, column=0, sticky="w", columnspan=2)
        for txt, val in [("Moon → Dungeons", "moon"),
                         ("Dungeon → Moons", "dungeon")]:
            ttkb.Radiobutton(self.radiobox, text=txt, variable=self.rel_mode,
                             value=val, command=self._rebuild_primary
                             ).pack(side="left")
        ttkb.Label(self.radiobox, text=" (F2 toggles)").pack(side="left", padx=4)

        self.prime_pane = ScrollPane(left, width=260)
        self.prime_pane.grid(row=2, column=0, sticky="nsw")

        # ── NOTEBOOK (mid + summary columns) ────────────────────────────────
        self.nb = ttkb.Notebook(self)
        self.nb.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Tab 1 – Dungeons
        self.tab_dun = ttkb.Frame(self.nb)
        self.nb.add(self.tab_dun, text="Dungeons")
        self._build_tab(self.tab_dun, "dun")

        # Tab 2 – Scrap
        self.tab_scr = ttkb.Frame(self.nb)
        self.nb.add(self.tab_scr, text="Scrap")
        self._build_tab(self.tab_scr, "scr")

        # Tab 3 – Enemies
        self.tab_en = ttkb.Frame(self.nb)
        self.nb.add(self.tab_en, text="Enemies")
        self._build_enemy_tab(self.tab_en)

        # SAVE button
        self.save_btn = ttkb.Button(self, text="Save All Changes",
                                    bootstyle=SUCCESS,
                                    command=self.save_cfg,
                                    state=DISABLED)
        self.save_btn.grid(row=1, column=2, pady=6, padx=12, sticky="e")

    # ------------------------------------------------------------------ generic tab
    def _build_tab(self, parent, tid):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        pane = ScrollPane(parent)
        pane.grid(row=0, column=0, sticky="nsew")
        setattr(self, f"relate_{tid}", pane)

        summary = ttkb.Frame(parent, padding=(6, 0, 0, 6))
        summary.grid(row=0, column=1, sticky="nsew")
        summary.columnconfigure(0, weight=1)
        setattr(self, f"summary_{tid}", summary)

        self._build_summary_header(summary, tid)

    # ------------------------------------------------------------------ enemy tab
    def _build_enemy_tab(self, parent):
        # orientation radio
        r_orient = ttkb.Frame(parent, padding=(6, 6, 6, 0))
        r_orient.grid(row=0, column=0, sticky="w")
        for txt, val in [("Moon → Enemies", "moon"),
                         ("Enemy → Moons", "enemy")]:
            ttkb.Radiobutton(r_orient, text=txt, variable=self.enemy_mode,
                             value=val, command=self._rebuild_primary
                             ).pack(side="left")

        # category radio
        r_cat = ttkb.Frame(parent, padding=(6, 2, 6, 0))
        r_cat.grid(row=1, column=0, sticky="w")
        for txt, val in [("Interior", "interior"),
                         ("Daytime",  "day"),
                         ("Nighttime","night")]:
            ttkb.Radiobutton(r_cat, text=txt, variable=self.enemy_cat,
                             value=val, command=lambda:
                             (self._populate_secondary(getattr(self,
                                                    "selected_primary", None)),
                              self._refresh_summary(getattr(self,
                                                    "selected_primary", None)))
                             ).pack(side="left")

        # mid-pane + summary
        frm = ttkb.Frame(parent)
        frm.grid(row=2, column=0, sticky="nsew")
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0,  weight=1)

        pane = ScrollPane(frm, width=550)        # wider pane
        pane.grid(row=0, column=0, sticky="nsew")
        self.relate_en = pane

        self._build_tab(frm, "en")               # builds summary on the right

        # NEW ─ let row 2 stretch
        parent.rowconfigure(2, weight=1)

    # ------------------------------------------------------------------ summary helper
    def _build_summary_header(self, parent, tid):
        lbl = ttkb.Label(parent, text="", bootstyle="inverse")
        lbl.grid(row=0, column=0, sticky="w")
        setattr(self, f"sum_lbl_{tid}", lbl)

        header = ttkb.Frame(parent)
        header.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        for c, txt, w in [(0, "Item", 26), (1, "Weight", 7), (2, "% of total", 10)]:
            ttkb.Label(header, text=txt, anchor="center", width=w,
                       bootstyle=("secondary", "inverse")
                       ).grid(row=0, column=c, padx=1, sticky="ew")

        body = ttkb.Frame(parent, borderwidth=1, relief="solid")
        body.grid(row=2, column=0, sticky="nsew")
        parent.rowconfigure(2, weight=1)
        setattr(self, f"sum_body_{tid}", body)

    # ════════════════════════════════════════════════════════════════════════
    #   PRIMARY LIST
    # ════════════════════════════════════════════════════════════════════════
    def _rebuild_primary(self):
        for w in self.prime_pane.inner.winfo_children():
            w.destroy()

        view = self.view.get()

        if view == "scrap":
            outline = "MoonOutline.TButton"
            items   = (m for m, r in self.moons.items() if r)

        elif view == "enemy":
            if self.enemy_mode.get() == "moon":
                outline = "MoonOutline.TButton"
                items   = (m for m, r in self.moons.items() if r)
            else:  # enemy primary list
                outline = "DungeonOutline.TButton"
                items   = sorted(self.all_enemies, key=str.lower)
        else:  # dungeon tab
            outline = "MoonOutline.TButton" if self.rel_mode.get()=="moon" else "DungeonOutline.TButton"
            items   = (m for m, r in self.moons.items() if r) \
                      if self.rel_mode.get()=="moon" else self.dmap.keys()

        for i, key in enumerate(items):
            ttkb.Button(self.prime_pane.inner, text=key, width=BTN_W,
                        style=outline,
                        command=lambda k=key: self._select_primary(k)
                        ).grid(row=i, column=0, sticky="w", pady=2)

        self.prime_pane._sync()

        self._populate_secondary(None)
        self._refresh_summary(None)
        self.radiobox.grid_remove() if (view != "dungeon") else self.radiobox.grid()

    # ════════════════════════════════════════════════════════════════════════
    #   SELECTION + HIGHLIGHT
    # ════════════════════════════════════════════════════════════════════════
    def _select_primary(self, key):
        self.selected_primary = key
        self._highlight_primary()
        self._populate_secondary(key)
        self._refresh_summary(key)

    def _highlight_primary(self):
        view = self.view.get()
        sel  = getattr(self, "selected_primary", None)

        if view == "dungeon":
            solid   = "MoonSolid.TButton" if self.rel_mode.get()=="moon" else "DungeonSolid.TButton"
            outline = "MoonOutline.TButton" if self.rel_mode.get()=="moon" else "DungeonOutline.TButton"
        elif view == "enemy" and self.enemy_mode.get() == "enemy":
            solid, outline = "DungeonSolid.TButton", "DungeonOutline.TButton"
        else:
            solid, outline = "MoonSolid.TButton", "MoonOutline.TButton"

        for b in self.prime_pane.inner.winfo_children():
            if isinstance(b, ttkb.Button):
                b.configure(style=solid if b.cget("text")==sel else outline)

    # ════════════════════════════════════════════════════════════════════════
    #   SECONDARY (middle pane)
    # ════════════════════════════════════════════════════════════════════════
    def _populate_secondary(self, sel):
        view = self.view.get()
        pane = getattr(self, f"relate_{'en' if view=='enemy' else view[:3]}")

        for w in pane.inner.winfo_children():
            w.destroy()

        if not sel:
            pane._sync()
            return

        rel = self.rel_mode.get()

        # ---------- SCRAP TAB
        if view == "scrap":
            items = sorted(self.smap.get(sel, {}).items(), key=lambda x: x[0].lower())
            style_mid = "MidMoon.TButton"

        # ---------- ENEMY TAB
        elif view == "enemy":
            etype = self.enemy_cat.get()

            if self.enemy_mode.get() == "moon":      # moon → enemies
                all_names = sorted(self.all_enemies, key=str.lower)
                m_map = self.emap.get(sel, {}).get(etype, {})
                items = [(name, m_map.get(name, "")) for name in all_names]
                style_mid = "MidMoon.TButton"
            else:                                    # enemy → moons
                all_moons = sorted([m for m, r in self.moons.items() if r], key=str.lower)
                items = [(m, self.emap[m][etype].get(sel, "")) for m in all_moons]
                style_mid = "MidDungeon.TButton"

        # ---------- DUNGEON TAB
        else:
            style_mid = "MidMoon.TButton" if rel == "moon" else "MidDungeon.TButton"
            if rel == "moon":
                items = [(d, self.dmap[d].get(sel, "")) for d in self.dmap]
            else:
                items = [(m, self.dmap[sel].get(m, "")) for m, r in self.moons.items() if r]

        w_btn = BTN_W_ENEMY if (view == "enemy" and self.enemy_mode.get()=="moon") else BTN_W

        for r, (name, wgt) in enumerate(items):
            present = bool(wgt)

            ttkb.Button(pane.inner, text=name, width=w_btn, style=style_mid
                       ).grid(row=r, column=0, sticky="w", padx=(0, 4), pady=2)

            var = tk.StringVar(value=str(wgt) if present else "")
            ttkb.Entry(pane.inner, textvariable=var, width=8
                       ).grid(row=r, column=1, padx=4)

            def _add_upd(k=name, v=var): self._add_update(sel, k, v)
            def _rmv(k=name):            self._remove(sel, k)

            if present:
                ttkb.Button(pane.inner, text="Update", command=_add_upd,
                            bootstyle=(INFO, OUTLINE, ROUND)
                           ).grid(row=r, column=2, padx=2)
                ttkb.Button(pane.inner, text="Remove", command=_rmv,
                            bootstyle=(DANGER, OUTLINE, ROUND)
                           ).grid(row=r, column=3, padx=2)
            else:
                ttkb.Button(pane.inner, text="Add", command=_add_upd,
                            bootstyle=(SUCCESS, OUTLINE, ROUND)
                           ).grid(row=r, column=2, padx=2)

        pane._sync()

    # ════════════════════════════════════════════════════════════════════════
    #   MUTATORS
    # ════════════════════════════════════════════════════════════════════════
    def _add_update(self, primary, secondary, var):
        w = var.get().strip()
        if not w.isdigit() or int(w) <= 0:
            messagebox.showerror("Weight error", "Weight must be a positive integer")
            return

        view = self.view.get()

        if view == "scrap":
            self.smap.setdefault(primary, OrderedDict())[secondary] = w

        elif view == "enemy":
            et = self.enemy_cat.get()
            self.all_enemies.add(primary if self.enemy_mode.get()=="enemy" else secondary)

            if self.enemy_mode.get() == "moon":       # moon → enemies
                self.emap.setdefault(primary, {}).setdefault(et, OrderedDict())[secondary] = w
            else:                                     # enemy → moons
                self.emap.setdefault(secondary, {}).setdefault(et, OrderedDict())[primary] = w

        else:  # dungeon tab
            if self.rel_mode.get() == "moon":
                self.dmap[secondary][primary] = w
            else:
                self.dmap[primary][secondary] = w

        self._select_primary(primary)

    def _remove(self, primary, secondary):
        view = self.view.get()

        if view == "scrap":
            self.smap.get(primary, {}).pop(secondary, None)

        elif view == "enemy":
            et = self.enemy_cat.get()
            if self.enemy_mode.get() == "moon":
                self.emap.get(primary, {}).get(et, {}).pop(secondary, None)
            else:
                self.emap.get(secondary, {}).get(et, {}).pop(primary, None)

        else:
            if self.rel_mode.get() == "moon":
                self.dmap[secondary].pop(primary, None)
            else:
                self.dmap[primary].pop(secondary, None)

        self._select_primary(primary)

    # ════════════════════════════════════════════════════════════════════════
    #   SUMMARY PANEL
    # ════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _hex_interp(c1, c2, t):
        h1 = tuple(int(c1[i:i+2], 16) for i in (1, 3, 5))
        h2 = tuple(int(c2[i:i+2], 16) for i in (1, 3, 5))
        mix = tuple(int(a + (b - a) * t) for a, b in zip(h1, h2))
        return f"#{mix[0]:02x}{mix[1]:02x}{mix[2]:02x}"

    def _refresh_summary(self, primary):
        view = self.view.get()
        body = getattr(self, f"sum_body_{'en' if view=='enemy' else view[:3]}")
        lbl  = getattr(self, f"sum_lbl_{'en' if view=='enemy' else view[:3]}")

        for w in body.winfo_children():
            w.destroy()

        if not primary:
            lbl["text"] = ""
            return

        # ---------- SCRAP
        if view == "scrap":
            rows = [(s, int(w)) for s, w in self.smap.get(primary, {}).items()]
            lbl["text"] = "Scrap distribution on this moon"

        # ---------- ENEMY
        elif view == "enemy":
            et = self.enemy_cat.get()
            if self.enemy_mode.get() == "moon":
                rows = [(e, int(w)) for e, w in
                        self.emap.get(primary, {}).get(et, {}).items()]
                lbl["text"] = f"{et.capitalize()} enemies on this moon"
            else:
                # NEW ─ iterate safely over moons that actually exist in emap
                rows = []
                for m, typedict in self.emap.items():
                    if primary in typedict.get(et, {}):
                        rows.append((m, int(typedict[et][primary])))
                lbl["text"] = f"Moons containing '{primary}' ({et})"

        # ---------- DUNGEON
        else:
            if self.rel_mode.get() == "moon":
                rows = [(d, int(self.dmap[d][primary]))
                        for d in self.dmap if primary in self.dmap[d]]
            else:
                rows = [(m, int(w)) for m, w in self.dmap[primary].items()]
            lbl["text"] = "Active dungeons on this moon"

        rows.sort(key=lambda x: -x[1])
        total   = sum(w for _, w in rows) or 1
        max_pct = rows[0][1] / total if rows else 1

        for r, (name, w) in enumerate(rows):
            pct       = w / total
            pct_text  = f"{pct*100:4.1f}%"
            t         = pct / max_pct if max_pct else 0
            fg_color  = self._hex_interp("#d91a1a",
                            self._hex_interp("#ffee55", "#1abe26", t), t)

            ttkb.Label(body, text=name, anchor="w", width=26
                       ).grid(row=r, column=0, sticky="w", padx=1)
            ttkb.Label(body, text=w,    anchor="center", width=7
                       ).grid(row=r, column=1, sticky="e", padx=1)
            ttkb.Label(body, text=pct_text, anchor="center", width=10,
                       foreground=fg_color
                       ).grid(row=r, column=2, sticky="e", padx=1)

    # ════════════════════════════════════════════════════════════════════════
    #   FILE I/O
    # ════════════════════════════════════════════════════════════════════════
    def open_cfg(self):
        p = filedialog.askopenfilename(filetypes=[("Config files", "*.cfg"),
                                                  ("All files", "*.*")])
        if not p:
            return
        try:
            self.dmap, self.smap, self.emap, self.moons, self.lines = parse_cfg(p)
            # build universe of enemies per type + overall union
            self.enemy_un = {t: set() for t in ENEMY_SUFFIXES}
            for moon in self.emap:
                for t in ENEMY_SUFFIXES:
                    self.enemy_un[t].update(self.emap[moon][t].keys())
            self.all_enemies = set().union(*self.enemy_un.values())
        except Exception as e:
            messagebox.showerror("Parse error", str(e))
            return

        self.cfg_path = p
        self.save_btn["state"] = NORMAL
        self._rebuild_primary()
        self.title(f"Dungeon ⇄ Moon Config Editor — {os.path.basename(p)}")

    def save_cfg(self, *_):
        if not self.cfg_path:
            return
        out = filedialog.asksaveasfilename(defaultextension=".cfg",
                                           filetypes=[("Config files", "*.cfg"),
                                                      ("All files", "*.*")])
        if not out:
            return
        try:
            write_cfg(self.lines, self.dmap, self.smap, self.emap, out)
            messagebox.showinfo("Saved", f"Wrote {out}")
        except Exception as e:
            messagebox.showerror("Write error", str(e))

    # ════════════════════════════════════════════════════════════════════════
    #   MISC
    # ════════════════════════════════════════════════════════════════════════
    def _on_tab_changed(self, *_):
        idx = self.nb.index(self.nb.select())
        self.view.set(("dungeon", "scrap", "enemy")[idx])
        self._rebuild_primary()

    def _toggle_mode(self):
        if self.view.get() != "dungeon":
            return
        self.rel_mode.set("dungeon" if self.rel_mode.get()=="moon" else "moon")
        self._rebuild_primary()

###############################################################################
# MAIN
###############################################################################
def main():
    ConfigEditor().mainloop()

if __name__ == "__main__":
    main()
