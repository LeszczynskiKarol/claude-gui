#!/usr/bin/env python3
"""
Claude GUI Assistant - Rozbudowany interfejs graficzny z pełnymi statystykami
Autor: Assistant
"""

import os
import sys
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font
import customtkinter as ctk
from anthropic import Anthropic
from dotenv import load_dotenv

# Ustaw tryb wyglądu customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Ładowanie zmiennych środowiskowych
load_dotenv()

try:
    from claude_gui_db_panel import DatabaseHistoryPanel
    from claude_db_extension import DatabaseManager
    DB_AVAILABLE = True
    print("[DB] ✅ Moduły bazy danych załadowane!")
except ImportError as e:
    DB_AVAILABLE = False
    print(f"[DB] ❌ Brak modułów bazy: {e}")


@dataclass
class ModelConfig:
    """Pełna konfiguracja modelu Claude"""
    id: str
    name: str
    description: str
    strengths: str
    max_output_tokens: int
    context_window: str
    latency: str
    vision: bool = True
    multilingual: bool = True
    extended_thinking: bool = False
    priority_tier: bool = False
    training_cutoff: str = ""
    # Koszty (w $ za milion tokenów)
    input_cost: float = 0.0
    output_cost: float = 0.0
    # Extended Thinking settings
    default_thinking_enabled: bool = False
    default_thinking_budget: int = 10000
    max_thinking_budget: int = 32000

# Pełna konfiguracja wszystkich modeli
MODELS = {
    "opus-4.1": ModelConfig(
        id="claude-opus-4-1-20250805",
        name="Claude Opus 4.1",
        description="Nasz najbardziej zaawansowany model",
        strengths="Najwyższy poziom inteligencji i możliwości",
        max_output_tokens=32000,
        context_window="200K",
        latency="Umiarkowanie szybki",
        extended_thinking=True,
        priority_tier=True,
        training_cutoff="Mar 2025",
        input_cost=15.0,
        output_cost=75.0,
        default_thinking_enabled=True,  # Domyślnie włączone dla Opus 4.1
        default_thinking_budget=16000,
        max_thinking_budget=32000
    ),
    "opus-4": ModelConfig(
        id="claude-opus-4-20240229",
        name="Claude Opus 4",
        description="Poprzedni flagowy model",
        strengths="Bardzo wysoka inteligencja i możliwości",
        max_output_tokens=32000,
        context_window="200K",
        latency="Umiarkowanie szybki",
        extended_thinking=True,
        priority_tier=True,
        training_cutoff="Mar 2025",
        input_cost=12.0,
        output_cost=60.0
    ),
    "sonnet-4": ModelConfig(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        description="Model o wysokiej wydajności",
        strengths="Wysoka inteligencja i zbalansowana wydajność",
        max_output_tokens=64000,
        context_window="200K / 1M (beta)",
        latency="Szybki",
        extended_thinking=True,
        priority_tier=True,
        training_cutoff="Mar 2025",
        input_cost=3.0,
        output_cost=15.0
    ),
    "sonnet-3.7": ModelConfig(
        id="claude-sonnet-3.7-20241029",
        name="Claude Sonnet 3.7",
        description="Model z rozszerzonym myśleniem",
        strengths="Wysoka inteligencja z przełączalnym rozszerzonym myśleniem",
        max_output_tokens=64000,
        context_window="200K",
        latency="Szybki",
        extended_thinking=True,
        priority_tier=True,
        training_cutoff="Nov 2024",
        input_cost=3.0,
        output_cost=15.0
    ),
    "haiku-3.5": ModelConfig(
        id="claude-3-5-haiku-20241022",
        name="Claude Haiku 3.5",
        description="Nasz najszybszy model",
        strengths="Inteligencja w błyskawicznej prędkości",
        max_output_tokens=8192,
        context_window="200K",
        latency="Najszybszy",
        extended_thinking=False,
        priority_tier=True,
        training_cutoff="July 2024",
        input_cost=1.0,
        output_cost=5.0
    ),
    "haiku-3": ModelConfig(
        id="claude-3-haiku-20240307",
        name="Claude Haiku 3",
        description="Szybki i kompaktowy model",
        strengths="Szybka i dokładna wydajność",
        max_output_tokens=4096,
        context_window="200K",
        latency="Szybki",
        extended_thinking=False,
        priority_tier=False,
        training_cutoff="Aug 2023",
        input_cost=0.25,
        output_cost=1.25
    )
}

class TokenStats:
    """Klasa do śledzenia statystyk tokenów"""
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.session_cost = 0.0
        self.messages_count = 0
        
    def add_usage(self, input_tokens: int, output_tokens: int, model: ModelConfig):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.messages_count += 1
        
        # Oblicz koszt (ceny są za milion tokenów)
        input_cost = (input_tokens / 1_000_000) * model.input_cost
        output_cost = (output_tokens / 1_000_000) * model.output_cost
        self.session_cost += input_cost + output_cost
        
        return input_cost + output_cost

