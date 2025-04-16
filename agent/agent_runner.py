#!/usr/bin/env python3
# agent/agent_runner.py
# import logging
# import base64
# from typing import Dict, Any, Optional
# import json
# import time
# import re
# from datetime import datetime
# import openai # Ensure openai is imported if not already

# # Use the configured OpenAI client and prompt from agent_definition
# from .agent_definition import client as openai_client, OPENAI_MODEL_NAME, CV_ASSESSMENT_PROMPT_TEMPLATE, logger as agent_logger

# # Import backend functions directly
# from backend import airtable_client as ac
# from backend.cv_parser import extract_text_from_cv_bytes

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# # --- Constants ---
# MAX_RETRIES = 1
# RETRY_DELAY = 7
# MAX_TOKENS_FOR_REPORT = 3500
# LLM_TEMPERATURE = 0.2

# # --- Helper Function for Parsing (parse_llm_response_v3 - Keep As Is) ---
# def parse_llm_response_v3(response_text: str) -> Dict[str, Any]:
#     """ Parses LLM response for JSON block and the full report text. """
#     parsed_data = { "full_report_text": response_text, "outcome_status": None, "primary_reason": None, "clarifying_questions": [], "parsing_error": None, "raw_response": response_text }
#     try:
#         json_match = re.search(r'```json\s*(\{.*?\})\s*```\s*$', response_text, re.DOTALL | re.IGNORECASE)
#         llm_json_output = None; json_parsed_ok = False; report_text_extracted = response_text
#         if json_match:
#             json_string = json_match.group(1)
#             try:
#                  llm_json_output = json.loads(json_string)
#                  parsed_data["outcome_status"] = llm_json_output.get("outcome_status")
#                  parsed_data["primary_reason"] = llm_json_output.get("primary_reason")
#                  parsed_data["clarifying_questions"] = llm_json_output.get("clarifying_questions", [])
#                  json_parsed_ok = True; logger.info("Successfully parsed JSON block.")
#                  report_text_extracted = response_text[:json_match.start()].strip()
#             except json.JSONDecodeError as json_e: logger.error(f"Failed decode JSON: {json_e}"); parsed_data["parsing_error"] = f"JSON Err: {json_e}"
#         else: logger.warning("JSON block ```json ... ``` not found."); parsed_data["parsing_error"] = "JSON block not found."

#         parsed_data["full_report_text"] = report_text_extracted

#         if not json_parsed_ok: # Fallback status inference if JSON failed
#             logger.info("Attempting fallback status inference as JSON parsing failed.")
#             report_lower = report_text_extracted.lower()
#             if "clarification needed" in report_lower or "clarifying questions for vendor" in report_lower: parsed_data["outcome_status"] = "Clarification Needed"
#             elif "matched" in report_lower and "mismatched" not in report_lower: parsed_data["outcome_status"] = "Matched"
#             elif "rejected" in report_lower or "mismatched" in report_lower: parsed_data["outcome_status"] = "Rejected"

#             if not parsed_data["outcome_status"]: parsed_data["outcome_status"] = "error"; parsed_data["primary_reason"] = "Could not parse JSON or infer status."; parsed_data["parsing_error"] = parsed_data.get("parsing_error") or "JSON block missing/invalid, inference failed."
#             else: parsed_data["primary_reason"] = parsed_data.get("primary_reason") or "Inferred from report text."
#             q_match = re.search(r"\*\*1\. Clarifying Questions for Vendor\*\*\s*\n([\s\S]*?)(\n\*\*|$)", report_text_extracted, re.IGNORECASE);
#             if q_match: questions_text = q_match.group(1).strip(); potential_questions = re.findall(r"^\s*[-*\d]+\.\s*(.*)", questions_text, re.MULTILINE); parsed_data["clarifying_questions"] = potential_questions or []

#         if parsed_data["outcome_status"] != "error": # Ensure defaults if not error
#              if not parsed_data["primary_reason"]: parsed_data["primary_reason"] = "No specific reason provided."

#         return parsed_data
#     except Exception as e: logger.exception("Unexpected error parsing LLM response."); parsed_data["parsing_error"] = f"Unexpected Parsing Err: {e}"; parsed_data["outcome_status"] = "error"; parsed_data["primary_reason"] = "Unexpected parsing error."; return parsed_data


# # --- Helper function to extract specific info from report text ---
# def extract_from_report(report_text: str, key_phrase: str) -> Optional[str]:
#     """ Extracts value after a key phrase in the report text. """
#     pattern1 = rf"^\s*\*\s*{re.escape(key_phrase)}\s*([^\n]+)"
#     pattern2 = rf"{re.escape(key_phrase)}\s*([^\n]+)"
#     match = re.search(pattern1, report_text, re.IGNORECASE | re.MULTILINE)
#     if not match: match = re.search(pattern2, report_text, re.IGNORECASE | re.MULTILINE)
#     if match:
#         value = match.group(1).strip()
#         if "not found" in value.lower() or not value: return None
#         return value
#     return None

# # --- Main Orchestration Function ---
# def run_c2c_analysis(
#     position_title: str,
#     cv_filename: str,
#     cv_file_bytes: bytes,
#     candidate_email: Optional[str],
#     # User inputs
#     budget_lpa: float,
#     required_location: str,
#     candidate_location_status: str,
#     grad_year_confirmed_by_user: str
# ) -> Dict[str, Any]:
#     """
#     Orchestrates C2C analysis. LLM does initial doc analysis.
#     Runner applies user input priority for budget/location before final status.
#     """
#     start_time = time.time()
#     present_date_str = datetime.now().strftime("%Y-%m-%d")
#     logger.info(f"--- Starting C2C Analysis (V6 - User Input Priority) for Pos: '{position_title}', CV: '{cv_filename}' ---")

#     log_record_id: Optional[str] = None
#     llm_response_record_id: Optional[str] = None
#     candidate_record_id: Optional[str] = None
#     final_result_dict: Dict[str, Any] = { # Structure for frontend
#         "status": "error", "reason": "Analysis did not complete.", "questions": [],
#         "candidate_id": None, "error_message": "Analysis initialization failed.",
#         "raw_output": None
#     }
#     extracted_cv_text: Optional[str] = None

#     try:
#         # 1. Log Initial Attempt
#         log_data = { "applied_position_title": position_title, "cv_filename": cv_filename, "candidate_email": candidate_email, "processing_status": "Received", "Input Budget LPA": budget_lpa, "Input Required Location": required_location, "Input Cand Location Status": candidate_location_status, "Input Grad Year Confirmed": grad_year_confirmed_by_user }
#         log_record_id = ac.create_application_log(log_data)
#         if not log_record_id: final_result_dict["error_message"] = "Failed log start."; logger.error(final_result_dict["error_message"]); return final_result_dict
#         logger.info(f"Initial application log created: {log_record_id}")

#         # 2. Fetch Job Description Details
#         ac.update_application_log(log_record_id, {"Processing Status": "Fetching JD"})
#         jd_details = ac.get_jd_details_by_title(position_title)
#         if not jd_details or 'fields' not in jd_details or not jd_details['fields'].get('Job Description Text'): error_msg = f"JD details missing '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - JD Fetch", "Error Details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         jd_text = jd_details['fields']['Job Description Text']; jd_record_id = jd_details.get('id'); logger.info(f"Successfully fetched JD: {jd_record_id}")

#         # 3. Parse CV
#         ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
#         extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
#         if extracted_cv_text is None or extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:"): error_msg = f"Failed CV parse '{cv_filename}': {extracted_cv_text or 'Unknown.'}"; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error Details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         if not extracted_cv_text.strip(): error_msg = f"CV '{cv_filename}' empty text."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error Details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         logger.info(f"Successfully parsed CV: {cv_filename}")

#         # 4. Prepare and Call LLM (ONLY Docs + Date)
#         ac.update_application_log(log_record_id, {"Processing Status": "LLM Document Analysis"})
#         prompt = CV_ASSESSMENT_PROMPT_TEMPLATE.format(
#             jd_text=jd_text,
#             cv_text=extracted_cv_text,
#             present_date=present_date_str
#         )
#         raw_llm_response_content = None; llm_call_successful = False

#         # --- [LLM Call loop with improved error handling] ---
#         for attempt in range(MAX_RETRIES + 1):
#             last_exception = None # Keep track of last exception
#             try:
#                 logger.info(f"Calling OpenAI API (Temp: {LLM_TEMPERATURE}) (Attempt {attempt + 1}/{MAX_RETRIES + 1})...")
#                 response = openai_client.chat.completions.create( model=OPENAI_MODEL_NAME, messages=[ {"role": "system", "content": "Generate candidate assessment report and initial JSON status based ONLY on JD/CV text."}, {"role": "user", "content": prompt} ], temperature=LLM_TEMPERATURE, max_tokens=MAX_TOKENS_FOR_REPORT )
#                 raw_llm_response_content = response.choices[0].message.content
#                 llm_call_successful = True
#                 logger.info("OpenAI API call successful.")
#                 break # Exit loop on success

#             # --- Specific Error Handling within the loop ---
#             except openai.RateLimitError as e_rate:
#                 logger.error(f"OpenAI Rate Limit/Quota Error (Attempt {attempt + 1}): {e_rate}")
#                 last_exception = e_rate; raw_llm_response_content = f"OpenAI Rate Limit/Quota Error: {e_rate}"; llm_call_successful = False; break
#             except openai.APIConnectionError as e_conn:
#                 logger.warning(f"OpenAI API Connection Error (Attempt {attempt + 1}): {e_conn}. Retrying...")
#                 last_exception = e_conn; raw_llm_response_content = f"OpenAI Connection Error: {e_conn}"; llm_call_successful = False # Will retry below
#             except openai.APIStatusError as e_status:
#                  logger.error(f"OpenAI API Status Error (Attempt {attempt + 1}): {e_status.status_code} - {e_status.response}. Aborting.")
#                  last_exception = e_status; raw_llm_response_content = f"OpenAI API Status Error: {e_status.status_code} - {e_status.message}"; llm_call_successful = False; break
#             except openai.BadRequestError as e_bad_req:
#                  last_exception = e_bad_req
#                  if "context_length_exceeded" in str(e_bad_req): error_msg = "Error: Combined JD/CV text too long for model."; logger.error(error_msg); raw_llm_response_content = error_msg
#                  else: logger.exception(f"OpenAI BadRequest Error (Attempt {attempt + 1}): {e_bad_req}. Aborting."); raw_llm_response_content = f"OpenAI API BadRequest Error: {e_bad_req}"
#                  llm_call_successful = False; break
#             except Exception as e_generic:
#                 logger.exception(f"Unexpected error calling OpenAI API (Attempt {attempt+1}): {e_generic}. Retrying...")
#                 last_exception = e_generic; raw_llm_response_content = f"Unexpected API Error: {e_generic}"; llm_call_successful = False # Will retry below

#             # --- Retry Delay ---
#             if attempt < MAX_RETRIES:
#                 logger.info(f"Waiting {RETRY_DELAY}s before retry...")
#                 time.sleep(RETRY_DELAY)
#             else:
#                  logger.error("Max retries reached for OpenAI API call.")
#                  if llm_call_successful is False and raw_llm_response_content is None: raw_llm_response_content = f"Max retries reached, last error: {last_exception or 'Unknown'}"
#                  llm_call_successful = False # Ensure marked as failed
#         # --- [End of LLM Call loop] ---

#         final_result_dict["raw_output"] = raw_llm_response_content # Store raw output

#         # 5. Log LLM Interaction (Initial Log with FULL LLM Response)
#         llm_log_data = { "associated_log_entry_id": log_record_id, "full_prompt_sent": prompt[:10000], "raw_response_received": str(raw_llm_response_content)[:100000], "parsing_status": "Pending", "Raw Extracted CV Text": extracted_cv_text[:100000] if extracted_cv_text else None }
#         llm_response_record_id = ac.create_llm_response_log(llm_log_data)
#         if llm_response_record_id: link_update_success = ac.update_application_log(log_record_id, {"Associated LLM Response": [llm_response_record_id]}); logger.info(f"LLM log created: {llm_response_record_id}" + (" and linked." if link_update_success else ", link failed."))
#         else: logger.error("Failed create LLM log.")

#         if not llm_call_successful or not raw_llm_response_content:
#             error_msg = f"Failed get report from LLM. Error: {raw_llm_response_content}"
#             logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - LLM Call", "Error Details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict

#         # 6. Parse LLM Response (Gets initial assessment + report text)
#         parsed_llm_data = parse_llm_response_v3(raw_llm_response_content) # Use v3 parser
#         llm_report_text = parsed_llm_data.get("full_report_text") # Get the report part
#         parsing_error_msg = parsed_llm_data.get("parsing_error")

#         # Update LLM log with parsing status ONLY (Report text already logged)
#         parsing_log_status = "Success" if not parsing_error_msg else f"Failure: {parsing_error_msg}"
#         llm_log_update_fields = { "Parsing Status": parsing_log_status }
#         if llm_response_record_id:
#              update_llm_log_success = ac.update_record(ac.LLM_TABLE_ID, llm_response_record_id, llm_log_update_fields)
#              if not update_llm_log_success: logger.warning(f"Failed update LLM log {llm_response_record_id} parsing status.")

#         # Check for parsing errors
#         if parsing_error_msg or parsed_llm_data.get("outcome_status") == "error":
#             error_msg = f"LLM analysis done but response parsing failed/indicated error. Details: {parsing_error_msg or parsed_llm_data.get('primary_reason', 'Unknown')}"
#             logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - LLM Parse", "Error Details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; final_result_dict["questions"] = parsed_llm_data.get("clarifying_questions", []); final_result_dict["status"] = "error"; return final_result_dict

#         # --- Extract Initial LLM Assessment ---
#         llm_initial_status = parsed_llm_data.get("outcome_status")
#         llm_initial_reason = parsed_llm_data.get("primary_reason", "No reason from LLM.")
#         current_questions = list(parsed_llm_data.get("clarifying_questions", [])) # Make a copy

#         # --- 7. POST-LLM VALIDATION & OVERRIDE using User Inputs ---
#         logger.info(f"LLM Initial Assessment: {llm_initial_status}. Reason: {llm_initial_reason}. Initial Questions: {len(current_questions)}")
#         logger.info("Applying User Input Prioritization for Budget & Location...")

