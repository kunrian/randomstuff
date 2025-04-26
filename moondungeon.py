#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dungeon ⇄ Moon Config Editor —  v0.5.1
Author  : ChatGPT  ·  2025-04-26

Requires: ttkbootstrap  →  pip install ttkbootstrap
"""

###############################################################################
# -------------------------------- PARSER -------------------------------------
###############################################################################
import os, re, sys, math, platform, tkinter as tk
from collections import OrderedDict
from tkinter import filedialog, messagebox

SECTION_RE_DUNGEON = re.compile(r"\[Dungeon:\s*(.+?)\s*\]")
SECTION_RE_MOON    = re.compile(r"\[Moon:\s*(.+?)\s*\]")
ADD_LINE_SUFFIX    = " - Add Dungeon by Planet Name ="

def parse_cfg(path):
    """
    Returns:
        dmap   : OrderedDict{ dungeon : OrderedDict{moon:weight} }
        moons  : OrderedDict{ moon : bool }  (bool == True if the moon has a real section)
        lines  : list(str)  original file lines
    """
    dmap   = OrderedDict()
    moons  = OrderedDict()
    cur_d  = None

    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    for ln in lines:
        mdun = SECTION_RE_DUNGEON.match(ln)
        mmoo = SECTION_RE_MOON.match(ln)

        if mdun:
            cur_d = mdun.group(1).strip()
            dmap.setdefault(cur_d, OrderedDict())
            continue
        if mmoo:
            moon = mmoo.group(1).strip()
            moons[moon] = True
            continue
        if cur_d and ADD_LINE_SUFFIX in ln:
            val = ln.split("=", 1)[1].strip()
            if val.lower().startswith("default values"):
                continue
            for pair in (p.strip() for p in val.split(",") if p.strip()):
                if ":" not in pair:
                    continue
                moon, w = map(str.strip, pair.split(":", 1))
                dmap[cur_d][moon] = w
                moons.setdefault(moon, False)

    return dmap, moons, lines


def build_add_line(dungeon, mapping, indent=""):
    key = f"{dungeon} - Add Dungeon by Planet Name = "
    val = ",".join(f"{m}:{w}" for m, w in mapping.items()) or "Default Values Were Empty"
    return f"{indent}{key}{val}\n"


def write_cfg(orig_lines, dmap, out_path):
    new_lines, cur, indent = [], None, ""

    for ln in orig_lines:
        md = SECTION_RE_DUNGEON.match(ln)
        if md:
            cur  = md.group(1).strip()
            indent = ""
            new_lines.append(ln)
            continue

        if cur and not indent and ln.strip():
            indent = ln[: len(ln) - len(ln.lstrip())]

        if cur and ADD_LINE_SUFFIX in ln and cur in dmap:
            new_lines.append(build_add_line(cur, dmap[cur], indent))
            cur = None
        else:
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

BTN_W       = 26                     # uniform “pill” width
CLR_ORANGE  = "#eb8600"
CLR_PURPLE  = "#714cff"

class ScrollPane(ttkb.Frame):
    """
    Re-usable scroll-canvas that hosts arbitrary widgets.
    """
    def __init__(self, master, width=260, **kw):
        super().__init__(master, **kw)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=master.master.style.colors.dark,
                                highlightthickness=0, width=width)
        self.inner  = ttkb.Frame(self.canvas)
        self.scr_y  = ttkb.Scrollbar(self, orient="vertical",
                                     command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scr_y.set)
        self.win_id = self.canvas.create_window((0,0), window=self.inner,
                                                anchor="nw")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scr_y.grid(row=0, column=1, sticky="ns")

        self.inner.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self.win_id,
                                                             width=e.width))

    def _sync(self, *_):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # expose a convenience mouse-wheel binder
    def bind_wheel(self):
        sys_plat = platform.system()
        if sys_plat == "Windows":
            self.canvas.bind("<Enter>",
                lambda *_: self.canvas.bind_all("<MouseWheel>",
                    lambda e: self.canvas.yview_scroll(int(-e.delta/120), "units")))
            self.canvas.bind("<Leave>",
                lambda *_: self.canvas.unbind_all("<MouseWheel>"))
        elif sys_plat == "Darwin":
            self.canvas.bind("<Enter>",
                lambda *_: self.canvas.bind_all("<MouseWheel>",
                    lambda e: self.canvas.yview_scroll(int(-e.delta), "units")))
            self.canvas.bind("<Leave>",
                lambda *_: self.canvas.unbind_all("<MouseWheel>"))
        else:  # X11
            self.canvas.bind("<Enter>", self._linux_on)
            self.canvas.bind("<Leave>", self._linux_off)

    def _linux_on(self, *_):
        self.canvas.bind_all("<Button-4>",
            lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>",
            lambda e: self.canvas.yview_scroll( 1, "units"))

    def _linux_off(self, *_):
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

# -----------------------------------------------------------------------------


class ConfigEditor(ttkb.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Dungeon ⇄ Moon Config Editor")
        self.geometry("1480x800")
        self.minsize(1180, 640)
        self.style.configure(".", font=(FONT_FAMILY, FONT_SIZE))

        # ── CUSTOM STYLES ────────────────────────────────────────────
        self._create_custom_styles()
        # ─────────────────────────────────────────────────────────────

        # Data
        self.cfg_path = None
        self.lines    = []
        self.dmap     = OrderedDict()
        self.moons    = OrderedDict()
        self.mode     = tk.StringVar(value="moon")     # moon or dungeon

        # Layout
        self._build_menu()
        self._build_layout()
        self.bind_all("<F2>", lambda *_: self._toggle_mode())

    # ---------- register orange/purple button styles ----------
    def _create_custom_styles(self):
        s = self.style

        # solid pills (selected)
        s.configure("MoonSolid.TButton",
                    background=CLR_ORANGE, foreground="white",
                    bordercolor=CLR_ORANGE, relief="flat")
        s.configure("DungeonSolid.TButton",
                    background=CLR_PURPLE, foreground="white",
                    bordercolor=CLR_PURPLE, relief="flat")

        # outline pills (un-selected)
        s.configure("MoonOutline.TButton",
                    foreground=CLR_ORANGE, bordercolor=CLR_ORANGE,
                    background=s.colors.bg, relief="ridge")
        s.configure("DungeonOutline.TButton",
                    foreground=CLR_PURPLE, bordercolor=CLR_PURPLE,
                    background=s.colors.bg, relief="ridge")

        # middle-list pills never go solid, just orange ↔ purple outlines
        s.configure("MidMoon.TButton",
                    foreground=CLR_PURPLE, bordercolor=CLR_PURPLE,
                    background=s.colors.bg, relief="ridge")
        s.configure("MidDungeon.TButton",
                    foreground=CLR_ORANGE, bordercolor=CLR_ORANGE,
                    background=s.colors.bg, relief="ridge")

    # ---------------------- Menu
    def _build_menu(self):
        mb = tk.Menu(self)
        fm = tk.Menu(mb, tearoff=False)
        fm.add_command(label="Open…",  accelerator="Ctrl+O", command=self.open_cfg)
        fm.add_command(label="Save As…", accelerator="Ctrl+S", command=self.save_cfg)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.destroy)
        mb.add_cascade(label="File", menu=fm)
        self.config(menu=mb)
        self.bind_all("<Control-o>", lambda *_: self.open_cfg())
        self.bind_all("<Control-s>", lambda *_: self.save_cfg())

    # ---------------------- Layout
    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(0, weight=1)

        # LEFT ─ primary list
        left = ttkb.Frame(self, padding=6)
        left.grid(row=0, column=0, sticky="nsw")
        left.rowconfigure(2, weight=1)

        # radio row
        rbbox = ttkb.Frame(left)
        rbbox.grid(row=0, column=0, sticky="w", columnspan=2)
        for txt, val in [("Moon → Dungeons", "moon"), ("Dungeon → Moons", "dungeon")]:
            ttkb.Radiobutton(rbbox, text=txt, variable=self.mode, value=val,
                             command=self._rebuild_primary).pack(side="left")
        ttkb.Label(rbbox, text=" (F2 toggles)").pack(side="left", padx=4)

        # primary scroll-pane (buttons)
        self.prime_pane = ScrollPane(left, width=260)
        self.prime_pane.grid(row=2, column=0, sticky="nsw")
        self.prime_pane.bind_wheel()

        # MIDDLE ─ relation list (shifted down 30 px)
        mid = ttkb.Frame(self, padding=(6, 36, 6, 6))   # top padding +30
        mid.grid(row=0, column=1, sticky="nsew")
        mid.columnconfigure(0, weight=1); mid.rowconfigure(0, weight=1)
        self.relate_pane = ScrollPane(mid)
        self.relate_pane.grid(row=0, column=0, sticky="nsew")
        self.relate_pane.bind_wheel()

        # RIGHT ─ summary
        self.summary = ttkb.Frame(self, padding=(0, 6, 12, 6))
        self.summary.grid(row=0, column=2, sticky="nsew")
        self.summary.columnconfigure(0, weight=1)
        self._build_summary()

        # bottom save
        self.save_btn = ttkb.Button(self, text="Save All Changes",
                                    bootstyle=SUCCESS, command=self.save_cfg,
                                    state=DISABLED)
        self.save_btn.grid(row=1, column=2, pady=6, padx=12, sticky="e")

    # ---------- build the right-hand summary (header + empty body) ----------
    def _build_summary(self):
        ttkb.Label(self.summary, text="Active dungeons on this moon",
                   bootstyle="inverse").grid(row=0, column=0, sticky="w")

        header = ttkb.Frame(self.summary)
        header.grid(row=1, column=0, sticky="ew", pady=(2,0))
        for c, txt, w in [(0,"Dungeon",26), (1,"Weight",7), (2,"% of total",10)]:
            lbl = ttkb.Label(header, text=txt, anchor="center",
                 width=w, bootstyle=("secondary", "inverse"))
            lbl.grid(row=0, column=c, sticky="ew", padx=1)

        # body – we’ll (re)populate it every time a moon is selected
        self.sum_body = ttkb.Frame(self.summary, borderwidth=1, relief="solid")
        self.sum_body.grid(row=2, column=0, sticky="nsew")
        self.summary.rowconfigure(2, weight=1)

    # ---------------------- Helpers
    def _hex_interp(self, c1, c2, t):
        """Linear interpolate two hex colours; t∈[0,1]."""
        h1 = tuple(int(c1[i:i+2],16) for i in (1,3,5))
        h2 = tuple(int(c2[i:i+2],16) for i in (1,3,5))
        mix = tuple(int(a+(b-a)*t) for a,b in zip(h1,h2))
        return f"#{mix[0]:02x}{mix[1]:02x}{mix[2]:02x}"

    # ---------------------- Primary rebuild
    def _rebuild_primary(self):
        for w in self.prime_pane.inner.winfo_children():
            w.destroy()

        outline_style = "MoonOutline.TButton"  if self.mode.get()=="moon" else "DungeonOutline.TButton"
        items = (m for m,r in self.moons.items() if r) if self.mode.get()=="moon" \
                else self.dmap.keys()

        for i,key in enumerate(items):
            btn = ttkb.Button(self.prime_pane.inner, text=key, width=BTN_W,
                              style=outline_style)
            btn.grid(row=i, column=0, pady=2, sticky="w")
            btn.bind("<Button-1>", lambda e,k=key: self._select_primary(k))

        self.prime_pane._sync()
        # Clear secondary + summary
        self._populate_secondary(None)
        self._refresh_summary(None)

    def _select_primary(self, key):
        self.selected_primary = key
        self._highlight_primary()
        self._populate_secondary(key)
        if self.mode.get()=="moon": self._refresh_summary(key)
        else:                        self._refresh_summary(None)

    # ─────────────────── highlight selected pill ───────────────────
    def _highlight_primary(self):
        solid   = "MoonSolid.TButton"    if self.mode.get()=="moon" else "DungeonSolid.TButton"
        outline = "MoonOutline.TButton"  if self.mode.get()=="moon" else "DungeonOutline.TButton"
        sel     = getattr(self, "selected_primary", None)

        for b in self.prime_pane.inner.winfo_children():
            if not isinstance(b, ttkb.Button):
                continue
            b.configure(style=solid if b.cget("text") == sel else outline)


    # ---------------------- Secondary list
    def _populate_secondary(self, sel):
        for w in self.relate_pane.inner.winfo_children():
            w.destroy()

        if not sel:
            self.relate_pane._sync(); return

        style_mid = "MidMoon.TButton" if self.mode.get()=="moon" else "MidDungeon.TButton"

        if self.mode.get()=="moon":
            items = [(d, self.dmap[d].get(sel,"")) for d in self.dmap]
        else:
            items = [(m, self.dmap[sel].get(m,"")) for m,r in self.moons.items() if r]

        for r,(name,wgt) in enumerate(items):
            present = bool(wgt)

            # middle-pane pills
            btn = ttkb.Button(self.relate_pane.inner, text=name, width=BTN_W,
                              style=style_mid)
            btn.grid(row=r, column=0, sticky="w", padx=(0,4), pady=2)

            var = tk.StringVar(value=str(wgt) if present else "")
            ent = ttkb.Entry(self.relate_pane.inner, textvariable=var, width=8)
            ent.grid(row=r, column=1, padx=4)

            def _add_upd(k=name, v=var): self._add_update(sel,k,v)
            def _rmv(k=name):            self._remove(sel,k)

            if present:
                ttkb.Button(self.relate_pane.inner, text="Update",
                            command=_add_upd,
                            bootstyle=(INFO, OUTLINE, ROUND)
                            ).grid(row=r, column=2, padx=2)
                ttkb.Button(self.relate_pane.inner, text="Remove",
                            command=_rmv,
                            bootstyle=(DANGER, OUTLINE, ROUND)
                            ).grid(row=r, column=3, padx=2)
            else:
                ttkb.Button(self.relate_pane.inner, text="Add",
                            command=_add_upd,
                            bootstyle=(SUCCESS, OUTLINE, ROUND)
                            ).grid(row=r, column=2, padx=2)

        self.relate_pane._sync()

    # ---------------------- Data mutators
    def _add_update(self, primary, secondary, var):
        w = var.get().strip()
        if not w.isdigit() or int(w)<=0:
            messagebox.showerror("Weight error","Weight must be a positive integer")
            return
        if self.mode.get()=="moon":
            self.dmap[secondary][primary] = w
        else:
            self.dmap[primary][secondary] = w
        self._select_primary(primary)

    def _remove(self, primary, secondary):
        if self.mode.get()=="moon":
            self.dmap[secondary].pop(primary, None)
        else:
            self.dmap[primary].pop(secondary, None)
        self._select_primary(primary)

    # ---------- refresh the summary body, colour only the % label ----------
    def _refresh_summary(self, moon):
        for w in self.sum_body.winfo_children():
            w.destroy()

        if not moon:
            return

        rows = [(d, int(w)) for d, mm in self.dmap.items() if moon in mm
                for m, w in mm.items() if m == moon]
        rows.sort(key=lambda x: -x[1])

        total   = sum(w for _, w in rows) or 1
        max_pct = rows[0][1] / total if rows else 1

        for r, (d, w) in enumerate(rows):
            pct       = w / total
            pct_text  = f"{pct*100:4.1f}%"
            t         = pct / max_pct if max_pct else 0
            fg_color  = self._hex_interp("#d91a1a",
                          self._hex_interp("#ffee55", "#1abe26", t), t)

            ttkb.Label(self.sum_body, text=d,  anchor="w", width=26
                       ).grid(row=r, column=0, sticky="w", padx=1)
            ttkb.Label(self.sum_body, text=w,  anchor="center", width=7
                       ).grid(row=r, column=1, sticky="e", padx=1)
            ttkb.Label(self.sum_body, text=pct_text, anchor="center", width=10,
                       foreground=fg_color
                       ).grid(row=r, column=2, sticky="e", padx=1)



    # ---------------------- File I/O
    def open_cfg(self):
        p = filedialog.askopenfilename(filetypes=[("Config files","*.cfg"),
                                                  ("All files","*.*")])
        if not p: return
        try:
            self.dmap, self.moons, self.lines = parse_cfg(p)
        except Exception as e:
            messagebox.showerror("Parse error",str(e)); return
        self.cfg_path = p
        self.save_btn["state"] = NORMAL
        self._rebuild_primary()
        self.title(f"Dungeon ⇄ Moon Config Editor — {os.path.basename(p)}")

    def save_cfg(self, *_):
        if not self.cfg_path: return
        out = filedialog.asksaveasfilename(defaultextension=".cfg",
            filetypes=[("Config files","*.cfg"),("All files","*.*")])
        if not out: return
        try:
            write_cfg(self.lines, self.dmap, out)
            messagebox.showinfo("Saved",f"Wrote {out}")
        except Exception as e:
            messagebox.showerror("Write error",str(e))

    # ---------------------- Toggle
    def _toggle_mode(self):
        self.mode.set("dungeon" if self.mode.get()=="moon" else "moon")
        self._rebuild_primary()

###############################################################################
# MAIN
###############################################################################
def main():
    app = ConfigEditor()
    app.mainloop()

if __name__ == "__main__":
    main()
