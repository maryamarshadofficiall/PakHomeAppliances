from database import init_db, ingest_product, ingest_reviews
from nlp.text_cleaning import clean_text
from nlp.sentiment import token_sentiment


def save_to_master_db(title, url, price, specs, features, reviews, brand, source):
    """
    Kisi bhi scraper ka scraped data lekar central database mein save karta hai.

    title    : str  -> product ka naam
    url      : str  -> product ka link
    price    : str/float -> price
    specs    : dict -> {"Capacity": "1.5 Ton", "Warranty": "10 Years", ...}
    features : list -> ["Self Cleaning", "WiFi Enabled", ...]
    reviews  : list -> ["review text 1", "review text 2", ...]
    brand    : str  -> "Haier" / "Dawlance" / "PEL" etc.
    source   : str  -> "daraz" / "official_site" etc.
    """
    init_db()  # DB pehle se ho to kuch nahi hota, safe hai

    product_dict = {
        "title": title,
        "url": url,
        "price": price,
        "brand": brand,
        "specifications": specs,
        "features_and_highlights": features,
    }

    pid = ingest_product(product_dict, source=source)

    if reviews:
        ingest_reviews(pid, reviews, clean_text, token_sentiment)

    print(f"[SAVED TO MASTER DB] {title[:50]}  (product_id={pid})")
    return pid