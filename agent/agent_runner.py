# # agent/agent_runner.py
# import logging, base64, json, time, re
# from typing import Dict, Any, Optional, List, Tuple
# from datetime import datetime
# import google.generativeai as genai
# from google.api_core import exceptions as google_exceptions
# # Use the logger from agent_definition
# from .agent_definition import ( gemini_model_object, GOOGLE_MODEL_NAME, EXTRACT_EXPERIENCE_PROMPT, CHECK_EDUCATION_YEARS_PROMPT, GENERATE_DETAILED_REPORT_PROMPT, logger as agent_logger )
# from backend import airtable_client as ac
# from backend.cv_parser import extract_text_from_cv_bytes
# # Import parse_locations directly from airtable_client
# from backend.airtable_client import parse_locations

# if not agent_logger.hasHandlers(): logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
# logger = agent_logger # Use the configured logger

# # --- Constants & Field IDs ---
# MAX_RETRIES = 1; RETRY_DELAY = 7; MAX_TOKENS_EXPERIENCE = 100; MAX_TOKENS_EDUCATION = 50; MAX_TOKENS_BACKEND_REPORT = 4000; LLM_TEMPERATURE = 0.1
# SAFETY_SETTINGS = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in [ "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT" ]]
# FLEXIBLE_BUDGET_KEYWORDS = ["not a constraint", "negotiable", "competitive", "open budget"]
# # Use field accessors from airtable_client (these now point to NEW IDs)
# APP_LOG_ERROR_DETAILS_FIELD_ID = ac.fields.ERROR_DETAILS; APP_LOG_ASSOC_CAND_REC_FIELD_ID = ac.fields.LOG_ASSOCIATED_CANDIDATE_RECORD
# LLM_RESP_BACKEND_REPORT_FIELD_ID = ac.fields.LLM_BACKEND_ANALYSIS_REPORT; LLM_RESP_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.LLM_ASSOCIATED_LOG_ENTRY; LLM_RESP_FULL_PROMPT_FIELD_ID = ac.fields.LLM_FULL_PROMPT_SENT; LLM_RESP_RAW_RESPONSE_FIELD_ID = ac.fields.LLM_RAW_RESPONSE_RECEIVED; LLM_RESP_PARSING_STATUS_FIELD_ID = ac.fields.LLM_PARSING_STATUS
# CAND_ASSOC_LOG_ENTRY_FIELD_ID = ac.fields.CAND_ASSOCIATED_LOG_ENTRY; CAND_APPLIED_POSITION_FIELD_ID = ac.fields.CAND_APPLIED_POSITION; CAND_NAME_FIELD_ID = ac.fields.CAND_NAME; CAND_COMPANY_NAME_FIELD_ID = ac.fields.CAND_COMPANY_NAME; CAND_LLM_MATCH_REASON_FIELD_ID = ac.fields.CAND_LLM_MATCH_REASON; CAND_INTERVIEW_STATUS_FIELD_ID = ac.fields.CAND_INTERVIEW_STATUS

# # --- Helper Functions ---
# def parse_llm_float(text: Optional[str]) -> Optional[float]:
#     if not text: return None
#     try: match = re.search(r"[-+]?\d*\.?\d+", text); return float(match.group(0)) if match else None
#     except (ValueError, TypeError, AttributeError): logger.warning(f"Could not parse '{text}' as float."); return None

# # *** CORRECTED FUNCTION ***
# def parse_llm_yes_no_unclear(text: Optional[str]) -> Optional[str]:
#     """Parses LLM response for Yes/No/Unclear, handling None input."""
#     if not text:
#         # Handles None or empty string case
#         return "Unclear"
#     # If text is valid, proceed with assignment and checks
#     text_lower = text.strip().lower()
#     if "yes" in text_lower:
#         return "Yes"
#     if "no" in text_lower:
#         return "No"
#     # Default if neither "yes" nor "no" is found
#     return "Unclear"
# # *** END CORRECTION ***

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
#             if not response_text: finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'Unknown'; error_message = f"LLM empty text. Finish: {finish_reason}"; logger.error(error_message); break # Treat genuinely empty string response as an issue for parsing logic downstream
#             error_message = None; logger.info("LLM call successful."); break # Success
#         except google_exceptions.ResourceExhausted as e: error_message = f"Quota Error: {e}"; last_exception = e; logger.error(error_message); break
#         except google_exceptions.InvalidArgument as e: error_message = f"Invalid Argument: {e}"; last_exception = e; logger.error(error_message); break
#         except Exception as e: error_message = f"API Error: {e}"; last_exception = e; logger.exception(f"LLM Call Err (Attempt {attempt+1}): {e}")
#         if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY)
#         else: logger.error("Max retries LLM call."); error_message = error_message or f"Max retries, last: {last_exception or 'Unknown'}"
#     # Ensure response_text is None if there was any error
#     if error_message: response_text = None
#     return response_text, error_message


