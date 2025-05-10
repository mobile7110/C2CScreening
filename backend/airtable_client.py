# # backend/airtable_client.py

# import os
# import logging
# import re
# from pyairtable import Api, Table
# from pyairtable.formulas import match
# # REMOVED: from dotenv import load_dotenv (will be imported conditionally)
# from typing import List, Dict, Any, Optional, Tuple, Type
# from enum import Enum

# # --- Conditional dotenv Loading ---
# # Check if running in a deployed environment like Streamlit Cloud
# # Streamlit Cloud typically sets specific env vars. Use one as a flag.
# # If not set, assume local development and try to load .env
# IS_DEPLOYED_ENV = os.getenv('STREAMLIT_SERVER_ENABLE_STATIC_SERVING') == 'true'

# if not IS_DEPLOYED_ENV:
#     try:
#         # Import dotenv only if needed for local dev
#         from dotenv import load_dotenv
#         # print("DEBUG: Local environment detected. Attempting to load .env...") # Optional debug
#         # Try to load .env from the default location (usually project root)
#         # load_dotenv will not override existing environment variables
#         if load_dotenv():
#             # print("DEBUG: .env file loaded successfully.") # Optional debug
#             pass
#         else:
#             # print("DEBUG: .env file not found or empty.") # Optional debug
#             pass
#     except ImportError:
#         # print("DEBUG: python-dotenv not installed, skipping .env load.") # Optional debug
#         pass # dotenv not installed, proceed without it
# else:
#     # print("DEBUG: Deployed environment detected. Skipping .env load.") # Optional debug
#     pass
# # --- End Conditional Loading ---


# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # --- Helper function to clean environment variables ---
# def get_clean_env_var(var_name: str) -> str:
#     """Gets env var, removes inline comments, and strips whitespace."""
#     # Now reads directly from environment (set by OS, Docker, Streamlit Secrets, or loaded by dotenv locally)
#     value = os.getenv(var_name, "")
#     value = value.split('#', 1)[0] # Remove potential inline comments
#     return value.strip() # Strip leading/trailing whitespace

# # --- Configuration (Using Cleaner Helper) ---
# # These os.getenv calls will now work both locally (via dotenv) and remotely (via Streamlit Secrets)
# AIRTABLE_PAT = get_clean_env_var("AIRTABLE_PAT")
# AIRTABLE_BASE_ID = get_clean_env_var("AIRTABLE_BASE_ID")
# API_TIMEOUT = int(get_clean_env_var("AIRTABLE_API_TIMEOUT") or 30)

# REQ_TABLE_ID = get_clean_env_var("AIRTABLE_JD_TABLE_ID")
# LOGS_TABLE_ID = get_clean_env_var("AIRTABLE_LOGS_TABLE_ID")
# LLM_TABLE_ID = get_clean_env_var("AIRTABLE_LLM_TABLE_ID")
# CANDS_TABLE_ID = get_clean_env_var("AIRTABLE_CANDS_TABLE_ID")
# ADMIN_TABLE_ID = get_clean_env_var("AIRTABLE_ADMIN_TABLE_ID")

# # Load other necessary secrets directly from environment
# GOOGLE_API_KEY = get_clean_env_var("GOOGLE_API_KEY")
# ADMIN_PASSWORD_SALT = get_clean_env_var("ADMIN_PASSWORD_SALT")

# # --- Validation (After Cleaning) ---
# # Updated error messages to refer to environment variables/secrets
# # These checks run at import time, failing fast if critical secrets are missing
# if not AIRTABLE_PAT: raise ValueError("AIRTABLE_PAT missing. Check environment variables/secrets.")
# if not AIRTABLE_BASE_ID: raise ValueError("AIRTABLE_BASE_ID missing. Check environment variables/secrets.")
# if not GOOGLE_API_KEY: raise ValueError("GOOGLE_API_KEY missing. Check environment variables/secrets.")
# # Check other required secrets (ensure they are loaded before this point)
# if not REQ_TABLE_ID: raise ValueError("AIRTABLE_JD_TABLE_ID missing. Check environment variables/secrets.")
# if not LOGS_TABLE_ID: raise ValueError("AIRTABLE_LOGS_TABLE_ID missing. Check environment variables/secrets.")
# if not CANDS_TABLE_ID: raise ValueError("AIRTABLE_CANDS_TABLE_ID missing. Check environment variables/secrets.")
# if not ADMIN_PASSWORD_SALT: raise ValueError("ADMIN_PASSWORD_SALT missing. Check environment variables/secrets.")

# # Optional tables checks (warnings only)
# required_tables = {"Requirements": REQ_TABLE_ID, "Logs": LOGS_TABLE_ID, "Candidates": CANDS_TABLE_ID} # Removed LLM table from here
# missing_or_invalid_tables = [name for name, tid in required_tables.items() if not tid or not tid.startswith("tbl")]
# if missing_or_invalid_tables:
#     # This check might be redundant given the specific checks above, but kept for structure
#     raise ValueError(f"Required Airtable Table IDs missing or invalid. Check environment variables/secrets: {', '.join(missing_or_invalid_tables)}")

# if not LLM_TABLE_ID or not LLM_TABLE_ID.startswith("tbl"):
#     logger.warning("LLM_TABLE_ID invalid or not set in environment variables/secrets. LLM Response logging will fail.")
# if not ADMIN_TABLE_ID or not ADMIN_TABLE_ID.startswith("tbl"):
#     logger.warning("ADMIN_TABLE_ID invalid or not set in environment variables/secrets. Admin functions might fail.")


# # --- Field ID Management (No changes needed in this section) ---
# class FieldIdEnum(Enum):
#     def __str__(self): return str(self.value)

# class ReqFields(FieldIdEnum): # Client Requirements (tblUviQXKrL3TUuus)
#     REQUIREMENT_TITLE = "fldf4apw7f4y4s0Zy"; CLIENT = "fldlaY7OwUCXHXGfx"; TECH_SKILLS = "fld5UG3kXtMZnQ7Ds"; STATUS = "fldOvvFgl7ghEGaQu"; LOCATION = "fldCnohrYlA4cKhYN"; JD_TEXT = "fldPkWJKJ6sVwt9NV"; MIN_EXPERIENCE = "fld4ZG4X7O1yXGsu8"; BUDGET = "fldmhLvi8ZVFRN1zq"; DEADLINE = "fld5SBPcybPQbHu3Y"; PRIORITY = "fldiiIVfOS1MFxncE"; SPOC = "fldlJZnO1t0l9ozEM"; NOTES = "fldQFsgSPDkxlULet"; JD_LINK = "fldiysXPGqj5f1in6"; SUCCESSFUL_CANDIDATES_LINK = "fldjR2qwag27Vjelv"

# class LogFields(FieldIdEnum): # Application Logs (tbljEEl3ybgchxK6w)
#     LOG_ID = "fldLE9gd2n8ufyRP6"; APPLIED_POSITION_TITLE = "fldk6gqvdEkEc7r9F"; CV_FILENAME = "fldbpuzhA5WVJLnah"; CANDIDATE_EMAIL = "fldOWPXAbZq6itM1q"; PROCESSING_STATUS = "fldskHsD0nAykgIZW"; FINAL_OUTCOME = "fldjJfTep86DzRmub"; BACKEND_ANALYSIS_REPORT = "fldh4Pv1usXr5dxO6"; ERROR_DETAILS = "fldb7Hjd7BkBI8kPV"; ASSOCIATED_LLM_RESPONSE = "fld3VaKWJGu9hJdWq"; ASSOCIATED_CANDIDATE_RECORD = "fldugqwAmk623hC0G"

# class LlmRespFields(FieldIdEnum): # LLM Responses (tblM5foLOcBIgSdRB)
#     RESPONSE_ID = "fldnNi9LqCXKn3YLv"; ASSOCIATED_LOG_ENTRY = "fldzyxo4kHTgrxzoo"; BACKEND_ANALYSIS_REPORT = "fldLFZpSRFFJjqqUu"; FULL_PROMPT_SENT = "fldx8jyCuhqrjzaxG"; RAW_RESPONSE_RECEIVED = "fldJUBSWKi5waAky4"; PARSING_STATUS = "fldMg8wx22Yzkcx1t"

# class CandFields(FieldIdEnum): # Successful Candidates (tbl1RYRfDafP5vO9O)
#     NAME = "fld6w5Z4tbrUxRT1m"; COMPANY_NAME = "fldRZ7nBj9GJVR5wK"; ASSOCIATED_LOG_ENTRY = "fldhOdTPV4QvA5DbE"; APPLIED_POSITION = "fldkaE74Z2LtsgAN9"; LLM_MATCH_REASON = "fld7XOs2Zu7mVBdmL"; INTERVIEW_STATUS = "fldPS2HzfkL0EbpbY"

