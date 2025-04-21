# # portals/public_app.py

# # --- Start Python Path Modification ---
# import os
# import sys
# from typing import List, Optional, Dict, Any
# try:
#     project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
#     if project_root not in sys.path:
#         # print(f"DEBUG: Prepending project root: {project_root}") # Keep commented out unless debugging imports
#         sys.path.insert(0, project_root)
#     from backend import airtable_client as ac
#     from backend.airtable_client import parse_locations
#     from agent import agent_runner
# except ImportError as e:
#     print(f"ERROR: Failed import backend/agent modules. Error: {e}", file=sys.stderr)
#     import streamlit as st
#     st.error(f"App Startup Error: Failed to load core components. Run from project root. Details: `{e}`")
#     st.stop()
# # --- End Python Path Modification ---

# import streamlit as st
# import logging
# import time

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
# logger = logging.getLogger(__name__)

# # --- Streamlit Page Configuration ---
# st.set_page_config(page_title="C2C Candidate Analyzer", page_icon="📄", layout="wide")
# st.title("📄 C2C Candidate Analyzer")
# st.markdown("Upload CV, select Client Requirement, provide candidate details. Required locations will be displayed.")

# # --- Helper Functions ---
# def load_active_requirements_for_display() -> Dict[str, str]:
#     logger.info("Attempting to load active requirements for display...")
#     display_to_title_map: Dict[str, str] = {}
#     try: reqs: Optional[List[Dict[str, Any]]] = ac.get_active_requirements()
#     except ConnectionError as ce: logger.error(f"Airtable connection error loading requirements: {ce}"); st.error(f"Error connecting to Airtable: {ce}"); return {}
#     except Exception as e: logger.exception("Unexpected error loading requirements."); st.error(f"Unexpected error loading requirements: {e}"); return {}
#     if reqs is None: st.error("Failed load requirements (received None)."); return {}
#     if not reqs: st.warning("No active Client Requirements found in Airtable."); return {}
#     processed_titles = set()
#     for req in reqs:
#         title = req.get('title'); location = req.get('location')
#         if title:
#             display_text_base = f"{title}"
#             if location: location_display = (location[:30] + '...') if len(location) > 33 else location; display_text_base += f" ({location_display})"
#             else: display_text_base += " (Location N/A)"
#             display_text = display_text_base; count = 2
#             while display_text in display_to_title_map: display_text = f"{display_text_base} #{count}"; count += 1
#             display_to_title_map[display_text] = title; processed_titles.add(title)
#     logger.info(f"Loaded {len(display_to_title_map)} unique display requirements.")
#     return display_to_title_map

# def update_selected_requirement_info():
#     selected_display = st.session_state.get("req_select_display", "")
#     req_map = st.session_state.get("req_display_map", {})
#     logger.debug(f"Callback triggered. Selected display text: '{selected_display}'")
#     st.session_state.selected_req_locations_list = None
#     st.session_state.selected_req_title = None
#     if selected_display and selected_display in req_map:
#         selected_title = req_map[selected_display]; st.session_state.selected_req_title = selected_title
#         logger.info(f"Fetching details for Requirement Title: '{selected_title}'...")
#         try:
#             req_details_record = ac.get_requirement_details_by_title(selected_title)
#             if req_details_record and 'fields' in req_details_record:
#                 location_str = req_details_record['fields'].get("Location")
#                 parsed_locs = parse_locations(location_str)
#                 st.session_state.selected_req_locations_list = parsed_locs
#                 logger.info(f"Fetched locations for '{selected_title}': {parsed_locs}")
#             else: logger.warning(f"Could not fetch details/fields for Req Title: {selected_title}"); st.session_state.selected_req_locations_list = []
#         except Exception as e: logger.exception(f"Error fetching details for Req '{selected_title}' in callback."); st.error(f"Error fetching required locations: {e}"); st.session_state.selected_req_locations_list = []
#     else: logger.debug("No valid Requirement selected, state cleared.")

# # --- Initialize Session State Keys ---
# default_state_values = {
#     "selected_req_locations_list": None,
#     "selected_req_title": None,
#     "req_display_map": {},
#     "req_select_display": "",
#     # Form input keys are now implicitly managed by the form itself when clear_on_submit=True
#     # We no longer need explicit keys here like "cand_name_in_form", etc. for default setting
#     # unless we want to pre-populate them *outside* the form context, which we don't.
#     "analysis_result": None,
#     "submitted_flag": False,
#     # "clear_form_on_next_run": False # REMOVED this flag
# }
# for key, default_value in default_state_values.items():
#     if key not in st.session_state:
#         st.session_state[key] = default_value

