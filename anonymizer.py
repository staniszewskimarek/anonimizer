import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "deepseek-r1:8b"
CHUNK_WORDS = 800
TIMEOUT = 120.0

SYSTEM_PROMPT = (
    "Jesteś asystentem anonimizującym dane osobowe.\n"
    "Zastąp WSZYSTKIE dane osobowe (PII) odpowiednimi placeholderami.\n"
    "Użyj: [IMIĘ], [NAZWISKO], [IMIĘ I NAZWISKO], [PESEL], [NIP], [REGON], "
    "[ADRES], [TELEFON], [EMAIL], [DATA URODZENIA], [NR DOWODU], "
    "[KONTO BANKOWE], [NR REJESTRACYJNY].\n"
    "Zwróć TYLKO zmodyfikowany tekst — bez komentarzy, bez wyjaśnień."
)


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
    return data["message"]["content"]


def anonymize_text(text: str, model: str = DEFAULT_MODEL) -> str:
    chunks = _split_into_chunks(text)
    anonymized_chunks: list[str] = []
    for chunk in chunks:
        if chunk.strip():
            anonymized_chunks.append(_call_ollama(chunk, model))
        else:
            anonymized_chunks.append(chunk)
    return "\n".join(anonymized_chunks)
