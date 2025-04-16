# # agent/agent_definition.py
# import os
# import logging
# from dotenv import load_dotenv
# import openai

# # --- [Existing OpenAI Client Setup Code - No changes needed here] ---
# # (Includes print statements for debugging, keep them for now)
# print("DEBUG: agent_definition.py - Starting execution")
# load_dotenv()
# print("DEBUG: agent_definition.py - load_dotenv() called")
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
# logger.debug("DEBUG: agent_definition.py - Logging configured")
# print("DEBUG: agent_definition.py - Logging configured")
# client = None
# OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
# try:
#     # ... [rest of the client init code remains the same] ...
#     print("DEBUG: agent_definition.py - About to call openai.OpenAI()...")
#     openai_api_key = os.getenv("OPENAI_API_KEY")
#     if openai_api_key is None:
#         raise ValueError("openai_api_key not found in environment variables.")
#     client = openai.OpenAI(api_key=openai_api_key)
#     print("DEBUG: agent_definition.py - openai.OpenAI() call completed.")
#     logger.info(f"OpenAI client initialized successfully for model: {OPENAI_MODEL_NAME}")
#     print("DEBUG: agent_definition.py - OpenAI client object created successfully.")
# except Exception as e: # Catch all exceptions during init
#     logger.exception(f"Fatal: Error during OpenAI client configuration: {e}")
#     print(f"ERROR: agent_definition.py - Error during OpenAI config: {type(e).__name__}: {e}")
#     raise ConnectionError(f"Fatal Error: Could not configure OpenAI client. Error: {e}") from e
# # --- [End of Existing OpenAI Client Setup Code] ---


# # --- UPDATED DETAILED PROMPT TEMPLATE ---
# CV_ASSESSMENT_PROMPT_TEMPLATE = """
# You are an expert C2C Candidate Screening Agent. Your task is to meticulously analyze the provided Job Description (JD) and Candidate CV, incorporating user-provided context. You must generate a comprehensive *internal analysis report* following the exact structure below, AND determine a final `outcome_status` ('Matched', 'Rejected', 'Clarification Needed') and a list of `clarifying_questions`. The present date is {present_date}.

# **User Provided Context:**
# *   Position Budget (LPA): {user_budget_lpa}
# *   Required Job Location: {user_required_location}
# *   Candidate Location Status: {user_candidate_location_status}
# *   CV Explicitly Contains Graduation Year: {user_grad_year_confirmed}

# **CRITICAL INSTRUCTIONS:**
# *   **Handle CV Variations:** Analyze the CV text thoroughly, identifying sections like Work Experience, Education, Skills, etc., even if the formatting or structure varies between documents.
# *   **Use User Inputs:** Prioritize the `user_budget_lpa` and `user_required_location` provided above. Use `user_candidate_location_status` and `user_grad_year_confirmed` to inform your analysis and question generation.
# *   **Extract from Docs:** Still attempt to extract Candidate Cost/Rate and Candidate Location from the CV text itself.
# *   **Clarify if Missing/Conflicting:** Generate `clarifying_questions` if:
#     *   Candidate Cost/Rate is missing from CV.
#     *   Candidate Location is missing from CV *and* user status is "Location details not specified/known".
#     *   User says grad year is NOT in CV (`user_grad_year_confirmed` == 'No').
#     *   There are ambiguous dates in CV.
#     *   There are gaps > 1 month in timeline.
#     *   There are missing Must-Have skills from JD in CV.
#     *   The extracted CV cost (if found) EXCEEDS the `user_budget_lpa`.
#     *   The extracted CV location (if found) CONFLICTS with `user_required_location` AND `user_candidate_location_status` is NOT "will relocate".
# *   **Determine `outcome_status`:**
#     *   `Rejected`: If critical Must-Have skills are missing OR if extracted CV cost > `user_budget_lpa` OR if location mismatch cannot be resolved by user input.
#     *   `Clarification Needed`: If the outcome is not 'Rejected' but there are *any* items in `clarifying_questions`.
#     *   `Matched`: Only if the outcome is not 'Rejected' AND the `clarifying_questions` list is EMPTY.
# *   **Output Format:** Generate the *entire* detailed report text below first, using markdown formatting (especially for tables). Conclude with a JSON block containing the final status and questions. Ensure headers exactly match `## [Number]. [Section Title]`.

