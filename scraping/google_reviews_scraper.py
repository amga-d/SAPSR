"""
Google Reviews Scraper for Yogyakarta public service Destinations

This script scrapes Google Maps reviews for public service destinations in Yogyakarta.
Based on the Apify tutorial: https://blog.apify.com/how-to-scrape-google-reviews/

Maximum reviews per destination: 100
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import csv
import pandas as pd
import random

# Configuration
MAX_REVIEWS_PER_DESTINATION = 100
DESTINATIONS_FILE = "public_service_destination.csv"
OUTPUT_FILE = "yogyakarta_public_service_reviews_original-test.csv"
HEADLESS = False  # Set to True for production
SCROLL_PAUSE_TIME = 1.5  # Seconds to wait between scrolls
REQUEST_DELAY = (2, 5)  # Random delay range between destinations (seconds)
DEFAULT_TIMEOUT = 15000  # 15 seconds timeout


async def handle_consent(page):
    """Handle Google consent popup if it appears"""
    try:
        # Try multiple consent button selectors
        consent_selectors = [
            "button:has-text('Accept all')",
            "button:has-text('Terima semua')",  # Indonesian
            "button:has-text('I agree')",
            "[aria-label='Accept all']",
            "form[action*='consent'] button",
        ]
        
        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await button.click(timeout=3000)
                    print("Accepted consent popup")
                    await page.wait_for_timeout(2000)
                    return True
            except:
                continue
        return False
    except:
        return False


async def search_and_navigate_to_reviews(page, search_query):
    """Search for a place on Google Maps and navigate to its reviews tab"""
    try:
        # Navigate to Google Maps
        await page.goto("https://www.google.com/maps", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Handle consent popup
        await handle_consent(page)
        
        # Wait for the search box with multiple possible selectors
        search_selectors = [
            "input#searchboxinput",
            "input[aria-label*='Search']",
            "input[name='q']",
            "#searchbox input",
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                s = page.locator(selector).first
                if await s.count() > 0:
                    await s.wait_for(state="visible", timeout=5000)
                    search_box = s
                    break
            except:
                continue
        
        if not search_box:
            print("Could not find search box")
            return False
        
        # Clear and fill search box
        await search_box.click()
        await search_box.fill("")
        await page.wait_for_timeout(500)
        await search_box.fill(search_query)
        await page.keyboard.press("Enter")
        
        # Wait for results
        await page.wait_for_timeout(4000)
        
        # Try to click on the first result if there are multiple
        try:
            first_result = page.locator("a.hfpxzc").first
            if await first_result.count() > 0:
                await first_result.click()
                await page.wait_for_timeout(3000)
        except:
            pass  # Single result, continue
        
        # Try to find and click Reviews tab with multiple selectors
        reviews_selectors = [
            "button[data-tab-index='1']",  # Usually the Reviews tab
            "[data-value='Reviews']",
            "button[aria-label*='Review']",
            "button:has-text('Reviews')",
            "button:has-text('Ulasan')",  # Indonesian
            "[role='tab']:has-text('Reviews')",
        ]
        
        for selector in reviews_selectors:
            try:
                tab = page.locator(selector).first
                if await tab.count() > 0 and await tab.is_visible():
                    await tab.click(timeout=5000)
                    await page.wait_for_timeout(2000)
                    print(f"Clicked reviews tab using: {selector}")
                    return True
            except:
                continue
        
        # Alternative: look for reviews count and click
        try:
            reviews_count = page.locator("[aria-label*='reviews']").first
            if await reviews_count.count() > 0:
                await reviews_count.click()
                await page.wait_for_timeout(2000)
                return True
        except:
            pass
        
        print("Could not find reviews tab, but will try to scrape anyway")
        return True  # Try to scrape even without clicking tab
        
    except PlaywrightTimeout as e:
        print(f"Timeout during navigation: {e}")
        return False
    except Exception as e:
        print(f"Error during navigation: {e}")
        return False


async def scroll_reviews_panel(page, max_reviews):
    """Scroll the reviews panel to load more reviews"""
    # Find the scrollable container with multiple selectors
    scrollable_selectors = [
        "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
        "div.m6QErb.DxyBCb",
        "div[role='main'] div.m6QErb",
        "[role='main'] div[tabindex='-1']",
    ]
    
    scroll_container = None
    for selector in scrollable_selectors:
        try:
            container = page.locator(selector).first
            if await container.count() > 0:
                scroll_container = container
                break
        except:
            continue
    
    if not scroll_container:
        print("Could not find scrollable container, skipping scroll")
        return
    
    previous_count = 0
    same_count_iterations = 0
    
    for _ in range(20):  # Max 20 scroll attempts
        # Get current number of unique reviews
        review_elements = page.locator("div[data-review-id]")
        review_ids = await review_elements.evaluate_all(
            "els => Array.from(new Set(els.map(el => el.getAttribute('data-review-id')).filter(Boolean)))"
        )
        current_count = len(review_ids)
        
        # Check if we have enough reviews or can't load more
        if current_count >= max_reviews:
            print(f"Reached target reviews: {current_count}")
            break
        
        if current_count == previous_count:
            same_count_iterations += 1
            if same_count_iterations >= 3:
                print(f"No more reviews to load. Total: {current_count}")
                break
        else:
            same_count_iterations = 0
        
        previous_count = current_count
        
        # Scroll down
        try:
            await scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
            await page.wait_for_timeout(SCROLL_PAUSE_TIME * 1000)
        except:
            break
        
        print(f"Loaded {current_count} unique reviews...")


async def scrape_reviews(page, destination, max_reviews):
    """Scrape reviews from the current page. `destination` is a dict from the CSV."""
    reviews = []
    seen_review_keys = set()
    destination_name = destination.get('name') if isinstance(destination, dict) else destination
    
    # Wait for review elements with multiple selectors
    review_selectors = [
        "div[data-review-id]",
        "div[data-review-id][jsaction]",
        ".jftiEf",  # Alternative review container class
    ]
    
    review_html_elements = None
    for selector in review_selectors:
        try:
            elements = page.locator(selector)
            await elements.first.wait_for(state="visible", timeout=10000)
            if await elements.count() > 0:
                review_html_elements = elements
                break
        except:
            continue
    
    if not review_html_elements:
        print(f"No reviews found for {destination_name}")
        return reviews
    
    # Scroll to load more reviews
    await scroll_reviews_panel(page, max_reviews)
    
    # Get all review elements and stop once we have enough unique reviews
    all_reviews = await review_html_elements.all()
    
    print(f"Scraping up to {max_reviews} unique reviews for {destination_name}...")

    for i, review_html_element in enumerate(all_reviews):
        try:
            review_key = await review_html_element.get_attribute("data-review-id") or ""

            # Extract user info with fallbacks
            user_url = ""
            username = ""
            
            try:
                user_element = review_html_element.locator("button[data-href*='/contrib/']").first
                if await user_element.count() > 0:
                    user_url = await user_element.get_attribute("data-href") or ""
                    name_el = user_element.locator("div").first
                    if await name_el.count() > 0:
                        username = await name_el.text_content() or ""
            except:
                pass
            
            # Alternative username extraction
            if not username:
                try:
                    name_el = review_html_element.locator(".d4r55").first
                    if await name_el.count() > 0:
                        username = await name_el.text_content() or ""
                except:
                    pass
            
            # Extract star rating with multiple approaches
            stars = None
            try:
                stars_element = review_html_element.locator("[aria-label*='star']").first
                if await stars_element.count() > 0:
                    stars_label = await stars_element.get_attribute("aria-label") or ""
                    for i in range(5, 0, -1):  # Check from 5 to 1
                        if str(i) in stars_label:
                            stars = i
                            break
            except:
                pass
            
            # Alternative star extraction
            if stars is None:
                try:
                    stars_element = review_html_element.locator("span.kvMYJc").first
                    if await stars_element.count() > 0:
                        aria_label = await stars_element.get_attribute("aria-label") or ""
                        for i in range(5, 0, -1):
                            if str(i) in aria_label:
                                stars = i
                                break
                except:
                    pass
            
            # Extract time
            review_time = ""
            try:
                time_element = review_html_element.locator(".rsqaWe").first
                if await time_element.count() > 0:
                    review_time = await time_element.text_content() or ""
            except:
                pass
            
            # Click "More" button if present
            try:
                more_selectors = [
                    "button[aria-label='See more']",
                    "button:has-text('More')",
                    "button:has-text('Lainnya')",  # Indonesian
                    ".w8nwRe.kyuRq",
                ]
                for sel in more_selectors:
                    more_btn = review_html_element.locator(sel).first
                    if await more_btn.count() > 0 and await more_btn.is_visible():
                        await more_btn.click(timeout=1000)
                        await page.wait_for_timeout(300)
                        break
            except:
                pass
            
            # After expanding, click 'See original' if Google auto-translated the review
            try:
                original_selectors = [
                    "button:has-text('See original')",
                    "button:has-text('Lihat asli')",
                    "a:has-text('See original')",
                    "span:has-text('See original')",
                    "button[aria-label='See original']",
                    "div[role='button']:has-text('See original')",
                ]
                for sel in original_selectors:
                    try:
                        see_btn = review_html_element.locator(sel).first
                        if await see_btn.count() > 0 and await see_btn.is_visible():
                            await see_btn.click(timeout=1000)
                            await page.wait_for_timeout(300)
                            break
                    except:
                        continue
            except:
                pass

            # Extract review text with fallbacks
            text = ""
            try:
                text_selectors = [
                    "span.wiI7pd",
                    "div[tabindex='-1'][lang]",
                    ".MyEned span",
                ]
                for sel in text_selectors:
                    text_el = review_html_element.locator(sel).first
                    if await text_el.count() > 0:
                        text = await text_el.text_content() or ""
                        if text:
                            break
            except:
                pass

            if not review_key:
                review_key = "|".join([
                    destination_name or "",
                    user_url.strip() if user_url else "",
                    username.strip() if username else "",
                    review_time.strip() if review_time else "",
                    str(stars) if stars is not None else "",
                ])

            if review_key in seen_review_keys:
                continue
            seen_review_keys.add(review_key)
            
            # Create review object (include category if available)
            review = {
                "destination": destination_name,
                "category": destination.get('category', '') if isinstance(destination, dict) else "",
                "user_url": user_url.strip() if user_url else "",
                "username": username.strip() if username else "",
                "stars": stars,
                "time": review_time.strip() if review_time else "",
                "text": text.strip() if text else ""
            }
            reviews.append(review)

            if len(reviews) >= max_reviews:
                break
            
        except Exception as e:
            print(f"Error extracting review {i+1}: {e}")
            continue
    
    return reviews


async def scrape_destination(page, destination, max_reviews):
    """Scrape reviews for a single destination"""
    name = destination['name']
    search_query = destination['search_query']
    
    print(f"\n{'='*50}")
    print(f"Scraping: {name}")
    print(f"Search query: {search_query}")
    print(f"{'='*50}")
    
    # Navigate to Google Maps and search
    success = await search_and_navigate_to_reviews(page, search_query)
    
    if not success:
        print(f"Could not access reviews for {name}")
        return []
    
    # Scrape reviews
    reviews = await scrape_reviews(page, destination, max_reviews)
    
    print(f"Collected {len(reviews)} reviews for {name}")
    return reviews


async def run():
    """Main scraping function"""
    # Load destinations
    try:
        destinations_df = pd.read_csv(DESTINATIONS_FILE)
        destinations = destinations_df.to_dict('records')
        print(f"Loaded {len(destinations)} destinations from {DESTINATIONS_FILE}")
    except FileNotFoundError:
        print(f"Error: {DESTINATIONS_FILE} not found. Make sure the file exists in the project root.")
        return
    
    all_reviews = []
    
    async with async_playwright() as p:
        # Launch browser with more options
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            locale='en-US',
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        # Initial navigation to handle consent
        try:
            await page.goto("https://www.google.com/maps")
            await page.wait_for_timeout(2000)
            await handle_consent(page)
        except:
            pass
        
        # Scrape each destination
        for i, destination in enumerate(destinations):
            try:
                reviews = await scrape_destination(page, destination, MAX_REVIEWS_PER_DESTINATION)
                all_reviews.extend(reviews)
                
                # Save intermediate results every 5 destinations
                if (i + 1) % 5 == 0:
                    save_reviews_to_csv(all_reviews, OUTPUT_FILE)
                    print(f"\nIntermediate save: {len(all_reviews)} total reviews")
                
                # Random delay between destinations
                delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
                print(f"Waiting {delay:.1f} seconds before next destination...")
                await page.wait_for_timeout(delay * 1000)
                
            except Exception as e:
                print(f"Error scraping {destination['name']}: {e}")
                continue
        
        await browser.close()
    
    # Final save
    save_reviews_to_csv(all_reviews, OUTPUT_FILE)
    print(f"\n{'='*50}")
    print(f"Scraping complete! Total reviews: {len(all_reviews)}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print(f"{'='*50}")


def save_reviews_to_csv(reviews, filename):
    """Save reviews to CSV file"""
    if not reviews:
        print("No reviews to save")
        return
    fieldnames = ["destination", "category", "user_url", "username", "stars", "time", "text"]
    
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)
    
    print(f"Saved {len(reviews)} reviews to {filename}")


def test_single_destination():
    """Test scraping with a single destination"""
    print("Running test with single destination...")
    
    async def test():
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                locale='en-US',
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT)
            
            # Test with Candi Prambanan
            test_destination = {
                'name': 'Candi Prambanan',
                'search_query': 'Candi Prambanan Yogyakarta'
            }

            # include a category to match the CSV header
            test_destination.setdefault('category', 'Unknown')
            
            # Handle consent
            try:
                await page.goto("https://www.google.com/maps")
                await page.wait_for_timeout(2000)
                await handle_consent(page)
            except:
                pass
            
            reviews = await scrape_destination(page, test_destination, 10)
            
            print(f"\nTest results: {len(reviews)} reviews scraped")
            for review in reviews[:5]:
                print(f"  - {review['username']}: {review['stars']} stars")
                text_preview = review['text'][:100] + "..." if len(review['text']) > 100 else review['text']
                print(f"    {text_preview}")
            
            await browser.close()
            
            # Save test results
            save_reviews_to_csv(reviews, "test_reviews.csv")
    
    asyncio.run(test())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-single":
        test_single_destination()
    else:
        asyncio.run(run())
