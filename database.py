import sqlite3
import hashlib
import json
import re
from datetime import datetime

from config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        brand TEXT,
        title TEXT,
        price REAL,
        original_price REAL,
        url TEXT UNIQUE,
        specs_json TEXT,
        features_json TEXT,
        source TEXT,
        first_added TEXT,
        last_updated TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_hash TEXT PRIMARY KEY,
        product_id TEXT,
        raw_text TEXT,
        clean_text TEXT,
        sentiment_score REAL,
        sentiment_label TEXT,
        scraped_at TEXT,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    """)
    conn.commit()
    conn.close()


def make_product_id(url_or_title):
    return hashlib.md5(url_or_title.strip().lower().encode()).hexdigest()[:16]


def clean_price(p):
    if p is None:
        return None
    digits = re.sub(r"[^\d.]", "", str(p))
    return float(digits) if digits else None


def normalize_product(raw):
    title = raw.get("title") or raw.get("name") or ""
    url = raw.get("url") or raw.get("product_url") or ""
    price = raw.get("price") or raw.get("sale_price") or None
    original_price = raw.get("original_price") or None
    brand = raw.get("brand")
    if not brand:
        title_lower = title.lower()
        if "haier" in title_lower:
            brand = "Haier"
        elif "dawlance" in title_lower:
            brand = "Dawlance"
        elif "pel" in title_lower:
            brand = "PEL"
        elif "orient" in title_lower:
            brand = "Orient"
        elif "gree" in title_lower:
            brand = "Gree"
        else:
            brand = "Unknown"
    specs = raw.get("specifications") or raw.get("specs") or {}
    features = (raw.get("features_and_highlights") or raw.get("key_attributes")
                or raw.get("features") or [])

    return {
        "product_id": make_product_id(url or title),
        "brand": brand,
        "title": title.strip(),
        "price": clean_price(price),
        "original_price": clean_price(original_price),
        "url": url,
        "specs": specs,
        "features": features,
    }


def ingest_product(raw_product_dict, source="scraper"):
    p = normalize_product(raw_product_dict)
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute("SELECT product_id FROM products WHERE product_id = ?", (p["product_id"],))
    exists = cur.fetchone()

    if exists:
        cur.execute("""
            UPDATE products SET brand=?, price=?, original_price=?, specs_json=?, features_json=?, last_updated=?
            WHERE product_id=?
        """, (p["brand"], p["price"], p["original_price"], json.dumps(p["specs"]),
              json.dumps(p["features"]), now, p["product_id"]))
        print(f"[UPDATED] {p['title'][:60]}")
    else:
        cur.execute("""
            INSERT INTO products (product_id, brand, title, price, original_price, url,
                                   specs_json, features_json, source, first_added, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (p["product_id"], p["brand"], p["title"], p["price"], p["original_price"],
              p["url"], json.dumps(p["specs"]), json.dumps(p["features"]), source, now, now))
        print(f"[ADDED]   {p['title'][:60]}")

    conn.commit()
    conn.close()
    return p["product_id"]


def review_hash(product_id, text):
    return hashlib.md5((product_id + text.strip().lower()).encode()).hexdigest()


def ingest_reviews(product_id, review_texts, clean_fn, sentiment_fn):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    added, skipped = 0, 0

    for raw_text in review_texts:
        clean = clean_fn(str(raw_text))
        if len(clean) < 3:
            continue
        h = review_hash(product_id, clean)

        cur.execute("SELECT review_hash FROM reviews WHERE review_hash = ?", (h,))
        if cur.fetchone():
            skipped += 1
            continue

        score, label = sentiment_fn(clean)
        cur.execute("""
            INSERT INTO reviews (review_hash, product_id, raw_text, clean_text,
                                  sentiment_score, sentiment_label, scraped_at)
            VALUES (?,?,?,?,?,?,?)
        """, (h, product_id, raw_text, clean, float(score), label, now))
        added += 1

    conn.commit()
    conn.close()
    print(f"          reviews: +{added} new, {skipped} already existed")


def load_all_products():
    import pandas as pd
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM products", conn)
    conn.close()
    df["specs"] = df["specs_json"].apply(json.loads)
    df["features"] = df["features_json"].apply(json.loads)
    return df


def load_all_reviews():
    import pandas as pd
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM reviews", conn)
    conn.close()
    return df