# class AdminFields(FieldIdEnum): # Admin Users (ID from env vars/secrets)
#      USERNAME = "fld???????????????" # Placeholder - Replace with actual ID if using admin features
#      PASSWORD_HASH = "fld???????????????" # Placeholder - Replace with actual ID if using admin features

# # --- `fields` class definition (No changes needed in this section) ---
# class fields:
#     """Provides string access to Field IDs via class attributes. Returns None if not defined."""
#     REQ_TITLE = str(ReqFields.REQUIREMENT_TITLE.value); REQ_LOCATION = str(ReqFields.LOCATION.value); REQ_MIN_EXPERIENCE = str(ReqFields.MIN_EXPERIENCE.value); REQ_STATUS = str(ReqFields.STATUS.value); REQ_JD_TEXT = str(ReqFields.JD_TEXT.value); REQ_BUDGET = str(ReqFields.BUDGET.value)
#     LOG_APPLIED_POSITION_TITLE = str(LogFields.APPLIED_POSITION_TITLE.value); LOG_CV_FILENAME = str(LogFields.CV_FILENAME.value)
#     LOG_CANDIDATE_EMAIL = str(LogFields.CANDIDATE_EMAIL.value); LOG_PROCESSING_STATUS = str(LogFields.PROCESSING_STATUS.value); LOG_FINAL_OUTCOME = str(LogFields.FINAL_OUTCOME.value); ERROR_DETAILS = str(LogFields.ERROR_DETAILS.value); LOG_BACKEND_REPORT = str(LogFields.BACKEND_ANALYSIS_REPORT.value); LOG_ASSOCIATED_LLM_RESPONSE = str(LogFields.ASSOCIATED_LLM_RESPONSE.value); LOG_ASSOCIATED_CANDIDATE_RECORD = str(LogFields.ASSOCIATED_CANDIDATE_RECORD.value)
#     LLM_ASSOCIATED_LOG_ENTRY = str(LlmRespFields.ASSOCIATED_LOG_ENTRY.value) if LLM_TABLE_ID else None; LLM_BACKEND_ANALYSIS_REPORT = str(LlmRespFields.BACKEND_ANALYSIS_REPORT.value) if LLM_TABLE_ID else None; LLM_FULL_PROMPT_SENT = str(LlmRespFields.FULL_PROMPT_SENT.value) if LLM_TABLE_ID else None; LLM_RAW_RESPONSE_RECEIVED = str(LlmRespFields.RAW_RESPONSE_RECEIVED.value) if LLM_TABLE_ID else None; LLM_PARSING_STATUS = str(LlmRespFields.PARSING_STATUS.value) if LLM_TABLE_ID else None
#     CAND_NAME = str(CandFields.NAME.value); CAND_COMPANY_NAME = str(CandFields.COMPANY_NAME.value); CAND_ASSOCIATED_LOG_ENTRY = str(CandFields.ASSOCIATED_LOG_ENTRY.value); CAND_APPLIED_POSITION = str(CandFields.APPLIED_POSITION.value); CAND_LLM_MATCH_REASON = str(CandFields.LLM_MATCH_REASON.value); CAND_INTERVIEW_STATUS = str(CandFields.INTERVIEW_STATUS.value)
#     ADMIN_USERNAME = str(AdminFields.USERNAME.value) if ADMIN_TABLE_ID and hasattr(AdminFields, 'USERNAME') and not AdminFields.USERNAME.value.startswith("fld????") else None
#     ADMIN_PASSWORD_HASH = str(AdminFields.PASSWORD_HASH.value) if ADMIN_TABLE_ID and hasattr(AdminFields, 'PASSWORD_HASH') and not AdminFields.PASSWORD_HASH.value.startswith("fld????") else None

#     @staticmethod
#     def get_field_id(field_name: str) -> Optional[str]:
#         """Maps common field names (case-insensitive) to their Field ID strings."""
#         if not isinstance(field_name, str): return None
#         name_to_attr_map = {
#             "requirement": "REQ_TITLE", "position_title": "REQ_TITLE", "location": "REQ_LOCATION", "minimum_experience": "REQ_MIN_EXPERIENCE",
#             "minimum_experience_in_years": "REQ_MIN_EXPERIENCE", "status": "REQ_STATUS", "jd_in_text": "REQ_JD_TEXT", "job_description_text": "REQ_JD_TEXT", "budget": "REQ_BUDGET",
#             "applied_position_title": "LOG_APPLIED_POSITION_TITLE", "cv_filename": "LOG_CV_FILENAME", "candidate_email": "LOG_CANDIDATE_EMAIL",
#             "processing_status": "LOG_PROCESSING_STATUS", "final_outcome": "LOG_FINAL_OUTCOME", "error_details": "ERROR_DETAILS", "backend_analysis_report": "LOG_BACKEND_REPORT",
#             "associated_llm_response": "LOG_ASSOCIATED_LLM_RESPONSE", "associated_candidate_record": "LOG_ASSOCIATED_CANDIDATE_RECORD",
#             "llm_associated_log_entry": "LLM_ASSOCIATED_LOG_ENTRY", "llm_backend_analysis_report": "LLM_BACKEND_ANALYSIS_REPORT", "full_prompt_sent": "LLM_FULL_PROMPT_SENT",
#             "raw_response_received": "LLM_RAW_RESPONSE_RECEIVED", "parsing_status": "LLM_PARSING_STATUS", "cand_name": "CAND_NAME", "cand_company_name": "CAND_COMPANY_NAME",
#             "interview_scheduling_status": "CAND_INTERVIEW_STATUS", "cand_interview_status": "CAND_INTERVIEW_STATUS",
#         }
#         normalized_name = re.sub(r'[\s-]+', '_', field_name).lower().strip()
#         attribute_name = name_to_attr_map.get(normalized_name)
#         if attribute_name:
#             field_id = getattr(fields, attribute_name, None)
#             if field_id and field_id.startswith("fld") and not field_id.startswith("fld????"): return field_id
#         elif field_name.startswith("fld") and not field_name.startswith("fld????"): return field_name
#         return None


# # --- AirtableConnector Class (No changes needed in logic, reads from env vars) ---
# class AirtableConnector:
#     _api: Optional[Api] = None; _tables: Dict[str, Table] = {}
#     @classmethod
#     def get_api(cls) -> Api:
#         if cls._api is None:
#             if not AIRTABLE_PAT: raise ValueError("Airtable PAT missing. Check environment variables/secrets.");
#             try: cls._api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT)); logger.info(f"Airtable API client init (Timeout: {API_TIMEOUT}s).")
#             except Exception as e: logger.exception("Fatal: Airtable API client init failed."); raise ConnectionError(f"Airtable API connect error: {e}") from e
#         return cls._api
#     @classmethod
#     def get_table(cls, table_id: str) -> Table:
#         if not table_id: raise ValueError("Empty table ID.");
#         if table_id not in cls._tables:
#             if not AIRTABLE_BASE_ID: raise ValueError("Airtable Base ID missing. Check environment variables/secrets.");
#             try: api = cls.get_api(); cls._tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id); logger.info(f"Airtable Table acquired: {table_id}")
#             except Exception as e: logger.exception(f"Fatal: Failed get Airtable table '{table_id}'."); raise ConnectionError(f"Airtable table access error '{table_id}': {e}") from e
#         return cls._tables[table_id]

# # --- Generic CRUD Operations (No changes needed) ---
# def create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not table_id: logger.error("Create failed: No table_id provided."); return None
#     valid_fields = {k: v for k, v in fields_to_create.items() if k and k.startswith("fld") and v is not None}
#     if not valid_fields: logger.warning(f"Create in '{table_id}' called with no valid/non-null Field ID keys. Original keys: {list(fields_to_create.keys())}"); return None
#     try:
#         table = AirtableConnector.get_table(table_id)
#         record = table.create(valid_fields, typecast=True)
#         rec_id = record.get('id', 'N/A')
#         logger.info(f"Record created in '{table_id}' (ID: {rec_id})")
#         return record
#     except ConnectionError as ce:
#         logger.error(f"Connection error creating record in '{table_id}': {ce}")
#         return None
#     except Exception as e:
#         error_detail = str(e)
#         response_text = getattr(getattr(e, 'response', None), 'text', None)
#         error_code = getattr(e, 'status_code', None)
#         if response_text:
#             error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}"
#         logger.exception(f"Error creating record in '{table_id}'. Fields sent: {list(valid_fields.keys())}. Error: {error_detail}")
#         return None

