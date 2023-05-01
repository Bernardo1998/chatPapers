import os
import PyPDF2
import re
import pandas as pd
from pdfminer.high_level import extract_text
import requests
from urllib.parse import urlparse
from scholarly import ProxyGenerator, scholarly
from tqdm import tqdm
              
              
class ScholarlySearch:
    def __init__(self):
        # Set up a ProxyGenerator object to use free proxies
        # This needs to be done only once per session
        pg = ProxyGenerator()
        pg.FreeProxies()
        scholarly.use_proxy(pg)
        
    def download_pdf(self,pdf_url,pdf_dirpath):
        filename = urlparse(pdf_url).path.split('/')[-1]
        file_path = os.path.join(pdf_dirpath, filename)
        # Do not download repeatedly
        if not os.path.exists(file_path):
            response = requests.get(pdf_url)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
        return file_path
        
    def download_pdf_byname(self, paper_name, pdf_dirpath):
        search_query = scholarly.search_pubs(paper_name)
        pdf_path = None
        try:
            result = next(search_query) 
            pdf_path = self.download_pdf(pdf_url, pdf_dirpath)
        except Exception as e:
            print(f'Exception when downloading paper: {paper_name}, error: {e}')
    	    
        return pdf_path
        
    def get_pdf_text(self, pdf_path):
        # Extract text from the PDF file
        text = extract_text(pdf_path)

        # Remove extra spaces and line breaks
        text = re.sub(r'\n+', '\n', text).strip()

        return text

    def split_text(self, text, max_words=1000):
        words = text.split()
        result = []

        while words:
            chunk = words[:max_words]
            result.append(' '.join(chunk))
            words = words[max_words:]

        return result
        
    def split_pdf(self, pdf_path, max_words=1000):
        pdf_text = self.get_pdf_text(pdf_path)
        text_chunks = self.split_text(pdf_text, max_words)

        return text_chunks
                
    def get_top_abstracts(self, query, num_papers=10, max_count=1000, pdf_dirpath='pdfs', max_words=500):
        search_query = scholarly.search_pubs(query)
        count = 0
        abstracts = []
        urls = []
        bibs = []
        
        while count < num_papers and count < max_count:
            try:
                result = next(search_query) 
                pdf_url = result['eprint_url'] if 'pdf' in result['eprint_url'] else None
                if pdf_url is not None:
                    print(pdf_url)
                    pdf_path = self.download_pdf(pdf_url, pdf_dirpath)
                    # Assume the first 500 words are abstracts.
                    abstract = self.split_pdf(pdf_path, max_words)[0]
                    abstracts.append(abstract)
                    urls.append(pdf_url)
                    bibs.append(result['bib'])
                    count += 1
            except StopIteration:
                break
            except Exception as e:
                print(f"Error while getting abstract: {e}")
                continue
                
        return abstracts, urls, bibs

    def download_top_pdfs(self, query, num_pdfs=1, pdf_dirpath='pdfs', max_count=1000):
        # Create a subdirectory to save the PDF files
        if not os.path.exists(pdf_dirpath):
            os.makedirs(pdf_dirpath)
        # Search for articles
        search_query = scholarly.search_pubs(query)

        # Download the PDFs of the top N most relevant papers and save them in the specified directory
        count = 0
        paper_names = []
        while count < num_pdfs and count < max_count:
            try:
                result = next(search_query)
                #print(result.keys())
                #result.fill()
                pdf_url = result['eprint_url'] if 'pdf' in result['eprint_url'] else None
                print(pdf_url)

                if pdf_url is not None:
                    # Download the PDF file using requests
                    _ = self.download_pdf(pdf_url, pdf_dirpath)
                    count += 1
                    paper_names.append(result['bib'])
            except StopIteration:
                break
            except Exception as e:
                print(f"Error while downloading PDF: {e}")
                continue
        return paper_names