# # --- REMOVED Manual Form Clearing Logic Block ---
# # The block checking for "clear_form_on_next_run" has been removed.

# # --- Main Application Logic ---

# if not st.session_state.req_display_map:
#      st.session_state.req_display_map = load_active_requirements_for_display()
# req_display_to_title_map = st.session_state.req_display_map

# if not req_display_to_title_map:
#     st.warning("Cannot proceed: No active Client Requirements loaded from Airtable. Please check Airtable or refresh.")
# else:
#     st.subheader("1. Select Client Requirement")
#     req_options = [""] + sorted(list(req_display_to_title_map.keys()))
#     # Note: No 'index' needed here if we rely on default selection or the callback
#     st.selectbox(
#          "Select Requirement*", options=req_options,
#          key="req_select_display",
#          help="Select the target client requirement.",
#          on_change=update_selected_requirement_info,
#          # index=req_options.index(st.session_state.req_select_display) if st.session_state.req_select_display in req_options else 0 # Optional: Can keep if preferred
#     )
#     st.divider()

#     # --- UPDATED form definition ---
#     with st.form("cv_submit_form", clear_on_submit=True): # Set clear_on_submit=True
#         st.subheader("2. Candidate & Company Details")
#         col2a, col2b = st.columns(2)
#         with col2a:
#             # Assign keys so we can read values after submission
#             cand_name_submitted = st.text_input("Candidate Name*", placeholder="e.g., Jane Doe", key="cand_name_in_form")
#             email_submitted = st.text_input("Candidate Email (Optional)", placeholder="e.g., name@example.com", key="cand_email_in_form")
#         with col2b:
#             comp_name_submitted = st.text_input("Company Name*", placeholder="e.g., Tech Solutions Inc.", key="company_name_in_form")
#             payout_submitted = st.number_input("Candidate Budget in INR*", min_value=0.0, step=1000.0, format="%.0f", placeholder="e.g., 200000", help="Enter expected monthly compensation in INR.", key="candidate_payout_pm_in_form")

#         st.subheader("3. Location Details & CV Upload")
#         col3a, col3b = st.columns([3, 2])
#         with col3a:
#              locations_list = st.session_state.get("selected_req_locations_list")
#              if st.session_state.req_select_display:
#                  if locations_list is not None:
#                      if locations_list: loc_text = ", ".join([f"**{loc}**" for loc in locations_list]); st.info(f"ℹ️ **Required Locations:** {loc_text}.", icon="📍")
#                      else: st.warning("⚠️ No specific locations listed for this Requirement.", icon=" ")
#                  else: st.warning("⏳ Loading required locations...")
#              else:
#                  st.markdown("_(Select a Requirement above to see required locations)_")

#              final_target_location = st.text_input( "For which location are you applying for?*", placeholder="Enter one location from the list above", key="target_location_in_form", help="Type the specific required location this candidate is targeting." )
#              final_current_location = st.text_input( "Candidate's Current Location*", placeholder="e.g., Mumbai, India", key="candidate_current_location_in_form", help="Enter the candidate's current primary work location." )
#         with col3b:
#              # Assign key to read the uploaded file state
#              cv_file_submitted = st.file_uploader( "Upload Candidate CV*", type=["pdf", "docx"], help="Upload resume (PDF/DOCX, max 10MB).", key="cv_upload_in_form" )
#              st.markdown("<br/>", unsafe_allow_html=True)
#              relocation_options = [
#                  "Candidate is already in a required city/location",
#                  "Candidate is elsewhere but WILL relocate to a required location"
#              ]
#              final_relocation_status = st.radio( "Candidate Location Status*", options=relocation_options, key="relocation_status_in_form", # index removed
#                        help="Select candidate's situation relative to required location(s)." )

#         st.subheader("4. Final Confirmation")
#         grad_options = ["Yes", "No", "Not Applicable/Sure"]
#         grad_confirm_submitted = st.radio("Is graduation year clearly specified in the CV?*", options=grad_options, key="grad_year_confirm_in_form", # index removed
#                    horizontal=True)

