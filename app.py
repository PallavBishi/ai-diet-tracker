import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# Configure Gemini API
# Ensure GEMINI_API_KEY is set in your .streamlit/secrets.toml
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="AI Macro Tracker", layout="centered")

st.title("🥗 AI Macro Tracker")
st.caption("Consistent discomfort is equal to consistent growth. Track every bite.")

# Initialize session state for logs
if "logs" not in st.session_state:
    st.session_state.logs = []

# Configure the model with a JSON schema for 100% reliable parsing
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
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

# --- UI INPUT ---
with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("What did you eat?", placeholder="e.g. 2 scrambled eggs and a piece of whole wheat toast")
    submit_button = st.form_submit_button("Add Meal")

if submit_button:
    if not food_input.strip():
        st.warning("Please enter some food.")
    else:
        try:
            with st.spinner("Analyzing macros..."):
                prompt = f"Estimate the nutritional content for this meal: {food_input}. Provide estimates for calories, protein (g), carbs (g), and fat (g)."
                response = model.generate_content(prompt)
                
                # Because we used response_schema, response.text is guaranteed to be valid JSON
                data = json.loads(response.text)

                # Log the entry
                st.session_state.logs.append({
                    "Time": datetime.now().strftime("%H:%M"),
                    "Food": food_input,
                    "Calories": data["calories"],
                    "Protein (g)": data["protein"],
                    "Carbs (g)": data["carbs"],
                    "Fat (g)": data["fat"]
                })
                st.success(f"Added: {food_input}")

        except Exception as e:
            st.error("Gemini API Error. Check your API key or connection.")
            st.exception(e)

# --- DISPLAY DATA ---
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)

    st.divider()
    
    # Totals Section
    st.subheader("Today's Totals")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{int(df['Calories'].sum())}")
    c2.metric("Protein", f"{int(df['Protein (g)'].sum())}g")
    c3.metric("Carbs", f"{int(df['Carbs (g)'].sum())}g")
    c4.metric("Fat", f"{int(df['Fat (g)'].sum())}g")

    st.subheader("Meal Log")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Clear Log"):
        st.session_state.logs = []
        st.rerun()
