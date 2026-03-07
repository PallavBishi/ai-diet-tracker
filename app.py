import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="AI Macro Tracker", layout="centered")

st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

scope = [
"https://spreadsheets.google.com/feeds",
"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
st.secrets["GCP_SERVICE_ACCOUNT"], scope
)

client = gspread.authorize(creds)
sheet = client.open("AI_Diet_Database").sheet1

# Initialize session state for logs
if "logs" not in st.session_state:
    st.session_state.logs = []

# --- UPDATED MODEL CONFIGURATION (2026 STABLE) ---
# Using gemini-2.5-flash which replaces the retired 1.5 series
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
    model_name="gemini-2.5-flash", 
    generation_config=generation_config
)

# --- UI INPUT ---
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
                
                data = json.loads(response.text)

                st.session_state.logs.append({
                    "Time": datetime.now().strftime("%H:%M"),
                    "Food": food_input,
                    "Calories": data["calories"],
                    "Protein (g)": data["protein"],
                    "Carbs (g)": data["carbs"],
                    "Fat (g)": data["fat"]
                })
                st.success(f"Log updated: {food_input}")
            sheet.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M"),
            food_input,
            data["calories"],
            data["protein"],
            data["carbs"],
            data["fat"]
            ])
        except Exception as e:
            st.error("Model Error: Gemini 1.5 is retired. Please ensure you are using gemini-2.5-flash.")
            st.info("If error persists, try 'gemini-3-flash-preview' for the latest experimental features.")

# --- DISPLAY DATA ---
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

    if st.button("Clear Data"):
        st.session_state.logs = []
        st.rerun()
