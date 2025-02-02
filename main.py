from client import OllamaClient
from pydantic import BaseModel
import argparse
from database import PaperDatabase
from topic_database import TopicDatabase
from pdfWorker import PDFWorker
from typing import Dict, List
from researcher import Researcher, PaperAnalysis, TopicConnection
from datetime import datetime
import pandas as pd
import traceback
import os
from IPython.display import clear_output

class PaperSummary(BaseModel):
    title: str
    abstract: str
    summary: str
    topics: list[str]
    importance_score: int  # 1-5
    key_paper_relations: dict[str, str]  # paper_title: relation_description

def parse_args():
    parser = argparse.ArgumentParser(description='Paper Processing with Ollama')
    parser.add_argument(
        '--model',
        type=str,
        default='llama3.1',
        help='Name of the Ollama model to use (default: llama3.1)'
    )
    return parser.parse_args()

def load_databases():
    """Initialize and load both paper and topic databases."""
    paper_db = PaperDatabase("papers.json")
    topic_db = TopicDatabase("topics.json")
    return paper_db, topic_db

def process_papers(folder_path: str, paper_db: PaperDatabase, topic_db: TopicDatabase, researcher: Researcher) -> Dict[str, str]:
    """
    Process papers from a folder and filter out already processed ones.
    
    Args:
        folder_path (str): Path to folder containing PDFs
        paper_db (PaperDatabase): Database of processed papers
        topic_db (TopicDatabase): Database of research topics
        researcher (Researcher): Researcher instance for paper analysis
    """
    # Initialize PDF worker
    pdf_worker = PDFWorker()
    
    # Keep track of all analyses and connections
    all_analyses: List[dict] = []
    all_connections: List[dict] = []
    
    # Load all PDFs from folder
    pdf_texts = pdf_worker.load_pdfs_from_folder(folder_path)
    
    # Process each paper
    for filename, text in pdf_texts.items():
        # Extract title
        title = researcher.infer_title(text)
        if not title:
            print(f"Warning: Could not extract title from {filename}, skipping...")
            continue
            
        # Check if paper exists in database
        if paper_db.search_paper(title):
            print(f"Skipping '{title}' - already processed")
            continue
            
        print(f"Found new paper: '{title}'")
        
        try:
            # Analyze the paper
            print(f"Analyzing paper: '{title}'...")
            analysis = researcher.analyze_paper(text, topic_db)
            print(f"Analysis complete. Main topic: {analysis.main_topic}")
            
            # Store analysis
            analysis_dict = analysis.model_dump()
            analysis_dict["filename"] = filename
            all_analyses.append(analysis_dict)
            
            # If paper has a main topic, analyze topic connection
            topic_connection = None
            if analysis.main_topic:
                print(f"Analyzing topic connection...")
                topic_connection = researcher.connect_summary_to_topic(analysis, topic_db)
                if topic_connection:
                    print(f"Found connection to topic: {analysis.main_topic}")
                    print(f"Related paper: {topic_connection.related_paper}")
                    
                    # Store connection
                    connection_dict = topic_connection.model_dump()
                    connection_dict["filename"] = filename
                    connection_dict["title"] = title
                    all_connections.append(connection_dict)
            
            # Store results in paper database
            paper_info = {
                "title": title,
                # Flatten analysis fields
                **analysis.model_dump(),
                # Flatten topic connection fields if available
                **(topic_connection.model_dump() if topic_connection else {
                    "key_problem": "",
                    "related_paper": "",
                    "method_comparison": "",
                    "topic_advancement": "",
                    "important": False
                })
            }
            paper_db.insert_paper(title, paper_info)
            print(f"Stored paper information in database")
            if paper_info["important"]:
                print(f"*** This paper is marked as important for detailed reading ***")
            
        except Exception as e:
            print(f"Error processing paper '{title}':")
            print(f"Error message: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            continue
    
    # Create output directories if they don't exist
    os.makedirs("summary_output", exist_ok=True)
    os.makedirs("topic_analysis", exist_ok=True)
    
    # Save results to CSV files if any new papers were processed
    if all_analyses or all_connections:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if all_analyses:
            analysis_df = pd.DataFrame(all_analyses)
            analysis_file = f"summary_output/paper_analyses_{timestamp}.csv"
            analysis_df.to_csv(analysis_file, index=False)
            print(f"\nSaved {len(all_analyses)} paper analyses to {analysis_file}")
            
        if all_connections:
            connections_df = pd.DataFrame(all_connections)
            connections_file = f"topic_analysis/topic_connections_{timestamp}.csv"
            connections_df.to_csv(connections_file, index=False)
            print(f"Saved {len(all_connections)} topic connections to {connections_file}")
            
        return connections_df if all_connections else None

def display_important_papers(connections_df: pd.DataFrame):
    """Display important papers interactively"""
    if connections_df is None or connections_df.empty:
        print("No paper connections to display.")
        return
        
    important_papers = connections_df[connections_df['important'] == True]
    if important_papers.empty:
        print("No papers marked as important for detailed reading.")
        return
        
    print(f"\nFound {len(important_papers)} important papers to review:")
    
    for idx, paper in important_papers.iterrows():
        clear_output(wait=True)
        print(f"\nImportant Paper {idx + 1}/{len(important_papers)}")
        print("=" * 80)
        print(f"Title: {paper['title']}")
        print(f"Topic: {paper.get('main_topic', 'N/A')}")
        print("-" * 80)
        print("Key Problem:")
        print(paper['key_problem'])
        print("\nRelated Important Paper:")
        print(paper['related_paper'] if paper['related_paper'] else "None found")
        if paper['method_comparison']:
            print("\nComparison with Related Work:")
            print(paper['method_comparison'])
        print("\nTopic Advancement:")
        print(paper['topic_advancement'])
        print("=" * 80)
        input("\nPress Enter to continue...")

def main():
    args = parse_args()
    
    # 1. Initialize the Ollama client with configured model
    client = OllamaClient(model=args.model)
    
    # 2. Load paper and topic databases
    paper_db, topic_db = load_databases()
    
    # 3. Initialize researcher
    researcher = Researcher(client)
    
    # 4. Process papers from input folder
    input_folder = "pdfs_folder"  # You might want to make this configurable via args
    connections_df = process_papers(input_folder, paper_db, topic_db, researcher)
    
    # 5. Save final state of databases
    print("\nSaving databases...")
    paper_db.save()
    topic_db.save()
    print("Databases saved successfully")
    
    # 6. Interactive review of important papers
    if connections_df is not None:
        print("\nStarting interactive review of important papers...")
        display_important_papers(connections_df)
    
    return client, paper_db, topic_db

if __name__ == "__main__":
    client, paper_db, topic_db = main()

# 1, init the ollama client

# 2, load database of the read papers and metadata. Create a database if not exists.
# 2.1 load the database on topics, the key papers under each topic and their brief summary.

# 4, for each pdf in a given folder, 
# 4.0, load the input pdf, filter checked ones based on title comparison with database. Skip if exists in database and print a message.
# 4.1, extract the abstract and intro(assume to be the first 2000 characters).
# 4.2, use ollama to generate the summary of the paper
# 4.3, based on the summary, use ollama to determine if the paper is related to one of the topics.
# 4.4, if related, compare the summary with the key papers (summary), summarize how the papers are related to the key papers, or it is a new direction/topic.
# 4.5, based on summary, determine if the papers is an important paper for me to read in depth. 
# 4.6, save the paper summary to database.
# 4.7, (optional) output file that connects to obsidian database.