# --- START OF INTERNAL ANALYSIS REPORT ---

# ## 1. Clarifying Questions for Vendor

# *List Questions Here based on CRITICAL INSTRUCTIONS:*
# - [Question 1...]
# - [Question 2...]

# ## 2. Candidate Requirement Matching Table

# | JD Requirement                 | Candidate's Details (from CV) | Match Rating        | Comments/Notes (Incorporate User Input)          |
# | :----------------------------- | :---------------------------- | :------------------ | :----------------------------------------------- |
# | [Skill/Exp/Cert from JD]       | [Relevant detail from CV]     | [Excellent/Good/Fair/Poor/Score] | [Gap/Ambiguity Note]                           |
# | ...                            | ...                           | ...                 | ...                                              |
# | **Required Location**          | {user_required_location} (User Input) | N/A              | Considered in analysis                           |
# | **Candidate Location (from CV)**| [Extracted Loc or "Not Found"] | N/A                 | Compared w/ user status: {user_candidate_location_status} |
# | **Position Budget (LPA)**      | {user_budget_lpa} (User Input)  | N/A                | Used for comparison                              |
# | **Candidate Cost (from CV)**   | [Extracted Cost or "Not Found"] | N/A                | Compared w/ budget if found                      |
# | **Graduation Year in CV**      | Per User: {user_grad_year_confirmed} | N/A             | Checked during Education Analysis                |

# ## 3. Preliminary Analysis of Timelines Table

# | Category          | Detail                               | Start Date | End Date   | Duration (Years/Months) | Notes                          |
# | :---------------- | :----------------------------------- | :--------- | :--------- | :---------------------- | :----------------------------- |
# | **Education**     | [Degree], [Institution]              | N/A        | [Grad Year]-06 (Assumed/Actual) | N/A                     | [Note if month assumed]        |
# | ...               | ...                                  | ...        | ...        | ...                     | ...                            |
# | **Work Experience**| [Job Title] at [Company]             | [YYYY-MM]  | [YYYY-MM]  | [Xy Ym]                 |                                |
# | ...               | ...                                  | ...        | ...        | ...                     |                                |
# | **Total Relevant Exp**|                                  | N/A        | N/A        | [Calculated Yy Mm]      | [Sum of relevant durations]    |
# | **Required Exp(JD)**|                                  | N/A        | N/A        | [From JD]               |                                |

# ## 4. Job Description Parsing Summary

# *   **Must-Have Skills:** [List MH skills from JD]
# *   **Good-to-Have Skills:** [List GTH skills from JD]
# *   **Other Requirements:** [Certifications, Education, Experience Level]
# *   **Required Location Extracted:** [Extracted from JD text or "Not Found in Text"]
# *   **Position Budget Extracted:** [Extracted from JD text or "Not Found in Text"]


# ## 5. Candidate CV Examination Summary

# *   **Work Experience Summary:** [List companies/titles/durations]
# *   **Key Responsibilities Mentioned:** [Highlights]
# *   **Education Summary:** [Degrees, Institutions, Dates (using June assumption)]
# *   **Projects Mentioned:** [List project names, key tech/contributions]
# *   **Candidate Cost/Rate Extracted:** [Extracted Value or "Not Found in Text"]
# *   **Candidate Location Extracted:** [Extracted Value or "Not Found in Text"]

# ## 6. Gap Identification Table

