import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from auto_save import save_to_master_db

MAX_REVIEW_PAGES = 50


# ======================================================================
# SOURCE 1: DARAZ
# ======================================================================
async def _scrape_daraz_async(product_url, brand_name):
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

        print(f"[DARAZ] Opening: {product_url}")
        await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.select_one('.pdp-mod-product-badge-title, h1')
        title = title_elem.text.strip() if title_elem else "Unknown Product"
        price_elem = soup.select_one('.pdp-price_type_normal, .pdp-price')
        price = price_elem.text.strip() if price_elem else "N/A"

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4);")
        await page.wait_for_timeout(2000)

        for selector in ['text="VIEW MORE"', 'text="View More"', 'text="SEE MORE"',
                          '.pdp-view-more-btn', 'button:has-text("VIEW MORE")', '.expand-button']:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click(force=True)
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        details_box = soup.select_one('.pdp-product-detail, .pdp-mod-product-detail, .detail-content')
        extracted_features, specs_dict = [], {}

        if details_box:
            for li in details_box.find_all('li'):
                text = li.text.strip()
                if ':' in text:
                    k, v = text.split(':', 1)
                    specs_dict[k.strip()] = v.strip()
                elif text:
                    extracted_features.append(text)

        for row in soup.select('.pdp-general-features li, .key-value-item, .sku-prop'):
            k_elem = row.select_one('.key-title, .key, span:first-child')
            v_elem = row.select_one('.key-value, .value, span:last-child')
            if k_elem and v_elem:
                k, v = k_elem.text.replace(':', '').strip(), v_elem.text.strip()
                if k and v:
                    specs_dict[k] = v

        for _ in range(7):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(800)

        all_reviews = []
        current_page = 1
        while current_page <= MAX_REVIEW_PAGES:
            await page.wait_for_timeout(3000)
            review_elements = await page.query_selector_all(".review-item, .item")
            for item in review_elements:
                content_el = await item.query_selector(".content, .item-content")
                review_text = await content_el.inner_text() if content_el else ""
                review_text = review_text.strip().replace("\n", " ")
                if review_text:
                    all_reviews.append(review_text)

            print(f"[DARAZ] Page {current_page} -> total reviews so far: {len(all_reviews)}")
            next_btn = await page.query_selector(
                "li.ant-pagination-next:not(.ant-pagination-disabled) button, .next-pagination-item.next:not(.disabled)"
            )
            if next_btn and current_page < MAX_REVIEW_PAGES:
                try:
                    await next_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await next_btn.click(force=True)
                    current_page += 1
                except Exception:
                    break
            else:
                break

        await browser.close()
        print(f"[DARAZ RESULT] {title} | {price} | {len(all_reviews)} reviews")

        save_to_master_db(
            title=title, url=product_url, price=price, specs=specs_dict,
            features=extracted_features, reviews=all_reviews,
            brand=brand_name, source="daraz",
        )


def scrape_daraz(product_url, brand_name):
    """Daraz product link se title/price/specs/features/reviews scrape karke DB mein save karta hai."""
    asyncio.run(_scrape_daraz_async(product_url, brand_name))


# ======================================================================
# SOURCE 2: OFFICIAL BRAND WEBSITE
# ======================================================================
async def _scrape_official_async(product_url, brand_name, selectors=None):
    """
    selectors (optional dict) se custom CSS selectors diye ja sakte hain agar
    default guesses us website pe kaam na karein, e.g.:
    selectors = {"title": "h1.product-title", "price": ".price-tag"}
    """
    selectors = selectors or {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print(f"[OFFICIAL SITE] Opening: {product_url}")
        await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        title_elem = soup.select_one(selectors.get("title", "h1"))
        title = title_elem.text.strip() if title_elem else "Unknown Product"

        price_elem = soup.select_one(selectors.get("price", '.price, .product-price, span[class*="price"]'))
        price = price_elem.text.strip() if price_elem else "N/A"

        specs_dict = {}
        rows = soup.select(selectors.get("specs_rows", "table tr, .specification-row, .spec-item, dl"))
        for row in rows:
            cols = row.find_all(['td', 'th', 'dt', 'dd'])
            if len(cols) >= 2:
                k, v = cols[0].text.strip(), cols[1].text.strip()
                if k and v and len(k) < 60:
                    specs_dict[k] = v

        badges = [b.text.strip() for b in soup.select(selectors.get("features", ".badge, .feature-badge, .badge-item")) if b.text.strip()]

        review_texts = []
        rev_blocks = soup.select(selectors.get("reviews", ".review-item, .user-review, .comment, .review-card"))
        for rev in rev_blocks:
            comment = rev.select_one('.review-text, .comment-body, p')
            text = comment.text.strip() if comment else rev.text.strip()
            if text:
                review_texts.append(text)

        await browser.close()
        print(f"[OFFICIAL RESULT] {title} | {price} | specs:{len(specs_dict)} | reviews:{len(review_texts)}")

        save_to_master_db(
            title=title, url=product_url, price=price, specs=specs_dict,
            features=badges, reviews=review_texts,
            brand=brand_name, source="official_site",
        )


def scrape_official_site(product_url, brand_name, selectors=None):
    """
    Brand ki apni official website se scrape karke DB mein save karta hai.
    Agar default selectors kaam na karein (kyunke har site alag banti hai),
    selectors dict de kar override kar sakti hain:
        scrape_official_site(url, "PEL", selectors={"title": "h1.pdp-title", "price": ".final-price"})
    """
    asyncio.run(_scrape_official_async(product_url, brand_name, selectors))


# ======================================================================
# SOURCE 3: YOUTUBE (comments as "reviews")
# ======================================================================
def scrape_youtube(video_url, brand_name, product_title):
    """
    YouTube video ke comments ko reviews ki tarah treat karke DB mein save karta hai.
    Koi API key nahi chahiye. Pehli dafa chalane se pehle terminal mein ye install karein:
        pip install youtube-comment-downloader
    """
    from youtube_comment_downloader import YoutubeCommentDownloader

    print(f"[YOUTUBE] Fetching comments from: {video_url}")
    downloader = YoutubeCommentDownloader()
    comments = downloader.get_comments_from_url(video_url, sort_by=0)

    review_texts = []
    for c in comments:
        text = c.get("text", "").strip()
        if text and len(text) > 3:
            review_texts.append(text)
        if len(review_texts) >= 500:   # safety cap
            break

    print(f"[YOUTUBE RESULT] {len(review_texts)} comments collected")

    save_to_master_db(
        title=product_title,
        url=video_url,
        price=None,
        specs={},
        features=[],
        reviews=review_texts,
        brand=brand_name,
        source="youtube",
    )


# ======================================================================
# SOURCE 4: FACEBOOK (manual paste — automated scraping unreliable/against ToS)
# ======================================================================
def add_facebook_reviews_manually(post_url, brand_name, product_title, review_texts_list):
    """
    Facebook automated scraping reliable nahi hai (login-wall + ToS restrictions).
    Isliye: Facebook post/group se reviews ko manually copy karke ek Python list
    mein paste karein, ye function unhe clean + sentiment-analyze karke DB mein save karega.

    Usage:
        add_facebook_reviews_manually(
            "https://facebook.com/...",
            "Haier",
            "Haier HSU-19LF",
            ["review text 1 copy pasted", "review text 2 copy pasted", ...]
        )
    """
    print(f"[FACEBOOK] Saving {len(review_texts_list)} manually-collected reviews")
    save_to_master_db(
        title=product_title,
        url=post_url,
        price=None,
        specs={},
        features=[],
        reviews=review_texts_list,
        brand=brand_name,
        source="facebook_manual",
    )