#         final_status = llm_initial_status; final_reason = llm_initial_reason; final_questions = current_questions

#         # --- Check 7a: Budget (JD Priority, then User Input) ---
#         llm_extracted_jd_budget_text = extract_from_report(llm_report_text, "Position Budget Extracted:")
#         llm_extracted_cv_cost_text = extract_from_report(llm_report_text, "Candidate Cost/Rate Extracted:")
#         budget_to_use = None; budget_source = "None"

#         if llm_extracted_jd_budget_text:
#             try: budget_to_use = float(re.sub(r'[^\d\.]', '', llm_extracted_jd_budget_text)); budget_source = "JD Text"; logger.info(f"Budget Check: Using budget from JD text: {budget_to_use}")
#             except (ValueError, TypeError): logger.warning(f"Budget Check: Could not parse budget from JD ('{llm_extracted_jd_budget_text}'). Fallback user."); budget_to_use = budget_lpa; budget_source = "User Input (JD Fail)"
#         else: budget_to_use = budget_lpa; budget_source = "User Input (JD N/A)"; logger.info(f"Budget Check: Using budget from user input: {budget_to_use}"); final_questions = [q for q in final_questions if "budget" not in q.lower()]

#         extracted_cv_cost_num = None
#         if llm_extracted_cv_cost_text:
#             try: cost_numeric_str = re.sub(r'[^\d\.]', '', llm_extracted_cv_cost_text.split('/')[0]); extracted_cv_cost_num = float(cost_numeric_str); logger.info(f"Budget Check: Extracted CV cost: {extracted_cv_cost_num} (from: '{llm_extracted_cv_cost_text}')"); final_questions = [q for q in final_questions if "cost/rate" not in q.lower()]
#             except (ValueError, TypeError): logger.warning(f"Budget Check: Could not parse CV cost '{llm_extracted_cv_cost_text}'.");
#             if not any("cost/rate" in q.lower() for q in final_questions): final_questions.append(f"CV cost ('{llm_extracted_cv_cost_text}') unparseable. Clarify rate.")

#         if extracted_cv_cost_num is not None and budget_to_use is not None:
#              # !!! Refine unit comparison if needed !!!
#              if extracted_cv_cost_num > budget_to_use: logger.warning(f"OVERRIDE: CV Cost ({extracted_cv_cost_num}) > Budget ({budget_to_use}, {budget_source}). Rejecting."); final_status = "Rejected"; final_reason = f"Candidate cost from CV ({llm_extracted_cv_cost_text}) exceeds budget ({budget_to_use} LPA from {budget_source})."
#              else: logger.info(f"Budget Check OK: CV Cost ({extracted_cv_cost_num}) <= Budget ({budget_to_use}, {budget_source}).")
#         elif extracted_cv_cost_num is None: logger.info("Budget Check: CV Cost not found/parsed.");
#         if not any("cost/rate" in q.lower() for q in final_questions) and extracted_cv_cost_num is None: final_questions.append("Provide candidate's cost/rate.")


#         # --- Check 7b: Location (User Input Priority) ---
#         if final_status != "Rejected":
#             logger.info("Location Check: Applying user input priority...")
#             llm_extracted_cv_loc = extract_from_report(llm_report_text, "Candidate Location Extracted:")
#             user_req_loc_norm = required_location.lower().strip()
#             cv_loc_norm = llm_extracted_cv_loc.lower().strip() if llm_extracted_cv_loc else None

#             if candidate_location_status == "Candidate is already in the same city where the position is open":
#                 if cv_loc_norm and cv_loc_norm != user_req_loc_norm: logger.warning(f"Location Conflict: User says 'same city', CV '{llm_extracted_cv_loc}' != Req '{required_location}'. Asking.");
#                 if not any("location" in q.lower() and "clarify" in q.lower() for q in final_questions) and cv_loc_norm and cv_loc_norm != user_req_loc_norm: final_questions.append(f"CV location ({llm_extracted_cv_loc}) differs from required ({required_location}), but user indicated 'same city'. Clarify current location.")
#                 final_questions = [q for q in final_questions if "location" not in q.lower() or "clarify" in q.lower()]; logger.info(f"Location Check: OK (User 'same city'). CV: '{llm_extracted_cv_loc}'.")
#             elif candidate_location_status == "Candidate is in different city and will relocate to the location":
#                 logger.info(f"Location Check: OK (User 'will relocate'). CV: '{llm_extracted_cv_loc}'.")
#                 final_questions = [q for q in final_questions if "location" not in q.lower() or "relocate" in q.lower()]
#                 if cv_loc_norm and cv_loc_norm != user_req_loc_norm:
#                      if not any("confirm relocation" in q.lower() for q in final_questions): final_questions.append(f"Confirm willingness/timeline to relocate from '{llm_extracted_cv_loc}' to '{required_location}'.")
#                 elif not cv_loc_norm:
#                      if not any("current location" in q.lower() for q in final_questions): final_questions.append("Confirm current city to assess relocation.")
#             elif candidate_location_status == "Location details not specified/known":
#                 if cv_loc_norm and cv_loc_norm == user_req_loc_norm: final_questions = [q for q in final_questions if "location" not in q.lower()]; logger.info(f"Location Check: OK (CV matches Required, User unknown).")
#                 elif cv_loc_norm and cv_loc_norm != user_req_loc_norm:
#                      logger.warning(f"Location Check: Mismatch needs clarification (CV:'{llm_extracted_cv_loc}', Req:'{required_location}', User unknown).")
#                      if not any("location" in q.lower() and "willingness" in q.lower() for q in final_questions): final_questions.append(f"CV location ({llm_extracted_cv_loc}) differs from required ({required_location}). Confirm location and willingness.")
#                 else: # CV loc missing, user unknown
#                      logger.warning("Location Check: Needs clarification (CV loc missing, User unknown).")
#                      if not any("location" in q.lower() and "willingness" in q.lower() for q in final_questions): final_questions.append(f"Candidate location not in CV. Confirm location and willingness for {required_location}.")

#         # --- Check 7c: Graduation Year Confirmation ---
#         if grad_year_confirmed_by_user == "No": logger.warning("User indicated Grad Year missing/unclear.");
#         if not any("graduation year" in q.lower() for q in final_questions) and grad_year_confirmed_by_user == "No": final_questions.append("User indicated graduation year details unclear/missing. Confirm graduation year(s).")
#         elif grad_year_confirmed_by_user == "Yes": final_questions = [q for q in final_questions if "graduation year" not in q.lower()]


#         # --- 8. Final Status Determination (after overrides) ---
#         final_airtable_outcome = "Error"; final_questions = sorted(list(set(final_questions)))

#         if final_status == "Rejected": logger.info("Final Status: Rejected."); final_airtable_outcome = "Rejected"; final_result_dict["status"] = "rejected"; final_result_dict["reason"] = final_reason; final_result_dict["questions"] = final_questions;
#         elif final_questions: logger.info("Final Status: Clarification Needed."); final_result_dict["status"] = "clarification_needed"; final_result_dict["questions"] = final_questions; final_result_dict["reason"] = llm_initial_reason if final_status != "Matched" else "Clarifications needed."; final_airtable_outcome = "Clarification Needed"
#         else: # Matched
#             logger.info("Final Status: Matched."); final_result_dict["status"] = "matched"; final_result_dict["reason"] = llm_initial_reason; final_result_dict["questions"] = []; final_airtable_outcome = "Matched"
#             # --- Create Candidate Record ---
#             if not jd_record_id: logger.error("Cannot create candidate: JD ID missing."); final_result_dict["status"] = "error"; final_result_dict["reason"] = "System error: Missing JD ID."; final_result_dict["error_message"] = final_result_dict["reason"]; final_airtable_outcome = "Error"
#             else:
#                  # Use extract_from_report for name too
#                  cand_name_extracted = extract_from_report(llm_report_text, "Candidate Name:") or cv_filename
#                  candidate_data = { "associated_log_entry_id": log_record_id, "applied_position_jd_id": jd_record_id, "candidate_name": cand_name_extracted.strip(), "candidate_email": candidate_email, "llm_match_reason": final_result_dict["reason"] }
#                  candidate_record_id = ac.create_successful_candidate(candidate_data)
#                  if candidate_record_id: logger.info(f"Created candidate record: {candidate_record_id}"); final_result_dict["candidate_id"] = candidate_record_id; link_cand_success = ac.update_application_log(log_record_id, {"Associated Candidate Record": [candidate_record_id]}); # Link log
#                  else: logger.error("Failed create candidate record."); final_result_dict["status"] = "error"; final_result_dict["reason"] = "Match determined but failed saving candidate record."; final_result_dict["error_message"] = final_result_dict["reason"]; final_airtable_outcome = "Error"


#         # --- 9. Update Final Airtable Log ---
#         log_updates = { "Processing Status": "Analysis Complete", "Final Outcome": final_airtable_outcome, "Error Details": final_result_dict["reason"] if final_airtable_outcome != "Matched" else None }
#         update_success = ac.update_application_log(log_record_id, log_updates)
#         if not update_success: logger.error(f"CRITICAL: Failed update final status log {log_record_id}.")


#     except Exception as e:
#         logger.exception("Unexpected error during main orchestration.")
#         error_msg = f"System error: {type(e).__name__}: {str(e)}"
#         final_result_dict["status"] = "error"
#         final_result_dict["error_message"] = error_msg
#         final_result_dict["reason"] = error_msg
#         if log_record_id:
#             try:
#                 ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", "Error Details": error_msg})
#             except Exception as log_e:
#                 logger.error(f"Failed log system error: {log_e}")

#     end_time = time.time()
#     logger.info(f"--- C2C Analysis Finished for: '{cv_filename}'. Final Status: {final_result_dict['status']}. Duration: {end_time - start_time:.2f} seconds ---")
#     return final_result_dict # Return the dict with final status/questions/reason/ID

































# # agent/agent_runner.py
# import logging
# import base64
# from typing import Dict, Any, Optional, List, Tuple
# import json
# import time
# import re
# from datetime import datetime
# import google.generativeai as genai
# from google.api_core import exceptions as google_exceptions

# # Use the configured Gemini model object and prompts from agent_definition
# from .agent_definition import (
#     gemini_model_object, GOOGLE_MODEL_NAME,
#     EXTRACT_EXPERIENCE_PROMPT,
#     CHECK_EDUCATION_YEARS_PROMPT,
#     GENERATE_DETAILED_REPORT_PROMPT,
#     logger as agent_logger
# )

# # Import backend functions directly
# # Import LLM_TABLE_ID as well
# from backend import airtable_client as ac
# from backend.cv_parser import extract_text_from_cv_bytes

# logger = logging.getLogger(__name__)
# if not logger.hasHandlers():
#      logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')

# # --- Constants ---
# MAX_RETRIES = 1
# RETRY_DELAY = 7
# MAX_TOKENS_EXPERIENCE = 100
# MAX_TOKENS_EDUCATION = 50
# MAX_TOKENS_BACKEND_REPORT = 4000 # Allow ample space for the final report
# LLM_TEMPERATURE = 0.1 # Lower temp for focused extraction

# # Safety settings for Gemini
# SAFETY_SETTINGS = [
#     {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
#     for c in [ "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
#                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT" ]
# ]

# # Keywords indicating a flexible budget (case-insensitive)
# FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open budget"]

# # --- Field ID Constants (Added for Robustness) ---
# # Application Logs Table
# APP_LOG_ERROR_DETAILS_FIELD_ID = "fldsg8CrkSMaEnhse" # The Field ID for 'Error Details'
# APP_LOG_ASSOC_CAND_REC_FIELD_ID = "fldD5bIKxiUb2JHry" # Field ID for 'Associated Candidate Record'
# APP_LOG_ASSOC_LLM_RESP_FIELD_ID = "fldXwS52KFi2dtiGn" # Field ID for 'Associated LLM Response' (Optional, might use if linking)

# # LLM Responses Table
# LLM_RESP_BACKEND_REPORT_FIELD_ID = "fldT6GWBGOvh3SbA9" # Field ID for 'Backend Analysis Report'
# LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID = "fldWWyUKg6fEjPELr" # Field ID for 'Associated Log Entry'
# LLM_RESP_FULL_PROMPT_FIELD_ID = "fldNmJ8f4mRaxyjbH" # Field ID for 'Full Prompt Sent'
# LLM_RESP_RAW_RESPONSE_FIELD_ID = "fldjbykqqB8H1U4CV" # Field ID for 'Raw Response Received'
# LLM_RESP_PARSING_STATUS_FIELD_ID = "fldvinsTvct2MbidE" # Field ID for 'Parsing Status'


# # --- Helper Functions ---
# # (parse_llm_float, parse_llm_yes_no_unclear, call_llm remain the same as the previous version)
# def parse_llm_float(text: Optional[str]) -> Optional[float]:
#     """Attempts to parse LLM text output into a float."""
#     if not text: return None
#     try:
#         # Improved regex to handle various number formats including leading/trailing non-digits
#         match = re.search(r"[-+]?\d*\.?\d+", text)
#         if match:
#             return float(match.group(0))
#         else:
#             # Try converting common words if number extraction fails
#             text_lower = text.strip().lower()
#             if text_lower == "unknown": return None # Explicitly handle "Unknown"
#             # Add more word-to-number conversions if needed, e.g., "ten" -> 10.0
#             return None # Default return None if no number found
#     except (ValueError, TypeError):
#         logger.warning(f"Could not parse '{text}' as float.")
#         return None


# def parse_llm_yes_no_unclear(text: Optional[str]) -> Optional[str]:
#     """Parses LLM text for Yes/No/Unclear, case-insensitive."""
#     if not text: return "Unclear"
#     text_lower = text.strip().lower()
#     if "yes" in text_lower: return "Yes" # Check if 'yes' is substring
#     if "no" in text_lower: return "No"   # Check if 'no' is substring
#     return "Unclear" # Default to Unclear if neither 'yes' nor 'no' is found

# def call_llm(prompt: str, max_tokens: int, temperature: float = LLM_TEMPERATURE) -> Tuple[Optional[str], Optional[str]]:
#     """ Helper to call LLM with retry logic. Returns (response_text, error_message). """
#     response_text: Optional[str] = None
#     error_message: Optional[str] = None
#     last_exception = None

