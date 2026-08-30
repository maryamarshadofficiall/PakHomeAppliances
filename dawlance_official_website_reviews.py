import asyncio
import json
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from auto_save import save_to_master_db

TARGET_URL = "https://www.dawlance.com.pk/inverter-split-ac/mega-t-inverter-10-co-split-air-conditioners"
PRODUCT_JSON_FILE = "dawlance_exact_product_data.json"


async def scrape_dawlance_exact_reviews():
    print("[INFO] Launching browser to scrape all reviews with exact format...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("[INFO] Loading Product Page...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # 1. Scroll down to Reviews section
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            await page.wait_for_timeout(2000)

            # 2. Click on 'Reviews' Accordion to expand if collapsed
            try:
                accordion = page.locator('text="Reviews"').first
                if await accordion.is_visible():
                    await accordion.click(force=True)
                    print("[INFO] Expanded Reviews accordion panel.")
                    await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[NOTE] Accordion step: {e}")

            # 3. Pagination handling (Iterate through all pages/load more buttons)
            for page_num in range(1, 10):
                try:
                    load_more = page.locator('text="Load More"', 'button:has-text("More")', '.next-page').first
                    if await load_more.is_visible():
                        await load_more.click()
                        await page.wait_for_timeout(2000)
                    else:
                        break
                except:
                    break

            # 4. Extract HTML & Parse specific card fields
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            reviews_list = []

            # Target all card blocks containing "Do you find this comment useful?"
            cards = soup.find_all(lambda tag: tag.name in ['div', 'article', 'section'] and
                                   ('Kanwal J' in tag.text or 'Do you find this comment useful?' in tag.text or
                                    ('recently purchased' in tag.text.lower() and len(tag.text) < 1500)))

            # Fallback to general cards if specific match is empty
            if not cards:
                cards = soup.select('div[class*="review"], div[class*="comment"], .card')

            for card in cards:
                full_text = card.text.strip()

                # Exclude container elements that wrap multiple reviews
                if full_text.count("Do you find this comment useful?") > 1:
                    continue

                if len(full_text) > 30 and ("Kanwal" in full_text or "comment useful" in full_text or "inverter" in full_text.lower()):

                    # Clean up "Do you find this comment useful?" footer
                    cleaned_card_text = full_text.replace("Do you find this comment useful?", "").strip()

                    # Extract lines
                    lines = [line.strip() for line in cleaned_card_text.split('\n') if line.strip()]

                    # Extract Author, Date, Title, Body
                    author = "Kanwal J" if "Kanwal J" in cleaned_card_text else (lines[1] if len(lines) > 1 else "Customer")
                    title = lines[0] if lines else "Dawlance mega t plus inverter 0.75 ton"

                    # Date extraction (Format like 17-04-2026)
                    date_match = re.search(r'\d{2}-\d{2}-\d{4}', cleaned_card_text)
                    review_date = date_match.group(0) if date_match else "N/A"

                    # Extract main body text
                    body = cleaned_card_text
                    if date_match:
                        body = body.split(review_date)[-1].strip()
                    body = body.replace(title, "").replace(author, "").strip()

                    reviews_list.append({
                        "Author": author,
                        "Date": review_date,
                        "Title": title,
                        "Review_Text": body
                    })

            await browser.close()

            # Save Output
            if reviews_list:
                df = pd.DataFrame(reviews_list)
                df = df.drop_duplicates(subset=["Review_Text"])  # Remove duplicates
                df.to_csv("dawlance_official_cleaned_reviews.csv", index=False)

                print(f"\n[SUCCESS] Extracted {len(df)} Cleaned Reviews!")
                print("[SAVED CSV] dawlance_official_cleaned_reviews.csv")
                print("\nSample Scraped Review:")
                print(df.head(1).to_dict(orient='records'))

                # ==== Ye naya hissa: scraped reviews ko master DB mein merge karna ====
                reviews_text_list = df["Review_Text"].dropna().astype(str).tolist()

                # Product ki base details (title/price/specs) already-saved JSON se lein
                try:
                    with open(PRODUCT_JSON_FILE, encoding="utf-8") as f:
                        product_json = json.load(f)
                    p_title = product_json.get("title", "")
                    p_price = product_json.get("sale_price") or product_json.get("price")
                    p_specs = product_json.get("specifications", {})
                    p_features = product_json.get("key_attributes", [])
                except FileNotFoundError:
                    # Agar dawlance_official_scraper.py pehle nahi chala, to basic info se hi save karein
                    p_title = "Mega T+ Inverter 10 CO Inverter Split AC"
                    p_price = None
                    p_specs = {}
                    p_features = []

                save_to_master_db(
                    title=p_title,
                    url=TARGET_URL,
                    price=p_price,
                    specs=p_specs,
                    features=p_features,
                    reviews=reviews_text_list,
                    brand="Dawlance",
                    source="official_site",
                )
            else:
                print("\n[INFO] Could not capture cards. Let's run terminal to inspect structure.")

        except Exception as e:
            await browser.close()
            print(f"[ERROR] Scraping failed: {e}")


if __name__ == "__main__":
    asyncio.run(scrape_dawlance_exact_reviews())