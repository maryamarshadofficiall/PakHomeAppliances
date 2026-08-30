from nlp.text_cleaning import tokenize

POSITIVE_WORDS = {
    "acha", "achi", "achha", "zabardast", "shandar", "behtareen", "mast", "kamal",
    "satisfied", "recommend", "recommended", "perfect", "excellent", "good", "great",
    "best", "love", "happy", "sahi", "top", "nice", "impressive", "efficient",
    "smooth", "reliable", "quiet", "quick", "fast", "worth", "fine",
}
NEGATIVE_WORDS = {
    "ganda", "bekar", "bakwas", "kharab", "waste", "faltu", "bura", "worst",
    "problem", "issue", "complaint", "shor", "awaz", "bad", "poor", "noise",
    "slow", "loud", "defective", "disappointed", "fake", "late", "delay", "damaged",
}
NEGATION_WORDS = {"nahi", "nahin", "na", "not", "never", "no", "don't", "didn't", "isn't", "wasn't"}
INTENSIFIERS = {"bohat", "bahut", "bhot", "bht", "bilkul", "very", "too", "zyada", "extremely", "highly", "super"}


def token_sentiment(text):
    tokens = tokenize(text)
    score, hits = 0.0, 0
    for i, word in enumerate(tokens):
        polarity = 1 if word in POSITIVE_WORDS else -1 if word in NEGATIVE_WORDS else 0
        if polarity == 0:
            continue
        window = tokens[max(0, i - 2):i]
        if any(w in NEGATION_WORDS for w in window):
            polarity = -polarity
        weight = 1.5 if any(w in INTENSIFIERS for w in window) else 1.0
        score += polarity * weight
        hits += 1

    if hits == 0:
        return 0.0, "Neutral"
    norm = round(score / hits, 3)
    label = "Positive" if norm > 0.15 else "Negative" if norm < -0.15 else "Neutral"
    return norm, label