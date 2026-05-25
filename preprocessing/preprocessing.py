"""
Text Preprocessing Script for Google Reviews

This script performs preprocessing on scraped Google reviews:
1. Remove duplicate comments
2. Remove stop words (Indonesian + English)
3. Remove punctuations
4. Save cleaned data to new CSV file
5. Generate documentation of all preprocessing steps

Input: yogyakarta_tourism_reviews.csv
Output: yogyakarta_tourism_reviews_preprocessed.csv
Documentation: preprocessing_documentation.txt

Requirements:
    pip install pandas nltk Sastrawi
"""

import pandas as pd
import re
import string
import nltk
from datetime import datetime

# Download NLTK data (run once)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

from nltk.corpus import stopwords

# ============== Configuration ==============
INPUT_FILE = "yogyakarta_tourism_reviews.csv"
OUTPUT_FILE = "yogyakarta_tourism_reviews_preprocessed.csv"
DOCUMENTATION_FILE = "preprocessing_documentation.txt"

# Indonesian stop words (comprehensive list)
INDONESIAN_STOP_WORDS = {
    # Common words
    'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'dengan', 'untuk', 'pada',
    'adalah', 'sebagai', 'dalam', 'tidak', 'akan', 'tetapi', 'juga', 'atau',
    'karena', 'ada', 'bisa', 'sudah', 'saya', 'kami', 'kita', 'mereka', 'anda',
    'dia', 'ia', 'beliau', 'kamu', 'kalian', 'nya', 'ku', 'mu',
    # Prepositions and conjunctions
    'oleh', 'tentang', 'seperti', 'ketika', 'setelah', 'sebelum', 'jika', 'bila',
    'maka', 'sehingga', 'agar', 'supaya', 'namun', 'walau', 'walaupun', 'meski',
    'meskipun', 'sedang', 'sambil', 'bahwa', 'daripada', 'demi', 'hingga',
    'sampai', 'selama', 'sejak', 'antara', 'terhadap', 'mengenai', 'sekitar',
    # Pronouns and determiners
    'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan',
    'sembilan', 'sepuluh', 'banyak', 'sedikit', 'beberapa', 'semua', 'setiap',
    'para', 'sang', 'si', 'tersebut', 'begitu', 'demikian',
    # Adverbs
    'sangat', 'amat', 'sekali', 'paling', 'lebih', 'kurang', 'cukup', 'agak',
    'hampir', 'selalu', 'sering', 'kadang', 'jarang', 'tidak', 'bukan', 'belum',
    'sudah', 'telah', 'pernah', 'masih', 'lagi', 'hanya', 'saja', 'pun',
    'bahkan', 'justru', 'malah', 'terlalu', 'begini', 'begitu',
    # Verbs (common auxiliary/helper)
    'dapat', 'bisa', 'harus', 'perlu', 'boleh', 'mau', 'ingin', 'hendak',
    'akan', 'sedang', 'tengah', 'mulai', 'terus', 'tetap',
    # Question words
    'apa', 'siapa', 'mana', 'kapan', 'dimana', 'kemana', 'bagaimana', 'mengapa',
    'kenapa', 'berapa',
    # Common informal words
    'yg', 'dgn', 'utk', 'krn', 'klo', 'kalo', 'gak', 'ga', 'nggak', 'ngga',
    'udah', 'udh', 'blm', 'tp', 'tpi', 'tapi', 'jd', 'jadi', 'jg', 'juga',
    'sm', 'sama', 'bgt', 'banget', 'aja', 'doang', 'dong', 'deh', 'sih', 'nih',
    'tuh', 'lho', 'loh', 'kok', 'kan', 'ya', 'yaa', 'gitu', 'gini', 'gimana',
    'gmn', 'emang', 'emg', 'bkn', 'kyk', 'kayak', 'kaya', 'dlm', 'dr', 'pd',
    'sy', 'ak', 'aku', 'gw', 'gue', 'lo', 'lu', 'bs', 'hrs', 'org', 'orang',
    'yah', 'wkwk', 'wkwkwk', 'haha', 'hehe', 'hihi', 'huhu',
    # Time-related
    'hari', 'minggu', 'bulan', 'tahun', 'jam', 'menit', 'detik', 'pagi',
    'siang', 'sore', 'malam', 'kemarin', 'besok', 'lusa', 'nanti', 'tadi',
    'sekarang', 'dulu', 'lalu',
    # Place-related
    'sini', 'situ', 'sana', 'tempat', 'disini', 'disitu', 'disana', 'kesini',
    'kesitu', 'kesana',
    # Others
    'hal', 'cara', 'waktu', 'kali', 'lain', 'sama', 'sendiri', 'bersama',
    'per', 'tiap', 'sebuah', 'suatu', 'salah', 'berbagai', 'macam', 'jenis',
    'oh', 'ah', 'eh', 'uh', 'ih', 'aduh', 'astaga', 'wow', 'yay', 'yeay',
}

