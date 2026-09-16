"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CipherVault — Premium Encryption Suite                                    ║
║  Modern CustomTkinter desktop application                                  ║
║  Text encryption, image encryption with preview, activity logging          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ── Dependency check & auto-install ──────────────────────────────────────────
import subprocess
import sys

def _ensure_package(pkg_name: str, import_name: str = None):
    """Install a package if it's not available."""
    import_name = import_name or pkg_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"[CipherVault] Installing {pkg_name}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg_name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

_ensure_package("customtkinter")
_ensure_package("Pillow", "PIL")

# ── Imports ──────────────────────────────────────────────────────────────────

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
import os
import threading
import time

# Local modules
from cipher_engine import encrypt_text, decrypt_text, encrypt_image, decrypt_image, ALGORITHM_INFO, ENC_MAP, SPECIALS
from user_manager import UserManager
from image_handler import generate_thumbnail, get_image_info, create_placeholder_image, is_valid_image

# ── App Configuration ────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════════════
#  COLOR PALETTE — Monochrome: black, white, grey
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    # Backgrounds (layered depth — pure blacks)
    BG_DEEP    = "#000000"    # Deepest background (true black)
    BG_BASE    = "#0a0a0a"    # Main background
    BG_CARD    = "#141414"    # Card / panel surfaces
    BG_ELEVATED = "#1e1e1e"   # Elevated surfaces (hover, active)
    BG_INPUT   = "#0d0d0d"    # Input fields

    # Borders & dividers
    BORDER     = "#2a2a2a"
    BORDER_DIM = "#1c1c1c"

    # Accent: Primary (white — used for encrypt highlights)
    VIOLET     = "#ffffff"
    VIOLET_DIM = "#c0c0c0"
    VIOLET_BG  = "#1a1a1a"

    # Accent: Secondary (light grey — used for decrypt highlights)
    EMERALD    = "#b0b0b0"
    EMERALD_DIM = "#8a8a8a"
    EMERALD_BG = "#161616"

    # Accent: Warning (mid-grey)
    AMBER      = "#999999"
    AMBER_DIM  = "#777777"

    # Accent: Error / danger (lighter grey to stand out)
    ROSE       = "#d0d0d0"

    # Accent: Info / neutral
    CYAN       = "#e0e0e0"

    # Text
    TEXT       = "#f0f0f0"
    TEXT_DIM   = "#909090"
    TEXT_MUTED = "#606060"
    TEXT_DARK  = "#0a0a0a"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class CipherVaultApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ── Window setup ──
        self.title("CipherVault")
        self.geometry("1280x820")
        self.minsize(900, 650)
        self.configure(fg_color=Colors.BG_DEEP)

        # Set app icon (optional)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        # ── State ──
        self.user_manager = UserManager()
        self.current_tab = "text"
        self._preview_images = {}  # Keep references to prevent GC
        self._clock_running = True
        self._selected_image_path = None
        self._encrypted_image_path = None

        # ── Build UI ──
        self._build_layout()
        self._start_clock()

    # ═══════════════════════════════════════════════════════════════════════════
    #  LAYOUT
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_layout(self):
        """Build the main 2-column layout: sidebar + content area."""

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──
        self._build_sidebar()

        # ── Content area ──
        self.content_frame = ctk.CTkFrame(
            self, fg_color=Colors.BG_BASE, corner_radius=0
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

        # ── Top bar ──
        self._build_topbar()

        # ── Tab frames (stacked) ──
        self.tab_frames = {}
        self._build_text_tab()
        self._build_image_tab()
        self._build_activity_tab()
        self._build_profile_tab()

        # Show default tab
        self._show_tab("text")

    # ═══════════════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        """Dark glass sidebar with navigation."""
        self.sidebar = ctk.CTkFrame(
            self, width=240, fg_color=Colors.BG_CARD,
            corner_radius=0, border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)  # Spacer

        # ── Logo ──
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(28, 6), sticky="ew")

        ctk.CTkLabel(
            logo_frame, text="⬡ CipherVault",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=Colors.VIOLET,
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Premium Encryption Suite",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # ── Divider ──
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=Colors.BORDER_DIM
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(16, 12))

        # ── Nav section label ──
        ctk.CTkLabel(
            self.sidebar, text="  WORKSPACE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=2, column=0, padx=20, pady=(4, 4), sticky="ew")

        # ── Navigation buttons ──
        self.nav_buttons = {}
        nav_items = [
            ("text",     "🔐  Text Cipher",  3),
            ("image",    "📷  Image Vault",   4),
            ("activity", "📊  Activity Log",  5),
            ("profile",  "👤  Profile",       6),
        ]

        for tab_id, label, row in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                fg_color="transparent",
                hover_color=Colors.BG_ELEVATED,
                text_color=Colors.TEXT_DIM,
                height=42, corner_radius=10,
                command=lambda t=tab_id: self._show_tab(t),
            )
            btn.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # ── Spacer ──  (row 10 has weight=1)

        # ── Bottom stats ──
        stats_frame = ctk.CTkFrame(
            self.sidebar, fg_color=Colors.BG_ELEVATED, corner_radius=12
        )
        stats_frame.grid(row=11, column=0, padx=14, pady=(0, 10), sticky="ew")

        self.sidebar_stats_label = ctk.CTkLabel(
            stats_frame, text="",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=Colors.TEXT_MUTED, justify="left",
        )
        self.sidebar_stats_label.pack(padx=12, pady=10, anchor="w")
        self._update_sidebar_stats()

        # ── Clock ──
        self.clock_label = ctk.CTkLabel(
            self.sidebar, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_MUTED,
        )
        self.clock_label.grid(row=12, column=0, padx=20, pady=(0, 16), sticky="w")

    def _update_sidebar_stats(self):
        """Refresh the sidebar stats display."""
        stats = self.user_manager.get_stats()
        text = (
            f"Session #{stats['session_id']}\n"
            f"Ops: {stats['session_ops']}  |  Total: {stats['total_operations']}\n"
            f"Uptime: {stats['session_uptime']}"
        )
        self.sidebar_stats_label.configure(text=text)

    # ═══════════════════════════════════════════════════════════════════════════
    #  TOP BAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_topbar(self):
        """Header bar with tab title and user info."""
        self.topbar = ctk.CTkFrame(
            self.content_frame, height=60, fg_color=Colors.BG_CARD,
            corner_radius=0, border_width=0,
        )
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(1, weight=1)
        self.topbar.grid_propagate(False)

        self.topbar_title = ctk.CTkLabel(
            self.topbar, text="Text Cipher",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=Colors.TEXT,
        )
        self.topbar_title.grid(row=0, column=0, padx=28, pady=14, sticky="w")

        self.topbar_subtitle = ctk.CTkLabel(
            self.topbar, text="Encrypt and decrypt messages with symbol-pair substitution",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_MUTED,
        )
        self.topbar_subtitle.grid(row=0, column=1, padx=10, pady=14, sticky="w")

        # User badge
        user_badge = ctk.CTkFrame(self.topbar, fg_color=Colors.VIOLET_BG, corner_radius=8)
        user_badge.grid(row=0, column=2, padx=20, pady=14, sticky="e")

        self.user_badge_label = ctk.CTkLabel(
            user_badge, text=f"  👤 {self.user_manager.username}  ",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.VIOLET,
        )
        self.user_badge_label.pack(padx=8, pady=4)

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB SWITCHING
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_tab(self, tab_id: str):
        """Switch visible tab and update sidebar button states."""
        titles = {
            "text": ("Text Cipher", "Encrypt & decrypt messages with symbol-pair substitution"),
            "image": ("Image Vault", "Visual encryption with full image preview"),
            "activity": ("Activity Log", "Complete history of all operations"),
            "profile": ("Profile & Settings", "Manage your identity and session"),
        }

        # Hide all tabs
        for frame in self.tab_frames.values():
            frame.grid_forget()

        # Show selected
        if tab_id in self.tab_frames:
            self.tab_frames[tab_id].grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Update topbar
        title, subtitle = titles.get(tab_id, ("", ""))
        self.topbar_title.configure(text=title)
        self.topbar_subtitle.configure(text=subtitle)

        # Update nav button highlights
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == tab_id:
                btn.configure(
                    fg_color=Colors.VIOLET_BG,
                    text_color=Colors.VIOLET,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=Colors.TEXT_DIM,
                )

        self.current_tab = tab_id

        # Refresh data if switching to activity or profile
        if tab_id == "activity":
            self._refresh_activity()
        elif tab_id == "profile":
            self._refresh_profile()

        self._update_sidebar_stats()

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 1: TEXT CIPHER
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_text_tab(self):
        """Build the text encryption/decryption tab."""
        frame = ctk.CTkFrame(self.content_frame, fg_color=Colors.BG_BASE, corner_radius=0)
        self.tab_frames["text"] = frame

        # Scrollable container
        scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Colors.BG_BASE,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.VIOLET_DIM,
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # ── Encrypt Card ──
        enc_card = self._make_card(scroll, "🔐  ENCRYPT", Colors.VIOLET, row=0, col=0)
        enc_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            enc_card, text="Enter plaintext message",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.enc_input = ctk.CTkTextbox(
            enc_card, height=150, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.TEXT,
            font=ctk.CTkFont(family="Consolas", size=13),
            border_width=1, border_color=Colors.BORDER,
            scrollbar_button_color=Colors.BORDER,
        )
        self.enc_input.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Char count
        self.enc_char_count = ctk.CTkLabel(
            enc_card, text="0 characters",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=Colors.TEXT_MUTED, anchor="e",
        )
        self.enc_char_count.grid(row=2, column=0, sticky="e", pady=(0, 6))
        self.enc_input.bind("<KeyRelease>", self._update_enc_count)

        # Encrypt button
        ctk.CTkButton(
            enc_card, text="⚡  ENCRYPT", height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=Colors.VIOLET, hover_color=Colors.VIOLET_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=10,
            command=self._do_encrypt_text,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 12))

        ctk.CTkLabel(
            enc_card, text="Encrypted Output",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Colors.VIOLET, anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=(0, 6))

        self.enc_output = ctk.CTkTextbox(
            enc_card, height=120, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.VIOLET,
            font=ctk.CTkFont(family="Consolas", size=12),
            border_width=1, border_color=Colors.VIOLET_BG,
            scrollbar_button_color=Colors.BORDER,
            state="disabled",
        )
        self.enc_output.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkButton(
            enc_card, text="📋  Copy Result", height=32,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER,
            text_color=Colors.TEXT_DIM, corner_radius=8,
            command=lambda: self._copy_output(self.enc_output),
        ).grid(row=6, column=0, sticky="w", pady=(0, 4))

        # ── Decrypt Card ──
        dec_card = self._make_card(scroll, "🔓  DECRYPT", Colors.EMERALD, row=0, col=1)
        dec_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dec_card, text="Paste encrypted cipher text",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.dec_input = ctk.CTkTextbox(
            dec_card, height=150, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.VIOLET,
            font=ctk.CTkFont(family="Consolas", size=13),
            border_width=1, border_color=Colors.BORDER,
            scrollbar_button_color=Colors.BORDER,
        )
        self.dec_input.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Char count
        self.dec_char_count = ctk.CTkLabel(
            dec_card, text="0 tokens",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=Colors.TEXT_MUTED, anchor="e",
        )
        self.dec_char_count.grid(row=2, column=0, sticky="e", pady=(0, 6))
        self.dec_input.bind("<KeyRelease>", self._update_dec_count)

        # Decrypt button
        ctk.CTkButton(
            dec_card, text="⚡  DECRYPT", height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=Colors.EMERALD, hover_color=Colors.EMERALD_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=10,
            command=self._do_decrypt_text,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 12))

        ctk.CTkLabel(
            dec_card, text="Decrypted Output",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Colors.EMERALD, anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=(0, 6))

        self.dec_output = ctk.CTkTextbox(
            dec_card, height=120, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.EMERALD,
            font=ctk.CTkFont(family="Consolas", size=12),
            border_width=1, border_color=Colors.EMERALD_BG,
            scrollbar_button_color=Colors.BORDER,
            state="disabled",
        )
        self.dec_output.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkButton(
            dec_card, text="📋  Copy Result", height=32,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER,
            text_color=Colors.TEXT_DIM, corner_radius=8,
            command=lambda: self._copy_output(self.dec_output),
        ).grid(row=6, column=0, sticky="w", pady=(0, 4))

        # ── Status bar for text tab ──
        status_frame = ctk.CTkFrame(
            frame, height=36, fg_color=Colors.BG_CARD, corner_radius=0
        )
        status_frame.pack(fill="x", side="bottom")

        self.text_status = ctk.CTkLabel(
            status_frame,
            text=f"Ready  ·  {len(ENC_MAP)} character mappings  ·  {len(SPECIALS)} special symbols",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_MUTED,
        )
        self.text_status.pack(padx=24, pady=8, anchor="w")

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 2: IMAGE VAULT
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_image_tab(self):
        """Build the image encryption tab with preview support."""
        frame = ctk.CTkFrame(self.content_frame, fg_color=Colors.BG_BASE, corner_radius=0)
        self.tab_frames["image"] = frame

        scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Colors.BG_BASE,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.VIOLET_DIM,
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # ── Left: Image Selection & Preview ──
        preview_card = self._make_card(scroll, "📷  IMAGE PREVIEW", Colors.VIOLET, row=0, col=0)
        preview_card.grid_columnconfigure(0, weight=1)

        # Drop zone / select button
        self.select_btn_frame = ctk.CTkFrame(
            preview_card, fg_color=Colors.BG_INPUT, corner_radius=12,
            border_width=2, border_color=Colors.BORDER,
        )
        self.select_btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.select_inner = ctk.CTkFrame(self.select_btn_frame, fg_color="transparent")
        self.select_inner.pack(padx=20, pady=20)

        ctk.CTkLabel(
            self.select_inner, text="📂",
            font=ctk.CTkFont(size=36),
            text_color=Colors.TEXT_MUTED,
        ).pack()

        ctk.CTkLabel(
            self.select_inner, text="Click to select an image",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(4, 8))

        ctk.CTkButton(
            self.select_inner, text="Browse Files", height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=Colors.VIOLET, hover_color=Colors.VIOLET_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=8,
            command=self._select_image,
        ).pack()

        # Image preview area
        self.image_preview_frame = ctk.CTkFrame(
            preview_card, fg_color=Colors.BG_INPUT, corner_radius=12,
            height=320, border_width=1, border_color=Colors.BORDER_DIM,
        )
        self.image_preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.image_preview_frame.grid_propagate(False)
        self.image_preview_frame.grid_columnconfigure(0, weight=1)
        self.image_preview_frame.grid_rowconfigure(0, weight=1)

        self.image_preview_label = ctk.CTkLabel(
            self.image_preview_frame, text="No image selected",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=Colors.TEXT_MUTED,
        )
        self.image_preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Image info panel
        self.image_info_label = ctk.CTkLabel(
            preview_card, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_DIM, anchor="w", justify="left",
        )
        self.image_info_label.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        # ── Right: Actions & Results ──
        action_card = self._make_card(scroll, "⚙  OPERATIONS", Colors.EMERALD, row=0, col=1)
        action_card.grid_columnconfigure(0, weight=1)

        # Encrypt button
        ctk.CTkButton(
            action_card, text="🔐  Encrypt Image", height=50,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=Colors.VIOLET, hover_color=Colors.VIOLET_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=12,
            command=self._do_encrypt_image,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Decrypt button
        ctk.CTkButton(
            action_card, text="🔓  Decrypt Image", height=50,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=Colors.EMERALD, hover_color=Colors.EMERALD_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=12,
            command=self._do_decrypt_image,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        # Divider
        ctk.CTkFrame(action_card, height=1, fg_color=Colors.BORDER_DIM).grid(
            row=2, column=0, sticky="ew", pady=(0, 16)
        )

        # Result header
        ctk.CTkLabel(
            action_card, text="RESULT",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=Colors.VIOLET, anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))

        # Result preview (for encrypted/decrypted image)
        self.result_preview_frame = ctk.CTkFrame(
            action_card, fg_color=Colors.BG_INPUT, corner_radius=12,
            height=200, border_width=1, border_color=Colors.BORDER_DIM,
        )
        self.result_preview_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.result_preview_frame.grid_propagate(False)
        self.result_preview_frame.grid_columnconfigure(0, weight=1)
        self.result_preview_frame.grid_rowconfigure(0, weight=1)

        self.result_preview_label = ctk.CTkLabel(
            self.result_preview_frame, text="Waiting for operation...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_MUTED,
        )
        self.result_preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Result text
        self.image_result_text = ctk.CTkTextbox(
            action_card, height=120, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.VIOLET,
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1, border_color=Colors.BORDER_DIM,
            state="disabled",
        )
        self.image_result_text.grid(row=5, column=0, sticky="ew", pady=(0, 4))

        # Status bar
        status_frame = ctk.CTkFrame(
            frame, height=36, fg_color=Colors.BG_CARD, corner_radius=0
        )
        status_frame.pack(fill="x", side="bottom")

        self.image_status = ctk.CTkLabel(
            status_frame,
            text="Select an image to preview before encrypting",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_MUTED,
        )
        self.image_status.pack(padx=24, pady=8, anchor="w")

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 3: ACTIVITY LOG
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_activity_tab(self):
        """Build the activity log tab with table view."""
        frame = ctk.CTkFrame(self.content_frame, fg_color=Colors.BG_BASE, corner_radius=0)
        self.tab_frames["activity"] = frame

        # Toolbar
        toolbar = ctk.CTkFrame(frame, fg_color="transparent", height=48)
        toolbar.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkButton(
            toolbar, text="🔄  Refresh", height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=Colors.BG_ELEVATED, hover_color=Colors.BORDER,
            text_color=Colors.TEXT_DIM, corner_radius=8,
            command=self._refresh_activity,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            toolbar, text="🗑  Clear History", height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=Colors.BG_ELEVATED, hover_color="#2a2a2a",
            text_color=Colors.ROSE, corner_radius=8,
            command=self._clear_history,
        ).pack(side="left")

        self.activity_count_label = ctk.CTkLabel(
            toolbar, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_MUTED,
        )
        self.activity_count_label.pack(side="right")

        # Table header
        header_frame = ctk.CTkFrame(frame, fg_color=Colors.BG_CARD, corner_radius=0, height=40)
        header_frame.pack(fill="x", padx=24, pady=(0, 0))
        header_frame.pack_propagate(False)

        headers = [("Time", 160), ("User", 100), ("Operation", 140), ("Input", 180), ("Status", 80), ("Details", 200)]
        for i, (text, width) in enumerate(headers):
            lbl = ctk.CTkLabel(
                header_frame, text=text, width=width,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=Colors.VIOLET, anchor="w",
            )
            lbl.pack(side="left", padx=(16 if i == 0 else 4, 4), pady=8)

        # Scrollable rows
        self.activity_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Colors.BG_BASE,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.VIOLET_DIM,
        )
        self.activity_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

    def _refresh_activity(self):
        """Refresh the activity log display."""
        # Clear existing rows
        for widget in self.activity_scroll.winfo_children():
            widget.destroy()

        history = self.user_manager.get_activity_history(limit=200)
        self.activity_count_label.configure(text=f"{len(history)} entries")

        if not history:
            ctk.CTkLabel(
                self.activity_scroll, text="No activity recorded yet.",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=Colors.TEXT_MUTED,
            ).pack(pady=40)
            return

        for i, entry in enumerate(history):
            bg = Colors.BG_CARD if i % 2 == 0 else Colors.BG_BASE
            row_frame = ctk.CTkFrame(
                self.activity_scroll, fg_color=bg, corner_radius=0, height=36
            )
            row_frame.pack(fill="x", pady=0)
            row_frame.pack_propagate(False)

            op = entry.get('operation', '')
            status = entry.get('status', '')

            # Color code by operation type
            op_color = Colors.VIOLET if 'encrypt' in op and 'decrypt' not in op else Colors.EMERALD
            status_color = Colors.EMERALD if status == 'success' else Colors.ROSE

            fields = [
                (entry.get('timestamp', ''), 160, Colors.TEXT_DIM),
                (entry.get('username', ''), 100, Colors.TEXT_DIM),
                (op.replace('_', ' ').title(), 140, op_color),
                (entry.get('input_preview', '')[:30], 180, Colors.TEXT_MUTED),
                (status.upper(), 80, status_color),
                (entry.get('details', '')[:30], 200, Colors.TEXT_MUTED),
            ]

            for j, (text, width, color) in enumerate(fields):
                ctk.CTkLabel(
                    row_frame, text=text, width=width,
                    font=ctk.CTkFont(family="Consolas", size=11),
                    text_color=color, anchor="w",
                ).pack(side="left", padx=(16 if j == 0 else 4, 4), pady=6)

    def _clear_history(self):
        if messagebox.askyesno("Clear History", "Delete all activity records? This cannot be undone."):
            self.user_manager.clear_history()
            self._refresh_activity()

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 4: PROFILE & SETTINGS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_profile_tab(self):
        """Build the user profile tab."""
        frame = ctk.CTkFrame(self.content_frame, fg_color=Colors.BG_BASE, corner_radius=0)
        self.tab_frames["profile"] = frame

        scroll = ctk.CTkScrollableFrame(
            frame, fg_color=Colors.BG_BASE,
            scrollbar_button_color=Colors.BORDER,
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # ── User Profile Card ──
        profile_card = self._make_card(scroll, "👤  USER PROFILE", Colors.VIOLET, row=0, col=0)
        profile_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            profile_card, text="Display Name",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.username_entry = ctk.CTkEntry(
            profile_card, height=40, corner_radius=10,
            fg_color=Colors.BG_INPUT, text_color=Colors.TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            border_width=1, border_color=Colors.BORDER,
            placeholder_text="Enter your name",
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.username_entry.insert(0, self.user_manager.username)

        ctk.CTkButton(
            profile_card, text="💾  Save Name", height=38,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=Colors.VIOLET, hover_color=Colors.VIOLET_DIM,
            text_color=Colors.TEXT_DARK, corner_radius=10,
            command=self._save_username,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 16))

        # Divider
        ctk.CTkFrame(profile_card, height=1, fg_color=Colors.BORDER_DIM).grid(
            row=3, column=0, sticky="ew", pady=(0, 16)
        )

        # Session info
        ctk.CTkLabel(
            profile_card, text="CURRENT SESSION",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=(0, 8))

        self.session_info_label = ctk.CTkLabel(
            profile_card, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=Colors.TEXT_DIM, anchor="w", justify="left",
        )
        self.session_info_label.grid(row=5, column=0, sticky="ew", pady=(0, 4))

        # ── Statistics Card ──
        stats_card = self._make_card(scroll, "📊  STATISTICS", Colors.EMERALD, row=0, col=1)
        stats_card.grid_columnconfigure(0, weight=1)

        self.stats_grid_frame = ctk.CTkFrame(stats_card, fg_color="transparent")
        self.stats_grid_frame.grid(row=0, column=0, sticky="ew")
        self.stats_grid_frame.grid_columnconfigure(0, weight=1)
        self.stats_grid_frame.grid_columnconfigure(1, weight=1)

        # Algorithm info
        ctk.CTkFrame(stats_card, height=1, fg_color=Colors.BORDER_DIM).grid(
            row=1, column=0, sticky="ew", pady=16
        )

        ctk.CTkLabel(
            stats_card, text="ENGINE INFO",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=Colors.TEXT_MUTED, anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        algo_info = (
            f"Text Cipher: {ALGORITHM_INFO['text']['name']}\n"
            f"Token Pool:  {ALGORITHM_INFO['text']['token_count']} tokens\n"
            f"Charset:     {ALGORITHM_INFO['text']['charset_size']} characters\n"
            f"Seed:        {ALGORITHM_INFO['text']['seed']}\n\n"
            f"Image Cipher: {ALGORITHM_INFO['image']['name']}\n"
            f"Color Space:  {ALGORITHM_INFO['image']['color_space']}\n"
            f"Encoding:     {ALGORITHM_INFO['image']['encoding']}\n"
            f"Hash:         {ALGORITHM_INFO['image']['hash']}"
        )
        ctk.CTkLabel(
            stats_card, text=algo_info,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=Colors.TEXT_MUTED, anchor="w", justify="left",
        ).grid(row=3, column=0, sticky="ew")

    def _refresh_profile(self):
        """Refresh profile tab data."""
        stats = self.user_manager.get_stats()

        # Session info
        self.session_info_label.configure(
            text=(
                f"ID:        {stats['session_id']}\n"
                f"Started:   {self.user_manager.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Uptime:    {stats['session_uptime']}\n"
                f"Ops:       {stats['session_ops']}"
            )
        )

        # Stats grid
        for widget in self.stats_grid_frame.winfo_children():
            widget.destroy()

        stat_items = [
            ("Total Operations", str(stats['total_operations']), Colors.VIOLET),
            ("Success Rate", stats['success_rate'], Colors.EMERALD),
            ("Text Ops", str(stats['text_operations']), Colors.CYAN),
            ("Image Ops", str(stats['image_operations']), Colors.AMBER),
            ("Encryptions", str(stats['encryptions']), Colors.VIOLET),
            ("Decryptions", str(stats['decryptions']), Colors.EMERALD),
        ]

        for i, (label, value, color) in enumerate(stat_items):
            row, col = divmod(i, 2)
            stat_card = ctk.CTkFrame(
                self.stats_grid_frame, fg_color=Colors.BG_INPUT,
                corner_radius=10, border_width=1, border_color=Colors.BORDER_DIM,
            )
            stat_card.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

            ctk.CTkLabel(
                stat_card, text=value,
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color=color,
            ).pack(padx=12, pady=(10, 2))

            ctk.CTkLabel(
                stat_card, text=label,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=Colors.TEXT_MUTED,
            ).pack(padx=12, pady=(0, 10))

    # ═══════════════════════════════════════════════════════════════════════════
    #  TEXT ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _do_encrypt_text(self):
        """Encrypt text input."""
        msg = self.enc_input.get("1.0", "end-1c")
        if not msg.strip():
            messagebox.showwarning("Empty Input", "Type a message to encrypt.")
            return

        try:
            result = encrypt_text(msg)

            self.enc_output.configure(state="normal")
            self.enc_output.delete("1.0", "end")
            self.enc_output.insert("1.0", result)
            self.enc_output.configure(state="disabled")

            self.text_status.configure(
                text=f"✓ Encrypted {len(msg)} chars → {len(result)} cipher symbols  ·  "
                     f"{datetime.now().strftime('%H:%M:%S')}",
                text_color=Colors.EMERALD,
            )

            self.user_manager.log_operation(
                operation="encrypt_text",
                input_preview=msg,
                input_size=len(msg),
                output_size=len(result),
                status="success",
                details=f"{len(msg)} chars encrypted",
            )
            self._update_sidebar_stats()

        except Exception as e:
            self.text_status.configure(text=f"✗ Error: {str(e)}", text_color=Colors.ROSE)
            self.user_manager.log_operation(
                operation="encrypt_text", input_preview=msg,
                input_size=len(msg), status="error", details=str(e),
            )

    def _do_decrypt_text(self):
        """Decrypt cipher text input."""
        msg = self.dec_input.get("1.0", "end-1c").strip()
        if not msg:
            messagebox.showwarning("Empty Input", "Paste encrypted text to decrypt.")
            return

        try:
            result = decrypt_text(msg)

            self.dec_output.configure(state="normal")
            self.dec_output.delete("1.0", "end")
            self.dec_output.insert("1.0", result)
            self.dec_output.configure(state="disabled")

            self.text_status.configure(
                text=f"✓ Decrypted → {len(result)} characters recovered  ·  "
                     f"{datetime.now().strftime('%H:%M:%S')}",
                text_color=Colors.EMERALD,
            )

            self.user_manager.log_operation(
                operation="decrypt_text",
                input_preview=msg[:60],
                input_size=len(msg),
                output_size=len(result),
                status="success",
                details=f"{len(result)} chars recovered",
            )
            self._update_sidebar_stats()

        except Exception as e:
            self.text_status.configure(text=f"✗ Error: {str(e)}", text_color=Colors.ROSE)
            self.user_manager.log_operation(
                operation="decrypt_text", input_preview=msg[:60],
                input_size=len(msg), status="error", details=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════════════
    #  IMAGE ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _select_image(self):
        """Open file dialog to select an image for preview."""
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self._selected_image_path = path
        self._show_image_preview(path)

    def _show_image_preview(self, path: str):
        """Display image preview in the preview area."""
        try:
            info = get_image_info(path)
            thumb = generate_thumbnail(path, max_size=(380, 280))

            # Convert to CTkImage for display
            ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb,
                                   size=(thumb.width, thumb.height))
            self._preview_images['current'] = ctk_img  # Prevent GC

            self.image_preview_label.configure(image=ctk_img, text="")

            self.image_info_label.configure(
                text=(
                    f"📁 {info['filename']}  ·  {info['width']}×{info['height']}  ·  "
                    f"{info['pixels']:,} px  ·  {info['size_kb']} KB  ·  {info['format']}"
                )
            )

            self.image_status.configure(
                text=f"Image loaded: {info['filename']}  —  Ready to encrypt",
                text_color=Colors.EMERALD,
            )

        except Exception as e:
            self.image_preview_label.configure(image=None, text=f"Cannot preview: {str(e)}")
            self.image_info_label.configure(text="")
            self.image_status.configure(text=f"Error: {str(e)}", text_color=Colors.ROSE)

    def _show_result_preview(self, path: str, label_text: str = ""):
        """Display result image in the result preview area."""
        try:
            thumb = generate_thumbnail(path, max_size=(350, 180))
            ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb,
                                   size=(thumb.width, thumb.height))
            self._preview_images['result'] = ctk_img

            self.result_preview_label.configure(image=ctk_img, text="")

        except Exception as e:
            self.result_preview_label.configure(image=None, text=label_text or str(e))

    def _do_encrypt_image(self):
        """Encrypt the selected image."""
        if not self._selected_image_path:
            messagebox.showwarning("No Image", "Select an image first using the Browse button.")
            return

        # Ask for output directory
        output_dir = filedialog.askdirectory(title="Select output folder for encrypted image")
        if not output_dir:
            return

        try:
            self.image_status.configure(text="Encrypting...", text_color=Colors.AMBER)
            self.update_idletasks()

            result = encrypt_image(self._selected_image_path, output_dir)

            # Show encrypted (white) image preview
            self._show_result_preview(result['actual_path'], "Encrypted (white image)")

            # Update result text
            output_text = (
                f"✓ Image Encrypted Successfully\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Original:     {result['original']}\n"
                f"Encrypted:    {result['filename']}\n"
                f"Dimensions:   {result['dimensions']}\n"
                f"Pixels:       {result['pixels']:,}\n"
                f"Output size:  {result['size_kb']} KB\n"
                f"Time:         {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠ Keep .png + .meta together!"
            )

            self.image_result_text.configure(state="normal")
            self.image_result_text.delete("1.0", "end")
            self.image_result_text.insert("1.0", output_text)
            self.image_result_text.configure(state="disabled")

            self.image_status.configure(
                text=f"✓ Encrypted → {result['filename']}  ·  {datetime.now().strftime('%H:%M:%S')}",
                text_color=Colors.EMERALD,
            )

            self.user_manager.log_operation(
                operation="encrypt_image",
                input_preview=result['original'],
                input_size=result['pixels'],
                output_size=int(float(result['size_kb']) * 1024),
                status="success",
                details=f"{result['dimensions']} → {result['filename']}",
            )
            self._update_sidebar_stats()

        except ValueError as e:
            self.image_status.configure(text=f"✗ {str(e)}", text_color=Colors.ROSE)
            self.result_preview_label.configure(image=None, text="Encryption failed")
            self.user_manager.log_operation(
                operation="encrypt_image", status="error", details=str(e),
            )

    def _do_decrypt_image(self):
        """Decrypt an encrypted image."""
        path = filedialog.askopenfilename(
            title="Select encrypted image (.png file)",
            filetypes=[
                ("Encrypted images", "*.png"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        output_dir = filedialog.askdirectory(title="Select output folder for decrypted image")
        if not output_dir:
            return

        try:
            self.image_status.configure(text="Decrypting...", text_color=Colors.AMBER)
            self.update_idletasks()

            result = decrypt_image(path, output_dir)

            # Show restored image preview
            self._show_result_preview(result['actual_path'], "Decrypted image")

            # Also show it in the main preview
            self._show_image_preview(result['actual_path'])

            output_text = (
                f"✓ Image Decrypted Successfully\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Restored:     {result['filename']}\n"
                f"Original:     {result['original']}\n"
                f"Dimensions:   {result['dimensions']}\n"
                f"Pixels:       {result['pixels']:,}\n"
                f"Output size:  {result['size_kb']} KB\n"
                f"Time:         {datetime.now().strftime('%H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✓ Colors & filename restored!"
            )

            self.image_result_text.configure(state="normal")
            self.image_result_text.delete("1.0", "end")
            self.image_result_text.insert("1.0", output_text)
            self.image_result_text.configure(state="disabled")

            self.image_status.configure(
                text=f"✓ Decrypted → {result['filename']}  ·  {datetime.now().strftime('%H:%M:%S')}",
                text_color=Colors.EMERALD,
            )

            self.user_manager.log_operation(
                operation="decrypt_image",
                input_preview=os.path.basename(path),
                input_size=result['pixels'],
                output_size=int(float(result['size_kb']) * 1024),
                status="success",
                details=f"{result['dimensions']} → {result['filename']}",
            )
            self._update_sidebar_stats()

        except ValueError as e:
            self.image_status.configure(text=f"✗ {str(e)}", text_color=Colors.ROSE)
            self.result_preview_label.configure(image=None, text="Decryption failed")
            self.user_manager.log_operation(
                operation="decrypt_image", status="error", details=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════════════
    #  PROFILE ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_username(self):
        """Save updated username."""
        name = self.username_entry.get().strip()
        if not name:
            messagebox.showwarning("Invalid Name", "Please enter a display name.")
            return

        self.user_manager.save_username(name)
        self.user_badge_label.configure(text=f"  👤 {name}  ")
        messagebox.showinfo("Saved", f"Display name updated to: {name}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _make_card(self, parent, title: str, accent_color: str, row: int, col: int):
        """Create a styled card frame with title."""
        outer = ctk.CTkFrame(
            parent, fg_color=Colors.BG_CARD, corner_radius=16,
            border_width=1, border_color=Colors.BORDER_DIM,
        )
        outer.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Title bar
        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=accent_color, anchor="w",
        ).grid(row=0, column=0, padx=20, pady=(16, 12), sticky="w")

        # Content area
        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        return content

    def _copy_output(self, textbox: ctk.CTkTextbox):
        """Copy textbox content to clipboard."""
        textbox.configure(state="normal")
        text = textbox.get("1.0", "end-1c").strip()
        textbox.configure(state="disabled")

        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.text_status.configure(
                text=f"📋 Copied to clipboard  ·  {datetime.now().strftime('%H:%M:%S')}",
                text_color=Colors.VIOLET,
            )

    def _update_enc_count(self, event=None):
        """Update character count for encrypt input."""
        text = self.enc_input.get("1.0", "end-1c")
        self.enc_char_count.configure(text=f"{len(text)} characters")

    def _update_dec_count(self, event=None):
        """Update token count for decrypt input."""
        text = self.dec_input.get("1.0", "end-1c").strip()
        tokens = text.split(chr(1)) if text else []
        self.dec_char_count.configure(text=f"{len(tokens)} tokens")

    def _start_clock(self):
        """Start the live clock in the sidebar."""
        def tick():
            if self._clock_running:
                now = datetime.now().strftime("%a %b %d  %H:%M:%S")
                self.clock_label.configure(text=f"🕐 {now}")
                self.after(1000, tick)
        tick()

    def destroy(self):
        """Clean shutdown."""
        self._clock_running = False
        super().destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = CipherVaultApp()
    app.mainloop()