#         # --- Submit button remains inside the form ---
#         submitted = st.form_submit_button("Submit")
#         if submitted:
#             st.session_state.submitted_flag = True
#             st.session_state.analysis_result = None
#             # Store submitted values in session_state temporarily AFTER submit is clicked,
#             # because the form widgets will clear on rerun if clear_on_submit=True.
#             # We need these values for the processing block below the form.
#             st.session_state.temp_submitted_data = {
#                 "selected_req_title": st.session_state.selected_req_title, # Get title from state set by selectbox callback
#                 "cv_file": cv_file_submitted,
#                 "cand_name": cand_name_submitted,
#                 "comp_name": comp_name_submitted,
#                 "payout": payout_submitted,
#                 "target_loc": final_target_location,
#                 "current_loc": final_current_location,
#                 "relo_status": final_relocation_status,
#                 "grad_confirm": grad_confirm_submitted,
#                 "email": email_submitted
#             }


# # --- Process Submission & Display Results (Triggered by submitted_flag) ---
# if st.session_state.submitted_flag:
#     st.divider(); st.subheader("Analysis Results")

#     # Retrieve the temporarily stored data
#     submitted_data = st.session_state.get("temp_submitted_data", {})

#     # --- Read values from the stored dictionary ---
#     final_selected_req_title = submitted_data.get("selected_req_title")
#     cv_file_to_process = submitted_data.get("cv_file") # This is the UploadedFile object
#     cand_name_to_process = submitted_data.get("cand_name", "").strip()
#     comp_name_to_process = submitted_data.get("comp_name", "").strip()
#     payout_to_process = submitted_data.get("payout")
#     target_loc_to_process = submitted_data.get("target_loc", "").strip()
#     current_loc_to_process = submitted_data.get("current_loc", "").strip()
#     relo_status_to_process = submitted_data.get("relo_status")
#     grad_confirm_to_process = submitted_data.get("grad_confirm")
#     email_to_process = submitted_data.get("email", "").strip()

#     # Perform validation using the retrieved values
#     validation_errors = []
#     if not final_selected_req_title: validation_errors.append("Please select a Client Requirement.")
#     if not cv_file_to_process: validation_errors.append("Please upload the CV file.") # Check the file object
#     if not cand_name_to_process: validation_errors.append("Please enter Candidate Name.")
#     if not comp_name_to_process: validation_errors.append("Please enter Company Name.")
#     if not target_loc_to_process: validation_errors.append("Please enter the Location Applying For.")
#     if not current_loc_to_process: validation_errors.append("Please enter Current Location.")
#     if relo_status_to_process is None: validation_errors.append("Please select Location Status.") # Check the value
#     if payout_to_process is None or payout_to_process <= 0: validation_errors.append("Please enter valid Candidate Budget (> 0).")
#     if grad_confirm_to_process is None: validation_errors.append("Please confirm grad year presence in CV.") # Check the value

#     if validation_errors:
#         st.error("Please fix the following errors in the form above:"); error_cols = st.columns(2)
#         for i, error in enumerate(validation_errors): error_cols[i % 2].warning(f"- {error}")
#         # Reset submitted_flag so user can correct and resubmit
#         st.session_state.submitted_flag = False
#         # Clear temp data if validation fails
#         if "temp_submitted_data" in st.session_state:
#             del st.session_state.temp_submitted_data
#     elif final_selected_req_title and cv_file_to_process: # Ensure these exist before proceeding
#         progress_bar = st.progress(0, text="Initializing analysis..."); status_placeholder = st.empty(); status_placeholder.info("🚀 Connecting and preparing...")
#         try:
#             # Get bytes and filename from the UploadedFile object
#             cv_bytes = cv_file_to_process.getvalue(); cv_filename = cv_file_to_process.name
#             logger.info(f"Form validated. Analyzing '{cand_name_to_process}' for Req: '{final_selected_req_title}'")
#             progress_bar.progress(20, text="Performing AI analysis..."); status_placeholder.info("🧠 AI analysis in progress...")