# # --- Main Orchestration Function ---
# # *** FINAL SIGNATURE - Matches new frontend call & schema ***
# def run_c2c_analysis(
#     position_title: str, # This is the 'Requirement' title from the new schema
#     cv_filename: str, cv_file_bytes: bytes, candidate_email: Optional[str],
#     candidate_name: str, company_name: str, candidate_expected_payout_pm: float,
#     candidate_applying_for_location: str, # Target location specified by user
#     candidate_current_location: str,
#     relocation_status: str,
#     grad_year_confirmed_by_user: str
# ) -> Dict[str, Any]:
# # *** END FINAL SIGNATURE ***
#     start_time = time.time(); present_date_str = datetime.now().strftime("%Y-%m-%d")
#     logger.info(f"--- Starting C2C Analysis (V27.1 - New Airtable Schema) ---") # Incremented version
#     logger.info(f"Requirement: '{position_title}', CV: '{cv_filename}'"); logger.info(f"Cand: '{candidate_name}', Comp: '{company_name}', Email: {candidate_email}");
#     logger.info(f"Target Loc: '{candidate_applying_for_location}', Current Loc: '{candidate_current_location}', Relo Status: '{relocation_status}'")
#     logger.info(f"Payout: {candidate_expected_payout_pm}, Grad Conf: {grad_year_confirmed_by_user}")
#     log_record_id: Optional[str] = None; candidate_record_id: Optional[str] = None; llm_response_record_id: Optional[str] = None
#     final_result_dict: Dict[str, Any] = { "status": "error", "reason": "Init fail.", "questions": [], "candidate_id": None, "error_message": "Init fail.", "llm_response_log_id": None }
#     extracted_cv_text: Optional[str] = None; requirement_details: Optional[Dict] = None; requirement_record_id: Optional[str] = None; budget_value: Optional[float] = None; min_experience: Optional[float] = None; req_location_list: List[str] = []; is_budget_flexible: bool = False; backend_report: Optional[str] = None; report_prompt: Optional[str] = None
#     try:
#         log_data = { "Applied Position Title": position_title, "CV Filename": cv_filename, "Candidate Name": candidate_name, "Company Name": company_name, "Candidate Email": candidate_email, "Processing Status": "Received", "Target Location Submitted": candidate_applying_for_location, "Current Location Submitted": candidate_current_location, "Relocation Status Submitted": relocation_status }
#         log_record_id = ac.create_application_log(log_data)
#         if not log_record_id: final_result_dict["error_message"] = "Failed create initial app log."; logger.error(final_result_dict["error_message"]); return final_result_dict
#         logger.info(f"Initial app log created: {log_record_id}")

#         ac.update_application_log(log_record_id, {"Processing Status": "Fetching Requirement Details"})
#         requirement_details_record = ac.get_requirement_details_by_title(position_title)
#         if not requirement_details_record or 'fields' not in requirement_details_record: error_msg = f"Requirement details/fields missing for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Requirement Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         requirement_details = requirement_details_record['fields']; requirement_record_id = requirement_details_record.get('id')
#         # Use correct NEW field names from schema
#         requirement_text = requirement_details.get("JD in Text") # Changed key
#         if not requirement_text: error_msg = f"'JD in Text' field empty for '{position_title}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Requirement Fetch", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         budget_raw = requirement_details.get("Budget"); location_raw = requirement_details.get("Location"); min_experience_raw = requirement_details.get("Minimum Experience") # Changed key
#         is_budget_flexible, budget_value = ac.parse_budget(budget_raw); min_experience = ac.parse_experience(min_experience_raw); req_location_list = ac.parse_locations(location_raw); logger.info(f"Fetched Requirement: {requirement_record_id}. Budget: {budget_value} (Flex: {is_budget_flexible}), Locations: {req_location_list}, Min Exp: {min_experience}")

