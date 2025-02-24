import os
import serpapi
import requests
from urllib.parse import urlparse
import time
import argparse
import json

def load_api_key(key_file='config.json'):
    """Load API key from config file"""
    try:
        with open(key_file, 'r') as f:
            config = json.load(f)
            return config.get('serpapi_key')
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None

def get_citing_papers(cited_paper_id, api_key, max_pages=None, wait_time=2):
    """Get papers that cite a specific paper across multiple pages
    Args:
        cited_paper_id: ID of the paper to get citations for
        api_key: SerpAPI key
        max_pages: Maximum number of pages to fetch (None for all pages)
        wait_time: Time to wait between requests in seconds
    """
    all_papers = []
    start = 0
    page = 1
    
    try:
        while True:
            client = serpapi.Client(api_key=api_key)
            results = client.search({
                'engine': 'google_scholar',
                'cites': cited_paper_id,
                'start': start  # Pagination parameter
            })
            
            papers = results.get('organic_results', [])
            if not papers:  # No more results
                break
                
            all_papers.extend(papers)
            print(f"Fetched page {page} - Found {len(papers)} papers")
            
            # Check if there's a next page
            if not results.get('pagination', {}).get('next'):
                break
                
            # Check if we've reached max_pages
            if max_pages and page >= max_pages:
                break
                
            start += 10  # Google Scholar uses 10 results per page
            page += 1
            time.sleep(wait_time)  # Be nice to the API
            
        return all_papers
    except Exception as e:
        print(f"Error getting citing papers: {e}")
        return all_papers  # Return what we've got so far

def download_pdf(url, save_dir):
    """Download PDF from a given URL"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Get filename from URL or use a default
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        filepath = os.path.join(save_dir, filename)
        
        # Download the file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check if it's actually a PDF
        if 'application/pdf' in response.headers.get('content-type', '').lower():
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded: {filename}")
            return True
        else:
            print(f"Not a valid PDF: {url}")
            return False
            
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main(query, save_dir='downloaded_papers', max_citation_pages=None, wait_time=2):
    """
    Args:
        query: Search query string
        save_dir: Directory to save downloaded PDFs
        max_citation_pages: Maximum number of citation pages to process (None for all)
        wait_time: Time to wait between requests in seconds
    """
    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("No API key found. Please add your SerpAPI key to config.json")
        return

    # Initial search
    client = serpapi.Client(api_key=api_key)
    results = client.search({
        'engine': 'google_scholar',
        'q': query,
    })

    # Get the first paper's citation ID
    if results.get('organic_results'):
        first_paper = results['organic_results'][0]
        citation_id = first_paper.get('inline_links', {}).get('cited_by', {}).get('cites_id')
        
        if citation_id:
            print(f"Finding papers citing: {first_paper.get('title')}")
            citing_papers = get_citing_papers(citation_id, api_key, max_citation_pages, wait_time)
            print(f"Total citing papers found: {len(citing_papers)}")
            
            # Create a directory for PDFs
            os.makedirs(save_dir, exist_ok=True)
            
            # Download PDFs from citing papers
            downloaded_count = 0
            for paper in citing_papers:
                # Check for direct PDF links in resources
                resources = paper.get('resources', [])
                for resource in resources:
                    if resource.get('file_format') == 'PDF':
                        if download_pdf(resource['link'], save_dir):
                            downloaded_count += 1
                
                # Check the main link
                main_link = paper.get('link', '')
                if main_link.endswith('.pdf'):
                    if download_pdf(main_link, save_dir):
                        downloaded_count += 1
                    
                # Add a small delay to avoid overwhelming servers
                time.sleep(wait_time)
            
            print(f"Downloaded {downloaded_count} PDFs to {save_dir}")
        else:
            print("No citation ID found for the first paper")
    else:
        print("No results found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download academic papers and their citations from Google Scholar')
    parser.add_argument('query', type=str, help='Search query string')
    parser.add_argument('--save_dir', type=str, default='pdfs_folder',
                      help='Directory to save downloaded PDFs (default: pdfs_folder)')
    parser.add_argument('--max_pages', type=int, default=None,
                      help='Maximum number of citation pages to process (default: None for all pages)')
    parser.add_argument('--wait_time', type=float, default=2.0,
                      help='Time to wait between requests in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    main(
        query=args.query,
        save_dir=args.save_dir,
        max_citation_pages=args.max_pages,
        wait_time=args.wait_time
    )