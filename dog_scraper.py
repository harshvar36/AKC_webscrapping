import csv
import time
from playwright.sync_api import sync_playwright

def scrape_akc():
    with sync_playwright() as p:
        # slow_mo=500 helps the click register properly
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        print("--- STAGE 1: Clicking 'Load More' until all dogs are found ---")
        try:
            page.goto("https://www.akc.org/dog-breeds/", timeout=60000)
            time.sleep(5)
            
            while True:
                # 1. Scroll to the bottom to make the button visible
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                # 2. Look for the "LOAD MORE" button
                # The button usually has a class like 'load-more' or specific text
                load_more_btn = page.get_by_text("LOAD MORE", exact=False)
                
                if load_more_btn.is_visible():
                    print("Found 'Load More' button. Clicking...")
                    load_more_btn.click()
                    time.sleep(3) # Wait for the next 12 dogs to pop in
                else:
                    print("No more 'Load More' buttons found. All dogs loaded!")
                    break
        except Exception as e:
            print(f"Collection interrupted: {e}")

        # Get all links once all 'Load More' clicks are done
        breed_elements = page.query_selector_all('h3.breed-type-card__title')
        links = [el.evaluate("node => node.parentElement.href") for el in breed_elements]
        print(f"SUCCESS: Total dogs to scrape: {len(links)}")

        # --- STAGE 2: Scraping Details (Same logic as before) ---
        all_dog_data = []

        for index, link in enumerate(links):
            try:
                print(f"[{index + 1}/{len(links)}] Scraping: {link}")
                page.goto(link, timeout=60000)
                time.sleep(2)
                
                # Open 'ALL TRAITS' tab (ID from your screenshot)
                tab_id = "#tab__breed-page__traits__all"
                if page.query_selector(tab_id):
                    page.click(tab_id)
                    time.sleep(1)
                
                # Nudge scroll to load bars
                page.evaluate("window.scrollBy(0, 500)")

                name_el = page.query_selector("h1")
                breed_name = name_el.inner_text().strip() if name_el else "Unknown"
                
                dog_info = {"Breed Name": breed_name}

                trait_rows = page.query_selector_all(".breed-trait-group__trait-all")
                for row in trait_rows:
                    label_el = row.query_selector(".breed-trait-group__header")
                    if label_el:
                        label = label_el.inner_text().strip()
                        
                        # Bar scores
                        filled_bars = row.query_selector_all(".breed-trait-score__score-unit--filled")
                        # Selected words
                        selected_choice = row.query_selector(".breed-trait-score__choice--selected")

                        if filled_bars:
                            dog_info[label] = f"{len(filled_bars)} out of 5"
                        elif selected_choice:
                            dog_info[label] = selected_choice.inner_text().strip()
                        else:
                            val_el = row.query_selector(".breed-trait-score__score-label")
                            dog_info[label] = val_el.inner_text().strip() if val_el else "N/A"

                dog_info["URL"] = link
                all_dog_data.append(dog_info)

            except Exception as e:
                print(f"Error on {link}: {e}")

        # --- STAGE 3: Final CSV Formatting ---
        if all_dog_data:
            all_keys = set().union(*(d.keys() for d in all_dog_data))
            trait_keys = sorted([k for k in all_keys if k not in ['Breed Name', 'URL']])
            fieldnames = ['Breed Name'] + trait_keys + ['URL']
            
            with open('dog_traits_full.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_dog_data)
            print(f"\nDONE! {len(all_dog_data)} dogs saved to 'dog_traits_full.csv'")
        
        browser.close()

if __name__ == "__main__":
    scrape_akc()