class ClaudeGUIAssistant:
    """Główna klasa aplikacji GUI"""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Claude GUI Assistant - Zaawansowany interfejs")
        self.root.geometry("1400x900")
        
        # Lista wszystkich widgetów do aktualizacji czcionki (musi być przed apply_global_font)
        self.all_widgets = []
        
        # Konfiguracja czcionek
        self.load_font_preferences()
        # apply_global_font będzie wywołane po zbudowaniu UI
        
        # API i konfiguracja
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.current_model = MODELS["sonnet-4"]
        self.conversation_history = []
        self.token_stats = TokenStats()
        self.system_prompt = "Jesteś pomocnym asystentem AI."
        
        # Ustawienie ikon i stylów
        self.setup_styles()
        
        # Budowanie interfejsu
        self.build_ui()
        
        # Zastosuj czcionki po zbudowaniu UI
        self.apply_global_font()
        
        # Sprawdź API key
        self.check_api_key()
    
    def start_new_conversation(self):
        """Rozpoczyna nową rozmowę"""
        if self.conversation_history:
            if messagebox.askyesno("Nowa rozmowa", "Czy chcesz rozpocząć nową rozmowę?\n(Obecna zostanie zachowana w bazie)"):
                # Wyczyść wszystko
                self.conversation_history.clear()
                self.chat_display.delete("1.0", "end")
                self.history_listbox.delete(0, tk.END)
                self.token_stats = TokenStats()
                self.update_statistics(0)
                
                # Resetuj ID rozmowy
                if hasattr(self, 'current_conversation_id'):
                    self.current_conversation_id = None
                
                # Odśwież listę w bazie jeśli jest
                if hasattr(self, 'db_panel') and hasattr(self.db_panel, 'load_conversations'):
                    self.db_panel.load_conversations()
                
                self.update_status("🆕 Rozpoczęto nową rozmowę", "success")
        else:
            self.update_status("Już jesteś w nowej rozmowie", "normal")

    def load_font_preferences(self):
        """Ładuje preferencje czcionki z pliku konfiguracyjnego"""
        self.font_config_file = "font_preferences.json"
        default_config = {
            "family": "Arial",
            "size": 12,
            "chat_family": "Consolas",
            "chat_size": 11
        }
        
        try:
            if os.path.exists(self.font_config_file):
                with open(self.font_config_file, 'r') as f:
                    config = json.load(f)
                    self.current_font_family = config.get("family", default_config["family"])
                    self.current_font_size = config.get("size", default_config["size"])
                    self.chat_font_family = config.get("chat_family", default_config["chat_family"])
                    self.chat_font_size = config.get("chat_size", default_config["chat_size"])
            else:
                self.current_font_family = default_config["family"]
                self.current_font_size = default_config["size"]
                self.chat_font_family = default_config["chat_family"]
                self.chat_font_size = default_config["chat_size"]
        except:
            self.current_font_family = default_config["family"]
            self.current_font_size = default_config["size"]
            self.chat_font_family = default_config["chat_family"]
            self.chat_font_size = default_config["chat_size"]
    
    def save_font_preferences(self):
        """Zapisuje preferencje czcionki do pliku"""
        config = {
            "family": self.current_font_family,
            "size": self.current_font_size,
            "chat_family": self.chat_font_family,
            "chat_size": self.chat_font_size
        }
        with open(self.font_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def apply_global_font(self):
        """Aplikuje globalną czcionkę do wszystkich widgetów"""
        # Zaktualizuj czcionkę dla wszystkich zarejestrowanych widgetów
        for widget_info in self.all_widgets:
            widget, widget_type = widget_info
            try:
                if widget.winfo_exists():
                    if widget_type == "chat":
                        widget.configure(font=(self.chat_font_family, self.chat_font_size))
                    elif widget_type == "title":
                        widget.configure(font=(self.current_font_family, int(self.current_font_size * 1.5), "bold"))
                    elif widget_type == "header":
                        widget.configure(font=(self.current_font_family, int(self.current_font_size * 1.2), "bold"))
                    elif widget_type == "button":
                        widget.configure(font=(self.current_font_family, self.current_font_size, "bold"))
                    else:
                        widget.configure(font=(self.current_font_family, self.current_font_size))
            except:
                pass
    
    def register_widget(self, widget, widget_type="normal"):
        """Rejestruje widget do globalnej aktualizacji czcionki"""
        self.all_widgets.append((widget, widget_type))
        # Zastosuj odpowiednią czcionkę od razu
        try:
            if widget_type == "chat":
                widget.configure(font=(self.chat_font_family, self.chat_font_size))
            elif widget_type == "title":
                widget.configure(font=(self.current_font_family, int(self.current_font_size * 1.5), "bold"))
            elif widget_type == "header":
                widget.configure(font=(self.current_font_family, int(self.current_font_size * 1.2), "bold"))
            elif widget_type == "button":
                widget.configure(font=(self.current_font_family, self.current_font_size, "bold"))
            else:
                widget.configure(font=(self.current_font_family, self.current_font_size))
        except:
            pass
        
    def setup_styles(self):
        """Konfiguracja stylów aplikacji"""
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#0084ff',
            'success': '#00d26a',
            'warning': '#ffa500',
            'error': '#ff4444'
        }
        
    def check_api_key(self):
        """Sprawdza i konfiguruje klucz API"""
        if not self.api_key:
            self.show_api_key_dialog()
        else:
            self.client = Anthropic(api_key=self.api_key)
            self.update_status("✅ API połączone", "success")
            
    def show_api_key_dialog(self):
        """Dialog do wprowadzenia klucza API"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Konfiguracja API")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="Wprowadź klucz API Anthropic",
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text="Pobierz klucz z: https://console.anthropic.com/",
            font=("Arial", 12)
        ).pack(pady=5)
        
        api_entry = ctk.CTkEntry(
            dialog,
            width=400,
            placeholder_text="sk-ant-api03-...",
            show="*"
        )
        api_entry.pack(pady=20)
        
        def save_api_key():
            key = api_entry.get()
            if key.startswith("sk-ant-"):
                self.api_key = key
                self.client = Anthropic(api_key=self.api_key)
                
                # Zapisz do .env
                with open('.env', 'w') as f:
                    f.write(f"ANTHROPIC_API_KEY={key}\n")
                
                self.update_status("✅ API połączone", "success")
                dialog.destroy()
            else:
                messagebox.showerror("Błąd", "Nieprawidłowy format klucza API")
        
        ctk.CTkButton(
            dialog,
            text="Zapisz",
            command=save_api_key
        ).pack(pady=10)
        
    def build_ui(self):
        """Buduje główny interfejs użytkownika"""
        # Główny kontener
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Lewa kolumna - Panel kontrolny
        self.build_control_panel(main_container)
        
        # Prawa kolumna - Chat
        self.build_chat_panel(main_container)
        
        # Dolny panel - Statystyki
        self.build_stats_panel()
        
    def build_control_panel(self, parent):
        """Buduje lewy panel kontrolny"""
        control_frame = ctk.CTkFrame(parent, width=400)
        control_frame.pack(side="left", fill="both", padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # Tytuł
        title_label = ctk.CTkLabel(
            control_frame,
            text="Panel kontrolny",
            font=(self.current_font_family, int(self.current_font_size * 1.5), "bold")
        )
        title_label.pack(pady=10)
        self.register_widget(title_label, "title")
        
        # Wybór modelu
        model_frame = ctk.CTkFrame(control_frame)
        model_frame.pack(fill="x", padx=10, pady=10)
        
        model_label = ctk.CTkLabel(
            model_frame,
            text="Aktywny model:",
            font=(self.current_font_family, int(self.current_font_size * 1.2), "bold")
        )
        model_label.pack(anchor="w", padx=10, pady=5)
        self.register_widget(model_label, "header")
        
        self.model_var = tk.StringVar(value="sonnet-4")
        model_dropdown = ctk.CTkOptionMenu(
            model_frame,
            variable=self.model_var,
            values=list(MODELS.keys()),
            command=self.change_model,
            width=350,
            font=(self.current_font_family, self.current_font_size)
        )
        model_dropdown.pack(padx=10, pady=5)
        self.register_widget(model_dropdown)
        
        # Informacje o modelu
        self.model_info_frame = ctk.CTkFrame(model_frame)
        self.model_info_frame.pack(fill="x", padx=10, pady=10)
        self.update_model_info()
        
        # Tabbed view dla dodatkowych opcji - ZAPISZ JAKO ATRYBUT KLASY!
        self.tabview = ctk.CTkTabview(control_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab: Porównanie modeli
        self.build_comparison_tab(self.tabview.add("Porównanie"))
        
        # Tab: Ustawienia
        self.build_settings_tab(self.tabview.add("Ustawienia"))
        
        # Tab: Historia
        self.build_history_tab(self.tabview.add("Historia"))
        
        # MIEJSCE NA DODATKOWĄ ZAKŁADKĘ BAZY DANYCH
        
    def build_comparison_tab(self, parent):
        """Buduje tabelę porównawczą modeli"""
        # ScrolledFrame dla tabeli
        canvas = tk.Canvas(parent, bg='#212121', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Nagłówek tabeli
        headers = ["Cecha", "Opus 4.1", "Opus 4", "Sonnet 4", "Sonnet 3.7", "Haiku 3.5", "Haiku 3"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                scrollable_frame,
                text=header,
                font=(self.current_font_family, int(self.current_font_size * 0.95), "bold"),
                width=100
            )
            label.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
            self.register_widget(label)
        
        # Dane do tabeli
        features = [
            ("Max output", "32K", "32K", "64K", "64K", "8K", "4K"),
            ("Context", "200K", "200K", "200K/1M", "200K", "200K", "200K"),
            ("Latencja", "Średnia", "Średnia", "Szybka", "Szybka", "Najszybsza", "Szybka"),
            ("Vision", "✅", "✅", "✅", "✅", "✅", "✅"),
            ("Extended", "✅", "✅", "✅", "✅", "❌", "❌"),
            ("Priority", "✅", "✅", "✅", "✅", "✅", "❌"),
            ("$/1M in", "$15", "$12", "$3", "$3", "$1", "$0.25"),
            ("$/1M out", "$75", "$60", "$15", "$15", "$5", "$1.25"),
        ]
        
        for row_idx, feature_data in enumerate(features, 1):
            for col_idx, value in enumerate(feature_data):
                # Kolorowanie dla różnych wartości
                fg_color = None
                if value == "✅":
                    fg_color = ("#00d26a", "#00a050")
                elif value == "❌":
                    fg_color = ("#ff4444", "#cc0000")
                elif "$" in value:
                    fg_color = ("#ffa500", "#ff8800")
                    
                label = ctk.CTkLabel(
                    scrollable_frame,
                    text=value,
                    font=(self.current_font_family, int(self.current_font_size * 0.9)),
                    width=100,
                    fg_color=fg_color
                )
                label.grid(row=row_idx, column=col_idx, padx=2, pady=2, sticky="ew")
                self.register_widget(label)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def build_settings_tab(self, parent):
        """Buduje zakładkę z ustawieniami"""
        settings_frame = ctk.CTkScrollableFrame(parent)
        settings_frame.pack(fill="both", expand=True)
        
        # SEKCJA: Czcionki
        font_section_label = ctk.CTkLabel(
            settings_frame,
            text="Ustawienia czcionek:",
            font=(self.current_font_family, int(self.current_font_size * 1.3), "bold")
        )
        font_section_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.register_widget(font_section_label, "header")
        
        font_frame = ctk.CTkFrame(settings_frame)
        font_frame.pack(fill="x", padx=10, pady=10)
        
        # SEKCJA: Extended Thinking
        thinking_section_label = ctk.CTkLabel(
            settings_frame,
            text="Extended Thinking (Rozszerzone myślenie):",
            font=(self.current_font_family, int(self.current_font_size * 1.3), "bold")
        )
        thinking_section_label.pack(anchor="w", padx=10, pady=(20, 5))
        self.register_widget(thinking_section_label, "header")
        
        thinking_frame = ctk.CTkFrame(settings_frame)
        thinking_frame.pack(fill="x", padx=10, pady=10)
        
        # Włącznik Extended Thinking
        self.thinking_enabled_var = tk.BooleanVar(
            value=self.current_model.default_thinking_enabled
        )
        thinking_checkbox = ctk.CTkCheckBox(
            thinking_frame,
            text="Włącz Extended Thinking",
            variable=self.thinking_enabled_var,
            font=(self.current_font_family, self.current_font_size),
            command=self.toggle_thinking
        )
        thinking_checkbox.pack(anchor="w", padx=10, pady=5)
        self.register_widget(thinking_checkbox)
        
        # Budżet tokenów dla Extended Thinking
        budget_label = ctk.CTkLabel(
            thinking_frame,
            text="Budżet tokenów myślenia (1024 - 32000):",
            font=(self.current_font_family, self.current_font_size)
        )
        budget_label.pack(anchor="w", padx=10, pady=5)
        self.register_widget(budget_label)
        
        self.thinking_budget_var = tk.IntVar(
            value=self.current_model.default_thinking_budget if self.current_model.extended_thinking else 10000
        )
        
        budget_slider = ctk.CTkSlider(
            thinking_frame,
            from_=1024,
            to=self.current_model.max_thinking_budget if self.current_model.extended_thinking else 32000,
            variable=self.thinking_budget_var,
            width=350,
            command=lambda v: self.update_thinking_budget_label()
        )
        budget_slider.pack(padx=10, pady=5)
        
        self.thinking_budget_label = ctk.CTkLabel(
            thinking_frame,
            text=f"Budżet: {self.thinking_budget_var.get()} tokenów",
            font=(self.current_font_family, self.current_font_size)
        )
        self.thinking_budget_label.pack()
        self.register_widget(self.thinking_budget_label)
        
        # Informacja o Extended Thinking
        info_text = ctk.CTkLabel(
            thinking_frame,
            text="💡 Extended Thinking pozwala Claude'owi na głębszą analizę\nproblemów przed udzieleniem odpowiedzi.\n⚠️ Zwiększa czas odpowiedzi, ale poprawia jakość.",
            font=(self.current_font_family, int(self.current_font_size * 0.9)),
            justify="left"
        )
        info_text.pack(anchor="w", padx=10, pady=10)
        self.register_widget(info_text)


        # Wybór czcionki głównej
        font_main_label = ctk.CTkLabel(
            font_frame,
            text="Czcionka główna:",
            font=(self.current_font_family, self.current_font_size)
        )
        font_main_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.register_widget(font_main_label)
        
        # Lista dostępnych czcionek
        available_fonts = sorted(font.families())
        common_fonts = ["Arial", "Helvetica", "Times New Roman", "Verdana", "Tahoma", 
                        "Trebuchet MS", "Georgia", "Segoe UI", "Calibri", "Consolas",
                        "Courier New", "Comic Sans MS", "Impact", "Lucida Console"]
        
        # Filtruj tylko popularne czcionki + te zainstalowane
        font_list = [f for f in common_fonts if f in available_fonts]
        
        self.font_family_var = tk.StringVar(value=self.current_font_family)
        font_dropdown = ctk.CTkOptionMenu(
            font_frame,
            variable=self.font_family_var,
            values=font_list,
            width=200,
            font=(self.current_font_family, self.current_font_size)
        )
        font_dropdown.grid(row=0, column=1, padx=10, pady=5)
        self.register_widget(font_dropdown)
        
        # Rozmiar czcionki głównej
        size_main_label = ctk.CTkLabel(
            font_frame,
            text="Rozmiar (px):",
            font=(self.current_font_family, self.current_font_size)
        )
        size_main_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.register_widget(size_main_label)
        
        self.font_size_var = tk.IntVar(value=self.current_font_size)
        size_spinbox = ctk.CTkEntry(
            font_frame,
            width=80,
            textvariable=self.font_size_var,
            font=(self.current_font_family, self.current_font_size)
        )
        size_spinbox.grid(row=0, column=3, padx=10, pady=5)
        self.register_widget(size_spinbox)
        
        # Czcionka czatu
        chat_font_label = ctk.CTkLabel(
            font_frame,
            text="Czcionka czatu:",
            font=(self.current_font_family, self.current_font_size)
        )
        chat_font_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.register_widget(chat_font_label)
        
        # Lista czcionek monospace dla czatu
        monospace_fonts = ["Consolas", "Courier New", "Lucida Console", "Monaco", 
                          "Menlo", "Source Code Pro", "Fira Code", "Cascadia Code"]
        chat_font_list = [f for f in monospace_fonts if f in available_fonts]
        
        self.chat_font_family_var = tk.StringVar(value=self.chat_font_family)
        chat_font_dropdown = ctk.CTkOptionMenu(
            font_frame,
            variable=self.chat_font_family_var,
            values=chat_font_list,
            width=200,
            font=(self.current_font_family, self.current_font_size)
        )
        chat_font_dropdown.grid(row=1, column=1, padx=10, pady=5)
        self.register_widget(chat_font_dropdown)
        
        # Rozmiar czcionki czatu
        chat_size_label = ctk.CTkLabel(
            font_frame,
            text="Rozmiar (px):",
            font=(self.current_font_family, self.current_font_size)
        )
        chat_size_label.grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.register_widget(chat_size_label)
        
        self.chat_font_size_var = tk.IntVar(value=self.chat_font_size)
        chat_size_spinbox = ctk.CTkEntry(
            font_frame,
            width=80,
            textvariable=self.chat_font_size_var,
            font=(self.current_font_family, self.current_font_size)
        )
        chat_size_spinbox.grid(row=1, column=3, padx=10, pady=5)
        self.register_widget(chat_size_spinbox)
        
        # Suwak dla szybkiej zmiany rozmiaru
        scale_label = ctk.CTkLabel(
            font_frame,
            text="Szybka zmiana rozmiaru głównego:",
            font=(self.current_font_family, self.current_font_size)
        )
        scale_label.grid(row=2, column=0, columnspan=2, padx=10, pady=(15, 5), sticky="w")
        self.register_widget(scale_label)
        
        font_scale_slider = ctk.CTkSlider(
            font_frame,
            from_=8,
            to=24,
            variable=self.font_size_var,
            width=300,
            command=lambda v: self.preview_font_change()
        )
        font_scale_slider.grid(row=3, column=0, columnspan=3, padx=10, pady=5)
        
        self.font_size_label = ctk.CTkLabel(
            font_frame,
            text=f"{self.font_size_var.get()} px",
            font=(self.current_font_family, self.current_font_size)
        )
        self.font_size_label.grid(row=3, column=3, padx=10, pady=5)
        self.register_widget(self.font_size_label)
        
        # Przyciski akcji
        button_frame = ctk.CTkFrame(font_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=(15, 5))
        
        apply_button = ctk.CTkButton(
            button_frame,
            text="Zastosuj czcionki",
            command=self.apply_font_changes,
            width=150,
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        apply_button.pack(side="left", padx=5)
        self.register_widget(apply_button, "button")
        
        reset_button = ctk.CTkButton(
            button_frame,
            text="Resetuj domyślne",
            command=self.reset_default_fonts,
            width=150,
            fg_color="#666666",
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        reset_button.pack(side="left", padx=5)
        self.register_widget(reset_button, "button")
        
        # Przycisk testowy do natychmiastowego odświeżania
        test_button = ctk.CTkButton(
            button_frame,
            text="Test czatu",
            command=self.test_chat_font,
            width=100,
            fg_color="#ff8800",
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        test_button.pack(side="left", padx=5)
        self.register_widget(test_button, "button")
        
        # Podgląd czcionki
        preview_frame = ctk.CTkFrame(settings_frame)
        preview_frame.pack(fill="x", padx=10, pady=10)
        
        preview_label = ctk.CTkLabel(
            preview_frame,
            text="Podgląd czcionki:",
            font=(self.current_font_family, int(self.current_font_size * 1.1), "bold")
        )
        preview_label.pack(anchor="w", padx=10, pady=5)
        self.register_widget(preview_label, "header")
        
        self.preview_text = ctk.CTkLabel(
            preview_frame,
            text="Przykładowy tekst - The quick brown fox jumps over the lazy dog\n1234567890 !@#$%^&*()",
            font=(self.current_font_family, self.current_font_size)
        )
        self.preview_text.pack(padx=10, pady=10)
        self.register_widget(self.preview_text)
        
        # Separator
        separator = ttk.Separator(settings_frame, orient='horizontal')
        separator.pack(fill='x', padx=10, pady=20)
        
        # SEKCJA: System Prompt (poprzednia)
        system_label = ctk.CTkLabel(
            settings_frame,
            text="System Prompt:",
            font=(self.current_font_family, int(self.current_font_size * 1.3), "bold")
        )
        system_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.register_widget(system_label, "header")
        
        self.system_prompt_text = ctk.CTkTextbox(
            settings_frame,
            height=100,
            width=350,
            font=(self.chat_font_family, self.chat_font_size)
        )
        self.system_prompt_text.pack(padx=10, pady=5)
        self.system_prompt_text.insert("1.0", self.system_prompt)
        self.register_widget(self.system_prompt_text, "chat")
        
        def update_system_prompt():
            self.system_prompt = self.system_prompt_text.get("1.0", "end-1c")
            self.update_status("System prompt zaktualizowany", "success")
        
        update_prompt_button = ctk.CTkButton(
            settings_frame,
            text="Zaktualizuj System Prompt",
            command=update_system_prompt,
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        update_prompt_button.pack(pady=10)
        self.register_widget(update_prompt_button, "button")
        
        # Parametry modelu
        params_label = ctk.CTkLabel(
            settings_frame,
            text="Parametry generowania:",
            font=(self.current_font_family, int(self.current_font_size * 1.3), "bold")
        )
        params_label.pack(anchor="w", padx=10, pady=(20, 5))
        self.register_widget(params_label, "header")
        
        # Temperature
        temp_label = ctk.CTkLabel(
            settings_frame,
            text="Temperature (0.0 - 1.0):",
            font=(self.current_font_family, self.current_font_size)
        )
        temp_label.pack(anchor="w", padx=10, pady=5)
        self.register_widget(temp_label)
        
        self.temperature_var = tk.DoubleVar(value=0.7)
        temperature_slider = ctk.CTkSlider(
            settings_frame,
            from_=0,
            to=1,
            variable=self.temperature_var,
            width=350
        )
        temperature_slider.pack(padx=10, pady=5)
        
        self.temp_label = ctk.CTkLabel(
            settings_frame,
            text=f"Wartość: {self.temperature_var.get():.2f}",
            font=(self.current_font_family, self.current_font_size)
        )
        self.temp_label.pack()
        self.register_widget(self.temp_label)
        
        def update_temp_label(value):
            self.temp_label.configure(text=f"Wartość: {value:.2f}")
        
        temperature_slider.configure(command=update_temp_label)
    
    def preview_font_change(self):
        """Aktualizuje podgląd czcionki w czasie rzeczywistym"""
        size = self.font_size_var.get()
        self.font_size_label.configure(text=f"{size} px")
        self.preview_text.configure(font=(self.font_family_var.get(), size))
    
    def test_chat_font(self):
        """Testuje czcionkę w oknie czatu"""
        # Pobierz aktualne wartości
        new_chat_family = self.chat_font_family_var.get()
        new_chat_size = self.chat_font_size_var.get()
        
        # Wymuś odświeżenie czcionki w głównym oknie czatu
        try:
            # tk.Text używa configure do zmiany czcionki
            new_font = (new_chat_family, new_chat_size)
            self.chat_display.configure(font=new_font)
            self.input_text.configure(font=new_font)
            
            # Dodaj testową wiadomość z tagiem
            test_message = f"[TEST] Czcionka zmieniona na: {new_chat_family} {new_chat_size}px"
            self.chat_display.insert("end", f"\n{test_message}\n", "test")
            self.chat_display.tag_config("test", foreground="#ffa500", font=new_font)
            self.chat_display.see("end")
            
            print(f"[SUCCESS] Zmieniono czcionkę czatu na: {new_chat_family} {new_chat_size}px")
            self.update_status(f"Test OK: {new_chat_family} {new_chat_size}px", "success")
        except Exception as e:
            print(f"[ERROR] Błąd zmiany czcionki: {e}")
            self.update_status(f"Błąd: {e}", "error")
    
    def force_refresh_all_fonts(self):
        """Wymusza odświeżenie wszystkich czcionek w aplikacji"""
        print(f"[REFRESH] Wymuszam odświeżenie czcionek...")
        
        # Odśwież główne okno czatu (tk.Text)
        if hasattr(self, 'chat_display'):
            try:
                new_font = (self.chat_font_family, self.chat_font_size)
                self.chat_display.configure(font=new_font)
                print(f"[SUCCESS] chat_display: {self.chat_font_family} {self.chat_font_size}px")
            except Exception as e:
                print(f"[ERROR] chat_display: {e}")
        
        if hasattr(self, 'input_text'):
            try:
                new_font = (self.chat_font_family, self.chat_font_size)
                self.input_text.configure(font=new_font)
                print(f"[SUCCESS] input_text: {self.chat_font_family} {self.chat_font_size}px")
            except Exception as e:
                print(f"[ERROR] input_text: {e}")
        
        # Odśwież system prompt (jeśli to też tk.Text)
        if hasattr(self, 'system_prompt_text'):
            try:
                # Sprawdź czy to tk.Text czy CTkTextbox
                if isinstance(self.system_prompt_text, tk.Text):
                    self.system_prompt_text.configure(font=(self.chat_font_family, self.chat_font_size))
                else:
                    # CTkTextbox - może nie działać
                    self.system_prompt_text.configure(font=(self.chat_font_family, self.chat_font_size))
            except Exception as e:
                print(f"[WARNING] system_prompt_text: {e}")
        
        if hasattr(self, 'history_listbox'):
            try:
                self.history_listbox.configure(font=(self.current_font_family, int(self.current_font_size * 0.9)))
            except:
                pass
        
        # Odśwież wszystkie zarejestrowane widgety
        self.apply_global_font()
        
        print(f"[REFRESH] Odświeżanie zakończone")
    
    def apply_font_changes(self):
        """Aplikuje zmiany czcionek do całej aplikacji"""
        # Zapisz nowe wartości
        self.current_font_family = self.font_family_var.get()
        self.current_font_size = self.font_size_var.get()
        self.chat_font_family = self.chat_font_family_var.get()
        self.chat_font_size = self.chat_font_size_var.get()
        
        print(f"[DEBUG] Zapisuję nowe ustawienia czcionek:")
        print(f"  - Główna: {self.current_font_family} {self.current_font_size}px")
        print(f"  - Czat: {self.chat_font_family} {self.chat_font_size}px")
        
        # Zapisz do pliku
        self.save_font_preferences()
        
        # Wymuś pełne odświeżenie
        self.force_refresh_all_fonts()
        
        # Odśwież informacje o modelu
        self.update_model_info()
        
        self.update_status(f"Czcionki zaktualizowane: {self.current_font_family} {self.current_font_size}px | Czat: {self.chat_font_family} {self.chat_font_size}px", "success")
    
    def reset_default_fonts(self):
        """Resetuje czcionki do domyślnych wartości"""
        self.font_family_var.set("Arial")
        self.font_size_var.set(12)
        self.chat_font_family_var.set("Consolas")
        self.chat_font_size_var.set(11)
        
        self.apply_font_changes()
        self.update_status("Czcionki zresetowane do domyślnych", "success")
        
    def build_history_tab(self, parent):
        """Buduje zakładkę z historią rozmów"""
        history_frame = ctk.CTkScrollableFrame(parent)
        history_frame.pack(fill="both", expand=True)
        
        history_label = ctk.CTkLabel(
            history_frame,
            text="Historia sesji:",
            font=(self.current_font_family, int(self.current_font_size * 1.2), "bold")
        )
        history_label.pack(anchor="w", padx=10, pady=10)
        self.register_widget(history_label, "header")
        
        # Przyciski akcji
        button_frame = ctk.CTkFrame(history_frame)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        save_button = ctk.CTkButton(
            button_frame,
            text="Zapisz historię",
            command=self.save_conversation,
            width=100,
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        save_button.pack(side="left", padx=5)
        self.register_widget(save_button, "button")
        
        load_button = ctk.CTkButton(
            button_frame,
            text="Wczytaj historię",
            command=self.load_conversation,
            width=100,
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        load_button.pack(side="left", padx=5)
        self.register_widget(load_button, "button")
        
        clear_button = ctk.CTkButton(
            button_frame,
            text="Wyczyść",
            command=self.clear_history,
            width=100,
            fg_color="#ff4444",
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        clear_button.pack(side="left", padx=5)
        self.register_widget(clear_button, "button")
        
        # Lista wiadomości
        self.history_listbox = tk.Listbox(
            history_frame,
            height=15,
            bg='#2b2b2b',
            fg='white',
            selectbackground='#0084ff',
            font=(self.current_font_family, int(self.current_font_size * 0.9))
        )
        self.history_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
    def build_chat_panel(self, parent):
        """Buduje główny panel czatu"""
        chat_frame = ctk.CTkFrame(parent)
        chat_frame.pack(side="right", fill="both", expand=True)
        
        # Nagłówek czatu
        header = ctk.CTkFrame(chat_frame, height=60)
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        self.chat_title = ctk.CTkLabel(
            header,
            text=f"Czat z {self.current_model.name}",
            font=(self.current_font_family, int(self.current_font_size * 1.5), "bold")
        )
        self.chat_title.pack(side="left", padx=10)
        self.register_widget(self.chat_title, "title")
        
        self.status_label = ctk.CTkLabel(
            header,
            text="⚡ Gotowy",
            font=(self.current_font_family, self.current_font_size)
        )
        self.status_label.pack(side="right", padx=10)
        self.register_widget(self.status_label)
        
        # UŻYWAMY STANDARDOWEGO tk.Text ZAMIAST CTkTextbox
        # Frame dla obszaru czatu z scrollbarem
        chat_container = ctk.CTkFrame(chat_frame)
        chat_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbar
        chat_scrollbar = tk.Scrollbar(chat_container)
        chat_scrollbar.pack(side="right", fill="y")
        
        # Obszar czatu - używamy tk.Text dla pełnej kontroli nad czcionkami
        self.chat_display = tk.Text(
            chat_container,
            wrap="word",
            font=(self.chat_font_family, self.chat_font_size),
            bg='#2b2b2b',
            fg='white',
            insertbackground='white',
            selectbackground='#0084ff',
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10
        )
        self.chat_display.pack(side="left", fill="both", expand=True)
        
        # Połącz scrollbar
        self.chat_display.config(yscrollcommand=chat_scrollbar.set)
        chat_scrollbar.config(command=self.chat_display.yview)
        
        # Panel wprowadzania
        input_frame = ctk.CTkFrame(chat_frame)
        input_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # UŻYWAMY tk.Text DLA POLA WPROWADZANIA
        # Frame dla pola tekstowego
        input_container = ctk.CTkFrame(input_frame)
        input_container.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Scrollbar dla pola wprowadzania
        input_scrollbar = tk.Scrollbar(input_container)
        input_scrollbar.pack(side="right", fill="y")
            
        new_conv_button = ctk.CTkButton(
            header,
            text="➕ Nowa rozmowa",
            command=self.start_new_conversation,
            width=120,
            height=30,
            font=(self.current_font_family, self.current_font_size, "bold"),
            fg_color="#00aa00"
        )
        new_conv_button.pack(side="left", padx=10)
        self.register_widget(new_conv_button, "button")


        # Pole tekstowe - używamy tk.Text
        self.input_text = tk.Text(
            input_container,
            height=4,
            wrap="word",
            font=(self.chat_font_family, self.chat_font_size),
            bg='#2b2b2b',
            fg='white',
            insertbackground='white',
            selectbackground='#0084ff',
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10
        )
        self.input_text.pack(side="left", fill="both", expand=True)
        
        # Połącz scrollbar
        self.input_text.config(yscrollcommand=input_scrollbar.set)
        input_scrollbar.config(command=self.input_text.yview)
        
        # Przyciski akcji
        button_panel = ctk.CTkFrame(input_frame)
        button_panel.pack(side="right", fill="y")
        
        self.send_button = ctk.CTkButton(
            button_panel,
            text="Wyślij",
            command=self.send_message,
            width=100,
            height=35,
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        self.send_button.pack(pady=(0, 5))
        self.register_widget(self.send_button, "button")
        
        self.stop_button = ctk.CTkButton(
            button_panel,
            text="Stop",
            command=self.stop_generation,
            width=100,
            height=35,
            state="disabled",
            fg_color="#ff4444",
            font=(self.current_font_family, self.current_font_size, "bold")
        )
        self.stop_button.pack()
        self.register_widget(self.stop_button, "button")
        
        # Skróty klawiszowe
        self.root.bind('<Control-Return>', lambda e: self.send_message())
        self.root.bind('<Control-n>', lambda e: self.start_new_conversation())  # CTRL+N dla nowej rozmowy

        print(f"[INIT] Chat używa tk.Text z czcionką: {self.chat_font_family} {self.chat_font_size}px")
        
    def build_stats_panel(self):
        """Buduje dolny panel ze statystykami"""
        stats_frame = ctk.CTkFrame(self.root, height=80)
        stats_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Statystyki tokenów
        self.stats_labels = {}
        stats_data = [
            ("messages", "Wiadomości: 0"),
            ("input_tokens", "Tokeny wejściowe: 0"),
            ("output_tokens", "Tokeny wyjściowe: 0"),
            ("total_tokens", "Suma tokenów: 0"),
            ("session_cost", "Koszt sesji: $0.00"),
            ("last_cost", "Ostatni koszt: $0.00")
        ]
        
        for i, (key, text) in enumerate(stats_data):
            label = ctk.CTkLabel(
                stats_frame,
                text=text,
                font=(self.current_font_family, self.current_font_size)
            )
            label.pack(side="left", padx=15, pady=10)
            self.stats_labels[key] = label
            self.register_widget(label)
        
    def update_model_info(self):
        """Aktualizuje informacje o wybranym modelu"""
        # Usuń poprzednie informacje
        for widget in self.model_info_frame.winfo_children():
            widget.destroy()
        
        model = self.current_model
        
        info_text = f"""📊 Max output: {model.max_output_tokens:,} tokenów