# Get English stop words from NLTK
try:
    ENGLISH_STOP_WORDS = set(stopwords.words('english'))
except:
    ENGLISH_STOP_WORDS = set()

# Combine all stop words
ALL_STOP_WORDS = INDONESIAN_STOP_WORDS.union(ENGLISH_STOP_WORDS)


class PreprocessingStats:
    """Class to track preprocessing statistics"""
    def __init__(self):
        self.original_count = 0
        self.after_duplicates = 0
        self.empty_removed = 0
        self.total_words_before = 0
        self.total_words_after = 0
        self.stopwords_removed = 0
        self.punctuation_removed = 0
        self.duplicates_removed = 0

    def to_dict(self):
        return {
            'original_reviews': self.original_count,
            'after_duplicate_removal': self.after_duplicates,
            'duplicates_removed': self.duplicates_removed,
            'empty_reviews_removed': self.empty_removed,
            'total_words_before_cleaning': self.total_words_before,
            'total_words_after_cleaning': self.total_words_after,
            'words_removed': self.total_words_before - self.total_words_after,
        }


def count_words(text):
    """Count words in text"""
    if pd.isna(text) or not isinstance(text, str):
        return 0
    return len(text.split())


def remove_punctuation(text):
    """Remove punctuation from text while preserving spaces"""
    if pd.isna(text) or not isinstance(text, str):
        return ""

    # Define punctuation to remove (keep alphanumeric and spaces)
    # Also remove common symbols and emojis
    punctuation_pattern = r'[^\w\s]'

    # Remove punctuation
    cleaned = re.sub(punctuation_pattern, ' ', text)

    # Remove extra whitespace and normalize
    cleaned = ' '.join(cleaned.split())

    return cleaned


def remove_stopwords(text, stop_words):
    """Remove stop words from text"""
    if pd.isna(text) or not isinstance(text, str):
        return ""

    words = text.lower().split()
    filtered_words = [word for word in words if word.lower() not in stop_words]

    return ' '.join(filtered_words)


def clean_text(text):
    """Apply basic text cleaning"""
    if pd.isna(text) or not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Remove numbers (optional - comment out if you want to keep numbers)
    text = re.sub(r'\d+', '', text)

    # Remove extra whitespace
    text = ' '.join(text.split())

    return text


