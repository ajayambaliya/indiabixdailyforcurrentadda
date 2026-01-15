import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from deep_translator import GoogleTranslator
from github import Github, Auth
from github.InputFileContent import InputFileContent
import datetime
import time
import json
import re
import random
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from notifications import NotificationSender

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GH_TOKEN = os.getenv("GH_TOKEN")
GIST_ID = os.getenv("GIST_ID")

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
auth = Auth.Token(GH_TOKEN)
gh = Github(auth=auth)

# Initialize Notification Sender
notifier = NotificationSender()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

GUJARATI_MONTHS = {
    1: "જાન્યુઆરી",
    2: "ફેબ્રુઆરી",
    3: "માર્ચ",
    4: "એપ્રિલ",
    5: "મે",
    6: "જૂન",
    7: "જુલાઈ",
    8: "ઓગસ્ટ",
    9: "સપ્ટેમ્બર",
    10: "ઓક્ટોબર",
    11: "નવેમ્બર",
    12: "ડિસેમ્બર"
}

def get_gujarati_date(date_iso):
    """Converts 2025-08-05 to 5 ઓગસ્ટ 2025"""
    try:
        dt = datetime.datetime.strptime(date_iso, "%Y-%m-%d")
        day = dt.day
        month = GUJARATI_MONTHS[dt.month]
        year = dt.year
        return f"{day} {month} {year}"
    except Exception as e:
        print(f"Date conversion error: {e}")
        return date_iso

def get_scraped_urls_from_gist():
    try:
        gist = gh.get_gist(GIST_ID)
        if "scraped_urls.json" in gist.files:
            content = gist.files["scraped_urls.json"].content
            return json.loads(content)
        return []
    except Exception as e:
        print(f"Error fetching Gist: {e}")
        return []

def update_scraped_urls_in_gist(urls):
    try:
        gist = gh.get_gist(GIST_ID)
        content = json.dumps(urls, indent=2)
        gist.edit(files={"scraped_urls.json": InputFileContent(content)})
        print("Gist updated successfully.")
    except Exception as e:
        print(f"Error updating Gist: {e}")

def get_new_quiz_urls(processed_urls):
    base_url = "https://www.indiabix.com/current-affairs/questions-and-answers/"
    response = requests.get(base_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")
    
    new_urls = []
    card_styles = soup.find_all("div", class_="card-style")
    for card in card_styles:
        links = card.find_all("a", class_="text-link")
        for link in links:
            href = link.get("href")
            if href:
                if not href.startswith("http"):
                    if href.startswith("/"):
                        href = "https://www.indiabix.com" + href
                    else:
                        href = "https://www.indiabix.com/current-affairs/" + href
                
                href = href.rstrip("/")
                if re.search(r'/current-affairs/\d{4}-\d{2}-\d{2}$', href):
                    if href not in processed_urls:
                        new_urls.append(href)
    
    return list(set(new_urls))

def translate_safe(text):
    if not text:
        return ""
    
    # Strip whitespace for cleaner translation
    text = text.strip()
    if not text:
        return ""

    wait_time = 1
    max_wait = 30
    attempts = 0
    
    # Use a local translator instance per call to be thread-safe
    local_translator = GoogleTranslator(source='en', target='gu')
    
    while True:
        try:
            result = local_translator.translate(text)
            if result:
                return result
            raise Exception("Empty translation result")
        except Exception as e:
            attempts += 1
            print(f"    [Attempt {attempts}] Translation failed for snippet: {text[:30]}... Error: {e}")
            jitter = random.uniform(0.5, 1.5)
            actual_wait = wait_time * jitter
            print(f"    Waiting {actual_wait:.2f}s before retry...")
            time.sleep(actual_wait)
            
            # Exponential backoff
            wait_time = min(wait_time * 2, max_wait)
            
            # Refresh translator instance after multiple failures
            if attempts % 5 == 0:
                local_translator = GoogleTranslator(source='en', target='gu')

def process_single_question(idx, container):
    """Processes and translates a single question container."""
    try:
        q_text_elem = container.find("div", class_="bix-td-qtxt")
        q_text_en = q_text_elem.get_text(strip=True) if q_text_elem else ""
        
        options_en = {}
        opt_rows = container.find_all("div", class_="bix-opt-row")
        for row in opt_rows:
            opt_letter_elem = row.find("div", class_="bix-td-option")
            opt_val_elem = row.find("div", class_="bix-td-option-val")
            
            if opt_letter_elem and opt_val_elem:
                letter_span = opt_letter_elem.find("span")
                letter = ""
                if letter_span:
                    classes = letter_span.get("class", [])
                    for c in classes:
                        if "option-svg-letter-" in c:
                            letter = c.split("-")[-1].upper()
                            break
                if not letter:
                    letter = opt_letter_elem.get_text(strip=True).replace(".", "")
                
                val_en = opt_val_elem.get_text(strip=True)
                options_en[letter] = val_en
        
        ans_input = container.find("input", class_="jq-hdnakq")
        answer = ans_input.get("value") if ans_input else ""
        
        exp_elem = container.find("div", class_="bix-ans-description")
        explanation_en = exp_elem.get_text(strip=True) if exp_elem else ""
        
        category = "General"
        cat_elem = container.find("div", class_="explain-link")
        if cat_elem:
            cat_a = cat_elem.find("a")
            if cat_a:
                category = cat_a.get_text(strip=True)
        
        print(f"  Starting translation for question {idx+1}...")
        
        text_gu = translate_safe(q_text_en)
        explanation_gu = translate_safe(explanation_en)
        options_gu = {k: translate_safe(v) for k, v in options_en.items()}
            
        return {
            "q_index": idx + 1,
            "text": text_gu,
            "options": options_gu,
            "explanation": explanation_gu,
            "answer": answer,
            "category": category
        }
    except Exception as e:
        print(f"  Error parsing question {idx+1}: {e}")
        return None

def scrape_quiz_page(url):
    print(f"Scraping: {url}")
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")
    
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', url)
    date_iso = date_match.group(1) if date_match else None
    date_gu = get_gujarati_date(date_iso) if date_iso else ""
    
    containers = soup.find_all("div", class_="bix-div-container")
    
    # Process all questions on the page concurrently for speed
    # Using 5 workers as a balance between speed and reliability
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda i_c: process_single_question(i_c[0], i_c[1]), enumerate(containers)))
    
    questions = [q for q in results if q is not None]
            
    return {
        "title": f"Current IndiaBix - {date_gu}",
        "date_str": date_gu,
        "slug": f"indiabix-{date_iso}",
        "quiz_date": date_iso,
        "source_url": url,
        "questions": questions
    }