# def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
#     if not table_id or not record_id:
#         logger.error("Get record failed: Missing table_id or record_id.")
#         return None
#     try:
#         table = AirtableConnector.get_table(table_id)
#         record = table.get(record_id)
#         logger.debug(f"Record '{record_id}' {'fetched' if record else 'not found'} from '{table_id}'.")
#         return record
#     except Exception as e:
#         logger.exception(f"Error fetching record '{record_id}' from '{table_id}'. Error: {e}")
#         return None

# def find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     if not table_id: logger.error("Find records failed: No table_id provided."); return None
#     try:
#         table = AirtableConnector.get_table(table_id)
#         sort_param = sort or []
#         records = table.all( formula=formula, fields=fields_to_fetch, max_records=max_records, sort=sort_param )
#         logger.info(f"Found {len(records)} records in '{table_id}'. Formula: '{formula or 'None'}'")
#         return records
#     except Exception as e:
#         logger.exception(f"Error finding records in '{table_id}'. Formula: {formula}. Error: {type(e).__name__}: {e}")
#         return None

# def update_record(table_id: str, record_id: str, fields_to_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not table_id or not record_id: logger.error("Update failed: No table_id or record_id provided."); return None
#     # Filter out null values before sending update, but allow empty strings/lists
#     valid_updates = {k: v for k, v in fields_to_update.items() if k and k.startswith("fld") and v is not None}
#     if not valid_updates: logger.warning(f"No valid/non-null Field IDs provided for update '{record_id}' in '{table_id}'. Original keys: {list(fields_to_update.keys())}"); return get_record(table_id, record_id) # Return current record if no valid updates
#     try:
#         table = AirtableConnector.get_table(table_id)
#         logger.debug(f"Updating record '{record_id}' in '{table_id}' with fields: {list(valid_updates.keys())}")
#         updated_record = table.update(record_id, valid_updates, typecast=True)
#         logger.info(f"Record '{record_id}' updated successfully in '{table_id}'.")
#         return updated_record
#     except Exception as e:
#         error_detail = str(e)
#         response_text = getattr(getattr(e, 'response', None), 'text', None)
#         error_code = getattr(e, 'status_code', None)
#         if response_text:
#             error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}"
#         logger.exception(f"Error updating record '{record_id}' in '{table_id}'. Updates sent: {list(valid_updates.keys())}. Error: {error_detail}")
#         return None

# def delete_record(table_id: str, record_id: str) -> bool:
#      if not table_id or not record_id: logger.error("Delete failed: No table_id or record_id provided."); return False
#      try:
#          table = AirtableConnector.get_table(table_id)
#          logger.warning(f"Attempting to delete record: '{record_id}' from table '{table_id}'")
#          result = table.delete(record_id)
#          success = result.get('deleted', False)
#          logger.info(f"Record '{record_id}' delete status from '{table_id}': {success}")
#          return success
#      except Exception as e:
#          logger.exception(f"Error deleting record '{record_id}' from '{table_id}'. Error: {e}")
#          return False

# # --- Specific Helper Functions (No changes needed) ---
# # (get_active_requirements, get_requirement_details_by_title, create_application_log, etc. remain the same)
# def get_active_requirements() -> Optional[List[Dict[str, Any]]]:
#     if not fields.REQ_STATUS: logger.error("REQ_STATUS field ID not configured."); return None
#     formula = match({fields.REQ_STATUS: "Active"})
#     fields_to_request = ["Requirement", "Location"] # Field Names used by pyairtable
#     sort_order = ["Requirement"] # Field Name used by pyairtable
#     records = find_records( REQ_TABLE_ID, formula=formula, fields_to_fetch=fields_to_request, sort=sort_order )
#     if records is None: logger.error("Failed retrieve active Requirements."); return None
#     processed_records = []
#     for record in records:
#         record_fields = record.get("fields", {}); title = record_fields.get("Requirement"); location = record_fields.get("Location"); record_id = record.get("id")
#         # Ensure essential fields exist in the response before appending
#         if record_id and title:
#             processed_records.append({"id": record_id, "title": title, "location": location})
#         else:
#             logger.warning(f"Skipping Requirement record {record_id or 'Unknown ID'} due to missing title or other essential field.")
#     logger.info(f"Processed {len(processed_records)} active Requirements for display.")
#     return processed_records

# def get_requirement_details_by_title(title: str) -> Optional[Dict[str, Any]]:
#     if not title: logger.warning("get_requirement_details_by_title called with empty title."); return None
#     if not fields.REQ_TITLE: logger.error("REQ_TITLE field ID not configured."); return None
#     formula = match({fields.REQ_TITLE: title}) # Use Field ID in formula
#     records = find_records(REQ_TABLE_ID, formula=formula, max_records=1)
#     if records is None: logger.error(f"Error fetching Requirement details for title '{title}'."); return None
#     if not records: logger.warning(f"No Requirement found with title '{title}'."); return None
#     # Check structure before returning
#     record = records[0]
#     if 'id' not in record or 'fields' not in record:
#         logger.error(f"Requirement record {record.get('id', 'Unknown ID')} is missing 'id' or 'fields'.")
#         return None
#     logger.info(f"Successfully fetched details for Requirement title '{title}' (ID: {record['id']}).")
#     return record

# def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
#     """Creates initial log. Expects field names as keys in log_data."""
#     airtable_data = {}
#     def add_if_valid(name, value):
#         field_id = fields.get_field_id(name)
#         if field_id and field_id.startswith("fld") and value is not None:
#             airtable_data[field_id] = value

#     add_if_valid("Applied Position Title", log_data.get("Applied Position Title"))
#     add_if_valid("CV Filename", log_data.get("CV Filename"))
#     add_if_valid("Candidate Email", log_data.get("Candidate Email"))
#     add_if_valid("Processing Status", log_data.get("Processing Status", "Received"))

#     if not airtable_data.get(fields.LOG_APPLIED_POSITION_TITLE) or not airtable_data.get(fields.LOG_CV_FILENAME):
#         logger.error("Cannot create log: Missing required 'Applied Position Title' or 'CV Filename' (or their Field IDs).")
#         return None

#     # Log skipped fields only if data was provided for them
#     skipped_keys = ["Candidate Name", "Company Name", "Target Location Submitted", "Current Location Submitted", "Relocation Status Submitted"]
#     skipped_data = {k: v for k, v in log_data.items() if k in skipped_keys and v is not None}
#     if skipped_data:
#         logger.info(f"Log Creation: Skipping save of these fields to Logs table (no configured Field IDs): {list(skipped_data.keys())}")

#     record = create_record(LOGS_TABLE_ID, airtable_data)
#     return record.get('id') if record else None

# def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
#     """Updates log record. Expects Field Names as keys in updates dict."""
#     if not log_record_id: logger.error("Update application log failed: No log_record_id provided."); return False
#     if not updates: logger.warning(f"Update application log called for {log_record_id} with no updates."); return True # No action needed, considered success

#     updates_with_ids = {}
#     failed_mappings = []
#     for name, value in updates.items():
#         field_id = fields.get_field_id(name)
#         if field_id and field_id.startswith("fld"):
#              # Special handling for link fields: ensure they are lists of record IDs
#              if field_id in [fields.LOG_ASSOCIATED_CANDIDATE_RECORD, fields.LOG_ASSOCIATED_LLM_RESPONSE]:
#                  if isinstance(value, str) and value.startswith("rec"):
#                      value = [value] # Convert single ID string to list
#                  elif value is None:
#                      value = [] # Allow clearing link fields by passing None -> empty list
#                  elif not isinstance(value, list):
#                      logger.warning(f"Update link field '{name}' ({field_id}) has invalid format: {value} (type: {type(value)}). Expected list, single recID string, or None. Skipping."); continue
#                  elif not all(isinstance(item, str) and item.startswith("rec") for item in value):
#                      logger.warning(f"Update link field '{name}' ({field_id}) contains non-recID items: {value}. Skipping."); continue
#              # For non-link fields, None is handled by the update_record filtering later if needed
#              updates_with_ids[field_id] = value
#         elif value is not None: # Only track as failed if mapping failed AND there was a value to update
#              failed_mappings.append(name)

#     if failed_mappings:
#         intentionally_skipped = ["Candidate Name", "Company Name", "Target Location Submitted", "Current Location Submitted", "Relocation Status Submitted"]
#         actual_failed = [f for f in failed_mappings if f not in intentionally_skipped]
#         if actual_failed:
#              logger.warning(f"Log Update ({log_record_id}): Updates skipped for unmapped fields: {actual_failed}")

