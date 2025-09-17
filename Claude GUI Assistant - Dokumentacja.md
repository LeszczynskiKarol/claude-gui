# Claude GUI Assistant - Dokumentacja

## 📋 Wymagania (requirements.txt)

```
anthropic>=0.25.0
customtkinter>=5.2.0
python-dotenv>=1.0.0
pillow>=10.0.0
```

## 🚀 Szybki start

### 1. Instalacja

```bash
# Klonuj lub stwórz folder projektu
mkdir claude-gui
cd claude-gui

# Zapisz kod jako claude_gui.py
# Zapisz requirements.txt

# Stwórz wirtualne środowisko
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows

# Zainstaluj zależności
pip install -r requirements.txt
```

### 2. Konfiguracja API

```bash
# Opcja 1: Plik .env
echo "ANTHROPIC_API_KEY=sk-ant-api03-xxxxx" > .env

# Opcja 2: Wprowadź klucz w GUI przy pierwszym uruchomieniu
```

### 3. Uruchomienie

```bash
python claude_gui.py
```

## 🎨 Funkcje GUI

### Panel główny

- **Chat w czasie rzeczywistym** z formatowaniem i kolorowaniem
- **Historia rozmowy** z zachowaniem kontekstu
- **Statystyki tokenów** i kosztów w czasie rzeczywistym
- **Dark mode** dla komfortu oczu

### Panel kontrolny

- **Wybór modelu** z rozwijanej listy
- **Informacje o modelu** - limity, koszty, możliwości
- **Tabela porównawcza** wszystkich 6 modeli Claude
- **Ustawienia** - system prompt, temperature
- **Historia** - podgląd i zarządzanie

### Statystyki sesji

- Liczba wiadomości
- Tokeny wejściowe/wyjściowe
- Koszt bieżący i całkowity
- Ostatni koszt wiadomości

## 📊 Specyfikacja modeli

| Model          | Max Output | Context | Koszt Input | Koszt Output | Najlepszy do                |
| -------------- | ---------- | ------- | ----------- | ------------ | --------------------------- |
| **Opus 4.1**   | 32,000     | 200K    | $15/1M      | $75/1M       | Najbardziej złożone zadania |
| **Opus 4**     | 32,000     | 200K    | $12/1M      | $60/1M       | Złożone zadania             |
| **Sonnet 4**   | 64,000     | 200K/1M | $3/1M       | $15/1M       | Balans wydajność/koszt      |
| **Sonnet 3.7** | 64,000     | 200K    | $3/1M       | $15/1M       | Extended thinking           |
| **Haiku 3.5**  | 8,192      | 200K    | $1/1M       | $5/1M        | Szybkie odpowiedzi          |
| **Haiku 3**    | 4,096      | 200K    | $0.25/1M    | $1.25/1M     | Najprostsze zadania         |

## 💡 Wskazówki użytkowania

### Wybór modelu

- **Opus 4.1**: Programowanie, analiza, złożone reasoning
- **Sonnet 4**: Długie dokumenty (do 64K tokenów output!)
- **Haiku 3.5**: Czat, szybkie odpowiedzi, FAQ

### Optymalizacja kosztów

1. Używaj Haiku do prostych zadań
2. Sonnet 4 ma najlepszy stosunek jakość/cena
3. Opus tylko gdy potrzebujesz maksymalnej inteligencji

### Skróty klawiszowe

- `Ctrl+Enter` - wyślij wiadomość
- `Shift+Enter` - nowa linia w wiadomości

## 🔧 Rozwiązywanie problemów

### "Błąd API"

- Sprawdź klucz API
- Sprawdź limity na koncie
- Sprawdź połączenie internetowe

### "Module not found"

```bash
pip install --upgrade anthropic customtkinter python-dotenv
```

### Problemy z GUI na Linux

```bash
# Zainstaluj tkinter
sudo apt-get install python3-tk
```

## 🚀 Zaawansowane funkcje

### Eksport rozmów

- Format JSON z pełnymi metadanymi
- Statystyki tokenów i kosztów
- Możliwość wczytania później

### Streaming (TODO)

Aby dodać streaming odpowiedzi:

```python
# W send_api_request() zmień na:
stream = self.client.messages.create(
    stream=True,
    # ... reszta parametrów
)
for chunk in stream:
    # Aktualizuj UI chunk po chunk
```

### Integracja z plikami

Możesz łatwo dodać obsługę plików:

```python
# Dodaj do GUI przycisk upload
def upload_file():
    file_path = filedialog.askopenfilename()
    with open(file_path, 'rb') as f:
        content = f.read()
    # Prześlij do API jako base64
```

## 📈 Monitorowanie kosztów

Aplikacja śledzi koszty w czasie rzeczywistym:

- **Koszt sesji**: Całkowity koszt od uruchomienia
- **Ostatni koszt**: Koszt ostatniej wymiany
- **Tokeny**: Dokładne liczby wejścia/wyjścia

### Przykładowe koszty miesięczne

- Casual (1000 msg/mies, Haiku): ~$2
- Regular (5000 msg/mies, Sonnet): ~$30
- Power User (10000 msg/mies, mix): ~$100

## 🎯 Najlepsze praktyki

1. **Zacznij od tańszego modelu** - często Haiku wystarcza
2. **Używaj system prompts** - poprawiają jakość odpowiedzi
3. **Zapisuj ważne rozmowy** - eksport do JSON
4. **Monitoruj koszty** - szczególnie przy Opus
5. **Eksperymentuj z temperature** - 0.3 dla faktów, 0.8 dla kreatywności

## 🔗 Przydatne linki

- [Anthropic Console](https://console.anthropic.com/)
- [API Documentation](https://docs.anthropic.com/)
- [Pricing](https://anthropic.com/pricing)
- [Model Cards](https://docs.anthropic.com/models)