# | Gap Period                                     | Start Date (YYYY-MM) | End Date (YYYY-MM) | Duration (Months) | Clarification Needed? |
# | :--------------------------------------------- | :------------------- | :----------------- | :---------------- | :-------------------- |
# | Graduation to First Job                        | [Grad Date]          | [First Job Start]  | [Calculated]      | [Yes/No]              |
# | Between Job [X] and Job [Y]                    | [Job X End]          | [Job Y Start]      | [Calculated]      | [Yes/No]              |
# | Last Job to Present ({present_date})         | [Last Job End]       | {present_date}     | [Calculated]      | [Yes/No]              |

# ## 7. Jumper Determination Table

# | Metric                     | Value                     |
# | :------------------------- | :------------------------ |
# | Total Relevant Experience (Years) | [From Timeline Table]     |
# | Total Number of Companies  | [Count from CV]           |
# | Ratio (Experience/Companies) | [Calculated Ratio or N/A] |
# | **Jumper Flag (< 1.5)**    | **[Yes / No / Cannot Be Determined]** |

# ## 8. Experience Table

# | Candidate Name | Project/Role Name & Company | Duration (Start-End) | Duration (Yy Mm) | Key Responsibilities        |
# | :------------- | :-------------------------- | :------------------- | :--------------- | :-------------------------- |
# | [Candidate Name Extracted/Placeholder] | [Role] at [Company]         | [YYYY-MM] - [YYYY-MM] | [Xy Ym]          | [List responsibilities...]  |
# | ...            | ...                         | ...                  | ...              | ...                         |

# ## 9. Skills Mapping Table

# | JD Skill (MH/GTH)      | Project/Experience Where Used | Duration (Yy Mm) | Roles/Responsibilities Related to Skill | How Skill Was Applied (Details from CV) |
# | :--------------------- | :---------------------------- | :--------------- | :-------------------------------------- | :-------------------------------------- |
# | [JD Skill 1]           | [Project/Company A]           | [Xy Ym]          | [Role description]                      | [Details of usage]                      |
# | ...                    | ...                           | ...              | ...                                     | ...                                     |


# --- END OF INTERNAL ANALYSIS REPORT ---

# ```json
# {{
#   "outcome_status": "Matched | Rejected | Clarification Needed",
#   "primary_reason": "Concise reason for the status (e.g., 'Strong skills match, no clarifications needed.', 'Missing critical skill: Java.', 'Requires clarification on employment gap and cost.')",
#   "clarifying_questions": [
#     "Question 1 based on CRITICAL INSTRUCTIONS...",
#     "Question 2 based on CRITICAL INSTRUCTIONS..."
#   ]
# }}

# Job Description Text:
# {jd_text}

# CV Text:
# {cv_text}

# Generate the full internal report text followed by the JSON block.
# """
# logger.debug("agent_definition.py - Reached end of file successfully.")
# print("DEBUG: agent_definition.py - Reached end of file successfully.") # DEBUG PRINT






# # agent/agent_definition.py
# import os
# import logging
# from dotenv import load_dotenv
# import google.generativeai as genai

# # --- Google AI Client Setup ---
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
# logger = logging.getLogger(__name__)
# gemini_model_object = None
# GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-1.5-flash-latest")
# try:
#     google_api_key = os.getenv("GOOGLE_API_KEY")
#     if not google_api_key: raise ValueError("GOOGLE_API_KEY missing.")
#     genai.configure(api_key=google_api_key)
#     gemini_model_object = genai.GenerativeModel(GOOGLE_MODEL_NAME)
#     logger.info(f"Gemini client configured for model: {GOOGLE_MODEL_NAME}")
# except Exception as e: logger.exception(f"Fatal Gemini config error: {e}"); raise ConnectionError(f"Could not configure Gemini client: {e}") from e
# # --- End Google AI Client Setup ---

# # --- PROMPT 1: Extract Total Relevant Experience Years ---
# EXTRACT_EXPERIENCE_PROMPT = """
# Analyze the following CV text STRICTLY and estimate the candidate's total years of relevant professional work experience based on the dates provided for their roles.
# - Consider only professional work roles, ignore internships or education periods unless explicitly stated as work experience.
# - Calculate the duration for each role based on start and end dates (Month/Year if available, otherwise Year).
# - Sum the durations of relevant roles.
# - If dates are unclear or missing for significant periods, making calculation impossible, state 'Unknown'.
# - Provide ONLY the estimated total number of years as a floating-point number (e.g., "7.5", "12.0", "3") or the word "Unknown". Do not add any other text, explanation, or formatting.

