"""
Steganography Image Tool — GUI
A sleek, dark-themed tkinter application for hiding and revealing secret messages in images.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter
except ImportError:
    messagebox.showerror(
        "Missing Dependency",
        "Pillow is not installed.\nRun:  pip install Pillow",
    )
    sys.exit(1)

from steganography import encode_message, decode_message, image_capacity


# ──────────────────────────────────────────────────────────────────────────────
# Color Palette
# ──────────────────────────────────────────────────────────────────────────────
BG_DARK   = "#0D0F14"
BG_PANEL  = "#13161D"
BG_CARD   = "#1A1E2A"
BG_INPUT  = "#1F2433"
ACCENT    = "#7C5CFC"
ACCENT2   = "#00D4FF"
SUCCESS   = "#00E676"
ERROR     = "#FF5252"
WARNING   = "#FFD740"
TEXT_PRI  = "#EAEEF8"
TEXT_SEC  = "#8892A4"
TEXT_MUT  = "#4A5265"
BORDER    = "#252A38"
HOVER_CARD= "#22283A"


# ──────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ──────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _gradient_image(width: int, height: int, color1: str, color2: str) -> Image.Image:
    """Create a horizontal gradient PIL image."""
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for x in range(width):
        t = x / max(width - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))
    return img


def _blend(c1: str, c2: str, t: float = 0.5) -> str:
    """Blend two hex colours by factor t (0=c1, 1=c2)."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class GradientButton(tk.Frame):
    """
    A styled button implemented as a tk.Frame + tk.Label.
    Avoids tk.Canvas subclassing, which breaks on Python 3.14.
    Hover effect blends between c1 and c2 to simulate a gradient shift.
    """

    def __init__(self, parent, text, command, c1=ACCENT, c2=ACCENT2,
                 width=180, height=42, font_size=11, **kwargs):
        # Use midpoint of the two colours as the normal background
        self._c1, self._c2 = c1, c2
        self._bg_normal = _blend(c1, c2, 0.4)
        self._bg_hover  = _blend(c1, c2, 0.65)
        self._command   = command

        super().__init__(parent, bg=self._bg_normal,
                         width=width, height=height,
                         cursor="hand2", **kwargs)
        self.pack_propagate(False)

        self._lbl = tk.Label(
            self, text=text,
            font=("Segoe UI", font_size, "bold"),
            bg=self._bg_normal, fg=TEXT_PRI,
            cursor="hand2")
        self._lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Bind hover / click on both the frame and label
        for widget in (self, self._lbl):
            widget.bind("<Enter>",    self._on_enter)
            widget.bind("<Leave>",    self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, _event=None):
        self.config(bg=self._bg_hover)
        self._lbl.config(bg=self._bg_hover)

    def _on_leave(self, _event=None):
        self.config(bg=self._bg_normal)
        self._lbl.config(bg=self._bg_normal)

    def _on_click(self, _event=None):
        if self._command:
            self._command()



