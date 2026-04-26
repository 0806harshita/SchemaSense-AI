import streamlit as st
from main import get_ai_response   # ✅ updated import
from dotenv import load_dotenv
load_dotenv()
import pandas as pd

st.set_page_config(
    page_title="AI Data Analyst 2.0",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 SchemaSense AI")
st.markdown("Ask questions about your data in natural language.")

# User input
user_query = st.text_area(
    "💬 Enter your question:",
    placeholder="e.g., Which product sold the most?"
)

if st.button("Analyze"):

    if user_query.strip() == "":
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking with Mistral AI + RAG... 🤖"):

            response = get_ai_response(user_query)

        st.success("Analysis complete!")

        # 🔥 Show RAG Schema
        # st.subheader("📚 Relevant Schema ")
        # st.code(response["schema_used"])

        # 🔥 Show Generated SQL
        st.subheader("🧠 Generated SQL ")
        st.code(response["sql"], language="sql")

        # 🔥 Show Result
        st.subheader("📊 Query Result")
       # st.write(response["result"])
        data = response["result"]

            # If it's string → split lines
        if isinstance(data, str):
                rows = data.split("\n")
                df = pd.DataFrame(rows, columns=["Customer Name"])
        else:
                df = pd.DataFrame(data)

        st.dataframe(df)

        # 🔥 Show Explanation
        st.subheader("💡 Explanation")
        st.write(response["explanation"])


# UI Styling
st.markdown("""
    <style>
    textarea {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)