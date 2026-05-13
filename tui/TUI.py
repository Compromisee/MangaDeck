"""
Mangadeck — Rich Terminal UI
pyfiglet shadow gradient title, gradient texts, live progress bars,
interactive search, comprehensive feature control.
"""

import os
import sys
import time
import threading
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TextColumn,
        TimeRemainingColumn, DownloadColumn, TransferSpeedColumn,
        TaskProgressColumn,
    )
    from rich.live import Live
    from rich.columns import Columns
    from rich.markdown import Markdown
    from rich.style import Style
    from rich.align import Align
    from rich import box
except ImportError:
    print("  Rich library required: pip install rich")
    sys.exit(1)

try:
    import pyfiglet
except ImportError:
    pyfiglet = None


class MangadeckTUI:
    """Rich-based terminal UI for Mangadeck."""

    # ANSI gradient blues
    GRADIENT = [
        "#1a3a5c", "#1e4a72", "#225a88", "#266a9e",
        "#2a7ab4", "#3a8ac4", "#4a9ad4", "#5aaae4",
        "#6abaef", "#7acaff",
    ]

    def __init__(self, ctx: Dict):
        self.ctx = ctx
        self.config = ctx["config"]
        self.logger = ctx["logger"]
        self.aggregator = ctx["aggregator"]
        self.queue_manager = ctx["queue_manager"]
        self.download_engine = ctx["download_engine"]

        self.queue_manager.set_download_engine(self.download_engine)

        self.console = Console()
        self.search_results = []
        self.running = True

    def run(self):
        self._show_splash()
        self._main_loop()

    # ────────────────── Splash ──────────────────

    def _show_splash(self):
        self.console.clear()

        # Figlet title with gradient
        if pyfiglet:
            fig_text = pyfiglet.figlet_format("Mangadeck", font="slant")
        else:
            fig_text = "  __  __                           _           _    \n |  \\/  | __ _ _ __   __ _  __ _  __| | ___  ___| | __\n | |\\/| |/ _` | '_ \\ / _` |/ _` |/ _` |/ _ \\/ __| |/ /\n | |  | | (_| | | | | (_| | (_| | (_| |  __/ (__|   < \n |_|  |_|\\__,_|_| |_|\\__, |\\__,_|\\__,_|\\___|\\___|_|\\_\\\n                      |___/                            "

        lines = fig_text.strip().split("\n")
        gradient_text = Text()
        for i, line in enumerate(lines):
            color_idx = int(i / max(len(lines) - 1, 1) * (len(self.GRADIENT) - 1))
            gradient_text.append(line + "\n", style=Style(color=self.GRADIENT[color_idx]))

        self.console.print()
        self.console.print(Align.center(gradient_text))

        subtitle = Text("Multi-source manga downloader", style="dim italic")
        self.console.print(Align.center(subtitle))

        version = Text(f"v{self.ctx['version']}", style="dim")
        self.console.print(Align.center(version))

        repo = Text("github.com/Compromisee/Mangadeck", style="dim blue underline")
        self.console.print(Align.center(repo))
        self.console.print()

        # Source status
        sources = self.aggregator.get_enabled_apis()
        source_text = Text()
        source_text.append("  Sources: ", style="dim")
        for i, s in enumerate(sources):
            color_idx = int(i / max(len(sources) - 1, 1) * (len(self.GRADIENT) - 1))
            source_text.append(s, style=Style(color=self.GRADIENT[color_idx]))
            if i < len(sources) - 1:
                source_text.append(" | ", style="dim")
        self.console.print(Align.center(source_text))
        self.console.print()
        time.sleep(0.5)

    # ────────────────── Main Loop ──────────────────

    def _main_loop(self):
        while self.running:
            self._show_menu()
            try:
                choice = Prompt.ask(
                    self._gradient_text(">>"),
                    choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                    default="1",
                )
            except (KeyboardInterrupt, EOFError):
                self.running = False
                break

            actions = {
                "1": self._search_interactive,
                "2": self._trending,
                "3": self._view_downloads,
                "4": self._view_cart,
                "5": self._manage_queue,
                "6": self._view_sources,
                "7": self._settings_menu,
                "8": self._view_logs,
                "9": self._quick_download,
                "0": self._quit,
            }

            action = actions.get(choice)
            if action:
                try:
                    action()
                except (KeyboardInterrupt, EOFError):
                    self.console.print("\n  [dim]Cancelled[/dim]\n")
                except Exception as e:
                    self.console.print(f"\n  [red]Error: {e}[/red]\n")

    def _show_menu(self):
        menu_items = [
            ("1", "Search manga"),
            ("2", "Trending"),
            ("3", "Downloads"),
            ("4", "Cart"),
            ("5", "Queue"),
            ("6", "Sources"),
            ("7", "Settings"),
            ("8", "Logs"),
            ("9", "Quick download"),
            ("0", "Exit"),
        ]

        table = Table(
            show_header=False, box=box.SIMPLE,
            border_style="dim blue",
            padding=(0, 2),
            expand=False,
        )
        table.add_column(style="bold blue", width=4)
        table.add_column(style="white")

        for key, label in menu_items:
            table.add_row(f"[{key}]", label)

        panel = Panel(
            table,
            title=self._gradient_text("  MENU  "),
            title_align="left",
            border_style="dim blue",
            padding=(1, 2),
        )
        self.console.print(panel)

    # ────────────────── Search ──────────────────

    def _search_interactive(self):
        self.console.print()
        query = Prompt.ask(self._gradient_text("  Search"))
        if not query.strip():
            return

        lang = Prompt.ask(
            "  [dim]Language[/dim]",
            default=self.config.get("language", "en"),
        )

        self.console.print()
        with self.console.status("[blue]Searching across all sources...[/blue]"):
            results = self.aggregator.search(query, lang, 1)

        self.search_results = results

        if not results:
            self.console.print("  [dim]No results found.[/dim]\n")
            return

        self._display_results(results)
        self._result_actions()

    def _trending(self):
        self.console.print()
        lang = Prompt.ask("  [dim]Language[/dim]", default="en")

        with self.console.status("[blue]Loading trending...[/blue]"):
            results = self.aggregator.get_trending(lang, 1)

        self.search_results = results

        if not results:
            self.console.print("  [dim]No trending manga found.[/dim]\n")
            return

        self._display_results(results)
        self._result_actions()

    def _display_results(self, results):
        table = Table(
            title=self._gradient_text(f"  {len(results)} results  "),
            box=box.SIMPLE_HEAVY,
            border_style="dim blue",
            show_lines=False,
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white bold", max_width=42)
        table.add_column("Type", style="cyan", width=8)
        table.add_column("Status", width=10)
        table.add_column("Sources", style="dim", max_width=28)
        table.add_column("Ch.", style="blue", width=5)

        for i, r in enumerate(results):
            sources = ", ".join(r.get("sources", [r.get("source", "")]))
            ch = str(r.get("chapter_count", "?") or "?")
            status = r.get("status", "unknown")
            status_color = {"ongoing": "green", "completed": "yellow"}.get(status, "dim")
            table.add_row(
                str(i + 1),
                r.get("title", "")[:42],
                r.get("type", "manga"),
                f"[{status_color}]{status}[/{status_color}]",
                sources[:28],
                ch,
            )

        self.console.print(table)
        self.console.print()

    def _result_actions(self):
        if not self.search_results:
            return

        self.console.print("  [dim]Actions: [d]ownload  [c]art  [i]nfo  [b]ack[/dim]")
        action = Prompt.ask("  [dim]Action[/dim]", default="b")

        if action.lower() == "b":
            return

        if action.lower() in ("d", "c", "i"):
            idx_str = Prompt.ask("  [dim]Select # (e.g. 1 or 1,3,5)[/dim]")
            indices = self._parse_selection(idx_str)
            if not indices:
                self.console.print("  [dim]Invalid selection.[/dim]\n")
                return

            if action.lower() == "d":
                self._download_from_results(indices)
            elif action.lower() == "c":
                self._add_to_cart_from_results(indices)
            elif action.lower() == "i":
                if indices:
                    self._show_manga_info(indices[0])

    def _parse_selection(self, text):
        result = []
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    for i in range(int(a), int(b) + 1):
                        if 1 <= i <= len(self.search_results):
                            result.append(i - 1)
                except ValueError:
                    continue
            else:
                try:
                    i = int(part) - 1
                    if 0 <= i < len(self.search_results):
                        result.append(i)
                except ValueError:
                    continue
        return result

    def _download_from_results(self, indices):
        fmt = Prompt.ask(
            "  [dim]Format[/dim]",
            choices=["cbz", "epub", "pdf", "images"],
            default=self.config.get("default_format", "cbz"),
        )

        ch_range_str = Prompt.ask("  [dim]Chapters (e.g. 1-50, blank=all)[/dim]", default="")
        vol_range_str = Prompt.ask("  [dim]Volumes (e.g. 1-5, blank=all)[/dim]", default="")
        ch_range = self._parse_range(ch_range_str)
        vol_range = self._parse_range(vol_range_str)

        for idx in indices:
            manga = self.search_results[idx]
            self.console.print(f"  [blue]Starting download:[/blue] {manga['title']}")

            task_id = self.download_engine.download(
                manga_id=manga["id"],
                title=manga.get("title", ""),
                source=manga.get("source", ""),
                source_ids=manga.get("source_ids", {}),
                output_format=fmt,
                chapter_range=ch_range,
                volume_range=vol_range,
                language=self.config.get("language", "en"),
                reading_direction=manga.get("reading_direction"),
            )

        self.console.print()
        self.console.print("  [green]Downloads started. View with option [3].[/green]\n")

    def _add_to_cart_from_results(self, indices):
        fmt = Prompt.ask(
            "  [dim]Format[/dim]",
            choices=["cbz", "epub", "pdf", "images"],
            default=self.config.get("default_format", "cbz"),
        )
        ch_str = Prompt.ask("  [dim]Chapters (blank=all)[/dim]", default="")
        ch_range = self._parse_range(ch_str)

        for idx in indices:
            manga = self.search_results[idx]
            self.queue_manager.add_to_cart(
                manga_id=manga["id"],
                title=manga.get("title", ""),
                source=manga.get("source", ""),
                source_ids=manga.get("source_ids", {}),
                cover_url=manga.get("cover_url", ""),
                output_format=fmt,
                chapter_range=ch_range,
                language=self.config.get("language", "en"),
                reading_direction=manga.get("reading_direction"),
            )
            self.console.print(f"  [green]+[/green] {manga['title']}")

        count = self.queue_manager.get_cart_count()
        self.console.print(f"\n  [dim]Cart: {count} items[/dim]\n")

    def _show_manga_info(self, idx):
        manga = self.search_results[idx]
        self.console.print()

        with self.console.status("[blue]Loading details...[/blue]"):
            details = self.aggregator.get_manga_details(
                manga["id"], manga.get("source")
            )

        if not details:
            self.console.print("  [dim]Could not load details.[/dim]\n")
            return

        info_text = Text()
        info_text.append(f"\n  {details.get('title', '')}\n", style="bold white")

        if details.get("alt_titles"):
            info_text.append(f"  {', '.join(details['alt_titles'][:3])}\n", style="dim")

        info_text.append(f"\n  Type: ", style="dim")
        info_text.append(f"{details.get('type', 'manga')}\n", style="cyan")

        info_text.append(f"  Status: ", style="dim")
        status = details.get("status", "unknown")
        scol = {"ongoing": "green", "completed": "yellow"}.get(status, "white")
        info_text.append(f"{status}\n", style=scol)

        info_text.append(f"  Direction: ", style="dim")
        info_text.append(f"{details.get('reading_direction', 'rtl')}\n", style="blue")

        if details.get("authors"):
            info_text.append(f"  Authors: ", style="dim")
            info_text.append(f"{', '.join(details['authors'])}\n", style="white")

        if details.get("genres"):
            info_text.append(f"  Genres: ", style="dim")
            info_text.append(f"{', '.join(details['genres'][:8])}\n", style="dim white")

        chapters = details.get("chapters", [])
        info_text.append(f"  Chapters: ", style="dim")
        info_text.append(f"{len(chapters)}\n", style="blue bold")

        if details.get("description"):
            desc = details["description"][:300]
            info_text.append(f"\n  {desc}\n", style="dim italic")

        sources = details.get("sources", [details.get("source", "")])
        info_text.append(f"\n  Sources: ", style="dim")
        info_text.append(f"{', '.join(sources)}\n", style="dim blue")

        panel = Panel(
            info_text,
            border_style="dim blue",
            padding=(0, 1),
        )
        self.console.print(panel)

        # Show chapter range
        if chapters:
            first = chapters[0]["chapter_number"]
            last = chapters[-1]["chapter_number"]
            self.console.print(
                f"  [dim]Chapters: {first} - {last}[/dim]\n"
            )

        # Related
        if details.get("related"):
            self.console.print("  [dim]Related:[/dim]")
            for rel in details["related"][:5]:
                self.console.print(f"    [dim]{rel.get('title', '')} ({rel.get('relation', '')})[/dim]")
            self.console.print()

    # ────────────────── Downloads ──────────────────

    def _view_downloads(self):
        self.console.print()

        tasks = self.download_engine.get_all_tasks()
        stats = self.download_engine.get_stats()

        if not tasks:
            self.console.print("  [dim]No active downloads.[/dim]\n")
            return

        # Stats bar
        stat_line = Text()
        stat_line.append("  Active: ", style="dim")
        stat_line.append(str(stats.get("active", 0)), style="blue bold")
        stat_line.append("  Complete: ", style="dim")
        stat_line.append(str(stats.get("complete", 0)), style="green bold")
        stat_line.append("  Error: ", style="dim")
        stat_line.append(str(stats.get("error", 0)), style="red bold")
        self.console.print(stat_line)
        self.console.print()

        table = Table(
            box=box.SIMPLE,
            border_style="dim blue",
            show_lines=False,
            padding=(0, 1),
        )
        table.add_column("Title", style="white", max_width=32)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=16)
        table.add_column("Speed", width=12)
        table.add_column("Current", width=16)
        table.add_column("ETA", width=8)

        for t in tasks:
            status = t.get("status", "")
            scol = {
                "downloading": "blue",
                "converting": "yellow",
                "complete": "green",
                "error": "red",
                "pending": "dim",
                "cancelled": "dim",
            }.get(status, "white")

            pct = t.get("progress_percent", 0)
            items = f"{t.get('completed_items', 0)}/{t.get('total_items', 0)}"
            progress = f"{pct:.0f}% ({items})"

            speed = t.get("speed_bps", 0)
            speed_str = f"{speed / 1024:.0f} KB/s" if speed > 0 else "--"

            eta = t.get("eta_seconds", 0)
            eta_str = f"{int(eta)}s" if eta > 0 else "--"

            # Progress bar text
            bar_len = 10
            filled = int(pct / 100 * bar_len)
            bar = "[blue]" + "=" * filled + "[/blue]" + "[dim]" + "-" * (bar_len - filled) + "[/dim]"

            table.add_row(
                t.get("title", "")[:32],
                f"[{scol}]{status}[/{scol}]",
                f"{bar} {pct:.0f}%",
                speed_str,
                t.get("current_chapter", "")[:16],
                eta_str,
            )

        self.console.print(table)
        self.console.print()

        # Live mode option
        if any(t.get("status") in ("downloading", "converting", "pending") for t in tasks):
            if Confirm.ask("  [dim]Watch live progress?[/dim]", default=False):
                self._live_progress()

    def _live_progress(self):
        """Live progress display using Rich Progress."""
        self.console.print("\n  [dim]Press Ctrl+C to stop watching.[/dim]\n")

        try:
            with Progress(
                SpinnerColumn(style="blue"),
                TextColumn("[blue]{task.fields[title]}[/blue]", justify="left"),
                BarColumn(bar_width=20, style="dim", complete_style="blue"),
                TaskProgressColumn(),
                TextColumn("[dim]{task.fields[speed]}[/dim]"),
                TextColumn("[dim]{task.fields[chapter]}[/dim]"),
                TimeRemainingColumn(),
                console=self.console,
                expand=False,
            ) as progress:
                task_map = {}

                while True:
                    tasks = self.download_engine.get_all_tasks()
                    active = [
                        t for t in tasks
                        if t.get("status") in ("downloading", "converting", "pending")
                    ]

                    if not active:
                        break

                    current_ids = set()
                    for t in active:
                        tid = t.get("task_id", "")
                        current_ids.add(tid)
                        total = max(t.get("total_items", 1), 1)
                        completed = t.get("completed_items", 0)
                        speed = t.get("speed_bps", 0)
                        speed_str = f"{speed / 1024:.0f} KB/s" if speed > 0 else ""

                        if tid not in task_map:
                            ptask = progress.add_task(
                                "", total=total,
                                title=t.get("title", "")[:28],
                                speed=speed_str,
                                chapter=t.get("current_chapter", ""),
                            )
                            task_map[tid] = ptask
                        else:
                            ptask = task_map[tid]
                            progress.update(
                                ptask, total=total, completed=completed,
                                title=t.get("title", "")[:28],
                                speed=speed_str,
                                chapter=t.get("current_chapter", ""),
                            )

                    # Remove finished from progress
                    for tid in list(task_map.keys()):
                        if tid not in current_ids:
                            progress.remove_task(task_map[tid])
                            del task_map[tid]

                    time.sleep(1)

        except KeyboardInterrupt:
            pass

        self.console.print("\n  [dim]Stopped watching.[/dim]\n")

    # ────────────────── Cart ──────────────────

    def _view_cart(self):
        self.console.print()
        items = self.queue_manager.get_cart()

        if not items:
            self.console.print("  [dim]Cart is empty.[/dim]\n")
            return

        table = Table(
            title=self._gradient_text(f"  Cart: {len(items)} items  "),
            box=box.SIMPLE,
            border_style="dim blue",
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white", max_width=36)
        table.add_column("Format", style="cyan", width=8)
        table.add_column("Source", style="dim", width=14)
        table.add_column("Chapters", style="blue", width=12)

        for i, item in enumerate(items):
            ch = item.get("chapter_range")
            ch_str = f"{min(ch)}-{max(ch)}" if ch else "all"
            table.add_row(
                str(i + 1),
                item.get("title", "")[:36],
                item.get("output_format", "cbz"),
                item.get("source", ""),
                ch_str,
            )

        self.console.print(table)
        self.console.print()

        self.console.print("  [dim][d]ownload all  [r]emove  [c]lear  [b]ack[/dim]")
        action = Prompt.ask("  [dim]Action[/dim]", default="b")

        if action.lower() == "d":
            count = self.queue_manager.enqueue_cart()
            self.queue_manager.start_processing()
            self.console.print(f"  [green]Started {count} downloads.[/green]\n")
        elif action.lower() == "r":
            idx = Prompt.ask("  [dim]Remove # [/dim]", default="")
            try:
                i = int(idx) - 1
                if 0 <= i < len(items):
                    self.queue_manager.remove_from_cart(items[i]["id"])
                    self.console.print("  [dim]Removed.[/dim]\n")
            except (ValueError, IndexError):
                pass
        elif action.lower() == "c":
            self.queue_manager.clear_cart()
            self.console.print("  [dim]Cart cleared.[/dim]\n")

    # ────────────────── Queue ──────────────────

    def _manage_queue(self):
        self.console.print()
        stats = self.queue_manager.get_stats()

        stat_line = Text()
        stat_line.append("  Queued: ", style="dim")
        stat_line.append(str(stats.get("queue_count", 0)), style="blue")
        stat_line.append("  Active: ", style="dim")
        stat_line.append(str(stats.get("active_count", 0)), style="yellow")
        stat_line.append("  Done: ", style="dim")
        stat_line.append(str(stats.get("completed", 0)), style="green")
        stat_line.append("  Failed: ", style="dim")
        stat_line.append(str(stats.get("failed", 0)), style="red")
        stat_line.append("  Processing: ", style="dim")
        stat_line.append(
            "yes" if stats.get("is_processing") else "no",
            style="green" if stats.get("is_processing") else "dim",
        )
        self.console.print(stat_line)
        self.console.print()

        items = self.queue_manager.get_queue()
        if items:
            table = Table(box=box.SIMPLE, border_style="dim blue", padding=(0, 1))
            table.add_column("#", width=4, style="dim")
            table.add_column("Title", max_width=36, style="white")
            table.add_column("Status", width=10)

            for i, item in enumerate(items):
                status = item.get("status", "queued")
                scol = {
                    "queued": "dim", "active": "blue",
                    "complete": "green", "error": "red",
                }.get(status, "white")
                table.add_row(
                    str(i + 1),
                    item.get("title", "")[:36],
                    f"[{scol}]{status}[/{scol}]",
                )
            self.console.print(table)
        else:
            self.console.print("  [dim]Queue is empty.[/dim]")

        self.console.print()
        self.console.print("  [dim][s]tart  [p]ause  [c]lear  [b]ack[/dim]")
        action = Prompt.ask("  [dim]Action[/dim]", default="b")

        if action.lower() == "s":
            self.queue_manager.start_processing()
            self.console.print("  [green]Queue started.[/green]\n")
        elif action.lower() == "p":
            self.queue_manager.stop_processing()
            self.console.print("  [yellow]Queue paused.[/yellow]\n")
        elif action.lower() == "c":
            self.queue_manager.clear_queue()
            self.console.print("  [dim]Queue cleared.[/dim]\n")

    # ────────────────── Sources ──────────────────

    def _view_sources(self):
        self.console.print()
        sources = self.aggregator.get_api_info()

        table = Table(
            title=self._gradient_text("  Sources  "),
            box=box.SIMPLE,
            border_style="dim blue",
            padding=(0, 1),
        )
        table.add_column("Name", style="blue bold", width=16)
        table.add_column("Enabled", width=8)
        table.add_column("Types", width=22)
        table.add_column("Rate", width=6, style="dim")
        table.add_column("Status", width=10)

        for s in sources:
            types = []
            if s.get("supports_manga"):
                types.append("manga")
            if s.get("supports_manhwa"):
                types.append("manhwa")
            if s.get("supports_manhua"):
                types.append("manhua")

            avail = s.get("available")
            status = "[dim]?[/dim]"
            if avail is True:
                status = "[green]online[/green]"
            elif avail is False:
                status = "[red]offline[/red]"

            table.add_row(
                s["name"],
                "[green]yes[/green]" if s.get("enabled") else "[dim]no[/dim]",
                ", ".join(types),
                f"{s.get('rate_limit', 0)}s",
                status,
            )

        self.console.print(table)
        self.console.print()

        if Confirm.ask("  [dim]Check availability?[/dim]", default=False):
            with self.console.status("[blue]Checking sources...[/blue]"):
                avail = self.aggregator.check_availability()
            for name, up in avail.items():
                icon = "[green]online[/green]" if up else "[red]offline[/red]"
                self.console.print(f"  {name}: {icon}")
            self.console.print()

    # ────────────────── Settings ──────────────────

    def _settings_menu(self):
        self.console.print()
        cfg = self.config.get_all()

        settings_display = [
            ("output_dir", "Output directory"),
            ("default_format", "Default format"),
            ("language", "Language"),
            ("reading_direction", "Reading direction"),
            ("max_concurrent_downloads", "Concurrent downloads"),
            ("max_concurrent_images", "Concurrent images"),
            ("bandwidth_limit_kbps", "Bandwidth limit (KB/s)"),
            ("auto_crop", "Auto-crop"),
            ("crop_min_ratio", "Min crop ratio"),
            ("jpeg_quality", "JPEG quality"),
            ("epub_apple_books_compat", "Apple Books compat"),
            ("epub_vertical_mode", "Vertical mode"),
            ("notify_on_complete", "Notifications"),
        ]

        table = Table(
            title=self._gradient_text("  Settings  "),
            box=box.SIMPLE,
            border_style="dim blue",
            padding=(0, 1),
        )
        table.add_column("#", width=4, style="dim")
        table.add_column("Setting", style="white", width=26)
        table.add_column("Value", style="blue")

        for i, (key, label) in enumerate(settings_display):
            val = cfg.get(key, "")
            table.add_row(str(i + 1), label, str(val))

        self.console.print(table)
        self.console.print()

        self.console.print("  [dim]Enter setting # to change, or [b]ack[/dim]")
        choice = Prompt.ask("  [dim]Setting[/dim]", default="b")

        if choice.lower() == "b":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(settings_display):
                key, label = settings_display[idx]
                current = cfg.get(key, "")
                self.console.print(f"  [dim]Current: {current}[/dim]")
                new_val = Prompt.ask(f"  [dim]New value for {label}[/dim]")

                # Type coercion
                if isinstance(current, bool):
                    self.config.set(key, new_val.lower() in ("true", "1", "yes"))
                elif isinstance(current, int):
                    self.config.set(key, int(new_val))
                elif isinstance(current, float):
                    self.config.set(key, float(new_val))
                else:
                    self.config.set(key, new_val)

                self.console.print(f"  [green]Updated {label}.[/green]\n")
        except (ValueError, IndexError):
            self.console.print("  [dim]Invalid selection.[/dim]\n")

    # ────────────────── Logs ──────────────────

    def _view_logs(self):
        self.console.print()
        data = self.logger.get_logs(limit=50)
        entries = data.get("entries", [])
        stats = self.logger.get_stats()

        stat_line = Text()
        stat_line.append("  Total: ", style="dim")
        stat_line.append(str(stats.get("total", 0)), style="blue")
        counts = stats.get("counts", {})
        stat_line.append(f"  Info: {counts.get('info', 0)}", style="blue")
        stat_line.append(f"  Warn: {counts.get('warning', 0)}", style="yellow")
        stat_line.append(f"  Error: {counts.get('error', 0)}", style="red")
        self.console.print(stat_line)
        self.console.print()

        for entry in entries[-30:]:
            ts = entry.get("timestamp", "")
            time_str = ts.split("T")[1][:8] if "T" in ts else ""
            lvl = entry.get("level", "INFO")
            msg = entry.get("message", "")

            lcol = {
                "INFO": "blue", "WARNING": "yellow",
                "ERROR": "red", "DEBUG": "dim",
            }.get(lvl, "white")

            self.console.print(
                f"  [dim]{time_str}[/dim]  [{lcol}]{lvl:<8}[/{lcol}]  {msg}"
            )

        self.console.print()

    # ────────────────── Quick Download ──────────────────

    def _quick_download(self):
        self.console.print()
        query = Prompt.ask(self._gradient_text("  Title"))
        if not query.strip():
            return

        with self.console.status("[blue]Searching...[/blue]"):
            results = self.aggregator.search(
                query, self.config.get("language", "en"), 1
            )

        if not results:
            self.console.print("  [dim]No results.[/dim]\n")
            return

        # Take first result
        manga = results[0]
        self.console.print(f"  [blue]Found:[/blue] {manga['title']}")
        self.console.print(
            f"  [dim]Sources: {', '.join(manga.get('sources', [manga.get('source', '')]))}[/dim]"
        )

        fmt = Prompt.ask(
            "  [dim]Format[/dim]",
            choices=["cbz", "epub", "pdf", "images"],
            default=self.config.get("default_format", "cbz"),
        )

        if not Confirm.ask("  [dim]Download?[/dim]", default=True):
            return

        task_id = self.download_engine.download(
            manga_id=manga["id"],
            title=manga.get("title", ""),
            source=manga.get("source", ""),
            source_ids=manga.get("source_ids", {}),
            output_format=fmt,
            language=self.config.get("language", "en"),
            reading_direction=manga.get("reading_direction"),
        )

        self.console.print(f"  [green]Download started.[/green]\n")
        self._live_progress()

    # ────────────────── Helpers ──────────────────

    def _gradient_text(self, text):
        """Create a Rich Text with blue gradient."""
        t = Text()
        for i, ch in enumerate(text):
            idx = int(i / max(len(text) - 1, 1) * (len(self.GRADIENT) - 1))
            t.append(ch, style=Style(color=self.GRADIENT[idx], bold=True))
        return t

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

    def _quit(self):
        self.running = False
        self.console.print("\n  [dim]Goodbye.[/dim]\n")