#             # Pass the processed values to the analysis function
#             analysis_result_dict = agent_runner.run_c2c_analysis(
#                 position_title=final_selected_req_title, cv_filename=cv_filename, cv_file_bytes=cv_bytes,
#                 candidate_email=email_to_process if email_to_process else None, candidate_name=cand_name_to_process, company_name=comp_name_to_process,
#                 candidate_expected_payout_pm=float(payout_to_process), candidate_applying_for_location=target_loc_to_process,
#                 candidate_current_location=current_loc_to_process, relocation_status=relo_status_to_process,
#                 grad_year_confirmed_by_user=grad_confirm_to_process
#             )
#             st.session_state.analysis_result = analysis_result_dict
#             progress_bar.progress(100, text="Analysis Complete!"); status_placeholder.empty(); time.sleep(0.5); progress_bar.empty()

#         except AttributeError as ae:
#              logger.error(f"Error accessing uploaded file: {ae}. Was a file uploaded correctly?"); progress_bar.progress(100, text="Error!"); status_placeholder.error("Error processing uploaded file. Please ensure a CV is uploaded.")
#              st.error("Error Details: Could not read the uploaded CV file. Please re-upload and try again.")
#              st.session_state.analysis_result = { "status": "error", "reason": "CV file read error.", "error_message": "Could not read the uploaded CV file.", "questions": [], "candidate_id": None, "llm_response_log_id": None }
#         except Exception as e:
#             logger.exception("Error during analysis call in frontend."); progress_bar.progress(100, text="Error!"); status_placeholder.error("An unexpected application error occurred during analysis.")
#             st.error(f"Error Details: {type(e).__name__}: {str(e)}")
#             st.session_state.analysis_result = { "status": "error", "reason": "Application error during analysis.", "error_message": f"{type(e).__name__}: {str(e)}", "questions": [], "candidate_id": None, "llm_response_log_id": None }
#         finally:
#              # Clear temp data after processing (success or failure)
#              if "temp_submitted_data" in st.session_state:
#                  del st.session_state.temp_submitted_data

#     # --- Display results based on st.session_state.analysis_result ---
#     if st.session_state.analysis_result:
#         result_data = st.session_state.analysis_result
#         analysis_status = result_data.get("status"); questions = result_data.get("questions", []); reason = result_data.get("reason", "N/A."); candidate_id = result_data.get("candidate_id"); error_message = result_data.get("error_message"); llm_log_id = result_data.get("llm_response_log_id")

#         if analysis_status == "error":
#             st.error(f"❗️ Analysis Failed: {error_message or reason}")
#         elif analysis_status == "clarification_needed":
#             st.warning(f"⚠️ Clarifications Needed: {reason}");
#             if questions: st.markdown("**Please address these points in the form above and resubmit:**"); q_cols = st.columns(2); [q_cols[i % 2].markdown(f"{i+1}. {str(q)}") for i, q in enumerate(questions)]
#             else: st.info("Check the reason above, update the form, and resubmit.")
#             # User needs to refill the cleared form to resubmit
#         elif analysis_status == "rejected":
#             st.error(f"❌ Candidate Not Matched: {reason}")
#             # Form is already cleared
#         elif analysis_status == "matched":
#             st.success(f"✅ Candidate Matched! Reason: {reason}")
#             if candidate_id:
#                 st.markdown(f"### Candidate Record ID: `{candidate_id}`")
#                 st.markdown("---"); st.subheader("Next Steps:"); st.markdown("Use the Candidate Record ID above for tracking in Airtable.")
#                 st.markdown("**Schedule Interview (Example Links):**")
#                 cols_cal = st.columns(3)
#                 with cols_cal[0]: st.link_button("Slot 1", "https://calendar.app.google/PBXeho3g8yttKGGz6", use_container_width=True)
#                 with cols_cal[1]: st.link_button("Slot 2", "https://calendar.app.google/Pu6PXtBqGamA36C47", use_container_width=True)
#                 with cols_cal[2]: st.link_button("Slot 3", "https://calendar.app.google/kHVa9aCLBrT2JjDy9", use_container_width=True)

#                 # REMOVED flag setting and info message about clearing
#                 st.info("Form has been cleared. You can submit another candidate.")

#             else: st.error("Analysis indicated 'Matched', but failed to create/retrieve the Candidate Record ID from the backend.")
#         else:
#             st.error(f"❗️ Unknown Status Received: '{analysis_status}' (Reason: {reason})")

#         # Reset submitted_flag after processing results
#         st.session_state.submitted_flag = False
#         # Ensure analysis_result is reset so it doesn't redisplay on simple interaction
#         # st.session_state.analysis_result = None # Or leave it to show last result until new submission


