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

class ChatPaper:
    def __init__(self,model="gpt-3.5-turbo"):
        # Global tracker for usage in this session
        self.total_token = 0
        self.model = model
        # Define prompts globally
        # Move format requirement closer to the end?
        self.context = "First read a chunk of research paper: {chunk}. Now answer the following questions: 1.What is the problem it solves, 2.What is the method it proposed(focus on the model structure and technical improvement), 3.how is it different from prior methods, 4.what is the dataset tested, 5.do you think this is a part of the main text (just say yes or no). Your answers must be returned in JSON format. For each question, the key you use in the return JSON is the question number and values are your answers. Limit your answer for each question to 1 sentence. If you cannot find answer to a question, your answer should be an empty string."
        self.question_texts = ["What is the problem the paper addresses", "What is the method the paper  proposed(include network, necessary math equations)", "how is the paper`s method different from prior methods", "what is the dataset tested in the paper"]
        self.new_col_names = ['problem','method', 'difference', 'dataset']
        self.review_context = "You read a paper and were given the question:{question_text}. Your prior response is: {prior_responses}. Rewrite your reponse in at most 2 sentences to make it coherent."
        self.abstract_context = "Read the following writing which includes a research paper abstract: {abstract}. Now answer the following questions: 1.What problem does the paper solves? 2.Is it closely related to {search_keywords}(just say yes or no)? Your answers must be returned in JSON format. For each question, the key you use in the return JSON is the question number and values are your answers."
        self.chunk_ending_question = '5'
        self.keywords_context = 'My research question is: {question}. Design the most relevant google scholar search keyword for me. Return your answer a phrase or keywords separated by space.'
        self.abstract_info_keys = {'1': 'summary', '2': 'related'}
        
    def get_reply(self, prompt):
        messages = [ {"role": "user", "content":prompt} ]
        chat = openai.ChatCompletion.create(
                model=self.model, messages=messages,
                temperature = 0
        )
        reply = chat.choices[0].message.content
        self.total_token += chat.usage.total_tokens
        return reply
        
    def traverse_paper(self, chunk, stop_after_page=None):
        responses = []
        keys = [str(i) for i in range(5)]
        for i,t in tqdm(enumerate(chunk)):
            context_this_t = self.context.replace('{chunk}', t)
            reply = self.get_reply(context_this_t)
            #print(reply)
            response_this_chunk = eval(reply)
            responses.append(response_this_chunk)
            if stop_after_page is not None and (i+1) >= stop_after_page:
            	break
            # Terminate if GPT believes the main text has ended, to save token.
            if 'no' in response_this_chunk[self.chunk_ending_question].lower():
                #print("Break automatically!")
                break

        response_df = pd.DataFrame(responses)
        
        return response_df
 
    def summarize_paper(self, chunk, search_keywords=None):
        response_df = self.traverse_paper(chunk)
        revised_answer = {}
        
        # Notice that summary mode does not check whether paper is related.
        for i in range(len(self.question_texts)):
            question_text = self.question_texts[i]
            prior_responses = ' '.join(response_df.iloc[:,i])
            review_context = self.review_context.replace("{question_text}",question_text)
            review_context = review_context.replace("{prior_responses}",prior_responses)
            reply = self.get_reply(review_context)
            revised_answer[self.new_col_names[i]] = reply
   
        response_df = pd.DataFrame([revised_answer])
        
        return response_df
    
    def read_abstract(self, abstract,search_keywords):
        '''
            The abstract returned by scholarly is not clear. 
            For now just consider chunk 1 as abstract.
        '''
        abstract_context = self.abstract_context.replace("{abstract}", abstract)
        abstract_context = abstract_context.replace("{search_keywords}", search_keywords)
        #print(abstract_context+'\n')
        reply = eval(self.get_reply(abstract_context))
        return {self.abstract_info_keys.get(k, k): v for k, v in reply.items()}
        
    def design_search_keywords(self, question):
        keywords_context = self.keywords_context.replace('{question}', question)
        return self.get_reply(keywords_context)
        
    def refine_search_keywords(self, question, keywords):
    	pass
    	
