import os
import requests
from bs4 import BeautifulSoup
import html2text
import pdfplumber
import pytesseract
from PIL import Image
import docx
import openpyxl
try:
    import aspose.words as aw
    HAS_ASPOSE = True
except ImportError:
    HAS_ASPOSE = False
import uuid
import json

from urllib.parse import urlparse

def is_valid_url(url):
    try:
        result = urlparse(url)
        # Block localhost, loopback, private IPs for SSRF protection
        # For simplicity, we just allow http and https and block clear local addresses
        if result.scheme not in ['http', 'https']:
            return False
        hostname = result.hostname
        if hostname in ['localhost', '127.0.0.1', '0.0.0.0'] or hostname.startswith('192.168.') or hostname.startswith('10.'):
            return False
        return True
    except:
        return False

def parse_url(url: str) -> str:
    if not is_valid_url(url):
        print(f"URL {url} is not permitted for security reasons.")
        return ""
    try:
        # Prevent accessing internal metadata endpoints
        if '169.254.169.254' in url:
            return ""

        response = requests.get(url, timeout=10)

        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        h = html2text.HTML2Text()
        h.ignore_links = False
        text = h.handle(str(soup))
        return text
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        return ""

def parse_pdf(file_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

                # Extract images and do OCR if page text is very short or user explicitly wants it
                # For simplicity, we can do OCR on cropped images or the whole page image if no text
                if not page_text or len(page_text.strip()) < 50:
                    im = page.to_image()
                    ocr_text = pytesseract.image_to_string(im.original)
                    if ocr_text:
                        text += ocr_text + "\n"
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
    return text

def parse_docx(file_path: str) -> str:
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        if HAS_ASPOSE:
            try:
                doc = aw.Document(file_path)
                text = doc.to_string(aw.SaveFormat.TEXT)
            except Exception as e2:
                print(f"Error parsing DOC/DOCX {file_path}: {e2}")
        else:
             print(f"Error parsing DOC/DOCX {file_path}: {e}. (aspose-words not available for fallback)")
    return text

def parse_excel(file_path: str) -> str:
    text = ""
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for sheet in wb.worksheets:
            text += f"--- Sheet: {sheet.title} ---\n"
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join([str(cell) for cell in row if cell is not None])
                if row_text:
                    text += row_text + "\n"
    except Exception as e:
        print(f"Error parsing Excel {file_path}: {e}")
    return text

def parse_wps(file_path: str) -> str:
    if not HAS_ASPOSE:
        print(f"Warning: Cannot parse WPS {file_path} because aspose-words is not installed on this python version.")
        return "无法解析 WPS 文件，因为当前 Python 环境未安装 aspose-words 库。"
    text = ""
    try:
        doc = aw.Document(file_path)
        text = doc.to_string(aw.SaveFormat.TEXT)
    except Exception as e:
        print(f"Error parsing WPS {file_path}: {e}")
    return text

def parse_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            print(f"Error parsing TXT {file_path}: {e}")
            return ""

def parse_file(file_path: str, filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]

    if ext == '.pdf':
        return parse_pdf(file_path)
    elif ext in ['.doc', '.docx']:
        return parse_docx(file_path)
    elif ext in ['.xls', '.xlsx']:
        return parse_excel(file_path)
    elif ext == '.wps':
        return parse_wps(file_path)
    elif ext in ['.txt', '.md']:
        return parse_txt(file_path)
    else:
        # fallback text reading
        return parse_txt(file_path)

def clean_and_unify_text(text: str, openai_client) -> str:
    """
    Uses DeepSeek to clean the text, remove non-valuable info, and unify the format.
    Chunks the text to avoid context length limits and avoid silent data loss.
    """
    if not openai_client or not text:
        return text

    # Chunk text to roughly 4000 characters per chunk to be safe with context windows
    chunk_size = 4000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    cleaned_chunks = []

    for chunk in chunks:
        prompt = f"""
        You are a professional data cleaning assistant.
        Your task is to review the following text, identify and remove non-valuable information (like random characters, irrelevant navbars from web pages, gibberish), and unify the text into a clean Markdown format.

        ONLY output the cleaned, valuable text. DO NOT add any extra conversational text.

        Raw Text:
        {chunk}
        """

        try:
            response = openai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional text cleaning assistant. Output only the cleaned markdown text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            cleaned_chunks.append(response.choices[0].message.content)
        except Exception as e:
            print(f"Error cleaning text chunk with DeepSeek: {e}")
            cleaned_chunks.append(chunk) # fallback to original chunk

    return "\n\n".join(cleaned_chunks)
