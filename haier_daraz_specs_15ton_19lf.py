import asyncio
import json
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from auto_save import save_to_master_db

PRODUCT_URL = "https://www.daraz.pk/products/haier-ac-15-ton-dc-inverter-model-ac-hsu-19lf-new-model-2025-19000-btu-ups-enabled-self-cleaning-turbo-cooling-wide-voltage-100-copper-full-btu-white-color-air-conditioner10-years-warrantyhaier-free-installation-i144376789.html"


async def scrape_daraz_product_details_view_more():
    print("[INFO] Opening Daraz Product Page...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # 1. Scroll down to Product Details Section
            print("[INFO] Scrolling down to 'Product Details' section...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4);")
            await page.wait_for_timeout(2000)

            # 2. Click VIEW MORE / SEE MORE Button
            print("[INFO] Looking for 'VIEW MORE' button...")
            view_more_selectors = [
                'text="VIEW MORE"',
                'text="View More"',
                'text="SEE MORE"',
                '.pdp-view-more-btn',
                'button:has-text("VIEW MORE")',
                '.expand-button'
            ]

            clicked = False
            for selector in view_more_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        print(f"[SUCCESS] Clicked '{selector}' button!")
                        clicked = True
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            if not clicked:
                # JS Click Fallback
                await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button, div, span, a'));
                    const viewMore = buttons.find(b => b.innerText && b.innerText.trim().toUpperCase().includes('VIEW MORE'));
                    if (viewMore) viewMore.click();
                }""")
                await page.wait_for_timeout(2000)

            # 3. Extract Full Content from Product Details
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Title & Price
            title_elem = soup.select_one('.pdp-mod-product-badge-title, h1')
            title = title_elem.text.strip() if title_elem else "Haier HSU-19LF"

            price_elem = soup.select_one('.pdp-price_type_normal, .pdp-price')
            price = price_elem.text.strip() if price_elem else "N/A"

            # Product Details Box Parsing
            details_box = soup.select_one('.pdp-product-detail, .pdp-mod-product-detail, .detail-content')

            extracted_features = []
            specs_dict = {}

            if details_box:
                # Extract all bullet points / list items
                list_items = details_box.find_all('li')
                for li in list_items:
                    text = li.text.strip()
                    if ':' in text:
                        parts = text.split(':', 1)
                        specs_dict[parts[0].strip()] = parts[1].strip()
                    elif text:
                        extracted_features.append(text)

                # If no list items, parse text lines
                if not extracted_features and not specs_dict:
                    lines = [line.strip() for line in details_box.text.split('\n') if line.strip()]
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':', 1)
                            specs_dict[parts[0].strip()] = parts[1].strip()
                        elif len(line) > 5:
                            extracted_features.append(line)

            # Also check Specifications Table (Side/Bottom grid)
            spec_rows = soup.select('.pdp-general-features li, .key-value-item, .sku-prop')
            for row in spec_rows:
                k_elem = row.select_one('.key-title, .key, span:first-child')
                v_elem = row.select_one('.key-value, .value, span:last-child')
                if k_elem and v_elem:
                    k = k_elem.text.replace(':', '').strip()
                    v = v_elem.text.strip()
                    if k and v:
                        specs_dict[k] = v

            await browser.close()

            print(f"\n[RESULTS]")
            print(f"Product: {title}")
            print(f"Price: {price}")
            print(f"Features / Highlights Extracted: {len(extracted_features)}")
            print(f"Specifications Extracted: {len(specs_dict)}")

            # 4. Save CSV & JSON Files
            full_data = {
                "title": title,
                "price": price,
                "product_url": PRODUCT_URL,
                "features_and_highlights": extracted_features,
                "specifications": specs_dict
            }

            with open("haier_19lf_daraz_full_details.json", "w", encoding="utf-8") as f:
                json.dump(full_data, f, indent=4, ensure_ascii=False)

            if extracted_features:
                pd.DataFrame(extracted_features, columns=["Product Feature / Detail"]).to_csv("haier_19lf_daraz_features.csv", index=False)
                print("[SAVED CSV] 'haier_19lf_daraz_features.csv'")

            if specs_dict:
                pd.DataFrame(list(specs_dict.items()), columns=["Specification", "Value"]).to_csv("haier_19lf_daraz_specs.csv", index=False)
                print("[SAVED CSV] 'haier_19lf_daraz_specs.csv'")

            # ==== Ye naya hissa: scraped specs/features ko master DB mein merge karna ====
            # Ye scraper reviews nahi nikalta (wo kaam haier_scraper.py karta hai),
            # isliye yahan reviews=[] pass kar rahe hain — ingest_product specs/price/features
            # update kar dega, aur agar is product ki reviews pehle se DB mein hain
            # (haier_scraper.py se) to wo waisi hi rahengi, delete nahi hongi.
            save_to_master_db(
                title=title,
                url=PRODUCT_URL,
                price=price,
                specs=specs_dict,
                features=extracted_features,
                reviews=[],
                brand="Haier",
                source="daraz",
            )

        except Exception as e:
            await browser.close()
            print(f"[ERROR] Failed to scrape: {e}")


if __name__ == "__main__":
    asyncio.run(scrape_daraz_product_details_view_more())