# # backend/airtable_client.py

# import os
# import logging
# from pyairtable import Api, Table
# from pyairtable.formulas import match
# from dotenv import load_dotenv
# from typing import List, Dict, Any, Optional

# # Load environment variables from .env file
# load_dotenv()

# # Configure basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # --- Configuration ---
# AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
# AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
# try:
#     API_TIMEOUT = int(os.getenv("AIRTABLE_API_TIMEOUT", 30))
# except (ValueError, TypeError):
#     logger.warning("Invalid or missing AIRTABLE_API_TIMEOUT in .env, defaulting to 30 seconds.")
#     API_TIMEOUT = 30

# # Load Table IDs from Environment Variables
# JD_TABLE_ID = os.getenv("AIRTABLE_JD_TABLE_ID", "").strip()
# LOGS_TABLE_ID = os.getenv("AIRTABLE_LOGS_TABLE_ID", "").strip()
# LLM_TABLE_ID = os.getenv("AIRTABLE_LLM_TABLE_ID", "").strip()
# CANDS_TABLE_ID = os.getenv("AIRTABLE_CANDS_TABLE_ID", "").strip()
# # ADMIN_TABLE_ID = os.getenv("AIRTABLE_ADMIN_TABLE_ID", "").strip() # REMOVED

# # Validate essential configuration
# if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
#     logger.critical("Airtable PAT or Base ID not found in environment variables.")
#     raise ValueError("Airtable credentials missing. Ensure AIRTABLE_PAT and AIRTABLE_BASE_ID are set in your .env file.")
# # Removed ADMIN_TABLE_ID from validation
# if not all([JD_TABLE_ID, LOGS_TABLE_ID, LLM_TABLE_ID, CANDS_TABLE_ID]):
#     logger.critical("One or more Airtable Table IDs (JD, Logs, LLM, Cands) not found or are empty in environment variables.")
#     raise ValueError("Airtable Table IDs missing or invalid. Ensure AIRTABLE_*_TABLE_ID variables for JD, Logs, LLM, Cands are correctly set in your .env file.")

# # --- Airtable Connection Management ---
# _api: Optional[Api] = None
# _tables: Dict[str, Table] = {}

# def get_api() -> Api:
#     """Gets the cached Airtable API client, initializing if needed."""
#     global _api
#     if _api is None:
#         try:
#             _api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT))
#             logger.info(f"Airtable API client initialized (Timeout: {API_TIMEOUT}s).")
#         except Exception as e:
#             logger.exception("Fatal: Failed to initialize Airtable API client.")
#             raise ConnectionError(f"Could not connect to Airtable API: {e}") from e
#     return _api

# def get_table(table_id: str) -> Table:
#     """Gets the cached Airtable Table object BY ID, initializing if needed."""
#     if not table_id:
#         logger.error("get_table called with empty table_id.")
#         raise ValueError("Cannot get table with an empty ID.")
#     if table_id not in _tables:
#         try:
#             api = get_api()
#             _tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id)
#             logger.info(f"Airtable Table object acquired for ID: {table_id}")
#         except Exception as e:
#             logger.exception(f"Fatal: Failed to get Airtable table with ID '{table_id}'. Base ID used: '{AIRTABLE_BASE_ID}'.")
#             raise ConnectionError(f"Could not access Airtable table ID '{table_id}' within base '{AIRTABLE_BASE_ID}': {e}") from e
#     return _tables[table_id]

# # --- Generic CRUD Operations (Remain the same, use table_id) ---

# def create_record(table_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     """Creates a new record in the table specified by ID."""
#     try:
#         table = get_table(table_id)
#         logger.debug(f"Creating record in table '{table_id}' with fields: {list(fields.keys())}")
#         record = table.create(fields, typecast=True)
#         logger.info(f"Record created in table '{table_id}' (ID: {record.get('id')})")
#         return record
#     except Exception as e:
#         logger.exception(f"Error creating record in table '{table_id}'. Fields: {fields}. Error: {e}")
#         return None

# def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
#     """Retrieves a specific record by ID from the table specified by ID."""
#     try:
#         table = get_table(table_id)
#         logger.debug(f"Fetching record '{record_id}' from table '{table_id}'")
#         record = table.get(record_id)
#         if record:
#             logger.debug(f"Record '{record_id}' fetched successfully.")
#         else:
#             logger.warning(f"Record '{record_id}' not found in table '{table_id}'.")
#         return record
#     except Exception as e:
#         logger.exception(f"Error fetching record '{record_id}' from table '{table_id}'. Error: {e}")
#         return None

# def find_records(table_id: str, formula: Optional[str] = None, fields: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     """Finds records matching criteria in the table specified by ID."""
#     try:
#         table = get_table(table_id)
#         logger.debug(f"Finding records in table '{table_id}' (Formula: '{formula}', Fields: {fields}, Max: {max_records}, Sort: {sort})")
#         sort_param = sort if sort else []
#         records = table.all(formula=formula, fields=fields, max_records=max_records, sort=sort_param)
#         logger.info(f"Found {len(records)} records in table '{table_id}' matching criteria.")
#         return records
#     except Exception as e:
#         logger.exception(f"Error finding records in table '{table_id}'. Formula: {formula}. Error: {e}")
#         return None

# def update_record(table_id: str, record_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     """Updates fields of an existing record in the table specified by ID."""
#     if not fields:
#         logger.warning(f"No fields provided for update on record '{record_id}' in table '{table_id}'. Skipping.")
#         return get_record(table_id, record_id)
#     try:
#         table = get_table(table_id)
#         logger.debug(f"Updating record '{record_id}' in table '{table_id}' with fields: {list(fields.keys())}")

#         fields_to_update = fields.copy()
#         for key, value in fields.items():
#             is_link_field = (
#                 key.startswith("Associated ") or
#                 key == "Applied Position" or
#                 key.endswith(" Entry") or
#                 key.endswith(" Response") or
#                 key.endswith(" Record") or
#                 key == "Application Logs"
#             )
#             if isinstance(value, str) and value.startswith("rec") and is_link_field:
#                  logger.debug(f"Converting single record ID '{value}' to list for potential link field '{key}'.")
#                  fields_to_update[key] = [value]
#             elif isinstance(value, list):
#                  if value and not all(isinstance(item, str) and item.startswith("rec") for item in value):
#                        logger.warning(f"Field '{key}' has a list value, but not all items look like record IDs: {value}. Attempting update anyway.")

#         updated_record = table.update(record_id, fields_to_update, typecast=True)
#         logger.info(f"Record '{record_id}' updated successfully in table '{table_id}'.")
#         return updated_record
#     except Exception as e:
#         logger.exception(f"Error updating record '{record_id}' in table '{table_id}'. Updates: {fields}. Error: {e}")
#         return None

# def delete_record(table_id: str, record_id: str) -> bool:
#     """Deletes a specific record by ID from the table specified by ID."""
#     try:
#         table = get_table(table_id)
#         logger.warning(f"Attempting to delete record '{record_id}' from table '{table_id}'")
#         result = table.delete(record_id)
#         success = result.get('deleted', False)
#         if success:
#             logger.info(f"Record '{record_id}' deleted successfully from table '{table_id}'.")
#         else:
#             logger.error(f"Failed to delete record '{record_id}' from table '{table_id}' (API response: {result}).")
#         return success
#     except Exception as e:
#         logger.exception(f"Error deleting record '{record_id}' from table '{table_id}'. Error: {e}")
#         return False

# # --- Specific Helper Functions (Remain the same, use table IDs) ---

# def get_active_job_descriptions() -> Optional[List[Dict[str, Any]]]:
#     """Reads active JDs using JD_TABLE_ID."""
#     formula = match({"Status": "Active"})
#     fields_to_fetch = ["Position Title", "Client Name"]
#     sort_order = ["Client Name", "Position Title"]
#     records = find_records(JD_TABLE_ID, formula=formula, fields=fields_to_fetch, sort=sort_order)
#     if records is None:
#         logger.error("Failed to retrieve active job descriptions (find_records returned None).")
#         return None
#     processed_records = []
#     for record in records:
#         record_fields = record.get("fields", {})
#         title = record_fields.get("Position Title")
#         client = record_fields.get("Client Name")
#         if record.get("id") and title and client:
#             processed_records.append({
#                 "id": record.get("id"),
#                 "title": title,
#                 "client": client
#             })
#         else:
#              logger.warning(f"Skipping JD record {record.get('id')} due to missing title or client name.")
#     return processed_records

# def get_jd_details_by_title(title: str) -> Optional[Dict[str, Any]]:
#     """Retrieves full record for a specific JD by title using JD_TABLE_ID."""
#     if not title:
#         logger.warning("get_jd_details_by_title called with empty title.")
#         return None
#     formula = match({"Position Title": title})
#     records = find_records(JD_TABLE_ID, formula=formula, max_records=1)
#     if records is None:
#          logger.error(f"Error occurred fetching JD by title '{title}'.")
#          return None
#     return records[0] if records else None

# def get_jd_details_by_id(record_id: str) -> Optional[Dict[str, Any]]:
#     """Retrieves full record for a specific JD by ID using JD_TABLE_ID."""
#     if not record_id:
#          logger.warning("get_jd_details_by_id called with empty record_id.")
#          return None
#     return get_record(JD_TABLE_ID, record_id)

# def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
#     """Creates a new Application Log record using LOGS_TABLE_ID."""
#     airtable_data = {
#         "Applied Position Title": log_data.get("applied_position_title"),
#         "Candidate Email": log_data.get("candidate_email"),
#         "CV Filename": log_data.get("cv_filename"),
#         "Processing Status": log_data.get("processing_status", "Received")
#     }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if v is not None}
#     if not airtable_data_cleaned.get("Applied Position Title") or not airtable_data_cleaned.get("CV Filename"):
#          logger.error("Cannot create application log without Applied Position Title and CV Filename.")
#          return None
#     record = create_record(LOGS_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
#     """Updates an Application Log record using LOGS_TABLE_ID."""
#     if not log_record_id:
#          logger.error("update_application_log called with empty log_record_id.")
#          return False
#     updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates)
#     return updated_record is not None

# def create_llm_response_log(response_data: Dict[str, Any]) -> Optional[str]:
#     """Creates an LLM Response record using LLM_TABLE_ID."""
#     assoc_log_id = response_data.get("associated_log_entry_id")
#     if not assoc_log_id or not isinstance(assoc_log_id, str) or not assoc_log_id.startswith("rec"):
#          logger.error("Cannot create LLM response log without a valid Associated Log Entry ID.")
#          return None

