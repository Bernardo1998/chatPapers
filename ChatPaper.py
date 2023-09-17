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
import pyperclip

'''
(done)0, given a list of things to look for: methods, problem to solve, comparison, dataset, relevant cites... Make a pd dataframe to save it.
(done)1, read 1000 words each time
(done)2, if any thing relevant found, add to cell in a df
3, for other things, write a small summary, append to the end.
(done)4, after entire paper read, revisit all recorded cell and summary, modify anything that does not seem right. 
5, for any relevant paper, add to the end of paper list to read. Maybe too hard?
6, save a log of papers read in a pd df

'''

class ChatPaper:
    def __init__(self,model="gpt-3.5-turbo",print_prompt=True):
        # Global tracker for usage in this session
        self.total_token = 0
        self.model = model
        # Define prompts globally
        # Move format requirement closer to the end?
        
        self.question_texts = ["What is the problem the paper addresses", "What is the method the paper  proposed(include network, necessary math equations)", "how is the paper`s method different from prior methods", "what is the dataset tested in the paper"]
        self.new_col_names = ['problem','method', 'difference', 'dataset']
        self.review_context = "You read a paper and were given the question:{question_text}. Your prior response is: {prior_responses}. Rewrite your reponse in at most 2 sentences to make it coherent."
        self.abstract_context = "Read the following writing which includes a research paper abstract: {abstract}. Now answer the following questions: 1.What problem does the paper solves? 2.Is it closely related to {search_keywords}(just say yes or no)? Your answers must be returned in JSON format. For each question, the key you use in the return JSON is the question number and values are your answers."
        self.chunk_ending_question = '5'
        self.keywords_context = 'I want to find answer for the following research question seperated by triple backticks: ```{question}```. Suggest the most relevant google scholar search keyword for this question. Your answer should not be the same as any used keywords in the following list seperated by triple backticks: ```{used_keywords}``` Return your answer a phrase or keywords separated by space and do not use quotes.'
        self.abstract_info_keys = {'1': 'summary', '2': 'related'}
        self.print_prompt = print_prompt # Whether to print the filled promplt
        
    def get_reply(self, prompt):
        messages = [ {"role": "user", "content":prompt} ]
        chat = openai.ChatCompletion.create(
                model=self.model, messages=messages,
                temperature = 0
        )
        reply = chat.choices[0].message.content
        self.total_token += chat.usage.total_tokens
        return reply

    def summarize_paragraph(self, text_chunks):
      """
      This function is based on Chi-hua`s prompt.
      """
      print("Start summarizing!")

      for text_chunk in text_chunks:
        prompt = f"""
                  I am reading research papers and writing summary for each paragraph came from research
                  paper. Here are the requirements for the article format, expression style, and
                  form. Please understand them carefully:

                  - Article Format: The summary must be divided into three key points. The title
                  should be concise, and the content should be presented in short paragraphs. Each
                  key point should start with a bold title to make it easy for readers to read and
                  understand.
                  - Expression Style: The article should be clear and easy to understand, using
                  concise and appropriate language. It should reflect the author's personal
                  emotions, balancing objectivity and subjectivity to resonate with readers and
                  spark their interest. The article should be concise, eliminating unnecessary
                  embellishments.
                  - Form: The article should be presented in short paragraphs, with compact content
                  conveying the author's insights and experiences. The wording should be clear and
                  concise, and the writing style should be engaging and natural, maintaining depth
                  and thoughtfulness. 

                  The short summary should use bold text to highlight the following information if found in the paragraph:
                  1, What problem does the paper address? 
                  2, What method/network does it use or surveyed?
                  3, What are the existing methods/papers? List their titles.
                  4, How is the proposed method related to the prior papers?
                  5, How does it differ from prior methods? What is it`s key advantage?
                  6, How much improvement has it achieved? 
                  7, What evaluation metrics/dataset was used?
                  8, What problem did it fail to solve? What does it need to improve

                  Please read the paragraph separated by triple backticks below carefully and rewrite them
                  into a short summary that fulfills the format requirements mentioned above. 

                  ```
                  {text_chunk}
                  ```
                  """
        print(prompt)
        pyperclip.copy(prompt)
        _ = input("The prompt above has been added to your clipboard. Please paste it to GPT, then press enter to continue.")
        
    def traverse_paper(self, chunk, stop_after_page=None):
        responses = []
        keys = [str(i) for i in range(5)]
        prompt = f"First read a chunk of research paper: {chunk}. Now answer the following questions: 1.What is the problem it solves, 2.What is the method it proposed(focus on the model structure, exact content of input/output and technical improvement), 3.how is it different from prior methods, 4.what is the dataset tested, 5.is this a part of the main text and not reference/appendix section(just say yes or no). Your answers must be returned in JSON format. For each question, the key you use in the return JSON is the question number and values are your answers. If you cannot find answer to a question, your answer for it should be an empty string."
        for i,t in tqdm(enumerate(chunk)):
            context_this_t = prompt
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
 
    def summarize_paper(self, chunk, search_keywords=None, review_option="simple"):
        response_df = self.traverse_paper(chunk)
        revised_answer = {}
        
        # Notice that summary mode does not check whether paper is related.
        for i in range(len(self.question_texts)):
            question_text = self.question_texts[i]
            prior_responses = ' '.join(response_df.iloc[:,i])
            if review_option == 'simple':
             review_context = f"You read a paper and were given the question:{question_text}. Your prior response is: {prior_responses}. Rewrite your reponse in at most 2 sentences to make it coherent."
            elif review_option == 'detail':
             review_context = f"You read a paper and were given the question:{question_text}. Your prior response is: {prior_responses}. Rewrite your reponse in at most 2 sentences to make it coherent."              
            reply = self.get_reply(review_context)
            revised_answer[self.new_col_names[i]] = reply
   
        response_df = pd.DataFrame([revised_answer])
        
        return response_df
        
    def read_abstract(self, abstract,search_keywords):
        '''
            This function reads on abstract from a paper, summarize it and  if it is relevant to the search_keywords.
        '''
        #abstract_context = self.abstract_context.replace("{abstract}", abstract)
        #abstract_context = abstract_context.replace("{search_keywords}", search_decidekeywords)
        abstract_context = f"Read the following writing seperated by triple backticks which includes a research paper abstract : ```{abstract}```. Now answer the following questions: 1.What problem does the paper solves? 2.Is it closely related to the following search keywords seperated by triple backticks: ```{search_keywords}```?(Your answer must only contain yes or no) Your answers must be returned in JSON format. For each question, the key you use in the return JSON is the question number and values are your answers."
        #print(abstract_context+'\n')
        reply = eval(self.get_reply(abstract_context))
        return {self.abstract_info_keys.get(k, k): v for k, v in reply.items()}
        
    def design_search_keywords(self, question, used_keywords=[]):
        keywords_context = f'I want to find answer for the following research question seperated by triple backticks: ```{question}```. Suggest the most relevant google scholar search keyword for this question. Your answer should not be the same as any used keywords in the following list seperated by triple backticks: ```{used_keywords}``` Return your answer a phrase or keywords separated by space and do not use quotes.'
        #keywords_context = self.keywords_context.replace('{question}', question, used_keywords)
        return self.get_reply(keywords_context)
    
    def infer_title(self, abstract):
        title_context = f'Read the following part of a research paper separated by triple backticks and identify its title: ```{abstract}```. Your response should only contain the extracted title'
        return self.get_reply(title_context)
        
    def refine_search_keywords(self, question, keywords):
    	pass
    	
