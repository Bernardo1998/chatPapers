import requests
import os
import time

# User Inputs
API_KEY = 'your_api_key_here'  # Replace with your Semantic Scholar API key
PAPER_ID = 'your_paper_id_here'  # Replace with the Semantic Scholar ID of the target paper
SAVE_DIR = 'downloaded_pdfs'  # Directory to save downloaded PDFs
PAGE_SIZE = 100  # Number of citing papers to retrieve per page
DELAY_BETWEEN_REQUESTS = 1  # Delay in seconds between API requests to respect rate limits

# Ensure the save directory exists
os.makedirs(SAVE_DIR, exist_ok=True)

def fetch_citing_papers(paper_id, api_key, page_size=100):
    """
    Fetches papers citing the specified paper using the Semantic Scholar API.
    """
    all_citing_papers = []
    page = 1
    headers = {'x-api-key': api_key} if api_key else {}
    while True:
        url = f'https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations'
        params = {
            'fields': 'title,authors,year,externalIds',
            'limit': page_size,
            'offset': (page - 1) * page_size
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            all_citing_papers.extend(data['data'])
            if len(data['data']) < page_size:
                break
            page += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)  # Respect rate limits
        else:
            print(f'Error: {response.status_code} - {response.text}')
            break
    return all_citing_papers

def download_pdf(doi, save_dir):
    """
    Attempts to download the PDF of a paper given its DOI.
    """
    pdf_url = f'https://doi.org/{doi}'
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            filename = doi.replace('/', '_') + '.pdf'
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f'Successfully downloaded: {filename}')
        else:
            print(f'Failed to download PDF for DOI: {doi} - Status Code: {response.status_code}')
    except Exception as e:
        print(f'Error downloading PDF for DOI: {doi} - {e}')

def main():
    # Fetch citing papers
    citing_papers = fetch_citing_papers(PAPER_ID, API_KEY, PAGE_SIZE)
    print(f'Total citing papers retrieved: {len(citing_papers)}')

    # Attempt to download PDFs of citing papers
    for paper in citing_papers:
        doi = paper.get('externalIds', {}).get('DOI')
        if doi:
            download_pdf(doi, SAVE_DIR)
        else:
            print(f'No DOI found for paper: {paper.get("title", "Unknown Title")}')

if __name__ == '__main__':
    main()