#     airtable_data = {
#         "Associated Log Entry": [assoc_log_id],
#         "Full Prompt Sent": response_data.get("full_prompt_sent"),
#         "Raw Response Received": response_data.get("raw_response_received"),
#         "Parsing Status": response_data.get("parsing_status")
#     }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if v is not None}
#     record = create_record(LLM_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
#     """Creates a Successful Candidate record using CANDS_TABLE_ID."""
#     assoc_log_id = candidate_data.get("associated_log_entry_id")
#     applied_jd_id = candidate_data.get("applied_position_jd_id")

#     if not assoc_log_id or not isinstance(assoc_log_id, str) or not assoc_log_id.startswith("rec"):
#          logger.error("Cannot create Successful Candidate without a valid Associated Log Entry ID.")
#          return None
#     if not applied_jd_id or not isinstance(applied_jd_id, str) or not applied_jd_id.startswith("rec"):
#          logger.error("Cannot create Successful Candidate without a valid Applied Position JD ID.")
#          return None

#     airtable_data = {
#         "Associated Log Entry": [assoc_log_id],
#         "Applied Position": [applied_jd_id],
#         "Candidate Name": candidate_data.get("candidate_name"),
#         "Candidate Email": candidate_data.get("candidate_email"),
#         "LLM Match Reason": candidate_data.get("llm_match_reason"),
#         "Interview Scheduling Status": candidate_data.get("interview_scheduling_status", "Pending")
#     }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if v is not None}
#     record = create_record(CANDS_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# # --- REMOVED Admin Specific Functions ---
# # def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]: ... # REMOVED
# # def admin_find_records(...) -> Optional[List[Dict[str, Any]]]: ... # REMOVED
# # def admin_create_record(...) -> Optional[Dict[str, Any]]: ... # REMOVED
# # def admin_delete_record(...) -> bool: ... # REMOVED

# # --- REMOVED Table ID exports for Admin ---
# # LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID # REMOVED
# # LLM_TABLE_ID_FOR_ADMIN = LLM_TABLE_ID # REMOVED
# # CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID # REMOVED
# # ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID # REMOVED




# # backend/airtable_client.py

# import os
# import logging
# import re
# from pyairtable import Api, Table
# from pyairtable.formulas import match
# from dotenv import load_dotenv
# from typing import List, Dict, Any, Optional

# load_dotenv()
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # --- Configuration ---
# AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
# AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
# API_TIMEOUT = int(os.getenv("AIRTABLE_API_TIMEOUT", 30))
# JD_TABLE_ID = os.getenv("AIRTABLE_JD_TABLE_ID", "").strip()
# LOGS_TABLE_ID = os.getenv("AIRTABLE_LOGS_TABLE_ID", "").strip()
# LLM_TABLE_ID = os.getenv("AIRTABLE_LLM_TABLE_ID", "").strip() # Keep for potential LLM logs if needed
# CANDS_TABLE_ID = os.getenv("AIRTABLE_CANDS_TABLE_ID", "").strip()
# ADMIN_TABLE_ID = os.getenv("AIRTABLE_ADMIN_TABLE_ID", "").strip()

# # Validation
# if not AIRTABLE_PAT or not AIRTABLE_BASE_ID: raise ValueError("Airtable PAT/Base ID missing.")
# if not all([JD_TABLE_ID, LOGS_TABLE_ID, CANDS_TABLE_ID]): raise ValueError("Required Airtable Table IDs missing (JD, Logs, Cands).")
# # LLM_TABLE_ID is optional now based on new flow, but keep if used elsewhere
# if not LLM_TABLE_ID: logger.warning("AIRTABLE_LLM_TABLE_ID not set. LLM-specific logging might fail if attempted.") # [cite: 5]

# # --- Connection Management ---
# _api: Optional[Api] = None
# _tables: Dict[str, Table] = {}

# def get_api() -> Api:
#     """Gets the cached Airtable API client, initializing if needed."""
#     global _api
#     if _api is None:
#         try:
#             _api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT)) # [cite: 6]
#             logger.info(f"Airtable API client initialized (Timeout: {API_TIMEOUT}s).") # [cite: 6]
#         except Exception as e:
#             logger.exception("Fatal: Failed to initialize Airtable API client.")
#             raise ConnectionError(f"Could not connect to Airtable API: {e}") from e
#     return _api

# def get_table(table_id: str) -> Table:
#     """Gets the cached Airtable Table object BY ID, initializing if needed."""
#     if not table_id: raise ValueError("Cannot get table with an empty ID.") # [cite: 7]
#     if table_id not in _tables:
#         try:
#             api = get_api()
#             _tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id)
#             logger.info(f"Airtable Table object acquired for ID: {table_id}") # [cite: 7]
#         except Exception as e:
#             logger.exception(f"Fatal: Failed get Airtable table ID '{table_id}'. Base: '{AIRTABLE_BASE_ID}'.") # [cite: 8]
#             raise ConnectionError(f"Could not access Airtable table ID '{table_id}': {e}") from e # [cite: 8]
#     return _tables[table_id]

# # --- Generic CRUD Operations ---
# def create_record(table_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     try:
#         table = get_table(table_id)
#         record = table.create(fields, typecast=True)
#         logger.info(f"Record created table '{table_id}' (ID: {record.get('id')})") # [cite: 10]
#         return record # [cite: 10]
#     except Exception as e:
#         logger.exception(f"Error creating record table '{table_id}'. F:{fields}. E:{e}") # [cite: 11]
#         return None # [cite: 11]

# def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
#     try:
#         table = get_table(table_id)
#         record = table.get(record_id) # [cite: 12]
#         logger.debug(f"Record '{record_id}' fetched." if record else f"Record '{record_id}' not found.") # [cite: 12]
#         return record # [cite: 13]
#     except Exception as e:
#         logger.exception(f"Error fetching record '{record_id}' from '{table_id}'. E:{e}") # [cite: 14]
#         return None # [cite: 14]

# def find_records(table_id: str, formula: Optional[str] = None, fields: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     try:
#         table = get_table(table_id)
#         sort_param = sort or [] # [cite: 15]
#         records = table.all(formula=formula, fields=fields, max_records=max_records, sort=sort_param) # [cite: 15]
#         logger.info(f"Found {len(records)} records table '{table_id}'.") # [cite: 15]
#         return records # [cite: 16]
#     except Exception as e:
#         error_details = str(e)
#         logger.exception(f"Error finding records '{table_id}'. F:{formula}. E:{error_details}") # [cite: 17]
#         return None # [cite: 17]

# def update_record(table_id: str, record_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not fields:
#         logger.warning(f"No fields update rec '{record_id}' table '{table_id}'.") # [cite: 18]
#         return get_record(table_id, record_id) # [cite: 18]
#     try:
#         table = get_table(table_id)
#         logger.debug(f"Updating rec '{record_id}' table '{table_id}' fields: {list(fields.keys())}") # [cite: 19]
#         fields_to_update = fields.copy() # [cite: 19]
#         # Handle linked records if necessary (logic assumed from original code comment)
#         updated_record = table.update(record_id, fields_to_update, typecast=True) # [cite: 19]
#         logger.info(f"Record '{record_id}' updated table '{table_id}'.") # [cite: 19]
#         return updated_record # [cite: 20]
#     except Exception as e:
#         logger.exception(f"Error updating rec '{record_id}' table '{table_id}'. U:{fields}. E:{e}") # [cite: 21]
#         return None # [cite: 21]

# def delete_record(table_id: str, record_id: str) -> bool:
#     try:
#         table = get_table(table_id)
#         logger.warning(f"Deleting rec '{record_id}' table '{table_id}'") # [cite: 22]
#         result = table.delete(record_id) # [cite: 22]
#         success = result.get('deleted', False) # [cite: 22]
#         logger.info(f"Record '{record_id}' deleted." if success else f"Failed delete '{record_id}'.") # [cite: 22]
#         return success # [cite: 23]
#     except Exception as e:
#         logger.exception(f"Error deleting rec '{record_id}' table '{table_id}'. E:{e}") # [cite: 24]
#         return False # [cite: 24]

# # --- Specific Helper Functions ---
# def get_active_job_descriptions() -> Optional[List[Dict[str, Any]]]:
#     formula = match({"Status": "Active"})
#     # Fetch necessary fields including the experience field
#     fields_to_fetch = ["Position Title", "Location", "Budget", "Minimum experience in years"] # [cite: 25]
#     sort_order = ["Location", "Position Title"] # [cite: 25]
#     records = find_records(JD_TABLE_ID, formula=formula, fields=fields_to_fetch, sort=sort_order) # [cite: 25]
#     if records is None:
#         logger.error("Failed retrieve active JDs.") # [cite: 25]
#         return None # [cite: 25]
#     processed_records = []
#     for record in records:
#         record_fields = record.get("fields", {})
#         title = record_fields.get("Position Title")
#         if record.get("id") and title:
#             processed_records.append({
#                 "id": record.get("id"),
#                 "title": title,
#                 "location": record_fields.get("Location"), # [cite: 26]
#                 "budget": record_fields.get("Budget"), # [cite: 26]
#                 "min_experience": record_fields.get("Minimum experience in years") # Fetch min exp [cite: 26]
#             })
#         else:
#             logger.warning(f"Skipping JD {record.get('id')} missing title.")
#     logger.info(f"Processed {len(processed_records)} active JDs.")
#     return processed_records

# def get_jd_details_by_title(title: str) -> Optional[Dict[str, Any]]:
#     if not title:
#         logger.warning("get_jd_details_by_title empty title.") # [cite: 27]
#         return None # [cite: 27]
#     formula = match({"Position Title": title}) # [cite: 27]
#     # Fetches ALL fields, including "Minimum experience in years"
#     records = find_records(JD_TABLE_ID, formula=formula, max_records=1) # [cite: 28]
#     if records is None:
#         logger.error(f"Error fetching JD title '{title}'.") # [cite: 28]
#         return None # [cite: 28]
#     return records[0] if records else None

# # --- Application Log ---
# def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
#     # Log only core fields confirmed in schema
#     airtable_data = {
#         "Applied Position Title": log_data.get("applied_position_title"),
#         "CV Filename": log_data.get("cv_filename"),
#         "Candidate Email": log_data.get("candidate_email"),
#         "Processing Status": log_data.get("processing_status", "Received") # [cite: 29]
#     }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if v is not None}