#     if not updates_with_ids:
#         logger.warning(f"No valid field updates to apply for log {log_record_id} after mapping/validation."); return True # No valid updates, considered success

#     updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates_with_ids)
#     return updated_record is not None

# def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
#     """Creates Candidate record. Expects keys matching CandFields enum names."""
#     # Extract data using Enum names
#     assoc_log_list = candidate_data.get(CandFields.ASSOCIATED_LOG_ENTRY.name)
#     applied_req_list = candidate_data.get(CandFields.APPLIED_POSITION.name)
#     cand_name = candidate_data.get(CandFields.NAME.name)
#     comp_name = candidate_data.get(CandFields.COMPANY_NAME.name)
#     llm_reason = candidate_data.get(CandFields.LLM_MATCH_REASON.name)
#     interview_status = candidate_data.get(CandFields.INTERVIEW_STATUS.name, "Pending") # Default status

#     # Validation
#     def is_valid_link_list(ll):
#         return ll and isinstance(ll, list) and all(isinstance(i, str) and i.startswith("rec") for i in ll)

#     if not is_valid_link_list(assoc_log_list):
#         logger.error(f"Create Candidate failed: Invalid Associated Log Entry IDs: {assoc_log_list}")
#         return None
#     if not is_valid_link_list(applied_req_list):
#         logger.error(f"Create Candidate failed: Invalid Applied Position (Requirement) IDs: {applied_req_list}")
#         return None
#     if not cand_name or not isinstance(cand_name, str):
#         logger.error("Create Candidate failed: Missing or invalid Candidate Name.")
#         return None
#     if not comp_name or not isinstance(comp_name, str):
#         logger.error("Create Candidate failed: Missing or invalid Company Name.")
#         return None

#     # Prepare data with Field IDs
#     airtable_data = {
#         fields.CAND_ASSOCIATED_LOG_ENTRY: assoc_log_list,
#         fields.CAND_APPLIED_POSITION: applied_req_list,
#         fields.CAND_NAME: cand_name,
#         fields.CAND_COMPANY_NAME: comp_name,
#         fields.CAND_LLM_MATCH_REASON: llm_reason, # Okay if None
#         fields.CAND_INTERVIEW_STATUS: interview_status
#     }

#     # Filter out any None values before creating (create_record also does this)
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if k and v is not None}

#     # Final check on required fields using Field IDs
#     required_cand_field_ids = [fields.CAND_ASSOCIATED_LOG_ENTRY, fields.CAND_APPLIED_POSITION, fields.CAND_NAME, fields.CAND_COMPANY_NAME]
#     if not all(rf_id in airtable_data_cleaned for rf_id in required_cand_field_ids):
#         missing = [f for f in required_cand_field_ids if f not in airtable_data_cleaned]
#         logger.error(f"Create Candidate failed: Required Field IDs missing after cleaning: {missing}")
#         return None

#     record = create_record(CANDS_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# def create_llm_response_log(data: Dict[str, Any]) -> Optional[str]:
#      """Creates LLM Response log. Expects keys matching LlmRespFields enum names. Skips RESPONSE_ID."""
#      if not LLM_TABLE_ID: logger.warning("LLM Log skipped: LLM_TABLE_ID not set in environment variables/secrets."); return None

#      airtable_data = {}
#      skipped_fields = []
#      for field_enum in LlmRespFields:
#          # Skip the Auto Number RESPONSE_ID field
#          if field_enum == LlmRespFields.RESPONSE_ID:
#              continue

#          # Attempt to get Field ID using Enum name
#          field_id = getattr(fields, f"LLM_{field_enum.name}", None)

#          if field_id and field_id.startswith("fld"):
#              value = data.get(field_enum.name) # Get value using Enum name as key
#              if value is not None:
#                  # Handle link field specifically
#                  if field_id == fields.LLM_ASSOCIATED_LOG_ENTRY:
#                      if isinstance(value, str) and value.startswith("rec"):
#                          airtable_data[field_id] = [value]
#                      elif isinstance(value, list) and all(isinstance(item, str) and item.startswith("rec") for item in value):
#                          airtable_data[field_id] = value
#                      else:
#                          logger.error(f"LLM Log: Invalid Associated Log Entry format for {field_enum.name}: {value}. Expected list or single recID string. Skipping field.")
#                          skipped_fields.append(field_enum.name)
#                          continue # Skip this invalid field
#                  else:
#                      # Assign other valid, non-None values
#                      airtable_data[field_id] = value
#              # else: value is None, so we skip adding it to airtable_data (create_record handles None filtering too)
#          elif data.get(field_enum.name) is not None: # Log if mapping failed but value existed
#              logger.error(f"LLM Log: Field ID mapping failed for '{field_enum.name}'. Cannot save.")
#              skipped_fields.append(field_enum.name)

#      # Ensure the essential link field is present
#      log_entry_id_key = fields.LLM_ASSOCIATED_LOG_ENTRY
#      if not log_entry_id_key or log_entry_id_key not in airtable_data:
#           logger.error(f"LLM Log Error: Associated Log Entry (Field ID: {log_entry_id_key}) missing or invalid after mapping. Cannot create log.")
#           return None

#      if skipped_fields: logger.warning(f"LLM Log Creation: Some fields not saved due to errors or mapping issues: {skipped_fields}")
#      if len(airtable_data) == 1 and fields.LLM_ASSOCIATED_LOG_ENTRY in airtable_data:
#          logger.warning(f"LLM Log may be incomplete (only Associated Log Entry saved).")

#      record = create_record(LLM_TABLE_ID, airtable_data)
#      return record.get('id') if record else None


# # --- Admin Functions (No changes needed) ---
# # (get_admin_user_by_username, admin_find_records, etc. remain the same)
# def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
#     admin_user_field_id = fields.ADMIN_USERNAME
#     # Check if admin features are configured
#     if not ADMIN_TABLE_ID or not admin_user_field_id:
#         logger.error("Admin user lookup failed: ADMIN_TABLE_ID or ADMIN_USERNAME Field ID not configured in environment variables/secrets.")
#         return None
#     if not username:
#         logger.warning("get_admin_user called with empty username.")
#         return None

#     formula = match({admin_user_field_id: username})
#     records = find_records(ADMIN_TABLE_ID, formula=formula, max_records=1)

#     if records is None:
#         logger.error(f"Error occurred while fetching admin user '{username}'.")
#         return None
#     logger.info(f"Admin user lookup for '{username}' returned {len(records)} record(s).")
#     return records[0] if records else None

# def admin_find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     # Check if Admin Table ID is configured before allowing access via admin functions
#     if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return None
#     return find_records(table_id, formula, fields_to_fetch, max_records, sort)

# def admin_create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return None
#     return create_record(table_id, fields_to_create)

# def admin_delete_record(table_id: str, record_id: str) -> bool:
#     if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return False
#     return delete_record(table_id, record_id)

# # --- Standalone Parsing Helpers (No changes needed) ---
# def parse_locations(location_string: Optional[str]) -> List[str]:
#     if not location_string or not isinstance(location_string, str): return []
#     delimiters = re.compile(r'[;,]')
#     return [loc.strip() for loc in delimiters.split(location_string) if loc.strip()]

# def parse_budget(budget_raw: Any) -> Tuple[bool, Optional[float]]:
#     is_flexible = False; budget_value = None; FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open"]
#     if isinstance(budget_raw, str):
#         if any(keyword in budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS): is_flexible = True
#         else:
#             try: cleaned = re.sub(r'[^\d\.\-]', '', budget_raw.replace(',', '')); budget_value = float(cleaned) if cleaned else None
#             except (ValueError, TypeError): logger.warning(f"Could not parse budget string: '{budget_raw}'")
#     elif isinstance(budget_raw, (int, float)): budget_value = float(budget_raw)
#     return is_flexible, budget_value

# def parse_experience(exp_raw: Any) -> Optional[float]:
#      if isinstance(exp_raw, (int, float)): return float(exp_raw)
#      elif isinstance(exp_raw, str):
#           try: cleaned = re.sub(r'[^\d\.\-]', '', exp_raw); return float(cleaned) if cleaned else None
#           except ValueError: pass
#      logger.warning(f"Could not parse experience value: {exp_raw} (type: {type(exp_raw)})"); return None