# ──────────────────────────────────────────────────────────────────────────────
# Scrollable container
# ──────────────────────────────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    """
    A vertically-scrollable container.
    Usage: put child widgets inside self.inner instead of self.
    Uses a plain tk.Canvas instance (not subclassed) — safe on Python 3.14.
    """

    def __init__(self, parent, bg=BG_DARK, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        # Scrollbar
        self._vsb = tk.Scrollbar(self, orient="vertical", width=8,
                                  troughcolor=BG_CARD, bg=BG_INPUT,
                                  activebackground=ACCENT, relief="flat", bd=0)
        self._vsb.pack(side="right", fill="y")

        # Plain canvas — NOT subclassed
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                  yscrollcommand=self._vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._vsb.config(command=self._canvas.yview)

        # Inner frame that holds all child widgets
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win_id = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        # Resize inner frame to match canvas width
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.inner.bind("<Configure>",   self._on_inner_resize)

        # Mousewheel bindings (Windows + Linux + Mac)
        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)
        self.inner.bind("<Enter>",   self._bind_mousewheel)
        self.inner.bind("<Leave>",   self._unbind_mousewheel)

    def _on_canvas_resize(self, event):
        """Keep the inner frame as wide as the canvas."""
        self._canvas.itemconfig(self._win_id, width=event.width)

    def _on_inner_resize(self, event):
        """Update scroll region whenever content height changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        # Hide scrollbar when content fits
        inner_h = self.inner.winfo_reqheight()
        canvas_h = self._canvas.winfo_height()
        if inner_h <= canvas_h:
            self._vsb.pack_forget()
        else:
            self._vsb.pack(side="right", fill="y")

    def _bind_mousewheel(self, _event=None):
        self._canvas.bind_all("<MouseWheel>",       self._on_mousewheel_win)
        self._canvas.bind_all("<Button-4>",         self._on_mousewheel_linux_up)
        self._canvas.bind_all("<Button-5>",         self._on_mousewheel_linux_down)

    def _unbind_mousewheel(self, _event=None):
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel_win(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux_up(self, _event):
        self._canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(self, _event):
        self._canvas.yview_scroll(1, "units")


# ──────────────────────────────────────────────────────────────────────────────
# Main Application
# ──────────────────────────────────────────────────────────────────────────────

class SteganographyApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("StegoCrypt — Steganography Image Tool")
        self.geometry("1100x760")
        self.minsize(900, 660)
        self.configure(bg=BG_DARK)

        # State
        self._enc_img_path = tk.StringVar()
        self._dec_img_path = tk.StringVar()
        self._enc_out_path = tk.StringVar()
        self._enc_pass     = tk.StringVar()
        self._dec_pass     = tk.StringVar()
        self._enc_preview  = None
        self._dec_preview  = None

        self._style_ttk()
        self._build_ui()

    # ── TTK Style ─────────────────────────────────────────────────────────────
    def _style_ttk(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Notebook
        style.configure("TNotebook",           background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_PANEL, foreground=TEXT_SEC,
                        padding=[20, 10], font=("Segoe UI", 11, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_CARD)],
                  foreground=[("selected", TEXT_PRI)])

        # Progressbar
        style.configure("Accent.Horizontal.TProgressbar",
                        troughcolor=BG_INPUT, background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=BG_INPUT, troughcolor=BG_CARD,
                        arrowcolor=TEXT_SEC, borderwidth=0)

    # ── Top bar ───────────────────────────────────────────────────────────────
    def _build_topbar(self, root):
        bar = tk.Frame(root, bg=BG_PANEL, height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Logo / Title
        logo_frame = tk.Frame(bar, bg=BG_PANEL)
        logo_frame.pack(side="left", padx=24)

        tk.Label(logo_frame, text="🔐", font=("Segoe UI Emoji", 22),
                 bg=BG_PANEL, fg=ACCENT).pack(side="left", pady=12)
        title_f = tk.Frame(logo_frame, bg=BG_PANEL)
        title_f.pack(side="left", padx=8)
        tk.Label(title_f, text="StegoCrypt", font=("Segoe UI", 16, "bold"),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(title_f, text="Hide secrets in plain sight",
                 font=("Segoe UI", 9), bg=BG_PANEL, fg=TEXT_SEC).pack(anchor="w")

        # Info badge
        badge = tk.Label(bar, text="  LSB Steganography + Caesar Cipher  ",
                         bg=ACCENT, fg=TEXT_PRI, font=("Segoe UI", 9, "bold"),
                         padx=8, pady=4, relief="flat")
        badge.pack(side="right", padx=24, pady=18)

    # ── Main UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar(self)

        # Separator line
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        # Notebook tabs
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        enc_frame = tk.Frame(self._nb, bg=BG_DARK)
        dec_frame = tk.Frame(self._nb, bg=BG_DARK)
        about_frame = tk.Frame(self._nb, bg=BG_DARK)

        self._nb.add(enc_frame,    text="  🔒  Encode (Hide)  ")
        self._nb.add(dec_frame,    text="  🔓  Decode (Reveal)  ")
        self._nb.add(about_frame,  text="  ℹ️   About  ")

        # Wrap each tab in a scrollable container
        enc_scroll   = ScrollableFrame(enc_frame,   bg=BG_DARK)
        dec_scroll   = ScrollableFrame(dec_frame,   bg=BG_DARK)
        about_scroll = ScrollableFrame(about_frame, bg=BG_DARK)
        enc_scroll.pack(fill="both", expand=True)
        dec_scroll.pack(fill="both", expand=True)
        about_scroll.pack(fill="both", expand=True)

        self._build_encode_tab(enc_scroll.inner)
        self._build_decode_tab(dec_scroll.inner)
        self._build_about_tab(about_scroll.inner)

    # ── Encode Tab ────────────────────────────────────────────────────────────
    def _build_encode_tab(self, parent):
        outer = tk.Frame(parent, bg=BG_DARK)
        outer.pack(fill="x", padx=24, pady=20)

        # === Left: image picker + preview ===
        left = tk.Frame(outer, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        self._build_section_header(left, "1. Select Carrier Image", ACCENT)

        pick_btn = GradientButton(left, "📂  Choose Image", self._enc_pick_image,
                                  c1="#2D3250", c2=ACCENT, width=220, height=40)
        pick_btn.pack(anchor="w", pady=(6, 4))

        self._enc_path_label = tk.Label(
            left, textvariable=self._enc_img_path,
            font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_SEC,
            anchor="w", wraplength=320)
        self._enc_path_label.pack(fill="x", padx=2)

        # Preview box
        preview_card = tk.Frame(left, bg=BG_CARD, bd=0, relief="flat")
        preview_card.pack(fill="both", expand=True, pady=(12, 0))
        self._highlight_border(preview_card)

        self._enc_preview_lbl = tk.Label(
            preview_card, text="No image selected\nSupported: PNG, BMP, JPG, TIFF",
            font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_MUT,
            compound="center", width=34, height=14)
        self._enc_preview_lbl.pack(fill="both", expand=True, padx=2, pady=2)

        # Capacity bar
        cap_frame = tk.Frame(left, bg=BG_DARK)
        cap_frame.pack(fill="x", pady=(10, 0))
        tk.Label(cap_frame, text="Image Capacity", font=("Segoe UI", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w")
        self._capacity_bar = ttk.Progressbar(
            cap_frame, style="Accent.Horizontal.TProgressbar",
            maximum=100, value=0, length=320)
        self._capacity_bar.pack(fill="x", pady=(4, 2))
        self._capacity_lbl = tk.Label(cap_frame, text="—", font=("Segoe UI", 9),
                                       bg=BG_DARK, fg=TEXT_SEC)
        self._capacity_lbl.pack(anchor="w")

        # === Right: inputs ===
        right = tk.Frame(outer, bg=BG_DARK, width=400)
        right.pack(side="right", fill="both", padx=(12, 0))
        right.pack_propagate(False)

        self._build_section_header(right, "2. Enter Secret Message", ACCENT)

        msg_frame = tk.Frame(right, bg=BG_INPUT, bd=0)
        msg_frame.pack(fill="both", expand=True, pady=(6, 0))
        self._highlight_border(msg_frame)

        self._enc_msg_text = tk.Text(
            msg_frame, font=("Consolas", 11), bg=BG_INPUT, fg=TEXT_PRI,
            insertbackground=ACCENT, relief="flat", wrap="word",
            bd=0, padx=10, pady=10, selectbackground=ACCENT)
        self._enc_msg_text.pack(fill="both", expand=True)
        self._enc_msg_text.bind("<KeyRelease>", self._on_enc_text_change)

        # Char counter
        self._char_counter = tk.Label(right, text="0 / — characters",
                                       font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_SEC)
        self._char_counter.pack(anchor="e", pady=(3, 0))

        self._build_section_header(right, "3. Password (Optional)", ACCENT)

        self._enc_pass_entry = self._build_password_entry(right, self._enc_pass)

        self._build_section_header(right, "4. Output File", ACCENT)

        out_row = tk.Frame(right, bg=BG_DARK)
        out_row.pack(fill="x", pady=(4, 0))

        self._enc_out_entry = tk.Entry(
            out_row, textvariable=self._enc_out_path,
            font=("Segoe UI", 10), bg=BG_INPUT, fg=TEXT_PRI,
            insertbackground=ACCENT, relief="flat", bd=0)
        self._enc_out_entry.pack(side="left", fill="x", expand=True,
                                  ipady=9, padx=(0, 6))
        self._highlight_border(self._enc_out_entry)

        GradientButton(out_row, "Browse", self._enc_pick_output,
                       c1="#2D3250", c2=ACCENT, width=90, height=38).pack(side="right")

        # Status
        self._enc_status = tk.Label(right, text="", font=("Segoe UI", 10, "bold"),
                                     bg=BG_DARK, fg=SUCCESS, wraplength=380, justify="left")
        self._enc_status.pack(anchor="w", pady=(10, 6))

        # Encode button
        GradientButton(right, "🔒  ENCODE & HIDE MESSAGE", self._do_encode,
                       c1=ACCENT, c2=ACCENT2, width=380, height=48, font_size=12).pack(
            fill="x", pady=(4, 0))

    # ── Decode Tab ────────────────────────────────────────────────────────────
    def _build_decode_tab(self, parent):
        outer = tk.Frame(parent, bg=BG_DARK)
        outer.pack(fill="x", padx=24, pady=20)

        # === Left: image picker + preview ===
        left = tk.Frame(outer, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        self._build_section_header(left, "1. Select Stego-Image", "#00D4FF")

        GradientButton(left, "📂  Choose Stego-Image", self._dec_pick_image,
                       c1="#1A2A3A", c2=ACCENT2, width=220, height=40).pack(
            anchor="w", pady=(6, 4))

        self._dec_path_label = tk.Label(
            left, textvariable=self._dec_img_path,
            font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_SEC,
            anchor="w", wraplength=320)
        self._dec_path_label.pack(fill="x", padx=2)

        preview_card = tk.Frame(left, bg=BG_CARD, bd=0)
        preview_card.pack(fill="both", expand=True, pady=(12, 0))
        self._highlight_border(preview_card)

        self._dec_preview_lbl = tk.Label(
            preview_card, text="No image selected",
            font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_MUT,
            compound="center", width=34, height=14)
        self._dec_preview_lbl.pack(fill="both", expand=True, padx=2, pady=2)

        # === Right ===
        right = tk.Frame(outer, bg=BG_DARK, width=400)
        right.pack(side="right", fill="both", padx=(12, 0))
        right.pack_propagate(False)

        self._build_section_header(right, "2. Password (Optional)", "#00D4FF")
        self._dec_pass_entry = self._build_password_entry(right, self._dec_pass)

        GradientButton(right, "🔓  DECODE & REVEAL MESSAGE", self._do_decode,
                       c1="#007A9A", c2=ACCENT2, width=380, height=48, font_size=12).pack(
            fill="x", pady=(18, 0))

        # Status
        self._dec_status = tk.Label(right, text="", font=("Segoe UI", 10, "bold"),
                                     bg=BG_DARK, fg=SUCCESS, wraplength=380, justify="left")
        self._dec_status.pack(anchor="w", pady=(10, 6))

        self._build_section_header(right, "3. Extracted Secret Message", "#00D4FF")

        msg_frame = tk.Frame(right, bg=BG_INPUT, bd=0)
        msg_frame.pack(fill="both", expand=True, pady=(6, 0))
        self._highlight_border(msg_frame)

        # Toolbar
        toolbar = tk.Frame(msg_frame, bg=BG_INPUT)
        toolbar.pack(fill="x", padx=6, pady=(6, 0))

        tk.Button(toolbar, text="📋 Copy", font=("Segoe UI", 9),
                  bg=ACCENT, fg=TEXT_PRI, relief="flat", bd=0, padx=10, pady=3,
                  cursor="hand2", command=self._copy_secret,
                  activebackground=HOVER_CARD, activeforeground=TEXT_PRI).pack(side="right")

        tk.Button(toolbar, text="🗑 Clear", font=("Segoe UI", 9),
                  bg=BG_CARD, fg=TEXT_SEC, relief="flat", bd=0, padx=10, pady=3,
                  cursor="hand2", command=self._clear_dec,
                  activebackground=HOVER_CARD, activeforeground=TEXT_PRI).pack(side="right", padx=(0, 6))

        self._dec_msg_text = tk.Text(
            msg_frame, font=("Consolas", 11), bg=BG_INPUT, fg=SUCCESS,
            insertbackground=ACCENT2, relief="flat", wrap="word",
            bd=0, padx=10, pady=10, selectbackground=ACCENT2,
            state="disabled")
        self._dec_msg_text.pack(fill="both", expand=True)

    # ── About Tab ─────────────────────────────────────────────────────────────
    def _build_about_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="both", expand=True)

        card = tk.Frame(frame, bg=BG_CARD, padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center", width=700, height=500)
        self._highlight_border(card)

        tk.Label(card, text="🔐 StegoCrypt", font=("Segoe UI", 28, "bold"),
                 bg=BG_CARD, fg=TEXT_PRI).pack(pady=(0, 4))
        tk.Label(card, text="Steganography Image Tool  •  v1.0",
                 font=("Segoe UI", 12), bg=BG_CARD, fg=ACCENT).pack()

        sep = tk.Frame(card, bg=BORDER, height=1)
        sep.pack(fill="x", pady=20)

        info = [
            ("Algorithm",     "LSB (Least Significant Bit) Steganography"),
            ("Encryption",    "Caesar Cipher (password-keyed obfuscation)"),
            ("Supported Formats", "PNG (lossless), BMP, TIFF — Output always PNG"),
            ("Capacity",      "1 bit per RGB channel → 3 bits per pixel"),
            ("Delimiter",     "<<END>> marker to detect message boundary"),
        ]

        for label, value in info:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=TEXT_SEC, width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10),
                     bg=BG_CARD, fg=TEXT_PRI, anchor="w").pack(side="left")

        sep2 = tk.Frame(card, bg=BORDER, height=1)
        sep2.pack(fill="x", pady=20)

        warning_text = (
            "⚠️  Use lossless formats (PNG, BMP) for the output.\n"
            "JPEG compression destroys hidden data — always save as PNG!"
        )
        tk.Label(card, text=warning_text, font=("Segoe UI", 10),
                 bg=BG_CARD, fg=WARNING, justify="left", wraplength=600).pack()

        tk.Label(card, text="Built with Python · Pillow · Tkinter",
                 font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_MUT).pack(pady=(24, 0))

    # ── Utility builders ──────────────────────────────────────────────────────

    def _build_section_header(self, parent, text: str, accent_color: str = ACCENT):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill="x", pady=(14, 0))
        tk.Frame(row, bg=accent_color, width=3, height=18).pack(side="left")
        tk.Label(row, text=f"  {text}", font=("Segoe UI", 10, "bold"),
                 bg=BG_DARK, fg=TEXT_PRI).pack(side="left")

    def _build_password_entry(self, parent, var: tk.StringVar) -> tk.Entry:
        frame = tk.Frame(parent, bg=BG_INPUT)
        frame.pack(fill="x", pady=(6, 0))
        self._highlight_border(frame)

        entry = tk.Entry(frame, textvariable=var, font=("Segoe UI", 11),
                         bg=BG_INPUT, fg=TEXT_PRI, insertbackground=ACCENT,
                         relief="flat", bd=0, show="●")
        entry.pack(side="left", fill="x", expand=True, ipady=10, padx=10)

        show_var = tk.BooleanVar(value=False)

        def toggle_show():
            entry.config(show="" if show_var.get() else "●")

        chk = tk.Checkbutton(frame, text="Show", variable=show_var, command=toggle_show,
                              bg=BG_INPUT, fg=TEXT_SEC, activebackground=BG_INPUT,
                              activeforeground=TEXT_PRI, selectcolor=BG_INPUT,
                              font=("Segoe UI", 9), bd=0, cursor="hand2")
        chk.pack(side="right", padx=8)
        return entry

    def _highlight_border(self, widget):
        """Paint a 1px border around a widget using a surrounding frame trick."""
        widget.configure(highlightbackground=BORDER, highlightcolor=ACCENT,
                         highlightthickness=1)

    # ── Image pickers ─────────────────────────────────────────────────────────

    def _enc_pick_image(self):
        path = filedialog.askopenfilename(
            title="Select Carrier Image",
            filetypes=[("Image Files", "*.png *.bmp *.tiff *.tif *.jpg *.jpeg"),
                       ("All Files", "*.*")])
        if not path:
            return
        self._enc_img_path.set(path)
        # Auto-suggest output path
        p = Path(path)
        self._enc_out_path.set(str(p.parent / (p.stem + "_stego.png")))
        self._load_preview(path, self._enc_preview_lbl, "enc")
        self._update_capacity()

    def _dec_pick_image(self):
        path = filedialog.askopenfilename(
            title="Select Stego-Image",
            filetypes=[("Image Files", "*.png *.bmp *.tiff *.tif *.jpg *.jpeg"),
                       ("All Files", "*.*")])
        if not path:
            return
        self._dec_img_path.set(path)
        self._load_preview(path, self._dec_preview_lbl, "dec")

    def _enc_pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Stego-Image As",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")])
        if path:
            self._enc_out_path.set(path)

    def _load_preview(self, path: str, label: tk.Label, side: str):
        try:
            img = Image.open(path)
            img.thumbnail((340, 240), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo, text="")
            label.image = photo  # keep reference
            if side == "enc":
                self._enc_preview = photo
            else:
                self._dec_preview = photo
        except Exception as exc:
            label.configure(text=f"Cannot preview:\n{exc}", image="")

    # ── Capacity updater ──────────────────────────────────────────────────────

    def _update_capacity(self):
        path = self._enc_img_path.get()
        if not path:
            return
        result = image_capacity(path)
        if result.get("success"):
            cap = result["capacity_chars"]
            w, h = result["width"], result["height"]
            msg_len = len(self._enc_msg_text.get("1.0", "end-1c"))
            pct = min(int(msg_len / max(cap, 1) * 100), 100)
            self._capacity_bar["value"] = pct
            self._capacity_lbl.config(
                text=f"{w}×{h}px  •  Max ≈ {cap:,} characters  •  Used: {msg_len:,}")
            self._char_counter.config(text=f"{msg_len:,} / {cap:,} characters")
        else:
            self._capacity_lbl.config(text=result.get("message", "Error"))

    def _on_enc_text_change(self, _event=None):
        self._update_capacity()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_encode(self):
        img_path = self._enc_img_path.get().strip()
        out_path = self._enc_out_path.get().strip()
        message  = self._enc_msg_text.get("1.0", "end-1c").strip()
        password = self._enc_pass.get()

        if not img_path:
            self._set_status(self._enc_status, "⚠  Please select a carrier image.", WARNING)
            return
        if not message:
            self._set_status(self._enc_status, "⚠  Please enter a secret message.", WARNING)
            return
        if not out_path:
            self._set_status(self._enc_status, "⚠  Please specify an output file.", WARNING)
            return

        result = encode_message(img_path, message, out_path, password)

        if result["success"]:
            self._set_status(self._enc_status,
                             f"✓  {result['message']}\n   Saved → {out_path}", SUCCESS)
        else:
            self._set_status(self._enc_status, f"✗  {result['message']}", ERROR)

    def _do_decode(self):
        img_path = self._dec_img_path.get().strip()
        password = self._dec_pass.get()

        if not img_path:
            self._set_status(self._dec_status, "⚠  Please select a stego-image.", WARNING)
            return

        result = decode_message(img_path, password)

        if result["success"]:
            self._set_status(self._dec_status, f"✓  {result['message']}", SUCCESS)
            self._set_decoded_text(result["secret"])
        else:
            self._set_status(self._dec_status, f"✗  {result['message']}", ERROR)
            self._set_decoded_text("")

    def _set_decoded_text(self, text: str):
        self._dec_msg_text.config(state="normal")
        self._dec_msg_text.delete("1.0", "end")
        if text:
            self._dec_msg_text.insert("1.0", text)
        self._dec_msg_text.config(state="disabled")

    def _copy_secret(self):
        text = self._dec_msg_text.get("1.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Secret message copied to clipboard!")
        else:
            messagebox.showinfo("Nothing to copy", "No decoded message yet.")

    def _clear_dec(self):
        self._set_decoded_text("")
        self._dec_status.config(text="")

    @staticmethod
    def _set_status(label: tk.Label, text: str, color: str):
        label.config(text=text, fg=color)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SteganographyApp()
    app.mainloop()