# # --- Footer ---
# st.divider()
# st.markdown("<div style='text-align: center; font-size: small;'>Staff Augmentation Analyzer v2.3 | Powered by Streamlit & Google Gemini</div>", unsafe_allow_html=True) # Updated version



# portals/public_app.py

# --- Start Python Path Modification ---
import os
import sys
from typing import List, Optional, Dict, Any
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        # print(f"DEBUG: Prepending project root: {project_root}") # Keep commented out unless debugging imports
        sys.path.insert(0, project_root)
    # Ensure these imports work correctly after the env var refactor in airtable_client
    from backend import airtable_client as ac
    from backend.airtable_client import parse_locations
    from agent import agent_runner
except ImportError as e:
    print(f"ERROR: Failed import backend/agent modules. Error: {e}", file=sys.stderr)
    import streamlit as st
    st.error(f"App Startup Error: Failed to load core components. Run from project root. Details: `{e}`")
    st.stop()
# --- End Python Path Modification ---

import streamlit as st
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(module)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="C2C Candidate Analyzer", page_icon="📄", layout="wide")
st.title("📄 C2C Candidate Analyzer")
st.markdown("Upload CV, select Client Requirement, provide candidate details. Required locations will be displayed.")

# --- Helper Functions ---
# No changes needed here - seem consistent with airtable_client
def load_active_requirements_for_display() -> Dict[str, str]:
    logger.info("Attempting to load active requirements for display...")
    display_to_title_map: Dict[str, str] = {}
    try: reqs: Optional[List[Dict[str, Any]]] = ac.get_active_requirements()
    except ConnectionError as ce: logger.error(f"Airtable connection error loading requirements: {ce}"); st.error(f"Error connecting to Airtable: {ce}"); return {}
    except Exception as e: logger.exception("Unexpected error loading requirements."); st.error(f"Unexpected error loading requirements: {e}"); return {}
    if reqs is None: st.error("Failed load requirements (received None)."); return {}
    if not reqs: st.warning("No active Client Requirements found in Airtable."); return {}
    processed_titles = set()
    for req in reqs:
        title = req.get('title'); location = req.get('location')
        if title:
            display_text_base = f"{title}"
            if location: location_display = (location[:30] + '...') if len(location) > 33 else location; display_text_base += f" ({location_display})"
            else: display_text_base += " (Location N/A)"
            display_text = display_text_base; count = 2
            while display_text in display_to_title_map: display_text = f"{display_text_base} #{count}"; count += 1
            display_to_title_map[display_text] = title; processed_titles.add(title)
    logger.info(f"Loaded {len(display_to_title_map)} unique display requirements.")
    return display_to_title_map

# No changes needed here - seem consistent with airtable_client
def update_selected_requirement_info():
    # Reads the current value of the selectbox
    selected_display = st.session_state.get("req_select_display", "")
    req_map = st.session_state.get("req_display_map", {})
    logger.debug(f"Callback triggered. Selected display text: '{selected_display}'")
    # Updates other session state keys based on the selection
    st.session_state.selected_req_locations_list = None
    st.session_state.selected_req_title = None
    if selected_display and selected_display in req_map:
        selected_title = req_map[selected_display]; st.session_state.selected_req_title = selected_title
        logger.info(f"Fetching details for Requirement Title: '{selected_title}'...")
        try:
            req_details_record = ac.get_requirement_details_by_title(selected_title)
            if req_details_record and 'fields' in req_details_record:
                location_str = req_details_record['fields'].get("Location")
                parsed_locs = parse_locations(location_str)
                st.session_state.selected_req_locations_list = parsed_locs
                logger.info(f"Fetched locations for '{selected_title}': {parsed_locs}")
            else: logger.warning(f"Could not fetch details/fields for Req Title: {selected_title}"); st.session_state.selected_req_locations_list = []
        except Exception as e: logger.exception(f"Error fetching details for Req '{selected_title}' in callback."); st.error(f"Error fetching required locations: {e}"); st.session_state.selected_req_locations_list = []
    else: logger.debug("No valid Requirement selected, state cleared.")

# --- Initialize Session State Keys ---
# Reduced keys as form inputs are implicitly handled by form reset
default_state_values = {
    "selected_req_locations_list": None,
    "selected_req_title": None,
    "req_display_map": {},
    "req_select_display": "", # Keep state for the selectbox outside the form
    "analysis_result": None,
    "submitted_flag": False,
    "temp_submitted_data": {} # Initialize the temporary storage
}
for key, default_value in default_state_values.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# --- Main Application Logic ---

