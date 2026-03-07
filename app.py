import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AI Macro Tracker", layout="centered")

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. GOOGLE SHEETS AUTHENTICATION ---
# Scopes for Sheets and Drive
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    # Modern auth using service_account_info
    creds_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(credentials)
    
    # Ensure your Sheet name matches exactly
    sheet = client.open("AI_Diet_Database").sheet1
except Exception as e:
    st.error(f"Failed to connect to Google Sheets: {e}")
    st.info("Check if you shared the sheet with your service account email.")
    st.stop()

# --- 3. MODEL CONFIGURATION (MARCH 2026 STABLE) ---
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

# gemini-2.5-flash is currently the most stable workhorse
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash", 
    generation_config=generation_config
)

# --- 4. SESSION STATE ---
if "logs" not in st.session_state:
    st.session_state.logs = []

# --- 5. UI APP ---
st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("What did you eat?", placeholder="e.g. 1 avocado and 2 boiled eggs")
    submit_button = st.form_submit_button("Add Meal")

if submit_button:
    if not food_input.strip():
        st.warning("Please enter some food.")
    else:
        try:
            with st.spinner("Calculating macros..."):
                prompt = f"Estimate macros for: {food_input}"
                response = model.generate_content(prompt)
                
                # Parse JSON response
                data = json.loads(response.text)

                # Update Local Session
                new_log = {
                    "Time": datetime.now().strftime("%H:%M"),
                    "Food": food_input,
                    "Calories": data["calories"],
                    "Protein (g)": data["protein"],
                    "Carbs (g)": data["carbs"],
                    "Fat (g)": data["fat"]
                }
                st.session_state.logs.append(new_log)

                # Update Google Sheet
                sheet.append_row([
                    datetime.now().strftime("%Y-%m-%d"),
                    new_log["Time"],
                    food_input,
                    data["Calories"],
                    data["Protein (g)"],
                    data["Carbs (g)"],
                    data["Fat (g)"]
                ])
                st.success(f"Log updated: {food_input}")

        except Exception as e:
            st.error(f"Analysis Error: {e}")
            st.info("If this is a model error, try updating your 'google-generativeai' library version.")

# --- 6. DISPLAY DATA ---
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    st.divider()
    
    st.subheader("Daily Progress")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{int(df['Calories'].sum())}")
    c2.metric("Protein", f"{int(df['Protein (g)'].sum())}g")
    c3.metric("Carbs", f"{int(df['Carbs (g)'].sum())}g")
    c4.metric("Fat", f"{int(df['Fat (g)'].sum())}g")

    st.subheader("Meal Log")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Clear Session Data"):
        st.session_state.logs = []
        st.rerun()