#         ac.update_application_log(log_record_id, {"Processing Status": "Parsing CV"})
#         extracted_cv_text = extract_text_from_cv_bytes(cv_file_bytes, cv_filename)
#         if isinstance(extracted_cv_text, str) and (extracted_cv_text.startswith("Error:") or extracted_cv_text.startswith("Warning:")): error_msg = f"CV parse issue '{cv_filename}': {extracted_cv_text}"; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         elif not extracted_cv_text or not isinstance(extracted_cv_text, str) or not extracted_cv_text.strip(): error_msg = f"CV parse fail/empty '{cv_filename}'."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - CV Read", "Error details": error_msg}); final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg; return final_result_dict
#         logger.info(f"Parsed CV: {cv_filename} ({len(extracted_cv_text)} chars)")

#         ac.update_application_log(log_record_id, {"Processing Status": "Performing Strict Checks"}); logger.info("--- Starting Stage 1: Strict Parameter Checks ---"); clarification_reasons = []
#         # Check 1: Salary
#         salary_match = True; salary_check_reason = None; cost_to_use = candidate_expected_payout_pm; budget_to_use = budget_value; logger.info(f"Check 1 (Salary): Payout {cost_to_use} vs Budget {budget_to_use} (Flex: {is_budget_flexible})")
#         if is_budget_flexible: salary_check_reason = "PASS (Flexible Budget)"
#         elif budget_to_use is None: salary_check_reason = "Clarification: Budget missing/invalid in Requirement."; clarification_reasons.append(salary_check_reason)
#         elif cost_to_use > budget_to_use: salary_match = False; salary_check_reason = f"Rejected: Payout ({cost_to_use:.0f}) > budget ({budget_to_use:.0f})."
#         else: salary_check_reason = "PASS (Payout within Budget)"
#         logger.info(f"Salary Result: {salary_check_reason}");
#         if not salary_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": salary_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = salary_check_reason; return final_result_dict
#         # Check 2: Experience
#         experience_match = True; experience_check_reason = None; candidate_experience_years = None; logger.info(f"Check 2 (Experience): CV vs Req Min ({min_experience} years)")
#         if min_experience is None: experience_check_reason = "PASS (No Min Exp Specified)"
#         else:
#              exp_prompt = EXTRACT_EXPERIENCE_PROMPT.format(cv_text=extracted_cv_text); exp_text, exp_error = call_llm(exp_prompt, MAX_TOKENS_EXPERIENCE)
#              if exp_error: experience_check_reason = f"Clarification: LLM Error verifying exp: {exp_error}."; clarification_reasons.append(experience_check_reason)
#              elif exp_text is None: # Explicitly check if text is None after successful call (e.g., empty response)
#                  experience_check_reason = "Clarification: Cannot determine exp from CV (LLM returned no text)."; clarification_reasons.append(experience_check_reason)
#              else:
#                   candidate_experience_years = parse_llm_float(exp_text); logger.info(f"LLM Extracted Exp: {candidate_experience_years} (Raw: '{exp_text}')")
#                   if candidate_experience_years is None: experience_check_reason = "Clarification: Cannot determine exp from CV (Parsing failed)."; clarification_reasons.append(experience_check_reason)
#                   elif candidate_experience_years < min_experience: experience_match = False; experience_check_reason = f"Rejected: Exp ({candidate_experience_years:.1f}) < Min ({min_experience:.1f})."
#                   else: experience_check_reason = f"PASS (Exp >= Min)"
#         logger.info(f"Experience Result: {experience_check_reason}");
#         if not experience_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": experience_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = experience_check_reason; return final_result_dict
#         # Check 3: Education Years
#         education_check_reason = None; logger.info("Check 3 (Education Years): Checking CV")
#         edu_prompt = CHECK_EDUCATION_YEARS_PROMPT.format(cv_text=extracted_cv_text); edu_text, edu_error = call_llm(edu_prompt, MAX_TOKENS_EDUCATION)
#         if edu_error: education_check_reason = f"Clarification: LLM Error verifying edu years: {edu_error}"; clarification_reasons.append(education_check_reason)
#         # No need for elif edu_text is None here, as parse_llm_yes_no_unclear handles it
#         else:
#              # Pass edu_text (which could be None or a string) to the corrected parser
#              edu_result = parse_llm_yes_no_unclear(edu_text);
#              logger.info(f"LLM Edu Years Check: {edu_result} (Raw: '{edu_text}')") # Log raw value too
#              if edu_result == "Yes": education_check_reason = "PASS (Grad Years Mentioned)"
#              else: # Covers "No" and "Unclear" (including None input or LLM errors leading to None)
#                  education_check_reason = "Clarification: CV unclear/missing grad years."; clarification_reasons.append(education_check_reason)
#         logger.info(f"Education Result: {education_check_reason}")
#         # Check 4: Location Match (Using target location from input)
#         location_match = True; location_check_reason = None
#         target_loc = candidate_applying_for_location # Use the target location specified by the user
#         logger.info(f"Check 4 (Location): Target '{target_loc}' vs Req Locations {req_location_list}")
#         if not req_location_list : location_check_reason = "PASS (Req has no specific location requirement)"; logger.info(location_check_reason)
#         elif not target_loc: # Handle case where user might submit empty target location
#             location_match = False; location_check_reason = "Rejected: Target location not specified by user."
#             logger.warning(location_check_reason)
#         elif not any(target_loc.lower() == req_loc.lower() for req_loc in req_location_list):
#              location_match = False; location_check_reason = f"Rejected: Target location '{target_loc}' not in required locations: {', '.join(req_location_list)}."; logger.warning(location_check_reason)
#         else: location_check_reason = f"PASS (Target location '{target_loc}' is valid)"; logger.info(location_check_reason)
#         logger.info(f"Location Check Result: {location_check_reason}")
#         if not location_match: ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Rejected", "Error details": location_check_reason}); final_result_dict["status"] = "rejected"; final_result_dict["reason"] = location_check_reason; return final_result_dict