# CV Text:
# {cv_text}

# Estimated Total Relevant Experience Years (Number or "Unknown"):
# """

# # --- PROMPT 2: Check for Specific Education Years ---
# CHECK_EDUCATION_YEARS_PROMPT = """
# Review the Education section(s) within the following CV text STRICTLY.
# Determine if specific graduation years (e.g., a 4-digit year like 2020, 2023) are mentioned for the main degrees listed (e.g., Bachelor's, Master's).
# Respond with ONLY ONE WORD: "Yes", "No", or "Unclear".
# - "Yes" if at least one main degree clearly lists a specific graduation year.
# - "No" if degrees are listed but no specific graduation years are mentioned for any of them.
# - "Unclear" if the education section is missing, formatted confusingly, or makes it impossible to determine if years are present.
# CV Text:
# {cv_text}

# Are specific graduation years mentioned? (Yes/No/Unclear):
# """

# # --- *** MODIFIED PROMPT 3: Generate Detailed Backend Report (Using Lists) *** ---
# GENERATE_DETAILED_REPORT_PROMPT = """
# You are an expert C2C Candidate Screening Agent. Your task is to meticulously analyze the provided Job Description (JD) and Candidate CV, strictly following the steps below, using ONLY the information present in the texts. Assume the present date is {present_date_str}. Assume the candidate is available immediately.

# **Input Information:**
# * **JD Text:** Provided Below
# * **CV Text:** Provided Below
# * **Candidate Expected Cost/Rate:** {candidate_expected_payout_pm} per month
# * **Candidate Stated Location:** {candidate_current_location}
# * **Present Date:** {present_date_str}

# **Output Instructions:** Generate a comprehensive backend analysis report. Structure the output exactly as follows using Markdown formatting (headers, **lists**, bullet points). **DO NOT USE TABLES.**

# --- START OF BACKEND ANALYSIS REPORT ---

# **1. JD Summary (Parsed from JD Text)**
#     * **Role:** [Position Title extracted from JD Text or "Not Specified"]
#     * **Required Experience:** [Experience level/years extracted from JD Text or "Not Specified"]
#     * **Required Location(s):** [Location(s) extracted from JD Text or "Not Specified"]
#     * **Budget Indication:** [Budget text extracted from JD Text or "Not Specified"]
#     * **Must-Have (MH) Skills:** [List extracted from JD Text or "None Specified"]
#     * **Good-to-Have (GTH) Skills:** [List extracted from JD Text or "None Specified"]
#     * **Other Requirements:** [Certifications, specific qualifications etc. from JD Text or "None Specified"]

# **2. CV Summary (Parsed from CV Text)**
#     * **Candidate Name:** [Name extracted from CV Text or "Not Found"]
#     * **Contact Info (Email/Phone if found):** [Extracted details or "Not Found"]
#     * **Stated Location (from CV):** [Location extracted from CV Text or "Not Found"]
#     * **Stated Cost/Rate/Salary Expectation (from CV):** [Value extracted from CV Text or "Not Found in CV"]
#     * **Education:** [List degrees, institutions, *graduation years/dates* as found. Assume June if month is missing.]
#     * **Skills Listed:** [List of skills explicitly mentioned in CV Text]

# **3. Work Experience Timeline (From CV Text - Use List Format)**
#     * List each work experience chronologically using bullet points:
#         * **Role/Company:** [Role @ Company Name]
#             * **Start Date:** [Start Date]
#             * **End Date:** [End Date or "Present"]
#             * **Duration:** [Calculated Duration Years/Months]
#             * **Key Responsibilities/Projects Mentioned:** [Bulleted list of responsibilities/projects mentioned for this role]
#         * *(Repeat for each role)*

