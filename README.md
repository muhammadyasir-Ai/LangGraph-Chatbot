# LangGraph Chatbot

An AI-powered chatbot built using **LangGraph, Groq LLM, Streamlit, and Model Context Protocol (MCP)**. It supports web search, mathematical calculations, stock price lookup, PDF document question answering using Retrieval-Augmented Generation (RAG), persistent conversation history, and expense management through MCP servers.

## Features

### AI Chatbot
- Chat with an LLM powered by Groq.
- Manage conversations through an interactive Streamlit interface.
- Stream responses for a better chat experience.

### Built-in Tools
- **Web Search:** Search the web using DuckDuckGo.
- **Calculator:** Perform basic arithmetic operations.
- **Stock Price:** Retrieve stock quotes using the Alpha Vantage API.

### Retrieval-Augmented Generation (RAG)
- **PDF Upload:** Upload PDF documents directly through the Streamlit sidebar.
- **PDF Loading:** Extract document text using PyPDFLoader.
- **Text Splitting:** Divide documents into smaller chunks using RecursiveCharacterTextSplitter.
- **Embeddings:** Generate local text embeddings using Hugging Face Sentence Transformers.
- **Vector Database:** Store and search document embeddings using FAISS.
- **Semantic Search:** Retrieve relevant document content based on user queries.
- **LangGraph Integration:** Use document retrieval as a chatbot tool to answer questions from uploaded PDFs.

The chatbot uses retrieved document content to generate context-aware answers. One PDF can be processed at a time, and uploading a different PDF replaces the previous document.

### MCP Integration
- **MCP Client:** Connect the chatbot to external MCP servers using Python and FastMCP.
- **Local MCP Server:** Connect to a locally running Expense Tracker server.
- **Remote MCP Server:** Connect to a deployed Expense Tracker server hosted on Horizon.
- **Multiple Server Connections:** Connect to local and remote MCP servers through an example client.
- **16 MCP Tools:** Access expense management functionality through MCP.

### Expense Tracker

The chatbot can perform the following operations:

- Add, list, search, edit, and delete expenses.
- Manage expense categories.
- Manage budgets.
- Generate expense summaries.
- Generate monthly reports.

### Conversation Management
- **Conversation History:** Access previous conversations.
- **New Chat:** Start a fresh conversation.
- **Chat Titles:** Automatically generate titles from the first user message.
- **Persistent Storage:** Save conversation states using SQLite and LangGraph checkpointing.

### Monitoring
- **LangSmith Integration:** Trace and monitor chatbot runs.

## Tech Stack

- Python
- LangGraph
- LangChain
- Groq
- Streamlit
- FastMCP
- Model Context Protocol (MCP)
- Hugging Face Sentence Transformers
- FAISS
- PyPDF
- SQLite
- DuckDuckGo Search (`ddgs`)
- Alpha Vantage API
- LangSmith
- Requests

## Project Structure

```text
LangGraph-Chatbot/
│
├── langgraph_backend.py
├── streamlit_frontend.py
│
├── rag_pipeline.py
├── rag_store.py
│
├── mcp_tools.py
│
├── client_local.py
├── client_remote.py
├── client_both.py
│
├── requirements.txt
├── README.md
├── .gitignore
│
└── Images/
    ├── chatbot-conversation.png
    ├── chatbot-interface.png
    ├── chatbot-response.png
    └── chatbot-sidebar.png
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/muhammadyasir-Ai/LangGraph-Chatbot.git
```

### 2. Open the Project Folder

```bash
cd LangGraph-Chatbot
```

### 3. Create a Virtual Environment

```bash
python -m venv myenv
```

Activate it on Windows:

```powershell
myenv\Scripts\activate
```

### 4. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root directory.

Add your API keys and application settings:

```env
GROQ_API_KEY=your_groq_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=LangGraph Chatbot

MCP_MODE=local
```

**MCP Configuration:**

- `MCP_MODE=local` uses the local Expense Tracker MCP server and its local database.
- `MCP_MODE=remote` uses the deployed remote MCP server.
- Configure the remote server URL and authentication credentials according to the settings used by the MCP client.

Add your own API keys and server credentials. Never upload your `.env` file to GitHub.

The Groq API key is required. Alpha Vantage is needed for stock price lookup. LangSmith settings are optional.

