from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, inspect
import sqlite3
import re

from rag_schema import get_relevant_schema
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI

db_url = "sqlite:///amazon.db"


# ---------------------------
# Step 1: Extract Schema (optional fallback)
# ---------------------------
def extract_schema():
    engine = create_engine(db_url)
    inspector = inspect(engine)

    schema_text = ""

    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        col_names = [col['name'] for col in columns]
        schema_text += f"\nTable: {table}\nColumns: {', '.join(col_names)}\n"

    return schema_text


# ---------------------------
# Step 2: Generate SQL (Mistral + RAG)
# ---------------------------
def generate_sql(question):
    schema_context = get_relevant_schema(question)

    SYSTEM_PROMPT = """
        You are an expert SQL generator.

        Rules:
        - Use ONLY the given schema
        - Use EXACT column names (do NOT rename or guess like product_name)
        - products table has column: name (NOT product_name)
        - Sales data is in order_items.quantity
        - Always JOIN order_items with products using product_id
        - Generate correct SQLite SQL
        - Return ONLY raw SQL
        """

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "Relevant Schema:\n{schema}\n\nQuestion:\n{question}\n\nSQL Query:")
    ])

    model = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0
    )

    chain = prompt | model

    response = chain.invoke({
        "schema": schema_context,
        "question": question
    })

    # ✅ FIX AIMessage
    raw_output = response.content if hasattr(response, "content") else str(response)

    # ✅ Clean SQL
    clean_sql = (
        raw_output
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )

    # ✅ Extract only SQL
    match = re.search(r"(SELECT|WITH|INSERT|UPDATE|DELETE).*", clean_sql, re.IGNORECASE | re.DOTALL)
    if match:
        clean_sql = match.group(0).strip()

    return clean_sql, schema_context


# ---------------------------
# Step 3: Execute SQL with retry (Agentic)
# ---------------------------
def execute_query_with_retry(sql, schema, question):
    conn = sqlite3.connect("amazon.db")
    cursor = conn.cursor()

    try:
        result = cursor.execute(sql).fetchall()
        conn.close()
        return sql, result

    except Exception as e:
        print("❌ SQL Error:", e)

        FIX_PROMPT = """
        The following SQL query is incorrect.

        Error:
        {error}

        Fix the SQL query using the schema.

        Schema:
        {schema}

        Question:
        {question}

        Wrong SQL:
        {sql}

        Return ONLY corrected SQL.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", FIX_PROMPT),
        ])

        model = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0
        )

        chain = prompt | model

        fixed_response = chain.invoke({
            "error": str(e),
            "schema": schema,
            "question": question,
            "sql": sql
        })

        # ✅ FIX AIMessage
        raw_fixed = fixed_response.content if hasattr(fixed_response, "content") else str(fixed_response)

        # ✅ Clean SQL
        fixed_sql = (
            raw_fixed
            .replace("```sql", "")
            .replace("```", "")
            .strip()
        )

        try:
            result = cursor.execute(fixed_sql).fetchall()
            conn.close()
            return fixed_sql, result

        except Exception as e2:
            conn.close()
            return sql, f"❌ Failed even after retry: {e2}"


# ---------------------------
# Step 4: Explain Result
# ---------------------------
def explain_result(question, sql, result):
    EXPLAIN_PROMPT = """
    Explain the SQL query and result in simple words.

    Question:
    {question}

    SQL:
    {sql}

    Result:
    {result}
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAIN_PROMPT)
    ])

    model = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.3
    )

    chain = prompt | model

    response = chain.invoke({
        "question": question,
        "sql": sql,
        "result": result
    })

    # ✅ FIX AIMessage
    explanation = response.content if hasattr(response, "content") else str(response)

    return explanation

# ---------------------------
# Helper: Format result for explanation and display
# ---------------------------

def format_result(result):
    if not result:
        return "No data found"

    formatted = []

    for row in result:
        if len(row) == 1:
            formatted.append(str(row[0]))  # single column
        else:
            formatted.append(" | ".join(str(col) for col in row))  # multiple columns

    return "\n".join(formatted)


# ---------------------------
# Final function
# ---------------------------
def get_ai_response(question):

    sql, schema_context = generate_sql(question)

    final_sql, result = execute_query_with_retry(sql, schema_context, question)

    explanation = explain_result(question, final_sql, result)

    return {
        "sql": final_sql,
        "result": format_result(result),
        "explanation": explanation,
        "schema_used": schema_context
    }