def preprocess_reviews(input_file, output_file, doc_file):
    """Main preprocessing function"""
    stats = PreprocessingStats()

    print("=" * 60)
    print("TEXT PREPROCESSING FOR GOOGLE REVIEWS")
    print("=" * 60)
    print(f"\nInput file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Documentation: {doc_file}")
    print()

    # Step 1: Load data
    print("Step 1: Loading data...")
    try:
        df = pd.read_csv(input_file)
        stats.original_count = len(df)
        print(f"   Loaded {stats.original_count} reviews")
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return None
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

    # Display columns
    print(f"   Columns: {list(df.columns)}")

    # Step 2: Remove duplicate comments
    print("\nStep 2: Removing duplicate comments...")
    # Remove duplicates based on 'text' column
    df_no_duplicates = df.drop_duplicates(subset=['text'], keep='first')
    stats.after_duplicates = len(df_no_duplicates)
    stats.duplicates_removed = stats.original_count - stats.after_duplicates
    print(f"   Removed {stats.duplicates_removed} duplicate reviews")
    print(f"   Remaining reviews: {stats.after_duplicates}")

    # Step 3: Handle empty/null values
    print("\nStep 3: Handling empty reviews...")
    # Count empty texts
    empty_mask = df_no_duplicates['text'].isna() | (df_no_duplicates['text'] == '')
    stats.empty_removed = empty_mask.sum()

    # Fill empty texts with empty string for processing
    df_no_duplicates = df_no_duplicates.copy()
    df_no_duplicates['text'] = df_no_duplicates['text'].fillna('')

    # Remove rows with empty text
    df_clean = df_no_duplicates[df_no_duplicates['text'].str.strip() != ''].copy()
    print(f"   Removed {stats.empty_removed} empty reviews")
    print(f"   Remaining reviews: {len(df_clean)}")

    # Count words before processing
    stats.total_words_before = df_clean['text'].apply(count_words).sum()
    print(f"\nTotal words before cleaning: {stats.total_words_before:,}")

    # Step 4: Create processed text column
    print("\nStep 4: Cleaning text (lowercase, URLs, emails, numbers)...")
    df_clean['text_cleaned'] = df_clean['text'].apply(clean_text)

    # Step 5: Remove punctuation
    print("\nStep 5: Removing punctuation...")
    df_clean['text_no_punct'] = df_clean['text_cleaned'].apply(remove_punctuation)

    # Step 6: Remove stop words
    print("\nStep 6: Removing stop words...")
    print(f"   Using {len(ALL_STOP_WORDS)} stop words (Indonesian + English)")
    df_clean['text_preprocessed'] = df_clean['text_no_punct'].apply(
        lambda x: remove_stopwords(x, ALL_STOP_WORDS)
    )

    # Count words after processing
    stats.total_words_after = df_clean['text_preprocessed'].apply(count_words).sum()
    print(f"\nTotal words after cleaning: {stats.total_words_after:,}")
    print(f"Words removed: {stats.total_words_before - stats.total_words_after:,}")

    # Step 7: Prepare final dataframe
    print("\nStep 7: Preparing final output...")

    # Create final dataframe with original and preprocessed text
    df_final = df_clean[['destination', 'user_url', 'username', 'stars', 'time',
                          'text', 'text_preprocessed']].copy()

    # Rename columns for clarity
    df_final = df_final.rename(columns={
        'text': 'original_text',
        'text_preprocessed': 'cleaned_text'
    })

    # Ensure each review is in one row (replace newlines with spaces in text columns)
    df_final['original_text'] = df_final['original_text'].apply(
        lambda x: ' '.join(str(x).split()) if pd.notna(x) else ''
    )
    df_final['cleaned_text'] = df_final['cleaned_text'].apply(
        lambda x: ' '.join(str(x).split()) if pd.notna(x) else ''
    )

    # Remove any reviews where cleaned_text is empty after preprocessing
    final_empty = (df_final['cleaned_text'].str.strip() == '').sum()
    df_final = df_final[df_final['cleaned_text'].str.strip() != '']

    print(f"   Removed {final_empty} reviews that became empty after preprocessing")
    print(f"   Final review count: {len(df_final)}")

    # Step 8: Save to CSV
    print(f"\nStep 8: Saving to {output_file}...")
    df_final.to_csv(output_file, index=False, encoding='utf-8')
    print(f"   Saved {len(df_final)} preprocessed reviews")

    # Step 9: Generate documentation
    print(f"\nStep 9: Generating documentation ({doc_file})...")
    generate_documentation(stats, df_final, doc_file, input_file, output_file)

    # Print summary
    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"Original reviews:     {stats.original_count:,}")
    print(f"Duplicates removed:   {stats.duplicates_removed:,}")
    print(f"Final reviews:        {len(df_final):,}")
    print(f"Words before:         {stats.total_words_before:,}")
    print(f"Words after:          {stats.total_words_after:,}")
    print(f"Output file:          {output_file}")
    print(f"Documentation:        {doc_file}")
    print("=" * 60)

    return df_final