#     if not gemini_model_object:
#         return None, "LLM model not initialized."

#     gen_config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)

#     for attempt in range(MAX_RETRIES + 1):
#         try:
#             logger.info(f"Calling LLM (Attempt {attempt+1}/{MAX_RETRIES+1})...")
#             response = gemini_model_object.generate_content(
#                 prompt, generation_config=gen_config, safety_settings=SAFETY_SETTINGS
#             )
#             # Handle potential lack of 'candidates' or other response issues
#             if not response.candidates:
#                 feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else None
#                 block_reason = feedback.block_reason if feedback and hasattr(feedback, 'block_reason') else "Unknown"
#                 safety_ratings = feedback.safety_ratings if feedback and hasattr(feedback, 'safety_ratings') else "N/A"
#                 error_message = f"LLM call blocked. Reason: {block_reason}. Ratings: {safety_ratings}"
#                 logger.error(error_message)
#                 break # Exit loop if blocked

#             # Check if the first candidate has content
#             if not response.candidates[0].content or not response.candidates[0].content.parts:
#                  finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'
#                  error_message = f"LLM returned no content parts. Finish Reason: {finish_reason}"
#                  logger.error(error_message)
#                  # Optionally break or retry depending on finish_reason
#                  # if finish_reason == genai.types.FinishReason.SAFETY: break
#                  break # Stop if no content

#             # Safely access text
#             try:
#                 # Directly use response.text as it seems to work for Gemini's text models
#                 # If using function calling later, this needs adjustment.
#                 response_text = response.text
#             except ValueError:
#                  # Handle cases where response.text might raise ValueError (e.g., function calls expected but text tried)
#                  logger.warning("LLM response did not contain direct text, might be expecting function call.")
#                  # Find the first text part if available - Fallback
#                  response_text = next((part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')), None)


#             if response_text is not None: response_text = response_text.strip()
#             if not response_text:
#                  # Check finish reason again if text is empty after stripping
#                  finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'
#                  error_message = f"LLM returned empty text response. Finish Reason: {finish_reason}"
#                  logger.error(error_message)
#                  break # Stop if empty text
#             error_message = None
#             logger.info("LLM call successful.")
#             break
#         except google_exceptions.ResourceExhausted as e:
#             error_message = f"API Quota Error: {e}"; last_exception = e; logger.error(error_message); break
#         except google_exceptions.InvalidArgument as e:
#             error_message = f"API Invalid Argument: {e}"; last_exception = e; logger.error(error_message); break
#         except Exception as e:
#             error_message = f"API Call Error: {e}"; last_exception = e; logger.exception(f"LLM Call Error (Attempt {attempt+1}): {e}")
#         if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY)
#         else:
#             logger.error("Max retries reached for LLM call.")
#             error_message = error_message or f"Max retries, last error: {last_exception or 'Unknown'}"

#     return response_text, error_message

# # --- Main Orchestration Function (New Workflow) ---
# def run_c2c_analysis(
#     position_title: str,
#     cv_filename: str,
#     cv_file_bytes: bytes,
#     candidate_email: Optional[str],
#     candidate_expected_payout_pm: float, # Frontend input
#     candidate_current_location: str, # Frontend input
#     grad_year_confirmed_by_user: str # Frontend input - NOT USED FOR STRICT CHECK per req
# ) -> Dict[str, Any]:
#     """
#     Orchestrates C2C analysis with a preliminary strict check stage.
#     """
#     start_time = time.time()
#     present_date_str = datetime.now().strftime("%Y-%m-%d")
#     logger.info(f"--- Starting C2C Analysis (V22 - Log Report to LLM Table) for Pos: '{position_title}', CV: '{cv_filename}' ---")

#     # --- Initialize Variables ---
#     log_record_id: Optional[str] = None
#     candidate_record_id: Optional[str] = None
#     llm_response_record_id: Optional[str] = None # To store ID of the LLM response log
#     final_result_dict: Dict[str, Any] = { "status": "error", "reason": "Analysis init failed.", "questions": [], "candidate_id": None, "error_message": "Analysis init failed."}
#     extracted_cv_text: Optional[str] = None
#     jd_details: Optional[Dict] = None; jd_record_id: Optional[str] = None
#     jd_budget_value: Optional[float] = None; jd_required_location_value: Optional[str] = None
#     jd_min_experience: Optional[float] = None
#     is_budget_flexible: bool = False
#     backend_report: Optional[str] = None

#     try:
#         # --- Step 1: Log Initial Attempt ---
#         log_data = { "applied_position_title": position_title, "cv_filename": cv_filename, "candidate_email": candidate_email, "processing_status": "Received" }
#         log_record_id = ac.create_application_log(log_data)
#         if not log_record_id:
#             final_result_dict["error_message"] = "Failed create app log."; logger.error(final_result_dict["error_message"]); return final_result_dict
#         logger.info(f"Initial app log created: {log_record_id}")

#         # --- Step 2: Fetch JD Details ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Fetching JD"})
#         jd_details_record = ac.get_jd_details_by_title(position_title)
#         if not jd_details_record or 'fields' not in jd_details_record or not jd_details_record['fields'].get('Job Description Text'):
#             error_msg = f"JD details/text not found for '{position_title}'."; logger.error(error_msg);
#             ac.update_application_log(log_record_id, {"Processing Status": "Error - JD Fetch", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#             final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         jd_details = jd_details_record['fields']; jd_record_id = jd_details_record.get('id'); jd_text = jd_details['Job Description Text']
#         jd_budget_raw = jd_details.get('Budget'); jd_required_location_value = jd_details.get('Location')
#         jd_min_experience_raw = jd_details.get('Minimum experience in years')
#         # Budget & Experience Parsing (same as previous version)
#         if jd_budget_raw and isinstance(jd_budget_raw, str):
#              if any(keyword in jd_budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS):
#                  is_budget_flexible = True; jd_budget_value = None; logger.info(f"JD Budget is flexible: '{jd_budget_raw}'.")
#              else:
#                  try:
#                      cleaned_budget = re.sub(r'[^\d\.]', '', jd_budget_raw.replace(',', ''))
#                      jd_budget_value = float(cleaned_budget) if cleaned_budget else None
#                  except (ValueError, TypeError):
#                      logger.warning(f"Could not parse Budget text ('{jd_budget_raw}') JD {jd_record_id}."); jd_budget_value = None
#         elif isinstance(jd_budget_raw, (int, float)): jd_budget_value = float(jd_budget_raw)
#         else: jd_budget_value = None
#         if isinstance(jd_min_experience_raw, (int, float)): jd_min_experience = float(jd_min_experience_raw)
#         else: jd_min_experience = None; logger.warning(f"JD 'Minimum experience in years' field missing/not a number for JD {jd_record_id}.")
#         logger.info(f"Fetched JD: {jd_record_id}. Budget: {jd_budget_value} (Flex: {is_budget_flexible}), Location: '{jd_required_location_value}', Min Exp: {jd_min_experience}")


#         # --- Step 3: Parse CV Text ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
#         extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
#         if isinstance(extracted_cv_text, str) and (extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:")):
#              error_msg = f"CV parse issue '{cv_filename}': {extracted_cv_text}"; logger.error(error_msg);
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         elif not extracted_cv_text or not isinstance(extracted_cv_text, str) or not extracted_cv_text.strip():
#              error_msg = f"CV parse fail/empty '{cv_filename}'."; logger.error(error_msg);
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         logger.info(f"Parsed CV: {cv_filename} ({len(extracted_cv_text)} chars)")

#         # --- ========== STAGE 1: PRELIMINARY STRICT CHECKS ========== ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Performing Strict Checks"})
#         logger.info("--- Starting Stage 1: Strict Parameter Checks ---")
#         # Salary Check (same as previous version)
#         salary_match = False; salary_reject_reason = None; cost_to_use = candidate_expected_payout_pm; budget_to_use = jd_budget_value
#         logger.info(f"Strict Check 1 (Salary): Payout {cost_to_use} vs Budget {budget_to_use} (Flex: {is_budget_flexible})")
#         if is_budget_flexible: salary_match = True; logger.info("Salary Check: PASS (Flexible)")
#         elif budget_to_use is None: salary_match = True; salary_reject_reason = "Budget missing/invalid in JD. Clarification needed."; logger.warning(f"Salary Check: Clarification ({salary_reject_reason})")
#         elif cost_to_use > budget_to_use: salary_match = False; salary_reject_reason = f"Candidate payout ({cost_to_use}) exceeds JD budget ({budget_to_use})."; logger.warning(f"Salary Check: FAIL ({salary_reject_reason})")
#         else: salary_match = True; logger.info("Salary Check: PASS (Within Budget)")
#         if not salary_match:
#             logger.warning(f"Strict Check FAILED: Salary. Reason: {salary_reject_reason}")
#             ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", APP_LOG_ERROR_DETAILS_FIELD_ID: salary_reject_reason})
#             final_result_dict["status"] = "rejected"; final_result_dict["reason"] = salary_reject_reason; return final_result_dict

#         # Experience Check (same as previous version)
#         experience_match = False; experience_reject_reason = None; candidate_experience_years: Optional[float] = None
#         logger.info(f"Strict Check 2 (Experience): CV vs JD Min ({jd_min_experience} years)")
#         if jd_min_experience is None: experience_match = True; logger.info("Experience Check: PASS (No Min Spec)")
#         else:
#             exp_prompt = EXTRACT_EXPERIENCE_PROMPT.format(cv_text=extracted_cv_text); exp_text, exp_error = call_llm(exp_prompt, MAX_TOKENS_EXPERIENCE)
#             if exp_error: experience_match = True; experience_reject_reason = f"LLM Error verifying experience: {exp_error}. Manual review needed."; logger.error(f"Experience Check: Clarification (LLM Error) - {exp_error}")
#             else:
#                 candidate_experience_years = parse_llm_float(exp_text); logger.info(f"LLM Extracted Exp: {candidate_experience_years} (Raw: '{exp_text}')")
#                 if candidate_experience_years is None: experience_match = True; experience_reject_reason = "Cannot determine experience years from CV. Manual review needed."; logger.warning(f"Experience Check: Clarification ({experience_reject_reason})")
#                 elif candidate_experience_years < jd_min_experience: experience_match = False; experience_reject_reason = f"Candidate experience ({candidate_experience_years} yrs) < Min required ({jd_min_experience} yrs)."; logger.warning(f"Experience Check: FAIL ({experience_reject_reason})")
#                 else: experience_match = True; logger.info("Experience Check: PASS (Met/Exceeded)")
#         if not experience_match:
#             logger.warning(f"Strict Check FAILED: Experience. Reason: {experience_reject_reason}")
#             ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", APP_LOG_ERROR_DETAILS_FIELD_ID: experience_reject_reason})
#             final_result_dict["status"] = "rejected"; final_result_dict["reason"] = experience_reject_reason; return final_result_dict

#         # Education Years Check (same as previous version)
#         education_years_present = False; education_clarification_q = None
#         logger.info("Strict Check 3 (Education Years): Checking CV")
#         edu_prompt = CHECK_EDUCATION_YEARS_PROMPT.format(cv_text=extracted_cv_text); edu_text, edu_error = call_llm(edu_prompt, MAX_TOKENS_EDUCATION)
#         if edu_error: education_years_present = False; education_clarification_q = f"LLM Error verifying education years: {edu_error}"; logger.error(f"Edu Years Check: UNCLEAR (LLM Error) - {edu_error}")
#         else:
#             edu_result = parse_llm_yes_no_unclear(edu_text); logger.info(f"LLM Edu Years Check: {edu_result} (Raw: '{edu_text}')")
#             if edu_result == "Yes": education_years_present = True; logger.info("Edu Years Check: PASS (Mentioned)")
#             else: education_years_present = False; education_clarification_q = "CV does not clearly mention specific graduation years. Clarification needed."; logger.warning(f"Edu Years Check: FAIL/UNCLEAR ({education_clarification_q})")

#         # Collect Clarification Reasons (same as previous version)
#         clarification_reasons = []
#         if salary_reject_reason and "Clarification needed" in salary_reject_reason: clarification_reasons.append(salary_reject_reason)
#         if experience_reject_reason and "Clarification Needed" in experience_reject_reason: clarification_reasons.append(experience_reject_reason) # Note: Check string might differ slightly
#         if experience_reject_reason and "Manual review needed" in experience_reject_reason: clarification_reasons.append(experience_reject_reason)
#         if not education_years_present and education_clarification_q: clarification_reasons.append(education_clarification_q)
#         if clarification_reasons:
#              logger.warning("Strict Checks require CLARIFICATION.")
#              combined_reason = "; ".join(clarification_reasons)
#              ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Clarification Needed", APP_LOG_ERROR_DETAILS_FIELD_ID: combined_reason})
#              final_result_dict["status"] = "clarification_needed"; final_result_dict["reason"] = "Clarification needed regarding candidate details."; final_result_dict["questions"] = clarification_reasons
#              return final_result_dict


#         # --- ========== STAGE 1 PASSED ========== ---
#         logger.info("--- Preliminary Strict Checks PASSED ---")
#         ac.update_application_log(log_record_id, {"Processing Status": "Preliminary Checks Passed"})

#         # --- ========== STAGE 2: Generate Backend Report ========== ---
#         logger.info("--- Starting Stage 2: Generating Detailed Backend Report ---")
#         ac.update_application_log(log_record_id, {"Processing Status": "Generating Backend Report"})

#         report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format(
#             jd_text=jd_text,
#             cv_text=extracted_cv_text,
#             present_date_str=present_date_str,
#             candidate_expected_payout_pm=candidate_expected_payout_pm,
#             candidate_current_location=candidate_current_location
#         )

#         backend_report, report_error = call_llm(report_prompt, MAX_TOKENS_BACKEND_REPORT, temperature=0.2)

#         # --- *** NEW: Log Backend Report to LLM Responses Table *** ---
#         logger.info("Logging Backend Report interaction to LLM Responses table...")
#         llm_log_record = None
#         llm_response_record_id = None # Reset before trying to create
#         if ac.LLM_TABLE_ID: # Check if the LLM Table ID is configured
#             parsing_status = "Success (Report Generated)" if not report_error else "Failure (Report Generation Error)"
#             report_content_for_log = backend_report if not report_error else f"Error generating report: {report_error}"
#             raw_response_for_log = backend_report if not report_error else report_error # Store error here too if it happened