# **4. Gap Analysis (Calculated - Use List Format)**
#     * List each identified gap (>1 month) using bullet points:
#         * **Gap Period:** [e.g., "Between Graduation and First Role", "Between Role X and Role Y", "After Last Role"]
#             * **Start Date:** [Gap Start Date]
#             * **End Date:** [Gap End Date]
#             * **Duration:** [Calculated Duration Months]
#             * **Notes:** [Any relevant notes, e.g., "Clarification potentially needed"]
#         * *(Repeat for each gap)*
#     * *If no gaps > 1 month are found, state:* "No significant gaps (>1 month) found."

# **5. Jumper Determination (Calculated - Use List Format)**
#     * **Total Relevant Work Experience (Years):** [Sum of durations from Work Experience Timeline]
#     * **Number of Companies:** [Count distinct companies from Work Experience Timeline]
#     * **Experience/Company Ratio:** [Calculate Total Experience / Number of Companies, round to 1 decimal]
#     * **Jumper Flag:** [Output "Yes" if ratio < 1.5, "No" if ratio >= 1.5, "Cannot Be Determined" if data insufficient]

# **6. Skill Analysis (CV vs JD - Use List Format)**
#     * **Must-Have Skills Match:**
#         * For each MH skill from JD Summary:
#             * **Skill:** [MH Skill Name]
#             * **Match:** ['Yes' / 'No' / 'Partial']
#             * **Evidence/Comment:** [Brief evidence/comment from CV (e.g., project name, skill list mention)]
#         * *(Repeat for each MH skill)*
#     * **Good-to-Have Skills Match:**
#         * For each GTH skill from JD Summary:
#             * **Skill:** [GTH Skill Name]
#             * **Match:** ['Yes' / 'No' / 'Partial']
#             * **Evidence/Comment:** [Brief evidence/comment from CV]
#         * *(Repeat for each GTH skill)*

# **7. Detailed Skills Mapping (Optional - Use List Format)**
#     * *(Generate only if necessary based on previous analysis)*
#     * For each relevant JD Skill:
#         * **Skill (from JD):** [Skill Name]
#             * **Project/Experience (from CV):** [Project Name / Role @ Company]
#                 * **Duration:** [Duration if available]
#                 * **Roles/Responsibilities related to skill:** [Specific tasks related to the skill]
#                 * **Detailed Application:** [Description of how the skill was used in this context]
#             * *(Repeat for each relevant project/experience)*
#         * *(Repeat for each relevant JD skill)*

# **8. Overall Notes / Potential Red Flags**
#     * [Use bullet points to list any significant discrepancies (beyond initial checks), ambiguities, or potential concerns observed strictly from the text comparison.]

# --- END OF BACKEND ANALYSIS REPORT ---

# **Constraint Checklist (Internal - Do not output):**
# * Did I only use information from the provided JD and CV text? Yes/No
# * Did I follow the exact output structure and list-based formatting (NO TABLES)? Yes/No
# * Did I calculate durations and gaps accurately based on dates and the present date? Yes/No
# * Did I correctly apply the Jumper calculation (Ratio < 1.5)? Yes/No
# * Did I avoid making assumptions beyond the specified graduation month rule? Yes/No

# **JD Text:**
# {jd_text}


# **CV Text:**
# {cv_text}


# **Generate the backend analysis report now using LISTS, NOT TABLES:**
# """

# logger.debug("agent_definition.py - Reached end of file successfully.")




# agent/agent_definition.py
import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# --- Google AI Client Setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)
gemini_model_object = None
GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-1.5-flash-latest")
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key: raise ValueError("GOOGLE_API_KEY missing.")
    genai.configure(api_key=google_api_key)
    gemini_model_object = genai.GenerativeModel(GOOGLE_MODEL_NAME)
    logger.info(f"Gemini client configured for model: {GOOGLE_MODEL_NAME}")