# # --- Exports for Admin Portal (No changes needed) ---
# # These directly expose the loaded table IDs
# LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID; CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID; ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID; JD_TABLE_ID_FOR_ADMIN = REQ_TABLE_ID; LLM_TABLE_ID_FOR_ADMIN = LLM_TABLE_ID






















# backend/airtable_client.py

import os
import logging
import re
from pyairtable import Api, Table
from pyairtable.formulas import match
# REMOVED: from dotenv import load_dotenv (will be imported conditionally)
from typing import List, Dict, Any, Optional, Tuple, Type
from enum import Enum

# --- Conditional dotenv Loading ---
# Check if running in a deployed environment like Streamlit Cloud
# Streamlit Cloud typically sets specific env vars. Use one as a flag.
# If not set, assume local development and try to load .env
IS_DEPLOYED_ENV = os.getenv('STREAMLIT_SERVER_ENABLE_STATIC_SERVING') == 'true'

if not IS_DEPLOYED_ENV:
    try:
        # Import dotenv only if needed for local dev
        from dotenv import load_dotenv
        # print("DEBUG: Local environment detected. Attempting to load .env...") # Optional debug
        # Try to load .env from the default location (usually project root)
        # load_dotenv will not override existing environment variables
        if load_dotenv():
            # print("DEBUG: .env file loaded successfully.") # Optional debug
            pass
        else:
            # print("DEBUG: .env file not found or empty.") # Optional debug
            pass
    except ImportError:
        # print("DEBUG: python-dotenv not installed, skipping .env load.") # Optional debug
        pass # dotenv not installed, proceed without it
else:
    # print("DEBUG: Deployed environment detected. Skipping .env load.") # Optional debug
    pass
# --- End Conditional Loading ---


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Helper function to clean environment variables ---
def get_clean_env_var(var_name: str) -> str:
    """Gets env var, removes inline comments, and strips whitespace."""
    # Now reads directly from environment (set by OS, Docker, Streamlit Secrets, or loaded by dotenv locally)
    value = os.getenv(var_name, "")
    value = value.split('#', 1)[0] # Remove potential inline comments
    return value.strip() # Strip leading/trailing whitespace

# --- Configuration (Using Cleaner Helper) ---
# These os.getenv calls will now work both locally (via dotenv) and remotely (via Streamlit Secrets)
AIRTABLE_PAT = get_clean_env_var("AIRTABLE_PAT")
AIRTABLE_BASE_ID = get_clean_env_var("AIRTABLE_BASE_ID")
API_TIMEOUT = int(get_clean_env_var("AIRTABLE_API_TIMEOUT") or 30)

REQ_TABLE_ID = get_clean_env_var("AIRTABLE_JD_TABLE_ID")
LOGS_TABLE_ID = get_clean_env_var("AIRTABLE_LOGS_TABLE_ID")
LLM_TABLE_ID = get_clean_env_var("AIRTABLE_LLM_TABLE_ID")
CANDS_TABLE_ID = get_clean_env_var("AIRTABLE_CANDS_TABLE_ID")
ADMIN_TABLE_ID = get_clean_env_var("AIRTABLE_ADMIN_TABLE_ID")

# Load other necessary secrets directly from environment
GOOGLE_API_KEY = get_clean_env_var("GOOGLE_API_KEY")
ADMIN_PASSWORD_SALT = get_clean_env_var("ADMIN_PASSWORD_SALT")

# --- Validation (After Cleaning) ---
# Updated error messages to refer to environment variables/secrets
# These checks run at import time, failing fast if critical secrets are missing
if not AIRTABLE_PAT: raise ValueError("AIRTABLE_PAT missing. Check environment variables/secrets.")
if not AIRTABLE_BASE_ID: raise ValueError("AIRTABLE_BASE_ID missing. Check environment variables/secrets.")
if not GOOGLE_API_KEY: raise ValueError("GOOGLE_API_KEY missing. Check environment variables/secrets.")
# Check other required secrets (ensure they are loaded before this point)
if not REQ_TABLE_ID: raise ValueError("AIRTABLE_JD_TABLE_ID missing. Check environment variables/secrets.")
if not LOGS_TABLE_ID: raise ValueError("AIRTABLE_LOGS_TABLE_ID missing. Check environment variables/secrets.")
if not CANDS_TABLE_ID: raise ValueError("AIRTABLE_CANDS_TABLE_ID missing. Check environment variables/secrets.")
if not ADMIN_PASSWORD_SALT: raise ValueError("ADMIN_PASSWORD_SALT missing. Check environment variables/secrets.")

# Optional tables checks (warnings only)
required_tables = {"Requirements": REQ_TABLE_ID, "Logs": LOGS_TABLE_ID, "Candidates": CANDS_TABLE_ID} # Removed LLM table from here
missing_or_invalid_tables = [name for name, tid in required_tables.items() if not tid or not tid.startswith("tbl")]
if missing_or_invalid_tables:
    # This check might be redundant given the specific checks above, but kept for structure
    raise ValueError(f"Required Airtable Table IDs missing or invalid. Check environment variables/secrets: {', '.join(missing_or_invalid_tables)}")

if not LLM_TABLE_ID or not LLM_TABLE_ID.startswith("tbl"):
    logger.warning("LLM_TABLE_ID invalid or not set in environment variables/secrets. LLM Response logging will fail.")
if not ADMIN_TABLE_ID or not ADMIN_TABLE_ID.startswith("tbl"):
    logger.warning("ADMIN_TABLE_ID invalid or not set in environment variables/secrets. Admin functions might fail.")


# --- Field ID Management (No changes needed in this section) ---
class FieldIdEnum(Enum):
    def __str__(self): return str(self.value)

class ReqFields(FieldIdEnum): # Client Requirements (tblUviQXKrL3TUuus)
    REQUIREMENT_TITLE = "fldf4apw7f4y4s0Zy"; CLIENT = "fldlaY7OwUCXHXGfx"; TECH_SKILLS = "fld5UG3kXtMZnQ7Ds"; STATUS = "fldOvvFgl7ghEGaQu"; LOCATION = "fldCnohrYlA4cKhYN"; JD_TEXT = "fldPkWJKJ6sVwt9NV"; MIN_EXPERIENCE = "fld4ZG4X7O1yXGsu8"; BUDGET = "fldmhLvi8ZVFRN1zq"; DEADLINE = "fld5SBPcybPQbHu3Y"; PRIORITY = "fldiiIVfOS1MFxncE"; SPOC = "fldlJZnO1t0l9ozEM"; NOTES = "fldQFsgSPDkxlULet"; JD_LINK = "fldiysXPGqj5f1in6"; SUCCESSFUL_CANDIDATES_LINK = "fldjR2qwag27Vjelv"

class LogFields(FieldIdEnum): # Application Logs (tbljEEl3ybgchxK6w)
    LOG_ID = "fldLE9gd2n8ufyRP6"; APPLIED_POSITION_TITLE = "fldk6gqvdEkEc7r9F"; CV_FILENAME = "fldbpuzhA5WVJLnah"; CANDIDATE_EMAIL = "fldOWPXAbZq6itM1q"; PROCESSING_STATUS = "fldskHsD0nAykgIZW"; FINAL_OUTCOME = "fldjJfTep86DzRmub"; BACKEND_ANALYSIS_REPORT = "fldh4Pv1usXr5dxO6"; ERROR_DETAILS = "fldb7Hjd7BkBI8kPV"; ASSOCIATED_LLM_RESPONSE = "fld3VaKWJGu9hJdWq"; ASSOCIATED_CANDIDATE_RECORD = "fldugqwAmk623hC0G"

class LlmRespFields(FieldIdEnum): # LLM Responses (tblM5foLOcBIgSdRB)
    RESPONSE_ID = "fldnNi9LqCXKn3YLv"; ASSOCIATED_LOG_ENTRY = "fldzyxo4kHTgrxzoo"; BACKEND_ANALYSIS_REPORT = "fldLFZpSRFFJjqqUu"; FULL_PROMPT_SENT = "fldx8jyCuhqrjzaxG"; RAW_RESPONSE_RECEIVED = "fldJUBSWKi5waAky4"; PARSING_STATUS = "fldMg8wx22Yzkcx1t"

class CandFields(FieldIdEnum): # Successful Candidates (tbl1RYRfDafP5vO9O)
    NAME = "fld6w5Z4tbrUxRT1m"; COMPANY_NAME = "fldRZ7nBj9GJVR5wK"; ASSOCIATED_LOG_ENTRY = "fldhOdTPV4QvA5DbE"; APPLIED_POSITION = "fldkaE74Z2LtsgAN9"; LLM_MATCH_REASON = "fld7XOs2Zu7mVBdmL"; INTERVIEW_STATUS = "fldPS2HzfkL0EbpbY"
    UNIQUE_GENERATED_ID = "fldGt1Yl4tszUGuQo" # Added this line