def generate_documentation(stats, df_final, doc_file, input_file, output_file):
    """Generate documentation file for preprocessing steps"""

    doc_content = f"""================================================================================
TEXT PREPROCESSING DOCUMENTATION
Google Reviews - Yogyakarta Tourism Destinations
================================================================================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Input File: {input_file}
Output File: {output_file}

================================================================================
1. PREPROCESSING STEPS
================================================================================

Step 1: Load Data
-----------------
- Loaded raw reviews from CSV file
- Original review count: {stats.original_count:,}

Step 2: Remove Duplicate Comments
---------------------------------
- Identified and removed duplicate reviews based on exact text match
- Kept first occurrence of each unique review
- Duplicates removed: {stats.duplicates_removed:,}
- Reviews after deduplication: {stats.after_duplicates:,}

Step 3: Handle Empty Reviews
----------------------------
- Identified reviews with empty or null text content
- Removed empty reviews from dataset
- Empty reviews removed: {stats.empty_removed:,}

Step 4: Text Cleaning
---------------------
- Converted all text to lowercase
- Removed URLs (http, https, www patterns)
- Removed email addresses
- Removed numeric characters
- Normalized whitespace

Step 5: Remove Punctuation
--------------------------
- Removed all punctuation marks and special characters
- Preserved alphanumeric characters and spaces
- Removed emojis and symbols
- Punctuation pattern used: [^\\w\\s]

Step 6: Remove Stop Words
-------------------------
- Applied bilingual stop word removal (Indonesian + English)
- Indonesian stop words: {len(INDONESIAN_STOP_WORDS):,} words
- English stop words (NLTK): {len(ENGLISH_STOP_WORDS):,} words
- Total unique stop words: {len(ALL_STOP_WORDS):,} words

Indonesian Stop Words Categories:
- Common words (yang, dan, di, ke, dari, ini, itu, etc.)
- Prepositions and conjunctions (oleh, tentang, seperti, etc.)
- Pronouns and determiners (saya, kami, kita, mereka, etc.)
- Adverbs (sangat, amat, sekali, paling, etc.)
- Auxiliary verbs (dapat, bisa, harus, perlu, etc.)
- Question words (apa, siapa, mana, kapan, etc.)
- Informal/slang words (yg, dgn, utk, gak, bgt, etc.)
- Time-related words (hari, minggu, bulan, etc.)
- Place-related words (sini, situ, tempat, etc.)

Step 7: Finalize Output
-----------------------
- Ensured each review remains in a single row
- Replaced newline characters with spaces
- Removed reviews that became empty after preprocessing

================================================================================
2. STATISTICS SUMMARY
================================================================================

Data Statistics:
- Original reviews:              {stats.original_count:,}
- Duplicates removed:            {stats.duplicates_removed:,}
- Empty reviews removed:         {stats.empty_removed:,}
- Final review count:            {len(df_final):,}
- Reduction rate:                {((stats.original_count - len(df_final)) / stats.original_count * 100):.2f}%

Word Statistics:
- Total words before cleaning:   {stats.total_words_before:,}
- Total words after cleaning:    {stats.total_words_after:,}
- Words removed:                 {stats.total_words_before - stats.total_words_after:,}
- Word reduction rate:           {((stats.total_words_before - stats.total_words_after) / stats.total_words_before * 100):.2f}%

================================================================================
3. OUTPUT FILE STRUCTURE
================================================================================

The output CSV file contains the following columns:

| Column          | Description                                      |
|-----------------|--------------------------------------------------|
| destination     | Name of the tourism destination                  |
| user_url        | URL to reviewer's Google profile                 |
| username        | Reviewer's display name                          |
| stars           | Rating given (1-5 stars)                         |
| time            | Time of review (relative, e.g., "2 weeks ago")   |
| original_text   | Original review text (single row, spaces only)   |
| cleaned_text    | Preprocessed text (lowercase, no stopwords/punct)|

================================================================================
4. DESTINATION BREAKDOWN
================================================================================

Reviews per destination after preprocessing:

"""
    # Add destination breakdown
    dest_counts = df_final['destination'].value_counts()
    for dest, count in dest_counts.items():
        doc_content += f"{dest}: {count:,} reviews\n"

    doc_content += f"""
================================================================================
5. RATING DISTRIBUTION
================================================================================

"""
    # Add rating distribution
    rating_counts = df_final['stars'].value_counts().sort_index()
    for rating, count in rating_counts.items():
        stars_visual = '*' * int(rating) if pd.notna(rating) else 'N/A'
        doc_content += f"{stars_visual} ({rating} stars): {count:,} reviews\n"

    doc_content += f"""
================================================================================
6. SAMPLE PREPROCESSED REVIEWS
================================================================================

"""
    # Add sample reviews
    samples = df_final.head(5)
    for idx, row in samples.iterrows():
        doc_content += f"Destination: {row['destination']}\n"
        doc_content += f"Rating: {row['stars']} stars\n"
        doc_content += f"Original: {row['original_text'][:200]}...\n"
        doc_content += f"Cleaned:  {row['cleaned_text'][:200]}...\n"
        doc_content += "-" * 60 + "\n"

    doc_content += """
================================================================================
7. TECHNICAL DETAILS
================================================================================

Libraries Used:
- pandas: Data manipulation and CSV handling
- re: Regular expressions for text cleaning
- string: String operations
- nltk: Natural Language Toolkit for English stop words

Code File: preprocessing.py
Python Version: 3.x

================================================================================
END OF DOCUMENTATION
================================================================================
"""

    # Write documentation file
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write(doc_content)

    print(f"   Documentation saved to {doc_file}")


def main():
    """Main entry point"""
    preprocess_reviews(INPUT_FILE, OUTPUT_FILE, DOCUMENTATION_FILE)


if __name__ == "__main__":
    main()