#             llm_log_fields = {
#                 LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID: [log_record_id], # Link back to Application Log
#                 LLM_RESP_FULL_PROMPT_FIELD_ID: report_prompt[:100000], # Log the prompt (limit size)
#                 LLM_RESP_RAW_RESPONSE_FIELD_ID: raw_response_for_log[:100000] if raw_response_for_log else "N/A", # Log raw response/error
#                 LLM_RESP_BACKEND_REPORT_FIELD_ID: report_content_for_log[:100000] if report_content_for_log else "N/A", # Log the report/error here
#                 LLM_RESP_PARSING_STATUS_FIELD_ID: parsing_status
#             }
#             try:
#                 llm_log_record = ac.create_record(ac.LLM_TABLE_ID, llm_log_fields)
#                 if llm_log_record and llm_log_record.get('id'):
#                     llm_response_record_id = llm_log_record['id']
#                     logger.info(f"Successfully created LLM Response log record: {llm_response_record_id}")
#                     # Optionally link this LLM log back to the main log if needed (using APP_LOG_ASSOC_LLM_RESP_FIELD_ID)
#                     # ac.update_application_log(log_record_id, {APP_LOG_ASSOC_LLM_RESP_FIELD_ID: [llm_response_record_id]})
#                 else:
#                     logger.error("Failed to create LLM Response log record (backend returned null/invalid).")
#             except Exception as llm_log_err:
#                 logger.exception(f"Error creating LLM Response log record: {llm_log_err}")
#         else:
#             logger.warning("AIRTABLE_LLM_TABLE_ID not configured. Skipping LLM Response table logging.")

#         # --- Handle Report Generation Error (if not already handled by check) ---
#         if report_error and not llm_log_record: # If logging failed AND report failed
#              # Log the error in the main log's error details as a fallback
#              error_msg = f"Preliminary checks passed, but failed to generate/log backend report: {report_error}"
#              logger.error(error_msg)
#              ac.update_application_log(log_record_id, {APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              # Decide if this is critical - perhaps proceed to create candidate but flag the issue
#              # For now, let's continue but the error is noted.

#         # --- Create Successful Candidate Record ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
#         name_match = re.search(r"Name:\s*(.*)|candidate name:\s*(.*)|^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z.'-]+)+)", extracted_cv_text, re.IGNORECASE | re.MULTILINE)
#         cand_name_extracted = name_match.group(1) or name_match.group(2) or name_match.group(3) if name_match else cv_filename

#         candidate_data = {
#              "associated_log_entry_id": log_record_id,
#              "applied_position_jd_id": jd_record_id,
#              "candidate_name": cand_name_extracted.strip()[:100],
#              "candidate_email": candidate_email,
#              "llm_match_reason": "Passed preliminary checks (Salary, Experience, Education Years)."
#              # Removed backend report from here
#         }
#         candidate_record_id = ac.create_successful_candidate(candidate_data)

#         if candidate_record_id:
#              logger.info(f"Created successful candidate record: {candidate_record_id}")
#              link_cand_success = ac.update_application_log(log_record_id, {APP_LOG_ASSOC_CAND_REC_FIELD_ID: [candidate_record_id]}) # Use Field ID
#              if not link_cand_success: logger.warning(f"Failed link Cand Record {candidate_record_id} to Log {log_record_id}.")
#              final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = []; final_airtable_outcome = "Matched"
#         else:
#              logger.error("Passed checks, but failed to create candidate record in Airtable.")
#              error_msg = "Passed preliminary checks, but failed saving candidate record."
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_status = "error"; final_reason = error_msg; final_questions = []; final_airtable_outcome = "Error"


#         # --- Update Final Log Status ---
#         # *** MODIFIED: Error Details field ONLY contains the reason for non-match/error/clarification ***
#         final_log_details_content = None
#         if final_airtable_outcome not in ["Matched"]:
#             final_log_details_content = final_reason or "Analysis complete with non-match outcome." # Use the reason if available

#         log_updates = {
#             "Processing Status": "Analysis Complete",
#             "Final Outcome": final_airtable_outcome,
#         }
#         # Only add Error Details if there's content for it
#         if final_log_details_content:
#              log_updates[APP_LOG_ERROR_DETAILS_FIELD_ID] = final_log_details_content[:100000] # Limit length

#         update_success = ac.update_application_log(log_record_id, log_updates)
#         if not update_success:
#             logger.error(f"CRITICAL: Failed update final status log {log_record_id}. Check Airtable/Logs.")

#         # Prepare final result dictionary
#         final_result_dict["status"] = final_status
#         final_result_dict["reason"] = final_reason
#         final_result_dict["questions"] = final_questions # These are from Stage 1 checks
#         final_result_dict["candidate_id"] = candidate_record_id
#         final_result_dict["error_message"] = final_reason if final_status == "error" else None
#         # Optionally include the LLM response record ID in the result
#         final_result_dict["llm_response_log_id"] = llm_response_record_id


#     except Exception as e:
#         logger.exception("Unexpected error during main orchestration.")
#         error_msg = f"System error: {type(e).__name__}: {str(e)}"
#         final_result_dict["status"] = "error"; final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg
#         if log_record_id:
#             try:
#                 ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#             except Exception as log_e:
#                 logger.error(f"Failed log system error: {log_e}")

#     # --- Final Logging & Return ---
#     end_time = time.time()
#     logger.info(f"--- C2C Analysis Finished: '{cv_filename}'. Final Status: {final_result_dict['status']}. Duration: {end_time - start_time:.2f}s ---")
#     return final_result_dict

















# # agent/agent_runner.py
# import logging
# import base64
# from typing import Dict, Any, Optional, List, Tuple
# import json
# import time
# import re
# from datetime import datetime
# import google.generativeai as genai
# from google.api_core import exceptions as google_exceptions

# # Use the configured Gemini model object and prompts from agent_definition
# from .agent_definition import (
#     gemini_model_object, GOOGLE_MODEL_NAME,
#     EXTRACT_EXPERIENCE_PROMPT,
#     CHECK_EDUCATION_YEARS_PROMPT,
#     GENERATE_DETAILED_REPORT_PROMPT,
#     logger as agent_logger
# )

# # Import backend functions directly
# # Import LLM_TABLE_ID as well
# from backend import airtable_client as ac
# from backend.cv_parser import extract_text_from_cv_bytes

# logger = logging.getLogger(__name__)
# if not logger.hasHandlers():
#      logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')

# # --- Constants ---
# MAX_RETRIES = 1
# RETRY_DELAY = 7
# MAX_TOKENS_EXPERIENCE = 100
# MAX_TOKENS_EDUCATION = 50
# MAX_TOKENS_BACKEND_REPORT = 4000 # Allow ample space for the final report
# LLM_TEMPERATURE = 0.1 # Lower temp for focused extraction

# # Safety settings for Gemini
# SAFETY_SETTINGS = [
#     {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
#     for c in [ "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
#                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT" ]
# ]

# # Keywords indicating a flexible budget (case-insensitive)
# FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open budget"]

# # --- Field ID Constants (Added for Robustness) ---
# # Application Logs Table
# APP_LOG_ERROR_DETAILS_FIELD_ID = "fldsg8CrkSMaEnhse" # The Field ID for 'Error Details'
# APP_LOG_ASSOC_CAND_REC_FIELD_ID = "fldD5bIKxiUb2JHry" # Field ID for 'Associated Candidate Record'
# APP_LOG_ASSOC_LLM_RESP_FIELD_ID = "fldXwS52KFi2dtiGn" # Field ID for 'Associated LLM Response' (Optional, might use if linking)

# # LLM Responses Table
# LLM_RESP_BACKEND_REPORT_FIELD_ID = "fldT6GWBGOvh3SbA9" # Field ID for 'Backend Analysis Report'
# LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID = "fldWWyUKg6fEjPELr" # Field ID for 'Associated Log Entry'
# LLM_RESP_FULL_PROMPT_FIELD_ID = "fldNmJ8f4mRaxyjbH" # Field ID for 'Full Prompt Sent'
# LLM_RESP_RAW_RESPONSE_FIELD_ID = "fldjbykqqB8H1U4CV" # Field ID for 'Raw Response Received'
# LLM_RESP_PARSING_STATUS_FIELD_ID = "fldvinsTvct2MbidE" # Field ID for 'Parsing Status'


# # --- Helper Functions ---
# def parse_llm_float(text: Optional[str]) -> Optional[float]:
#     """Attempts to parse LLM text output into a float."""
#     if not text: return None
#     try:
#         # Improved regex to handle various number formats including leading/trailing non-digits
#         match = re.search(r"[-+]?\d*\.?\d+", text)
#         if match:
#             return float(match.group(0))
#         else:
#             # Try converting common words if number extraction fails
#             text_lower = text.strip().lower()
#             if text_lower == "unknown": return None # Explicitly handle "Unknown"
#             # Add more word-to-number conversions if needed, e.g., "ten" -> 10.0
#             return None # Default return None if no number found
#     except (ValueError, TypeError):
#         logger.warning(f"Could not parse '{text}' as float.")
#         return None


# def parse_llm_yes_no_unclear(text: Optional[str]) -> Optional[str]:
#     """Parses LLM text for Yes/No/Unclear, case-insensitive."""
#     if not text: return "Unclear"
#     text_lower = text.strip().lower()
#     if "yes" in text_lower: return "Yes" # Check if 'yes' is substring
#     if "no" in text_lower: return "No"   # Check if 'no' is substring
#     return "Unclear" # Default to Unclear if neither 'yes' nor 'no' is found

# def call_llm(prompt: str, max_tokens: int, temperature: float = LLM_TEMPERATURE) -> Tuple[Optional[str], Optional[str]]:
#     """ Helper to call LLM with retry logic. Returns (response_text, error_message). """
#     response_text: Optional[str] = None
#     error_message: Optional[str] = None
#     last_exception = None

#     if not gemini_model_object:
#         return None, "LLM model not initialized."

#     gen_config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)

#     for attempt in range(MAX_RETRIES + 1):
#         try:
#             logger.info(f"Calling LLM (Attempt {attempt+1}/{MAX_RETRIES+1})...")
#             response = gemini_model_object.generate_content(
#                 prompt, generation_config=gen_config, safety_settings=SAFETY_SETTINGS
#             )
#             # Handle potential lack of 'candidates' or other response issues
#             if not response.candidates:
#                 feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else None
#                 block_reason = feedback.block_reason if feedback and hasattr(feedback, 'block_reason') else "Unknown"
#                 safety_ratings = feedback.safety_ratings if feedback and hasattr(feedback, 'safety_ratings') else "N/A"
#                 error_message = f"LLM call blocked. Reason: {block_reason}. Ratings: {safety_ratings}"
#                 logger.error(error_message)
#                 break # Exit loop if blocked

#             # Check if the first candidate has content
#             if not response.candidates[0].content or not response.candidates[0].content.parts:
#                  finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'
#                  error_message = f"LLM returned no content parts. Finish Reason: {finish_reason}"
#                  logger.error(error_message)
#                  # Optionally break or retry depending on finish_reason
#                  # if finish_reason == genai.types.FinishReason.SAFETY: break
#                  break # Stop if no content

#             # Safely access text
#             try:
#                 # Directly use response.text as it seems to work for Gemini's text models
#                 # If using function calling later, this needs adjustment.
#                 response_text = response.text
#             except ValueError:
#                  # Handle cases where response.text might raise ValueError (e.g., function calls expected but text tried)
#                  logger.warning("LLM response did not contain direct text, might be expecting function call.")
#                  # Find the first text part if available - Fallback
#                  response_text = next((part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')), None)


#             if response_text is not None: response_text = response_text.strip()
#             if not response_text:
#                  # Check finish reason again if text is empty after stripping
#                  finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'
#                  error_message = f"LLM returned empty text response. Finish Reason: {finish_reason}"
#                  logger.error(error_message)
#                  break # Stop if empty text
#             error_message = None
#             logger.info("LLM call successful.")
#             break
#         except google_exceptions.ResourceExhausted as e:
#             error_message = f"API Quota Error: {e}"; last_exception = e; logger.error(error_message); break
#         except google_exceptions.InvalidArgument as e:
#             error_message = f"API Invalid Argument: {e}"; last_exception = e; logger.error(error_message); break
#         except Exception as e:
#             error_message = f"API Call Error: {e}"; last_exception = e; logger.exception(f"LLM Call Error (Attempt {attempt+1}): {e}")
#         if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY)
#         else:
#             logger.error("Max retries reached for LLM call.")
#             error_message = error_message or f"Max retries, last error: {last_exception or 'Unknown'}"

#     return response_text, error_message

# # --- Main Orchestration Function (New Workflow) ---
# def run_c2c_analysis(
#     position_title: str,
#     cv_filename: str,
#     cv_file_bytes: bytes,
#     candidate_email: Optional[str],
#     candidate_expected_payout_pm: float, # Frontend input
#     candidate_current_location: str, # Frontend input
#     grad_year_confirmed_by_user: str # Frontend input - NOT USED FOR STRICT CHECK per req
# ) -> Dict[str, Any]:
#     """
#     Orchestrates C2C analysis with a preliminary strict check stage.
#     Logs detailed report to LLM Responses table.
#     """
#     start_time = time.time()
#     present_date_str = datetime.now().strftime("%Y-%m-%d")
#     logger.info(f"--- Starting C2C Analysis (V22 - Log Report to LLM Table) for Pos: '{position_title}', CV: '{cv_filename}' ---")

#     # --- Initialize Variables ---
#     log_record_id: Optional[str] = None
#     candidate_record_id: Optional[str] = None
#     llm_response_record_id: Optional[str] = None # To store ID of the LLM response log
#     final_result_dict: Dict[str, Any] = { "status": "error", "reason": "Analysis init failed.", "questions": [], "candidate_id": None, "error_message": "Analysis init failed.", "llm_response_log_id": None }
#     extracted_cv_text: Optional[str] = None
#     jd_details: Optional[Dict] = None; jd_record_id: Optional[str] = None
#     jd_budget_value: Optional[float] = None; jd_required_location_value: Optional[str] = None
#     jd_min_experience: Optional[float] = None
#     is_budget_flexible: bool = False
#     backend_report: Optional[str] = None
#     report_prompt: Optional[str] = None # Store the prompt used for the report

