from sqlalchemy import create_engine, inspect
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Create embeddings
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

DB_NAME = "schema_db"

def create_vector_db():
    engine = create_engine("sqlite:///amazon.db")
    inspector = inspect(engine)

    documents = []

    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        col_names = [col['name'] for col in columns]

    text = f"""
        Table: {table}
        Columns: {', '.join(col_names)}

        Description:
        - products: contains product details (column 'name' is product name)
        - order_items: contains quantity of products sold
        - orders: contains order info
        - customers: contains customer data
        """

    vectordb = Chroma.from_texts(documents, embedding, persist_directory=DB_NAME)
    vectordb.persist()

    print("✅ Schema embedded in ChromaDB!")


def get_relevant_schema(query):
    vectordb = Chroma(persist_directory=DB_NAME, embedding_function=embedding)

    docs = vectordb.similarity_search(query, k=2)

    context = "\n\n".join([doc.page_content for doc in docs])

    return context