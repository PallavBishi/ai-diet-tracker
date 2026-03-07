import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="AI Macro Tracker", layout="centered")

st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth.")

# Initialize session storage
if "logs" not in st.session_state:
    st.session_state.logs = []

# Gemini configuration
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

# Input form
with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input(
        "What did you eat?",
        placeholder="Example: 2 eggs and 1 roti"
    )
    submit_button = st.form_submit_button("Add Meal")

# When user submits
if submit_button:

    if not food_input.strip():
        st.warning("Please enter some food.")
    else:
        try:
            with st.spinner("Calculating macros..."):

                prompt = f"""
Estimate calories, protein, carbs, and fat for this meal:

{food_input}
"""

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

                st.success("Meal added!")

        except Exception as e:
            st.error("AI calculation failed.")
            st.write(e)

# Display data
if st.session_state.logs:

    df = pd.DataFrame(st.session_state.logs)

    st.divider()

    st.subheader("Today's Progress")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Calories", int(df["Calories"].sum()))
    c2.metric("Protein", f"{int(df['Protein (g)'].sum())} g")
    c3.metric("Carbs", f"{int(df['Carbs (g)'].sum())} g")
    c4.metric("Fat", f"{int(df['Fat (g)'].sum())} g")

    st.subheader("Meal Log")

    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Clear Data"):
        st.session_state.logs = []
        st.rerun()
