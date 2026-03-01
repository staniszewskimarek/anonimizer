import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "deepseek-r1:8b"
CHUNK_WORDS = 800
TIMEOUT = 120.0

SYSTEM_PROMPT = """\
Jesteś narzędziem do anonimizacji tekstu. Zastępujesz dane osobowe (PII) placeholderami.

BEZWZGLĘDNE ZASADY:
1. Zwróć WYŁĄCZNIE przetworzony tekst — nic więcej.
2. NIE dodawaj żadnych słów od siebie: żadnych nagłówków, wstępów, komentarzy, wyjaśnień, list punktowanych, odmów ani instrukcji.
3. NIE zaczynaj odpowiedzi od słów takich jak "Oto", "Zmodyfikowany", "Tekst", "Zastąpiłem" itp.
4. NIE odmawiaj przetwarzania — zawsze zwróć tekst z placeholderami.
5. Używaj WYŁĄCZNIE tych placeholderów (nie twórz własnych):
   [IMIĘ], [NAZWISKO], [IMIĘ I NAZWISKO], [PESEL], [NIP], [REGON],
   [ADRES], [TELEFON], [EMAIL], [DATA URODZENIA], [NR DOWODU],
   [KONTO BANKOWE], [NR REJESTRACYJNY]
6. Zachowaj oryginalną strukturę, interpunkcję i formatowanie tekstu.
7. Fragmenty tekstu niebędące danymi osobowymi przepisz BEZ ZMIAN.

PRZYKŁAD:
Wejście:
  Jan Kowalski, PESEL 85010112345, tel. 600 123 456, jan.kowalski@firma.pl
  Mieszka przy ul. Lipowej 12, Warszawa.
Wyjście:
  [IMIĘ I NAZWISKO], PESEL [PESEL], tel. [TELEFON], [EMAIL]
  Mieszka przy [ADRES].\
"""


def _split_into_chunks(text: str, max_words: int = CHUNK_WORDS) -> list[str]:
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    current_word_count = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_word_count + para_words > max_words and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_word_count = 0
        current_lines.append(para)
        current_word_count += para_words

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks or [""]


_JUNK_PREFIXES = (
    "oto zmodyfikowany tekst",
    "oto tekst",
    "zmodyfikowany tekst",
    "przetworzony tekst",
    "wynik anonimizacji",
    "oto wynik",
)


def _strip_junk(text: str) -> str:
    """Remove common model preambles that appear despite instructions."""
    line0 = text.split("\n")[0].rstrip(": \t").lower()
    if any(line0.startswith(p) for p in _JUNK_PREFIXES):
        text = "\n".join(text.split("\n")[1:]).lstrip("\n")
    return text.strip()


def _call_ollama(chunk: str, model: str) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk},
        ],
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
    data = response.json()
    return _strip_junk(data["message"]["content"])


def anonymize_text(text: str, model: str = DEFAULT_MODEL) -> str:
    chunks = _split_into_chunks(text)
    anonymized_chunks: list[str] = []
    for chunk in chunks:
        if chunk.strip():
            anonymized_chunks.append(_call_ollama(chunk, model))
        else:
            anonymized_chunks.append(chunk)
    return "\n".join(anonymized_chunks)
