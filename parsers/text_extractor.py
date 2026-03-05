import re
import io
from docx import Document
import PyPDF2


def clean_resume(txt: str) -> str:
    cleanText = re.sub(r'http\S+\s', ' ', txt)
    cleanText = re.sub(r'\b(RT|cc)\b', ' ', cleanText)
    cleanText = re.sub(r'#\S+\s', ' ', cleanText)
    cleanText = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '', cleanText)
    cleanText = re.sub(r'[%s]' % re.escape(r"""!"#$%&()*+,/:;<=>?@[\]^_{|}~"""), ' ', cleanText)
    cleanText = re.sub(r'[\u2013\u2014\u2013\u2014]', '-', cleanText)
    cleanText = re.sub(r'\s+', ' ', cleanText)
    return cleanText.strip()


def extract_text(file_storage, filename: str) -> str:
    ext = filename.rsplit('.', 1)[-1].lower()

    try:
        if ext == 'pdf':
            if hasattr(file_storage, "stream"):
                file_storage.stream.seek(0)
                reader = PyPDF2.PdfReader(file_storage.stream)
            else:
                data = file_storage.read()
                reader = PyPDF2.PdfReader(io.BytesIO(data))

            try:
                if getattr(reader, "is_encrypted", False):
                    try:
                        reader.decrypt("")
                    except Exception:
                        pass
            except Exception:
                pass

            texts = []
            for p in reader.pages:
                try:
                    texts.append(p.extract_text() or "")
                except Exception:
                    texts.append("")
            return ''.join(texts)

        elif ext == 'docx':
            if hasattr(file_storage, "stream"):
                file_storage.stream.seek(0)
                data = file_storage.read()
            else:
                data = file_storage.read()
            doc = Document(io.BytesIO(data))
            return '\n'.join(p.text for p in doc.paragraphs)

        elif ext == 'txt':
            if hasattr(file_storage, "stream"):
                file_storage.stream.seek(0)
            return file_storage.read().decode('utf-8', errors='ignore')

        else:
            raise ValueError(f"Unsupported file type: .{ext}")

    except Exception as e:
        raise ValueError(f"Failed to extract text from {filename}: {e}") from e