# Load requirements if map is empty (runs on first load and if state gets cleared)
if not st.session_state.req_display_map:
     st.session_state.req_display_map = load_active_requirements_for_display()
req_display_to_title_map = st.session_state.req_display_map

if not req_display_to_title_map:
    st.warning("Cannot proceed: No active Client Requirements loaded from Airtable. Please check Airtable or refresh.")
else:
    # --- Requirement Selection (Outside the Form) ---
    st.subheader("1. Select Client Requirement")
    req_options = [""] + sorted(list(req_display_to_title_map.keys()))
    # This selectbox retains its state across form submissions because it's outside the form
    # Its state is managed by the "req_select_display" key and the on_change callback
    st.selectbox(
         "Select Requirement*", options=req_options,
         key="req_select_display",
         help="Select the target client requirement.",
         on_change=update_selected_requirement_info,
         # index is optional, default selection "" works
    )
    st.divider()

    # --- Form Definition (clear_on_submit=True) ---
    with st.form("cv_submit_form", clear_on_submit=True):
        st.subheader("2. Candidate & Company Details")
        col2a, col2b = st.columns(2)
        with col2a:
            # Assign keys to capture values on submit
            cand_name_submitted = st.text_input("Candidate Name*", placeholder="e.g., Jane Doe", key="cand_name_in_form")
            email_submitted = st.text_input("Vendor Email", placeholder="e.g., name@example.com", key="cand_email_in_form")
        with col2b:
            comp_name_submitted = st.text_input("Company Name*", placeholder="e.g., Tech Solutions Inc.", key="company_name_in_form")
            payout_submitted = st.number_input("Candidate Budget in INR*", min_value=0.0, step=1000.0, format="%.0f", placeholder="e.g., 200000", help="Enter expected monthly compensation in INR.", key="candidate_payout_pm_in_form", value=None) # Explicitly set default to None

        st.subheader("3. Location Details & CV Upload")
        col3a, col3b = st.columns([3, 2])
        with col3a:
             # Display locations based on state updated by the selectbox callback
             locations_list = st.session_state.get("selected_req_locations_list")
             if st.session_state.req_select_display: # Check if a requirement is selected
                 if locations_list is not None: # Check if details have been fetched
                     if locations_list: loc_text = ", ".join([f"**{loc}**" for loc in locations_list]); st.info(f"ℹ️ **Required Locations:** {loc_text}.", icon="📍")
                     else: st.warning("⚠️ No specific locations listed for this Requirement.", icon=" ")
                 else: st.warning("⏳ Loading required locations...") # State while fetching
             else:
                 st.markdown("_(Select a Requirement above to see required locations)_") # Prompt

             # Assign keys to capture values on submit
             final_target_location = st.text_input( "For which location are you applying for?*", placeholder="Enter one location from the list above", key="target_location_in_form", help="Type the specific required location this candidate is targeting." )
             final_current_location = st.text_input( "Candidate's Current Location*", placeholder="e.g., Mumbai, India", key="candidate_current_location_in_form", help="Enter the candidate's current primary work location." )
        with col3b:
             # Assign key to capture value on submit
             cv_file_submitted = st.file_uploader( "Upload Candidate CV*", type=["pdf", "docx"], help="Upload resume (PDF/DOCX, max 10MB).", key="cv_upload_in_form" )
             st.markdown("<br/>", unsafe_allow_html=True)
             relocation_options = [
                 "Candidate is already in a required city/location",
                 "Candidate is elsewhere but WILL relocate to a required location"
             ]
             # Assign key to capture value on submit
             # Set index=None for radio to ensure a default isn't pre-selected unless intended
             # And makes validation check for None more reliable if user doesn't interact
             final_relocation_status = st.radio( "Candidate Location Status*", options=relocation_options, key="relocation_status_in_form", index=None,
                       help="Select candidate's situation relative to required location(s)." )

        st.subheader("4. Final Confirmation")
        grad_options = ["Yes", "No", "Not Applicable/Sure"]
        # Assign key to capture value on submit
        # Set index=None for same reason as above
        grad_confirm_submitted = st.radio("Is graduation year clearly specified in the CV?*", options=grad_options, key="grad_year_confirm_in_form", index=None,
                   horizontal=True)

        # --- Submit Button ---
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state.submitted_flag = True
            # Store captured values immediately before form clears on rerun
            st.session_state.temp_submitted_data = {
                "selected_req_title": st.session_state.selected_req_title, # Read from state
                "cv_file": cv_file_submitted, # From widget variable
                "cand_name": cand_name_submitted, # From widget variable
                "comp_name": comp_name_submitted, # From widget variable
                "payout": payout_submitted, # From widget variable
                "target_loc": final_target_location, # From widget variable
                "current_loc": final_current_location, # From widget variable
                "relo_status": final_relocation_status, # From widget variable
                "grad_confirm": grad_confirm_submitted, # From widget variable
                "email": email_submitted # From widget variable
            }


