import openai
import os
import PyPDF2
import re
import pandas as pd
import requests
from tqdm import tqdm

import json
from Preset import Preset
              
       
'''
Functions I want to impelement:
(done)0, create the pandas data frame for literatures
(done)1, take a general instruction
2, take a input xlsx file containing names of pdfs
(done)3, for each url download the pdf and convert it to text
(done)4, Ask chatgpt to read the text approximately 1000 words at a time, summarize the part read. If there are any key points mentioned in this part, save the summarized keypoints into the pandas dataframe.
(done)5, record status log
6, based on status log, let GPT decide if the mission is completed.

Some limits:
1, disk usage
2, chatgpt usage limit. 
3, stop when there are repeated failures/exceptions
'''      


class Session:
    def __init__(self, args) -> None:
        self.args = args
        self.action = args.action
        self.paper_list_path = args.file
        self.search_keywords = args.search_keywords
        self.topic = args.topic
        self.paper_each_round = args.paper_each_round
        self.read = args.read
        self.preset = Preset(args.rountin_config_path)

        openai.api_key = json.load(open(args.apikey))['apikey']
        pass
    
    def run(self, engine, reader):
        action = self.action #['load', 'interactive', 'iterate']

        if action == 'interactive':
            self.interactive_session(engine, reader)
        elif action == 'load':
            paper_list_path = self.paper_list_path
            search_keywords = self.search_keywords
            #print(paper_list_path, search_keywords)
            csv_path = ''.join(['csv/summary']+[w.capitalize() for w in search_keywords.split()]+['.csv'])
            self.summarize_paper_list(engine, reader, paper_list_path, csv_path, search_keywords,read=self.read)
        elif action == 'iterate':
            topic = self.topic
            self.iterative(topic,engine, reader)
            pass
        else:
            raise NotImplementedError(f"Action type {action} is not implemented!")
        
    def interactive_session(self, engine, reader):
        request, choice = self.interactive_session_type()
        if choice == 1:
            question = request
            search_keywords = reader.design_search_keywords(question) 
            search_keywords = re.sub(r"['\"]", "", search_keywords)
            print(f"Suggested keyword:{search_keywords}")
        elif choice == 2:
            question = None
            search_keywords = request
        elif choice == 3:
            pass

        if choice in [1,2]:
            self.search_by_keyword(engine, reader, search_keywords)
        elif choice == 3:
            self.selectAndread_local_papers(engine, reader)
        elif choice == 4:
            pass


    def interactive_session_type(self):
        next_prompt = "Enter 1 to ask a question, 2 to search with a set of keywords, 3 to read a local pdf, 4 to perform a rountine search. \n"
        choice = 0
        while choice == 0:
            entry = input(next_prompt)
            if '1' == entry:
                next_prompt = "Please enter the research question:"
                choice = 1
            elif '2' == entry:
                next_prompt = "Please enter the search keywords:"
                choice = 2
            elif '3' == entry:
                next_prompt = "Press any key to continue:"
                choice = 3
            elif '4' == entry:
                next_prompt = "Press any key to continue:"
                choice = 4
            else:
                next_prompt = "Invalid choice! Please enter 1 or 2"
            
        return input(next_prompt), choice
    
    def search_by_keyword(self, engine, reader, search_keywords):   
        paper_each_round = self.paper_each_round
        searched_round, max_round = 0, 10
        if not os.path.exists("csv"):
            os.mkdir("csv")
        csv_path = ''.join(['csv/abstract']+[w.capitalize() for w in search_keywords.split()]+['.csv'])
        print("Csv path to be saved:",csv_path)

        while searched_round < max_round:
            try:    
                abstract_df, related_df = self.filter_by_abstracts(engine, reader, search_keywords, paper_each_round)
                abstract_df.to_csv(csv_path, index=False)
                break
            except Exception as e:
                print(f"Error getting abstract! {e}")
                searched_round += 1
                
            # Decide if the problem is solved. 
            # If not solved, update search keywords.
            # How to determine if these problems are good?

        return related_df

    def filter_by_abstracts(self, engine, reader, search_keywords, paper_each_round=10):
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
        
        abstract_df = pd.DataFrame(abstracts_dicts, index=[i for i in range(len(abstracts_dicts))])
        abstract_df['related'] = abstract_df['related'].str.lower()      
        related_df = abstract_df.loc[abstract_df['related'].str.contains('yes')]
        related_df.drop(columns=['related'])
        
        return abstract_df, related_df
        
    def selectAndread_local_papers(self, engine, reader, pdf_directory='pdfs'):
        """
        1, go to /pdfs and list all papers.
        2, ask user to pick a paper. 
        3, pass the paper file path to get_pdf_text() and get a list of text
        4, pass the list of text to summarize_paragraph()
        4, delete the read paper from /pdfs
        5, take user choice. If choice = 0, stop, else goto step 1.  
        """
        while True:
            print(f"1. Go to {pdf_directory} and list all papers.")
            print("0. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                papers = os.listdir(pdf_directory)
                for index, paper in enumerate(papers, start=1):
                    print(f"{index}. {paper}")
                    
                while True:           
                    try:
                        paper_choice = input("Pick a paper (enter the corresponding number): ")
                        paper_index = int(paper_choice) - 1
                        break
                    except Exception as e:
                        print(f"Invalid paper choice!")
                        pass
                print(paper_index)

                if 0 <= paper_index < len(papers):
                    selected_paper = papers[paper_index]
                    paper_path = os.path.join(pdf_directory, selected_paper)

                    text = engine.get_pdf_text(paper_path)
                    text_list = engine.split_text(text)
                    print(len(text_list))
                    summarized_text = reader.summarize_paragraph(text_list)

                    os.remove(paper_path)

                    print("Paper summary:")
                    print(summarized_text)
                else:
                    print("Invalid paper choice.")
            elif choice == "0":
                break
            else:
                print("Invalid choice. Please try again.")

    # TODO: make paper_list a df with both title and url. 
    # First try read by title and return extracted bib. If failed, use url.
    def summarize_paper_list(self, engine, reader, paper_list_path, csv_path, search_keywords='', pdf_dirpath='pdfs', chunk_size=1000, read=None):
        '''
            paper_list_path: a pd DataFrame or path to a pd dataframe, each row has a title and a url. 
            readPapers: file path of a pd data frame of all read papers.
        '''
        dfs = []
        if isinstance(paper_list_path, str):
            paper_list = pd.read_csv(paper_list_path)
        elif isinstance(paper_list_path, pd.DataFrame):
            paper_list = paper_list_path
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

    def iterative(self, topic, engine, reader, max_round=2, chunk_size=500, pdf_dirpath='pdfs'):
        used_keywords = []
        used_urls = set()
        read_urls = set()
        print(topic)
        for i in range(max_round):
            keywords = reader.design_search_keywords(topic, used_keywords)
            print(i, keywords)
            abstracts, urls, bibs = engine.get_top_abstracts(keywords)
            full_papers_to_read = []
            for abstract, url, bib in zip(abstracts, urls, bibs):
                #print(url, bib, abstract)
                if url in used_urls:
                    continue
                used_urls.add(url)
                abstract_response = reader.read_abstract(abstract, keywords)
                #print(abstract_response)
                if 'yes' not in abstract_response['related'].lower():
                    continue
                full_papers_to_read.append({'url':url, 'bib':bib})

        print(len(full_papers_to_read))
        used_keywords.append(keywords)

        for paper in full_papers_to_read:
            url, bib = paper['url'], paper['bib']
            if url in read_urls:
                continue
            else:
                read_urls.add(url)
                print(f"Downloading from {url}")
                pdf_path = engine.download_pdf(url,pdf_dirpath)
                try:
                    chunk = engine.split_pdf(pdf_path,chunk_size)
                    summary = reader.summarize_paper(chunk, keywords)
                except Exception as e:
                    print(f"Exception {e} when loading: {url}")
                    # Fill in empty, ensure output and paper_list have the same row number.
                    summary = {}
                    for col in reader.new_col_names:
                        summary[col] = ''
                    summary = pd.DataFrame(summary, index=[i])

        summary.to_csv("csv/summary.csv",index=False)

    def rountine_check(self, engine, reader, search_keywords):
        '''
            This function completes a rountine section:
            for every preset topic:
                1, find relevant papers based on a given keyword. 
                2, for papers that have not been checked before, generated a detailed report
                3, for past papers that were recorded as important, check relevant papers in the papers cited them
                4, add all papers just checked to a preset file.
            Finally check all papers in /pdfs.
        '''
        # First check any changes in precheck
        self.preset.change_preset()

        # Go over every preset keywords
        for keyword in self.preset.get_keywords():
            related_df = self.search_by_keyword(engine, reader, keyword)
        
        

    



