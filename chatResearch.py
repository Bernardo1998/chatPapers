import openai
import os
import PyPDF2
import re
import pandas as pd
from pdfminer.high_level import extract_text
import requests
from urllib.parse import urlparse
from scholarly import ProxyGenerator, scholarly
from tqdm import tqdm
import argparse


from ChatPaper import ChatPaper
from ScholarlySearch import ScholarlySearch
              
openai.api_key = "your_openai_key"

def session_type():
    next_prompt = "Enter 1 to ask a question, 2 to search with a set of keywords."
    choice = 0
    while choice == 0:
        entry = input(next_prompt)
        if '1' == entry:
            next_prompt = "Please enter the research question:"
            choice = 1
        elif '2' == entry:
            next_prompt = "Please enter the search keywords:"
            choice = 2
        else:
            next_prompt = "Invalid choice! Please enter 1 or 2"
            
    return input(next_prompt), choice
        
def filter_by_abstracts(engine, reader, search_keywords, paper_each_round=10):
    abstracts, _, bibs = engine.get_top_abstracts(search_keywords,num_papers=paper_each_round)
    
    abstracts_dicts = []

    for i, item in tqdm(enumerate(zip(abstracts, bibs))):
        try:
            ab, bib = item[0], item[1]
            del bib['abstract']
            bib['author'] = ' and '.join(bib['author'])
            #print(bib)
            abstract_info = reader.read_abstract(ab,search_keywords)
            bib.update(abstract_info)
            abstracts_dicts.append(bib)
        except Exception as e:
            print(f"Error when reading abstract: {e}")
            continue
        #print(abstract_info)
        #break
    
    abstract_df['related'] = abstract_df['related'].str.lower()
    abstract_df = pd.DataFrame(abstracts_dicts, index=[i for i in range(len(abstracts_dicts))])      
    related_df = abstract_df.loc[abstract_df['related'].str.contains('yes')]
    
    return abstract_df, related_df
    
    
def interactive_session(engine, reader):
    request, choice = session_type()
    if choice == 1:
        question = request
        search_keywords = reader.design_search_keywords(question) 
        search_keywords = re.sub(r"['\"]", "", search_keywords)
        print(f"Suggested keyword:{search_keywords}")
    else:
        question = None
        search_keywords = request
    
    paper_each_round = 5
    searched_round, max_round = 0, 10
    csv_path = ''.join(['csv/abstract']+[w.capitalize() for w in search_keywords.split()]+['.csv'])
    print(csv_path)

    while searched_round < max_round:
        try:    
            abstract_df, related_df = filter_by_abstracts(engine, reader, search_keywords, paper_each_round)
            abstract_df.to_csv(csv_path, index=False)
            print(related_df)
            break
        except Exception as e:
            print(f"Error getting abstract! {e}")
            searched_round += 1
            
        # Decide if the problem is solved. 
        # If not solved, update search keywords.
        # How to determine if these problems are good?
        
# TODO: make paper_list a df with both title and url. 
# First try read by title and return extracted bib. If failed, use url.
def summarize_paper_list(engine, reader, paper_list_path, csv_path, search_keywords='', pdf_dirpath='pdfs', chunk_size=1000, read=None):
    '''
        paper_list_path: path to a pd dataframe, each row has a title and a url. 
        readPapers: file path of a pd data frame of all read papers.
    '''
    dfs = []
    paper_list = pd.read_csv(paper_list_path)
    #print("Paper_list is:",paper_list)
    readPapers = pd.read_csv(read) if read is not None else None
    readPapersPath = read if read is not None else "DefaultRreadPapers.csv"
    
    for i in range(paper_list.shape[0]):
        # Skip read papers
        title, url = paper_list['Title'][i], paper_list['URL'][i]
        if readPapers is not None and (title in readPapers['Title'] or url in readPapers['URL']):
            continue 

        pdf_path = engine.download_pdf(url,pdf_dirpath)
            
        try:
            chunk = engine.split_pdf(pdf_path,chunk_size)
            summary = reader.summarize_paper(chunk, search_keywords)
        except Exception as e:
            print(f"Exception {e} when loading: {title}")
            # Fill in empty, ensure output and paper_list have the same row number.
            summary = {}
            for col in reader.new_col_names:
                summary[col] = ''
            summary = pd.DataFrame(summary, index=[i])
            
        dfs.append(summary)
           
    output = pd.concat(dfs, axis=0).reset_index()
    #print(output, paper_list)
    output = pd.concat([paper_list,output], axis=1)
    output.to_csv(csv_path, index=False)
    
    readPapers = pd.concat([readPapers, paper_list], axis=0)
    readPapers.to_csv(readPapersPath, index=False)
    
    
def filter_and_summarize(engine, reader, args):
    pass
       
if __name__ == "__main__" :    
    parser = argparse.ArgumentParser(description='Description of your script')

    parser.add_argument('--action', type=str, help='Action to take in this session.', default='load')
    parser.add_argument('-f', '--file', type=str, help='Input df path with papers to read.', default='paper_lists/paper_list.csv')
    parser.add_argument('-plc', '--paperListColumn', type=str, help='Column name of the paper list', default='url')
    parser.add_argument('-ft', '--fileType', type=str, help='Paper list type, url or title', default='url')
    parser.add_argument('-s', '--search_keywords', type=str, help='Search keywords', default='')
    parser.add_argument('--sep', type=str, help='Separator', default='\t')
    parser.add_argument('--read', type=str, help='file of read papers', default='readPapers.csv')
    parser.add_argument('--pdf_dirpath', type=str, help='dir to save pdfs', default='pdfs')
    parser.add_argument('--chunk_size', type=int, help='max words in a chunk', default=1000)
    
    args = parser.parse_args()

    engine = ScholarlySearch()
    reader = ChatPaper()
        
    action = args.action #['load', 'interactive', 'filter']
    
    if action == 'interactive':
        interactive_session(engine, reader)
    elif action == 'load':
        paper_list_path = args.file
        
        search_keywords = args.search_keywords
        #print(paper_list_path, search_keywords)
        csv_path = ''.join(['csv/summary']+[w.capitalize() for w in search_keywords.split()]+['.csv'])
        summarize_paper_list(engine, reader, paper_list_path, csv_path, search_keywords,read=args.read)
    elif action == 'filer':
        pass
    else:
        raise NotImplementedError(f"Action type {action} is not implemented!")

    print("total_token:",reader.total_token)