#     try:
#         # --- Step 1: Log Initial Attempt ---
#         log_data = { "applied_position_title": position_title, "cv_filename": cv_filename, "candidate_email": candidate_email, "processing_status": "Received" }
#         log_record_id = ac.create_application_log(log_data)
#         if not log_record_id:
#             final_result_dict["error_message"] = "Failed create initial app log."; logger.error(final_result_dict["error_message"]); return final_result_dict
#         logger.info(f"Initial app log created: {log_record_id}")

#         # --- Step 2: Fetch JD Details ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Fetching JD"})
#         jd_details_record = ac.get_jd_details_by_title(position_title)
#         if not jd_details_record or 'fields' not in jd_details_record or not jd_details_record['fields'].get('Job Description Text'):
#             error_msg = f"JD details or required 'Job Description Text' field not found for '{position_title}'."; logger.error(error_msg);
#             ac.update_application_log(log_record_id, {"Processing Status": "Error - JD Fetch", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#             final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         jd_details = jd_details_record['fields']; jd_record_id = jd_details_record.get('id'); jd_text = jd_details['Job Description Text']
#         jd_budget_raw = jd_details.get('Budget'); jd_required_location_value = jd_details.get('Location')
#         jd_min_experience_raw = jd_details.get('Minimum experience in years')

#         # Parse Budget & Check Flexibility
#         if jd_budget_raw and isinstance(jd_budget_raw, str):
#              if any(keyword in jd_budget_raw.lower() for keyword in FLEXIBLE_BUDGET_KEYWORDS):
#                  is_budget_flexible = True; jd_budget_value = None; logger.info(f"JD Budget is flexible: '{jd_budget_raw}'.")
#              else:
#                  try:
#                      cleaned_budget = re.sub(r'[^\d\.]', '', jd_budget_raw.replace(',', ''))
#                      jd_budget_value = float(cleaned_budget) if cleaned_budget else None
#                  except (ValueError, TypeError):
#                      logger.warning(f"Could not parse Budget text ('{jd_budget_raw}') from JD {jd_record_id}. Treating as missing/invalid."); jd_budget_value = None
#         elif isinstance(jd_budget_raw, (int, float)): jd_budget_value = float(jd_budget_raw)
#         else: jd_budget_value = None

#         # Parse Min Experience (Number field)
#         if isinstance(jd_min_experience_raw, (int, float)): jd_min_experience = float(jd_min_experience_raw)
#         else: jd_min_experience = None; logger.warning(f"JD 'Minimum experience in years' field is missing or not a number for JD {jd_record_id}. Cannot perform experience check.")

#         logger.info(f"Fetched JD: {jd_record_id}. Budget: {jd_budget_value} (Flex: {is_budget_flexible}), Location: '{jd_required_location_value}', Min Exp: {jd_min_experience}")


#         # --- Step 3: Parse CV Text ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
#         extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
#         if isinstance(extracted_cv_text, str) and (extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:")):
#              error_msg = f"CV parsing issue for '{cv_filename}': {extracted_cv_text}"; logger.error(error_msg);
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         elif not extracted_cv_text or not isinstance(extracted_cv_text, str) or not extracted_cv_text.strip():
#              error_msg = f"CV parsing failed or resulted in empty text for '{cv_filename}'."; logger.error(error_msg);
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         logger.info(f"Parsed CV: {cv_filename} ({len(extracted_cv_text)} chars)")

#         # --- ========== STAGE 1: PRELIMINARY STRICT CHECKS ========== ---
#         ac.update_application_log(log_record_id, {"Processing Status": "Performing Strict Checks"})
#         logger.info("--- Starting Stage 1: Strict Parameter Checks ---")
#         clarification_reasons = []

#         # --- Check 1: Salary Expectation vs Budget ---
#         salary_match = True # Assume pass unless explicitly failed or needs clarification
#         salary_check_reason = None
#         cost_to_use = candidate_expected_payout_pm
#         budget_to_use = jd_budget_value
#         logger.info(f"Strict Check 1 (Salary): Payout {cost_to_use} vs Budget {budget_to_use} (Flex: {is_budget_flexible})")
#         if is_budget_flexible:
#             salary_check_reason = "PASS (Flexible Budget)"; logger.info(salary_check_reason)
#         elif budget_to_use is None:
#             salary_check_reason = "Clarification Needed: Budget missing/invalid in JD."; logger.warning(salary_check_reason)
#             clarification_reasons.append(salary_check_reason)
#         elif cost_to_use > budget_to_use:
#             salary_match = False; salary_check_reason = f"Rejected: Candidate payout ({cost_to_use}) exceeds JD budget ({budget_to_use})."; logger.warning(salary_check_reason)
#         else:
#             salary_check_reason = "PASS (Payout within Budget)"; logger.info(salary_check_reason)
#         # If salary check fails, reject immediately
#         if not salary_match:
#             logger.warning(f"Strict Check FAILED: Salary. Reason: {salary_check_reason}")
#             ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", APP_LOG_ERROR_DETAILS_FIELD_ID: salary_check_reason})
#             final_result_dict["status"] = "rejected"; final_result_dict["reason"] = salary_check_reason; return final_result_dict

#         # --- Check 2: Total Years of Experience ---
#         experience_match = True # Assume pass unless explicitly failed or needs clarification
#         experience_check_reason = None
#         candidate_experience_years: Optional[float] = None
#         logger.info(f"Strict Check 2 (Experience): CV vs JD Min ({jd_min_experience} years)")
#         if jd_min_experience is None:
#              experience_check_reason = "PASS (No Minimum Experience Specified in JD)"; logger.info(experience_check_reason)
#         else:
#              exp_prompt = EXTRACT_EXPERIENCE_PROMPT.format(cv_text=extracted_cv_text); exp_text, exp_error = call_llm(exp_prompt, MAX_TOKENS_EXPERIENCE)
#              if exp_error:
#                   experience_check_reason = f"Clarification Needed: LLM Error verifying experience: {exp_error}. Manual review needed."; logger.error(experience_check_reason)
#                   clarification_reasons.append(experience_check_reason)
#              else:
#                   candidate_experience_years = parse_llm_float(exp_text); logger.info(f"LLM Extracted Experience: {candidate_experience_years} (Raw: '{exp_text}')")
#                   if candidate_experience_years is None:
#                        experience_check_reason = "Clarification Needed: Cannot determine total experience years from CV. Manual review needed."; logger.warning(experience_check_reason)
#                        clarification_reasons.append(experience_check_reason)
#                   elif candidate_experience_years < jd_min_experience:
#                        experience_match = False; experience_check_reason = f"Rejected: Candidate experience ({candidate_experience_years:.1f} yrs) < Min required ({jd_min_experience:.1f} yrs)."; logger.warning(experience_check_reason)
#                   else:
#                        experience_check_reason = f"PASS (Experience {candidate_experience_years:.1f} yrs >= Min {jd_min_experience:.1f} yrs)"; logger.info(experience_check_reason)
#         # If experience check fails, reject immediately
#         if not experience_match:
#              logger.warning(f"Strict Check FAILED: Experience. Reason: {experience_check_reason}")
#              ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", APP_LOG_ERROR_DETAILS_FIELD_ID: experience_check_reason})
#              final_result_dict["status"] = "rejected"; final_result_dict["reason"] = experience_check_reason; return final_result_dict

#         # --- Check 3: Education Years Mentioned ---
#         education_check_reason = None
#         logger.info("Strict Check 3 (Education Years): Checking CV for specific graduation years")
#         edu_prompt = CHECK_EDUCATION_YEARS_PROMPT.format(cv_text=extracted_cv_text); edu_text, edu_error = call_llm(edu_prompt, MAX_TOKENS_EDUCATION)
#         if edu_error:
#              education_check_reason = f"Clarification Needed: LLM Error verifying education years: {edu_error}"; logger.error(education_check_reason)
#              clarification_reasons.append(education_check_reason)
#         else:
#              edu_result = parse_llm_yes_no_unclear(edu_text); logger.info(f"LLM Education Years Check Result: {edu_result} (Raw: '{edu_text}')")
#              if edu_result == "Yes":
#                   education_check_reason = "PASS (Graduation Years Mentioned)"; logger.info(education_check_reason)
#              else: # No or Unclear
#                   education_check_reason = "Clarification Needed: CV does not clearly mention specific graduation years."; logger.warning(education_check_reason)
#                   clarification_reasons.append(education_check_reason)

#         # --- Handle Clarifications ---
#         if clarification_reasons:
#              logger.warning("Strict Checks require CLARIFICATION.")
#              combined_reason = "; ".join(clarification_reasons)
#              ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Clarification Needed", APP_LOG_ERROR_DETAILS_FIELD_ID: combined_reason})
#              final_result_dict["status"] = "clarification_needed"; final_result_dict["reason"] = "Clarification needed regarding candidate details."; final_result_dict["questions"] = clarification_reasons
#              return final_result_dict


#         # --- ========== STAGE 1 PASSED ========== ---
#         logger.info("--- Preliminary Strict Checks PASSED ---")
#         ac.update_application_log(log_record_id, {"Processing Status": "Preliminary Checks Passed"})

#         # --- ========== STAGE 2: Generate and Log Backend Report ========== ---
#         logger.info("--- Starting Stage 2: Generating Detailed Backend Report ---")
#         ac.update_application_log(log_record_id, {"Processing Status": "Generating Backend Report"})

#         # Store the prompt used for the report
#         report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format(
#             jd_text=jd_text,
#             cv_text=extracted_cv_text,
#             present_date_str=present_date_str,
#             candidate_expected_payout_pm=candidate_expected_payout_pm,
#             candidate_current_location=candidate_current_location
#         )

#         backend_report, report_error = call_llm(report_prompt, MAX_TOKENS_BACKEND_REPORT, temperature=0.2)

#         # Log Backend Report interaction to LLM Responses table
#         logger.info("Logging Backend Report interaction to LLM Responses table...")
#         llm_response_record_id = None # Reset before trying to create
#         if ac.LLM_TABLE_ID: # Check if the LLM Table ID is configured
#             parsing_status = "Success (Report Generated)" if not report_error else "Failure (Report Generation Error)"
#             report_content_for_log = backend_report if not report_error else f"Error generating report: {report_error}"
#             raw_response_for_log = backend_report if not report_error else report_error # Store raw response/error

#             llm_log_fields = {
#                 LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID: [log_record_id], # Link back to Application Log
#                 LLM_RESP_FULL_PROMPT_FIELD_ID: report_prompt[:100000], # Log the prompt (limit size)
#                 LLM_RESP_RAW_RESPONSE_FIELD_ID: raw_response_for_log[:100000] if raw_response_for_log else "N/A", # Log raw response/error
#                 LLM_RESP_BACKEND_REPORT_FIELD_ID: report_content_for_log[:100000] if report_content_for_log else "N/A", # Log the report/error here
#                 LLM_RESP_PARSING_STATUS_FIELD_ID: parsing_status
#             }
#             try:
#                 llm_log_record = ac.create_record(ac.LLM_TABLE_ID, llm_log_fields)
#                 if llm_log_record and llm_log_record.get('id'):
#                     llm_response_record_id = llm_log_record['id']
#                     logger.info(f"Successfully created LLM Response log record: {llm_response_record_id}")
#                     # Optionally link this LLM log back to the main log if needed
#                     # ac.update_application_log(log_record_id, {APP_LOG_ASSOC_LLM_RESP_FIELD_ID: [llm_response_record_id]})
#                 else:
#                     logger.error("Failed to create LLM Response log record (backend returned null/invalid).")
#             except Exception as llm_log_err:
#                 logger.exception(f"Error creating LLM Response log record: {llm_log_err}")
#         else:
#             logger.warning("AIRTABLE_LLM_TABLE_ID not configured. Skipping LLM Response table logging.")

#         # If report generation failed, log error in main log as fallback (if not already logged)
#         if report_error and not llm_response_record_id:
#              error_msg_fallback = f"Preliminary checks passed, but failed to generate/log backend report: {report_error}"
#              logger.error(error_msg_fallback)
#              # Update the main log only if the error field wasn't already set by a check failure
#              existing_log = ac.get_record(ac.LOGS_TABLE_ID, log_record_id)
#              if existing_log and not existing_log.get('fields', {}).get(APP_LOG_ERROR_DETAILS_FIELD_ID):
#                  ac.update_application_log(log_record_id, {APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg_fallback})


#         # --- Create Successful Candidate Record ---
#         # (The outcome is 'Matched' because all strict checks passed, regardless of report generation success)
#         ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
#         name_match = re.search(r"Name:\s*(.*)|candidate name:\s*(.*)|^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z.'-]+)+)", extracted_cv_text, re.IGNORECASE | re.MULTILINE)
#         cand_name_extracted = name_match.group(1) or name_match.group(2) or name_match.group(3) if name_match else cv_filename

#         candidate_data = {
#              "associated_log_entry_id": log_record_id,
#              "applied_position_jd_id": jd_record_id,
#              "candidate_name": cand_name_extracted.strip()[:100],
#              "candidate_email": candidate_email,
#              "llm_match_reason": "Passed preliminary checks (Salary, Experience, Education Years)." # Keep this high-level reason
#         }
#         candidate_record_id = ac.create_successful_candidate(candidate_data)

#         if candidate_record_id:
#              logger.info(f"Created successful candidate record: {candidate_record_id}")
#              link_cand_success = ac.update_application_log(log_record_id, {APP_LOG_ASSOC_CAND_REC_FIELD_ID: [candidate_record_id]}) # Use Field ID
#              if not link_cand_success: logger.warning(f"Failed link Candidate Record {candidate_record_id} to Log {log_record_id}.")
#              final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = []; final_airtable_outcome = "Matched"
#         else:
#              # This is an error state - checks passed but couldn't save candidate
#              logger.error("Passed preliminary checks, but failed to create candidate record in Airtable.")
#              error_msg = "Passed preliminary checks, but failed saving candidate record."
#              ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#              final_status = "error"; final_reason = error_msg; final_questions = []; final_airtable_outcome = "Error"


