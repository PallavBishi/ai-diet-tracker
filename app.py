import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="AI Macro Tracker", layout="centered")
st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

# --- 2. CONFIGURATION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def init_gsheet():
    try:
        # Load secrets
        gcp_info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
        
        # Clean the private key: convert literal \n to real newlines
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n").strip()

        # Authorize
        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
        client = gspread.authorize(creds)
        
        # Open by ID (The most stable method)
        return client.open_by_key("1g6U3DHqqiCKbyo5DR0w4SCTYFqucAQst8bJRpqMpcc4").sheet1
        
    except Exception as e:
        st.error("🚨 KEY ERROR: Your private_key in Secrets is likely incomplete or poorly copied.")
        st.exception(e)
        st.stop()

sheet = init_gsheet()

# --- 3. MODEL SETUP ---
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
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

# --- 4. UI & LOGIC ---
if "logs" not in st.session_state:
    st.session_state.logs = []

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("What did you eat?", placeholder="Example: 1 chicken wrap")
    submit = st.form_submit_button("Add Meal")

if submit and food_input:
    try:
        with st.spinner("Analyzing..."):
            response = model.generate_content(f"Estimate macros for: {food_input}")
            data = json.loads(response.text)
            
            now = datetime.now()
            row = [now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), food_input, 
                   data["calories"], data["protein"], data["carbs"], data["fat"]]
            
            sheet.append_row(row)
            
            st.session_state.logs.append({
                "Time": now.strftime("%H:%M"), "Food": food_input, 
                "Calories": data["calories"], "Protein": data["protein"]
            })
            st.success(f"Logged {food_input}!")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 5. DASHBOARD ---
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    st.metric("Total Calories", int(df["Calories"].sum()))
    st.dataframe(df, use_container_width=True)