#     if not airtable_data_cleaned.get("Applied Position Title") or not airtable_data_cleaned.get("CV Filename"): # [cite: 29]
#         logger.error("Cannot create log without Position Title & CV Filename.") # [cite: 29]
#         return None # [cite: 29]
#     record = create_record(LOGS_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
#     if not log_record_id:
#         logger.error("update_application_log empty log_record_id.") # [cite: 30]
#         return False # [cite: 30]
#     # Ensure field names like "Processing Status", "Final Outcome", "Error Details",
#     # "Associated Candidate Record" match schema
#     updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates) # [cite: 30]
#     return updated_record is not None

# # *** REMOVED update_log_with_backend_report function ***

# # --- Successful Candidate ---
# def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
#     assoc_log_id = candidate_data.get("associated_log_entry_id") # [cite: 34]
#     applied_jd_id = candidate_data.get("applied_position_jd_id") # [cite: 34]
#     if not assoc_log_id or not isinstance(assoc_log_id, str) or not assoc_log_id.startswith("rec"):
#         logger.error("Cannot create Candidate: Invalid Log ID.") # [cite: 35]
#         return None # [cite: 35]
#     if not applied_jd_id or not isinstance(applied_jd_id, str) or not applied_jd_id.startswith("rec"):
#         logger.error("Cannot create Candidate: Invalid JD ID.") # [cite: 36]
#         return None # [cite: 36]
#     # Ensure field names match schema
#     airtable_data = {
#         "Associated Log Entry": [assoc_log_id],
#         "Applied Position": [applied_jd_id],
#         "Candidate Name": candidate_data.get("candidate_name"),
#         "Candidate Email": candidate_data.get("candidate_email"),
#         "LLM Match Reason": candidate_data.get("llm_match_reason"), # Optional: Reason for passing prelim checks [cite: 37]
#         "Interview Scheduling Status": candidate_data.get("interview_scheduling_status", "Pending") # [cite: 37]
#     }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if v is not None} # [cite: 37]
#     record = create_record(CANDS_TABLE_ID, airtable_data_cleaned)
#     return record.get('id') if record else None

# # --- LLM Response Logging (Optional - If needed for focused calls) ---
# # No separate LLM response logging is implemented here based on previous analysis [cite: 38, 39, 40]
# def create_llm_response_log(data: Dict[str, Any]) -> Optional[str]:
#      # Placeholder if LLM_TABLE_ID is used elsewhere, but not for backend report
#      logger.warning("create_llm_response_log called, but separate LLM logging not fully implemented for backend reports.")
#      # if LLM_TABLE_ID:
#      #    return create_record(LLM_TABLE_ID, data)
#      return None


# # --- Admin Functions ---
# def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
#     if not ADMIN_TABLE_ID:
#         logger.error("Admin User lookup fail: ADMIN_TABLE_ID not set.") # [cite: 41]
#         return None # [cite: 41]
#     if not username:
#         logger.warning("get_admin_user_by_username empty username.") # [cite: 42]
#         return None # [cite: 42]
#     formula = match({"Username": username}) # [cite: 42]
#     records = find_records(ADMIN_TABLE_ID, formula=formula, max_records=1) # [cite: 43]
#     if records is None:
#         logger.error(f"Error fetch admin user '{username}'.") # [cite: 43]
#         return None # [cite: 43]
#     return records[0] if records else None

# def admin_find_records(table_id: str, formula: Optional[str] = None, fields: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     return find_records(table_id, formula, fields, max_records, sort)

# def admin_create_record(table_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     return create_record(table_id, fields)

# def admin_delete_record(table_id: str, record_id: str) -> bool:
#     return delete_record(table_id, record_id)

# # --- Exports for Admin Portal ---
# LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID
# CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID
# ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID











# # backend/airtable_client.py

# import os, logging, re
# from pyairtable import Api, Table
# from pyairtable.formulas import match
# from dotenv import load_dotenv
# from typing import List, Dict, Any, Optional, Tuple, Type
# from enum import Enum

# load_dotenv()
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # --- Configuration ---
# AIRTABLE_PAT = os.getenv("AIRTABLE_PAT"); AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID"); API_TIMEOUT = int(os.getenv("AIRTABLE_API_TIMEOUT", 30))
# JD_TABLE_ID = os.getenv("AIRTABLE_JD_TABLE_ID", "").strip(); LOGS_TABLE_ID = os.getenv("AIRTABLE_LOGS_TABLE_ID", "").strip(); LLM_TABLE_ID = os.getenv("AIRTABLE_LLM_TABLE_ID", "").strip(); CANDS_TABLE_ID = os.getenv("AIRTABLE_CANDS_TABLE_ID", "").strip(); ADMIN_TABLE_ID = os.getenv("AIRTABLE_ADMIN_TABLE_ID", "").strip()
# if not AIRTABLE_PAT or not AIRTABLE_BASE_ID: raise ValueError("Airtable PAT/Base ID missing.")
# if not all([JD_TABLE_ID, LOGS_TABLE_ID, CANDS_TABLE_ID]): raise ValueError("Required Table IDs missing (JD, Logs, Cands).")
# if not LLM_TABLE_ID: logger.warning("LLM_TABLE_ID not set. LLM Response logging might fail.")
# if not ADMIN_TABLE_ID: logger.warning("ADMIN_TABLE_ID not set. Admin functions might fail.")

# # --- Field ID Management ---
# class FieldIdEnum(Enum):
#     def __str__(self): return str(self.value)
# class JdFields(FieldIdEnum): POSITION_TITLE = "fldBRftsyQHq6lnPa"; LOCATION = "fld2R34E3V6R2bf9x"; MIN_EXPERIENCE = "fldrwDdQNYVh97l1j"; STATUS = "fldEg9wC01hlPJQPw"; DESCRIPTION_TEXT = "fldfMdA8J7lK6tVjH"; BUDGET = "fld8p5KlnDGHA8cwb"
# class LogFields(FieldIdEnum): APPLIED_POSITION_TITLE = "fldf4WN2SyiOG8QdC"; CV_FILENAME = "fldnvRSdN3UYGsYgG"; CANDIDATE_EMAIL = "fld2LeowbvMYDYGVw"; PROCESSING_STATUS = "fldcWhSfphOUU0af2"; FINAL_OUTCOME = "fldAVIxmrZ9fCBnvS"; ERROR_DETAILS = "fldsg8CrkSMaEnhse"; ASSOCIATED_LLM_RESPONSE = "fldXwS52KFi2dtiGn"; ASSOCIATED_CANDIDATE_RECORD = "fldD5bIKxiUb2JHry"; CANDIDATE_NAME = "fld???????????????"; COMPANY_NAME = "fld???????????????"; TARGET_LOCATION_SUBMITTED = "fld???????????????"; CURRENT_LOCATION_SUBMITTED = "fld???????????????"; RELOCATION_STATUS_SUBMITTED = "fld???????????????"
# class LlmRespFields(FieldIdEnum): ASSOCIATED_LOG_ENTRY = "fldWWyUKg6fEjPELr"; BACKEND_ANALYSIS_REPORT = "fldT6GWBGOvh3SbA9"; FULL_PROMPT_SENT = "fldNmJ8f4mRaxyjbH"; RAW_RESPONSE_RECEIVED = "fldjbykqqB8H1U4CV"; PARSING_STATUS = "fldvinsTvct2MbidE"
# class CandFields(FieldIdEnum): NAME = "fldq2t6vHWrqAcqD2"; COMPANY_NAME = "fldP8bLyNfT7ZI4dA"; ASSOCIATED_LOG_ENTRY = "fldzAjLqiKiV7hXsK"; APPLIED_POSITION = "fldQw38UYRNIkrknd"; LLM_MATCH_REASON = "fldUfnZQ6dCNRPTDY"; INTERVIEW_STATUS = "fldoi24VdjyWhqbVM"
# class AdminFields(FieldIdEnum): USERNAME = "fldwm7v8nGV5MdTD2"; PASSWORD_HASH = "fldRjRrnnQlA2hnpW"

# class fields:
#     """Provides string access to Field IDs via class attributes. Returns None for placeholders."""
#     JD_POSITION_TITLE = str(JdFields.POSITION_TITLE.value); JD_LOCATION = str(JdFields.LOCATION.value); JD_MIN_EXPERIENCE = str(JdFields.MIN_EXPERIENCE.value); JD_STATUS = str(JdFields.STATUS.value); JD_DESCRIPTION_TEXT = str(JdFields.DESCRIPTION_TEXT.value); JD_BUDGET = str(JdFields.BUDGET.value)
#     LOG_APPLIED_POSITION_TITLE = str(LogFields.APPLIED_POSITION_TITLE.value); LOG_CV_FILENAME = str(LogFields.CV_FILENAME.value)
#     LOG_CANDIDATE_NAME = str(LogFields.CANDIDATE_NAME.value) if hasattr(LogFields, 'CANDIDATE_NAME') and not LogFields.CANDIDATE_NAME.value.startswith("fld????") else None
#     LOG_COMPANY_NAME = str(LogFields.COMPANY_NAME.value) if hasattr(LogFields, 'COMPANY_NAME') and not LogFields.COMPANY_NAME.value.startswith("fld????") else None
#     LOG_TARGET_LOCATION = str(LogFields.TARGET_LOCATION_SUBMITTED.value) if hasattr(LogFields, 'TARGET_LOCATION_SUBMITTED') and not LogFields.TARGET_LOCATION_SUBMITTED.value.startswith("fld????") else None
#     LOG_CURRENT_LOCATION = str(LogFields.CURRENT_LOCATION_SUBMITTED.value) if hasattr(LogFields, 'CURRENT_LOCATION_SUBMITTED') and not LogFields.CURRENT_LOCATION_SUBMITTED.value.startswith("fld????") else None
#     LOG_RELOCATION_STATUS = str(LogFields.RELOCATION_STATUS_SUBMITTED.value) if hasattr(LogFields, 'RELOCATION_STATUS_SUBMITTED') and not LogFields.RELOCATION_STATUS_SUBMITTED.value.startswith("fld????") else None
#     LOG_CANDIDATE_EMAIL = str(LogFields.CANDIDATE_EMAIL.value); LOG_PROCESSING_STATUS = str(LogFields.PROCESSING_STATUS.value); LOG_FINAL_OUTCOME = str(LogFields.FINAL_OUTCOME.value); ERROR_DETAILS = str(LogFields.ERROR_DETAILS.value); LOG_ASSOCIATED_LLM_RESPONSE = str(LogFields.ASSOCIATED_LLM_RESPONSE.value); LOG_ASSOCIATED_CANDIDATE_RECORD = str(LogFields.ASSOCIATED_CANDIDATE_RECORD.value)
#     LLM_ASSOCIATED_LOG_ENTRY = str(LlmRespFields.ASSOCIATED_LOG_ENTRY.value); LLM_BACKEND_ANALYSIS_REPORT = str(LlmRespFields.BACKEND_ANALYSIS_REPORT.value); LLM_FULL_PROMPT_SENT = str(LlmRespFields.FULL_PROMPT_SENT.value); LLM_RAW_RESPONSE_RECEIVED = str(LlmRespFields.RAW_RESPONSE_RECEIVED.value); LLM_PARSING_STATUS = str(LlmRespFields.PARSING_STATUS.value)
#     CAND_NAME = str(CandFields.NAME.value); CAND_COMPANY_NAME = str(CandFields.COMPANY_NAME.value); CAND_ASSOCIATED_LOG_ENTRY = str(CandFields.ASSOCIATED_LOG_ENTRY.value); CAND_APPLIED_POSITION = str(CandFields.APPLIED_POSITION.value); CAND_LLM_MATCH_REASON = str(CandFields.LLM_MATCH_REASON.value); CAND_INTERVIEW_STATUS = str(CandFields.INTERVIEW_STATUS.value)
#     ADMIN_USERNAME = str(AdminFields.USERNAME.value); ADMIN_PASSWORD_HASH = str(AdminFields.PASSWORD_HASH.value)