### 6. Configure the MCP Server

The chatbot requires a compatible Expense Tracker MCP server to use expense management tools.

- Start the local MCP server when using local mode.
- Ensure the deployed remote server is available and its authentication is configured when using remote mode.

The local mode stores expense data in a local SQLite database. The remote server is currently intended for testing.

### 7. Run the Application

```bash
streamlit run streamlit_frontend.py
```

The application will open in your browser.

## Using RAG with PDF Documents

1. Start the Streamlit chatbot.
2. Open the sidebar.
3. Upload a PDF document.
4. Wait for the document processing to complete.
5. Ask questions related to the uploaded document.
6. The chatbot retrieves relevant document chunks through FAISS and uses them to generate an answer.

**RAG Processing Pipeline:**

```text
PDF Upload
    |
    v
PyPDFLoader
    |
    v
Text Extraction
    |
    v
RecursiveCharacterTextSplitter
    |
    v
Hugging Face Embeddings
    |
    v
FAISS Vector Store
    |
    v
Semantic Retrieval
    |
    v
LangGraph RAG Tool
    |
    v
Groq LLM Response
```

The embedding model is downloaded locally from Hugging Face. The first run may take additional time because the model needs to be downloaded.

## MCP Client Examples

The repository includes three example clients for understanding MCP connections:

| File | Purpose |
|---|---|
| `client_local.py` | Connect to the local MCP server |
| `client_remote.py` | Connect to the remote MCP server |
| `client_both.py` | Connect to both MCP servers |

The main MCP integration is handled through `mcp_tools.py`, which connects MCP tools with the LangGraph chatbot.

## How It Works

1. The user sends a message through the Streamlit interface.
2. LangGraph manages the chatbot workflow.
3. The Groq model processes the request.
4. The chatbot selects the appropriate tool when required:
   - Web Search
   - Calculator
   - Stock Price
   - PDF Document Retrieval (RAG)
   - Expense Tracker MCP Tools
5. For document-related questions, the RAG tool retrieves relevant content from the uploaded PDF.
6. For expense-related requests, the MCP client communicates with the configured MCP server.
7. The MCP server executes the requested expense operation.
8. LangGraph processes the tool response and generates the final answer.
9. SQLite checkpointing maintains conversation state.

## Expense Management Rules

- Expense amounts are handled in PKR.
- The chatbot uses the current date and month range for date-related queries.
- It asks for confirmation before deleting an expense.
- It asks before creating a new expense category.
- Tool errors are handled so the chatbot can explain problems without unnecessarily stopping other functionality.

## Local and Remote Modes

| Mode | Description | Data Storage |
|---|---|---|
| Local | Connects to the local Expense Tracker MCP server | Local SQLite database |
| Remote | Connects to the deployed Horizon MCP server | Currently temporary test storage |

**Recommendation:** Use local mode for normal usage because its expense database is persistent. Remote mode is currently intended for testing because its data may reset when the server restarts.

## Environment Variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Connects to the Groq LLM |
| `ALPHA_VANTAGE_API_KEY` | Retrieves stock prices |
| `LANGSMITH_TRACING` | Enables LangSmith tracing |
| `LANGSMITH_API_KEY` | LangSmith authentication |
| `LANGSMITH_PROJECT` | LangSmith project name |
| `MCP_MODE` | Selects local or remote MCP mode |

## Screenshots

### Chatbot Conversation

![Chatbot Conversation](Images/chatbot-conversation.png)

### Chatbot Interface

![Chatbot Interface](Images/chatbot-interface.png)

### Chatbot Response

![Chatbot Response](Images/chatbot-response.png)

### Sidebar

![Sidebar Screenshot](Images/chatbot-sidebar.png)

## Future Improvements

- Improve search result freshness and relevance.
- Enhance token-by-token response streaming.
- Improve conversation history display for MCP tool interactions.
- Add persistent storage for the remote Expense Tracker server.
- Improve document management and support for multiple uploaded documents.
- Further improve error handling and user experience.

## Author

**Muhammad Yasir**

- GitHub: [muhammadyasir-Ai](https://github.com/muhammadyasir-Ai)
- LinkedIn: [Muhammad Yasir](https://www.linkedin.com/in/muhammad-yasir-17211a423)

---

If you find this project useful, feel free to explore the repository.