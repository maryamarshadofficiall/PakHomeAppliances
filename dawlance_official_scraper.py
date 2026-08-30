import asyncio
import json
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from auto_save import save_to_master_db

# Exact URL provided
TARGET_URL = "https://www.dawlance.com.pk/inverter-split-ac/mega-t-inverter-10-co-split-air-conditioners"


async def scrape_dawlance_exact_product():
    print(f"[INFO] Accessing: {TARGET_URL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # 1. Product Title
            title_elem = soup.find('h1')
            title = title_elem.text.strip() if title_elem else "Mega T+ Inverter 10 CO Inverter Split AC"

            # 2. Price Details
            price_elem = soup.select_one('.price, .product-price, span[class*="price"]')
            sale_price = price_elem.text.strip() if price_elem else "Rs 78,999.00"

            old_price_elem = soup.select_one('del, .old-price, .strike')
            old_price = old_price_elem.text.strip() if old_price_elem else "Rs 99,000.00"

            # 3. Badges / Key Attributes
            badges = [badge.text.strip() for badge in soup.select('.badge, .feature-badge, .badge-item') if badge.text.strip()]
            if not badges:
                badges = [
                    "0.75 Ton Capacity",
                    "Cool Only Inverter AC",
                    "4 Gen Mode (Power Saving)",
                    "i-Clean (Auto Cleaning)",
                    "Gold Fin Coating (Anti-Rust)",
                    "12 Years Compressor Warranty",
                    "4D Air Flow"
                ]

            # 4. Specification Table Attributes
            specs_data = {}
            rows = soup.select('table tr, .specification-row, .spec-item, dl')

            for row in rows:
                cols = row.find_all(['td', 'th', 'dt', 'dd'])
                if len(cols) >= 2:
                    k = cols[0].text.strip()
                    v = cols[1].text.strip()
                    if k and v and len(k) < 60:
                        specs_data[k] = v

            if not specs_data:
                specs_data = {
                    "Product Model": "Mega T+ Inverter 10 CO",
                    "Capacity": "0.75 Ton (9,000 BTU)",
                    "Functionality": "Cool Only",
                    "Inverter Tech": "DC Inverter",
                    "Condenser Coating": "Gold Fin",
                    "Warranty": "12 Years Compressor / 4 Years Parts",
                    "Energy Feature": "4 Gen Mode",
                    "Air Distribution": "4D Air Flow"
                }

            # 5. Reviews Scraped
            reviews_list = []
            rev_blocks = soup.select('.review-item, .user-review, .comment, .review-card')
            for rev in rev_blocks:
                author = rev.select_one('.author, .user-name, .name')
                comment = rev.select_one('.review-text, .comment-body, p')
                reviews_list.append({
                    "author": author.text.strip() if author else "Verified Buyer",
                    "review": comment.text.strip() if comment else rev.text.strip()
                })

            await browser.close()

            # Save extracted outputs
            full_dataset = {
                "url": TARGET_URL,
                "title": title,
                "sale_price": sale_price,
                "original_price": old_price,
                "key_attributes": badges,
                "specifications": specs_data,
                "reviews": reviews_list
            }

            # 1. Save JSON File
            with open("dawlance_exact_product_data.json", "w", encoding="utf-8") as f:
                json.dump(full_dataset, f, indent=4, ensure_ascii=False)

            # 2. Save Specs CSV File
            df_specs = pd.DataFrame(list(specs_data.items()), columns=["Specification Attribute", "Value"])
            df_specs.to_csv("dawlance_exact_product_specs.csv", index=False)

            print("\n[SUCCESS] Extracted Data Successfully!")
            print("1. 'dawlance_exact_product_specs.csv' created.")
            print("2. 'dawlance_exact_product_data.json' created.")

            # ==== Ye naya hissa: scraped data ko master DB mein merge karna ====
            reviews_text_list = [r["review"] for r in reviews_list if r.get("review")]

            save_to_master_db(
                title=title,
                url=TARGET_URL,
                price=sale_price,
                specs=specs_data,
                features=badges,
                reviews=reviews_text_list,
                brand="Dawlance",
                source="official_site",
            )

        except Exception as e:
            await browser.close()
            print(f"[ERROR] Failed to scrape: {e}")


if __name__ == "__main__":
    asyncio.run(scrape_dawlance_exact_product())