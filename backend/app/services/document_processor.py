"""
Document processing service for knowledge base ingestion.
Supports PDF, CSV, and text document processing.
"""
import os
import re
from typing import List, Dict, Optional
from pathlib import Path

# PDF processing
PDF_AVAILABLE = False
try:
    import PyPDF2
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    pass

# CSV processing
CSV_AVAILABLE = False
try:
    import pandas as pd
    CSV_AVAILABLE = True
except ImportError:
    pass

# Document processing
DOCX_AVAILABLE = False
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    pass


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks for embedding.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind('\n', start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


def extract_metadata_from_filename(filename: str) -> Dict[str, str]:
    """
    Extract metadata (title, category, tags) from filename.
    
    Args:
        filename: File name
    
    Returns:
        Dictionary with metadata
    """
    # Remove extension
    name = Path(filename).stem
    
    # Try to extract category from path or filename
    category = "General"
    tags = []
    
    # Check for category in path
    path_parts = Path(filename).parts
    if len(path_parts) > 1:
        category = path_parts[-2].title()
    
    # Extract tags from filename (e.g., "product-guide_v2_final.pdf")
    parts = re.split(r'[_\-\s]+', name)
    if len(parts) > 1:
        tags = [p.lower() for p in parts[1:] if len(p) > 2]
    
    return {
        "title": name.replace('_', ' ').replace('-', ' ').title(),
        "category": category,
        "tags": ",".join(tags) if tags else ""
    }


def process_pdf(file_path: str) -> List[Dict[str, str]]:
    """
    Process PDF file and extract text.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        List of dictionaries with title, content, category, tags
    """
    if not PDF_AVAILABLE:
        raise Exception("PDF processing not available. Install PyPDF2 or pypdf.")
    
    articles = []
    metadata = extract_metadata_from_filename(file_path)
    
    try:
        # Try pypdf first (newer)
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except:
            # Fallback to PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        
        # Chunk the text
        chunks = chunk_text(text)
        
        # Create articles from chunks
        for i, chunk in enumerate(chunks):
            title = f"{metadata['title']} - Part {i+1}" if len(chunks) > 1 else metadata['title']
            articles.append({
                "title": title,
                "content": chunk,
                "category": metadata["category"],
                "tags": metadata["tags"]
            })
    
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")
    
    return articles


def process_csv(file_path: str, title_column: Optional[str] = None, content_columns: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """
    Process CSV file and convert rows to knowledge base articles.
    
    Args:
        file_path: Path to CSV file
        title_column: Column to use as title (default: first column)
        content_columns: Columns to include in content (default: all columns)
    
    Returns:
        List of dictionaries with title, content, category, tags
    """
    if not CSV_AVAILABLE:
        raise Exception("CSV processing not available. Install pandas.")
    
    articles = []
    metadata = extract_metadata_from_filename(file_path)
    
    try:
        df = pd.read_csv(file_path)
        
        # Determine title column
        if not title_column:
            title_column = df.columns[0]
        
        # Determine content columns
        if not content_columns:
            content_columns = [col for col in df.columns if col != title_column]
        
        # Process each row
        for idx, row in df.iterrows():
            title = str(row[title_column]) if title_column in row else f"Row {idx+1}"
            
            # Build content from selected columns
            content_parts = []
            for col in content_columns:
                if col in row and pd.notna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            content = "\n".join(content_parts)
            
            if content:
                articles.append({
                    "title": title,
                    "content": content,
                    "category": metadata["category"],
                    "tags": metadata["tags"]
                })
    
    except Exception as e:
        raise Exception(f"Error processing CSV: {e}")
    
    return articles


def process_text_file(file_path: str) -> List[Dict[str, str]]:
    """
    Process text file (.txt, .md, etc.).
    
    Args:
        file_path: Path to text file
    
    Returns:
        List of dictionaries with title, content, category, tags
    """
    articles = []
    metadata = extract_metadata_from_filename(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        # Chunk the text
        chunks = chunk_text(text)
        
        # Create articles from chunks
        for i, chunk in enumerate(chunks):
            title = f"{metadata['title']} - Part {i+1}" if len(chunks) > 1 else metadata['title']
            articles.append({
                "title": title,
                "content": chunk,
                "category": metadata["category"],
                "tags": metadata["tags"]
            })
    
    except Exception as e:
        raise Exception(f"Error processing text file: {e}")
    
    return articles


def process_docx(file_path: str) -> List[Dict[str, str]]:
    """
    Process DOCX file and extract text.
    
    Args:
        file_path: Path to DOCX file
    
    Returns:
        List of dictionaries with title, content, category, tags
    """
    if not DOCX_AVAILABLE:
        raise Exception("DOCX processing not available. Install python-docx.")
    
    articles = []
    metadata = extract_metadata_from_filename(file_path)
    
    try:
        doc = Document(file_path)
        
        # Extract text from all paragraphs
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        
        # Chunk the text
        chunks = chunk_text(text)
        
        # Create articles from chunks
        for i, chunk in enumerate(chunks):
            title = f"{metadata['title']} - Part {i+1}" if len(chunks) > 1 else metadata['title']
            articles.append({
                "title": title,
                "content": chunk,
                "category": metadata["category"],
                "tags": metadata["tags"]
            })
    
    except Exception as e:
        raise Exception(f"Error processing DOCX: {e}")
    
    return articles


def process_document(file_path: str, file_type: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Process a document file based on its type.
    
    Args:
        file_path: Path to document file
        file_type: File type (pdf, csv, txt, md, docx). If None, inferred from extension.
    
    Returns:
        List of dictionaries with title, content, category, tags
    """
    if not file_type:
        ext = Path(file_path).suffix.lower()
        file_type = ext.lstrip('.')
    
    file_type = file_type.lower()
    
    if file_type == 'pdf':
        return process_pdf(file_path)
    elif file_type == 'csv':
        return process_csv(file_path)
    elif file_type in ['txt', 'md', 'markdown']:
        return process_text_file(file_path)
    elif file_type == 'docx':
        return process_docx(file_path)
    else:
        raise Exception(f"Unsupported file type: {file_type}")