except Exception as e: logger.exception(f"Fatal Gemini config error: {e}"); raise ConnectionError(f"Could not configure Gemini client: {e}") from e

# --- PROMPT 1: Extract Total Relevant Experience Years (No Change) ---
EXTRACT_EXPERIENCE_PROMPT = """
Analyze the following CV text STRICTLY and estimate the candidate's total years of relevant professional work experience based on the dates provided for their roles.
- Consider only professional work roles, ignore internships or education periods unless explicitly stated as work experience.
- Calculate the duration for each role based on start and end dates (Month/Year if available, otherwise Year).
- Sum the durations of relevant roles.
- If dates are unclear or missing for significant periods, making calculation impossible, state 'Unknown'.
- Provide ONLY the estimated total number of years as a floating-point number (e.g., "7.5", "12.0", "3") or the word "Unknown". Do not add any other text, explanation, or formatting.

CV Text:
{cv_text}

Estimated Total Relevant Experience Years (Number or "Unknown"):
"""

# --- PROMPT 2: Check for Specific Education Years (No Change) ---
CHECK_EDUCATION_YEARS_PROMPT = """
Review the Education section(s) within the following CV text STRICTLY.
Determine if specific graduation years (e.g., a 4-digit year like 2020, 2023) are mentioned for the main degrees listed (e.g., Bachelor's, Master's).
Respond with ONLY ONE WORD: "Yes", "No", or "Unclear".
- "Yes" if at least one main degree clearly lists a specific graduation year.
- "No" if degrees are listed but no specific graduation years are mentioned for any of them.
- "Unclear" if the education section is missing, formatted confusingly, or makes it impossible to determine if years are present.
CV Text:
{cv_text}

Are specific graduation years mentioned? (Yes/No/Unclear):
"""

