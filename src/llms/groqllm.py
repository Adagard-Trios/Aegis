from langchain_groq import ChatGroq
import os

class GroqLLM:
    """
    Groq LLM wrapper.
    NOTE: load_dotenv() must be called BEFORE instantiating this class.
    Do NOT call load_dotenv() here — it triggers os.getcwd() which is a
    blocking call that raises BlockingError in langgraph dev's async context.
    """
    def __init__(self, specialty: str = None):
        self.specialty = specialty

    def get_llm(self):
        try:
            # Fallback to general API key if specialty-specific one isn't found
            env_var = "GROQ_API_KEY"
            if self.specialty:
                clean_spec = self.specialty.upper().replace(" EXPERT", "").replace(" ", "_").replace("/", "_")
                env_var = f"GROQ_API_KEY_{clean_spec}"
            
            groq_api_key = os.getenv(env_var) or os.getenv("GROQ_API_KEY")

            llm = ChatGroq(
                api_key=groq_api_key,
                model="openai/gpt-oss-120b", # Using a highly capable model for detailed interpretations
                streaming=False,
                temperature=0.3, # Increased slightly to encourage more detailed output
            )
            return llm
        except Exception as e:
            raise ValueError("Error Initializing Groq LLM: {}".format(e))