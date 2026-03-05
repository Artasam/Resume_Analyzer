from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

# ---------- LLM setup ----------

USE_LLM = False
MODEL = None

try:
    LLM = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.3-70B-Instruct",
        task="text-generation"
    )
    MODEL = ChatHuggingFace(llm=LLM)
    USE_LLM = True
    print("✅ Using HuggingFace LLaMA-3.3-70B-Instruct for resume parsing")
except Exception as e:
    print("⚠️ LLM not available, falling back to rule-based extraction.")


def llm_available() -> bool:
    """Check if LLM quota/availability is active."""
    return USE_LLM and MODEL is not None