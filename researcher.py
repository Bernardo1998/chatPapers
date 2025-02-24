import re
from typing import Tuple, Optional
from pydantic import BaseModel
from client import OllamaClient
from topic_database import TopicDatabase

class PaperAnalysis(BaseModel):
    """Structured output for paper analysis"""
    journal_conference: str
    year: int
    title: str
    url: Optional[str]
    main_topic: str
    keywords: list[str]
    methodology_innovation: str
    dataset: str
    evaluation_metrics: list[str]
    summary: str
    pros: list[str]
    cons: list[str]

class TopicConnection(BaseModel):
    """Structured output for connecting paper to topic"""
    key_problem: str
    related_paper: str = ""  # Empty if no closely related paper found
    method_comparison: str = ""  # Empty if no related paper
    topic_advancement: str
    important: bool  # Whether the paper deserves detailed manual reading

class InferredTitle(BaseModel):
    """Structured output for title inference"""
    title: str

class Researcher:
    def __init__(self, client: OllamaClient):
        """Initialize with an Ollama client"""
        self.client = client

    def extract_sections(self, text: str) -> Tuple[str, str]:
        """
        Extract abstract and introduction from paper text.
        
        Args:
            text (str): Full paper text
            
        Returns:
            Tuple[str, str]: (abstract, introduction)
        """
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Try to find abstract
        abstract_match = re.search(
            r'abstract\s*\n(.*?)(?=\n\s*(?:introduction|1\.|\d\.|keywords))',
            text_lower,
            re.DOTALL
        )
        
        # Try to find introduction
        intro_match = re.search(
            r'(?:introduction|1\.introduction)\s*\n(.*?)(?=\n\s*(?:2\.|background|related work))',
            text_lower,
            re.DOTALL
        )
        
        # Extract matched sections from original text to preserve case
        if abstract_match:
            abstract = text[abstract_match.start(1):abstract_match.end(1)].strip()
        else:
            # Take first 1000 characters if abstract not found
            abstract = text[:2000].strip()
            
        if intro_match:
            introduction = text[intro_match.start(1):intro_match.end(1)].strip()
        else:
            # Take next 5000 characters if introduction not found
            introduction = text[2000:7000].strip()
            
        return abstract, introduction

    def analyze_paper(self, text: str, topic_db: TopicDatabase) -> PaperAnalysis:
        """
        Analyze paper text and generate structured summary.
        
        Args:
            text (str): Full paper text
            topic_db (TopicDatabase): Database of known research topics
            
        Returns:
            PaperAnalysis: Structured analysis of the paper
        """
        # Extract abstract and introduction
        abstract, intro = self.extract_sections(text)
        
        # Get available topics
        available_topics = list(topic_db.list_topics().keys())
        topics_str = "\n".join(f"- {topic}" for topic in available_topics)
        
        # Create prompt for the model
        prompt = f"""Analyze the following paper abstract and introduction to extract key information.
        Please provide a structured analysis including publication details, methodology, and critical evaluation.

        ABSTRACT:
        {abstract}

        INTRODUCTION:
        {intro}

        Available research topics (choose ONE that best matches, or leave blank if none match):
        {topics_str}

        Please analyze the text and provide the following information in a structured format:
        - Journal/Conference where it was published
        - Year of publication
        - Paper title
        - URL or DOI if present
        - Main research topic (must be one from the list above, or blank if none match)
        - Key technical keywords (3-5)
        - Main methodological innovation
        - Datasets used in the paper
        - Evaluation metrics
        - Brief summary of the core message of the paper (2-3 sentences)
        - Key strengths/pros of the method (2-3 points)
        - Limitations/cons of the method (2-3 points)

        Note: For the main research topic, only use exactly one of the provided topics, or leave it blank if none are suitable.
        """
        
        # Get structured response from the model
        try:
            analysis = self.client.get_structured_response(
                prompt=prompt,
                output_model=PaperAnalysis
            )
            
            # Validate that the main topic is from the available topics
            if analysis.main_topic and analysis.main_topic not in available_topics:
                analysis.main_topic = ""  # Clear invalid topic
                
            return analysis
            
        except Exception as e:
            print(f"Error analyzing paper: {str(e)}")
            raise

    def connect_summary_to_topic(self, analysis: PaperAnalysis, topic_db: TopicDatabase) -> Optional[TopicConnection]:
        """
        Connect paper analysis to its research topic and analyze relationships.
        
        Args:
            analysis (PaperAnalysis): Structured analysis of the paper
            topic_db (TopicDatabase): Database of research topics
            
        Returns:
            Optional[TopicConnection]: Connection analysis if topic found, None otherwise
        """
        # Verify topic exists
        topic_info = topic_db.search_topic(analysis.main_topic)
        if not topic_info:
            return None
            
        # Process important papers list
        important_papers = topic_info.get('important_papers', [])
        if important_papers and isinstance(important_papers[0], dict):
            # If papers are dictionaries with title and summary
            important_papers_str = '\n'.join(
                f"- {paper['title']}: {paper.get('summary', 'No summary available')}"
                for paper in important_papers
            )
            important_titles = [paper['title'] for paper in important_papers]
        else:
            # If papers are just strings
            important_papers_str = '\n'.join(f"- {paper}" for paper in important_papers)
            important_titles = important_papers

        prompt = f"""Analyze how this paper connects to its research topic.

        PAPER ANALYSIS:
        Title: {analysis.title}
        Summary: {analysis.summary}
        Methodology: {analysis.methodology_innovation}
        Dataset: {analysis.dataset}
        Metrics: {', '.join(analysis.evaluation_metrics)}
        Pros: {', '.join(analysis.pros)}
        Cons: {', '.join(analysis.cons)}

        TOPIC INFORMATION:
        Topic: {analysis.main_topic}
        Description: {topic_info.get('description', '')}
        Current Status: {topic_info.get('current_status', '')}
        Important Papers:
        {important_papers_str}
        Key Challenges to address: {",".join(topic_info.get('key_challenges', []))}

        Please analyze the connection between this paper and the research topic by answering these questions:

        1. What is the key problem or challenge this paper claims to address?

        2. Among the topic's important papers ({', '.join(important_titles)}), 
        which ONE is most closely related to this paper's method? If none are closely related, leave blank.

        3. If a related paper was identified, how does this paper's method relate to or differ from that paper's approach?
        If no related paper, leave this blank.

        4. How does this paper help advance the research topic and address any challenges listed in the current status?
        Consider the topic's current status: {topic_info.get('current_status', '')} and key challenges: {",".join(topic_info.get('key_challenges', []))}

        5. Should this paper be read in detail? Consider:
        - Does the method show substantial novelty in method or fundamentally better performance (not just incremental improvement)?
        - Does it explore a novel or understudied topic/intersection?
        - Is the study extensive and methodologically sound?
        Answer with true only if the paper meets multiple criteria above and appears particularly significant.

        Please provide a structured response with these exact fields:
        - key_problem: The main problem addressed
        - related_paper: The most related important paper (or blank if none)
        - method_comparison: Comparison with related paper (or blank if none)
        - topic_advancement: How it advances the topic and addresses challenges
        - important: true/false indicating if detailed reading is recommended
        """
        
        try:
            connection = self.client.get_structured_response(
                prompt=prompt,
                output_model=TopicConnection
            )
            return connection
            
        except Exception as e:
            print(f"Error analyzing topic connection: {str(e)}")
            raise

    def infer_title(self, text: str, char_limit: int = 500) -> Optional[str]:
        """
        Infer the paper title from the beginning of the text.
        
        Args:
            text (str): Full paper text
            char_limit (int): Number of initial characters to consider
            
        Returns:
            Optional[str]: Inferred title, or None if inference fails
        """
        if not text:
            return None
            
        # Take initial portion of text
        text_sample = text[:char_limit].strip()
        
        prompt = f"""Given the beginning of an academic paper, identify its title.
        Return only the main title (no subtitle).
        If multiple possible titles are found, return the most likely one.
        
        Paper beginning:
        {text_sample}
        
        Please provide the title in this exact format:
        - title: The inferred paper title
        """
        
        try:
            result = self.client.get_structured_response(
                prompt=prompt,
                output_model=InferredTitle
            )
            return result.title
            
        except Exception as e:
            print(f"Error inferring title: {str(e)}")
            return None

