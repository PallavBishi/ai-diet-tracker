import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AI Macro Tracker", layout="centered")
st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

# Scopes and API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def init_gsheet():
    try:
        # Load and fix secrets
        gcp_info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
        
        # This is the critical line: it converts the string back to a valid PEM format
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
        client = gspread.authorize(creds)
        
        # Ensure the Sheet ID is correct
        return client.open_by_key("1g6U3DHqqiCKbyo5DR0w4SCTYFqucAQst8bJRpqMpcc4").sheet1
    except Exception as e:
        st.error("🚨 Authentication Failed. Ensure the private_key is pasted exactly as shown in the JSON file.")
        st.exception(e)
        st.stop()

sheet = init_gsheet()

# --- 2. AI MODEL SETUP ---
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
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
        }
    }
)

# --- 3. UI & LOGIC ---
if "logs" not in st.session_state:
    st.session_state.logs = []

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("What did you eat?", placeholder="Example: 2 boiled eggs")
    submit = st.form_submit_button("Add Meal")

if submit and food_input:
    try:
        with st.spinner("Calculating..."):
            response = model.generate_content(f"Estimate calories, protein, carbs, fat: {food_input}")
            data = json.loads(response.text)
            
            now = datetime.now()
            row = [now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), food_input, 
                   data["calories"], data["protein"], data["carbs"], data["fat"]]
            
            sheet.append_row(row)
            
            st.session_state.logs.append({
                "Time": now.strftime("%H:%M"),
                "Food": food_input,
                "Calories": data["calories"],
                "Protein": data["protein"],
                "Carbs": data["carbs"],
                "Fat": data["fat"]
            })
            st.success("Meal logged!")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 4. DISPLAY ---
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    st.divider()
    cols = st.columns(4)

    cols[0].metric("Calories Today", int(df["Calories"].sum()))
    cols[1].metric("Protein Today", f"{int(df['Protein'].sum())} g")
    cols[2].metric("Carbs Today", f"{int(df['Carbs'].sum())} g")
    cols[3].metric("Fat Today", f"{int(df['Fat'].sum())} g")