#         # --- Update Final Log Status ---
#         # Error Details field in Application Logs should only contain high-level error/clarification reasons now
#         final_log_details_content = None
#         if final_airtable_outcome not in ["Matched"]: # e.g., Error, Clarification Needed, Rejected (shouldn't happen here)
#             final_log_details_content = final_reason or f"Analysis complete with outcome: {final_airtable_outcome}"

#         log_updates = {
#             "Processing Status": "Analysis Complete",
#             "Final Outcome": final_airtable_outcome,
#         }
#         # Only add Error Details if there's content for it (i.e., not a clean match)
#         if final_log_details_content:
#              log_updates[APP_LOG_ERROR_DETAILS_FIELD_ID] = final_log_details_content[:100000]

#         update_success = ac.update_application_log(log_record_id, log_updates)
#         if not update_success:
#             logger.error(f"CRITICAL: Failed update final status for log {log_record_id}. Check Airtable/Logs.")

#         # Prepare final result dictionary
#         final_result_dict["status"] = final_status
#         final_result_dict["reason"] = final_reason
#         final_result_dict["questions"] = final_questions # From Stage 1 checks, if any led to clarification
#         final_result_dict["candidate_id"] = candidate_record_id
#         final_result_dict["error_message"] = final_reason if final_status == "error" else None
#         final_result_dict["llm_response_log_id"] = llm_response_record_id


#     except Exception as e:
#         logger.exception("Unexpected error during main C2C analysis orchestration.")
#         error_msg = f"System error: {type(e).__name__}: {str(e)}"
#         final_result_dict["status"] = "error"; final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg
#         if log_record_id:
#             try:
#                 # Attempt to log the system error
#                 ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", APP_LOG_ERROR_DETAILS_FIELD_ID: error_msg})
#             except Exception as log_e:
#                 logger.error(f"CRITICAL: Failed to log system error to Airtable log {log_record_id}: {log_e}")

#     # --- Final Logging & Return ---
#     end_time = time.time()
#     logger.info(f"--- C2C Analysis Finished: '{cv_filename}'. Final Status: {final_result_dict.get('status', 'unknown')}. Duration: {end_time - start_time:.2f}s ---")
#     return final_result_dict














# # agent/agent_runner.py
# import logging, base64, json, time, re
# from typing import Dict, Any, Optional, List, Tuple
# from datetime import datetime
# import google.generativeai as genai
# from google.api_core import exceptions as google_exceptions
# from .agent_definition import ( gemini_model_object, GOOGLE_MODEL_NAME, EXTRACT_EXPERIENCE_PROMPT, CHECK_EDUCATION_YEARS_PROMPT, GENERATE_DETAILED_REPORT_PROMPT, logger as agent_logger )
# from backend import airtable_client as ac
# from backend.cv_parser import extract_text_from_cv_bytes
# from backend.airtable_client import parse_locations # Import helper

# if not agent_logger.hasHandlers(): logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
# logger = agent_logger

# # --- Constants & Field IDs ---
# MAX_RETRIES = 1; RETRY_DELAY = 7; MAX_TOKENS_EXPERIENCE = 100; MAX_TOKENS_EDUCATION = 50; MAX_TOKENS_BACKEND_REPORT = 4000; LLM_TEMPERATURE = 0.1
# SAFETY_SETTINGS = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in [ "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT" ]]
# FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open budget"]
# APP_LOG_ERROR_DETAILS_FIELD_ID = ac.fields.ERROR_DETAILS; APP_LOG_ASSOC_CAND_REC_FIELD_ID = ac.fields.LOG_ASSOCIATED_CANDIDATE_RECORD
# LLM_RESP_BACKEND_REPORT_FIELD_ID = ac.fields.LLM_BACKEND_ANALYSIS_REPORT; LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.LLM_ASSOCIATED_LOG_ENTRY; LLM_RESP_FULL_PROMPT_FIELD_ID = ac.fields.LLM_FULL_PROMPT_SENT; LLM_RESP_RAW_RESPONSE_FIELD_ID = ac.fields.LLM_RAW_RESPONSE_RECEIVED; LLM_RESP_PARSING_STATUS_FIELD_ID = ac.fields.LLM_PARSING_STATUS
# CAND_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.CAND_ASSOCIATED_LOG_ENTRY; CAND_APPLIED_POSITION_FIELD_ID = ac.fields.CAND_APPLIED_POSITION; CAND_NAME_FIELD_ID = ac.fields.CAND_NAME; CAND_COMPANY_NAME_FIELD_ID = ac.fields.CAND_COMPANY_NAME; CAND_LLM_MATCH_REASON_FIELD_ID = ac.fields.CAND_LLM_MATCH_REASON; CAND_INTERVIEW_STATUS_FIELD_ID = ac.fields.CAND_INTERVIEW_STATUS

# # --- Helper Functions ---
# def parse_llm_float(text: Optional[str]) -> Optional[float]:
#     if not text: return None
#     try: match = re.search(r"[-+]?\d*\.?\d+", text); return float(match.group(0)) if match else None
#     except (ValueError, TypeError, AttributeError): logger.warning(f"Could not parse '{text}' as float."); return None
# def parse_llm_yes_no_unclear(text: Optional[str]) -> Optional[str]:
#     if not text: return "Unclear"; text_lower = text.strip().lower()
#     if "yes" in text_lower: return "Yes";
#     if "no" in text_lower: return "No"; return "Unclear"
# def call_llm(prompt: str, max_tokens: int, temperature: float = LLM_TEMPERATURE) -> Tuple[Optional[str], Optional[str]]:
#     response_text: Optional[str] = None; error_message: Optional[str] = None; last_exception = None
#     if not gemini_model_object: return None, "LLM model not initialized."
#     gen_config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
#     for attempt in range(MAX_RETRIES + 1):
#         try:
#             logger.info(f"Calling LLM (Attempt {attempt+1}/{MAX_RETRIES+1})..."); response = gemini_model_object.generate_content(prompt, generation_config=gen_config, safety_settings=SAFETY_SETTINGS)
#             if not response.candidates: feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else None; block_reason = feedback.block_reason if feedback and hasattr(feedback, 'block_reason') else "Unknown"; safety_ratings = feedback.safety_ratings if feedback and hasattr(feedback, 'safety_ratings') else "N/A"; error_message = f"LLM blocked: {block_reason}. R: {safety_ratings}"; logger.error(error_message); break
#             if not response.candidates[0].content or not response.candidates[0].content.parts: finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'; error_message = f"LLM no content parts. Finish: {finish_reason}"; logger.error(error_message); break
#             try: response_text = response.text
#             except ValueError: logger.warning("LLM response not direct text."); response_text = next((part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')), None)
#             if response_text is not None: response_text = response_text.strip()
#             if not response_text: finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'; error_message = f"LLM empty text. Finish: {finish_reason}"; logger.error(error_message); break
#             error_message = None; logger.info("LLM call successful."); break
#         except google_exceptions.ResourceExhausted as e: error_message = f"Quota Error: {e}"; last_exception = e; logger.error(error_message); break
#         except google_exceptions.InvalidArgument as e: error_message = f"Invalid Argument: {e}"; last_exception = e; logger.error(error_message); break
#         except Exception as e: error_message = f"API Error: {e}"; last_exception = e; logger.exception(f"LLM Call Err (Attempt {attempt+1}): {e}")
#         if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY)
#         else: logger.error("Max retries LLM call."); error_message = error_message or f"Max retries, last: {last_exception or 'Unknown'}"
#     return response_text, error_message

# # --- Main Orchestration Function ---
# # *** REVISED SIGNATURE TO MATCH FRONTEND ***
# def run_c2c_analysis(
#     position_title: str, cv_filename: str, cv_file_bytes: bytes, candidate_email: Optional[str],
#     candidate_name: str, company_name: str, candidate_expected_payout_pm: float,
#     candidate_applying_for_location: str, # Added back
#     candidate_current_location: str,
#     relocation_status: str,
#     grad_year_confirmed_by_user: str
# ) -> Dict[str, Any]:
# # *** END REVISED SIGNATURE ***
#     start_time = time.time(); present_date_str = datetime.now().strftime("%Y-%m-%d")
#     logger.info(f"--- Starting C2C Analysis (V26 - Target Loc Re-added) ---") # Version bump
#     logger.info(f"Pos: '{position_title}', CV: '{cv_filename}'"); logger.info(f"Cand: '{candidate_name}', Comp: '{company_name}', Email: {candidate_email}");
#     logger.info(f"Target Loc: '{candidate_applying_for_location}', Current Loc: '{candidate_current_location}', Relo Status: '{relocation_status}'") # Log all
#     logger.info(f"Payout: {candidate_expected_payout_pm}, Grad Conf: {grad_year_confirmed_by_user}")
#     log_record_id: Optional[str] = None; candidate_record_id: Optional[str] = None; llm_response_record_id: Optional[str] = None
#     final_result_dict: Dict[str, Any] = { "status": "error", "reason": "Init fail.", "questions": [], "candidate_id": None, "error_message": "Init fail.", "llm_response_log_id": None }
#     extracted_cv_text: Optional[str] = None; jd_details: Optional[Dict] = None; jd_record_id: Optional[str] = None; jd_budget_value: Optional[float] = None; jd_min_experience: Optional[float] = None; jd_full_location_list: List[str] = []; is_budget_flexible: bool = False; backend_report: Optional[str] = None; report_prompt: Optional[str] = None
#     try:
#         log_data = { "Applied Position Title": position_title, "CV Filename": cv_filename, "Candidate Name": candidate_name, "Company Name": company_name, "Candidate Email": candidate_email, "Processing Status": "Received", "Target Location Submitted": candidate_applying_for_location, "Current Location Submitted": candidate_current_location, "Relocation Status Submitted": relocation_status }
#         log_record_id = ac.create_application_log(log_data)
#         if not log_record_id: final_result_dict["error_message"] = "Failed create initial app log."; logger.error(final_result_dict["error_message"]); return final_result_dict
#         logger.info(f"Initial app log created: {log_record_id}")

#         ac.update_application_log(log_record_id, {"Processing Status": "Fetching JD"})
#         jd_details_record = ac.get_jd_details_by_title(position_title)
#         if not jd_details_record or 'fields' not in jd_details_record: error_msg = f"JD details/fields missing for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - JD Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         jd_details = jd_details_record['fields']; jd_record_id = jd_details_record.get('id')
#         jd_text = jd_details.get("Job Description Text")
#         if not jd_text: error_msg = f"JD text field empty for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - JD Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         jd_budget_raw = jd_details.get("Budget"); jd_location_raw = jd_details.get("Location"); jd_min_experience_raw = jd_details.get("Minimum experience in years")
#         is_budget_flexible, jd_budget_value = ac.parse_budget(jd_budget_raw); jd_min_experience = ac.parse_experience(jd_min_experience_raw); jd_full_location_list = ac.parse_locations(jd_location_raw); logger.info(f"Fetched JD: {jd_record_id}. Budget: {jd_budget_value} (Flex: {is_budget_flexible}), Locations: {jd_full_location_list}, Min Exp: {jd_min_experience}")

#         ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
#         extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
#         if isinstance(extracted_cv_text, str) and (extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:")): error_msg = f"CV parse issue '{cv_filename}': {extracted_cv_text}"; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         elif not extracted_cv_text or not isinstance(extracted_cv_text, str) or not extracted_cv_text.strip(): error_msg = f"CV parse fail/empty '{cv_filename}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         logger.info(f"Parsed CV: {cv_filename} ({len(extracted_cv_text)} chars)")

#         ac.update_application_log(log_record_id, {"Processing Status": "Performing Strict Checks"}); logger.info("--- Starting Stage 1: Strict Parameter Checks ---"); clarification_reasons = []
#         # Check 1: Salary
#         salary_match = True; salary_check_reason = None; cost_to_use = candidate_expected_payout_pm; budget_to_use = jd_budget_value; logger.info(f"Check 1 (Salary): Payout {cost_to_use} vs Budget {budget_to_use} (Flex: {is_budget_flexible})")
#         if is_budget_flexible: salary_check_reason = "PASS (Flexible Budget)"
#         elif budget_to_use is None: salary_check_reason = "Clarification: Budget missing/invalid in JD."; clarification_reasons.append(salary_check_reason)
#         elif cost_to_use > budget_to_use: salary_match = False; salary_check_reason = f"Rejected: Payout ({cost_to_use:.0f}) > budget ({budget_to_use:.0f})."
#         else: salary_check_reason = "PASS (Payout within Budget)"
#         logger.info(f"Salary Result: {salary_check_reason}");
#         if not salary_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": salary_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = salary_check_reason; return final_result_dict
#         # Check 2: Experience
#         experience_match = True; experience_check_reason = None; candidate_experience_years = None; logger.info(f"Check 2 (Experience): CV vs JD Min ({jd_min_experience} years)")
#         if jd_min_experience is None: experience_check_reason = "PASS (No Min Exp)"
#         else:
#              exp_prompt = EXTRACT_EXPERIENCE_PROMPT.format(cv_text=extracted_cv_text); exp_text, exp_error = call_llm(exp_prompt, MAX_TOKENS_EXPERIENCE)
#              if exp_error: experience_check_reason = f"Clarification: LLM Error verifying exp: {exp_error}."; clarification_reasons.append(experience_check_reason)
#              else:
#                   candidate_experience_years = parse_llm_float(exp_text); logger.info(f"LLM Extracted Exp: {candidate_experience_years} (Raw: '{exp_text}')")
#                   if candidate_experience_years is None: experience_check_reason = "Clarification: Cannot determine exp from CV."; clarification_reasons.append(experience_check_reason)
#                   elif candidate_experience_years < jd_min_experience: experience_match = False; experience_check_reason = f"Rejected: Exp ({candidate_experience_years:.1f}) < Min ({jd_min_experience:.1f})."
#                   else: experience_check_reason = f"PASS (Exp >= Min)"
#         logger.info(f"Experience Result: {experience_check_reason}");
#         if not experience_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": experience_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = experience_check_reason; return final_result_dict
#         # Check 3: Education Years
#         education_check_reason = None; logger.info("Check 3 (Education Years): Checking CV")
#         edu_prompt = CHECK_EDUCATION_YEARS_PROMPT.format(cv_text=extracted_cv_text); edu_text, edu_error = call_llm(edu_prompt, MAX_TOKENS_EDUCATION)
#         if edu_error: education_check_reason = f"Clarification: LLM Error verifying edu years: {edu_error}"; clarification_reasons.append(education_check_reason)
#         else:
#              edu_result = parse_llm_yes_no_unclear(edu_text); logger.info(f"LLM Edu Years Check: {edu_result} (Raw: '{edu_text}')")
#              if edu_result == "Yes": education_check_reason = "PASS (Grad Years Mentioned)"
#              else: education_check_reason = "Clarification: CV unclear/missing grad years."; clarification_reasons.append(education_check_reason)
#         logger.info(f"Education Result: {education_check_reason}")

