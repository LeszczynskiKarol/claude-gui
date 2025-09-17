#!/usr/bin/env python3
"""
Rozszerzenie bazy danych dla Claude GUI Assistant
Obsługuje PostgreSQL do przechowywania historii rozmów
"""

import os
from datetime import datetime
from typing import List, Optional, Dict
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

Base = declarative_base()

# Modele bazy danych
class Conversation(Base):
    """Model rozmowy"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    model_id = Column(String(100), nullable=False)
    model_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    message_count = Column(Integer, default=0)
    system_prompt = Column(Text)
    temperature = Column(Float, default=0.7)
    is_archived = Column(Boolean, default=False)
    tags = Column(JSON)  # Lista tagów
    
    # Relacja z wiadomościami
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'model_name': self.model_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': self.message_count,
            'total_cost': self.total_cost
        }

class Message(Base):
    """Model pojedynczej wiadomości"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' lub 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Relacja z rozmową
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'tokens': self.input_tokens + self.output_tokens,
            'cost': self.cost
        }

class DatabaseManager:
    """Menedżer bazy danych"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        """Inicjalizacja menedżera bazy danych"""
        if db_config is None:
            # Domyślna konfiguracja
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'claude_assistant'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres')
            }
        
        self.db_config = db_config
        self.engine = None
        self.Session = None
        
        # Inicjalizuj połączenie
        self.initialize_database()
    
    def create_database_if_not_exists(self):
        """Tworzy bazę danych jeśli nie istnieje"""
        try:
            # Połącz się z PostgreSQL (nie z konkretną bazą)
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Sprawdź czy baza istnieje
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.db_config['database'],)
            )
            exists = cursor.fetchone()
            
            if not exists:
                # Utwórz bazę danych
                cursor.execute(f"CREATE DATABASE {self.db_config['database']}")
                print(f"[DB] Utworzono bazę danych: {self.db_config['database']}")
            else:
                print(f"[DB] Baza danych już istnieje: {self.db_config['database']}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[DB ERROR] Nie można utworzyć bazy danych: {e}")
            raise
    
    def initialize_database(self):
        """Inicjalizuje połączenie z bazą danych i tworzy tabele"""
        try:
            # Najpierw upewnij się, że baza istnieje
            self.create_database_if_not_exists()
            
            # Utwórz connection string
            db_url = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            
            # Utwórz silnik
            self.engine = create_engine(db_url, echo=False, pool_size=5, max_overflow=10)
            
            # Utwórz tabele
            Base.metadata.create_all(self.engine)
            
            # Utwórz sesję
            self.Session = sessionmaker(bind=self.engine)
            
            print("[DB] Połączono z bazą danych PostgreSQL")
            
        except Exception as e:
            print(f"[DB ERROR] Błąd inicjalizacji bazy danych: {e}")
            raise
    
    def create_conversation(self, title: str, model_id: str, model_name: str, 
                          system_prompt: str = "", temperature: float = 0.7) -> Optional[int]:
        """Tworzy nową rozmowę w bazie"""
        session = self.Session()
        try:
            conversation = Conversation(
                title=title,
                model_id=model_id,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=temperature
            )
            session.add(conversation)
            session.commit()
            
            print(f"[DB] Utworzono rozmowę: {title} (ID: {conversation.id})")
            return conversation.id
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DB ERROR] Błąd tworzenia rozmowy: {e}")
            return None
        finally:
            session.close()
    
    def add_message(self, conversation_id: int, role: str, content: str,
                   input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0) -> bool:
        """Dodaje wiadomość do rozmowy"""
        session = self.Session()
        try:
            # Dodaj wiadomość
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost
            )
            session.add(message)
            
            # Zaktualizuj statystyki rozmowy
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.message_count += 1
                conversation.total_tokens += input_tokens + output_tokens
                conversation.total_cost += cost
                conversation.updated_at = datetime.now()
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DB ERROR] Błąd dodawania wiadomości: {e}")
            return False
        finally:
            session.close()
    
    def get_all_conversations(self, include_archived: bool = False) -> List[Dict]:
        """Pobiera wszystkie rozmowy"""
        session = self.Session()
        try:
            query = session.query(Conversation)
            
            if not include_archived:
                query = query.filter_by(is_archived=False)
            
            conversations = query.order_by(Conversation.updated_at.desc()).all()
            
            return [conv.to_dict() for conv in conversations]
            
        except SQLAlchemyError as e:
            print(f"[DB ERROR] Błąd pobierania rozmów: {e}")
            return []
        finally:
            session.close()
    
    def get_conversation_with_messages(self, conversation_id: int) -> Optional[Dict]:
        """Pobiera rozmowę wraz z wszystkimi wiadomościami"""
        session = self.Session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            
            if not conversation:
                return None
            
            result = conversation.to_dict()
            result['messages'] = [msg.to_dict() for msg in conversation.messages]
            result['system_prompt'] = conversation.system_prompt
            result['temperature'] = conversation.temperature
            
            return result
            
        except SQLAlchemyError as e:
            print(f"[DB ERROR] Błąd pobierania rozmowy: {e}")
            return None
        finally:
            session.close()
    
    def update_conversation_title(self, conversation_id: int, new_title: str) -> bool:
        """Aktualizuje tytuł rozmowy"""
        session = self.Session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            
            if conversation:
                conversation.title = new_title
                conversation.updated_at = datetime.now()
                session.commit()
                return True
            
            return False
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DB ERROR] Błąd aktualizacji tytułu: {e}")
            return False
        finally:
            session.close()
    
    def archive_conversation(self, conversation_id: int) -> bool:
        """Archiwizuje rozmowę"""
        session = self.Session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            
            if conversation:
                conversation.is_archived = True
                conversation.updated_at = datetime.now()
                session.commit()
                return True
            
            return False
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DB ERROR] Błąd archiwizacji: {e}")
            return False
        finally:
            session.close()
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Usuwa rozmowę i wszystkie jej wiadomości"""
        session = self.Session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            
            if conversation:
                session.delete(conversation)
                session.commit()
                print(f"[DB] Usunięto rozmowę ID: {conversation_id}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"[DB ERROR] Błąd usuwania rozmowy: {e}")
            return False
        finally:
            session.close()
    
    def search_conversations(self, query: str) -> List[Dict]:
        """Wyszukuje rozmowy po tytule lub treści"""
        session = self.Session()
        try:
            # Wyszukaj w tytułach
            conversations = session.query(Conversation).filter(
                Conversation.title.ilike(f'%{query}%')
            ).all()
            
            # Wyszukaj również w treści wiadomości
            message_convs = session.query(Conversation).join(Message).filter(
                Message.content.ilike(f'%{query}%')
            ).distinct().all()
            
            # Połącz wyniki
            all_convs = list(set(conversations + message_convs))
            
            return [conv.to_dict() for conv in all_convs]
            
        except SQLAlchemyError as e:
            print(f"[DB ERROR] Błąd wyszukiwania: {e}")
            return []
        finally:
            session.close()
    
    def get_statistics(self) -> Dict:
        """Pobiera statystyki użytkowania"""
        session = self.Session()
        try:
            total_conversations = session.query(func.count(Conversation.id)).scalar()
            total_messages = session.query(func.count(Message.id)).scalar()
            total_tokens = session.query(func.sum(Conversation.total_tokens)).scalar() or 0
            total_cost = session.query(func.sum(Conversation.total_cost)).scalar() or 0.0
            
            # Najczęściej używane modele
            model_usage = session.query(
                Conversation.model_name,
                func.count(Conversation.id).label('count')
            ).group_by(Conversation.model_name).all()
            
            return {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'total_cost': total_cost,
                'model_usage': {model: count for model, count in model_usage}
            }
            
        except SQLAlchemyError as e:
            print(f"[DB ERROR] Błąd pobierania statystyk: {e}")
            return {}
        finally:
            session.close()
    
    def generate_title_from_first_message(self, first_message: str, max_length: int = 50) -> str:
        """Generuje tytuł rozmowy na podstawie pierwszej wiadomości"""
        # Usuń zbędne białe znaki
        title = first_message.strip()
        
        # Jeśli jest pytanie, użyj go jako tytułu
        if '?' in title:
            title = title.split('?')[0] + '?'
        
        # Ogranicz długość
        if len(title) > max_length:
            title = title[:max_length-3] + '...'
        
        # Jeśli tytuł jest zbyt krótki, dodaj prefix
        if len(title) < 10:
            title = f"Rozmowa: {title}"
        
        return title
    
    def export_conversation_to_json(self, conversation_id: int, filepath: str) -> bool:
        """Eksportuje rozmowę do pliku JSON"""
        try:
            conversation = self.get_conversation_with_messages(conversation_id)
            
            if conversation:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(conversation, f, ensure_ascii=False, indent=2)
                
                print(f"[DB] Wyeksportowano rozmowę do: {filepath}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[DB ERROR] Błąd eksportu: {e}")
            return False

# Przykład użycia z GUI
def integrate_with_gui(gui_instance):
    """Integruje bazę danych z istniejącą aplikacją GUI"""
    
    # Dodaj menedżer bazy do GUI
    gui_instance.db = DatabaseManager()
    
    # Utwórz nową rozmowę przy starcie
    if not hasattr(gui_instance, 'current_conversation_id'):
        gui_instance.current_conversation_id = None
    
    # Modyfikuj metodę send_message żeby zapisywała do bazy
    original_send = gui_instance.send_message
    
    def enhanced_send_message():
        # Jeśli to pierwsza wiadomość, utwórz nową rozmowę
        if gui_instance.current_conversation_id is None and gui_instance.conversation_history:
            first_msg = gui_instance.conversation_history[0]['content'] if gui_instance.conversation_history else "Nowa rozmowa"
            title = gui_instance.db.generate_title_from_first_message(first_msg)
            
            conv_id = gui_instance.db.create_conversation(
                title=title,
                model_id=gui_instance.current_model.id,
                model_name=gui_instance.current_model.name,
                system_prompt=gui_instance.system_prompt,
                temperature=gui_instance.temperature_var.get()
            )
            gui_instance.current_conversation_id = conv_id
        
        # Wywołaj oryginalną metodę
        original_send()
    
    gui_instance.send_message = enhanced_send_message
    
    print("[DB] Zintegrowano bazę danych z GUI")

if __name__ == "__main__":
    # Test bazy danych
    db = DatabaseManager()
    
    # Utwórz testową rozmowę
    conv_id = db.create_conversation(
        title="Test rozmowy",
        model_id="claude-3-haiku",
        model_name="Claude 3 Haiku",
        system_prompt="Jesteś pomocnym asystentem."
    )
    
    if conv_id:
        # Dodaj testowe wiadomości
        db.add_message(conv_id, "user", "Cześć, jak się masz?", input_tokens=10)
        db.add_message(conv_id, "assistant", "Świetnie, dziękuję! Jak mogę Ci pomóc?", output_tokens=15, cost=0.0001)
        
        # Pobierz statystyki
        stats = db.get_statistics()
        print(f"[DB] Statystyki: {stats}")
        
        # Pobierz rozmowę
        conversation = db.get_conversation_with_messages(conv_id)
        print(f"[DB] Rozmowa: {conversation}")