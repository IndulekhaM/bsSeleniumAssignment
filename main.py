import os
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
OUTPUT_DIR = "C:/Users/msi/PycharmProjects/BrowserStack/images"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize Google Translator
translator = Translator()

async def translate_titles(titles):
    """Translate a list of titles to English."""
    translated = []
    for title in titles:
        try:
            translated_title = await translator.translate(title, src='es', dest='en')
            translated.append(translated_title.text)
        except Exception as e:
            print(f"Error translating title '{title}': {e}")
            translated.append("Translation failed")
    return translated

async def scrape_articles():
    """Scrape the first five articles from the Opinion section."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--headless")  # Uncomment for headless mode

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        driver.get(BASE_URL + OPINION_SECTION)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article'))
        )
        articles = driver.find_elements(By.CSS_SELECTOR, 'article')[:5]

        if not articles:
            print("No articles found.")
            return [], []

        scraped_data = []
        titles_to_translate = []
        for article in articles:
            try:
                # Extract title
                title_element = article.find_element(By.CSS_SELECTOR, 'h2 a')
                title = title_element.text.strip()
                titles_to_translate.append(title)

                # Extract content
                try:
                    content = article.find_element(By.CSS_SELECTOR, 'p').text.strip()
                except NoSuchElementException:
                    content = "Content unavailable"

                # Extract image
                image_path = None
                try:
                    image_elements = article.find_elements(By.CSS_SELECTOR, 'img')
                    if image_elements:
                        image_url = image_elements[0].get_attribute('src')
                        if image_url:
                            image_path = os.path.join(OUTPUT_DIR, os.path.basename(image_url))
                            save_image(image_url, image_path)
                except Exception as e:
                    print(f"Image extraction failed: {e}")

                # Append article data
                scraped_data.append({
                    "title": title,
                    "content": content,
                    "image": image_path,
                })
            except Exception as e:
                print(f"Error scraping article: {e}")

        # Translate titles asynchronously
        translated_titles = await translate_titles(titles_to_translate)

        # Add translations to scraped data
        for i, article in enumerate(scraped_data):
            article["translated_title"] = translated_titles[i]

        return scraped_data, translated_titles
    finally:
        driver.quit()

def save_image(url, path):
    """Download and save the image to the specified path."""
    try:
        base_name = os.path.basename(url)
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)  # Replace invalid characters with an underscore
        sanitized_path = os.path.join(os.path.dirname(path), base_name)

        print(f"Downloading image from {url} to {sanitized_path}")  # Debugging line
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(sanitized_path, 'wb') as f:
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


async def main():
    """Main function to execute the scraping and processing."""
    # Await the asynchronous scrape_articles function
    articles_data, translated_titles = await scrape_articles()
    print("Scraping completed.")
    print("Articles Data:", articles_data)
    print("Translated Titles:", translated_titles)

    # Analyze repeated words in translated titles
    repeated_words = analyze_headers(translated_titles)
    print("Repeated Words in Titles:")
    for word, count in repeated_words.items():
        print(f"{word}: {count}")

if __name__ == "__main__":
    asyncio.run(main())

