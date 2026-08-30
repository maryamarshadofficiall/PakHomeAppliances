import asyncio
import csv
import json
import pandas as pd
from playwright.async_api import async_playwright

from auto_save import save_to_master_db

# Exact Pearl Inverter Series (Black) HSU-18HFP Target URL
TARGET_URL = "https://www.daraz.pk/products/haier-inverter-ac-hsu-18hfp-cab-pearl-inverter-series-15-ton-dc-inverter-ups-enabled-self-cleaning-wifi-enabled-turbo-cooling-black-color-10-years-warranty-haier-free-installation-i335655697.html"
MAX_PAGES = 7  # Total 7 pages
OUTPUT_FILE = "haier_pearl_black_hsu18hfp_reviews.csv"
PRODUCT_JSON_FILE = "haier_pearl_black_hsu18hfp_full_details.json"


async def scrape_haier_black_pearl():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[INFO] Opening Haier Pearl Black (HSU-18HFP) Product Page...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)

        # Scroll to load reviews section
        print("[INFO] Navigating down to reviews section...")
        for _ in range(7):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(800)

        # Initialize CSV File with headers
        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["id", "page", "user", "date", "review"])
            writer.writeheader()

        total_scraped = 0
        current_page = 1

        while current_page <= MAX_PAGES:
            await page.wait_for_timeout(3000)

            # Query all review items on the current page
            review_elements = await page.query_selector_all(".review-item, .item")
            page_data = []

            for item in review_elements:
                content_el = await item.query_selector(".content, .item-content")
                review_text = await content_el.inner_text() if content_el else ""
                review_text = review_text.strip().replace("\n", " ")

                user_el = await item.query_selector(".user-name, .user-name-wrapper")
                user_name = await user_el.inner_text() if user_el else "Anonymous"
                user_name = user_name.strip()

                date_el = await item.query_selector(".titleExt, .date")
                review_date = await date_el.inner_text() if date_el else "N/A"
                review_date = review_date.strip()

                if review_text:
                    total_scraped += 1
                    page_data.append({
                        "id": total_scraped,
                        "page": current_page,
                        "user": user_name,
                        "date": review_date,
                        "review": review_text
                    })

            # Append page data to CSV immediately
            if page_data:
                with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=["id", "page", "user", "date", "review"])
                    writer.writerows(page_data)

            print(f"[Page {current_page}/{MAX_PAGES}] Scraped {len(page_data)} reviews. (Total Collected: {total_scraped})")

            # Check and Click Next Page Pagination Button
            next_btn = await page.query_selector("li.ant-pagination-next:not(.ant-pagination-disabled) button, .next-pagination-item.next:not(.disabled)")

            if next_btn and current_page < MAX_PAGES:
                try:
                    await next_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await next_btn.click(force=True)
                    current_page += 1
                except Exception as err:
                    print(f"[INFO] Pagination end or click issue: {err}")
                    break
            else:
                print("[INFO] Reached the last available review page.")
                break

        await browser.close()
        print(f"\n[SUCCESS] Completed! All {total_scraped} reviews saved into '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    asyncio.run(scrape_haier_black_pearl())

    # ==== Ye naya hissa: scraped reviews ko master DB mein merge karna ====

    # Reviews CSV se load karein jo abhi scrape hui
    reviews_df = pd.read_csv(OUTPUT_FILE)
    reviews_list = reviews_df["review"].dropna().astype(str).tolist()

    # Product ki base details (title/price/specs) yahan se lein
    with open(PRODUCT_JSON_FILE, encoding="utf-8") as f:
        product_json = json.load(f)

    save_to_master_db(
        title=product_json.get("title", ""),
        url=product_json.get("product_url") or product_json.get("url") or TARGET_URL,
        price=product_json.get("price") or product_json.get("sale_price"),
        specs=product_json.get("specifications", {}),
        features=product_json.get("features_and_highlights", []),
        reviews=reviews_list,
        brand="Haier",
        source="daraz",
    )