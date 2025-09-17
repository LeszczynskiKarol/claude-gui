#!/usr/bin/env python3
"""
Panel historii rozmów - rozszerzenie GUI o obsługę bazy danych
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

class DatabaseHistoryPanel:
    """Panel do zarządzania historią rozmów z bazy danych"""
    
    def __init__(self, parent_gui):
        """Inicjalizacja panelu historii"""
        self.gui = parent_gui
        self.db = None  # Będzie ustawione przez integrate_database
        self.selected_conversation_id = None
        
    def build_database_tab(self, parent):
        """Buduje zakładkę z historią rozmów z bazy"""
        # Główny frame
        main_frame = ctk.CTkFrame(parent)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Górny panel - wyszukiwanie i przyciski
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", padx=5, pady=5)
        
        # Pole wyszukiwania
        search_label = ctk.CTkLabel(
            top_frame,
            text="Szukaj:",
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        search_label.pack(side="left", padx=5)
        
        self.search_entry = ctk.CTkEntry(
            top_frame,
            placeholder_text="Szukaj w tytułach i treści rozmów...",  # Jaśniejszy opis
            width=250,
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_conversations())
        
        search_button = ctk.CTkButton(
            top_frame,
            text="🔍 Szukaj",
            command=self.search_conversations,
            width=80,
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        search_button.pack(side="left", padx=5)
        
        refresh_button = ctk.CTkButton(
            top_frame,
            text="🔄 Odśwież",
            command=self.load_conversations,
            width=80,
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        refresh_button.pack(side="left", padx=5)
        
        # Środkowy panel - lista rozmów i podgląd
        middle_frame = ctk.CTkFrame(main_frame)
        middle_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Lewa strona - lista rozmów
        left_frame = ctk.CTkFrame(middle_frame, width=300)
        left_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        list_label = ctk.CTkLabel(
            left_frame,
            text="📚 Historia rozmów:",
            font=(self.gui.current_font_family, int(self.gui.current_font_size * 1.1), "bold")
        )
        list_label.pack(pady=5)
        
        # Listbox z rozmowami
        list_container = ctk.CTkFrame(left_frame)
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        self.conversations_listbox = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            bg='#2b2b2b',
            fg='white',
            selectbackground='#0084ff',
            font=(self.gui.current_font_family, int(self.gui.current_font_size * 0.9)),
            height=20
        )
        self.conversations_listbox.pack(side="left", fill="both", expand=True)
        self.conversations_listbox.bind('<<ListboxSelect>>', self.on_conversation_select)
        self.conversations_listbox.bind('<Double-Button-1>', lambda e: self.load_selected_conversation())

        scrollbar.config(command=self.conversations_listbox.yview)
        
        # Przyciski akcji
        action_frame = ctk.CTkFrame(left_frame)
        action_frame.pack(fill="x", padx=5, pady=5)
        
        load_button = ctk.CTkButton(
            action_frame,
            text="📖 Wczytaj do czatu",  # Bardziej jasny opis
            command=self.load_selected_conversation,
            width=120,
            font=(self.gui.current_font_family, self.gui.current_font_size),
            fg_color="#00aa00"  # Zielony żeby było widać że to ważne
        )

        load_button.pack(side="left", padx=2)
        
        archive_button = ctk.CTkButton(
            action_frame,
            text="📦 Archiwizuj",
            command=self.archive_selected_conversation,
            width=90,
            fg_color="#666666",
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        archive_button.pack(side="left", padx=2)
        
        delete_button = ctk.CTkButton(
            action_frame,
            text="🗑️ Usuń",
            command=self.delete_selected_conversation,
            width=90,
            fg_color="#ff4444",
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        delete_button.pack(side="left", padx=2)
        
        # Prawa strona - podgląd rozmowy
        right_frame = ctk.CTkFrame(middle_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        preview_label = ctk.CTkLabel(
            right_frame,
            text="👁️ Podgląd rozmowy:",
            font=(self.gui.current_font_family, int(self.gui.current_font_size * 1.1), "bold")
        )
        preview_label.pack(pady=5)
        
        # Info o rozmowie
        self.conversation_info = ctk.CTkLabel(
            right_frame,
            text="Wybierz rozmowę z listy",
            font=(self.gui.current_font_family, int(self.gui.current_font_size * 0.9)),
            justify="left"
        )
        self.conversation_info.pack(pady=5)
        
        # Obszar podglądu
        preview_container = ctk.CTkFrame(right_frame)
        preview_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        preview_scrollbar = tk.Scrollbar(preview_container)
        preview_scrollbar.pack(side="right", fill="y")
        
        self.preview_text = tk.Text(
            preview_container,
            wrap="word",
            bg='#2b2b2b',
            fg='white',
            font=(self.gui.chat_font_family, int(self.gui.chat_font_size * 0.9)),
            state="disabled",
            yscrollcommand=preview_scrollbar.set
        )
        self.preview_text.pack(side="left", fill="both", expand=True)
        
        preview_scrollbar.config(command=self.preview_text.yview)
        
        # Dolny panel - statystyki
        stats_frame = ctk.CTkFrame(main_frame)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="📊 Statystyki: Ładowanie...",
            font=(self.gui.current_font_family, self.gui.current_font_size)
        )
        self.stats_label.pack(pady=5)
        
        # Załaduj rozmowy przy starcie
        self.load_conversations()
        self.load_statistics()
        
    def load_conversations(self):
        """Ładuje listę rozmów z bazy"""
        if not self.db:
            return
        
        try:
            conversations = self.db.get_all_conversations()
            
            self.conversations_listbox.delete(0, tk.END)
            self.conversation_data = {}
            
            for conv in conversations:
                # Format: "📅 Data | 💬 Tytuł | 📊 Wiad: X"
                created = datetime.fromisoformat(conv['created_at']).strftime("%Y-%m-%d %H:%M")
                display_text = f"📅 {created} | 💬 {conv['title'][:30]}... | 📊 {conv['message_count']} wiad."
                
                self.conversations_listbox.insert(tk.END, display_text)
                self.conversation_data[len(self.conversation_data)] = conv
            
            self.gui.update_status(f"Załadowano {len(conversations)} rozmów", "success")
            
        except Exception as e:
            print(f"[DB ERROR] {e}")
            self.gui.update_status("Błąd ładowania rozmów", "error")
    
    def search_conversations(self):
        """Wyszukuje rozmowy"""
        query = self.search_entry.get()
        
        if not query or not self.db:
            self.load_conversations()
            return
        
        try:
            conversations = self.db.search_conversations(query)
            
            self.conversations_listbox.delete(0, tk.END)
            self.conversation_data = {}
            
            for conv in conversations:
                created = datetime.fromisoformat(conv['created_at']).strftime("%Y-%m-%d %H:%M")
                display_text = f"🔍 {created} | 💬 {conv['title'][:30]}... | 📊 {conv['message_count']} wiad."
                
                self.conversations_listbox.insert(tk.END, display_text)
                self.conversation_data[len(self.conversation_data)] = conv
            
            self.gui.update_status(f"Znaleziono {len(conversations)} rozmów", "success")
            
        except Exception as e:
            print(f"[DB ERROR] {e}")
            self.gui.update_status("Błąd wyszukiwania", "error")
    
    def on_conversation_select(self, event):
        """Obsługuje wybór rozmowy z listy"""
        selection = self.conversations_listbox.curselection()
        
        if not selection or not self.db:
            return
        
        index = selection[0]
        if index in self.conversation_data:
            conv_data = self.conversation_data[index]
            self.selected_conversation_id = conv_data['id']
            
            # Pobierz pełną rozmowę
            full_conversation = self.db.get_conversation_with_messages(self.selected_conversation_id)
            
            if full_conversation:
                # Aktualizuj info
                info_text = f"""
