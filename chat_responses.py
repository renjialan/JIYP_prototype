try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3
import sys
sys.modules['sqlite3'] = sqlite3
sys.modules['pysqlite3'] = sqlite3 
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
import asyncio
from typing import AsyncGenerator
from langsmith import Client 
import streamlit as st
from retrieval import Retriever




class LMMentorBot:

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def __init__(self):

        print("Starting Jeeves Assistant -----------------------------------###")

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = st.secrets["langchain"]["api_key"]

        client = Client()

        print("Initializing RAG system")
        retriever = Retriever()

        # create retrievers for audit(dummy) and chat(rag)
        rag_retriver = retriever.retriver_sim
        dummy_retriever = retriever.retriever_dummy

        print("Initializing LLM")
        llm = ChatOpenAI(temperature=0.7, model= "gpt-4o-mini-2024-07-18", api_key=st.secrets["api_keys"]["OPENAI_API_KEY"], streaming=True)
        audit_summary_llm = ChatAnthropic(temperature=0.7, model="claude-3-5-sonnet-20240620", api_key=st.secrets["api_keys"]["ANTHROPIC_API_KEY"])
        dummy_llm = ChatOpenAI(temperature=0.7, model= "gpt-4o-mini-2024-07-18", api_key=st.secrets["api_keys"]["OPENAI_API_KEY"], max_tokens=1)

        # 
        with open("retriever_prompt.txt", "r") as f:
            retriever_prompt = f.read()

        with open("audit_summary_prompt.txt", "r") as f:
            audit_summary_prompt = f.read()

        with open("tara_prompt.txt", "r") as f:
            tara_prompt = f.read()
        
        retriever_template = ChatPromptTemplate.from_messages(
            [
                ("system", retriever_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        tara_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", tara_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        ).partial(
            dietary_preferences="",  # Will be filled from user context
            nutritional_goals="",    # Will be filled from user context
            user_specific_conditions=""  # Will be filled from user context
        )
        audit_summary_template = ChatPromptTemplate.from_template(audit_summary_prompt)

        history_aware_retriever = create_history_aware_retriever(
            llm, rag_retriver, retriever_template
        )

        audit_retrevier = create_history_aware_retriever(
            dummy_llm, dummy_retriever, retriever_template
        )

        print("Creating RAG chain")
        
        #create chain to insert documents for context (rag documents)
        tara_chain = create_stuff_documents_chain(llm, tara_prompt_template)

        # chain that retrieves documents and then passes them to the question_answer_chain
        self.audit_summary_chain = audit_summary_template | audit_summary_llm
        # audit_text_chain2 = (
        #     {"input": audit_summary_chain},
        # )

        rag_chain = create_retrieval_chain(history_aware_retriever, tara_chain)
        audit_text_chain = create_retrieval_chain(audit_retrevier, tara_chain)

        print("Creating chat history")
        self.store = {}

        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in self.store:
                print("Creating new chat history for session_id", session_id)
                self.store[session_id] = ChatMessageHistory()
            return self.store[session_id]


        self.conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

        self.conversational_chain_no_rag = RunnableWithMessageHistory(
            audit_text_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def upload_degree_audit(self, text: str):
        print("Uploading degree audit")
        audit_summary = self.audit_summary_chain.invoke({"audit": text})
        print("Finished summarizing audit")
        for chunk in self.conversational_chain_no_rag.stream(
            {"input": audit_summary.content},
                config={
                    "configurable": {"session_id": "abc123"}
                },  # constructs a key "abc123" in `store`.
            ):
            if 'answer' in chunk.keys():
                yield chunk.get("answer")
            else:
                continue
        print(self.store["abc123"])

    def chat(self, text: str) -> str:
        print("Chatting with Jeeves")
        response = self.conversational_rag_chain.invoke(
            {"input": text},
                config={
                    "configurable": {"session_id": "abc123"}
                },  # constructs a key "abc123" in `store`.
            )["answer"]
        print(self.store["abc123"])
        return response
    
    def chat_stream(self, text: str):
        print("Chatting with Jeeves")
        
        # Extract user context from session state
        user_context = st.session_state.get("user_context", "")
        
        # Parse the context into the required variables
        dietary_preferences = ""
        nutritional_goals = ""
        user_specific_conditions = ""
        
        if user_context:
            # Extract dietary preferences
            if "Dietary Restrictions:" in user_context:
                dietary_preferences = user_context.split("Dietary Restrictions:")[1].split("\n")[0].strip()
            
            # Extract nutritional goals
            if "Primary Goal:" in user_context:
                nutritional_goals = user_context.split("Primary Goal:")[1].split("\n")[0].strip()
            
            # Extract user specific conditions
            conditions = []
            if "Health Conditions:" in user_context:
                conditions.append(user_context.split("Health Conditions:")[1].split("\n")[0].strip())
            if "Allergies:" in user_context:
                conditions.append(user_context.split("Allergies:")[1].split("\n")[0].strip())
            user_specific_conditions = ", ".join(filter(None, conditions))
        
        for chunk in self.conversational_rag_chain.stream(
            {
                "input": text,
                "dietary_preferences": dietary_preferences,
                "nutritional_goals": nutritional_goals,
                "user_specific_conditions": user_specific_conditions
            },
            config={
                "configurable": {"session_id": "abc123"}
            },
        ):
            if 'answer' in chunk.keys():
                yield chunk.get("answer")
            else:
                continue
        print(self.store["abc123"])