#     @staticmethod
#     def get_field_id(field_name: str) -> Optional[str]:
#         """Maps common field names (case-insensitive) to their Field ID strings."""
#         if not isinstance(field_name, str): return None
#         name_to_attr_map = {
#             "applied_position_title": "LOG_APPLIED_POSITION_TITLE", "cv_filename": "LOG_CV_FILENAME",
#             "candidate_name": "LOG_CANDIDATE_NAME", "company_name": "LOG_COMPANY_NAME",
#             "target_location_submitted": "LOG_TARGET_LOCATION", "current_location_submitted": "LOG_CURRENT_LOCATION",
#             "relocation_status_submitted": "LOG_RELOCATION_STATUS", "candidate_email": "LOG_CANDIDATE_EMAIL",
#             "processing_status": "LOG_PROCESSING_STATUS", "final_outcome": "LOG_FINAL_OUTCOME",
#             "error_details": "ERROR_DETAILS", # Handles "Error details" from description
#             "associated_llm_response": "LOG_ASSOCIATED_LLM_RESPONSE",
#             "associated_candidate_record": "LOG_ASSOCIATED_CANDIDATE_RECORD",
#             # Add mappings for LLM fields if needed elsewhere, though create_llm_response_log uses direct attributes now
#             "llm_associated_log_entry": "LLM_ASSOCIATED_LOG_ENTRY",
#             "backend_analysis_report": "LLM_BACKEND_ANALYSIS_REPORT",
#             "full_prompt_sent": "LLM_FULL_PROMPT_SENT",
#             "raw_response_received": "LLM_RAW_RESPONSE_RECEIVED",
#             "parsing_status": "LLM_PARSING_STATUS",
#         }
#         normalized_name = field_name.lower().replace(" ", "_").replace("-", "_")
#         attribute_name = name_to_attr_map.get(normalized_name)
#         if attribute_name:
#             field_id = getattr(fields, attribute_name, None)
#             if field_id and field_id.startswith("fld") and not field_id.startswith("fld????"): return field_id
#         if field_name.startswith("fld") and not field_name.startswith("fld????"): return field_name
#         logger.warning(f"Could not map field name '{field_name}' (norm: '{normalized_name}') to valid Field ID.")
#         return None

# class AirtableConnector:
#     _api: Optional[Api] = None; _tables: Dict[str, Table] = {}
#     @classmethod
#     def get_api(cls) -> Api:
#         if cls._api is None:
#             if not AIRTABLE_PAT: raise ValueError("Airtable PAT missing.");
#             try: cls._api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT)); logger.info(f"Airtable API client init (Timeout: {API_TIMEOUT}s).")
#             except Exception as e: logger.exception("Fatal: Airtable API client init failed."); raise ConnectionError(f"Airtable API connect error: {e}") from e
#         return cls._api
#     @classmethod
#     def get_table(cls, table_id: str) -> Table:
#         if not table_id: raise ValueError("Empty table ID.");
#         if table_id not in cls._tables:
#             if not AIRTABLE_BASE_ID: raise ValueError("Airtable Base ID missing.");
#             try: api = cls.get_api(); cls._tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id); logger.info(f"Airtable Table acquired: {table_id}")
#             except Exception as e: logger.exception(f"Fatal: Failed get Airtable table '{table_id}'."); raise ConnectionError(f"Airtable table access error '{table_id}': {e}") from e
#         return cls._tables[table_id]

# def create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not table_id: logger.error("Create failed: No table_id."); return None
#     valid_fields = {k: v for k, v in fields_to_create.items() if k and k.startswith("fld")} # Ensure keys are valid Field IDs
#     if not valid_fields: logger.warning(f"Create in '{table_id}' with no valid Field ID keys."); return None
#     try: table = AirtableConnector.get_table(table_id); record = table.create(valid_fields, typecast=True); rec_id = record.get('id', 'N/A'); logger.info(f"Record created in '{table_id}' (ID: {rec_id})"); return record
#     except ConnectionError as ce: logger.error(f"Connection error creating in '{table_id}': {ce}"); return None
#     except Exception as e: error_detail = str(e); response_text = getattr(getattr(e, 'response', None), 'text', None);
#     if response_text: error_detail = f"{error_detail} - Resp: {response_text}"; logger.exception(f"Error creating in '{table_id}'. Fields: {list(valid_fields.keys())}. E: {error_detail}"); return None

# def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
#     if not table_id or not record_id: return None
#     try: table = AirtableConnector.get_table(table_id); record = table.get(record_id); logger.debug(f"Rec '{record_id}' {'fetched' if record else 'not found'} from '{table_id}'."); return record
#     except Exception as e: logger.exception(f"Error fetching rec '{record_id}' from '{table_id}'. E:{e}"); return None

# def find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
#     if not table_id: logger.error("Find failed: No table_id."); return None
#     try: table = AirtableConnector.get_table(table_id); sort_param = sort or []; records = table.all( formula=formula, fields=fields_to_fetch, max_records=max_records, sort=sort_param ); logger.info(f"Found {len(records)} in '{table_id}'. Formula: '{formula or 'None'}'"); return records
#     except Exception as e: logger.exception(f"Error finding in '{table_id}'. Formula: {formula}. E:{type(e).__name__}: {e}"); return None

# def update_record(table_id: str, record_id: str, fields_to_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     if not table_id or not record_id: logger.error("Update failed: No table/record id."); return None
#     valid_updates = {k: v for k, v in fields_to_update.items() if k and k.startswith("fld")} # Ensure keys are Field IDs
#     if not valid_updates: logger.warning(f"No valid Field IDs provided for update '{record_id}' in '{table_id}'. Orig keys: {list(fields_to_update.keys())}"); return get_record(table_id, record_id)
#     try: table = AirtableConnector.get_table(table_id); logger.debug(f"Updating '{record_id}' in '{table_id}' fields: {list(valid_updates.keys())}"); updated_record = table.update(record_id, valid_updates, typecast=True); logger.info(f"Record '{record_id}' updated in '{table_id}'."); return updated_record
#     except Exception as e: error_detail = str(e); response_text = getattr(getattr(e, 'response', None), 'text', None);
#     if response_text: error_detail = f"{error_detail} - Resp: {response_text}"; logger.exception(f"Error updating '{record_id}' in '{table_id}'. Updates: {list(valid_updates.keys())}. E: {error_detail}"); return None

# def delete_record(table_id: str, record_id: str) -> bool:
#      if not table_id or not record_id: logger.error("Delete failed: No table/record id."); return False
#      try: table = AirtableConnector.get_table(table_id); logger.warning(f"Attempting delete: '{record_id}' from '{table_id}'"); result = table.delete(record_id); success = result.get('deleted', False); logger.info(f"Record '{record_id}' delete status: {success}"); return success
#      except Exception as e: logger.exception(f"Error deleting '{record_id}' from '{table_id}'. E:{e}"); return False

# def get_active_job_descriptions() -> Optional[List[Dict[str, Any]]]:
#     formula = match({fields.JD_STATUS: "Active"}); fields_to_request = ["Position Title", "Location"]; sort_order = ["Position Title"]
#     records = find_records( JD_TABLE_ID, formula=formula, fields_to_fetch=fields_to_request, sort=sort_order )
#     if records is None: logger.error("Failed retrieve active JDs."); return None
#     processed_records = []
#     for record in records:
#         record_fields = record.get("fields", {}); title = record_fields.get("Position Title"); location = record_fields.get("Location"); record_id = record.get("id")
#         if record_id and title: processed_records.append({"id": record_id, "title": title, "location": location})
#         else: logger.warning(f"Skipping JD {record_id or 'Unknown ID'} due to missing title.")
#     logger.info(f"Processed {len(processed_records)} active JDs for display.")
#     return processed_records

# def get_jd_details_by_title(title: str) -> Optional[Dict[str, Any]]:
#     if not title: logger.warning("get_jd_details_by_title empty title."); return None
#     formula = match({fields.JD_POSITION_TITLE: title}); records = find_records(JD_TABLE_ID, formula=formula, max_records=1)
#     if records is None: logger.error(f"Error fetching JD details for title '{title}'."); return None
#     if not records: logger.warning(f"No JD found with title '{title}'."); return None
#     if 'fields' not in records[0]: logger.error(f"JD record {records[0].get('id')} missing 'fields'."); return None
#     return records[0]

