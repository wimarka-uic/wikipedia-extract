import requests
import re
import json
import time
import os
from bs4 import BeautifulSoup
from pathlib import Path

# Dictionary mapping full language names to their Wikipedia language codes
LANG_CODES = {
    'english': 'en',
    'filipino': 'tl',
    'cebuano': 'ceb',
    'ilokano': 'ilo'
}

# Reverse mapping for display
LANG_NAMES = {v: k for k, v in LANG_CODES.items()}

# Target languages for bulk extraction
TARGET_LANGUAGES = ['en', 'tl', 'ilo', 'ceb']
ARTICLES_PER_LANGUAGE = 6250  # 25,000 total / 4 languages

# For production - full 25,000 articles
TEST_MODE = False
USE_KNOWN_ARTICLES = False  # Use random articles from Wikipedia
ARTICLES_PER_LANGUAGE = 6250  # 25,000 total / 4 languages

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

    # Headers to identify as a legitimate bot
    headers = {
        'User-Agent': 'WikipediaExtractor/1.0 (https://github.com/your-repo; your-email@example.com) Python/3.12',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    try:
        # Send a request to the URL
        response = requests.get(url, headers=headers, timeout=10)
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

def get_wikipedia_articles(lang_code, limit=100):
    """
    Gets a list of popular article titles from Wikipedia using the API.

    Args:
        lang_code (str): The language code for Wikipedia.
        limit (int): Number of articles to retrieve.

    Returns:
        list: List of article titles.
    """
    articles = []

    # Headers to identify as a legitimate bot
    headers = {
        'User-Agent': 'WikipediaExtractor/1.0 (https://github.com/your-repo; your-email@example.com) Python/3.12',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    # First, test if the Wikipedia site is accessible
    test_url = f"https://{lang_code}.wikipedia.org"
    try:
        print(f"  Testing connectivity to {test_url}...")
        test_response = requests.get(test_url, headers=headers, timeout=15, allow_redirects=True)
        print(f"  ✓ {lang_code}.wikipedia.org is accessible (Status: {test_response.status_code})")
    except Exception as e:
        print(f"  ✗ Cannot access {lang_code}.wikipedia.org: {e}")
        print(f"  Falling back to predefined articles for {lang_code}...")
        fallback_articles = get_fallback_articles(lang_code)
        return fallback_articles[:limit]

    try:
        # Method 1: Try Special:Random approach
        print(f"  Trying Special:Random method for {lang_code}...")
        url = f"https://{lang_code}.wikipedia.org/wiki/Special:Random"
        
        for i in range(limit):
            print(f"    Getting random article {i+1}/{limit}...")
            
            try:
                # Get a random page with longer timeout
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()
                
                # Extract the title from the final URL after redirect
                final_url = response.url
                title = final_url.split('/wiki/')[-1].replace('_', ' ')
                
                # Decode URL-encoded characters
                import urllib.parse
                title = urllib.parse.unquote(title)
                
                if title and title not in articles:
                    articles.append(title)
                    print(f"      ✓ Got: {title}")
                else:
                    print(f"      ⚠ Skipped duplicate: {title}")
                
            except Exception as e:
                print(f"      ✗ Failed to get article {i+1}: {e}")
                continue
            
            time.sleep(1)  # Increased rate limiting

        if articles:
            print(f"  ✓ Successfully got {len(articles)} articles via Special:Random")
            return articles
        else:
            raise Exception("No articles retrieved via Special:Random")

    except Exception as e:
        print(f"  Error with Special:Random method for {lang_code}: {e}")
        
        # Method 2: Fallback to predefined popular articles
        print(f"  Falling back to predefined articles for {lang_code}...")
        fallback_articles = get_fallback_articles(lang_code)
        return fallback_articles[:limit]

def check_article_exists(lang_code, article_title):
    """
    Checks if an article exists in the specified language Wikipedia.
    
    Args:
        lang_code (str): The language code for Wikipedia.
        article_title (str): The title of the article to check.
        
    Returns:
        bool: True if article exists, False otherwise.
    """
    url = f"https://{lang_code}.wikipedia.org/wiki/{article_title.replace(' ', '_')}"
    
    # Headers to identify as a legitimate bot
    headers = {
        'User-Agent': 'WikipediaExtractor/1.0 (https://github.com/your-repo; your-email@example.com) Python/3.12',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        # Check if the page exists (not a 404)
        return response.status_code == 200
    except Exception as e:
        print(f"    Error checking {lang_code}:{article_title}: {e}")
        return False

def check_article_availability(article_title):
    """
    Checks if an article exists in ALL target languages.
    
    Args:
        article_title (str): The title of the article to check.
        
    Returns:
        dict: Dictionary with language codes as keys and boolean availability as values.
    """
    availability = {}
    
    for lang_code in TARGET_LANGUAGES:
        print(f"    Checking {lang_code}:{article_title}...")
        exists = check_article_exists(lang_code, article_title)
        availability[lang_code] = exists
        print(f"      {'✓' if exists else '✗'} {lang_code}")
        time.sleep(0.5)  # Rate limiting
    
    return availability

def get_articles_with_availability_check(limit=100):
    """
    Gets articles from English Wikipedia and checks their availability in all languages.
    Optimized for large-scale extraction.
    
    Args:
        limit (int): Number of articles to retrieve.
        
    Returns:
        list: List of article titles that exist in ALL target languages.
    """
    print(f"Getting {limit} articles from English Wikipedia...")
    
    # For large-scale extraction, we'll use a more efficient approach
    # Get articles in batches and check availability
    batch_size = 100
    total_batches = (limit + batch_size - 1) // batch_size
    
    available_articles = []
    total_checked = 0
    
    for batch_num in range(total_batches):
        print(f"\n--- Batch {batch_num + 1}/{total_batches} ---")
        
        # Get a batch of English articles
        batch_limit = min(batch_size, limit - len(available_articles))
        english_articles = get_wikipedia_articles('en', batch_limit * 5)  # Get more to account for filtering
        
        if not english_articles:
            print("No articles found in English Wikipedia!")
            break
        
        print(f"Found {len(english_articles)} English articles in this batch. Checking availability...")
        
        for article_title in english_articles:
            total_checked += 1
            
            # Show progress every 10 articles
            if total_checked % 10 == 0:
                print(f"Progress: {total_checked} checked, {len(available_articles)} available")
            
            availability = check_article_availability(article_title)
            
            # Check if article exists in ALL languages
            all_available = all(availability.values())
            
            if all_available:
                available_articles.append(article_title)
                print(f"  ✓ [{len(available_articles)}/{limit}] {article_title}")
                
                # Save progress periodically
                if len(available_articles) % 50 == 0:
                    save_availability_progress(available_articles, storage_dir)
            else:
                missing_langs = [lang for lang, exists in availability.items() if not exists]
                print(f"  ✗ Missing in: {', '.join(missing_langs)} - {article_title}")
            
            # Stop if we have enough articles
            if len(available_articles) >= limit:
                print(f"\nReached target of {limit} articles available in all languages!")
                break
        
        # Stop if we have enough articles
        if len(available_articles) >= limit:
            break
    
    print(f"\nFinal result: {len(available_articles)} articles available in all languages")
    return available_articles

def save_availability_progress(available_articles, storage_dir):
    """Saves the current list of available articles for resume capability."""
    try:
        progress_file = storage_dir / "availability_progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                "available_articles": available_articles,
                "count": len(available_articles),
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving availability progress: {e}")

def get_known_common_articles():
    """
    Returns a list of articles that are likely to exist in all target languages.
    These are common topics that typically have Wikipedia articles in multiple languages.
    """
    return [
        'Earth', 'Sun', 'Moon', 'Water', 'Human', 'Music', 'Art', 'Science',
        'History', 'Geography', 'Biology', 'Chemistry', 'Physics', 'Mathematics',
        'Literature', 'Philosophy', 'Religion', 'Education', 'Technology',
        'Computer', 'Internet', 'Food', 'Culture', 'Language', 'Government',
        'Economy', 'Health', 'Sports', 'Transportation', 'Agriculture', 'Medicine'
    ]

def get_fallback_articles(lang_code):
    """
    Returns a list of common Wikipedia articles as fallback.
    """
    common_articles = {
        'en': [
            'United States', 'World War II', 'Earth', 'Human', 'Water', 'Sun', 
            'Moon', 'Computer', 'Internet', 'Music', 'Art', 'Science', 
            'Mathematics', 'History', 'Geography', 'Biology', 'Chemistry',
            'Physics', 'Literature', 'Philosophy'
        ],
        'tl': [
            'Pilipinas', 'Maynila', 'Jose Rizal', 'Tagalog', 'Wika', 'Kultura',
            'Kasaysayan', 'Agham', 'Sining', 'Musika', 'Literatura', 'Relihiyon',
            'Edukasyon', 'Kalusugan', 'Ekonomiya', 'Politika', 'Lipunan',
            'Teknolohiya', 'Kapaligiran', 'Pagkain'
        ],
        'ilo': [
            'Filipinas', 'Ilocano', 'Pagsasao', 'Kultura', 'Kasaysayan',
            'Agham', 'Sining', 'Musika', 'Literatura', 'Relihiyon',
            'Edukasion', 'Salun-at', 'Ekonomia', 'Politika', 'Sosiedad',
            'Teknolohia', 'Aglawlaw', 'Taraon', 'Dagiti tattao', 'Lugar'
        ],
        'ceb': [
            'Pilipinas', 'Cebuano', 'Pinulongan', 'Kultura', 'Kasaysayan',
            'Siyensiya', 'Arte', 'Musika', 'Literatura', 'Relihiyon',
            'Edukasyon', 'Kahimsog', 'Ekonomiya', 'Politika', 'Katilingban',
            'Teknolohiya', 'Kalikopan', 'Pagkaon', 'Mga tawo', 'Lugar'
        ]
    }
    
    return common_articles.get(lang_code, common_articles['en'])

def create_storage_structure():
    """Creates the directory structure for storing extracted articles."""
    base_dir = Path("extracted_articles")

    for lang_code in TARGET_LANGUAGES:
        lang_dir = base_dir / lang_code
        lang_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        (lang_dir / "raw").mkdir(exist_ok=True)
        (lang_dir / "processed").mkdir(exist_ok=True)

    return base_dir

def save_article(article_data, lang_code, storage_dir):
    """Saves an article to the appropriate file."""
    lang_dir = storage_dir / lang_code / "raw"
    filename = f"{article_data['title'].replace('/', '_').replace(':', '_')}.json"

    try:
        with open(lang_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving article {article_data['title']}: {e}")
        return False

def process_article(article_data, lang_code, storage_dir):
    """
    Processes an article and creates processed versions.
    
    Args:
        article_data (dict): The raw article data
        lang_code (str): Language code
        storage_dir (Path): Storage directory
    """
    try:
        # Create processed directory
        processed_dir = storage_dir / lang_code / "processed"
        processed_dir.mkdir(exist_ok=True)
        
        # Get base filename
        base_filename = article_data['title'].replace('/', '_').replace(':', '_')
        
        # 1. Create cleaned text version
        cleaned_text = clean_article_text(article_data['content'])
        cleaned_data = {
            "title": article_data['title'],
            "language": lang_code,
            "language_name": article_data['language_name'],
            "content": cleaned_text,
            "word_count": len(cleaned_text.split()),
            "char_count": len(cleaned_text),
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "original_file": f"{base_filename}.json"
        }
        
        with open(processed_dir / f"{base_filename}_cleaned.json", 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        
        # 2. Create plain text version
        with open(processed_dir / f"{base_filename}.txt", 'w', encoding='utf-8') as f:
            f.write(f"Title: {article_data['title']}\n")
            f.write(f"Language: {article_data['language_name']} ({lang_code})\n")
            f.write(f"URL: {article_data['url']}\n")
            f.write(f"Extracted: {article_data['extracted_at']}\n")
            f.write(f"Word Count: {len(cleaned_text.split())}\n")
            f.write(f"Character Count: {len(cleaned_text)}\n")
            f.write("-" * 80 + "\n\n")
            f.write(cleaned_text)
        
        # 3. Create metadata summary
        metadata = {
            "title": article_data['title'],
            "language": lang_code,
            "language_name": article_data['language_name'],
            "url": article_data['url'],
            "extracted_at": article_data['extracted_at'],
            "word_count": len(cleaned_text.split()),
            "char_count": len(cleaned_text),
            "sentence_count": len([s for s in cleaned_text.split('.') if s.strip()]),
            "paragraph_count": len([p for p in article_data['content'].split('\n\n') if p.strip()]),
            "has_numbers": any(char.isdigit() for char in cleaned_text),
            "has_links": 'http' in article_data['content'].lower(),
            "processing_info": {
                "cleaned": True,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0"
            }
        }
        
        with open(processed_dir / f"{base_filename}_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error processing article {article_data['title']}: {e}")
        return False

def clean_article_text(text):
    """
    Cleans and normalizes article text.
    
    Args:
        text (str): Raw article text
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Remove citation brackets
    cleaned = re.sub(r'\[\d+\]', '', cleaned)
    cleaned = re.sub(r'\[citation needed\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[who\?\]', '', cleaned, flags=re.IGNORECASE)
    
    # Remove edit links
    cleaned = re.sub(r'\[edit\]', '', cleaned, flags=re.IGNORECASE)
    
    # Remove external link text
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    
    # Clean up punctuation
    cleaned = re.sub(r'\s+([.,!?;:])', r'\1', cleaned)
    
    # Remove multiple periods
    cleaned = re.sub(r'\.{2,}', '.', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def create_summary_report(storage_dir, master_articles):
    """
    Creates a summary report of all extracted and processed articles.
    
    Args:
        storage_dir (Path): Storage directory
        master_articles (list): List of master article titles
    """
    try:
        report_file = storage_dir / "extraction_summary.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Wikipedia Article Extraction Summary\n\n")
            f.write(f"**Extraction Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Articles:** {len(master_articles)}\n")
            f.write(f"**Languages:** {', '.join(TARGET_LANGUAGES)}\n\n")
            
            f.write("## Article List\n\n")
            for i, article in enumerate(master_articles, 1):
                f.write(f"{i}. {article}\n")
            
            f.write("\n## Language Statistics\n\n")
            for lang_code in TARGET_LANGUAGES:
                lang_dir = storage_dir / lang_code
                raw_count = len(list((lang_dir / "raw").glob("*.json")))
                processed_count = len(list((lang_dir / "processed").glob("*.json")))
                
                f.write(f"### {LANG_NAMES[lang_code].capitalize()} ({lang_code})\n")
                f.write(f"- Raw articles: {raw_count}\n")
                f.write(f"- Processed articles: {processed_count}\n")
                f.write(f"- Text files: {len(list((lang_dir / 'processed').glob('*.txt')))}\n")
                f.write(f"- Metadata files: {len(list((lang_dir / 'processed').glob('*_metadata.json')))}\n\n")
            
            f.write("## File Structure\n\n")
            f.write("```\n")
            f.write("extracted_articles/\n")
            for lang_code in TARGET_LANGUAGES:
                f.write(f"├── {lang_code}/\n")
                f.write(f"│   ├── raw/          # Original JSON files\n")
                f.write(f"│   ├── processed/    # Cleaned and formatted files\n")
                f.write(f"│   └── progress.json # Extraction progress\n")
            f.write(f"└── master_articles.json  # Master article list\n")
            f.write("```\n\n")
            
            f.write("## Processing Details\n\n")
            f.write("Each article is processed to create:\n")
            f.write("- **Cleaned JSON**: Text with citations and formatting removed\n")
            f.write("- **Plain Text**: Human-readable format with metadata\n")
            f.write("- **Metadata JSON**: Statistics and article information\n\n")
            
            f.write("## Usage\n\n")
            f.write("This dataset can be used for:\n")
            f.write("- Parallel corpus creation\n")
            f.write("- Multilingual NLP training\n")
            f.write("- Language comparison studies\n")
            f.write("- Translation quality assessment\n")
        
        print(f"✓ Summary report created: {report_file}")
        
    except Exception as e:
        print(f"Error creating summary report: {e}")

def load_progress(lang_code, storage_dir):
    """Loads the progress file to resume extraction."""
    progress_file = storage_dir / lang_code / "progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"completed_articles": [], "last_index": 0}
    return {"completed_articles": [], "last_index": 0}

def save_progress(lang_code, progress_data, storage_dir):
    """Saves the progress to resume later."""
    progress_file = storage_dir / lang_code / "progress.json"
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving progress for {lang_code}: {e}")

def translate_text(text, from_lang, to_lang):
    """
    Placeholder for translation functionality.
    Translation is not used in bulk extraction mode.
    
    Args:
        text (str): The text to translate.
        from_lang (str): The source language code.
        to_lang (str): The target language code.

    Returns:
        str: The original text (no translation performed).
    """
    print(f"Translation not performed in bulk extraction mode.")
    return text

def bulk_extract_articles():
    """
    Main function to perform bulk extraction of 25,000 articles across multiple languages.
    Uses the same article titles across all languages for parallel corpus creation.
    """
    print("=== Wikipedia Bulk Article Extractor ===")
    print(f"Target: {ARTICLES_PER_LANGUAGE} articles per language")
    print(f"Languages: {', '.join(TARGET_LANGUAGES)}")
    print("Strategy: Same articles across all languages for parallel corpus")
    
    # Estimate time
    total_articles = ARTICLES_PER_LANGUAGE * len(TARGET_LANGUAGES)
    estimated_hours = (total_articles * 2) / 3600  # 2 seconds per article average
    print(f"Total articles to extract: {total_articles:,}")
    print(f"Estimated time: {estimated_hours:.1f} hours")
    print("=" * 50)

    # Create storage structure
    storage_dir = create_storage_structure()
    print(f"Storage directory created: {storage_dir}")

    total_stats = {lang: {"target": ARTICLES_PER_LANGUAGE, "completed": 0, "failed": 0}
                   for lang in TARGET_LANGUAGES}

    # Step 1: Get article titles from English Wikipedia with availability check
    print(f"\n--- Step 1: Getting {ARTICLES_PER_LANGUAGE} articles available in ALL languages ---")
    
    # Check if we already have a master list of articles
    master_articles_file = storage_dir / "master_articles.json"
    if master_articles_file.exists():
        print("Loading existing master article list...")
        with open(master_articles_file, 'r', encoding='utf-8') as f:
            master_articles = json.load(f)
        print(f"Loaded {len(master_articles)} existing articles")
    else:
        print("Creating new master article list with availability check...")
        
        # Check if we have partial availability progress
        availability_progress_file = storage_dir / "availability_progress.json"
        if availability_progress_file.exists():
            print("Found existing availability progress, resuming...")
            with open(availability_progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                existing_articles = progress_data.get("available_articles", [])
                print(f"Resuming with {len(existing_articles)} existing articles")
        
        if USE_KNOWN_ARTICLES:
            print("Using known common articles for testing...")
            known_articles = get_known_common_articles()
            master_articles = known_articles[:ARTICLES_PER_LANGUAGE]
            print(f"Selected {len(master_articles)} known articles: {master_articles}")
        else:
            master_articles = get_articles_with_availability_check(ARTICLES_PER_LANGUAGE)
        
        if master_articles:
            # Save the master list
            with open(master_articles_file, 'w', encoding='utf-8') as f:
                json.dump(master_articles, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(master_articles)} articles to master list")
        else:
            print("ERROR: Could not find any articles available in all languages!")
            return

    if not master_articles:
        print("ERROR: Could not get any articles from English Wikipedia!")
        return

    print(f"Master article list: {master_articles[:5]}...")  # Show first 5

    # Step 2: Extract each article from all languages
    print(f"\n--- Step 2: Extracting articles from all languages ---")
    
    for i, article_title in enumerate(master_articles):
        print(f"\n--- Processing Article {i+1}/{len(master_articles)}: '{article_title}' ---")
        
        for lang_code in TARGET_LANGUAGES:
            print(f"  Extracting from {LANG_NAMES[lang_code].capitalize()} ({lang_code})...")
            
            # Load progress for this language
            progress = load_progress(lang_code, storage_dir)
            completed_titles = set(progress.get("completed_articles", []))
            
            # Skip if already completed
            if article_title in completed_titles:
                print(f"    ✓ Already completed")
                continue
            
            # Scrape the article
            article_text = scrape_wikipedia_article(lang_code, article_title)
            
            if article_text:
                # Prepare article data
                article_data = {
                    "title": article_title,
                    "language": lang_code,
                    "language_name": LANG_NAMES[lang_code],
                    "content": article_text,
                    "url": f"https://{lang_code}.wikipedia.org/wiki/{article_title.replace(' ', '_')}",
                    "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "master_article_index": i
                }
                
                # Save the article
                if save_article(article_data, lang_code, storage_dir):
                    # Process the article
                    if process_article(article_data, lang_code, storage_dir):
                        print(f"    ✓ Successfully extracted, saved, and processed")
                    else:
                        print(f"    ⚠ Extracted and saved, but processing failed")
                    
                    completed_titles.add(article_title)
                    total_stats[lang_code]["completed"] += 1
                    
                    # Update progress
                    progress_data = {
                        "completed_articles": list(completed_titles),
                        "last_index": len(completed_titles)
                    }
                    save_progress(lang_code, progress_data, storage_dir)
                else:
                    total_stats[lang_code]["failed"] += 1
                    print(f"    ✗ Failed to save article")
            else:
                total_stats[lang_code]["failed"] += 1
                print(f"    ✗ Failed to extract article (may not exist in {lang_code})")
            
            # Rate limiting
            time.sleep(1)
        
        print(f"  Completed article {i+1}/{len(master_articles)} across all languages")

    # Print final statistics
    print("\n" + "=" * 50)
    print("EXTRACTION COMPLETE - FINAL STATISTICS")
    print("=" * 50)

    total_completed = 0
    total_failed = 0

    for lang_code in TARGET_LANGUAGES:
        # Get actual completed count from progress file
        progress = load_progress(lang_code, storage_dir)
        actual_completed = len(progress.get("completed_articles", []))
        failed = total_stats[lang_code]["failed"]
        target = total_stats[lang_code]["target"]

        total_completed += actual_completed
        total_failed += failed

        print(f"{LANG_NAMES[lang_code].capitalize()} ({lang_code}): {actual_completed}/{target} completed, {failed} failed")

    print("-" * 50)
    print(f"TOTAL: {total_completed}/25000 completed, {total_failed} failed")
    success_rate = (total_completed / 25000) * 100 if total_completed > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    print(f"\nArticles saved in: {storage_dir}/")
    
    # Create summary report
    create_summary_report(storage_dir, master_articles)

def main():
    """
    Main function - runs bulk extraction by default.
    For single article extraction, modify the code.
    """
    try:
        bulk_extract_articles()
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Progress has been saved. You can resume later.")

if __name__ == "__main__":
    main()
