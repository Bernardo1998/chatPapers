import argparse
from ChatPaper import ChatPaper
from ScholarlySearch import ScholarlySearch
from Sessions import Session

def main():
    parser = argparse.ArgumentParser(description='Description of your script')

    parser.add_argument('--action', type=str, help='Action to take in this session.', default='load')
    parser.add_argument('-f', '--file', type=str, help='Input df path with papers to read.', default='paper_lists/paper_list.csv')
    parser.add_argument('-plc', '--paperListColumn', type=str, help='Column name of the paper list', default='url')
    parser.add_argument('-ft', '--fileType', type=str, help='Paper list type, url or title', default='url')
    parser.add_argument('-s', '--search_keywords', type=str, help='Search keywords', default='')
    parser.add_argument('--topic', type=str, help='A search topic or a question.', default='')
    parser.add_argument('--sep', type=str, help='Separator', default='\t')
    parser.add_argument('--read', type=str, help='file of read papers', default='readPapers.csv')
    parser.add_argument('--pdf_dirpath', type=str, help='dir to save pdfs', default='pdfs')
    parser.add_argument('--chunk_size', type=int, help='max words in a chunk', default=1000)
    parser.add_argument('--paper_each_round', type=int, help='papers to be searched in each query', default=15)
    parser.add_argument('--model', type=str, help='name of the model', default='gpt-3.5-turbo')
    parser.add_argument('--apikey', type=str, help='path to the openai api key', default="configs/default.json") # rountine_config
    parser.add_argument('--rountine_config', type=str, help='path to records of rountine checking', default="configs/routine_config.json")
    
    args = parser.parse_args()

    engine = ScholarlySearch()
    reader = ChatPaper(model=args.model)
    print("Init!")
    session = Session(args)
            
    session.run(engine, reader)

    print("total_token:",reader.total_token)
       
if __name__ == "__main__" :    
    main()