"""
Mangadeck — Tkinter GUI
Minimalist, dark theme, JetBrains Mono, blue accents.
Controls all features: search, download, cart, queue, settings.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Dict, List, Optional


class MangadeckGUI:
    """Tkinter-based GUI for Mangadeck."""

    # ── Color palette ──
    BG_0 = "#0e1015"
    BG_1 = "#15171e"
    BG_2 = "#1b1e27"
    BG_3 = "#222630"
    BORDER = "#2a2f3c"
    TEXT_0 = "#e8eaf0"
    TEXT_1 = "#b0b8c8"
    TEXT_2 = "#7a8498"
    ACCENT = "#4a8fe7"
    ACCENT_DIM = "#3a6fb8"
    GREEN = "#4caf50"
    RED = "#e74c4c"
    ORANGE = "#e7974a"

    FONT_MONO = ("JetBrains Mono", 10)
    FONT_MONO_SM = ("JetBrains Mono", 9)
    FONT_MONO_XS = ("JetBrains Mono", 8)
    FONT_TITLE = ("Georgia", 18, "bold")
    FONT_HEADING = ("Georgia", 13, "bold")
    FONT_BODY = ("Georgia", 10)

    def __init__(self, ctx: Dict):
        self.ctx = ctx
        self.config = ctx["config"]
        self.logger = ctx["logger"]
        self.aggregator = ctx["aggregator"]
        self.queue_manager = ctx["queue_manager"]
        self.download_engine = ctx["download_engine"]

        self.queue_manager.set_download_engine(self.download_engine)

        self.root = None
        self.search_results = []
        self.cart_items = []
        self._poll_id = None

    def run(self):
        self.root = tk.Tk()
        self.root.title("Mangadeck")
        self.root.geometry("1080x720")
        self.root.minsize(800, 520)
        self.root.configure(bg=self.BG_0)

        self._configure_styles()
        self._build_ui()
        self._start_polling()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    # ────────────────────── Styles ──────────────────────

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=self.BG_0, foreground=self.TEXT_0,
                         font=self.FONT_MONO_SM, borderwidth=0)
        style.configure("TFrame", background=self.BG_0)
        style.configure("Card.TFrame", background=self.BG_1)
        style.configure("TLabel", background=self.BG_0, foreground=self.TEXT_0,
                         font=self.FONT_BODY)
        style.configure("Heading.TLabel", font=self.FONT_HEADING,
                         foreground=self.TEXT_0, background=self.BG_0)
        style.configure("Title.TLabel", font=self.FONT_TITLE,
                         foreground=self.ACCENT, background=self.BG_0)
        style.configure("Sub.TLabel", foreground=self.TEXT_2,
                         font=self.FONT_MONO_XS, background=self.BG_0)
        style.configure("Accent.TLabel", foreground=self.ACCENT,
                         font=self.FONT_MONO_SM, background=self.BG_0)

        style.configure("TNotebook", background=self.BG_0, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.BG_2,
                         foreground=self.TEXT_2, font=self.FONT_MONO_SM,
                         padding=[14, 6])
        style.map("TNotebook.Tab",
                   background=[("selected", self.BG_1)],
                   foreground=[("selected", self.ACCENT)])

        style.configure("TEntry", fieldbackground=self.BG_2,
                         foreground=self.TEXT_0, insertcolor=self.TEXT_0,
                         borderwidth=1, font=self.FONT_MONO_SM)

        style.configure("TButton", background=self.BG_2, foreground=self.TEXT_0,
                         font=self.FONT_MONO_SM, borderwidth=1, padding=[10, 4])
        style.map("TButton",
                   background=[("active", self.BG_3), ("pressed", self.ACCENT_DIM)],
                   foreground=[("active", self.TEXT_0)])

        style.configure("Accent.TButton", background=self.ACCENT,
                         foreground="#fff", font=self.FONT_MONO_SM)
        style.map("Accent.TButton",
                   background=[("active", self.ACCENT_DIM)])

        style.configure("TCombobox", fieldbackground=self.BG_2,
                         foreground=self.TEXT_0, background=self.BG_2,
                         font=self.FONT_MONO_SM)
        style.map("TCombobox",
                   fieldbackground=[("readonly", self.BG_2)],
                   foreground=[("readonly", self.TEXT_0)])

        style.configure("Horizontal.TProgressbar",
                         background=self.ACCENT, troughcolor=self.BG_3,
                         borderwidth=0, thickness=6)

        style.configure("Treeview", background=self.BG_1,
                         foreground=self.TEXT_0, fieldbackground=self.BG_1,
                         font=self.FONT_MONO_XS, rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=self.BG_2,
                         foreground=self.TEXT_2, font=self.FONT_MONO_XS)
        style.map("Treeview",
                   background=[("selected", self.BG_3)],
                   foreground=[("selected", self.ACCENT)])

        style.configure("TCheckbutton", background=self.BG_0,
                         foreground=self.TEXT_0, font=self.FONT_MONO_SM)
        style.map("TCheckbutton",
                   background=[("active", self.BG_0)])

        style.configure("TSpinbox", fieldbackground=self.BG_2,
                         foreground=self.TEXT_0, font=self.FONT_MONO_SM)

    # ────────────────────── Layout ──────────────────────

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=20, pady=(16, 4))
        ttk.Label(header, text="Mangadeck", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"v{self.ctx['version']}",
                   style="Sub.TLabel").pack(side=tk.LEFT, padx=(8, 0), pady=(8, 0))

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        self._build_search_tab()
        self._build_downloads_tab()
        self._build_cart_tab()
        self._build_settings_tab()
        self._build_logs_tab()

    # ── Search tab ──

    def _build_search_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  Search  ")

        # Top bar
        bar = ttk.Frame(frame)
        bar.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.search_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.search_var, width=40)
        entry.pack(side=tk.LEFT, padx=(0, 6))
        entry.bind("<Return>", lambda e: self._do_search())

        self.lang_var = tk.StringVar(value="en")
        lang_cb = ttk.Combobox(bar, textvariable=self.lang_var, width=5,
                                values=["en", "ja", "ko", "zh", "fr", "es", "de"],
                                state="readonly")
        lang_cb.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(bar, text="Search", style="Accent.TButton",
                    command=self._do_search).pack(side=tk.LEFT)

        # Format selector
        ttk.Label(bar, text="Format:", style="Sub.TLabel").pack(side=tk.LEFT, padx=(16, 4))
        self.format_var = tk.StringVar(value=self.config.get("default_format", "cbz"))
        fmt_cb = ttk.Combobox(bar, textvariable=self.format_var, width=7,
                               values=["cbz", "epub", "pdf", "images"],
                               state="readonly")
        fmt_cb.pack(side=tk.LEFT)

        # Results tree
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        cols = ("title", "type", "status", "sources", "chapters")
        self.search_tree = ttk.Treeview(tree_frame, columns=cols,
                                         show="headings", selectmode="extended")
        self.search_tree.heading("title", text="Title")
        self.search_tree.heading("type", text="Type")
        self.search_tree.heading("status", text="Status")
        self.search_tree.heading("sources", text="Sources")
        self.search_tree.heading("chapters", text="Chapters")

        self.search_tree.column("title", width=340, minwidth=200)
        self.search_tree.column("type", width=70, minwidth=50)
        self.search_tree.column("status", width=80, minwidth=60)
        self.search_tree.column("sources", width=160, minwidth=100)
        self.search_tree.column("chapters", width=70, minwidth=50)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                   command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=scrollbar.set)
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Actions
        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, padx=16, pady=(0, 12))

        # Chapter/volume range
        ttk.Label(actions, text="Chapters:", style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.ch_range_var = tk.StringVar()
        ttk.Entry(actions, textvariable=self.ch_range_var, width=12).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(actions, text="Volumes:", style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.vol_range_var = tk.StringVar()
        ttk.Entry(actions, textvariable=self.vol_range_var, width=8).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(actions, text="Download selected", style="Accent.TButton",
                    command=self._download_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="Add to cart",
                    command=self._add_selected_to_cart).pack(side=tk.LEFT, padx=(0, 6))

        self.search_status = tk.StringVar(value="Enter a search query")
        ttk.Label(actions, textvariable=self.search_status,
                   style="Sub.TLabel").pack(side=tk.RIGHT)

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query:
            return

        self.search_status.set("Searching...")
        self.search_tree.delete(*self.search_tree.get_children())
        self.search_results = []

        def _run():
            try:
                results = self.aggregator.search(
                    query, self.lang_var.get(), 1
                )
                self.search_results = results
                self.root.after(0, lambda: self._populate_search(results))
            except Exception as e:
                self.root.after(0, lambda: self.search_status.set(f"Error: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _populate_search(self, results):
        self.search_tree.delete(*self.search_tree.get_children())
        if not results:
            self.search_status.set("No results found")
            return

        for i, r in enumerate(results):
            sources = ", ".join(r.get("sources", [r.get("source", "")]))
            ch_count = r.get("chapter_count", "?") or "?"
            self.search_tree.insert("", tk.END, iid=str(i), values=(
                r.get("title", ""),
                r.get("type", "manga"),
                r.get("status", "unknown"),
                sources,
                ch_count,
            ))
        self.search_status.set(f"{len(results)} results")

    def _get_selected_manga(self) -> List[Dict]:
        selected = self.search_tree.selection()
        manga_list = []
        for iid in selected:
            idx = int(iid)
            if 0 <= idx < len(self.search_results):
                manga_list.append(self.search_results[idx])
        return manga_list

    def _parse_range(self, text):
        if not text or not text.strip():
            return None
        result = []
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    for i in range(int(a), int(b) + 1):
                        result.append(float(i))
                except ValueError:
                    continue
            else:
                try:
                    result.append(float(part))
                except ValueError:
                    continue
        return result if result else None

    def _download_selected(self):
        manga_list = self._get_selected_manga()
        if not manga_list:
            messagebox.showinfo("Mangadeck", "Select manga from results first.")
            return

        ch_range = self._parse_range(self.ch_range_var.get())
        vol_range = self._parse_range(self.vol_range_var.get())
        fmt = self.format_var.get()

        for manga in manga_list:
            self.download_engine.download(
                manga_id=manga["id"],
                title=manga.get("title", ""),
                source=manga.get("source", ""),
                source_ids=manga.get("source_ids", {}),
                output_format=fmt,
                chapter_range=ch_range,
                volume_range=vol_range,
                language=self.lang_var.get(),
                reading_direction=manga.get("reading_direction"),
            )

        self.search_status.set(f"Started {len(manga_list)} download(s)")
        self.notebook.select(1)  # Switch to downloads tab

    def _add_selected_to_cart(self):
        manga_list = self._get_selected_manga()
        if not manga_list:
            messagebox.showinfo("Mangadeck", "Select manga from results first.")
            return

        for manga in manga_list:
            self.queue_manager.add_to_cart(
                manga_id=manga["id"],
                title=manga.get("title", ""),
                source=manga.get("source", ""),
                source_ids=manga.get("source_ids", {}),
                cover_url=manga.get("cover_url", ""),
                output_format=self.format_var.get(),
                chapter_range=self._parse_range(self.ch_range_var.get()),
                volume_range=self._parse_range(self.vol_range_var.get()),
                language=self.lang_var.get(),
                reading_direction=manga.get("reading_direction"),
            )

        self.search_status.set(f"Added {len(manga_list)} to cart")
        self._refresh_cart()

    # ── Downloads tab ──

    def _build_downloads_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  Downloads  ")

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        ttk.Label(header, text="Downloads", style="Heading.TLabel").pack(side=tk.LEFT)
        self.dl_stats_var = tk.StringVar(value="")
        ttk.Label(header, textvariable=self.dl_stats_var,
                   style="Sub.TLabel").pack(side=tk.RIGHT)
        ttk.Button(header, text="Clear done",
                    command=self._clear_downloads).pack(side=tk.RIGHT, padx=(0, 8))

        # Download list
        cols = ("title", "status", "progress", "speed", "chapter", "eta")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.dl_tree = ttk.Treeview(tree_frame, columns=cols,
                                     show="headings", selectmode="browse")
        self.dl_tree.heading("title", text="Title")
        self.dl_tree.heading("status", text="Status")
        self.dl_tree.heading("progress", text="Progress")
        self.dl_tree.heading("speed", text="Speed")
        self.dl_tree.heading("chapter", text="Current")
        self.dl_tree.heading("eta", text="ETA")

        self.dl_tree.column("title", width=280, minwidth=160)
        self.dl_tree.column("status", width=90, minwidth=70)
        self.dl_tree.column("progress", width=90, minwidth=60)
        self.dl_tree.column("speed", width=90, minwidth=60)
        self.dl_tree.column("chapter", width=120, minwidth=80)
        self.dl_tree.column("eta", width=70, minwidth=50)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                   command=self.dl_tree.yview)
        self.dl_tree.configure(yscrollcommand=scrollbar.set)
        self.dl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Cancel button
        bottom = ttk.Frame(frame)
        bottom.pack(fill=tk.X, padx=16, pady=(0, 12))
        ttk.Button(bottom, text="Cancel selected",
                    command=self._cancel_selected_dl).pack(side=tk.LEFT)

    def _refresh_downloads(self):
        tasks = self.download_engine.get_all_tasks()
        stats = self.download_engine.get_stats()

        self.dl_stats_var.set(
            f"Active: {stats.get('active', 0)}  "
            f"Complete: {stats.get('complete', 0)}  "
            f"Error: {stats.get('error', 0)}"
        )

        existing = set(self.dl_tree.get_children())
        task_ids = set()

        for t in tasks:
            tid = t.get("task_id", "")
            task_ids.add(tid)

            speed = t.get("speed_bps", 0)
            speed_str = f"{speed / 1024:.0f} KB/s" if speed > 0 else "--"

            pct = t.get("progress_percent", 0)
            progress_str = f"{pct:.0f}% ({t.get('completed_items', 0)}/{t.get('total_items', 0)})"

            eta = t.get("eta_seconds", 0)
            eta_str = f"{int(eta)}s" if eta > 0 else "--"

            values = (
                t.get("title", ""),
                t.get("status", ""),
                progress_str,
                speed_str,
                t.get("current_chapter", ""),
                eta_str,
            )

            if tid in existing:
                self.dl_tree.item(tid, values=values)
            else:
                self.dl_tree.insert("", tk.END, iid=tid, values=values)

        # Remove stale entries
        for iid in existing - task_ids:
            self.dl_tree.delete(iid)

    def _cancel_selected_dl(self):
        selected = self.dl_tree.selection()
        for tid in selected:
            self.download_engine.cancel_task(tid)

    def _clear_downloads(self):
        self.download_engine.clear_completed()
        self._refresh_downloads()

    # ── Cart tab ──

    def _build_cart_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  Cart  ")

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        ttk.Label(header, text="Cart", style="Heading.TLabel").pack(side=tk.LEFT)
        self.cart_count_var = tk.StringVar(value="0 items")
        ttk.Label(header, textvariable=self.cart_count_var,
                   style="Sub.TLabel").pack(side=tk.LEFT, padx=(12, 0))

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Download all", style="Accent.TButton",
                    command=self._download_cart).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Clear cart",
                    command=self._clear_cart).pack(side=tk.LEFT)

        # Cart list
        cols = ("title", "format", "source", "chapters")
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.cart_tree = ttk.Treeview(tree_frame, columns=cols,
                                      show="headings", selectmode="extended")
        self.cart_tree.heading("title", text="Title")
        self.cart_tree.heading("format", text="Format")
        self.cart_tree.heading("source", text="Source")
        self.cart_tree.heading("chapters", text="Chapters")

        self.cart_tree.column("title", width=320, minwidth=180)
        self.cart_tree.column("format", width=70, minwidth=50)
        self.cart_tree.column("source", width=120, minwidth=80)
        self.cart_tree.column("chapters", width=100, minwidth=60)

        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(frame)
        bottom.pack(fill=tk.X, padx=16, pady=(0, 12))
        ttk.Button(bottom, text="Remove selected",
                    command=self._remove_from_cart).pack(side=tk.LEFT)

    def _refresh_cart(self):
        items = self.queue_manager.get_cart()
        self.cart_count_var.set(f"{len(items)} items")
        self.cart_tree.delete(*self.cart_tree.get_children())

        for item in items:
            ch = item.get("chapter_range")
            ch_str = ""
            if ch:
                ch_str = f"{min(ch)}-{max(ch)}"
            self.cart_tree.insert("", tk.END, iid=item["id"], values=(
                item.get("title", ""),
                item.get("output_format", "cbz"),
                item.get("source", ""),
                ch_str or "all",
            ))

    def _remove_from_cart(self):
        selected = self.cart_tree.selection()
        for iid in selected:
            self.queue_manager.remove_from_cart(iid)
        self._refresh_cart()

    def _clear_cart(self):
        self.queue_manager.clear_cart()
        self._refresh_cart()

    def _download_cart(self):
        count = self.queue_manager.enqueue_cart()
        if count == 0:
            messagebox.showinfo("Mangadeck", "Cart is empty.")
            return
        self.queue_manager.start_processing()
        self._refresh_cart()
        self.notebook.select(1)  # Go to downloads

    # ── Settings tab ──

    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  Settings  ")

        canvas = tk.Canvas(frame, bg=self.BG_0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.setting_vars = {}

        def add_section(parent, title):
            lbl = ttk.Label(parent, text=title, style="Accent.TLabel")
            lbl.pack(anchor=tk.W, pady=(16, 6))
            sep = ttk.Separator(parent, orient=tk.HORIZONTAL)
            sep.pack(fill=tk.X, pady=(0, 8))

        def add_entry(parent, label, key, default=""):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, style="Sub.TLabel", width=28).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(self.config.get(key, default)))
            ttk.Entry(row, textvariable=var, width=30).pack(side=tk.LEFT, padx=(4, 0))
            self.setting_vars[key] = var

        def add_combo(parent, label, key, values, default=""):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, style="Sub.TLabel", width=28).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(self.config.get(key, default)))
            ttk.Combobox(row, textvariable=var, values=values,
                          state="readonly", width=14).pack(side=tk.LEFT, padx=(4, 0))
            self.setting_vars[key] = var

        def add_check(parent, label, key, default=False):
            var = tk.BooleanVar(value=self.config.get(key, default))
            ttk.Checkbutton(parent, text=label, variable=var).pack(anchor=tk.W, pady=2)
            self.setting_vars[key] = var

        def add_dir_chooser(parent, label, key):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, style="Sub.TLabel", width=28).pack(side=tk.LEFT)
            var = tk.StringVar(value=self.config.get(key, ""))
            ttk.Entry(row, textvariable=var, width=24).pack(side=tk.LEFT, padx=(4, 0))
            def browse():
                d = filedialog.askdirectory()
                if d:
                    var.set(d)
            ttk.Button(row, text="Browse", command=browse).pack(side=tk.LEFT, padx=(4, 0))
            self.setting_vars[key] = var

        # ── Sections ──
        add_section(inner, "OUTPUT")
        add_dir_chooser(inner, "Output directory", "output_dir")
        add_combo(inner, "Default format", "default_format",
                   ["cbz", "epub", "pdf", "images"], "cbz")
        add_combo(inner, "Language", "language",
                   ["en", "ja", "ko", "zh", "fr", "es", "de", "pt-br", "it", "ru"], "en")
        add_combo(inner, "Reading direction", "reading_direction",
                   ["auto", "rtl", "ltr", "vertical"], "auto")

        add_section(inner, "PERFORMANCE")
        add_entry(inner, "Concurrent downloads", "max_concurrent_downloads", "4")
        add_entry(inner, "Concurrent images", "max_concurrent_images", "8")
        add_entry(inner, "Bandwidth limit (KB/s)", "bandwidth_limit_kbps", "0")

        add_section(inner, "IMAGE PROCESSING")
        add_check(inner, "Auto-crop borders", "auto_crop", True)
        add_entry(inner, "Crop threshold", "crop_threshold", "10")
        add_entry(inner, "Min crop ratio", "crop_min_ratio", "0.70")
        add_entry(inner, "JPEG quality", "jpeg_quality", "92")

        add_section(inner, "EPUB")
        add_check(inner, "Apple Books compatibility", "epub_apple_books_compat", True)
        add_check(inner, "Generate cover page", "epub_generate_cover", True)
        add_check(inner, "Vertical mode (webtoon)", "epub_vertical_mode", False)
        add_entry(inner, "Page width (px)", "epub_page_width", "800")
        add_entry(inner, "Page height (px)", "epub_page_height", "1200")

        add_section(inner, "NOTIFICATIONS")
        add_check(inner, "Enable notifications", "notify_on_complete", False)
        add_check(inner, "Desktop notifications", "notify_desktop", False)
        add_entry(inner, "Discord webhook URL", "discord_webhook_url", "")
        add_entry(inner, "Telegram bot token", "telegram_bot_token", "")
        add_entry(inner, "Telegram chat ID", "telegram_chat_id", "")

        # Save button
        btn_frame = ttk.Frame(inner)
        btn_frame.pack(fill=tk.X, pady=(20, 8))
        ttk.Button(btn_frame, text="Save settings", style="Accent.TButton",
                    command=self._save_settings).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Reset defaults",
                    command=self._reset_settings).pack(side=tk.LEFT)

    def _save_settings(self):
        updates = {}
        int_keys = {"max_concurrent_downloads", "max_concurrent_images",
                     "bandwidth_limit_kbps", "crop_threshold", "jpeg_quality",
                     "epub_page_width", "epub_page_height"}
        float_keys = {"crop_min_ratio"}
        bool_keys = {"auto_crop", "epub_apple_books_compat", "epub_generate_cover",
                      "epub_vertical_mode", "notify_on_complete", "notify_desktop"}

        for key, var in self.setting_vars.items():
            val = var.get()
            if key in bool_keys:
                updates[key] = bool(val)
            elif key in int_keys:
                try:
                    updates[key] = int(val)
                except (ValueError, TypeError):
                    updates[key] = 0
            elif key in float_keys:
                try:
                    updates[key] = float(val)
                except (ValueError, TypeError):
                    updates[key] = 0.0
            else:
                updates[key] = str(val)

        self.config.set_many(updates)
        messagebox.showinfo("Mangadeck", "Settings saved.")

    def _reset_settings(self):
        if messagebox.askyesno("Mangadeck", "Reset all settings to defaults?"):
            self.config.reset()
            # Reload vars
            for key, var in self.setting_vars.items():
                val = self.config.get(key, "")
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(val))
                else:
                    var.set(str(val))

    # ── Logs tab ──

    def _build_logs_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="  Logs  ")

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        ttk.Label(header, text="Logs", style="Heading.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Refresh",
                    command=self._refresh_logs).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(header, text="Clear",
                    command=self._clear_logs).pack(side=tk.RIGHT)

        self.log_level_var = tk.StringVar(value="")
        ttk.Combobox(header, textvariable=self.log_level_var, width=8,
                      values=["", "DEBUG", "INFO", "WARNING", "ERROR"],
                      state="readonly").pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(header, text="Level:", style="Sub.TLabel").pack(side=tk.RIGHT, padx=(0, 4))

        self.log_text = scrolledtext.ScrolledText(
            frame, bg=self.BG_1, fg=self.TEXT_1,
            font=("JetBrains Mono", 8),
            insertbackground=self.TEXT_0,
            selectbackground=self.BG_3,
            borderwidth=0, highlightthickness=0,
            wrap=tk.WORD, state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        # Tag colors
        self.log_text.tag_configure("INFO", foreground=self.ACCENT)
        self.log_text.tag_configure("WARNING", foreground=self.ORANGE)
        self.log_text.tag_configure("ERROR", foreground=self.RED)
        self.log_text.tag_configure("DEBUG", foreground=self.TEXT_2)
        self.log_text.tag_configure("time", foreground=self.TEXT_2)

    def _refresh_logs(self):
        level = self.log_level_var.get()
        data = self.logger.get_logs(level=level or None, limit=500)
        entries = data.get("entries", [])

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)

        for entry in entries:
            ts = entry.get("timestamp", "")
            time_str = ts.split("T")[1][:8] if "T" in ts else ts[:8]
            lvl = entry.get("level", "INFO")
            msg = entry.get("message", "")

            self.log_text.insert(tk.END, f"{time_str}  ", "time")
            self.log_text.insert(tk.END, f"{lvl:<8}  ", lvl)
            self.log_text.insert(tk.END, f"{msg}\n")

        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def _clear_logs(self):
        self.logger.clear()
        self._refresh_logs()

    # ── Polling ──

    def _start_polling(self):
        self._poll_downloads()

    def _poll_downloads(self):
        try:
            self._refresh_downloads()
        except Exception:
            pass
        self._poll_id = self.root.after(2000, self._poll_downloads)

    def _on_close(self):
        if self._poll_id:
            self.root.after_cancel(self._poll_id)
        self.root.destroy()