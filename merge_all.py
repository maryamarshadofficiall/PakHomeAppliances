import json
import pandas as pd
from database import init_db, ingest_product, ingest_reviews
from nlp.text_cleaning import clean_text
from nlp.sentiment import token_sentiment


def load_json_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_reviews_list(csv_path, text_column_candidates=("Review_Text", "review")):
    df = pd.read_csv(csv_path)
    col = next((c for c in text_column_candidates if c in df.columns), None)
    if col is None:
        print(f"  [SKIP] {csv_path} — koi review column nahi mila")
        return []
    return df[col].dropna().astype(str).tolist()


def merge_product(json_path, review_csvs, source, brand_override=None):
    print(f"\nMerging: {json_path}")
    raw = load_json_file(json_path)
    if brand_override:
        raw["brand"] = brand_override
    pid = ingest_product(raw, source=source)
    for csv_path in review_csvs:
        reviews = get_reviews_list(csv_path)
        if reviews:
            ingest_reviews(pid, reviews, clean_text, token_sentiment)
    return pid


if __name__ == "__main__":
    init_db()

    merge_product(
        json_path="dawlance_exact_product_data.json",
        review_csvs=[
            "dawlance_mega_t10_200_pages_reviews.csv",
            "dawlance_official_cleaned_reviews.csv",
        ],
        source="dawlance_official",
        brand_override="Dawlance",
    )

    merge_product(
        json_path="haier_19lf_daraz_full_details.json",
        review_csvs=["haier_reviews.csv"],
        source="daraz",
    )

    merge_product(
        json_path="haier_pearl_black_hsu18hfp_full_details.json",
        review_csvs=["haier_pearl_black_hsu18hfp_reviews.csv"],
        source="daraz",
    )

    print("\n=== DONE — sab data data/products_master.db mein merge ho gaya ===")