#         if clarification_reasons: logger.warning("Strict Checks require CLARIFICATION."); combined_reason = "; ".join(clarification_reasons); ac.update_application_log(log_record_id, {"Processing Status": "Analysis Complete", "Final Outcome": "Clarification Needed", "Error details": combined_reason}); final_result_dict["status"] = "clarification_needed"; final_result_dict["reason"] = "Clarification needed."; final_result_dict["questions"] = clarification_reasons; return final_result_dict

#         logger.info("--- Preliminary Strict Checks PASSED ---"); ac.update_application_log(log_record_id, {"Processing Status": "Preliminary Checks Passed"})
#         logger.info("--- Starting Stage 2: Generating Detailed Backend Report ---"); ac.update_application_log(log_record_id, {"Processing Status": "Generating Backend Report"})
#         # Use the new requirement_text variable and pass all location context
#         report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format(
#             requirement_text=requirement_text, # Pass Requirement Text as jd_text for the prompt
#             cv_text=extracted_cv_text, present_date_str=present_date_str,
#             candidate_name=candidate_name, company_name=company_name,
#             candidate_expected_payout_pm=candidate_expected_payout_pm,
#             candidate_applying_for_location=candidate_applying_for_location, # Pass target location
#             candidate_current_location=candidate_current_location,
#             candidate_relocation_status=relocation_status
#             )
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
#         # Corrected fallback error logging
#         if report_error and not llm_response_record_id:
#              error_msg_fallback = f"Checks passed, but failed generate/log report: {report_error}"; logger.error(error_msg_fallback);
#              existing_log = ac.get_record(ac.LOGS_TABLE_ID, log_record_id); # Fetch log record here before check
#              if existing_log and not existing_log.get('fields', {}).get("Error details"): # Check using string name
#                  ac.update_application_log(log_record_id, {"Error details": error_msg_fallback}) # Update using string name

#         # If report generation failed, we should probably stop here and indicate error?
#         # For now, proceeding to create candidate record even if report failed, but logging the error.
#         if report_error:
#             logger.error(f"Backend report generation failed: {report_error}. Proceeding to create candidate record but flagging.")
#             # Optionally update log here too if needed

