import requests
import re
from bs4 import BeautifulSoup
import translators as ts

# Dictionary mapping full language names to their Wikipedia language codes
LANG_CODES = {
    'english': 'en',
    'filipino': 'tl',
    'cebuano': 'ceb',
    'ilokano': 'ilo'
}

def scrape_wikipedia_article(lang_code, article_title):
    """
    Scrapes the main text content of a Wikipedia article.

    Args:
        lang_code (str): The two-letter language code for the Wikipedia domain (e.g., 'en', 'tl').
        article_title (str): The title of the article to scrape.

    Returns:
        str: The cleaned text content of the article, or None if the article could not be fetched.
    """
    # Construct the Wikipedia URL
    url = f"https://{lang_code}.wikipedia.org/wiki/{article_title.replace(' ', '_')}"
    print(f"Fetching article from: {url}")

    try:
        # Send a request to the URL
        response = requests.get(url, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the main content area of the article
        content_div = soup.find(id='mw-content-text')
        if not content_div:
            print("Could not find the main content area of the article.")
            return None

        # Extract text from all paragraph tags within the main content
        paragraphs = content_div.find_all('p')
        
        # Combine the text from all paragraphs
        article_text = ' '.join([para.get_text() for para in paragraphs])

        # Clean the text by removing citation brackets (e.g., [1], [2], [citation needed])
        cleaned_text = re.sub(r'\[.*?\]', '', article_text)
        
        # Replace multiple newlines/spaces with a single space
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        return cleaned_text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the article: {e}")
        return None

def translate_text(text, from_lang, to_lang):
    """
    Translates text from a source language to a target language using the translators library.

    Args:
        text (str): The text to translate.
        from_lang (str): The source language code.
        to_lang (str): The target language code.

    Returns:
        str: The translated text, or None if translation fails.
    """
    if not text:
        return None
        
    print(f"\nTranslating from '{from_lang}' to '{to_lang}'... (This may take a moment)")
    try:
        # Using the 'google' translator. You can try others like 'bing', 'deepl' if needed.
        translated_text = ts.translate_text(text, translator='google', from_language=from_lang, to_language=to_lang)
        return translated_text
    except Exception as e:
        print(f"An error occurred during translation: {e}")
        return None

def main():
    """
    Main function to run the scraper and translator.
    """
    print("--- Wikipedia Article Scraper and Translator ---")
    print("Supported Languages: English, Filipino, Cebuano, Ilokano")

    # --- Get User Input for Source Language ---
    while True:
        source_lang_name = input("Enter the source language: ").lower()
        if source_lang_name in LANG_CODES:
            source_lang_code = LANG_CODES[source_lang_name]
            break
        print("Invalid language. Please choose from the supported languages.")

    # --- Get User Input for Target Language ---
    while True:
        target_lang_name = input("Enter the target language: ").lower()
        if target_lang_name in LANG_CODES:
            if target_lang_name == source_lang_name:
                print("Source and target languages cannot be the same. Please choose a different target language.")
            else:
                target_lang_code = LANG_CODES[target_lang_name]
                break
        print("Invalid language. Please choose from the supported languages.")

    # --- Get User Input for Article Title ---
    article_title = input(f"Enter the Wikipedia article title in {source_lang_name.capitalize()}: ")

    # --- Scrape the Article ---
    original_text = scrape_wikipedia_article(source_lang_code, article_title)

    if original_text:
        print("\n--- Original Text (Cleaned) ---")
        print(original_text[:1000] + "..." if len(original_text) > 1000 else original_text) # Preview first 1000 chars

        # --- Translate the Article ---
        translated_text = translate_text(original_text, source_lang_code, target_lang_code)

        if translated_text:
            print(f"\n--- Translated Text ({target_lang_name.capitalize()}) ---")
            print(translated_text)
        else:
            print("\nCould not translate the article.")
    else:
        print("\nCould not retrieve the article. Please check the language and title.")

if __name__ == "__main__":
    main()