# --- Process Submission & Display Results (Triggered by submitted_flag) ---
if st.session_state.submitted_flag:
    st.divider(); st.subheader("Analysis Results")

    # Retrieve the temporarily stored data
    # Use .get with defaults for safer access in case temp_submitted_data is somehow cleared unexpectedly
    submitted_data = st.session_state.get("temp_submitted_data", {})

    # Read values from the stored dictionary
    final_selected_req_title = submitted_data.get("selected_req_title")
    cv_file_to_process = submitted_data.get("cv_file") # UploadedFile object or None
    cand_name_to_process = submitted_data.get("cand_name", "").strip()
    comp_name_to_process = submitted_data.get("comp_name", "").strip()
    payout_to_process = submitted_data.get("payout") # number or None
    target_loc_to_process = submitted_data.get("target_loc", "").strip()
    current_loc_to_process = submitted_data.get("current_loc", "").strip()
    relo_status_to_process = submitted_data.get("relo_status") # string or None
    grad_confirm_to_process = submitted_data.get("grad_confirm") # string or None
    email_to_process = submitted_data.get("email", "").strip()

    # Perform validation using the retrieved values
    validation_errors = []
    if not final_selected_req_title: validation_errors.append("Please select a Client Requirement.")
    if not cv_file_to_process: validation_errors.append("Please upload the CV file.")
    if not cand_name_to_process: validation_errors.append("Please enter Candidate Name.")
    if not comp_name_to_process: validation_errors.append("Please enter Company Name.")
    if not target_loc_to_process: validation_errors.append("Please enter the Location Applying For.")
    if not current_loc_to_process: validation_errors.append("Please enter Current Location.")
    # Check explicitly for None for radio buttons that start with index=None
    if relo_status_to_process is None: validation_errors.append("Please select Candidate Location Status.")
    if payout_to_process is None or payout_to_process <= 0: validation_errors.append("Please enter valid Candidate Budget (> 0).")
    if grad_confirm_to_process is None: validation_errors.append("Please confirm if graduation year is specified in CV.")

    if validation_errors:
        st.error("Please fix the following errors in the form above:"); error_cols = st.columns(2)
        for i, error in enumerate(validation_errors): error_cols[i % 2].warning(f"- {error}")
        st.session_state.submitted_flag = False # Allow correction
        # Clear temp data if validation fails, otherwise it might persist
        if "temp_submitted_data" in st.session_state:
            del st.session_state.temp_submitted_data
    # Ensure key values exist before proceeding to analysis
    elif final_selected_req_title and cv_file_to_process:
        progress_bar = st.progress(0, text="Initializing analysis..."); status_placeholder = st.empty(); status_placeholder.info("🚀 Connecting and preparing...")
        try:
            cv_bytes = cv_file_to_process.getvalue(); cv_filename = cv_file_to_process.name
            logger.info(f"Form validated. Analyzing '{cand_name_to_process}' for Req: '{final_selected_req_title}'")
            progress_bar.progress(20, text="Performing AI analysis..."); status_placeholder.info("🧠 AI analysis in progress...")

            # Call agent runner - seems consistent with agent_runner signature
            analysis_result_dict = agent_runner.run_c2c_analysis(
                position_title=final_selected_req_title, cv_filename=cv_filename, cv_file_bytes=cv_bytes,
                candidate_email=email_to_process if email_to_process else None, candidate_name=cand_name_to_process, company_name=comp_name_to_process,
                candidate_expected_payout_pm=float(payout_to_process), candidate_applying_for_location=target_loc_to_process,
                candidate_current_location=current_loc_to_process, relocation_status=relo_status_to_process,
                grad_year_confirmed_by_user=grad_confirm_to_process
            )
            # Store result
            st.session_state.analysis_result = analysis_result_dict
            progress_bar.progress(100, text="Analysis Complete!"); status_placeholder.empty(); time.sleep(0.5); progress_bar.empty()

        except AttributeError as ae:
             # Handle case where file object might be invalid after upload somehow
             logger.error(f"Error accessing uploaded file attributes: {ae}. File object: {cv_file_to_process}"); progress_bar.progress(100, text="Error!"); status_placeholder.error("Error processing uploaded file. Please ensure a CV is uploaded.")
             st.error("Error Details: Could not read the uploaded CV file. Please re-upload and try again.")
             st.session_state.analysis_result = { "status": "error", "reason": "CV file read error.", "error_message": "Could not read the uploaded CV file.", "questions": [], "candidate_id": None, "llm_response_log_id": None }
        except Exception as e:
            logger.exception("Error during analysis call in frontend."); progress_bar.progress(100, text="Error!"); status_placeholder.error("An unexpected application error occurred during analysis.")
            st.error(f"Error Details: {type(e).__name__}: {str(e)}")
            st.session_state.analysis_result = { "status": "error", "reason": "Application error during analysis.", "error_message": f"{type(e).__name__}: {str(e)}", "questions": [], "candidate_id": None, "llm_response_log_id": None }
        finally:
             # Ensure temp data is cleared regardless of analysis outcome
             if "temp_submitted_data" in st.session_state:
                 del st.session_state.temp_submitted_data

    # --- Display results based on st.session_state.analysis_result ---
    # This block runs only if submitted_flag was true initially
    # It reads the result stored in session state by the block above
    if st.session_state.analysis_result:
        result_data = st.session_state.analysis_result
        analysis_status = result_data.get("status"); questions = result_data.get("questions", []); reason = result_data.get("reason", "N/A."); candidate_id = result_data.get("candidate_id"); error_message = result_data.get("error_message"); llm_log_id = result_data.get("llm_response_log_id")

        # Display based on status
        if analysis_status == "error":
            st.error(f"❗️ Analysis Failed: {error_message or reason}")
        elif analysis_status == "clarification_needed":
            st.warning(f"⚠️ Clarifications Needed: {reason}");
            if questions: st.markdown("**Please address these points in the form above and resubmit:**"); q_cols = st.columns(2); [q_cols[i % 2].markdown(f"{i+1}. {str(q)}") for i, q in enumerate(questions)]
            else: st.info("Check the reason above, update the form, and resubmit.")
        elif analysis_status == "rejected":
            st.error(f"❌ Candidate Not Matched: {reason}")
        elif analysis_status == "matched":
            st.success(f"✅ Candidate Matched! Reason: {reason}")
            if candidate_id:
                st.markdown(f"### Candidate Record ID: `{candidate_id}`")
                st.markdown("---"); st.subheader("Next Steps:"); st.markdown("Use the Candidate Record ID above for tracking in Airtable.")
                st.markdown("**Schedule Interview (Example Links):**")
                cols_cal = st.columns(3)
                with cols_cal[0]: st.link_button("Slot 1", "https://calendar.app.google/PBXeho3g8yttKGGz6", use_container_width=True)
                with cols_cal[1]: st.link_button("Slot 2", "https://calendar.app.google/Pu6PXtBqGamA36C47", use_container_width=True)
                with cols_cal[2]: st.link_button("Slot 3", "https://calendar.app.google/kHVa9aCLBrT2JjDy9", use_container_width=True)
                st.info("Form has been cleared. You can submit another candidate.")
            else: st.error("Analysis indicated 'Matched', but failed to create/retrieve the Candidate Record ID from the backend.")
        else:
            st.error(f"❗️ Unknown Status Received: '{analysis_status}' (Reason: {reason})")

        # Reset submitted_flag after processing results to prevent re-running analysis on interactions
        st.session_state.submitted_flag = False
        # Reset analysis_result *after* displaying it, so it doesn't persist visually until next submission
        st.session_state.analysis_result = None


# --- Footer ---
st.divider()
st.markdown("<div style='text-align: center; font-size: small;'>Staff Augmentation Analyzer v2.3 | Powered by Streamlit & Google Gemini</div>", unsafe_allow_html=True)