# --- *** UPDATED PROMPT 3: Generate Detailed Backend Report (Reflects NEW Schema) *** ---
# Note: Renamed placeholders like {jd_text} to {requirement_text}
# Updated section headers and fields based on "Client Requirements" table
GENERATE_DETAILED_REPORT_PROMPT = """
You are an expert C2C Candidate Screening Agent. Your task is to meticulously analyze the provided Client Requirement and Candidate CV, strictly following the steps below, using ONLY the information present in the texts and provided inputs. Assume the present date is {present_date_str}.

**Input Information:**
* **Client Requirement Text:** Provided Below (Field: "JD in Text")
* **CV Text:** Provided Below
* **Candidate Name:** {candidate_name} (From Input)
* **Company Name:** {company_name} (From Input)
* **Candidate Expected Budget:** {candidate_expected_payout_pm} INR per month (From Input)
* **Candidate Applying for Location:** {candidate_applying_for_location} (From Input)
* **Candidate Current Location:** {candidate_current_location} (From Input)
* **Candidate Relocation Status:** {candidate_relocation_status} (From Input)
* **Present Date:** {present_date_str}

**Output Instructions:** Generate a comprehensive backend analysis report. Structure the output exactly as follows using Markdown formatting (headers, **lists**, bullet points). **DO NOT USE TABLES.**

--- START OF BACKEND ANALYSIS REPORT ---

**1. Requirement Summary (Parsed from Client Requirement Text)**
    * **Requirement Title:** [Value from 'Requirement' field or "Not Specified"]
    * **Required Experience (Min):** [Value from 'Minimum Experience' field or "Not Specified"]
    * **Required Location(s):** [Value from 'Location' field or "Not Specified"]
    * **Budget Indication:** [Value from 'Budget' field or "Not Specified"]
    * **Tech Skills Needed:** [Value from 'Tech Skills Needed' field or "None Specified"]
    * **Other Requirements/Notes:** [Combine 'Notes', 'Priority Level', 'Deadline' etc. if relevant, or "None Specified"]

**2. CV Summary (Parsed from CV Text)**
    * **Candidate Name (from CV):** [Name extracted from CV Text or "Not Found"]
    * **Contact Info (Email/Phone if found):** [Extracted details or "Not Found"]
    * **Stated Location (from CV):** [Location extracted from CV Text or "Not Found"]
    * **Stated Cost/Rate/Salary Expectation (from CV):** [Value extracted from CV Text or "Not Found in CV"]
    * **Education:** [List degrees, institutions, *graduation years/dates* as found. Assume June if month missing.]
    * **Skills Listed:** [List of skills explicitly mentioned in CV Text]

**3. Work Experience Timeline (From CV Text - Use List Format)**
    * List each work experience chronologically using bullet points:
        * **Role/Company:** [Role @ Company Name]
            * **Start Date:** [Start Date]
            * **End Date:** [End Date or "Present"]
            * **Duration:** [Calculated Duration Years/Months]
            * **Key Responsibilities/Projects Mentioned:** [Bulleted list of responsibilities/projects mentioned for this role]
        * *(Repeat for each role)*

**4. Gap Analysis (Calculated - Use List Format)**
    * List each identified gap (>1 month) using bullet points:
        * **Gap Period:** [e.g., "Between Graduation and First Role", "Between Role X and Role Y", "After Last Role"]
            * **Start Date:** [Gap Start Date]
            * **End Date:** [Gap End Date]
            * **Duration:** [Calculated Duration Months]
            * **Notes:** [Any relevant notes, e.g., "Clarification potentially needed"]
        * *(Repeat for each gap)*
    * *If no gaps > 1 month are found, state:* "No significant gaps (>1 month) found."

**5. Jumper Determination (Calculated - Use List Format)**
    * **Total Relevant Work Experience (Years):** [Sum of durations from Work Experience Timeline]
    * **Number of Companies:** [Count distinct companies from Work Experience Timeline]
    * **Experience/Company Ratio:** [Calculate Total Experience / Number of Companies, round to 1 decimal]
    * **Jumper Flag:** [Output "Yes" if ratio < 1.5, "No" if ratio >= 1.5, "Cannot Be Determined" if data insufficient]

**6. Skill Analysis (CV vs Requirement - Use List Format)**
    * **Tech Skills Needed Match:**
        * For each skill from Requirement Summary -> Tech Skills Needed:
            * **Skill:** [Skill Name]
            * **Match:** ['Yes' / 'No' / 'Partial']
            * **Evidence/Comment:** [Brief evidence/comment from CV (e.g., project name, skill list mention)]
        * *(Repeat for each skill)*

**7. Location Analysis**
    * **Requirement Locations:** [List locations from Requirement Summary]
    * **Candidate Target Location:** {candidate_applying_for_location}
    * **Candidate Current Location:** {candidate_current_location}
    * **Candidate Relocation Status:** {candidate_relocation_status}
    * **Location Match Assessment:** [Brief assessment - e.g., "Candidate targets valid location", "Candidate currently in required location", "Candidate targets valid location and will relocate", "Potential mismatch - targets valid location but relocation uncertain", "Target location not listed in requirement"]

**8. Overall Notes / Potential Red Flags**
    * [Use bullet points to list any significant discrepancies (budget mismatch if applicable, experience gaps, skill gaps), ambiguities, or potential concerns observed strictly from the text comparison and input details.]

--- END OF BACKEND ANALYSIS REPORT ---

**Constraint Checklist (Internal - Do not output):**
* Did I only use information from the provided Requirement text and CV text, and candidate input details? Yes/No
* Did I follow the exact output structure and list-based formatting (NO TABLES)? Yes/No
* Did I calculate durations and gaps accurately based on dates and the present date? Yes/No
* Did I correctly apply the Jumper calculation (Ratio < 1.5)? Yes/No
* Did I avoid making assumptions beyond the specified graduation month rule? Yes/No

**Client Requirement Text:**
{requirement_text}


**CV Text:**
{cv_text}


**Generate the backend analysis report now using LISTS, NOT TABLES:**
"""

logger.debug("agent_definition.py - Reached end of file successfully.")