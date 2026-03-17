from langchain_groq import ChatGroq
import os

class GroqLLM:
    """
    Groq LLM wrapper.
    NOTE: load_dotenv() must be called BEFORE instantiating this class.
    Do NOT call load_dotenv() here — it triggers os.getcwd() which is a
    blocking call that raises BlockingError in langgraph dev's async context.
    """
    def get_llm(self):
        try:
            groq_api_key = os.getenv("GROQ_API_KEY")
            llm = ChatGroq(
                api_key=groq_api_key,
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                streaming=False,
                temperature=0.1,
            )
            return llm
        except Exception as e:
            raise ValueError("Error Initializing Groq LLM: {}".format(e))