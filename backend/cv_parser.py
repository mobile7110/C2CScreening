# # c2c_analyzer/backend/cv_parser.py

# import fitz  # PyMuPDF
# from docx import Document
# from docx.document import Document as DocxDocumentType
# from docx.oxml.table import CT_Tbl
# from docx.oxml.text.paragraph import CT_P
# from docx.table import _Cell, Table as DocxTableType
# from docx.text.paragraph import Paragraph
# import io
# import logging
# from typing import Optional

# # Configure basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # Define reasonable limits
# MAX_CV_SIZE_MB = 10
# MAX_CV_SIZE_BYTES = MAX_CV_SIZE_MB * 1024 * 1024

# def iter_block_items(parent):
#     """
#     Yields paragraph and table objects from the immediate parent object.
#     Necessary because document._body directly yields only low-level XML elements.
#     """
#     if isinstance(parent, DocxDocumentType):
#         parent_elm = parent.element.body
#     elif isinstance(parent, _Cell):
#         parent_elm = parent._tc
#     else:
#         raise ValueError("Parent object type not supported")

#     for child in parent_elm.iterchildren():
#         if isinstance(child, CT_P):
#             yield Paragraph(child, parent)
#         elif isinstance(child, CT_Tbl):
#             yield DocxTableType(child, parent)


# def extract_text_from_cv_bytes(file_bytes: bytes, file_name: str) -> Optional[str]:
#     """
#     Extracts text content from CV file bytes (PDF or DOCX) with improved formatting,
#     including Markdown conversion for DOCX tables.

#     Args:
#         file_bytes: The content of the file as bytes.
#         file_name: The original filename including extension.

#     Returns:
#         The extracted text as a string, or an error/warning message if extraction fails.
#     """
#     if not file_bytes or not file_name:
#         logger.error("CV Parser: Missing file bytes or filename.")
#         return "Error: Missing file content or filename."

#     if len(file_bytes) > MAX_CV_SIZE_BYTES:
#         logger.warning(f"CV Parser: File '{file_name}' ({len(file_bytes)/(1024*1024):.2f} MB) exceeds {MAX_CV_SIZE_MB}MB limit.")
#         return f"Error: File size exceeds {MAX_CV_SIZE_MB}MB limit."

#     try:
#         file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
#         text_parts = []
#         logger.info(f"CV Parser: Attempting to parse '{file_name}' (Type: {file_ext}, Size: {len(file_bytes)} bytes)")

#         if file_ext == 'pdf':
#             try:
#                 with fitz.open(stream=file_bytes, filetype="pdf") as doc:
#                     if not doc.page_count:
#                         logger.warning(f"CV Parser: PDF '{file_name}' contains no pages.")
#                         return "Error: PDF contains no pages."

#                     for page_num, page in enumerate(doc):
#                         page_text = page.get_text("text", sort=True).strip()
#                         if page_text:
#                             text_parts.append(page_text)
#                         elif page.get_images(full=True):
#                              logger.warning(f"CV Parser: Page {page_num+1} of PDF '{file_name}' has images but yielded little/no text. Might be image-based.")
#                         else:
#                              logger.debug(f"CV Parser: Page {page_num+1} of PDF '{file_name}' yielded no text.")

#                     if not text_parts:
#                          logger.warning(f"CV Parser: PDF '{file_name}' resulted in no text extraction. Might be image-based or empty.")
#                          return "Warning: No text extracted from PDF. File might be image-based, empty, or have unusual formatting."
#                     # Join pages with double newline
#                     final_text = "\n\n".join(text_parts)

#             except Exception as pdf_err:
#                 err_str = str(pdf_err).lower()
#                 if "password" in err_str or "encrypted" in err_str: return "Error: PDF is password-protected."
#                 elif "cannot open" in err_str or "damaged" in err_str: return "Error: PDF seems corrupted."
#                 else: logger.exception(f"CV Parser: PDF extraction error '{file_name}'."); return "Error: Failed to extract text from PDF."