class AdminFields(FieldIdEnum): # Admin Users (ID from env vars/secrets)
     USERNAME = "fld???????????????" # Placeholder - Replace with actual ID if using admin features
     PASSWORD_HASH = "fld???????????????" # Placeholder - Replace with actual ID if using admin features

# --- `fields` class definition (No changes needed in this section) ---
class fields:
    """Provides string access to Field IDs via class attributes. Returns None if not defined."""
    REQ_TITLE = str(ReqFields.REQUIREMENT_TITLE.value); REQ_LOCATION = str(ReqFields.LOCATION.value); REQ_MIN_EXPERIENCE = str(ReqFields.MIN_EXPERIENCE.value); REQ_STATUS = str(ReqFields.STATUS.value); REQ_JD_TEXT = str(ReqFields.JD_TEXT.value); REQ_BUDGET = str(ReqFields.BUDGET.value)
    LOG_APPLIED_POSITION_TITLE = str(LogFields.APPLIED_POSITION_TITLE.value); LOG_CV_FILENAME = str(LogFields.CV_FILENAME.value)
    LOG_CANDIDATE_EMAIL = str(LogFields.CANDIDATE_EMAIL.value); LOG_PROCESSING_STATUS = str(LogFields.PROCESSING_STATUS.value); LOG_FINAL_OUTCOME = str(LogFields.FINAL_OUTCOME.value); ERROR_DETAILS = str(LogFields.ERROR_DETAILS.value); LOG_BACKEND_REPORT = str(LogFields.BACKEND_ANALYSIS_REPORT.value); LOG_ASSOCIATED_LLM_RESPONSE = str(LogFields.ASSOCIATED_LLM_RESPONSE.value); LOG_ASSOCIATED_CANDIDATE_RECORD = str(LogFields.ASSOCIATED_CANDIDATE_RECORD.value)
    LLM_ASSOCIATED_LOG_ENTRY = str(LlmRespFields.ASSOCIATED_LOG_ENTRY.value) if LLM_TABLE_ID else None; LLM_BACKEND_ANALYSIS_REPORT = str(LlmRespFields.BACKEND_ANALYSIS_REPORT.value) if LLM_TABLE_ID else None; LLM_FULL_PROMPT_SENT = str(LlmRespFields.FULL_PROMPT_SENT.value) if LLM_TABLE_ID else None; LLM_RAW_RESPONSE_RECEIVED = str(LlmRespFields.RAW_RESPONSE_RECEIVED.value) if LLM_TABLE_ID else None; LLM_PARSING_STATUS = str(LlmRespFields.PARSING_STATUS.value) if LLM_TABLE_ID else None
    CAND_NAME = str(CandFields.NAME.value); CAND_COMPANY_NAME = str(CandFields.COMPANY_NAME.value); CAND_ASSOCIATED_LOG_ENTRY = str(CandFields.ASSOCIATED_LOG_ENTRY.value); CAND_APPLIED_POSITION = str(CandFields.APPLIED_POSITION.value); CAND_LLM_MATCH_REASON = str(CandFields.LLM_MATCH_REASON.value); CAND_INTERVIEW_STATUS = str(CandFields.INTERVIEW_STATUS.value)
    CAND_UNIQUE_GENERATED_ID = str(CandFields.UNIQUE_GENERATED_ID.value) # Added this line
    ADMIN_USERNAME = str(AdminFields.USERNAME.value) if ADMIN_TABLE_ID and hasattr(AdminFields, 'USERNAME') and not AdminFields.USERNAME.value.startswith("fld????") else None
    ADMIN_PASSWORD_HASH = str(AdminFields.PASSWORD_HASH.value) if ADMIN_TABLE_ID and hasattr(AdminFields, 'PASSWORD_HASH') and not AdminFields.PASSWORD_HASH.value.startswith("fld????") else None

    @staticmethod
    def get_field_id(field_name: str) -> Optional[str]:
        """Maps common field names (case-insensitive) to their Field ID strings."""
        if not isinstance(field_name, str): return None
        name_to_attr_map = {
            "requirement": "REQ_TITLE", "position_title": "REQ_TITLE", "location": "REQ_LOCATION", "minimum_experience": "REQ_MIN_EXPERIENCE",
            "minimum_experience_in_years": "REQ_MIN_EXPERIENCE", "status": "REQ_STATUS", "jd_in_text": "REQ_JD_TEXT", "job_description_text": "REQ_JD_TEXT", "budget": "REQ_BUDGET",
            "applied_position_title": "LOG_APPLIED_POSITION_TITLE", "cv_filename": "LOG_CV_FILENAME", "candidate_email": "LOG_CANDIDATE_EMAIL",
            "processing_status": "LOG_PROCESSING_STATUS", "final_outcome": "LOG_FINAL_OUTCOME", "error_details": "ERROR_DETAILS", "backend_analysis_report": "LOG_BACKEND_REPORT",
            "associated_llm_response": "LOG_ASSOCIATED_LLM_RESPONSE", "associated_candidate_record": "LOG_ASSOCIATED_CANDIDATE_RECORD",
            "llm_associated_log_entry": "LLM_ASSOCIATED_LOG_ENTRY", "llm_backend_analysis_report": "LLM_BACKEND_ANALYSIS_REPORT", "full_prompt_sent": "LLM_FULL_PROMPT_SENT",
            "raw_response_received": "LLM_RAW_RESPONSE_RECEIVED", "parsing_status": "LLM_PARSING_STATUS", "cand_name": "CAND_NAME", "cand_company_name": "CAND_COMPANY_NAME",
            "interview_scheduling_status": "CAND_INTERVIEW_STATUS", "cand_interview_status": "CAND_INTERVIEW_STATUS",
            # No need to add CAND_UNIQUE_GENERATED_ID here as it's typically not referred to by common name
        }
        normalized_name = re.sub(r'[\s-]+', '_', field_name).lower().strip()
        attribute_name = name_to_attr_map.get(normalized_name)
        if attribute_name:
            field_id = getattr(fields, attribute_name, None)
            if field_id and field_id.startswith("fld") and not field_id.startswith("fld????"): return field_id
        elif field_name.startswith("fld") and not field_name.startswith("fld????"): return field_name
        return None


# --- AirtableConnector Class (No changes needed in logic, reads from env vars) ---
class AirtableConnector:
    _api: Optional[Api] = None; _tables: Dict[str, Table] = {}
    @classmethod
    def get_api(cls) -> Api:
        if cls._api is None:
            if not AIRTABLE_PAT: raise ValueError("Airtable PAT missing. Check environment variables/secrets.");
            try: cls._api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT)); logger.info(f"Airtable API client init (Timeout: {API_TIMEOUT}s).")
            except Exception as e: logger.exception("Fatal: Airtable API client init failed."); raise ConnectionError(f"Airtable API connect error: {e}") from e
        return cls._api
    @classmethod
    def get_table(cls, table_id: str) -> Table:
        if not table_id: raise ValueError("Empty table ID.");
        if table_id not in cls._tables:
            if not AIRTABLE_BASE_ID: raise ValueError("Airtable Base ID missing. Check environment variables/secrets.");
            try: api = cls.get_api(); cls._tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id); logger.info(f"Airtable Table acquired: {table_id}")
            except Exception as e: logger.exception(f"Fatal: Failed get Airtable table '{table_id}'."); raise ConnectionError(f"Airtable table access error '{table_id}': {e}") from e
        return cls._tables[table_id]

# --- Generic CRUD Operations (No changes needed) ---
def create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not table_id: logger.error("Create failed: No table_id provided."); return None
    valid_fields = {k: v for k, v in fields_to_create.items() if k and k.startswith("fld") and v is not None}
    if not valid_fields: logger.warning(f"Create in '{table_id}' called with no valid/non-null Field ID keys. Original keys: {list(fields_to_create.keys())}"); return None
    try:
        table = AirtableConnector.get_table(table_id)
        record = table.create(valid_fields, typecast=True)
        rec_id = record.get('id', 'N/A')
        logger.info(f"Record created in '{table_id}' (ID: {rec_id})")
        return record
    except ConnectionError as ce:
        logger.error(f"Connection error creating record in '{table_id}': {ce}")
        return None
    except Exception as e:
        error_detail = str(e)
        response_text = getattr(getattr(e, 'response', None), 'text', None)
        error_code = getattr(e, 'status_code', None)
        if response_text:
            error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}"
        logger.exception(f"Error creating record in '{table_id}'. Fields sent: {list(valid_fields.keys())}. Error: {error_detail}")
        return None

