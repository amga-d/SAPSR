"""
Destinations Scraper for Yogyakarta Tourism

This script scrapes the list of tourism destinations from yogyes.com
and saves them to a CSV file with Google Maps search queries.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Configuration
URL = "https://www.yogyes.com/id/yogyakarta-tourism-object/"
OUTPUT_FILE = "destinations.csv"


def scrape_destinations():
    """Scrape tourism destination names from yogyes.com"""
    print(f"Fetching destinations from {URL}...")
    
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all h2 elements which contain destination names
    destinations = []
    
    # The destinations are in h2 tags with format "1. Candi Prambanan", "2. Malioboro", etc.
    for h2 in soup.find_all('h2'):
        text = h2.get_text(strip=True)
        # Match pattern: "number. destination name"
        match = re.match(r'^\d+\.\s*(.+)$', text)
        if match:
            name = match.group(1)
            destinations.append(name)
    
    print(f"Found {len(destinations)} destinations")
    return destinations


def create_search_queries(destinations):
    """Create Google Maps search queries for each destination"""
    data = []
    for name in destinations:
        # Add "Yogyakarta" to make the search more specific
        search_query = f"{name} Yogyakarta"
        data.append({
            'name': name,
            'search_query': search_query
        })
    return data


def save_to_csv(data, filename):
    """Save destinations to CSV file"""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Saved {len(data)} destinations to {filename}")


def main():
    print("=" * 50)
    print("Yogyakarta Tourism Destinations Scraper")
    print("=" * 50)
    
    # Scrape destinations
    destinations = scrape_destinations()
    
    if not destinations:
        print("No destinations found. Exiting.")
        return
    
    # Create search queries
    data = create_search_queries(destinations)
    
    # Save to CSV
    save_to_csv(data, OUTPUT_FILE)
    
    # Display first 10 destinations
    print("\nFirst 10 destinations:")
    for i, item in enumerate(data[:10], 1):
        print(f"  {i}. {item['name']} -> {item['search_query']}")
    
    print("\n" + "=" * 50)
    print("Scraping complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