📌 Tytuł: {full_conversation['title']}
📅 Utworzono: {full_conversation['created_at']}
🔄 Zaktualizowano: {full_conversation['updated_at']}
🤖 Model: {full_conversation['model_name']}
💬 Wiadomości: {full_conversation['message_count']}
💰 Koszt: ${full_conversation['total_cost']:.4f}
                """
                self.conversation_info.configure(text=info_text.strip())
                
                # Wyświetl podgląd
                self.preview_text.configure(state="normal")
                self.preview_text.delete("1.0", tk.END)
                
                for msg in full_conversation['messages']:
                    timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                    role = "👤 Użytkownik" if msg['role'] == 'user' else "🤖 Claude"
                    
                    self.preview_text.insert(tk.END, f"[{timestamp}] {role}:\n")
                    self.preview_text.insert(tk.END, f"{msg['content']}\n")
                    self.preview_text.insert(tk.END, "-" * 60 + "\n")
                
                self.preview_text.configure(state="disabled")
                self.preview_text.see("1.0")
    
    def load_selected_conversation(self):
        """Wczytuje wybraną rozmowę do głównego okna czatu"""
        if not self.selected_conversation_id or not self.db:
            return
        
        try:
            conversation = self.db.get_conversation_with_messages(self.selected_conversation_id)
            
            if conversation:
                # Wyczyść obecny czat
                self.gui.conversation_history.clear()
                self.gui.chat_display.delete("1.0", tk.END)
                
                # Ustaw parametry rozmowy
                if conversation['system_prompt']:
                    self.gui.system_prompt = conversation['system_prompt']
                    if hasattr(self.gui, 'system_prompt_text'):
                        self.gui.system_prompt_text.delete("1.0", tk.END)
                        self.gui.system_prompt_text.insert("1.0", conversation['system_prompt'])
                
                # Wczytaj wiadomości
                for msg in conversation['messages']:
                    self.gui.conversation_history.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
                    
                    sender = "Ty" if msg['role'] == 'user' else "Claude"
                    color = "#0084ff" if msg['role'] == 'user' else "#00d26a"
                    self.gui.append_to_chat(sender, msg['content'], color)
                
                # Ustaw ID obecnej rozmowy
                self.gui.current_conversation_id = self.selected_conversation_id
                
                # Aktualizuj UI
                self.gui.update_history_list()
                self.gui.update_status(f"Wczytano rozmowę: {conversation['title']}", "success")
                
        except Exception as e:
            print(f"[DB ERROR] {e}")
            self.gui.update_status("Błąd wczytywania rozmowy", "error")
    
    def archive_selected_conversation(self):
        """Archiwizuje wybraną rozmowę"""
        if not self.selected_conversation_id or not self.db:
            return
        
        if messagebox.askyesno("Archiwizacja", "Czy na pewno chcesz zarchiwizować tę rozmowę?"):
            if self.db.archive_conversation(self.selected_conversation_id):
                self.gui.update_status("Rozmowa zarchiwizowana", "success")
                self.load_conversations()
            else:
                self.gui.update_status("Błąd archiwizacji", "error")
    
    def delete_selected_conversation(self):
        """Usuwa wybraną rozmowę"""
        if not self.selected_conversation_id or not self.db:
            return
        
        if messagebox.askyesno("Usuwanie", "Czy na pewno chcesz TRWALE usunąć tę rozmowę?"):
            if self.db.delete_conversation(self.selected_conversation_id):
                self.gui.update_status("Rozmowa usunięta", "success")
                self.load_conversations()
                self.selected_conversation_id = None
                self.preview_text.configure(state="normal")
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.configure(state="disabled")
            else:
                self.gui.update_status("Błąd usuwania", "error")
    
    def load_statistics(self):
        """Ładuje statystyki z bazy"""
        if not self.db:
            return
        
        try:
            stats = self.db.get_statistics()
            
            stats_text = f"📊 Rozmów: {stats.get('total_conversations', 0)} | "
            stats_text += f"💬 Wiadomości: {stats.get('total_messages', 0)} | "
            stats_text += f"🔢 Tokenów: {stats.get('total_tokens', 0):,} | "
            stats_text += f"💰 Koszt całkowity: ${stats.get('total_cost', 0):.2f}"
            
            self.stats_label.configure(text=stats_text)
            
        except Exception as e:
            print(f"[DB ERROR] {e}")

def integrate_database_with_gui(gui_instance):
    """Integruje bazę danych z istniejącą aplikacją GUI"""
    
    # Import modułu bazy danych
    from claude_db_extension import DatabaseManager
    
    # Utwórz panel historii
    history_panel = DatabaseHistoryPanel(gui_instance)
    
    # Utwórz menedżer bazy
    gui_instance.db = DatabaseManager()
    history_panel.db = gui_instance.db
    
    # Inicjalizuj zmienne
    gui_instance.current_conversation_id = None
    
    # Zmodyfikuj metodę build_control_panel żeby dodać nową zakładkę
    original_build_control = gui_instance.build_control_panel
    
    def enhanced_build_control_panel(parent):
        # Wywołaj oryginalną metodę
        original_build_control(parent)
        
        # Znajdź tabview (już istnieje)
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkTabview):
                # Dodaj nową zakładkę
                db_tab = widget.add("📚 Baza")
                history_panel.build_database_tab(db_tab)
                break
    
    gui_instance.build_control_panel = enhanced_build_control_panel
    
    # Zmodyfikuj send_api_request żeby zapisywała do bazy
    original_send_api = gui_instance.send_api_request
    
    def enhanced_send_api_request(message):
        # Jeśli to pierwsza wiadomość, utwórz nową rozmowę
        if gui_instance.current_conversation_id is None:
            title = gui_instance.db.generate_title_from_first_message(message)
            
            conv_id = gui_instance.db.create_conversation(
                title=title,
                model_id=gui_instance.current_model.id,
                model_name=gui_instance.current_model.name,
                system_prompt=gui_instance.system_prompt,
                temperature=gui_instance.temperature_var.get()
            )
            gui_instance.current_conversation_id = conv_id
            
            # Zapisz pierwszą wiadomość użytkownika
            if conv_id:
                gui_instance.db.add_message(
                    conversation_id=conv_id,
                    role="user",
                    content=message,
                    input_tokens=len(message) // 4  # Przybliżone
                )
        else:
            # Zapisz kolejną wiadomość użytkownika
            gui_instance.db.add_message(
                conversation_id=gui_instance.current_conversation_id,
                role="user",
                content=message,
                input_tokens=len(message) // 4
            )
        
        # Wywołaj oryginalną metodę
        original_send_api(message)
    
    gui_instance.send_api_request = enhanced_send_api_request
    
    # Zmodyfikuj update_after_response żeby zapisywała odpowiedź do bazy
    original_update = gui_instance.update_after_response
    
    def enhanced_update_after_response(message, cost):
        # Wywołaj oryginalną metodę
        original_update(message, cost)
        
        # Zapisz odpowiedź asystenta do bazy
        if gui_instance.current_conversation_id:
            gui_instance.db.add_message(
                conversation_id=gui_instance.current_conversation_id,
                role="assistant",
                content=message,
                output_tokens=len(message) // 4,  # Przybliżone
                cost=cost
            )
            
            # Odśwież listę w panelu historii jeśli jest otwarty
            if hasattr(history_panel, 'load_conversations'):
                history_panel.load_conversations()
    
    gui_instance.update_after_response = enhanced_update_after_response
    
    # Dodaj przycisk "Nowa rozmowa" do głównego interfejsu
    def start_new_conversation():
        if gui_instance.conversation_history and messagebox.askyesno(
            "Nowa rozmowa", 
            "Czy chcesz zapisać obecną rozmowę i rozpocząć nową?"
        ):
            # Wyczyść obecną rozmowę
            gui_instance.conversation_history.clear()
            gui_instance.chat_display.delete("1.0", tk.END)
            gui_instance.history_listbox.delete(0, tk.END)
            gui_instance.current_conversation_id = None
            gui_instance.update_status("Rozpoczęto nową rozmowę", "success")
    
    # Dodaj przycisk do GUI (możesz go umieścić gdzie chcesz)
    gui_instance.start_new_conversation = start_new_conversation
    
    print("[DB] Zintegrowano bazę danych PostgreSQL z GUI!")
    gui_instance.update_status("✅ Baza danych połączona", "success")

# Użycie:
# W głównym pliku GUI dodaj:
# from claude_gui_db_panel import integrate_database_with_gui
# Po utworzeniu instancji GUI:
# integrate_database_with_gui(app)