# # --- Application Log ---
# def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
#     """Creates initial log. Expects field names as keys in log_data."""
#     airtable_data = {}
#     # Only map fields that are known and have valid IDs (not placeholders)
#     known_log_fields = {
#         "Applied Position Title": fields.LOG_APPLIED_POSITION_TITLE,
#         "CV Filename": fields.LOG_CV_FILENAME,
#         "Candidate Name": fields.LOG_CANDIDATE_NAME,
#         "Company Name": fields.LOG_COMPANY_NAME,
#         "Target Location Submitted": fields.LOG_TARGET_LOCATION,
#         "Current Location Submitted": fields.LOG_CURRENT_LOCATION,
#         "Relocation Status Submitted": fields.LOG_RELOCATION_STATUS,
#         "Candidate Email": fields.LOG_CANDIDATE_EMAIL,
#         "Processing Status": fields.LOG_PROCESSING_STATUS,
#     }
#     for name, value in log_data.items():
#         field_id = known_log_fields.get(name)
#         if field_id and value is not None: # Ensures ID is valid (not None from placeholder)
#              airtable_data[field_id] = value

#     # Default status if not provided
#     if fields.LOG_PROCESSING_STATUS not in airtable_data:
#         airtable_data[fields.LOG_PROCESSING_STATUS] = "Received"

#     # Validate essential fields using Field IDs after mapping
#     if not airtable_data.get(fields.LOG_APPLIED_POSITION_TITLE) or \
#        not airtable_data.get(fields.LOG_CV_FILENAME):
#         logger.error("Cannot create log: Missing required Title/Filename."); return None
#     if not airtable_data: logger.warning("Cannot create log: No valid fields mapped."); return None

#     record = create_record(LOGS_TABLE_ID, airtable_data); return record.get('id') if record else None

# def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
#     """Updates log record. Expects Field Names as keys in updates dict."""
#     if not log_record_id: logger.error("update_log empty id."); return False
#     if not updates: logger.warning(f"update_log for {log_record_id} no updates."); return True
#     updates_with_ids = {}
#     for name, value in updates.items():
#         field_id = fields.get_field_id(name) # Map name to ID using revised helper
#         if field_id:
#              if field_id in [fields.LOG_ASSOCIATED_CANDIDATE_RECORD, fields.LOG_ASSOCIATED_LLM_RESPONSE]:
#                  if isinstance(value, str) and value.startswith("rec"): value = [value]
#                  elif not isinstance(value, list) and value is not None: logger.warning(f"Update link '{name}' invalid format: {value}. Skipping."); continue
#              updates_with_ids[field_id] = value
#         # else: Warning is logged by get_field_id
#     if not updates_with_ids: logger.warning(f"No valid field updates mapped for log {log_record_id}."); return True
#     updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates_with_ids); return updated_record is not None

# # --- Successful Candidate ---
# def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
#     """Creates Candidate record. Expects keys matching CandFields enum names."""
#     assoc_log_list = candidate_data.get(CandFields.ASSOCIATED_LOG_ENTRY.name); applied_jd_list = candidate_data.get(CandFields.APPLIED_POSITION.name); cand_name = candidate_data.get(CandFields.NAME.name); comp_name = candidate_data.get(CandFields.COMPANY_NAME.name)
#     def is_valid_link_list(ll): return ll and isinstance(ll, list) and all(isinstance(i, str) and i.startswith("rec") for i in ll)
#     if not is_valid_link_list(assoc_log_list): logger.error(f"Invalid Assoc Log IDs: {assoc_log_list}"); return None
#     if not is_valid_link_list(applied_jd_list): logger.error(f"Invalid Applied Pos IDs: {applied_jd_list}"); return None
#     if not cand_name or not isinstance(cand_name, str): logger.error("Missing/invalid cand name."); return None
#     if not comp_name or not isinstance(comp_name, str): logger.error("Missing/invalid company name."); return None
#     airtable_data = { fields.CAND_ASSOCIATED_LOG_ENTRY: assoc_log_list, fields.CAND_APPLIED_POSITION: applied_jd_list, fields.CAND_NAME: cand_name, fields.CAND_COMPANY_NAME: comp_name, fields.CAND_LLM_MATCH_REASON: candidate_data.get(CandFields.LLM_MATCH_REASON.name), fields.CAND_INTERVIEW_STATUS: candidate_data.get(CandFields.INTERVIEW_STATUS.name, "Pending") }
#     airtable_data_cleaned = {k: v for k, v in airtable_data.items() if k is not None}
#     record = create_record(CANDS_TABLE_ID, airtable_data_cleaned); return record.get('id') if record else None

# # --- LLM Response Logging ---
# def create_llm_response_log(data: Dict[str, Any]) -> Optional[str]:
#      """Creates LLM Response log. Expects keys matching LlmRespFields enum names."""
#      if not LLM_TABLE_ID: logger.warning("LLM Log skipped: LLM_TABLE_ID not set."); return None

#      # --- CORRECTED: Use field ID attributes directly ---
#      airtable_data = {
#          fields.LLM_ASSOCIATED_LOG_ENTRY: data.get(LlmRespFields.ASSOCIATED_LOG_ENTRY.name),
#          fields.LLM_BACKEND_ANALYSIS_REPORT: data.get(LlmRespFields.BACKEND_ANALYSIS_REPORT.name),
#          fields.LLM_FULL_PROMPT_SENT: data.get(LlmRespFields.FULL_PROMPT_SENT.name),
#          fields.LLM_RAW_RESPONSE_RECEIVED: data.get(LlmRespFields.RAW_RESPONSE_RECEIVED.name),
#          fields.LLM_PARSING_STATUS: data.get(LlmRespFields.PARSING_STATUS.name),
#      }
#      # --- END CORRECTION ---

#      # Validate and format link field (using the correct Field ID key)
#      log_entry_id_key = fields.LLM_ASSOCIATED_LOG_ENTRY
#      if not log_entry_id_key: logger.error("LLM Log Error: Assoc Log Entry Field ID not configured."); return None

#      log_entry_val = airtable_data.get(log_entry_id_key) # Get value using the ID key
#      if log_entry_val is None: # Check if it's missing from input data
#           logger.error(f"LLM Log Error: Missing value for {LlmRespFields.ASSOCIATED_LOG_ENTRY.name} in input data.")
#           return None
#      elif isinstance(log_entry_val, str) and log_entry_val.startswith("rec"):
#          airtable_data[log_entry_id_key] = [log_entry_val] # Convert to list
#      elif not isinstance(log_entry_val, list):
#          logger.error(f"LLM Log Error: Invalid Assoc Log format: {log_entry_val} (type: {type(log_entry_val)})"); return None
#      elif not log_entry_val: # Check if list is empty
#          logger.error("LLM Log Error: Empty Assoc Log list provided."); return None

#      # Filter out None values and invalid keys before sending
#      airtable_data_cleaned = {k: v for k, v in airtable_data.items() if k and k.startswith("fld") and v is not None}

#      if not airtable_data_cleaned.get(fields.LLM_ASSOCIATED_LOG_ENTRY): # Double check required field exists after cleaning
#           logger.error("LLM Log Error: Associated Log Entry missing after cleaning.")
#           return None

#      if len(airtable_data_cleaned) <= 1: # Should have more than just the link field
#          logger.warning(f"LLM Log may be incomplete. Fields being sent: {list(airtable_data_cleaned.keys())}")

#      record = create_record(LLM_TABLE_ID, airtable_data_cleaned); return record.get('id') if record else None

# # --- Admin Functions (No changes needed) ---
# def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
#     if not ADMIN_TABLE_ID: logger.error("Admin lookup fail: ADMIN_TABLE_ID not set."); return None
#     if not username: logger.warning("get_admin_user empty username."); return None
#     formula = match({fields.ADMIN_USERNAME: username}); records = find_records(ADMIN_TABLE_ID, formula=formula, max_records=1)
#     if records is None: logger.error(f"Error fetch admin user '{username}'."); return None
#     return records[0] if records else None
# def admin_find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]: return find_records(table_id, formula, fields_to_fetch, max_records, sort)
# def admin_create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]: return create_record(table_id, fields_to_create)
# def admin_delete_record(table_id: str, record_id: str) -> bool: return delete_record(table_id, record_id)

# # --- Standalone Parsing Helpers (No changes needed) ---
# def parse_locations(location_string: Optional[str]) -> List[str]:
#     if not location_string or not isinstance(location_string, str): return []
#     return [loc.strip() for loc in location_string.split(',') if loc.strip()]
# def parse_budget(budget_raw: Any) -> Tuple[bool, Optional[float]]:
#     is_flexible = False; budget_value = None; FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open"]
#     if isinstance(budget_raw, str):
#         if any(keyword in budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS): is_flexible = True
#         else:
#             try: cleaned = re.sub(r'[^\d\.]', '', budget_raw.replace(',', '')); budget_value = float(cleaned) if cleaned else None
#             except (ValueError, TypeError): logger.warning(f"Could not parse budget string: '{budget_raw}'")
#     elif isinstance(budget_raw, (int, float)): budget_value = float(budget_raw)
#     return is_flexible, budget_value
# def parse_experience(exp_raw: Any) -> Optional[float]:
#      if isinstance(exp_raw, (int, float)): return float(exp_raw)
#      elif isinstance(exp_raw, str):
#           try: return float(exp_raw)
#           except ValueError: logger.warning(f"Could not parse experience string: '{exp_raw}'"); return None
#      return None

# # --- Exports for Admin Portal ---
# LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID; CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID; ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID; JD_TABLE_ID_FOR_ADMIN = JD_TABLE_ID; LLM_TABLE_ID_FOR_ADMIN = LLM_TABLE_ID






# backend/airtable_client.py

import os
import logging
import re
from pyairtable import Api, Table
from pyairtable.formulas import match
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Tuple, Type
from enum import Enum

load_dotenv() # Load variables from .env
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Helper function to clean environment variables ---
def get_clean_env_var(var_name: str) -> str:
    """Gets env var, removes inline comments, and strips whitespace."""
    value = os.getenv(var_name, "")
    value = value.split('#', 1)[0] # Remove potential inline comments
    return value.strip() # Strip leading/trailing whitespace

# --- Configuration (Using Cleaner Helper) ---
AIRTABLE_PAT = get_clean_env_var("AIRTABLE_PAT")
AIRTABLE_BASE_ID = get_clean_env_var("AIRTABLE_BASE_ID")
API_TIMEOUT = int(get_clean_env_var("AIRTABLE_API_TIMEOUT") or 30)

REQ_TABLE_ID = get_clean_env_var("AIRTABLE_JD_TABLE_ID")
LOGS_TABLE_ID = get_clean_env_var("AIRTABLE_LOGS_TABLE_ID")
LLM_TABLE_ID = get_clean_env_var("AIRTABLE_LLM_TABLE_ID")
CANDS_TABLE_ID = get_clean_env_var("AIRTABLE_CANDS_TABLE_ID")
ADMIN_TABLE_ID = get_clean_env_var("AIRTABLE_ADMIN_TABLE_ID")