def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
    if not table_id or not record_id:
        logger.error("Get record failed: Missing table_id or record_id.")
        return None
    try:
        table = AirtableConnector.get_table(table_id)
        record = table.get(record_id)
        logger.debug(f"Record '{record_id}' {'fetched' if record else 'not found'} from '{table_id}'.")
        return record
    except Exception as e:
        logger.exception(f"Error fetching record '{record_id}' from '{table_id}'. Error: {e}")
        return None

def find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
    if not table_id: logger.error("Find records failed: No table_id provided."); return None
    try:
        table = AirtableConnector.get_table(table_id)
        sort_param = sort or []
        records = table.all( formula=formula, fields=fields_to_fetch, max_records=max_records, sort=sort_param )
        logger.info(f"Found {len(records)} records in '{table_id}'. Formula: '{formula or 'None'}'")
        return records
    except Exception as e:
        logger.exception(f"Error finding records in '{table_id}'. Formula: {formula}. Error: {type(e).__name__}: {e}")
        return None

def update_record(table_id: str, record_id: str, fields_to_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not table_id or not record_id: logger.error("Update failed: No table_id or record_id provided."); return None
    # Filter out null values before sending update, but allow empty strings/lists
    valid_updates = {k: v for k, v in fields_to_update.items() if k and k.startswith("fld") and v is not None}
    if not valid_updates: logger.warning(f"No valid/non-null Field IDs provided for update '{record_id}' in '{table_id}'. Original keys: {list(fields_to_update.keys())}"); return get_record(table_id, record_id) # Return current record if no valid updates
    try:
        table = AirtableConnector.get_table(table_id)
        logger.debug(f"Updating record '{record_id}' in '{table_id}' with fields: {list(valid_updates.keys())}")
        updated_record = table.update(record_id, valid_updates, typecast=True)
        logger.info(f"Record '{record_id}' updated successfully in '{table_id}'.")
        return updated_record
    except Exception as e:
        error_detail = str(e)
        response_text = getattr(getattr(e, 'response', None), 'text', None)
        error_code = getattr(e, 'status_code', None)
        if response_text:
            error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}"
        logger.exception(f"Error updating record '{record_id}' in '{table_id}'. Updates sent: {list(valid_updates.keys())}. Error: {error_detail}")
        return None

def delete_record(table_id: str, record_id: str) -> bool:
     if not table_id or not record_id: logger.error("Delete failed: No table_id or record_id provided."); return False
     try:
         table = AirtableConnector.get_table(table_id)
         logger.warning(f"Attempting to delete record: '{record_id}' from table '{table_id}'")
         result = table.delete(record_id)
         success = result.get('deleted', False)
         logger.info(f"Record '{record_id}' delete status from '{table_id}': {success}")
         return success
     except Exception as e:
         logger.exception(f"Error deleting record '{record_id}' from '{table_id}'. Error: {e}")
         return False

# --- Specific Helper Functions (No changes needed) ---
# (get_active_requirements, get_requirement_details_by_title, create_application_log, etc. remain the same)
def get_active_requirements() -> Optional[List[Dict[str, Any]]]:
    if not fields.REQ_STATUS: logger.error("REQ_STATUS field ID not configured."); return None
    formula = match({fields.REQ_STATUS: "Active"})
    fields_to_request = ["Requirement", "Location"] # Field Names used by pyairtable
    sort_order = ["Requirement"] # Field Name used by pyairtable
    records = find_records( REQ_TABLE_ID, formula=formula, fields_to_fetch=fields_to_request, sort=sort_order )
    if records is None: logger.error("Failed retrieve active Requirements."); return None
    processed_records = []
    for record in records:
        record_fields = record.get("fields", {}); title = record_fields.get("Requirement"); location = record_fields.get("Location"); record_id = record.get("id")
        # Ensure essential fields exist in the response before appending
        if record_id and title:
            processed_records.append({"id": record_id, "title": title, "location": location})
        else:
            logger.warning(f"Skipping Requirement record {record_id or 'Unknown ID'} due to missing title or other essential field.")
    logger.info(f"Processed {len(processed_records)} active Requirements for display.")
    return processed_records

def get_requirement_details_by_title(title: str) -> Optional[Dict[str, Any]]:
    if not title: logger.warning("get_requirement_details_by_title called with empty title."); return None
    if not fields.REQ_TITLE: logger.error("REQ_TITLE field ID not configured."); return None
    formula = match({fields.REQ_TITLE: title}) # Use Field ID in formula
    records = find_records(REQ_TABLE_ID, formula=formula, max_records=1)
    if records is None: logger.error(f"Error fetching Requirement details for title '{title}'."); return None
    if not records: logger.warning(f"No Requirement found with title '{title}'."); return None
    # Check structure before returning
    record = records[0]
    if 'id' not in record or 'fields' not in record:
        logger.error(f"Requirement record {record.get('id', 'Unknown ID')} is missing 'id' or 'fields'.")
        return None
    logger.info(f"Successfully fetched details for Requirement title '{title}' (ID: {record['id']}).")
    return record

def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
    """Creates initial log. Expects field names as keys in log_data."""
    airtable_data = {}
    def add_if_valid(name, value):
        field_id = fields.get_field_id(name)
        if field_id and field_id.startswith("fld") and value is not None:
            airtable_data[field_id] = value

    add_if_valid("Applied Position Title", log_data.get("Applied Position Title"))
    add_if_valid("CV Filename", log_data.get("CV Filename"))
    add_if_valid("Candidate Email", log_data.get("Candidate Email"))
    add_if_valid("Processing Status", log_data.get("Processing Status", "Received"))

    if not airtable_data.get(fields.LOG_APPLIED_POSITION_TITLE) or not airtable_data.get(fields.LOG_CV_FILENAME):
        logger.error("Cannot create log: Missing required 'Applied Position Title' or 'CV Filename' (or their Field IDs).")
        return None

    # Log skipped fields only if data was provided for them
    skipped_keys = ["Candidate Name", "Company Name", "Target Location Submitted", "Current Location Submitted", "Relocation Status Submitted"]
    skipped_data = {k: v for k, v in log_data.items() if k in skipped_keys and v is not None}
    if skipped_data:
        logger.info(f"Log Creation: Skipping save of these fields to Logs table (no configured Field IDs): {list(skipped_data.keys())}")

    record = create_record(LOGS_TABLE_ID, airtable_data)
    return record.get('id') if record else None

def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
    """Updates log record. Expects Field Names as keys in updates dict."""
    if not log_record_id: logger.error("Update application log failed: No log_record_id provided."); return False
    if not updates: logger.warning(f"Update application log called for {log_record_id} with no updates."); return True # No action needed, considered success

    updates_with_ids = {}
    failed_mappings = []
    for name, value in updates.items():
        field_id = fields.get_field_id(name)
        if field_id and field_id.startswith("fld"):
             # Special handling for link fields: ensure they are lists of record IDs
             if field_id in [fields.LOG_ASSOCIATED_CANDIDATE_RECORD, fields.LOG_ASSOCIATED_LLM_RESPONSE]:
                 if isinstance(value, str) and value.startswith("rec"):
                     value = [value] # Convert single ID string to list
                 elif value is None:
                     value = [] # Allow clearing link fields by passing None -> empty list
                 elif not isinstance(value, list):
                     logger.warning(f"Update link field '{name}' ({field_id}) has invalid format: {value} (type: {type(value)}). Expected list, single recID string, or None. Skipping."); continue
                 elif not all(isinstance(item, str) and item.startswith("rec") for item in value):
                     logger.warning(f"Update link field '{name}' ({field_id}) contains non-recID items: {value}. Skipping."); continue
             # For non-link fields, None is handled by the update_record filtering later if needed
             updates_with_ids[field_id] = value
        elif value is not None: # Only track as failed if mapping failed AND there was a value to update
             failed_mappings.append(name)

    if failed_mappings:
        intentionally_skipped = ["Candidate Name", "Company Name", "Target Location Submitted", "Current Location Submitted", "Relocation Status Submitted"]
        actual_failed = [f for f in failed_mappings if f not in intentionally_skipped]
        if actual_failed:
             logger.warning(f"Log Update ({log_record_id}): Updates skipped for unmapped fields: {actual_failed}")

    if not updates_with_ids:
        logger.warning(f"No valid field updates to apply for log {log_record_id} after mapping/validation."); return True # No valid updates, considered success

    updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates_with_ids)
    return updated_record is not None