if __name__ == "__main__":
    # Example usage
    client = OllamaClient(model='llama3.1')
    researcher = Researcher(client)
    topic_db = TopicDatabase()
    
    # Test with a sample paper
    sample_text = """
    Title: A Novel Approach to Deep Learning
        
    Abstract
    This paper presents a novel approach to deep learning...
    
    1. Introduction
    Deep learning has revolutionized many areas of computer science...
    """
    
    # Test full analysis
    analysis = researcher.analyze_paper(sample_text, topic_db)
    print("\nAnalysis:", analysis)
    
    # Test topic connection
    if analysis.main_topic:
        connection = researcher.connect_summary_to_topic(analysis, topic_db)
        if connection:
            print("\nTopic Connection:")
            print(f"Key Problem: {connection.key_problem}")
            print(f"Related Paper: {connection.related_paper}")
            print(f"Method Comparison: {connection.method_comparison}")
            print(f"Topic Advancement: {connection.topic_advancement}")

    # Test title inference
    sample_text = """
    Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing, pages 1556–1572
    November 12-16, 2024 ©2024 Association for Computational Linguistics
    Watch Every Step! LLM Agent Learning via Iterative Step-Level Process Refinement
    Weimin Xiong1, Yifan Song1, Xiutian Zhao2, Wenhao Wu1, Xun Wang1
    Ke Wang3, Cheng Li3, Wei Peng3, Sujian Li1*
    1National Key Laboratory for Multimedia Information Processing,
    School of Computer Science, Peking University
    2University of Edinburgh
    3H...
    """
    
    title = researcher.infer_title(sample_text)
    print(f"Inferred title: {title}")
