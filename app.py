import streamlit as st
import json
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("AI Macro Tracker")

# Initialize session state
if "logs" not in st.session_state:
    st.session_state.logs = []

# Input field
food_input = st.text_input("Enter what you ate")

# Add meal button
if st.button("Add Meal"):

    if food_input.strip() == "":
        st.warning("Please enter some food.")
    else:

        prompt = f"""
Estimate calories, protein, carbs, and fat for this meal.

Meal: {food_input}

Return ONLY JSON in this format:

{{
"calories": number,
"protein": number,
"carbs": number,
"fat": number
}}
"""

        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
            response = model.generate_content(prompt)

            # Clean Gemini response
            text = response.text.strip()

            if text.startswith("```"):
                text = text.replace("```json", "").replace("```", "").strip()

            data = json.loads(text)

            st.session_state.logs.append({
                "time": datetime.now(),
                "food": food_input,
                "calories": data["calories"],
                "protein": data["protein"],
                "carbs": data["carbs"],
                "fat": data["fat"]
            })

            st.success("Meal added!")

        except Exception as e:
            st.error("Could not parse Gemini response.")
            st.write(e)

# Display logs
if st.session_state.logs:

    df = pd.DataFrame(st.session_state.logs)

    st.subheader("Today's Totals")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Calories", int(df["calories"].sum()))
    col2.metric("Protein (g)", int(df["protein"].sum()))
    col3.metric("Carbs (g)", int(df["carbs"].sum()))
    col4.metric("Fat (g)", int(df["fat"].sum()))

    st.subheader("Meal Log")

    st.dataframe(df, use_container_width=True)
