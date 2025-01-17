import os
import time
import re
import requests
import asyncio
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from googletrans import Translator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Constants
BASE_URL = "https://elpais.com"
OPINION_SECTION = "/opinion/"
OUTPUT_DIR = "./images"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize Google Translator
translator = Translator()

async def translate_title(title):
    """Translate a single title to English."""
    return await translator.translate(title, src='es', dest='en')

def scrape_articles():
    """Scrape the first five articles from the Opinion section."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--headless")  # Uncomment if running in headless mode

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(BASE_URL)
    print("Starting the scraping process...")

    # Navigate to the Opinion section
    driver.get(BASE_URL + OPINION_SECTION)
    time.sleep(3)

    try:
        # Wait explicitly for articles to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article'))
        )
    except TimeoutException:
        print("Timed out waiting for articles to load")
        driver.quit()
        return []

    articles = driver.find_elements(By.CSS_SELECTOR, 'article')
    print(f"Number of articles found: {len(articles)}")  # Debugging line
    articles = articles[:5]  # Limit to first five articles

    if not articles:
        print("No articles found.")
        driver.quit()
        return []

    scraped_data = []
    translated_titles = []  # List to store translated titles
    for article in articles:
        try:
            title_element = article.find_element(By.CSS_SELECTOR, 'h2 a')
            title = title_element.text
            print(f"Scraped Title: {title}")

            # Translate the title immediately
            translated_title = asyncio.run(translate_title(title))
            translated_titles.append(translated_title.text)
            print(f"Translated Title: {translated_title.text}")

            # Wait for content element to load
            content_element = WebDriverWait(article, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.article-content'))
            )
            content = content_element.text if content_element else "Content not available"

            if not content.strip():
                content = "Content could not be extracted."

            image_elements = article.find_elements(By.CSS_SELECTOR, 'img')
            image_path = None
            if image_elements:
                image_url = image_elements[0].get_attribute('src')
                image_path = os.path.join(OUTPUT_DIR, os.path.basename(image_url))
                save_image(image_url, image_path)

            scraped_data.append({
                "title": title,
                "content": content,
                "image": image_path
            })
        except NoSuchElementException as e:
            print(f"Element not found: {e}")
        except Exception as e:
            print(f"Error scraping an article: {e}")

    driver.quit()
    return scraped_data, translated_titles

def save_image(url, path):
    """Download and save the image to the specified path."""
    try:
        base_name = os.path.basename(url)
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)  # Replace invalid characters with an underscore
        sanitized_path = os.path.join(os.path.dirname(path), base_name)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(sanitized_path, 'wb') as f:  # Corrected line
                f.write(response.content)
            print(f"Image saved to {sanitized_path}")
        else:
            print(f"Failed to download image: {url} (Status code: {response.status_code})")
    except Exception as e:
        print(f"Error saving image: {e}")

def analyze_headers(headers):
    """Analyze the repeated words in the given headers."""
    words = []
    for header in headers:
        words.extend(re.findall(r'\w+', header.lower()))  # Extract words and convert to lowercase
    return Counter(words)  # Count occurrences of each word

def main():
    """Main function to execute the scraping and processing."""
    scraped_data, translated_titles = scrape_articles()

    # Check if there are titles to analyze
    if not translated_titles:
        print("No titles found to analyze.")
        return

    # Analyze repeated words in translated titles
    repeated_words = analyze_headers(translated_titles)

    print("Translated Titles:")
    for title in translated_titles:
        print(title)

    print("Repeated Words in Titles:")
    for word, count in repeated_words.items():
        print(f"{word}: {count}")

if __name__ == "__main__":
    main()
