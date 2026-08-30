import re


def clean_text(text):
    if not isinstance(text, str):
        return ""
    t = text.strip()
    t = re.split(r"Read more", t)[0]
    t = re.sub(r"\s*\d+\s*$", "", t)
    t = re.sub(r"Color Family:\s*\w+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def tokenize(text):
    return re.findall(r"[a-zA-Z]+", text.lower())