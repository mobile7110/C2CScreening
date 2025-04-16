import pydantic # No adk import needed here anymore
import logging
from typing import List, Dict, Any, Optional

# Import specific functions from the backend Airtable client
from backend.airtable_client import (
    get_jd_details_by_title,
    create_application_log,
    update_application_log,
    create_llm_response_log,
    create_successful_candidate
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Tool: Get Job Description Details ---
class GetJdInput(pydantic.BaseModel):
    position_title: str = pydantic.Field(..., description="The exact 'Position Title' field value of the job description to retrieve from Airtable.")

class GetJdOutput(pydantic.BaseModel):
    jd_record_id: Optional[str] = pydantic.Field(description="The Airtable Record ID of the found Job Description. Null if not found or error.")
    jd_details: Optional[Dict[str, Any]] = pydantic.Field(description="A dictionary containing the 'fields' of the Job Description record (e.g., 'Job Description Text', 'Client Name'). Null if not found or error.")
    error_message: Optional[str] = pydantic.Field(description="Error message if the lookup failed (e.g., 'JD not found', 'Airtable connection error'). Null on success.")

# REMOVED @adk.tool decorator
def get_jd_details_tool(inp: GetJdInput) -> GetJdOutput:
    """
    Retrieves the full details (Record ID and all fields) for a specific job description from Airtable using its exact 'Position Title'. Critical for obtaining the JD text for analysis.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'get_job_description_details' for title: '{inp.position_title}'")
    try:
        record = get_jd_details_by_title(inp.position_title)
        if record and 'id' in record and 'fields' in record:
            logger.info(f"Found JD '{record['id']}' for title '{inp.position_title}'.")
            return GetJdOutput(jd_record_id=record['id'], jd_details=record['fields'], error_message=None)
        else:
            logger.warning(f"JD details not found for title '{inp.position_title}'.")
            error_msg = f"Job Description with title '{inp.position_title}' not found in Airtable."
            return GetJdOutput(jd_record_id=None, jd_details=None, error_message=error_msg)
    except ConnectionError as ce:
        logger.exception(f"Airtable connection error in 'get_job_description_details' for title '{inp.position_title}'.")
        return GetJdOutput(jd_record_id=None, jd_details=None, error_message=f"Airtable connection error: {str(ce)}")
    except Exception as e:
        logger.exception(f"Unexpected error in 'get_job_description_details' tool for title '{inp.position_title}'.")
        return GetJdOutput(jd_record_id=None, jd_details=None, error_message=f"An unexpected error occurred while fetching JD details: {str(e)}")


# --- Tool: Log Application Attempt ---
class LogAppInput(pydantic.BaseModel):
    applied_position_title: str = pydantic.Field(..., description="The title of the position the candidate applied for.")
    candidate_email: Optional[str] = pydantic.Field(None, description="The candidate's email address, if provided.")
    cv_filename: str = pydantic.Field(..., description="The original filename of the submitted CV.")
    processing_status: str = pydantic.Field(default="Received", description="The initial processing status (defaults to 'Received').")

class LogAppOutput(pydantic.BaseModel):
    log_record_id: Optional[str] = pydantic.Field(description="The Airtable Record ID of the newly created 'Application Logs' entry. Null on failure.")
    error_message: Optional[str] = pydantic.Field(description="Error message if logging failed. Null on success.")

# REMOVED @adk.tool decorator
def log_application_tool(inp: LogAppInput) -> LogAppOutput:
    """
    Creates an initial record in the 'Application Logs' table in Airtable when starting to process a new application. Returns the Record ID of the new log entry, which is needed for future updates.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'log_application_attempt' for '{inp.applied_position_title}', CV: {inp.cv_filename}")
    try:
        log_data = inp.model_dump(exclude_none=True)
        record_id = create_application_log(log_data)
        if record_id:
            logger.info(f"Successfully created application log with ID: {record_id}")
            return LogAppOutput(log_record_id=record_id, error_message=None)
        else:
            logger.error("Failed to create application log (backend returned None ID). Check Airtable connection and permissions.")
            return LogAppOutput(log_record_id=None, error_message="Failed to create application log entry in Airtable. Check connection/permissions.")
    except ConnectionError as ce:
        logger.exception("Airtable connection error in 'log_application_attempt'.")
        return LogAppOutput(log_record_id=None, error_message=f"Airtable connection error: {str(ce)}")
    except Exception as e:
        logger.exception("Unexpected error in 'log_application_attempt' tool.")
        return LogAppOutput(log_record_id=None, error_message=f"An unexpected error occurred while logging the application attempt: {str(e)}")


# --- Tool: Update Application Log ---
class UpdateLogInput(pydantic.BaseModel):
    log_record_id: str = pydantic.Field(..., description="The Airtable Record ID of the 'Application Logs' entry to update.")
    updates: Dict[str, Any] = pydantic.Field(..., description="A dictionary of fields to update. Keys are Airtable field names (e.g., 'Processing Status', 'Final Outcome', 'Error Details'). Values are the new data. For linked records (e.g., 'Associated LLM Response', 'Associated Candidate Record'), provide the value as a LIST containing the linked record ID(s), like ['recXXXXXXXXXXXXXX'].")

class UpdateLogOutput(pydantic.BaseModel):
    success: bool = pydantic.Field(description="True if the update was confirmed successful by the backend API, False otherwise.")
    error_message: Optional[str] = pydantic.Field(description="Error message if the update failed. Null on success.")

# REMOVED @adk.tool decorator
def update_log_tool(inp: UpdateLogInput) -> UpdateLogOutput:
    """
    Updates one or more fields of an existing Application Log record in Airtable using its Record ID. Essential for tracking progress, recording outcomes, linking related records (LLM responses, candidate profiles), and logging errors.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'update_application_log' for ID '{inp.log_record_id}' with fields: {list(inp.updates.keys())}")
    if not inp.updates:
         logger.warning(f"Tool 'update_application_log' called with empty updates for ID '{inp.log_record_id}'. No action taken.")
         return UpdateLogOutput(success=True, error_message=None)
    try:
        success = update_application_log(inp.log_record_id, inp.updates)
        if success:
            logger.info(f"Successfully updated application log '{inp.log_record_id}'.")
            return UpdateLogOutput(success=True, error_message=None)
        else:
            logger.error(f"Failed to update application log '{inp.log_record_id}' (backend returned False). Record might not exist or Airtable API error.")
            return UpdateLogOutput(success=False, error_message="Failed to update application log entry in Airtable (record might not exist or update failed).")
    except ConnectionError as ce:
         logger.exception(f"Airtable connection error in 'update_application_log' for log '{inp.log_record_id}'.")
         return UpdateLogOutput(success=False, error_message=f"Airtable connection error: {str(ce)}")
    except Exception as e:
        logger.exception(f"Unexpected error in 'update_application_log' tool for log '{inp.log_record_id}'.")
        return UpdateLogOutput(success=False, error_message=f"An unexpected error occurred while updating the application log: {str(e)}")


# --- Tool: Log LLM Response ---
class LogLlmResponseInput(pydantic.BaseModel):
    associated_log_entry_id: str = pydantic.Field(..., description="The Record ID of the 'Application Logs' entry this LLM interaction relates to.")
    full_prompt_sent: str = pydantic.Field(..., description="The complete prompt text that was sent to the language model for analysis.")
    raw_response_received: str = pydantic.Field(..., description="The exact, unparsed response text or JSON received from the language model.")
    parsing_status: str = pydantic.Field(..., description="Indicates if the agent successfully parsed the required information from the LLM response ('Success' or 'Failure').")

class LogLlmResponseOutput(pydantic.BaseModel):
    llm_response_record_id: Optional[str] = pydantic.Field(description="The Airtable Record ID of the newly created 'LLM Responses' entry. Null on failure.")
    error_message: Optional[str] = pydantic.Field(description="Error message if logging failed. Null on success.")

# REMOVED @adk.tool decorator
def log_llm_response_tool(inp: LogLlmResponseInput) -> LogLlmResponseOutput:
    """
    Creates a record in the 'LLM Responses' table in Airtable to store the details of an interaction with the language model (prompt, response, parsing status). Requires the Record ID of the associated 'Application Logs' entry for linking.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'log_llm_interaction' for Application Log ID: {inp.associated_log_entry_id}")
    try:
        response_data = inp.model_dump()
        record_id = create_llm_response_log(response_data)
        if record_id:
            logger.info(f"Successfully created LLM response log with ID: {record_id}")
            return LogLlmResponseOutput(llm_response_record_id=record_id, error_message=None)
        else:
            logger.error("Failed to create LLM response log (backend returned None ID). Check link ID and permissions.")
            return LogLlmResponseOutput(llm_response_record_id=None, error_message="Failed to create LLM response log entry in Airtable.")
    except ConnectionError as ce:
         logger.exception(f"Airtable connection error in 'log_llm_interaction' for log '{inp.associated_log_entry_id}'.")
         return LogLlmResponseOutput(llm_response_record_id=None, error_message=f"Airtable connection error: {str(ce)}")
    except Exception as e:
        logger.exception(f"Error in 'log_llm_interaction' tool for log '{inp.associated_log_entry_id}'.")
        return LogLlmResponseOutput(llm_response_record_id=None, error_message=f"An unexpected error occurred while logging the LLM response: {str(e)}")


# --- Tool: Create Successful Candidate Record ---
class CreateCandidateInput(pydantic.BaseModel):
    associated_log_entry_id: str = pydantic.Field(..., description="The Record ID of the 'Application Logs' entry corresponding to this successful candidate.")
    applied_position_jd_id: str = pydantic.Field(..., description="The Record ID of the 'Job Descriptions' record the candidate applied for and matched.")
    candidate_name: Optional[str] = pydantic.Field(None, description="The candidate's name, if extracted or available.")
    candidate_email: Optional[str] = pydantic.Field(None, description="The candidate's email address.")
    llm_match_reason: Optional[str] = pydantic.Field(None, description="A brief summary from the LLM analysis explaining why the candidate was considered a match.")
    interview_scheduling_status: str = pydantic.Field(default="Pending", description="Initial scheduling status (defaults to 'Pending').")

class CreateCandidateOutput(pydantic.BaseModel):
    candidate_record_id: Optional[str] = pydantic.Field(description="The Airtable Record ID of the newly created 'Successful Candidates' entry. Null on failure.")
    error_message: Optional[str] = pydantic.Field(description="Error message if creation failed. Null on success.")

# REMOVED @adk.tool decorator
def create_candidate_tool(inp: CreateCandidateInput) -> CreateCandidateOutput:
    """
    Creates a record in the 'Successful Candidates' table in Airtable ONLY when a candidate definitively passes the LLM screening. Requires the Record IDs of the associated 'Application Logs' entry and the matched 'Job Descriptions' entry.
    """
    # Function implementation remains the same...
    logger.info(f"Executing tool 'create_successful_candidate_record' for Application Log ID: {inp.associated_log_entry_id}")
    try:
        candidate_data = inp.model_dump(exclude_none=True)
        record_id = create_successful_candidate(candidate_data)
        if record_id:
            logger.info(f"Successfully created successful candidate record with ID: {record_id}")
            return CreateCandidateOutput(candidate_record_id=record_id, error_message=None)
        else:
            logger.error("Failed to create successful candidate record (backend returned None ID). Check link IDs and permissions.")
            return CreateCandidateOutput(candidate_record_id=None, error_message="Failed to create successful candidate entry in Airtable.")
    except ConnectionError as ce:
        logger.exception(f"Airtable connection error in 'create_successful_candidate_record' for log '{inp.associated_log_entry_id}'.")
        return CreateCandidateOutput(candidate_record_id=None, error_message=f"Airtable connection error: {str(ce)}")
    except Exception as e:
        logger.exception(f"Error in 'create_successful_candidate_record' tool for log '{inp.associated_log_entry_id}'.")
        return CreateCandidateOutput(candidate_record_id=None, error_message=f"An unexpected error occurred while creating the successful candidate record: {str(e)}")