🧠 Context window: {model.context_window}
⚡ Latencja: {model.latency}
💰 Koszt: ${model.input_cost}/1M in, ${model.output_cost}/1M out
📅 Training cutoff: {model.training_cutoff}"""
        
        info_label = ctk.CTkLabel(
            self.model_info_frame,
            text=info_text,
            font=(self.chat_font_family, int(self.current_font_size * 0.9)),
            justify="left"
        )
        info_label.pack(anchor="w")
        self.register_widget(info_label)
        
    def change_model(self, model_key):
        """Zmienia aktywny model"""
        self.current_model = MODELS[model_key]
        self.update_model_info()
        self.chat_title.configure(text=f"Czat z {self.current_model.name}")
        
        # Zaktualizuj ustawienia Extended Thinking
        if hasattr(self, 'thinking_enabled_var'):
            self.thinking_enabled_var.set(self.current_model.default_thinking_enabled)
            if self.current_model.extended_thinking:
                self.thinking_budget_var.set(self.current_model.default_thinking_budget)
                self.thinking_budget_label.configure(
                    text=f"Budżet: {self.current_model.default_thinking_budget} tokenów"
                )
        
        self.update_status(f"Przełączono na {self.current_model.name}", "success")
        
    def send_message(self):
        """Wysyła wiadomość do API"""
        message = self.input_text.get("1.0", "end-1c").strip()
        if not message or not self.client:
            return
        
        # Wyczyść pole wejściowe
        self.input_text.delete("1.0", "end")
        
        # Dodaj wiadomość użytkownika do wyświetlacza
        self.append_to_chat("Ty", message, "#0084ff")
        
        # Dodaj do historii
        self.conversation_history.append({"role": "user", "content": message})
        self.update_history_list()
        
        # Wyłącz przyciski i pokaż status
        self.send_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.update_status("🤔 Claude myśli...", "warning")
        
        # Wyślij w osobnym wątku
        thread = threading.Thread(target=self.send_api_request, args=(message,))
        thread.daemon = True
        thread.start()
        
    def send_api_request(self, message):
        """Wysyła request do API ze streamowaniem i Extended Thinking"""
        try:
            # Przygotuj parametry
            params = {
                "model": self.current_model.id,
                "max_tokens": self.current_model.max_output_tokens,
                "temperature": self.temperature_var.get(),
                "system": self.system_prompt,
                "messages": self.conversation_history
            }
            
            # Dodaj Extended Thinking jeśli włączone
            if (self.current_model.extended_thinking and 
                hasattr(self, 'thinking_enabled_var') and 
                self.thinking_enabled_var.get()):
                params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget_var.get()
                }
                
                # Dla Extended Thinking użyj bardziej szczegółowej obsługi
                with self.client.messages.stream(**params) as stream:
                    full_response = ""
                    thinking_content = ""
                    
                    # Zainicjalizuj odpowiedź
                    self.root.after(0, self.init_claude_response)
                    
                    for event in stream:
                        # Obsługa różnych typów eventów
                        if event.type == 'content_block_start':
                            if event.content_block.type == 'thinking':
                                # Rozpoczyna się blok myślenia
                                pass
                        elif event.type == 'content_block_delta':
                            if event.delta.type == 'thinking_delta':
                                # Dodaj do myślenia
                                thinking_content += event.delta.thinking
                            elif event.delta.type == 'text_delta':
                                # Dodaj do odpowiedzi
                                text = event.delta.text
                                full_response += text
                                self.root.after(0, self.append_streaming_text, text)
                    
                    # Pobierz finalne metryki
                    final_message = stream.get_final_message()
                    
                    # Zapisz pełną odpowiedź
                    self.conversation_history.append({
                        "role": "assistant", 
                        "content": full_response
                    })
                    
                    # Oblicz koszt
                    usage = final_message.usage if hasattr(final_message, 'usage') else None
                    input_tokens = usage.input_tokens if usage else len(message) // 4
                    output_tokens = usage.output_tokens if usage else len(full_response) // 4
                    
                    message_cost = self.token_stats.add_usage(
                        input_tokens,
                        output_tokens,
                        self.current_model
                    )
                    
                    self.root.after(0, self.finalize_streaming_response, 
                                full_response, message_cost, thinking_content)
            else:
                # Bez Extended Thinking - użyj prostszego streamowania
                with self.client.messages.stream(**params) as stream:
                    full_response = ""
                    
                    self.root.after(0, self.init_claude_response)
                    
                    # Użyj wbudowanego text_stream
                    for text in stream.text_stream:
                        full_response += text
                        self.root.after(0, self.append_streaming_text, text)
                    
                    # Finalizuj
                    final_message = stream.get_final_message()
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_response
                    })
                    
                    usage = final_message.usage if hasattr(final_message, 'usage') else None
                    input_tokens = usage.input_tokens if usage else len(message) // 4
                    output_tokens = usage.output_tokens if usage else len(full_response) // 4
                    
                    message_cost = self.token_stats.add_usage(
                        input_tokens, output_tokens, self.current_model
                    )
                    
                    self.root.after(0, self.finalize_streaming_response,
                                full_response, message_cost, "")
                    
        except Exception as e:
            self.root.after(0, self.handle_error, str(e))
   

    def init_claude_response(self):
        """Inicjalizuje nową odpowiedź Claude'a w czacie"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert("end", f"\n[{timestamp}] ", "timestamp")
        self.chat_display.insert("end", "Claude:\n", "ai_sender")
        # Zapisz pozycję gdzie zaczynamy dodawać tekst
        self.streaming_start_pos = self.chat_display.index("end-1c")

    def append_streaming_text(self, text_chunk):
        """Dodaje fragment tekstu podczas streamowania"""
        # Dodaj tekst bezpośrednio
        self.chat_display.insert("end", text_chunk, "message")
        self.chat_display.see("end")

    def finalize_streaming_response(self, full_response, cost, thinking_content=""):
        """Finalizuje odpowiedź po zakończeniu streamowania"""
        # Dodaj separator
        self.chat_display.insert("end", "\n" + "-" * 80 + "\n", "separator")
        
        # Jeśli było Extended Thinking, pokaż info
        if thinking_content:
            print(f"[THINKING] Użyto Extended Thinking ({len(thinking_content)} znaków)")
            self.update_status("✅ Gotowy (użyto Extended Thinking)", "success")
        else:
            self.update_status("✅ Gotowy", "success")
        
        # Aktualizuj statystyki
        self.update_history_list()
        self.update_statistics(cost)
        
        # Włącz przyciski
        self.send_button.configure(state="normal")
        self.stop_button.configure(state="disabled")


    def append_streaming_text(self, text_chunk):
        """Dodaje fragment tekstu podczas streamowania"""
        # Znajdź ostatnią pozycję Claude'a
        last_pos = self.chat_display.search("Claude:", "1.0", tk.END)
        if last_pos:
            # Dodaj tekst na końcu
            self.chat_display.insert("end", text_chunk)
            self.chat_display.see("end")
        else:
            # Rozpocznij nową wiadomość Claude'a
            self.append_to_chat("Claude", text_chunk, "#00d26a")

    def update_thinking_display(self, thinking_text):
        """Opcjonalnie: wyświetla proces myślenia Claude'a"""
        # Możesz utworzyć osobne okno lub sekcję dla wyświetlania myślenia
        if hasattr(self, 'thinking_display'):
            self.thinking_display.insert("end", thinking_text)
            self.thinking_display.see("end")

    def finalize_streaming_response(self, full_response, cost, thinking_content=""):
        """Finalizuje odpowiedź po zakończeniu streamowania"""
        # Jeśli Extended Thinking był używany, możesz zapisać lub wyświetlić myślenie
        if thinking_content:
            print(f"[THINKING] Claude pomyślał:\n{thinking_content[:500]}...")  # Pierwsze 500 znaków
        
        # Aktualizuj historię i statystyki
        self.update_history_list()
        self.update_statistics(cost)
        
        # Włącz przyciski
        self.send_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_status("✅ Gotowy", "success")

    def toggle_thinking(self):
        """Przełącza Extended Thinking"""
        if self.thinking_enabled_var.get():
            if not self.current_model.extended_thinking:
                self.thinking_enabled_var.set(False)
                messagebox.showwarning(
                    "Extended Thinking", 
                    f"{self.current_model.name} nie obsługuje Extended Thinking"
                )
            else:
                self.update_status("🧠 Extended Thinking włączony", "success")
        else:
            self.update_status("Extended Thinking wyłączony", "normal")

    def update_thinking_budget_label(self):
        """Aktualizuje etykietę budżetu myślenia"""
        budget = self.thinking_budget_var.get()
        self.thinking_budget_label.configure(text=f"Budżet: {budget} tokenów")
        if budget > 21333:
            self.thinking_budget_label.configure(text=f"Budżet: {budget} tokenów (wymaga streamowania)")


    def update_after_response(self, message, cost):
        """Aktualizuje UI po otrzymaniu odpowiedzi"""
        # Dodaj odpowiedź do czatu
        self.append_to_chat("Claude", message, "#00d26a")
        
        # Aktualizuj historię i statystyki
        self.update_history_list()
        self.update_statistics(cost)
        
        # Włącz przyciski
        self.send_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_status("✅ Gotowy", "success")
        
    def append_to_chat(self, sender, message, color):
        """Dodaje wiadomość do okna czatu (tk.Text)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Konfiguruj tagi dla różnych elementów
        self.chat_display.tag_config("timestamp", foreground="#888888")
        self.chat_display.tag_config("user_sender", foreground="#0084ff", font=(self.chat_font_family, self.chat_font_size, "bold"))
        self.chat_display.tag_config("ai_sender", foreground="#00d26a", font=(self.chat_font_family, self.chat_font_size, "bold"))
        self.chat_display.tag_config("message", font=(self.chat_font_family, self.chat_font_size))
        self.chat_display.tag_config("separator", foreground="#444444")
        
        # Dodaj elementy z odpowiednimi tagami
        self.chat_display.insert("end", f"\n[{timestamp}] ", "timestamp")
        
        if sender == "Ty":
            self.chat_display.insert("end", f"{sender}:\n", "user_sender")
        else:
            self.chat_display.insert("end", f"{sender}:\n", "ai_sender")
        
        self.chat_display.insert("end", f"{message}\n", "message")
        self.chat_display.insert("end", "-" * 80 + "\n", "separator")
        
        # Przewiń do końca
        self.chat_display.see("end")
        
    def update_statistics(self, last_cost):
        """Aktualizuje panel statystyk"""
        stats = self.token_stats
        
        self.stats_labels["messages"].configure(
            text=f"Wiadomości: {stats.messages_count}"
        )
        self.stats_labels["input_tokens"].configure(
            text=f"Tokeny wejściowe: {stats.total_input_tokens:,}"
        )
        self.stats_labels["output_tokens"].configure(
            text=f"Tokeny wyjściowe: {stats.total_output_tokens:,}"
        )
        self.stats_labels["total_tokens"].configure(
            text=f"Suma tokenów: {stats.total_input_tokens + stats.total_output_tokens:,}"
        )
        self.stats_labels["session_cost"].configure(
            text=f"Koszt sesji: ${stats.session_cost:.4f}"
        )
        self.stats_labels["last_cost"].configure(
            text=f"Ostatni koszt: ${last_cost:.4f}"
        )
        
    def update_history_list(self):
        """Aktualizuje listę historii"""
        self.history_listbox.delete(0, tk.END)
        for i, msg in enumerate(self.conversation_history):
            role = "👤" if msg["role"] == "user" else "🤖"
            preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            self.history_listbox.insert(tk.END, f"{role} {preview}")
            
    def save_conversation(self):
        """Zapisuje rozmowę do pliku"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"claude_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filename:
            data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.current_model.id,
                "system_prompt": self.system_prompt,
                "messages": self.conversation_history,
                "statistics": {
                    "total_input_tokens": self.token_stats.total_input_tokens,
                    "total_output_tokens": self.token_stats.total_output_tokens,
                    "total_cost": self.token_stats.session_cost,
                    "messages_count": self.token_stats.messages_count
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.update_status(f"Zapisano: {os.path.basename(filename)}", "success")
            
    def load_conversation(self):
        """Wczytuje rozmowę z pliku"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.conversation_history = data["messages"]
            self.system_prompt = data.get("system_prompt", "")
            self.system_prompt_text.delete("1.0", "end")
            self.system_prompt_text.insert("1.0", self.system_prompt)
            
            # Odtwórz rozmowę w czacie
            self.chat_display.delete("1.0", "end")
            for msg in self.conversation_history:
                sender = "Ty" if msg["role"] == "user" else "Claude"
                color = "#0084ff" if msg["role"] == "user" else "#00d26a"
                self.append_to_chat(sender, msg["content"], color)
            
            self.update_history_list()
            self.update_status(f"Wczytano: {os.path.basename(filename)}", "success")
            
    def clear_history(self):
        """Czyści historię rozmowy"""
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz wyczyścić całą historię?"):
            self.conversation_history.clear()
            self.chat_display.delete("1.0", "end")
            self.history_listbox.delete(0, tk.END)
            self.token_stats = TokenStats()
            self.update_statistics(0)
            self.update_status("Historia wyczyszczona", "success")
            
    def stop_generation(self):
        """Zatrzymuje generowanie (placeholder)"""
        self.send_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_status("⏹️ Zatrzymano", "warning")
        
    def handle_error(self, error_msg):
        """Obsługuje błędy"""
        self.append_to_chat("System", f"Błąd: {error_msg}", "#ff4444")
        self.send_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_status("❌ Błąd", "error")
        messagebox.showerror("Błąd API", error_msg)
        
    def update_status(self, text, status_type="normal"):
        """Aktualizuje status"""
        color_map = {
            "normal": "#ffffff",
            "success": "#00d26a",
            "warning": "#ffa500",
            "error": "#ff4444"
        }
        self.status_label.configure(text=text)
        
    def run(self):
        """Uruchamia aplikację"""
        self.root.mainloop()
      

def main():
    """Punkt wejścia aplikacji"""
    try:
        import customtkinter
    except ImportError:
        print("Instaluję customtkinter...")
        os.system("pip install customtkinter")
        
    app = ClaudeGUIAssistant()
    
    # ============= INTEGRACJA BAZY DANYCH =============
    if DB_AVAILABLE:
        try:
            print("\n[DB] 🔧 DODAJĘ ZAKŁADKĘ BAZY DANYCH...")
            
            # Utwórz menedżer bazy
            app.db = DatabaseManager()
            app.db_panel = DatabaseHistoryPanel(app)
            app.db_panel.db = app.db
            
            original_send_api = app.send_api_request
            
            def enhanced_send_api_request(message):
                # Utwórz nową rozmowę jeśli nie ma ID
                if not hasattr(app, 'current_conversation_id') or app.current_conversation_id is None:
                    title = message[:50] + "..." if len(message) > 50 else message
                    app.current_conversation_id = app.db.create_conversation(
                        title=title,
                        model_id=app.current_model.id,
                        model_name=app.current_model.name,
                        system_prompt=app.system_prompt,
                        temperature=app.temperature_var.get()
                    )
                
                # Zapisz wiadomość użytkownika
                if app.current_conversation_id:
                    app.db.add_message(
                        app.current_conversation_id,
                        "user",
                        message,
                        input_tokens=len(message) // 4
                    )
                
                # Wywołaj oryginalną funkcję
                original_send_api(message)
            
            def load_conversation_from_db():
                """Wczytuje wybraną rozmowę z bazy do czatu"""
                if hasattr(app.db_panel, 'selected_conversation_id') and app.db_panel.selected_conversation_id:
                    try:
                        # Pobierz rozmowę
                        conv = app.db.get_conversation_with_messages(app.db_panel.selected_conversation_id)
                        if conv:
                            # Wyczyść obecny czat
                            app.conversation_history.clear()
                            app.chat_display.delete("1.0", "end")
                            
                            # Wczytaj system prompt
                            if conv['system_prompt']:
                                app.system_prompt = conv['system_prompt']
                                app.system_prompt_text.delete("1.0", "end")
                                app.system_prompt_text.insert("1.0", conv['system_prompt'])
                            
                            # Wczytaj wiadomości
                            for msg in conv['messages']:
                                app.conversation_history.append({
                                    'role': msg['role'],
                                    'content': msg['content']
                                })
                                
                                sender = "Ty" if msg['role'] == 'user' else "Claude"
                                color = "#0084ff" if msg['role'] == 'user' else "#00d26a"
                                app.append_to_chat(sender, msg['content'], color)
                            
                            # Ustaw ID rozmowy
                            app.current_conversation_id = app.db_panel.selected_conversation_id
                            
                            # Aktualizuj UI
                            app.update_history_list()
                            app.update_status(f"✅ Wczytano: {conv['title']}", "success")
                            
                            # Przełącz na zakładkę czatu (opcjonalne)
                            app.tabview.set("Historia")  # Przełącz widok jeśli chcesz
                            
                    except Exception as e:
                        app.update_status(f"Błąd wczytywania: {e}", "error")
                else:
                    app.update_status("Najpierw wybierz rozmowę z listy", "warning")
            
            # Podepnij funkcję do panelu
            app.db_panel.load_from_db = load_conversation_from_db

            app.send_api_request = enhanced_send_api_request
            
            # Nadpisz też update_after_response
            original_update = app.update_after_response
            
            def enhanced_update_after_response(message, cost):
                original_update(message, cost)
                
                # Zapisz odpowiedź Claude'a
                if hasattr(app, 'current_conversation_id') and app.current_conversation_id:
                    app.db.add_message(
                        app.current_conversation_id,
                        "assistant",
                        message,
                        output_tokens=len(message) // 4,
                        cost=cost
                    )
                    # Odśwież listę rozmów
                    if hasattr(app.db_panel, 'load_conversations'):
                        app.db_panel.load_conversations()
            
            app.update_after_response = enhanced_update_after_response


            # DODAJ ZAKŁADKĘ DO TABVIEW!!!
            db_tab = app.tabview.add("📚 BAZA DANYCH")
            app.db_panel.build_database_tab(db_tab)
            
            # Test zakładka
            test_tab = app.tabview.add("🔴 TEST KURWA")
            test_label = ctk.CTkLabel(test_tab, text="DZIAŁA KURWA!", font=("Arial", 30, "bold"))
            test_label.pack(expand=True)
            
            app.current_conversation_id = None
            
            print("[DB] ✅✅✅ ZAKŁADKA BAZY DODANA! SZUKAJ '📚 BAZA DANYCH'")
            
        except Exception as e:
            print(f"\n[DB] ❌❌❌ BŁĄD: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[DB] ⚠️ BRAK MODUŁÓW - sprawdź czy masz:")
        print("     - claude_db_extension.py")
        print("     - claude_gui_db_panel.py")
    
    app.run()

if __name__ == "__main__":
    main()