def save_to_supabase(data):
    try:
        quiz_data = {
            "title": data["title"],
            "slug": data["slug"],
            "date_str": data["date_str"],
            "quiz_date": data["quiz_date"],
            "source_url": data["source_url"]
        }
        
        is_new_quiz = False
        existing = supabase.table("quizzes").select("id").eq("slug", quiz_data["slug"]).execute()
        if existing.data:
            quiz_id = existing.data[0]["id"]
            print(f"Quiz already exists: {quiz_data['slug']}. Updating questions...")
            supabase.table("questions").delete().eq("quiz_id", quiz_id).execute()
            # Forcing notification even for updates to ensure user sees it working
            is_new_quiz = True 
        else:
            res = supabase.table("quizzes").insert(quiz_data).execute()
            quiz_id = res.data[0]["id"]
            is_new_quiz = True
        
        # Batch insert questions for more speed
        q_rows = []
        for q in data["questions"]:
            q_rows.append({
                "quiz_id": quiz_id,
                "q_index": q["q_index"],
                "text": q["text"],
                "options": q["options"],
                "explanation": q["explanation"],
                "answer": q["answer"],
                "category": q["category"]
            })
        
        if q_rows:
            supabase.table("questions").insert(q_rows).execute()
            
        return True, is_new_quiz
    except Exception as e:
        print(f"Supabase error: {e}")
        return False, False

def main():
    print("Starting Scraper...")
    processed_urls = get_scraped_urls_from_gist()
    print(f"Found {len(processed_urls)} already processed URLs.")
    
    new_urls = get_new_quiz_urls(processed_urls)
    print(f"Found {len(new_urls)} new URLs to process.")
    
    if not new_urls:
        print("No new content to scrap.")
        return

    # Sort URLs to process in a predictable order (e.g. oldest first if possible)
    new_urls.sort()
    
    for url in new_urls:
        try:
            quiz_data = scrape_quiz_page(url)
            if quiz_data["questions"]:
                success, is_new = save_to_supabase(quiz_data)
                if success:
                    # Send notification if it's a new quiz
                    if is_new:
                        print(f"Sending notification for new quiz: {quiz_data['slug']}")
                        notifier.send_quiz_notification(quiz_data["date_str"], quiz_data["slug"])
                        
                    # Update cache and Gist immediately after each successful URL
                    processed_urls.append(url)
                    update_scraped_urls_in_gist(processed_urls)
                    print(f"Successfully processed, saved and checkpointed: {url}")
                else:
                    print(f"Failed to save {url} to Supabase.")
            else:
                print(f"No questions found on page: {url}")
        except Exception as e:
            print(f"Failed to process {url}: {e}")
            # Try to save what we have if it's a transient failure between pages
            pass
        
        # Short wait between pages to avoid being blocked
        time.sleep(1)
        
    print("Scraping Task Completed.")

if __name__ == "__main__":
    main()
