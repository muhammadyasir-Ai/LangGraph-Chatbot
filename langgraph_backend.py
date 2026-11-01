from langgraph.graph import StateGraph,START,END, add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY")
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]



def chat_node(state: ChatState) -> ChatState:

   #take user query from state and append to messages
    messages = state['messages']
   #send to llm and get response
    response = llm.invoke(messages)
    return {'messages': response}

checkpointer = MemorySaver()

graph = StateGraph(ChatState)

#add nodes to the graph
graph.add_node('chat_node',chat_node)

#add edges to the graph
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot = graph.compile(checkpointer=checkpointer)