import streamlit as st
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
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

        if "private_key" in gcp_info:
            gcp_info["private_key"] = gcp_info["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)

        client = gspread.authorize(creds)

        sheet = client.open_by_key(
            "1g6U3DHqqiCKbyo5DR0w4SCTYFqucAQst8bJRpqMpcc4"
        ).sheet1

        return sheet

    except Exception as e:

        st.error("🚨 Authentication Failed")
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
        return pd.DataFrame(columns=["Date","Time","Food","Calories","Protein","Carbs","Fat"])
    
    df = pd.DataFrame(data)
    # Ensure Date is a string for easy comparison
    df["Date"] = df["Date"].astype(str)
    return df

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
            "required": ["calories","protein","carbs","fat"],
        }
    }
)

# --------------------------------------------------
# 5. MEAL INPUT FORM
# --------------------------------------------------

with st.form("meal_form", clear_on_submit=True):

    food_input = st.text_input(
        "What did you eat?",
        placeholder="Example: 2 boiled eggs"
    )

    submit = st.form_submit_button("Add Meal")

# --------------------------------------------------
# 6. PROCESS ENTRY
# --------------------------------------------------

if submit and food_input:

    try:

        with st.spinner("Calculating macros..."):

            response = model.generate_content(
                f"Estimate calories, protein, carbs, fat: {food_input}"
            )

            data = json.loads(response.text)

            # Correct IST time
            now = datetime.now(ZoneInfo("Asia/Kolkata"))

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

            # refresh cache
            load_logs.clear()

            st.success("Meal logged!")

            st.rerun()

    except Exception as e:

        st.error(f"Error: {e}")

# --------------------------------------------------
# 7. DASHBOARD DISPLAY
# --------------------------------------------------

if not df.empty:
    st.divider()

    # Get current date in IST to match your logging timezone
    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

    # Convert macros safely
    for col in ["Calories","Protein","Carbs","Fat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- FILTER FOR TODAY ---
    df_today = df[df["Date"] == today_str]
    
    calories_total = df_today["Calories"].sum()
    protein_total = df_today["Protein"].sum()
    carbs_total = df_today["Carbs"].sum()
    fat_total = df_today["Fat"].sum()

    st.subheader(f"📅 Today's Progress ({today_str})")
    cols = st.columns(4)
    cols[0].metric("Calories", int(calories_total))
    cols[1].metric("Protein", f"{int(protein_total)}g")
    cols[2].metric("Carbs", f"{int(carbs_total)}g")
    cols[3].metric("Fat", f"{int(fat_total)}g")

    # --- HISTORICAL TOTALS ---
    st.divider()
    st.subheader("🕰️ Past Daily Totals")
    
    # Group by Date and sum the macros
    history_df = df.groupby("Date")[["Calories", "Protein", "Carbs", "Fat"]].sum().reset_index()
    # Sort to show newest dates first, excluding today if you only want 'past'
    history_df = history_df[history_df["Date"] != today_str].sort_values("Date", ascending=False)

    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No historical data available yet.")

    # --- DETAILED LOG ---
    st.divider()
    st.subheader("📋 Full Meal Log")
    st.dataframe(df.sort_values(["Date", "Time"], ascending=False), use_container_width=True, hide_index=True)

else:
    st.info("No meals logged yet.")
