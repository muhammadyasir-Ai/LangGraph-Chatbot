# ***************************** IMPORTS *****************************

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ***************************** DOCUMENT LOADER *****************************

def load_pdf(file_path):

    """
    Load PDF document and extract its text.
    """

    loader = PyPDFLoader(file_path)

    documents = loader.load()

    return documents


# ***************************** TEXT SPLITTER *****************************

def split_documents(documents):

    """
    Split documents into smaller text chunks.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = text_splitter.split_documents(documents)

    return chunks


# ***************************** EMBEDDING MODEL *****************************

def get_embeddings():

    """
    Initialize Hugging Face embedding model.
    """

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return embeddings



# ***************************** VECTOR STORE *****************************

def create_vector_store(chunks):

    """
    Create FAISS vector store from document chunks.
    """

    embeddings = get_embeddings()

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings
    )

    return vector_store


# ***************************** PROCESS PDF *****************************

def process_pdf(file_path):

    """
    Complete PDF processing pipeline.
    """

    # Load PDF
    documents = load_pdf(file_path)

    # Split documents into chunks
    chunks = split_documents(documents)

    # Create FAISS vector store
    vector_store = create_vector_store(chunks)

    return vector_store


# ***************************** DOCUMENT RETRIEVAL *****************************

def retrieve_documents(vector_store, query):

    """
    Retrieve relevant document chunks based on user query.
    """

    retriever = vector_store.as_retriever(
        search_kwargs={"k": 4}
    )

    relevant_documents = retriever.invoke(query)

    return relevant_documents