# --- Validation (After Cleaning) ---
if not AIRTABLE_PAT or not AIRTABLE_BASE_ID: raise ValueError("Airtable PAT/Base ID missing or invalid in .env.")
required_tables = {"Requirements": REQ_TABLE_ID, "Logs": LOGS_TABLE_ID, "Candidates": CANDS_TABLE_ID, "LLM Responses": LLM_TABLE_ID}
missing_or_invalid_tables = [name for name, tid in required_tables.items() if not tid or not tid.startswith("tbl")]
if missing_or_invalid_tables:
    raise ValueError(f"Required Airtable Table IDs missing or invalid in .env: {', '.join(missing_or_invalid_tables)}")
if not LLM_TABLE_ID or not LLM_TABLE_ID.startswith("tbl"): logger.warning("LLM_TABLE_ID invalid or not set. LLM Response logging will fail.")
if not ADMIN_TABLE_ID or not ADMIN_TABLE_ID.startswith("tbl"): logger.warning("ADMIN_TABLE_ID invalid or not set. Admin functions might fail.")

# --- Field ID Management (UPDATED FOR NEW SCHEMA - appgRwS5bf1GRGhBI) ---
class FieldIdEnum(Enum):
    def __str__(self): return str(self.value)

class ReqFields(FieldIdEnum): # Client Requirements (tblUviQXKrL3TUuus)
    REQUIREMENT_TITLE = "fldf4apw7f4y4s0Zy"; CLIENT = "fldlaY7OwUCXHXGfx"; TECH_SKILLS = "fld5UG3kXtMZnQ7Ds"; STATUS = "fldOvvFgl7ghEGaQu"; LOCATION = "fldCnohrYlA4cKhYN"; JD_TEXT = "fldPkWJKJ6sVwt9NV"; MIN_EXPERIENCE = "fld4ZG4X7O1yXGsu8"; BUDGET = "fldmhLvi8ZVFRN1zq"; DEADLINE = "fld5SBPcybPQbHu3Y"; PRIORITY = "fldiiIVfOS1MFxncE"; SPOC = "fldlJZnO1t0l9ozEM"; NOTES = "fldQFsgSPDkxlULet"; JD_LINK = "fldiysXPGqj5f1in6"; SUCCESSFUL_CANDIDATES_LINK = "fldjR2qwag27Vjelv"

# *** LogFields: REMOVED PLACEHOLDERS - THESE FIELDS WILL NOT BE SAVED TO LOGS TABLE ***
class LogFields(FieldIdEnum): # Application Logs (tbljEEl3ybgchxK6w)
    LOG_ID = "fldLE9gd2n8ufyRP6"; APPLIED_POSITION_TITLE = "fldk6gqvdEkEc7r9F"; CV_FILENAME = "fldbpuzhA5WVJLnah"; CANDIDATE_EMAIL = "fldOWPXAbZq6itM1q"; PROCESSING_STATUS = "fldskHsD0nAykgIZW"; FINAL_OUTCOME = "fldjJfTep86DzRmub"; BACKEND_ANALYSIS_REPORT = "fldh4Pv1usXr5dxO6"; ERROR_DETAILS = "fldb7Hjd7BkBI8kPV"; ASSOCIATED_LLM_RESPONSE = "fld3VaKWJGu9hJdWq"; ASSOCIATED_CANDIDATE_RECORD = "fldugqwAmk623hC0G"
    # NOTE: Candidate Name, Company Name, Target Location, Current Location, Relocation Status
    # are NOT included here because their Field IDs were not provided.
    # They will NOT be saved to the Application Logs table.
# *** END LogFields UPDATE section ***

class LlmRespFields(FieldIdEnum): # LLM Responses (tblM5foLOcBIgSdRB)
    RESPONSE_ID = "fldnNi9LqCXKn3YLv"; ASSOCIATED_LOG_ENTRY = "fldzyxo4kHTgrxzoo"; BACKEND_ANALYSIS_REPORT = "fldLFZpSRFFJjqqUu"; FULL_PROMPT_SENT = "fldx8jyCuhqrjzaxG"; RAW_RESPONSE_RECEIVED = "fldJUBSWKi5waAky4"; PARSING_STATUS = "fldMg8wx22Yzkcx1t" # Corrected FULL_PROMPT_SENT ID

class CandFields(FieldIdEnum): # Successful Candidates (tbl1RYRfDafP5vO9O)
    NAME = "fld6w5Z4tbrUxRT1m"; COMPANY_NAME = "fldRZ7nBj9GJVR5wK"; ASSOCIATED_LOG_ENTRY = "fldhOdTPV4QvA5DbE"; APPLIED_POSITION = "fldkaE74Z2LtsgAN9"; LLM_MATCH_REASON = "fld7XOs2Zu7mVBdmL"; INTERVIEW_STATUS = "fldPS2HzfkL0EbpbY" # Mapped from "Interview Scheduling" in description

class AdminFields(FieldIdEnum): # Admin Users (ID from .env)
     USERNAME = "fld???????????????" # Placeholder - Replace with actual ID if using admin features
     PASSWORD_HASH = "fld???????????????" # Placeholder - Replace with actual ID if using admin features

# --- `fields` class definition for easy access to Field ID strings ---
class fields:
    """Provides string access to Field IDs via class attributes. Returns None if not defined."""
    # Client Requirements (REQ_)
    REQ_TITLE = str(ReqFields.REQUIREMENT_TITLE.value); REQ_LOCATION = str(ReqFields.LOCATION.value); REQ_MIN_EXPERIENCE = str(ReqFields.MIN_EXPERIENCE.value); REQ_STATUS = str(ReqFields.STATUS.value); REQ_JD_TEXT = str(ReqFields.JD_TEXT.value); REQ_BUDGET = str(ReqFields.BUDGET.value)
    # Application Logs (LOG_)
    LOG_APPLIED_POSITION_TITLE = str(LogFields.APPLIED_POSITION_TITLE.value); LOG_CV_FILENAME = str(LogFields.CV_FILENAME.value)
    # *** REMOVED attributes for fields not saved to Logs ***
    LOG_CANDIDATE_EMAIL = str(LogFields.CANDIDATE_EMAIL.value); LOG_PROCESSING_STATUS = str(LogFields.PROCESSING_STATUS.value); LOG_FINAL_OUTCOME = str(LogFields.FINAL_OUTCOME.value); ERROR_DETAILS = str(LogFields.ERROR_DETAILS.value); LOG_BACKEND_REPORT = str(LogFields.BACKEND_ANALYSIS_REPORT.value); LOG_ASSOCIATED_LLM_RESPONSE = str(LogFields.ASSOCIATED_LLM_RESPONSE.value); LOG_ASSOCIATED_CANDIDATE_RECORD = str(LogFields.ASSOCIATED_CANDIDATE_RECORD.value)
    # LLM Responses (LLM_)
    LLM_ASSOCIATED_LOG_ENTRY = str(LlmRespFields.ASSOCIATED_LOG_ENTRY.value); LLM_BACKEND_ANALYSIS_REPORT = str(LlmRespFields.BACKEND_ANALYSIS_REPORT.value); LLM_FULL_PROMPT_SENT = str(LlmRespFields.FULL_PROMPT_SENT.value); LLM_RAW_RESPONSE_RECEIVED = str(LlmRespFields.RAW_RESPONSE_RECEIVED.value); LLM_PARSING_STATUS = str(LlmRespFields.PARSING_STATUS.value)
    # Successful Candidates (CAND_)
    CAND_NAME = str(CandFields.NAME.value); CAND_COMPANY_NAME = str(CandFields.COMPANY_NAME.value); CAND_ASSOCIATED_LOG_ENTRY = str(CandFields.ASSOCIATED_LOG_ENTRY.value); CAND_APPLIED_POSITION = str(CandFields.APPLIED_POSITION.value); CAND_LLM_MATCH_REASON = str(CandFields.LLM_MATCH_REASON.value); CAND_INTERVIEW_STATUS = str(CandFields.INTERVIEW_STATUS.value)
    # Admin Users (ADMIN_)
    ADMIN_USERNAME = str(AdminFields.USERNAME.value) if hasattr(AdminFields, 'USERNAME') and not AdminFields.USERNAME.value.startswith("fld????") else None
    ADMIN_PASSWORD_HASH = str(AdminFields.PASSWORD_HASH.value) if hasattr(AdminFields, 'PASSWORD_HASH') and not AdminFields.PASSWORD_HASH.value.startswith("fld????") else None

    @staticmethod
    def get_field_id(field_name: str) -> Optional[str]:
        """Maps common field names (case-insensitive) to their Field ID strings."""
        if not isinstance(field_name, str): return None
        # Map common input names (lowercase, underscore) to CLASS ATTRIBUTE NAMES
        name_to_attr_map = {
            # Requirement fields
            "requirement": "REQ_TITLE", "position_title": "REQ_TITLE",
            "location": "REQ_LOCATION", "minimum_experience": "REQ_MIN_EXPERIENCE",
            "minimum_experience_in_years": "REQ_MIN_EXPERIENCE", "status": "REQ_STATUS",
            "jd_in_text": "REQ_JD_TEXT", "job_description_text": "REQ_JD_TEXT",
            "budget": "REQ_BUDGET",
            # Log fields (Only those defined in `fields` class now)
            "applied_position_title": "LOG_APPLIED_POSITION_TITLE",
            "cv_filename": "LOG_CV_FILENAME",
            "candidate_email": "LOG_CANDIDATE_EMAIL",
            "processing_status": "LOG_PROCESSING_STATUS",
            "final_outcome": "LOG_FINAL_OUTCOME",
            "error_details": "ERROR_DETAILS",
            "backend_analysis_report": "LOG_BACKEND_REPORT",
            "associated_llm_response": "LOG_ASSOCIATED_LLM_RESPONSE",
            "associated_candidate_record": "LOG_ASSOCIATED_CANDIDATE_RECORD",
            # *** REMOVED MAPPINGS for fields not saved to Logs ***
            # "candidate_name": "LOG_CANDIDATE_NAME",
            # "company_name": "LOG_COMPANY_NAME",
            # "target_location_submitted": "LOG_TARGET_LOCATION",
            # "current_location_submitted": "LOG_CURRENT_LOCATION",
            # "relocation_status_submitted": "LOG_RELOCATION_STATUS",
            # LLM Table Name Mappings
            "llm_associated_log_entry": "LLM_ASSOCIATED_LOG_ENTRY",
            "llm_backend_analysis_report": "LLM_BACKEND_ANALYSIS_REPORT",
            "full_prompt_sent": "LLM_FULL_PROMPT_SENT",
            "raw_response_received": "LLM_RAW_RESPONSE_RECEIVED",
            "parsing_status": "LLM_PARSING_STATUS",
            # Successful Candidate Name Mappings
            "cand_name": "CAND_NAME",
            "cand_company_name": "CAND_COMPANY_NAME",
            "interview_scheduling_status": "CAND_INTERVIEW_STATUS", # Map from old name
            "cand_interview_status": "CAND_INTERVIEW_STATUS", # Map from new name
        }
        normalized_name = re.sub(r'[\s-]+', '_', field_name).lower().strip()
        attribute_name = name_to_attr_map.get(normalized_name)

        if attribute_name:
            field_id = getattr(fields, attribute_name, None)
            # Check if it's a valid, non-placeholder field ID
            if field_id and field_id.startswith("fld") and not field_id.startswith("fld????"):
                 return field_id
            # No warning needed if attribute found but field ID is None (placeholder)
        elif field_name.startswith("fld") and not field_name.startswith("fld????"):
             # Pass through if it looks like a valid non-placeholder Field ID already
             return field_name
        # else: # Removed warning for unmapped fields to reduce noise, as some are intentionally unmapped now
            # logger.warning(f"Could not map field name '{field_name}' (norm: '{normalized_name}') to any known attribute.")
        return None


