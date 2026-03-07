import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai

st.title("AI Macro Tracker")

if "logs" not in st.session_state:
    st.session_state.logs = []

food_input = st.text_input("Enter what you ate")

if st.button("Add Meal"):

    prompt = f"""
    Estimate calories, protein, carbs, and fat for this meal:

    {food_input}

    Return JSON like:
    {{"calories":0,"protein":0,"carbs":0,"fat":0}}
    """

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)

    try:
        data = eval(response.text)

        st.session_state.logs.append({
            "time": datetime.now(),
            "food": food_input,
            "calories": data["calories"],
            "protein": data["protein"],
            "carbs": data["carbs"],
            "fat": data["fat"]
        })

    except:
        st.error("Could not parse response")

if st.session_state.logs:

    df = pd.DataFrame(st.session_state.logs)

    st.subheader("Today's totals")

    st.write("Calories:", df["calories"].sum())
    st.write("Protein:", df["protein"].sum())
    st.write("Carbs:", df["carbs"].sum())
    st.write("Fat:", df["fat"].sum())

    st.subheader("Meal Log")

    st.dataframe(df)
