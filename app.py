import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. PAGE SETUP
st.set_page_config(page_title="AI Macro Tracker", layout="centered")
st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

# 2. AUTHENTICATION & CONFIGURATION
# Configure Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Fix GCP Private Key formatting for oauth2client
# --- DEBUGGING CONNECTION BLOCK ---
try:
    # 1. Load and Clean
    gcp_info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
    if "private_key" in gcp_info:
        # This handles both real newlines and escaped string newlines
        gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")
    
    # 2. Authenticate
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
    client = gspread.authorize(creds)
    
    # 3. List all sheets the bot can actually see (to verify sharing)
    visible_sheets = [s.title for s in client.openall()]
    st.write(f"✅ Bot connected! Sheets found: {visible_sheets}")
    
    # 4. Open the specific sheet
    sheet = client.open("AI_DIET_DATABASE").sheet1

except Exception as e:
    st.error("🚨 CONNECTION FAILED")
    st.exception(e)  # This will show the full Traceback error
    st.stop()

@st.cache_resource
def init_gsheet():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
    client = gspread.authorize(creds)
    # Ensure this name matches your Google Sheet exactly
    return client.open_by_key("1g6U3DHqqiCKbyo5DR0w4SCTYFqucAQst8bJRpqMpcc4")

try:
    sheet = init_gsheet()
except Exception as e:
    st.error("Google Sheets Connection Error. Check if you shared the sheet with the client_email.")
    st.stop()

# 3. AI MODEL SETUP
generation_config = {
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "calories": {"type": "number"},
            "protein": {"type": "number"},
            "carbs": {"type": "number"},
            "fat": {"type": "number"},
        },
        "required": ["calories", "protein", "carbs", "fat"],
    },
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Current stable version
    generation_config=generation_config
)

# 4. SESSION STATE
if "logs" not in st.session_state:
    st.session_state.logs = []

# 5. USER INPUT FORM
with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input(
        "What did you eat?",
        placeholder="Example: 2 eggs and 1 roti"
    )
    submit_button = st.form_submit_button("Add Meal")

# 6. LOGIC: WHEN USER SUBMITS
if submit_button:
    if not food_input.strip():
        st.warning("Please enter some food.")
    else:
        try:
            with st.spinner("Analyzing nutrition..."):
                prompt = f"Estimate calories, protein, carbs, and fat for this meal: {food_input}"
                response = model.generate_content(prompt)
                data = json.loads(response.text)

                # Prepare row for Google Sheets
                now = datetime.now()
                row = [
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M"),
                    food_input,
                    data["calories"],
                    data["protein"],
                    data["carbs"],
                    data["fat"]
                ]
                
                sheet.append_row(row)

                # Add to local UI state
                st.session_state.logs.append({
                    "Time": now.strftime("%H:%M"),
                    "Food": food_input,
                    "Calories": data["calories"],
                    "Protein (g)": data["protein"],
                    "Carbs (g)": data["carbs"],
                    "Fat (g)": data["fat"]
                })
                st.success(f"Added: {food_input}!")

        except Exception as e:
            st.error(f"Error: {e}")

# 7. DASHBOARD DISPLAY
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    
    st.divider()
    st.subheader("Today's Progress")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{int(df['Calories'].sum())}")
    c2.metric("Protein", f"{int(df['Protein (g)'].sum())}g")
    c3.metric("Carbs", f"{int(df['Carbs (g)'].sum())}g")
    c4.metric("Fat", f"{int(df['Fat (g)'].sum())}g")

    st.subheader("Meal Log")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Clear Log View"):
        st.session_state.logs = []
        st.rerun()
