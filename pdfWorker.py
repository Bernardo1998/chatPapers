import os
from pathlib import Path
from typing import Dict, Optional
import fitz  # PyMuPDF

class PDFWorker:
    def __init__(self):
        """Initialize the PDF worker."""
        pass

    def extract_title_from_text(self, text: str) -> Optional[str]:
        """
        Extract the title from PDF text content.
        Looks for the title in the first few lines of text,
        typically before any abstract or content.
        
        Args:
            text (str): The extracted text from PDF
            
        Returns:
            str: Extracted title if found
            None: If title couldn't be extracted
        """
        if not text:
            return None
            
        # Split into lines and get first few non-empty lines
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line][:5]  # Look at first 5 non-empty lines
        
        # Usually the title is the first substantial line
        # before words like "Abstract", "Introduction", etc.
        for line in lines:
            # Skip lines that are likely not titles
            if any(word in line.lower() for word in ['abstract', 'introduction', 'arxiv']):
                continue
            # Skip very short lines or lines with typical header information
            if len(line) < 10 or '@' in line or 'http' in line:
                continue
            # Skip lines that are likely author lists (multiple commas)
            if line.count(',') > 2:
                continue
                
            return line.strip()
            
        return None

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from a single PDF file, ignoring figures and images.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text from the PDF
            None: If file doesn't exist or extraction fails
        """
        try:
            if not os.path.exists(pdf_path):
                print(f"File not found: {pdf_path}")
                return None

            doc = fitz.open(pdf_path)
            text = ""
            
            for page in doc:
                # Extract text while ignoring images
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return None

    def load_pdfs_from_folder(self, folder_path: str) -> Dict[str, str]:
        """
        Load all PDFs from a folder and extract their text.
        
        Args:
            folder_path (str): Path to the folder containing PDFs
            
        Returns:
            Dict[str, str]: Dictionary with filename as key and extracted text as value
        """
        pdf_texts = {}
        folder = Path(folder_path)
        
        if not folder.exists() or not folder.is_dir():
            print(f"Invalid folder path: {folder_path}")
            return pdf_texts

        # Process all PDF files in the folder
        for pdf_file in folder.glob("*.pdf"):
            text = self.extract_text_from_pdf(str(pdf_file))
            if text:
                # Use the filename without extension as the key
                key = pdf_file.stem
                pdf_texts[key] = text

        return pdf_texts


if __name__ == "__main__":
    # Example usage
    worker = PDFWorker()
    
    # Example 1: Process single PDF
    single_pdf_path = "2411.11195v2.pdf"
    text = worker.extract_text_from_pdf(single_pdf_path)
    if text:
        title = worker.extract_title_from_text(text)
        print(f"Title: {title}")
        print(f"First 2000 characters: {text[:2000]}...")
    
    # Example 2: Process folder of PDFs
    folder_path = "pdfs_folder"
    pdf_texts = worker.load_pdfs_from_folder(folder_path)
    print(f"\nProcessed {len(pdf_texts)} PDF files from folder")
    for filename, text in pdf_texts.items():
        title = worker.extract_title_from_text(text)
        print(f"- {filename}: {title}")