# --- AirtableConnector Class (No changes) ---
class AirtableConnector:
    _api: Optional[Api] = None; _tables: Dict[str, Table] = {}
    @classmethod
    def get_api(cls) -> Api:
        if cls._api is None:
            if not AIRTABLE_PAT: raise ValueError("Airtable PAT missing.");
            try: cls._api = Api(AIRTABLE_PAT, timeout=(API_TIMEOUT, API_TIMEOUT)); logger.info(f"Airtable API client init (Timeout: {API_TIMEOUT}s).")
            except Exception as e: logger.exception("Fatal: Airtable API client init failed."); raise ConnectionError(f"Airtable API connect error: {e}") from e
        return cls._api
    @classmethod
    def get_table(cls, table_id: str) -> Table:
        if not table_id: raise ValueError("Empty table ID.");
        if table_id not in cls._tables:
            if not AIRTABLE_BASE_ID: raise ValueError("Airtable Base ID missing.");
            try: api = cls.get_api(); cls._tables[table_id] = api.table(AIRTABLE_BASE_ID, table_id); logger.info(f"Airtable Table acquired: {table_id}")
            except Exception as e: logger.exception(f"Fatal: Failed get Airtable table '{table_id}'."); raise ConnectionError(f"Airtable table access error '{table_id}': {e}") from e
        return cls._tables[table_id]

# --- Generic CRUD Operations ---
# Added check for valid field IDs in create/update
def create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not table_id: logger.error("Create failed: No table_id."); return None
    valid_fields = {k: v for k, v in fields_to_create.items() if k and k.startswith("fld")}
    if not valid_fields: logger.warning(f"Create in '{table_id}' called with no valid Field ID keys to save. Original keys attempted: {list(fields_to_create.keys())}"); return None
    try: table = AirtableConnector.get_table(table_id); record = table.create(valid_fields, typecast=True); rec_id = record.get('id', 'N/A'); logger.info(f"Record created in '{table_id}' (ID: {rec_id})"); return record
    except ConnectionError as ce: logger.error(f"Connection error creating in '{table_id}': {ce}"); return None
    except Exception as e:
        error_detail = str(e); response_text = getattr(getattr(e, 'response', None), 'text', None); error_code = getattr(e, 'status_code', None)
        if response_text: error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}";
        logger.exception(f"Error creating in '{table_id}'. Fields sent: {list(valid_fields.keys())}. E: {error_detail}")
        return None

def get_record(table_id: str, record_id: str) -> Optional[Dict[str, Any]]:
    if not table_id or not record_id: return None
    try: table = AirtableConnector.get_table(table_id); record = table.get(record_id); logger.debug(f"Rec '{record_id}' {'fetched' if record else 'not found'} from '{table_id}'."); return record
    except Exception as e: logger.exception(f"Error fetching rec '{record_id}' from '{table_id}'. E:{e}"); return None

def find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
    if not table_id: logger.error("Find failed: No table_id."); return None
    try: table = AirtableConnector.get_table(table_id); sort_param = sort or []; records = table.all( formula=formula, fields=fields_to_fetch, max_records=max_records, sort=sort_param ); logger.info(f"Found {len(records)} in '{table_id}'. Formula: '{formula or 'None'}'"); return records
    except Exception as e: logger.exception(f"Error finding in '{table_id}'. Formula: {formula}. E:{type(e).__name__}: {e}"); return None