#         elif file_ext == 'docx':
#             try:
#                 document = Document(io.BytesIO(file_bytes))
#                 # Iterate through paragraphs and tables directly in document body
#                 for block in iter_block_items(document):
#                     if isinstance(block, Paragraph):
#                         para_text = block.text.strip()
#                         if para_text:
#                             text_parts.append(para_text)
#                     elif isinstance(block, DocxTableType):
#                         # Attempt to format table as Markdown
#                         markdown_table = "\n" # Start with newline before table
#                         header_row_processed = False
#                         num_cols = 0
#                         if block.rows:
#                              num_cols = len(block.rows[0].cells) # Assume consistent cols
#                              # Header Row
#                              header_cells = [cell.text.strip() for cell in block.rows[0].cells]
#                              markdown_table += "| " + " | ".join(header_cells) + " |\n"
#                              # Separator Row
#                              markdown_table += "| " + " | ".join(['---'] * num_cols) + " |\n"
#                              header_row_processed = True

#                         # Data Rows (skip first row if header was processed)
#                         start_row = 1 if header_row_processed else 0
#                         for i in range(start_row, len(block.rows)):
#                              row = block.rows[i]
#                              # Ensure we don't try accessing cells beyond the actual count for potentially merged rows
#                              current_row_cells = [cell.text.strip() for cell in row.cells[:num_cols]]
#                              # Pad if row has fewer cells than header (unlikely but possible)
#                              current_row_cells.extend([''] * (num_cols - len(current_row_cells)))
#                              markdown_table += "| " + " | ".join(current_row_cells) + " |\n"

#                         text_parts.append(markdown_table.strip()) # Add formatted table

#                 # Join all parts with double newlines for separation
#                 final_text = "\n\n".join(filter(None, text_parts))

#             except Exception as docx_err:
#                 logger.exception(f"CV Parser: DOCX extraction error '{file_name}'. Error: {docx_err}")
#                 return "Error: Failed to extract text from DOCX."
#         else:
#             logger.error(f"CV Parser: Unsupported type '{file_ext}' for '{file_name}'.")
#             return f"Error: Unsupported file type '{file_ext}'. Only PDF/DOCX."

#         # Final check for empty result after successful parse attempt
#         if not final_text or not final_text.strip():
#             logger.warning(f"CV Parser: Extraction resulted in empty text for '{file_name}'.")
#             return "Warning: Text extraction yielded empty content. File might be image-based or have no text."

#         logger.info(f"CV Parser: Successfully extracted ~{len(final_text)} chars from '{file_name}'.")
#         return final_text.strip()

#     except Exception as general_err:
#         logger.exception(f"CV Parser: Unexpected error processing '{file_name}'. Error: {general_err}")
#         return "Error: An unexpected system error occurred during file processing."





# c2c_analyzer/backend/cv_parser.py

import fitz  # PyMuPDF
from docx import Document
from docx.document import Document as DocxDocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table as DocxTableType
from docx.text.paragraph import Paragraph
import io
import logging
from typing import Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
logger = logging.getLogger(__name__)

# Define reasonable limits
MAX_CV_SIZE_MB = 10
MAX_CV_SIZE_BYTES = MAX_CV_SIZE_MB * 1024 * 1024

def iter_block_items(parent):
    """
    Yields paragraph and table objects from the immediate parent object.
    """
    if isinstance(parent, DocxDocumentType):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Parent object type not supported")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield DocxTableType(child, parent)