#         ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
#         # Use Enum names as keys for candidate_data, matching create_successful_candidate expectation
#         candidate_data_for_airtable = {
#             ac.CandFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id],
#             ac.CandFields.APPLIED_POSITION.name: [requirement_record_id] if requirement_record_id else [], # Link to Requirement record
#             ac.CandFields.NAME.name: candidate_name,
#             ac.CandFields.COMPANY_NAME.name: company_name,
#             ac.CandFields.LLM_MATCH_REASON.name: "Passed prelim checks (Salary, Exp, Edu, Location)." + (" Report generation failed." if report_error else ""), # Append warning if report failed
#             ac.CandFields.INTERVIEW_STATUS.name: "Pending" # Use new Enum name
#          }
#         candidate_record_id = ac.create_successful_candidate(candidate_data_for_airtable)
#         if candidate_record_id:
#             logger.info(f"Created candidate record: {candidate_record_id}");
#             # Use correct field name for update
#             link_cand_success = ac.update_application_log(log_record_id, {"Associated Candidate Record": [candidate_record_id]});
#             if link_cand_success: final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = clarification_reasons
#             else: logger.warning(f"Failed link Cand Rec {candidate_record_id} to Log {log_record_id}."); final_status = "matched"; final_reason = "Passed preliminary checks, link failed."; final_questions = clarification_reasons
#             final_airtable_outcome = "Matched"
#         else: error_msg = "Passed checks, but failed saving candidate record."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", "Error details": error_msg}); final_status = "error"; final_reason = error_msg; final_questions = clarification_reasons; final_airtable_outcome = "Error"