def update_record(table_id: str, record_id: str, fields_to_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not table_id or not record_id: logger.error("Update failed: No table/record id."); return None
    valid_updates = {k: v for k, v in fields_to_update.items() if k and k.startswith("fld")}
    if not valid_updates: logger.warning(f"No valid Field IDs provided for update '{record_id}' in '{table_id}'. Orig keys: {list(fields_to_update.keys())}"); return get_record(table_id, record_id)
    try: table = AirtableConnector.get_table(table_id); logger.debug(f"Updating '{record_id}' in '{table_id}' fields: {list(valid_updates.keys())}"); updated_record = table.update(record_id, valid_updates, typecast=True); logger.info(f"Record '{record_id}' updated in '{table_id}'."); return updated_record
    except Exception as e:
        error_detail = str(e); response_text = getattr(getattr(e, 'response', None), 'text', None); error_code = getattr(e, 'status_code', None)
        if response_text: error_detail = f"({error_code} {getattr(getattr(e, 'response', None), 'reason', '')}) {error_detail} - Resp: {response_text}";
        logger.exception(f"Error updating '{record_id}' in '{table_id}'. Updates sent: {list(valid_updates.keys())}. E: {error_detail}")
        return None

def delete_record(table_id: str, record_id: str) -> bool:
     if not table_id or not record_id: logger.error("Delete failed: No table/record id."); return False
     try: table = AirtableConnector.get_table(table_id); logger.warning(f"Attempting delete: '{record_id}' from '{table_id}'"); result = table.delete(record_id); success = result.get('deleted', False); logger.info(f"Record '{record_id}' delete status: {success}"); return success
     except Exception as e: logger.exception(f"Error deleting '{record_id}' from '{table_id}'. E:{e}"); return False

# --- Specific Helper Functions (ADAPTED FOR NEW SCHEMA) ---
def get_active_requirements() -> Optional[List[Dict[str, Any]]]:
    """Gets active Requirements using field names 'Requirement' and 'Location'."""
    if not fields.REQ_STATUS: logger.error("REQ_STATUS field ID not configured."); return None
    formula = match({fields.REQ_STATUS: "Active"})
    fields_to_request = ["Requirement", "Location"]
    sort_order = ["Requirement"]
    records = find_records( REQ_TABLE_ID, formula=formula, fields_to_fetch=fields_to_request, sort=sort_order )
    if records is None: logger.error("Failed retrieve active Requirements."); return None
    processed_records = []
    for record in records:
        record_fields = record.get("fields", {}); title = record_fields.get("Requirement"); location = record_fields.get("Location"); record_id = record.get("id")
        if record_id and title: processed_records.append({"id": record_id, "title": title, "location": location})
        else: logger.warning(f"Skipping Requirement {record_id or 'Unknown ID'} due to missing title.")
    logger.info(f"Processed {len(processed_records)} active Requirements for display.")
    return processed_records

def get_requirement_details_by_title(title: str) -> Optional[Dict[str, Any]]:
    """Gets full Requirement details by its title ('Requirement' field)."""
    if not title: logger.warning("get_requirement_details_by_title empty title."); return None
    if not fields.REQ_TITLE: logger.error("REQ_TITLE field ID not configured."); return None
    formula = match({fields.REQ_TITLE: title})
    records = find_records(REQ_TABLE_ID, formula=formula, max_records=1)
    if records is None: logger.error(f"Error fetching Req details for title '{title}'."); return None
    if not records: logger.warning(f"No Requirement found with title '{title}'."); return None
    if 'fields' not in records[0]: logger.error(f"Requirement record {records[0].get('id')} missing 'fields'."); return None
    return records[0]

# --- Application Log ---
# *** MODIFIED create_application_log: Does NOT save Name, Company, Locations, Relo Status ***
def create_application_log(log_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates initial log. Expects field names as keys in log_data.
    NOTE: Candidate Name, Company Name, Locations, Relocation Status are NOT saved
          to this table due to missing Field ID configuration.
    """
    airtable_data = {}
    # Function to map name to ID and add to dict if valid
    def add_if_valid(name, value):
        field_id = fields.get_field_id(name)
        # Only add if we got a valid field ID and a value exists
        if field_id and field_id.startswith("fld") and value is not None:
            airtable_data[field_id] = value
        # No warning here for unmapped fields, handled by get_field_id if needed

    # Pass expected string names from agent_runner
    # ONLY map fields that have configured IDs in the 'fields' class
    add_if_valid("Applied Position Title", log_data.get("Applied Position Title"))
    add_if_valid("CV Filename", log_data.get("CV Filename"))
    add_if_valid("Candidate Email", log_data.get("Candidate Email"))
    add_if_valid("Processing Status", log_data.get("Processing Status", "Received"))
    # Intentionally skipping: "Candidate Name", "Company Name", "Target Location Submitted",
    #                        "Current Location Submitted", "Relocation Status Submitted"

    # Validate essential fields using their Field IDs from 'fields' class
    if not airtable_data.get(fields.LOG_APPLIED_POSITION_TITLE) or not airtable_data.get(fields.LOG_CV_FILENAME):
        logger.error("Cannot create log: Missing required Title/Filename field IDs or values.")
        return None
    if not airtable_data:
        logger.warning("Cannot create log: No valid fields mapped after filtering.")
        return None

    # Log which fields are being skipped IF data for them was provided
    skipped_data = {k:v for k,v in log_data.items() if k in [
        "Candidate Name", "Company Name", "Target Location Submitted",
        "Current Location Submitted", "Relocation Status Submitted"
        ] and v is not None}
    if skipped_data:
        logger.info(f"Log Creation: Skipping save of these fields to Logs table (no configured Field IDs): {list(skipped_data.keys())}")

    record = create_record(LOGS_TABLE_ID, airtable_data); return record.get('id') if record else None
# *** END MODIFICATION ***

def update_application_log(log_record_id: str, updates: Dict[str, Any]) -> bool:
    """Updates log record. Expects Field Names as keys in updates dict."""
    if not log_record_id: logger.error("update_log empty id."); return False
    if not updates: logger.warning(f"update_log for {log_record_id} no updates."); return True
    updates_with_ids = {}
    failed_mappings = []
    for name, value in updates.items():
        field_id = fields.get_field_id(name) # get_field_id now returns None for unconfigured fields
        # Proceed only if a valid field ID was found
        if field_id and field_id.startswith("fld"):
             # Special handling for link fields: ensure they are lists of record IDs
             if field_id in [fields.LOG_ASSOCIATED_CANDIDATE_RECORD, fields.LOG_ASSOCIATED_LLM_RESPONSE]:
                 if isinstance(value, str) and value.startswith("rec"): value = [value] # Convert single ID string to list
                 elif not isinstance(value, list) and value is not None:
                     logger.warning(f"Update link field '{name}' ({field_id}) has invalid format: {value} (type: {type(value)}). Expected list or single recID string. Skipping."); continue # Skip this invalid link update
                 elif isinstance(value, list) and not all(isinstance(item, str) and item.startswith("rec") for item in value):
                     logger.warning(f"Update link field '{name}' ({field_id}) contains invalid items: {value}. Skipping."); continue # Skip list with invalid items
             updates_with_ids[field_id] = value
        elif value is not None: # Only track as failed if mapping failed AND there was a value to update
             failed_mappings.append(name)
    if failed_mappings:
        # Filter out intentionally skipped fields from the warning
        intentionally_skipped = ["Candidate Name", "Company Name", "Target Location Submitted", "Current Location Submitted", "Relocation Status Submitted"]
        actual_failed = [f for f in failed_mappings if f not in intentionally_skipped]
        if actual_failed:
             logger.warning(f"Log Update ({log_record_id}): Updates skipped for unmapped fields: {actual_failed}")
    if not updates_with_ids: logger.warning(f"No valid field updates to apply for log {log_record_id}."); return True
    updated_record = update_record(LOGS_TABLE_ID, log_record_id, updates_with_ids); return updated_record is not None

# --- Successful Candidate ---
def create_successful_candidate(candidate_data: Dict[str, Any]) -> Optional[str]:
    """Creates Candidate record. Expects keys matching CandFields enum names."""
    assoc_log_list = candidate_data.get(CandFields.ASSOCIATED_LOG_ENTRY.name)
    applied_req_list = candidate_data.get(CandFields.APPLIED_POSITION.name)
    cand_name = candidate_data.get(CandFields.NAME.name)
    comp_name = candidate_data.get(CandFields.COMPANY_NAME.name)
    llm_reason = candidate_data.get(CandFields.LLM_MATCH_REASON.name)
    interview_status = candidate_data.get(CandFields.INTERVIEW_STATUS.name, "Pending")

    def is_valid_link_list(ll): return ll and isinstance(ll, list) and all(isinstance(i, str) and i.startswith("rec") for i in ll)
    if not is_valid_link_list(assoc_log_list): logger.error(f"Create Candidate failed: Invalid Assoc Log IDs: {assoc_log_list}"); return None
    if not is_valid_link_list(applied_req_list): logger.error(f"Create Candidate failed: Invalid Applied Position (Req) IDs: {applied_req_list}"); return None
    if not cand_name or not isinstance(cand_name, str): logger.error("Create Candidate failed: Missing/invalid cand name."); return None
    if not comp_name or not isinstance(comp_name, str): logger.error("Create Candidate failed: Missing/invalid company name."); return None

    airtable_data = {
        fields.CAND_ASSOCIATED_LOG_ENTRY: assoc_log_list,
        fields.CAND_APPLIED_POSITION: applied_req_list,
        fields.CAND_NAME: cand_name,
        fields.CAND_COMPANY_NAME: comp_name,
        fields.CAND_LLM_MATCH_REASON: llm_reason,
        fields.CAND_INTERVIEW_STATUS: interview_status
    }
    airtable_data_cleaned = {k: v for k, v in airtable_data.items() if k and k.startswith("fld") and v is not None}

    required_cand_fields = [fields.CAND_ASSOCIATED_LOG_ENTRY, fields.CAND_APPLIED_POSITION, fields.CAND_NAME, fields.CAND_COMPANY_NAME]
    if not all(rf in airtable_data_cleaned for rf in required_cand_fields):
        missing = [f for f in required_cand_fields if f not in airtable_data_cleaned]
        logger.error(f"Create Candidate failed: Required fields missing after cleaning. Missing: {missing}")
        return None

    record = create_record(CANDS_TABLE_ID, airtable_data_cleaned); return record.get('id') if record else None

# --- LLM Response Logging ---
# *** CORRECTED FUNCTION: Skips RESPONSE_ID ***
def create_llm_response_log(data: Dict[str, Any]) -> Optional[str]:
     """Creates LLM Response log. Expects keys matching LlmRespFields enum names. Skips RESPONSE_ID."""
     if not LLM_TABLE_ID: logger.warning("LLM Log skipped: LLM_TABLE_ID not set."); return None

     airtable_data = {}
     skipped_fields = []
     for field_enum in LlmRespFields:
         # *** SKIP the Auto Number RESPONSE_ID field ***
         if field_enum == LlmRespFields.RESPONSE_ID:
             continue

         field_id = getattr(fields, f"LLM_{field_enum.name}", None)
         if field_id and field_id.startswith("fld"):
             value = data.get(field_enum.name)
             if value is not None:
                 if field_id == fields.LLM_ASSOCIATED_LOG_ENTRY: # Link field handling
                     if isinstance(value, str) and value.startswith("rec"):
                         airtable_data[field_id] = [value]
                     elif isinstance(value, list) and all(isinstance(item, str) and item.startswith("rec") for item in value):
                         airtable_data[field_id] = value
                     else:
                         logger.error(f"LLM Log: Invalid Assoc Log format for {field_enum.name}: {value}. Skipping field."); skipped_fields.append(field_enum.name); continue
                 else:
                     airtable_data[field_id] = value # Assign other values
         elif data.get(field_enum.name) is not None: # Log if mapping failed but value existed
             logger.error(f"LLM Log: Field ID mapping failed for '{field_enum.name}'. Cannot save.")
             skipped_fields.append(field_enum.name)

     log_entry_id_key = fields.LLM_ASSOCIATED_LOG_ENTRY
     if not log_entry_id_key or log_entry_id_key not in airtable_data:
          logger.error(f"LLM Log Error: Associated Log Entry missing or invalid. Cannot create log."); return None

     if skipped_fields: logger.warning(f"LLM Log Creation: Some fields not saved: {skipped_fields}")
     if len(airtable_data) == 1 and fields.LLM_ASSOCIATED_LOG_ENTRY in airtable_data:
         logger.warning(f"LLM Log may be incomplete (only Assoc Log Entry saved).")

     record = create_record(LLM_TABLE_ID, airtable_data); return record.get('id') if record else None
# *** END CORRECTION ***


# --- Admin Functions ---
def get_admin_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    admin_user_field_id = fields.ADMIN_USERNAME
    if not ADMIN_TABLE_ID or not admin_user_field_id: logger.error("Admin lookup fail: ADMIN_TABLE_ID or ADMIN_USERNAME Field ID not set/configured."); return None
    if not username: logger.warning("get_admin_user empty username."); return None
    formula = match({admin_user_field_id: username}); records = find_records(ADMIN_TABLE_ID, formula=formula, max_records=1)
    if records is None: logger.error(f"Error fetch admin user '{username}'."); return None
    return records[0] if records else None
def admin_find_records(table_id: str, formula: Optional[str] = None, fields_to_fetch: Optional[List[str]] = None, max_records: Optional[int] = None, sort: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]: return find_records(table_id, formula, fields_to_fetch, max_records, sort)
def admin_create_record(table_id: str, fields_to_create: Dict[str, Any]) -> Optional[Dict[str, Any]]: return create_record(table_id, fields_to_create)
def admin_delete_record(table_id: str, record_id: str) -> bool: return delete_record(table_id, record_id)

# --- Standalone Parsing Helpers ---
def parse_locations(location_string: Optional[str]) -> List[str]:
    if not location_string or not isinstance(location_string, str): return []
    delimiters = re.compile(r'[;,]')
    return [loc.strip() for loc in delimiters.split(location_string) if loc.strip()]

def parse_budget(budget_raw: Any) -> Tuple[bool, Optional[float]]:
    is_flexible = False; budget_value = None; FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open"]
    if isinstance(budget_raw, str):
        if any(keyword in budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS): is_flexible = True
        else:
            try:
                cleaned = re.sub(r'[^\d\.\-]', '', budget_raw.replace(',', ''))
                if cleaned:
                    budget_value = float(cleaned)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse budget string: '{budget_raw}'")
    elif isinstance(budget_raw, (int, float)): budget_value = float(budget_raw)
    return is_flexible, budget_value

def parse_experience(exp_raw: Any) -> Optional[float]:
     if isinstance(exp_raw, (int, float)): return float(exp_raw)
     elif isinstance(exp_raw, str):
          try:
              cleaned = re.sub(r'[^\d\.\-]', '', exp_raw)
              if cleaned:
                  return float(cleaned)
          except ValueError:
              pass # Ignore error if cleaned string is not a valid float
          logger.warning(f"Could not parse experience string: '{exp_raw}'"); return None
     logger.warning(f"Could not parse experience value: {exp_raw} (type: {type(exp_raw)})")
     return None

# --- Exports for Admin Portal ---
LOGS_TABLE_ID_FOR_ADMIN = LOGS_TABLE_ID; CANDS_TABLE_ID_FOR_ADMIN = CANDS_TABLE_ID; ADMIN_TABLE_ID_FOR_ADMIN = ADMIN_TABLE_ID; JD_TABLE_ID_FOR_ADMIN = REQ_TABLE_ID; LLM_TABLE_ID_FOR_ADMIN = LLM_TABLE_ID