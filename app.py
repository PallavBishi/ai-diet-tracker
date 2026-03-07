import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --------------------------------------------------
# 1. PAGE CONFIG
# --------------------------------------------------

st.set_page_config(page_title="AI Macro Tracker", layout="centered")

st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

# --------------------------------------------------
# 2. API + GOOGLE SHEETS SETUP
# --------------------------------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_resource
def init_gsheet():
    try:
        gcp_info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])

        # Fix private key formatting
        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)

        client = gspread.authorize(creds)

        sheet = client.open_by_key(
            "1g6U3DHqqiCKbyo5DR0w4SCTYFqucAQst8bJRpqMpcc4"
        ).sheet1

        return sheet

    except Exception as e:
        st.error("🚨 Google Sheets Authentication Failed")
        st.exception(e)
        st.stop()


sheet = init_gsheet()

# --------------------------------------------------
# 3. LOAD DATA FROM GOOGLE SHEETS
# --------------------------------------------------

@st.cache_data(ttl=60)
def load_logs():
    data = sheet.get_all_records()

    if not data:
        return pd.DataFrame(
            columns=["Date", "Time", "Food", "Calories", "Protein", "Carbs", "Fat"]
        )

    return pd.DataFrame(data)


df = load_logs()

# --------------------------------------------------
# 4. GEMINI AI MODEL
# --------------------------------------------------

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
        },
    },
)

# --------------------------------------------------
# 5. MEAL INPUT FORM
# --------------------------------------------------

with st.form("meal_form", clear_on_submit=True):

    food_input = st.text_input(
        "What did you eat?",
        placeholder="Example: 2 boiled eggs and 1 slice bread"
    )

    submit = st.form_submit_button("Add Meal")

# --------------------------------------------------
# 6. PROCESS MEAL ENTRY
# --------------------------------------------------

if submit and food_input:

    try:

        with st.spinner("Calculating macros with AI..."):

            response = model.generate_content(
                f"Estimate calories, protein, carbs, fat: {food_input}"
            )

            data = json.loads(response.text)

            now = datetime.now()

            row = [
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M"),
                food_input,
                data["calories"],
                data["protein"],
                data["carbs"],
                data["fat"],
            ]

            sheet.append_row(row)

            # Clear cache so new data appears immediately
            load_logs.clear()

            st.success("Meal logged successfully!")

            st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

# --------------------------------------------------
# 7. DISPLAY DASHBOARD
# --------------------------------------------------

if not df.empty:

    st.divider()

    # Convert columns to numeric
    df["Calories"] = pd.to_numeric(df["Calories"])
    df["Protein"] = pd.to_numeric(df["Protein"])
    df["Carbs"] = pd.to_numeric(df["Carbs"])
    df["Fat"] = pd.to_numeric(df["Fat"])

    # Daily totals
    calories_total = df["Calories"].sum()
    protein_total = df["Protein"].sum()
    carbs_total = df["Carbs"].sum()
    fat_total = df["Fat"].sum()

    cols = st.columns(4)

    cols[0].metric("Calories Today", int(calories_total))
    cols[1].metric("Protein Today", f"{int(protein_total)} g")
    cols[2].metric("Carbs Today", f"{int(carbs_total)} g")
    cols[3].metric("Fat Today", f"{int(fat_total)} g")

    st.divider()

    st.subheader("📋 Meal Log")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No meals logged yet.")