#         # *** Check 4: Location Match (Reinstated using target_location) ***
#         location_match = True # Assume pass unless explicitly rejected
#         location_check_reason = None
#         target_loc = candidate_applying_for_location # Use the target location specified by the user
#         logger.info(f"Check 4 (Location): Target '{target_loc}' vs JD Locations {jd_full_location_list}")
#         if not jd_full_location_list : # JD has no locations listed, always pass
#             location_check_reason = "PASS (JD has no specific location requirement)"; logger.info(location_check_reason)
#         # Check if the target location provided exists in the JD list (case-insensitive check recommended)
#         elif not any(target_loc.lower() == jd_loc.lower() for jd_loc in jd_full_location_list):
#              location_match = False
#              location_check_reason = f"Rejected: Target location '{target_loc}' not in required JD locations: {', '.join(jd_full_location_list)}."
#              logger.warning(location_check_reason)
#         else:
#              location_check_reason = f"PASS (Target location '{target_loc}' is valid for JD)"; logger.info(location_check_reason)
#         logger.info(f"Location Check Result: {location_check_reason}")
#         if not location_match:
#              ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": location_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = location_check_reason; return final_result_dict
#         # --- End Reinstated Location Check ---

#         if clarification_reasons: logger.warning("Strict Checks require CLARIFICATION."); combined_reason = "; ".join(clarification_reasons); ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Clarification Needed", "Error details": combined_reason}); final_result_dict["status"] = "clarification_needed"; final_result_dict["reason"] = "Clarification needed."; final_result_dict["questions"] = clarification_reasons; return final_result_dict

#         logger.info("--- Preliminary Strict Checks PASSED ---"); ac.update_application_log(log_record_id, {"Processing Status": "Preliminary Checks Passed"}) # Updated log message
#         logger.info("--- Starting Stage 2: Generating Detailed Backend Report ---"); ac.update_application_log(log_record_id, {"Processing Status": "Generating Backend Report"})
#         # Pass all location info to the prompt
#         report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format( jd_text=jd_text, cv_text=extracted_cv_text, present_date_str=present_date_str, candidate_name=candidate_name, company_name=company_name, candidate_expected_payout_pm=candidate_expected_payout_pm, candidate_target_location=candidate_applying_for_location, candidate_current_location=candidate_current_location, candidate_relocation_status=relocation_status )
#         backend_report, report_error = call_llm(report_prompt, MAX_TOKENS_BACKEND_REPORT, temperature=0.2)
#         logger.info("Logging Backend Report interaction...")
#         llm_response_record_id = None
#         if ac.LLM_TABLE_ID:
#             parsing_status = "Success (Report Generated)" if not report_error else "Failure (Report Generation Error)"; report_content_for_log = backend_report if not report_error else f"Error: {report_error}"; raw_response_for_log = backend_report if not report_error else report_error
#             llm_log_fields = { ac.LlmRespFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id], ac.LlmRespFields.FULL_PROMPT_SENT.name: report_prompt[:100000], ac.LlmRespFields.RAW_RESPONSE_RECEIVED.name: raw_response_for_log[:100000] if raw_response_for_log else "N/A", ac.LlmRespFields.BACKEND_ANALYSIS_REPORT.name: report_content_for_log[:100000] if report_content_for_log else "N/A", ac.LlmRespFields.PARSING_STATUS.name: parsing_status }
#             llm_response_record_id = ac.create_llm_response_log(llm_log_fields)
#             if llm_response_record_id: logger.info(f"LLM Response log created: {llm_response_record_id}")
#             else: logger.error("Failed create LLM Response log record.")
#         else: logger.warning("LLM_TABLE_ID not set. Skipping LLM Response log.")
#         # Fallback logging if report failed AND LLM log failed
#         if report_error and not llm_response_record_id:
#              error_msg_fallback = f"Checks passed, but failed generate/log report: {report_error}"; logger.error(error_msg_fallback);
#              # Check if existing log fetch needed OR just update if log_record_id exists
#              if log_record_id: # Only try to update if initial log was created
#                  existing_log = ac.get_record(ac.LOGS_TABLE_ID, log_record_id);
#                  if existing_log and not existing_log.get('fields', {}).get("Error details"): # Check using string name
#                      ac.update_application_log(log_record_id, {"Error details": error_msg_fallback}) # Update using string name

#         ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
#         candidate_data_for_airtable = { ac.CandFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id], ac.CandFields.APPLIED_POSITION.name: [jd_record_id] if jd_record_id else [], ac.CandFields.NAME.name: candidate_name, ac.CandFields.COMPANY_NAME.name: company_name, ac.CandFields.LLM_MATCH_REASON.name: "Passed prelim checks (Salary, Exp, Edu, Location).", ac.CandFields.INTERVIEW_STATUS.name: "Pending" } # Reason updated
#         candidate_record_id = ac.create_successful_candidate(candidate_data_for_airtable)
#         if candidate_record_id:
#             logger.info(f"Created candidate record: {candidate_record_id}");
#             link_cand_success = ac.update_application_log(log_record_id, {"Associated Candidate Record": [candidate_record_id]}); # Use name
#             if link_cand_success: final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = clarification_reasons
#             else: logger.warning(f"Failed link Cand Rec {candidate_record_id} to Log {log_record_id}."); final_status = "matched"; final_reason = "Passed preliminary checks, link failed."; final_questions = clarification_reasons
#             final_airtable_outcome = "Matched"
#         else: error_msg = "Passed checks, but failed saving candidate record."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", "Error details": error_msg}); final_status = "error"; final_reason = error_msg; final_questions = clarification_reasons; final_airtable_outcome = "Error"

#         final_log_details_content = None
#         if final_airtable_outcome != "Matched": final_log_details_content = final_reason or f"Analysis complete: {final_airtable_outcome}"
#         log_updates = {"Processing Status": "Analysis Complete", "Final Outcome": final_airtable_outcome}
#         if final_log_details_content: log_updates["Error details"] = final_log_details_content[:100000] # Use correct key name
#         update_success = ac.update_application_log(log_record_id, log_updates)
#         if not update_success: logger.error(f"CRITICAL: Failed update final status log {log_record_id}.")

#         final_result_dict["status"] = final_status; final_result_dict["reason"] = final_reason; final_result_dict["questions"] = clarification_reasons; final_result_dict["candidate_id"] = candidate_record_id; final_result_dict["error_message"] = final_reason if final_status == "error" else None; final_result_dict["llm_response_log_id"] = llm_response_record_id
#     except Exception as e:
#         logger.exception("Unexpected error during main orchestration."); error_msg = f"System error: {type(e).__name__}: {str(e)}"; final_result_dict["status"] = "error"; final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg
#         if log_record_id:
#             try: ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", "Error details": error_msg}) # Use correct key name
#             except Exception as log_e: logger.error(f"CRITICAL: Failed log system error to log {log_record_id}: {log_e}")
#     end_time = time.time()
#     logger.info(f"--- C2C Analysis Finished: '{cv_filename}'. Status: {final_result_dict.get('status', 'unknown')}. Duration: {end_time - start_time:.2f}s ---")
#     return final_result_dict






# agent/agent_runner.py
import logging, base64, json, time, re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
# Use the logger from agent_definition
from .agent_definition import ( gemini_model_object, GOOGLE_MODEL_NAME, EXTRACT_EXPERIENCE_PROMPT, CHECK_EDUCATION_YEARS_PROMPT, GENERATE_DETAILED_REPORT_PROMPT, logger as agent_logger )
from backend import airtable_client as ac
from backend.cv_parser import extract_text_from_cv_bytes
# Import parse_locations directly from airtable_client
from backend.airtable_client import parse_locations

if not agent_logger.hasHandlers(): logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
logger = agent_logger # Use the configured logger

# --- Constants & Field IDs ---
MAX_RETRIES = 1; RETRY_DELAY = 7; MAX_TOKENS_EXPERIENCE = 100; MAX_TOKENS_EDUCATION = 50; MAX_TOKENS_BACKEND_REPORT = 4000; LLM_TEMPERATURE = 0.1
SAFETY_SETTINGS = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in [ "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT" ]]
FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open budget"]
# Use field accessors from airtable_client (these now point to NEW IDs)
APP_LOG_ERROR_DETAILS_FIELD_ID = ac.fields.ERROR_DETAILS; APP_LOG_ASSOC_CAND_REC_FIELD_ID = ac.fields.LOG_ASSOCIATED_CANDIDATE_RECORD
LLM_RESP_BACKEND_REPORT_FIELD_ID = ac.fields.LLM_BACKEND_ANALYSIS_REPORT; LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.LLM_ASSOCIATED_LOG_ENTRY; LLM_RESP_FULL_PROMPT_FIELD_ID = ac.fields.LLM_FULL_PROMPT_SENT; LLM_RESP_RAW_RESPONSE_FIELD_ID = ac.fields.LLM_RAW_RESPONSE_RECEIVED; LLM_RESP_PARSING_STATUS_FIELD_ID = ac.fields.LLM_PARSING_STATUS
CAND_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.CAND_ASSOCIATED_LOG_ENTRY; CAND_APPLIED_POSITION_FIELD_ID = ac.fields.CAND_APPLIED_POSITION; CAND_NAME_FIELD_ID = ac.fields.CAND_NAME; CAND_COMPANY_NAME_FIELD_ID = ac.fields.CAND_COMPANY_NAME; CAND_LLM_MATCH_REASON_FIELD_ID = ac.fields.CAND_LLM_MATCH_REASON; CAND_INTERVIEW_STATUS_FIELD_ID = ac.fields.CAND_INTERVIEW_STATUS

# --- Helper Functions ---
def parse_llm_float(text: Optional[str]) -> Optional[float]:
    if not text: return None
    try: match = re.search(r"[-+]?\d*\.?\d+", text); return float(match.group(0)) if match else None
    except (ValueError, TypeError, AttributeError): logger.warning(f"Could not parse '{text}' as float."); return None

# *** CORRECTED FUNCTION ***
def parse_llm_yes_no_unclear(text: Optional[str]) -> Optional[str]:
    """Parses LLM response for Yes/No/Unclear, handling None input."""
    if not text:
        # Handles None or empty string case
        return "Unclear"
    # If text is valid, proceed with assignment and checks
    text_lower = text.strip().lower()
    if "yes" in text_lower:
        return "Yes"
    if "no" in text_lower:
        return "No"
    # Default if neither "yes" nor "no" is found
    return "Unclear"
# *** END CORRECTION ***

