from langchain_groq import ChatGroq
import os


# Maps a specialty (as used in EXPERT_TOOLS / EXPERT_SYSTEM_PROMPTS) to
# the env var name actually set in render.yaml + the HF Space dashboard.
# These names are irregular ("Pulmonology" → PULMONARY, "Obstetrics" →
# GYNECOLOGY, "Ocular" → OCULOMETRIC, "General Physician" → no _EXPERT
# suffix), so we use an explicit table instead of string transforms.
# Falls back to the shared GROQ_API_KEY when a specialty isn't listed.
_SPECIALTY_ENV_VAR = {
    "Cardiology Expert":  "CARDIOLOGY_EXPERT_GROQ_API_KEY",
    "Pulmonology Expert": "PULMONARY_EXPERT_GROQ_API_KEY",
    "Pulmonary Expert":   "PULMONARY_EXPERT_GROQ_API_KEY",
    "Neurology Expert":   "NEUROLOGY_EXPERT_GROQ_API_KEY",
    "Dermatology Expert": "DERMATOLOGY_EXPERT_GROQ_API_KEY",
    "Obstetrics Expert":  "GYNECOLOGY_EXPERT_GROQ_API_KEY",
    "Gynecology Expert":  "GYNECOLOGY_EXPERT_GROQ_API_KEY",
    "Ocular Expert":      "OCULOMETRIC_EXPERT_GROQ_API_KEY",
    "General Physician":  "GENERAL_PHYSICIAN_GROQ_API_KEY",
}


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
            env_var = _SPECIALTY_ENV_VAR.get((self.specialty or "").strip(), "GROQ_API_KEY")
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