def extract_text_from_cv_bytes(file_bytes: bytes, file_name: str) -> Optional[str]:
    """
    Extracts text content from CV file bytes (PDF or DOCX) with improved formatting,
    including Markdown conversion for DOCX tables.

    Args:
        file_bytes: The content of the file as bytes.
        file_name: The original filename including extension.

    Returns:
        The extracted text as a string, or an error/warning message if extraction fails.
    """
    if not file_bytes or not file_name:
        logger.error("CV Parser: Missing file bytes or filename.")
        return "Error: Missing file content or filename."

    if len(file_bytes) > MAX_CV_SIZE_BYTES:
        logger.warning(f"CV Parser: File '{file_name}' ({len(file_bytes)/(1024*1024):.2f} MB) exceeds {MAX_CV_SIZE_MB}MB limit.")
        return f"Error: File size exceeds {MAX_CV_SIZE_MB}MB limit."

    try:
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        text_parts = []
        final_text = ""
        logger.info(f"CV Parser: Attempting to parse '{file_name}' (Type: {file_ext}, Size: {len(file_bytes)} bytes)")

        if file_ext == 'pdf':
            try:
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    if not doc.page_count:
                        logger.warning(f"CV Parser: PDF '{file_name}' contains no pages.")
                        return "Error: PDF contains no pages."

                    for page_num, page in enumerate(doc):
                        page_text = page.get_text("text", sort=True).strip()
                        if page_text:
                            text_parts.append(page_text)
                        elif page.get_images(full=True):
                             logger.warning(f"CV Parser: Page {page_num+1} of PDF '{file_name}' has images but yielded little/no text. Might be image-based.")
                        else:
                             logger.debug(f"CV Parser: Page {page_num+1} of PDF '{file_name}' yielded no text.")

                    if not text_parts:
                         logger.warning(f"CV Parser: PDF '{file_name}' resulted in no text extraction. Might be image-based or empty.")
                         return "Warning: No text extracted from PDF. File might be image-based, empty, or have unusual formatting."
                    final_text = "\n\n".join(text_parts) # Join pages with double newline

            except Exception as pdf_err:
                err_str = str(pdf_err).lower()
                if "password" in err_str or "encrypted" in err_str: return "Error: PDF is password-protected."
                elif "cannot open" in err_str or "damaged" in err_str: return "Error: PDF seems corrupted."
                else: logger.exception(f"CV Parser: PDF extraction error '{file_name}'."); return "Error: Failed to extract text from PDF."

        elif file_ext == 'docx':
            try:
                document = Document(io.BytesIO(file_bytes))
                for block in iter_block_items(document):
                    if isinstance(block, Paragraph):
                        para_text = block.text.strip()
                        if para_text:
                            text_parts.append(para_text)
                    elif isinstance(block, DocxTableType):
                        markdown_table = "\n"
                        num_cols = 0
                        if block.rows:
                             num_cols = len(block.rows[0].cells)
                             header_cells = [cell.text.strip().replace('|', '\\|') for cell in block.rows[0].cells] # Escape pipe characters
                             markdown_table += "| " + " | ".join(header_cells) + " |\n"
                             markdown_table += "| " + " | ".join(['---'] * num_cols) + " |\n"
                             start_row = 1
                        else:
                            start_row = 0 # No header row

                        for i in range(start_row, len(block.rows)):
                             row = block.rows[i]
                             current_row_cells = [cell.text.strip().replace('|', '\\|') for cell in row.cells[:num_cols]] # Escape pipe characters
                             current_row_cells.extend([''] * (num_cols - len(current_row_cells)))
                             markdown_table += "| " + " | ".join(current_row_cells) + " |\n"
                        text_parts.append(markdown_table.strip())
                final_text = "\n\n".join(filter(None, text_parts)) # Join blocks with double newlines

            except Exception as docx_err:
                logger.exception(f"CV Parser: DOCX extraction error '{file_name}'. Error: {docx_err}")
                return "Error: Failed to extract text from DOCX."
        else:
            logger.error(f"CV Parser: Unsupported type '{file_ext}' for '{file_name}'.")
            return f"Error: Unsupported file type '{file_ext}'. Only PDF/DOCX."

        if not final_text or not final_text.strip():
            logger.warning(f"CV Parser: Extraction resulted in empty text for '{file_name}'.")
            return "Warning: Text extraction yielded empty content. File might be image-based or have no text."

        logger.info(f"CV Parser: Successfully extracted ~{len(final_text)} chars from '{file_name}'.")
        return final_text.strip()

    except Exception as general_err:
        logger.exception(f"CV Parser: Unexpected error processing '{file_name}'. Error: {general_err}")
        return "Error: An unexpected system error occurred during file processing."