#         final_log_details_content = None
#         if final_airtable_outcome != "Matched": final_log_details_content = final_reason or f"Analysis complete: {final_airtable_outcome}"
#         log_updates = {"Processing Status": "Analysis Complete", "Final Outcome": final_airtable_outcome}
#         # Use correct string name "Error details" for the key when updating
#         if final_log_details_content: log_updates["Error details"] = final_log_details_content[:100000]
#         # Also ensure the backend report gets logged if it exists, even on final update
#         if backend_report and ac.fields.LOG_BACKEND_REPORT: # Check if field ID exists
#             log_updates[ac.fields.LOG_BACKEND_REPORT] = backend_report[:100000] # Log report to Application Log

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
# Added CAND_UNIQUE_GENERATED_ID
CAND_UNIQUE_GENERATED_ID_FIELD = ac.fields.CAND_UNIQUE_GENERATED_ID


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
    relocation_status: str, # This is the variable passed from the frontend
    grad_year_confirmed_by_user: str
) -> Dict[str, Any]:
# *** END FINAL SIGNATURE ***
    start_time = time.time(); present_date_str = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"--- Starting C2C Analysis (V27.1 - New Airtable Schema) ---") # Incremented version
    logger.info(f"Requirement: '{position_title}', CV: '{cv_filename}'"); logger.info(f"Cand: '{candidate_name}', Comp: '{company_name}', Email: {candidate_email}");
    logger.info(f"Target Loc: '{candidate_applying_for_location}', Current Loc: '{candidate_current_location}', Relo Status: '{relocation_status}'") # Uses the passed 'relocation_status'
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
        
        report_prompt = GENERATE_DETAILED_REPORT_PROMPT.format(
            requirement_text=requirement_text,
            cv_text=extracted_cv_text,
            present_date_str=present_date_str,
            candidate_name=candidate_name,
            company_name=company_name,
            candidate_expected_payout_pm=candidate_expected_payout_pm,
            candidate_applying_for_location=candidate_applying_for_location,
            candidate_current_location=candidate_current_location,
            candidate_relocation_status=relocation_status # This is the keyword argument for the placeholder
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
        
        if report_error and not llm_response_record_id:
             error_msg_fallback = f"Checks passed, but failed generate/log report: {report_error}"; logger.error(error_msg_fallback);
             existing_log = ac.get_record(ac.LOGS_TABLE_ID, log_record_id); 
             if existing_log and not existing_log.get('fields', {}).get("Error details"): 
                 ac.update_application_log(log_record_id, {"Error details": error_msg_fallback}) 

        if report_error:
            logger.error(f"Backend report generation failed: {report_error}. Proceeding to create candidate record but flagging.")

        ac.update_application_log(log_record_id, {"Processing Status": "Creating Candidate Record"})
        candidate_data_for_airtable = {
            ac.CandFields.ASSOCIATED_LOG_ENTRY.name: [log_record_id],
            ac.CandFields.APPLIED_POSITION.name: [requirement_record_id] if requirement_record_id else [],
            ac.CandFields.NAME.name: candidate_name,
            ac.CandFields.COMPANY_NAME.name: company_name,
            ac.CandFields.LLM_MATCH_REASON.name: "Passed prelim checks (Salary, Exp, Edu, Location)." + (" Report generation failed." if report_error else ""),
            ac.CandFields.INTERVIEW_STATUS.name: "Pending"
         }
        candidate_record_id = ac.create_successful_candidate(candidate_data_for_airtable)
        
        if candidate_record_id:
            logger.info(f"Created candidate record: {candidate_record_id}");
            
            if CAND_UNIQUE_GENERATED_ID_FIELD:
                update_unique_id_payload = {CAND_UNIQUE_GENERATED_ID_FIELD: candidate_record_id}
                updated_cand_rec = ac.update_record(ac.CANDS_TABLE_ID, candidate_record_id, update_unique_id_payload)
                if updated_cand_rec:
                    logger.info(f"Successfully updated candidate record '{candidate_record_id}' with its own ID in 'Unique generated ID' field.")
                else:
                    logger.error(f"Failed to update candidate record '{candidate_record_id}' with its own ID in 'Unique generated ID' field.")
            else:
                logger.warning("CAND_UNIQUE_GENERATED_ID_FIELD not configured in airtable_client. Skipping update of unique ID field.")

            link_cand_success = ac.update_application_log(log_record_id, {"Associated Candidate Record": [candidate_record_id]});
            if link_cand_success: final_status = "matched"; final_reason = "Candidate passed preliminary checks."; final_questions = clarification_reasons
            else: logger.warning(f"Failed link Cand Rec {candidate_record_id} to Log {log_record_id}."); final_status = "matched"; final_reason = "Passed preliminary checks, link failed."; final_questions = clarification_reasons
            final_airtable_outcome = "Matched"
        else: error_msg = "Passed checks, but failed saving candidate record."; logger.error(error_msg); ac.update_application_log(log_record_id, {"Processing Status": "Error - Candidate Save", "Final Outcome": "Error", "Error details": error_msg}); final_status = "error"; final_reason = error_msg; final_questions = clarification_reasons; final_airtable_outcome = "Error"

        final_log_details_content = None
        if final_airtable_outcome != "Matched": final_log_details_content = final_reason or f"Analysis complete: {final_airtable_outcome}"
        log_updates = {"Processing Status": "Analysis Complete", "Final Outcome": final_airtable_outcome}
        
        if final_log_details_content: log_updates["Error details"] = final_log_details_content[:100000]
        
        if backend_report and ac.fields.LOG_BACKEND_REPORT: 
            log_updates[ac.fields.LOG_BACKEND_REPORT] = backend_report[:100000]

        update_success = ac.update_application_log(log_record_id, log_updates)
        if not update_success: logger.error(f"CRITICAL: Failed update final status log {log_record_id}.")

        final_result_dict["status"] = final_status; final_result_dict["reason"] = final_reason; final_result_dict["questions"] = clarification_reasons; final_result_dict["candidate_id"] = candidate_record_id; final_result_dict["error_message"] = final_reason if final_status == "error" else None; final_result_dict["llm_response_log_id"] = llm_response_record_id
    except Exception as e:
        logger.exception("Unexpected error during main orchestration."); error_msg = f"System error: {type(e).__name__}: {str(e)}"; final_result_dict["status"] = "error"; final_result_dict["error_message"] = error_msg; final_result_dict["reason"] = error_msg
        if log_record_id:
            try: ac.update_application_log(log_record_id, {"Processing Status": "Error - System", "Final Outcome": "Error", "Error details": error_msg}) 
            except Exception as log_e: logger.error(f"CRITICAL: Failed log system error to log {log_record_id}: {log_e}")
    end_time = time.time()
    logger.info(f"--- C2C Analysis Finished: '{cv_filename}'. Status: {final_result_dict.get('status', 'unknown')}. Duration: {end_time - start_time:.2f}s ---")
    return final_result_dict
