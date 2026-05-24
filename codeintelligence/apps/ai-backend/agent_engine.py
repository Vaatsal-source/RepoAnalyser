import os
from google import genai
from google.genai import types
from context_engine import UnifiedContextEngine
from dotenv import load_dotenv

load_dotenv()

class CodeIntelAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        self.fallback_model = "gemini-1.5-flash"  # Highly resilient fallback endpoint
        self.context_engine = UnifiedContextEngine()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY is missing from your .env file!")
        
        self.client = genai.Client(api_key=api_key)

    def answer_with_context(self, user_question: str):
        # 1. Pull context parameters across Neon, Qdrant, and Neo4j
        context_data = self.context_engine.construct_ai_context(user_question)
        
        if not context_data:
            return "I couldn't find any relevant code segments in the repository to answer your question."

        target_file = context_data["target_file"]
        code_snippet = context_data["raw_content_snippet"]
        repo_url = context_data["repository"]["clone_url"]
        
        # 2. Setup structural instructions
        system_instructions = (
            "You are CodeIntel, an expert AI software engineering assistant.\n"
            "You are given specific code file context from a user's repository to answer their question.\n"
            "Be precise, reference exact file variables/structures, and write clean code examples if needed."
        )

        user_prompt = f"""
        Context from repository ({repo_url}):
        ---------------------------------------------
        Primary Target File: {target_file}
        
        Code Snippet Contents:
        \"\"\"
        {code_snippet}
        \"\"\"
        ---------------------------------------------
        
        User Question: {user_question}
        
        Provide a concise engineering answer based on the code context above.
        """

        # 3. Fire content synthesis with automated structural retry logic
        try:
            print(f"🚀 Context gathered. Routing execution to Primary Gemini Cloud '{self.model_name}'...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                    temperature=0.2
                )
            )
            return response.text

        except Exception as primary_error:
            # Catching 503 or concurrency traffic blocks
            if "503" in str(primary_error) or "UNAVAILABLE" in str(primary_error):
                print(f"⚠️ Primary tier '{self.model_name}' overloaded. Initiating failover to '{self.fallback_model}'...")
                try:
                    response = self.client.models.generate_content(
                        model=self.fallback_model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instructions,
                            temperature=0.2
                        )
                    )
                    return f"⚠️ [Failover Active] {response.text}"
                except Exception as fallback_error:
                    return f"❌ Both primary and secondary Gemini tiers are currently saturated: {str(fallback_error)}"
            
            return f"❌ Failed to communicate with Gemini Cloud Model: {str(primary_error)}"

if __name__ == "__main__":
    agent = CodeIntelAgent()
    question = "What are the specific margin and text properties set for the octocat element?"
    answer = agent.answer_with_context(question)
    print("\n💡 === AI AGENT ANSWER ===")
    print(answer)