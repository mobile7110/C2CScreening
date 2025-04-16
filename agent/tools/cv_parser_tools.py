# No adk import needed here anymore
import pydantic
import base64
import logging
from typing import Optional, Tuple

# Import the specific parsing function from the backend module
from backend.cv_parser import extract_text_from_cv_bytes

# Configure logging specific to this tool
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Adjust level as needed

class ParseCvInput(pydantic.BaseModel):
    """Input schema for the CV parsing tool."""
    file_content_base64: str = pydantic.Field(..., description="Base64 encoded string of the CV file content (PDF or DOCX).")
    file_name: str = pydantic.Field(..., description="Original filename including the extension (e.g., 'candidate_resume.pdf'). Required to determine file type.")

class ParseCvOutput(pydantic.BaseModel):
    """Output schema for the CV parsing tool."""
    extracted_text: Optional[str] = pydantic.Field(description="The extracted text content from the CV. Null if parsing failed or the file was empty/unsupported.")
    error_message: Optional[str] = pydantic.Field(description="A descriptive error message if text extraction failed (e.g., size limit, unsupported type, password protected). Null on success.")

# REMOVED @adk.tool decorator
def parse_cv_tool(inp: ParseCvInput) -> ParseCvOutput:
    """
    Extracts plain text from a candidate's CV document (PDF or DOCX). Input requires the filename (with extension) and the file content encoded as a Base64 string. Returns the extracted text or an error message if parsing fails.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'parse_candidate_cv' for file: {inp.file_name}")
    extracted_text: Optional[str] = None
    error_message: Optional[str] = None

    try:
        # Decode the base64 content
        try:
            file_bytes = base64.b64decode(inp.file_content_base64, validate=True) # Add validation
            logger.debug(f"Successfully decoded base64 content for {inp.file_name}.")
        except (TypeError, base64.binascii.Error) as decode_err:
            logger.error(f"Base64 decoding failed for {inp.file_name}: {decode_err}")
            error_message = "Invalid Base64 encoding provided for CV content."
            return ParseCvOutput(extracted_text=None, error_message=error_message)

        # Call the backend parsing function
        result = extract_text_from_cv_bytes(file_bytes=file_bytes, file_name=inp.file_name)

        if result is None:
             logger.error(f"CV parsing returned None unexpectedly for {inp.file_name}.")
             error_message = "An unknown error occurred during CV parsing."
        elif result.startswith("Error:") or result.startswith("Warning:"):
             logger.warning(f"CV parsing for {inp.file_name} resulted in: {result}")
             error_message = result # Pass the specific error/warning message from backend
        else:
             # Success case
             extracted_text = result
             logger.info(f"Successfully parsed CV: {inp.file_name}")

        return ParseCvOutput(extracted_text=extracted_text, error_message=error_message)

    except Exception as e:
        logger.exception(f"Unexpected error within 'parse_candidate_cv' tool for {inp.file_name}.")
        error_message = f"An unexpected system error occurred during CV parsing: {str(e)}"
        return ParseCvOutput(extracted_text=None, error_message=error_message)