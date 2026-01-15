import os
import requests
from bs4 import BeautifulSoup
from github import Github, Auth
from github.InputFileContent import InputFileContent
import json
import re
from dotenv import load_dotenv

load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")

auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_all_available_urls():
    base_url = "https://www.indiabix.com/current-affairs/questions-and-answers/"
    print(f"Fetching URLs from {base_url}...")
    response = requests.get(base_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")
    
    urls = []
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
                    urls.append(href)
    
    return list(set(urls))

def update_gist_with_all_urls(urls):
    print(f"Updating Gist {GIST_ID} with {len(urls)} URLs...")
    try:
        gist = gh.get_gist(GIST_ID)
        
        # Using InputFileContent for PyGithub compatibility
        new_content = json.dumps(urls, indent=2)
        files = {
            "scraped_urls.json": InputFileContent(new_content)
        }
        
        # If gistfile1.txt exists, we clear it or remove it
        if "gistfile1.txt" in gist.files:
            files["gistfile1.txt"] = InputFileContent("Synced with scraped_urls.json")
            
        gist.edit(description="Indiabix Scraper Tracking", files=files)
        print("Gist updated successfully.")
        print(f"Files now in Gist: {list(gist.files.keys())}")
    except Exception as e:
        print(f"Error updating Gist: {e}")

if __name__ == "__main__":
    urls = get_all_available_urls()
    if urls:
        update_gist_with_all_urls(urls)
    else:
        print("No URLs found to mark.")