def call_llm(prompt: str, max_tokens: int, temperature: float = LLM_TEMPERATURE) -> Tuple[Optional[str], Optional[str]]:
    response_text: Optional[str] = None; error_message: Optional[str] = None; last_exception = None
    if not gemini_model_object: return None, "LLM model not initialized."
    gen_config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(f"Calling LLM (Attempt {attempt+1}/{MAX_RETRIES+1})..."); response = gemini_model_object.generate_content(prompt, generation_config=gen_config, safety_settings=SAFETY_SETTINGS)
            if not response.candidates: feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else None; block_reason = feedback.block_reason if feedback and hasattr(feedback, 'block_reason') else "Unknown"; safety_ratings = feedback.safety_ratings if feedback and hasattr(feedback, 'safety_ratings') else "N/A"; error_message = f"LLM blocked: {block_reason}. R: {safety_ratings}"; logger.error(error_message); break
            if not response.candidates[0].content or not response.candidates[0].content.parts: finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'; error_message = f"LLM no content parts. Finish: {finish_reason}"; logger.error(error_message); break
            try: response_text = response.text
            except ValueError: logger.warning("LLM response not direct text."); response_text = next((part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')), None)
            if response_text is not None: response_text = response_text.strip()
            if not response_text: finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'; error_message = f"LLM empty text. Finish: {finish_reason}"; logger.error(error_message); break # Treat genuinely empty string response as an issue for parsing logic downstream
            error_message = None; logger.info("LLM call successful."); break # Success
        except google_exceptions.ResourceExhausted as e: error_message = f"Quota Error: {e}"; last_exception = e; logger.error(error_message); break
        except google_exceptions.InvalidArgument as e: error_message = f"Invalid Argument: {e}"; last_exception = e; logger.error(error_message); break
        except Exception as e: error_message = f"API Error: {e}"; last_exception = e; logger.exception(f"LLM Call Err (Attempt {attempt+1}): {e}")
        if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY)
        else: logger.error("Max retries LLM call."); error_message = error_message or f"Max retries, last: {last_exception or 'Unknown'}"
    # Ensure response_text is None if there was any error
    if error_message: response_text = None
    return response_text, error_message


# --- Main Orchestration Function ---
# *** FINAL SIGNATURE - Matches new frontend call & schema ***
def run_c2c_analysis(
    position_title: str, # This is the 'Requirement' title from the new schema
    cv_filename: str, cv_file_bytes: bytes, candidate_email: Optional[str],
    candidate_name: str, company_name: str, candidate_expected_payout_pm: float,
    candidate_applying_for_location: str, # Target location specified by user
    candidate_current_location: str,
    relocation_status: str,
    grad_year_confirmed_by_user: str
) -> Dict[str, Any]:
# *** END FINAL SIGNATURE ***
    start_time = time.time(); present_date_str = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"--- Starting C2C Analysis (V27.1 - New Airtable Schema) ---") # Incremented version
    logger.info(f"Requirement: '{position_title}', CV: '{cv_filename}'"); logger.info(f"Cand: '{candidate_name}', Comp: '{company_name}', Email: {candidate_email}");
    logger.info(f"Target Loc: '{candidate_applying_for_location}', Current Loc: '{candidate_current_location}', Relo Status: '{relocation_status}'")
    logger.info(f"Payout: {candidate_expected_payout_pm}, Grad Conf: {grad_year_confirmed_by_user}")
    log_record_id: Optional[str] = None; candidate_record_id: Optional[str] = None; llm_response_record_id: Optional[str] = None
    final_result_dict: Dict[str, Any] = { "status": "error", "reason": "Init fail.", "questions": [], "candidate_id": None, "error_message": "Init fail.", "llm_response_log_id": None }
    extracted_cv_text: Optional[str] = None; requirement_details: Optional[Dict] = None; requirement_record_id: Optional[str] = None; budget_value: Optional[float] = None; min_experience: Optional[float] = None; req_location_list: List[str] = []; is_budget_flexible: bool = False; backend_report: Optional[str] = None; report_prompt: Optional[str] = None
    try:
        log_data = { "Applied Position Title": position_title, "CV Filename": cv_filename, "Candidate Name": candidate_name, "Company Name": company_name, "Candidate Email": candidate_email, "Processing Status": "Received", "Target Location Submitted": candidate_applying_for_location, "Current Location Submitted": candidate_current_location, "Relocation Status Submitted": relocation_status }
        log_record_id = ac.create_application_log(log_data)
        if not log_record_id: final_result_dict["error_message"] = "Failed create initial app log."; logger.error(final_result_dict["error_message"]); return final_result_dict
        logger.info(f"Initial app log created: {log_record_id}")

        ac.update_application_log(log_record_id, {"Processing Status": "Fetching Requirement Details"})
        requirement_details_record = ac.get_requirement_details_by_title(position_title)
        if not requirement_details_record or 'fields' not in requirement_details_record: error_msg = f"Requirement details/fields missing for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Requirement Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
        requirement_details = requirement_details_record['fields']; requirement_record_id = requirement_details_record.get('id')
        # Use correct NEW field names from schema
        requirement_text = requirement_details.get("JD in Text") # Changed key
        if not requirement_text: error_msg = f"'JD in Text' field empty for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Requirement Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
        budget_raw = requirement_details.get("Budget"); location_raw = requirement_details.get("Location"); min_experience_raw = requirement_details.get("Minimum Experience") # Changed key
        is_budget_flexible, budget_value = ac.parse_budget(budget_raw); min_experience = ac.parse_experience(min_experience_raw); req_location_list = ac.parse_locations(location_raw); logger.info(f"Fetched Requirement: {requirement_record_id}. Budget: {budget_value} (Flex: {is_budget_flexible}), Locations: {req_location_list}, Min Exp: {min_experience}")

        ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
        extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
        if isinstance(extracted_cv_text, str) and (extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:")): error_msg = f"CV parse issue '{cv_filename}': {extracted_cv_text}"; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
        elif not extracted_cv_text or not isinstance(extracted_cv_text, str) or not extracted_cv_text.strip(): error_msg = f"CV parse fail/empty '{cv_filename}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
        logger.info(f"Parsed CV: {cv_filename} ({len(extracted_cv_text)} chars)")

        ac.update_application_log(log_record_id, {"Processing Status": "Performing Strict Checks"}); logger.info("--- Starting Stage 1: Strict Parameter Checks ---"); clarification_reasons = []
        # Check 1: Salary
        salary_match = True; salary_check_reason = None; cost_to_use = candidate_expected_payout_pm; budget_to_use = budget_value; logger.info(f"Check 1 (Salary): Payout {cost_to_use} vs Budget {budget_to_use} (Flex: {is_budget_flexible})")
        if is_budget_flexible: salary_check_reason = "PASS (Flexible Budget)"
        elif budget_to_use is None: salary_check_reason = "Clarification: Budget missing/invalid in Requirement."; clarification_reasons.append(salary_check_reason)
        elif cost_to_use > budget_to_use: salary_match = False; salary_check_reason = f"Rejected: Payout ({cost_to_use:.0f}) > budget ({budget_to_use:.0f})."
        else: salary_check_reason = "PASS (Payout within Budget)"
        logger.info(f"Salary Result: {salary_check_reason}");
        if not salary_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": salary_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = salary_check_reason; return final_result_dict
        # Check 2: Experience
        experience_match = True; experience_check_reason = None; candidate_experience_years = None; logger.info(f"Check 2 (Experience): CV vs Req Min ({min_experience} years)")
        if min_experience is None: experience_check_reason = "PASS (No Min Exp Specified)"
        else:
             exp_prompt = EXTRACT_EXPERIENCE_PROMPT.format(cv_text=extracted_cv_text); exp_text, exp_error = call_llm(exp_prompt, MAX_TOKENS_EXPERIENCE)
             if exp_error: experience_check_reason = f"Clarification: LLM Error verifying exp: {exp_error}."; clarification_reasons.append(experience_check_reason)
             elif exp_text is None: # Explicitly check if text is None after successful call (e.g., empty response)
                 experience_check_reason = "Clarification: Cannot determine exp from CV (LLM returned no text)."; clarification_reasons.append(experience_check_reason)
             else:
                  candidate_experience_years = parse_llm_float(exp_text); logger.info(f"LLM Extracted Exp: {candidate_experience_years} (Raw: '{exp_text}')")
                  if candidate_experience_years is None: experience_check_reason = "Clarification: Cannot determine exp from CV (Parsing failed)."; clarification_reasons.append(experience_check_reason)
                  elif candidate_experience_years < min_experience: experience_match = False; experience_check_reason = f"Rejected: Exp ({candidate_experience_years:.1f}) < Min ({min_experience:.1f})."
                  else: experience_check_reason = f"PASS (Exp >= Min)"
        logger.info(f"Experience Result: {experience_check_reason}");
        if not experience_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": experience_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = experience_check_reason; return final_result_dict
        # Check 3: Education Years
        education_check_reason = None; logger.info("Check 3 (Education Years): Checking CV")
        edu_prompt = CHECK_EDUCATION_YEARS_PROMPT.format(cv_text=extracted_cv_text); edu_text, edu_error = call_llm(edu_prompt, MAX_TOKENS_EDUCATION)
        if edu_error: education_check_reason = f"Clarification: LLM Error verifying edu years: {edu_error}"; clarification_reasons.append(education_check_reason)
        # No need for elif edu_text is None here, as parse_llm_yes_no_unclear handles it
        else:
             # Pass edu_text (which could be None or a string) to the corrected parser
             edu_result = parse_llm_yes_no_unclear(edu_text);
             logger.info(f"LLM Edu Years Check: {edu_result} (Raw: '{edu_text}')") # Log raw value too
             if edu_result == "Yes": education_check_reason = "PASS (Grad Years Mentioned)"
             else: # Covers "No" and "Unclear" (including None input or LLM errors leading to None)
                 education_check_reason = "Clarification: CV unclear/missing grad years."; clarification_reasons.append(education_check_reason)
        logger.info(f"Education Result: {education_check_reason}")
        # Check 4: Location Match (Using target location from input)
        location_match = True; location_check_reason = None
        target_loc = candidate_applying_for_location # Use the target location specified by the user
        logger.info(f"Check 4 (Location): Target '{target_loc}' vs Req Locations {req_location_list}")
        if not req_location_list : location_check_reason = "PASS (Req has no specific location requirement)"; logger.info(location_check_reason)
        elif not target_loc: # Handle case where user might submit empty target location
            location_match = False; location_check_reason = "Rejected: Target location not specified by user."
            logger.warning(location_check_reason)
        elif not any(target_loc.lower() == req_loc.lower() for req_loc in req_location_list):
             location_match = False; location_check_reason = f"Rejected: Target location '{target_loc}' not in required locations: {', '.join(req_location_list)}."; logger.warning(location_check_reason)
        else: location_check_reason = f"PASS (Target location '{target_loc}' is valid)"; logger.info(location_check_reason)
        logger.info(f"Location Check Result: {location_check_reason}")
        if not location_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": location_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = location_check_reason; return final_result_dict

        if clarification_reasons: logger.warning("Strict Checks require CLARIFICATION."); combined_reason = "; ".join(clarification_reasons); ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Clarification Needed", "Error details": combined_reason}); final_result_dict["status"] = "clarification_needed"; final_result_dict["reason"] = "Clarification needed."; final_result_dict["questions"] = clarification_reasons; return final_result_dict

        logger.info("--- Preliminary Strict Checks PASSED ---"); ac.update_application_log(log_record_id, {"Processing Status": "Preliminary Checks Passed"})
        logger.info("--- Starting Stage 2: Generating Detailed Backend Report ---"); ac.update_application_log(log_record_id, {"Processing Status": "Generating Backend Report"})
        # Use the new requirement_text variable and pass all location context
        report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format(
            requirement_text=requirement_text, # Pass Requirement Text as jd_text for the prompt
            cv_text=extracted_cv_text, present_date_str=present_date_str,
            candidate_name=candidate_name, company_name=company_name,
            candidate_expected_payout_pm=candidate_expected_payout_pm,
            candidate_applying_for_location=candidate_applying_for_location, # Pass target location
            candidate_current_location=candidate_current_location,
            candidate_relocation_status=relocation_status
            )
        backend_report, report_error = call_llm(report_prompt, MAX_TOKENS_BACKEND_REPORT, temperature=0.2)
        logger.info("Logging Backend Report interaction...")
        llm_response_record_id = None
        if ac.LLM_TABLE_ID:
            parsing_status = "Success (Report Generated)" if not report_error else "Failure (Report Generation Error)"; report_content_for_log = backend_report if not report_error else f"Error: {report_error}"; raw_response_for_log = backend_report if not report_error else report_error
            llm_log_fields = { ac.LlmRespFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id], ac.LlmRespFields.FULL_PROMPT_SENT.name: report_prompt[:100000], ac.LlmRespFields.RAW_RESPONSE_RECEIVED.name: raw_response_for_log[:100000] if raw_response_for_log else "N/A", ac.LlmRespFields.BACKEND_ANALYSIS_REPORT.name: report_content_for_log[:100000] if report_content_for_log else "N/A", ac.LlmRespFields.PARSING_STATUS.name: parsing_status }
            llm_response_record_id = ac.create_llm_response_log(llm_log_fields)
            if llm_response_record_id: logger.info(f"LLM Response log created: {llm_response_record_id}")
            else: logger.error("Failed create LLM Response log record.")
        else: logger.warning("LLM_TABLE_ID not set. Skipping LLM Response log.")
        # Corrected fallback error logging
        if report_error and not llm_response_record_id:
             error_msg_fallback = f"Checks passed, but failed generate/log report: {report_error}"; logger.error(error_msg_fallback);
             existing_log = ac.get_record(ac.LOGS_TABLE_ID, log_record_id); # Fetch log record here before check
             if existing_log and not existing_log.get('fields', {}).get("Error details"): # Check using string name
                 ac.update_application_log(log_record_id, {"Error details": error_msg_fallback}) # Update using string name

        # If report generation failed, we should probably stop here and indicate error?
        # For now, proceeding to create candidate record even if report failed, but logging the error.
        if report_error:
            logger.error(f"Backend report generation failed: {report_error}. Proceeding to create candidate record but flagging.")
            # Optionally update log here too if needed

        ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
        # Use Enum names as keys for candidate_data, matching create_successful_candidate expectation
        candidate_data_for_airtable = {
            ac.CandFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id],
            ac.CandFields.APPLIED_POSITION.name: [requirement_record_id] if requirement_record_id else [], # Link to Requirement record
            ac.CandFields.NAME.name: candidate_name,
            ac.CandFields.COMPANY_NAME.name: company_name,
            ac.CandFields.LLM_MATCH_REASON.name: "Passed prelim checks (Salary, Exp, Edu, Location)." + (" Report generation failed." if report_error else ""), # Append warning if report failed
            ac.CandFields.INTERVIEW_STATUS.name: "Pending" # Use new Enum name
         }
        candidate_record_id = ac.create_successful_candidate(candidate_data_for_airtable)
        if candidate_record_id:
            logger.info(f"Created candidate record: {candidate_record_id}");
            # Use correct field name for update
            link_cand_success = ac.update_application_log(log_record_id, {"Associated Candidate Record": [candidate_record_id]});
            if link_cand_success: final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = clarification_reasons
            else: logger.warning(f"Failed link Cand Rec {candidate_record_id} to Log {log_record_id}."); final_status = "matched"; final_reason = "Passed preliminary checks, link failed."; final_questions = clarification_reasons
            final_airtable_outcome = "Matched"
        else: error_msg = "Passed checks, but failed saving candidate record."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", "Error details": error_msg}); final_status = "error"; final_reason = error_msg; final_questions = clarification_reasons; final_airtable_outcome = "Error"

        final_log_details_content = None
        if final_airtable_outcome != "Matched": final_log_details_content = final_reason or f"Analysis complete: {final_airtable_outcome}"
        log_updates = {"Processing Status": "Analysis Complete", "Final Outcome": final_airtable_outcome}
        # Use correct string name "Error details" for the key when updating
        if final_log_details_content: log_updates["Error details"] = final_log_details_content[:100000]
        # Also ensure the backend report gets logged if it exists, even on final update
        if backend_report and ac.fields.LOG_BACKEND_REPORT: # Check if field ID exists
            log_updates[ac.fields.LOG_BACKEND_REPORT] = backend_report[:100000] # Log report to Application Log

        update_success = ac.update_application_log(log_record_id, log_updates)
        if not update_success: logger.error(f"CRITICAL: Failed update final status log {log_record_id}.")

        final_result_dict["status"] = final_status; final_result_dict["reason"] = final_reason; final_result_dict["questions"] = clarification_reasons; final_result_dict["candidate_id"] = candidate_record_id; final_result_dict["error_message"] = final_reason if final_status == "error" else None; final_result_dict["llm_response_log_id"] = llm_response_record_id
    except Exception as e:
        logger.exception("Unexpected error during main orchestration."); error_msg = f"System error: {type(e).__name__}: {str(e)}"; final_result_dict["status"] = "error"; final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg
        if log_record_id:
            try: ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", "Error details": error_msg}) # Use correct key name
            except Exception as log_e: logger.error(f"CRITICAL: Failed log system error to log {log_record_id}: {log_e}")
    end_time = time.time()
    logger.info(f"--- C2C Analysis Finished: '{cv_filename}'. Status: {final_result_dict.get('status', 'unknown')}. Duration: {end_time - start_time:.2f}s ---")
    return final_result_dict