def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
    """Creates Candidate record. Expects keys matching CandFields enum names."""
    # Extract data using Enum names
    assoc_log_list = candidate_data.get(CandFields.ASSOCIATED_LOG_ENTRY.name)
    applied_req_list = candidate_data.get(CandFields.APPLIED_POSITION.name)
    cand_name = candidate_data.get(CandFields.NAME.name)
    comp_name = candidate_data.get(CandFields.COMPANY_NAME.name)
    llm_reason = candidate_data.get(CandFields.LLM_MATCH_REASON.name)
    interview_status = candidate_data.get(CandFields.INTERVIEW_STATUS.name, "Pending") # Default status
    # Note: UNIQUE_GENERATED_ID is not expected in candidate_data here, it's set after creation

    # Validation
    def is_valid_link_list(ll):
        return ll and isinstance(ll, list) and all(isinstance(i, str) and i.startswith("rec") for i in ll)

    if not is_valid_link_list(assoc_log_list):
        logger.error(f"Create Candidate failed: Invalid Associated Log Entry IDs: {assoc_log_list}")
        return None
    if not is_valid_link_list(applied_req_list):
        logger.error(f"Create Candidate failed: Invalid Applied Position (Requirement) IDs: {applied_req_list}")
        return None
    if not cand_name or not isinstance(cand_name, str):
        logger.error("Create Candidate failed: Missing or invalid Candidate Name.")
        return None
    if not comp_name or not isinstance(comp_name, str):
        logger.error("Create Candidate failed: Missing or invalid Company Name.")
        return None

    # Prepare data with Field IDs
    airtable_data = {
        fields.CAND_ASSOCIATED_LOG_ENTRY: assoc_log_list,
        fields.CAND_APPLIED_POSITION: applied_req_list,
        fields.CAND_NAME: cand_name,
        fields.CAND_COMPANY_NAME: comp_name,
        fields.CAND_LLM_MATCH_REASON: llm_reason, # Okay if None
        fields.CAND_INTERVIEW_STATUS: interview_status
        # UNIQUE_GENERATED_ID is NOT set here
    }

    # Filter out any None values before creating (create_record also does this)
    airtable_data_cleaned = {k: v for k, v in airtable_data.items() if k and v is not None}

    # Final check on required fields using Field IDs
    required_cand_field_ids = [fields.CAND_ASSOCIATED_LOG_ENTRY, fields.CAND_APPLIED_POSITION, fields.CAND_NAME, fields.CAND_COMPANY_NAME]
    if not all(rf_id in airtable_data_cleaned for rf_id in required_cand_field_ids):
        missing = [f for f in required_cand_field_ids if f not in airtable_data_cleaned]
        logger.error(f"Create Candidate failed: Required Field IDs missing after cleaning: {missing}")
        return None

    record = create_record(CANDS_TABLE_ID, airtable_data_cleaned)
    return record.get('id') if record else None

def create_llm_response_log(data: Dict[str, Any]) -> Optional[str]:
     """Creates LLM Response log. Expects keys matching LlmRespFields enum names. Skips RESPONSE_ID."""
     if not LLM_TABLE_ID: logger.warning("LLM Log skipped: LLM_TABLE_ID not set in environment variables/secrets."); return None

     airtable_data = {}
     skipped_fields = []
     for field_enum in LlmRespFields:
         # Skip the Auto Number RESPONSE_ID field
         if field_enum == LlmRespFields.RESPONSE_ID:
             continue

         # Attempt to get Field ID using Enum name
         field_id = getattr(fields, f"LLM_{field_enum.name}", None)

         if field_id and field_id.startswith("fld"):
             value = data.get(field_enum.name) # Get value using Enum name as key
             if value is not None:
                 # Handle link field specifically
                 if field_id == fields.LLM_ASSOCIATED_LOG_ENTRY:
                     if isinstance(value, str) and value.startswith("rec"):
                         airtable_data[field_id] = [value]
                     elif isinstance(value, list) and all(isinstance(item, str) and item.startswith("rec") for item in value):
                         airtable_data[field_id] = value
                     else:
                         logger.error(f"LLM Log: Invalid Associated Log Entry format for {field_enum.name}: {value}. Expected list or single recID string. Skipping field.")
                         skipped_fields.append(field_enum.name)
                         continue # Skip this invalid field
                 else:
                     # Assign other valid, non-None values
                     airtable_data[field_id] = value
             # else: value is None, so we skip adding it to airtable_data (create_record handles None filtering too)
         elif data.get(field_enum.name) is not None: # Log if mapping failed but value existed
             logger.error(f"LLM Log: Field ID mapping failed for '{field_enum.name}'. Cannot save.")
             skipped_fields.append(field_enum.name)

     # Ensure the essential link field is present
     log_entry_id_key = fields.LLM_ASSOCIATED_LOG_ENTRY
     if not log_entry_id_key or log_entry_id_key not in airtable_data:
          logger.error(f"LLM Log Error: Associated Log Entry (Field ID: {log_entry_id_key}) missing or invalid after mapping. Cannot create log.")
          return None

     if skipped_fields: logger.warning(f"LLM Log Creation: Some fields not saved due to errors or mapping issues: {skipped_fields}")
     if len(airtable_data) == 1 and fields.LLM_ASSOCIATED_LOG_ENTRY in airtable_data:
         logger.warning(f"LLM Log may be incomplete (only Associated Log Entry saved).")

     record = create_record(LLM_TABLE_ID, airtable_data)
     return record.get('id') if record else None


# --- Admin Functions (No changes needed) ---
# (get_admin_user_by_username, admin_find_records, etc. remain the same)
def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    admin_user_field_id = fields.ADMIN_USERNAME
    # Check if admin features are configured
    if not ADMIN_TABLE_ID or not admin_user_field_id:
        logger.error("Admin user lookup failed: ADMIN_TABLE_ID or ADMIN_USERNAME Field ID not configured in environment variables/secrets.")
        return None
    if not username:
        logger.warning("get_admin_user called with empty username.")
        return None

    formula = match({admin_user_field_id: username})
    records = find_records(ADMIN_TABLE_ID, formula=formula, max_records=1)

    if records is None:
        logger.error(f"Error occurred while fetching admin user '{username}'.")
        return None
    logger.info(f"Admin user lookup for '{username}' returned {len(records)} record(s).")
    return records[0] if records else None

def admin_find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
    # Check if Admin Table ID is configured before allowing access via admin functions
    if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return None
    return find_records(table_id, formula, fields_to_fetch, max_records, sort)

def admin_create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return None
    return create_record(table_id, fields_to_create)

def admin_delete_record(table_id: str, record_id: str) -> bool:
    if not ADMIN_TABLE_ID: logger.error("Admin function called but ADMIN_TABLE_ID not configured."); return False
    return delete_record(table_id, record_id)

# --- Standalone Parsing Helpers (No changes needed) ---
def parse_locations(location_string: Optional[str]) -> List[str]:
    if not location_string or not isinstance(location_string, str): return []
    delimiters = re.compile(r'[;,]')
    return [loc.strip() for loc in delimiters.split(location_string) if loc.strip()]

def parse_budget(budget_raw: Any) -> Tuple[bool, Optional[float]]:
    is_flexible = False; budget_value = None; FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open"]
    if isinstance(budget_raw, str):
        if any(keyword in budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS): is_flexible = True
        else:
            try: cleaned = re.sub(r'[^\d\.\-]', '', budget_raw.replace(',', '')); budget_value = float(cleaned) if cleaned else None
            except (ValueError, TypeError): logger.warning(f"Could not parse budget string: '{budget_raw}'")
    elif isinstance(budget_raw, (int, float)): budget_value = float(budget_raw)
    return is_flexible, budget_value

def parse_experience(exp_raw: Any) -> Optional[float]:
     if isinstance(exp_raw, (int, float)): return float(exp_raw)
     elif isinstance(exp_raw, str):
          try: cleaned = re.sub(r'[^\d\.\-]', '', exp_raw); return float(cleaned) if cleaned else None
          except ValueError: pass
     logger.warning(f"Could not parse experience value: {exp_raw} (type: {type(exp_raw)})"); return None

# --- Exports for Admin Portal (No changes needed) ---
# These directly expose the loaded table IDs
LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID; CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID; ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID; JD_TABLE_ID_FOR_ADMIN = REQ_TABLE_ID; LLM_TABLE_ID_FOR_ADMIN = LLM_TABLE_ID
