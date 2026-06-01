import os
import time
import asyncio
from typing import List, Dict, Any, Literal
from typing_extensions import TypedDict
from google import genai
from google.genai import types
from dotenv import load_dotenv

# LangGraph compilation layers
from langgraph.graph import StateGraph, END

# Cross-Engine Context Connections
from context_engine import UnifiedContextEngine

load_dotenv()

# =====================================================================
# 1. AGENTIC STATE VECTOR MATRIX DEFINITION
# =====================================================================
class RepoState(TypedDict):
    user_query: str
    query_type: Literal["code", "architecture", "documentation", "bug_hunt"]
    target_file: str
    repository_id: str
    repo_url: str
    code_snippets: List[Dict[str, Any]]
    graph_paths: List[str]
    analysis_findings: List[str]
    final_answer: str

# =====================================================================
# 2. CORE PLATFORM ORCHESTRATOR
# =====================================================================
class CodeIntelAgenticPlatform:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        self.fallback_model = "gemini-1.5-flash"
        self.context_engine = UnifiedContextEngine()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY is missing from your .env file!")
        
        self.client = genai.Client(api_key=api_key)
        self.graph = self._compile_agentic_workflow()

    def _call_llm_with_retry(self, contents, system_instruction=None, temperature=0.2, is_stream=False, max_retries=5, model_override=None):
        """
        Executes Gemini API requests with exponential backoff 
        to handle 429 RESOURCE_EXHAUSTED seamlessly.
        """
        config = types.GenerateContentConfig(temperature=temperature)
        if system_instruction:
            config.system_instruction = system_instruction
            
        target_model = model_override or self.model_name
        delay = 1.0  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                if is_stream:
                    return self.client.models.generate_content_stream(
                        model=target_model, contents=contents, config=config
                    )
                else:
                    return self.client.models.generate_content(
                        model=target_model, contents=contents, config=config
                    )
            except Exception as e:
                # Check if it's a rate limit error
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt == max_retries - 1:
                        raise e
                    print(f"⚠️ Rate limit hit (429). Retrying in {delay}s (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise e

    def _is_rate_limit_error(self, exc) -> bool:
        message = str(exc)
        return "429" in message or "RESOURCE_EXHAUSTED" in message

    def _local_query_classifier(self, user_query: str) -> str:
        query = str(user_query or "").lower()
        if any(term in query for term in ["bug", "issue", "error", "broken", "dead", "smell", "performance"]):
            return "bug_hunt"
        if any(term in query for term in ["architecture", "structure", "dependency", "dependencies", "flow", "graph"]):
            return "architecture"
        if any(term in query for term in ["document", "readme", "summary", "about", "setup", "explain"]):
            return "documentation"
        return "code"

    def _fallback_findings(self, state: RepoState, label: str) -> str:
        snippets = state.get("code_snippets", [])
        if not snippets:
            return (
                f"{label}: No scoped vector context was found for repository "
                f"'{state.get('repository_id') or 'Unknown'}'. Re-index this workspace, "
                "then ask again with the same repository id selected."
            )

        files = ", ".join(match.get("file_path", "Unknown") for match in snippets)
        return (
            f"{label}: Gemini quota is currently exhausted, so I am using retrieved "
            f"context only. Relevant scoped files for repository "
            f"'{state.get('repository_id') or 'Unknown'}': {files}."
        )

    def _quota_fallback_answer(self, state: RepoState) -> str:
        snippets = state.get("code_snippets", [])
        findings = "\n\n".join(state.get("analysis_findings", []))
        if not snippets:
            return (
                "Gemini quota is exhausted, and I could not find scoped repository "
                f"context for '{state.get('repository_id') or 'Unknown'}'. Please confirm "
                "the workspace was indexed successfully and that the active repo id matches it."
            )

        file_lines = []
        for match in snippets:
            snippet = (match.get("snippet") or "").strip().replace("\n", " ")
            if len(snippet) > 240:
                snippet = snippet[:240] + "..."
            file_lines.append(f"- {match.get('file_path')}: {snippet}")

        return (
            "Gemini quota is exhausted, so this is a local fallback answer based on "
            "the retrieved repository context only.\n\n"
            f"Repository: {state.get('repository_id') or 'Unknown'}\n"
            f"Question: {state.get('user_query')}\n\n"
            f"{findings}\n\n"
            "Most relevant files:\n"
            + "\n".join(file_lines)
        )

    # =====================================================================
    # 3. WORKER NODE IMPLEMENTATIONS (THE AGENT MATRIX)
    # =====================================================================
    
    def query_classifier(self, state: RepoState) -> Dict[str, Any]:
        """Agent 1: Evaluates user intent to map explicit system execution paths."""
        print("🧠 [Agent 1: Query Classifier] Evaluating structural intent...")
        prompt = f"""
        Analyze the following user question about a codebase and classify it into exactly ONE category:
        - 'code': For specific code implementation questions, variable lookups, or file specifics.
        - 'architecture': For high-level patterns, module links, dependencies, and file relationships.
        - 'documentation': For writing descriptions, setup steps, README layouts, or high-level summaries.
        - 'bug_hunt': For identifying issues, code smells, performance blockers, or dead files.

        User Question: "{state['user_query']}"
        
        Respond with ONLY the category word lowercase.
        """
        try:
            response = self._call_llm_with_retry(contents=prompt, temperature=0.0)
            q_type = response.text.strip().lower()
        except Exception as exc:
            if not self._is_rate_limit_error(exc):
                raise
            q_type = self._local_query_classifier(state["user_query"])
            print("Gemini quota exhausted during classification; using local classifier.")

        if q_type not in ["code", "architecture", "documentation", "bug_hunt"]:
            q_type = "code" # Safe default fallback
            
        print(f"↳ Identified Intent: Layer '{q_type.upper()}' Routing Activated.")
        return {"query_type": q_type}

    def retrieval_planner(self, state: RepoState) -> Dict[str, Any]:
        """Agent 2: Maps optimal retrieval strategy and pulls root vectors scoped by repo ID."""
        print(f"🗺️ [Agent 2: Retrieval Planner] Injecting assets for workspace: {state['repository_id']}...")
        
        # Safeguard parameters to match your lower layer architecture signatures cleanly
        matches = self.context_engine.semantic_code_search(
            query=state['user_query'], 
            repository_id=state['repository_id'] if state['repository_id'] else None, 
            limit=2
        )
        
        if not matches:
            return {"target_file": "", "code_snippets": [], "repo_url": "Unknown"}
            
        best_match = matches[0]
        meta = self.context_engine.relational_meta_lookup(
            best_match["file_path"],
            repository_id=state["repository_id"],
        )
        
        return {
            "target_file": best_match["file_path"],
            "code_snippets": matches,
            "repository_id": state['repository_id'], 
            "repo_url": meta["repo_url"] if meta else "Unknown"
        }

    def code_agent(self, state: RepoState) -> Dict[str, Any]:
        """Agent 3: Analyzes local structures, functional lines, and implementation paths."""
        print("💻 [Agent 3: Code Agent] Analyzing localized scopes & code targets...")
        snippets_str = "\n".join([f"File: {m['file_path']}\n```{m['snippet']}```" for m in state['code_snippets']])
        prompt = f"""
        You are a specialized Code Analysis Agent. Analyze these structural snippets regarding the query: "{state['user_query']}"
        Context:
        {snippets_str}
        Provide localized scoping insights or class interactions relative to the question.
        """
        try:
            res = self._call_llm_with_retry(contents=prompt)
            finding = f"Code Analysis:\n{res.text}"
        except Exception as exc:
            if not self._is_rate_limit_error(exc):
                raise
            finding = self._fallback_findings(state, "Code Analysis")

        return {"analysis_findings": state.get("analysis_findings", []) + [finding]}

    def graph_agent(self, state: RepoState) -> Dict[str, Any]:
        """Agent 4: Executes multi-hop relationship extraction out of Neo4j Graph Topology."""
        print("🕸️ [Agent 4: Graph Agent] Navigating multi-hop topological structures...")
        if not state["target_file"] or state["repository_id"] == "Unknown":
            return {"graph_paths": []}
            
        siblings = self.context_engine.structural_graph_traverse(state["repository_id"], state["target_file"])
        findings = f"Graph Topology Mapping: File '{state['target_file']}' is clustered inside the repository with structural sibling components: {', '.join(siblings)}"
        return {"graph_paths": siblings, "analysis_findings": state.get("analysis_findings", []) + [findings]}

    def documentation_agent(self, state: RepoState) -> Dict[str, Any]:
        """Agent 5: Generates architectural diagrams references, README details or files layout mappings."""
        print("📝 [Agent 5: Documentation Agent] Generating structural specs...")
        prompt = f"""
        You are an Architectural Documentation Agent. Summarize structural or conceptual onboarding elements for: "{state['user_query']}"
        Target Core Asset: {state['target_file']}
        Generate clear specifications mapped to the question intent.
        """
        try:
            res = self._call_llm_with_retry(contents=prompt)
            finding = f"Doc Specifications:\n{res.text}"
        except Exception as exc:
            if not self._is_rate_limit_error(exc):
                raise
            finding = self._fallback_findings(state, "Doc Specifications")

        return {"analysis_findings": state.get("analysis_findings", []) + [finding]}

    def bug_hunter_agent(self, state: RepoState) -> Dict[str, Any]:
        """Agent 6: Targets compilation syntax issues, dead imports, or performance leaks."""
        print("🪲 [Agent 6: Bug Hunter Agent] Auditing codebase for smells & architectural vulnerabilities...")
        snippets_str = "\n".join([f"File: {m['file_path']}\n```{m['snippet']}```" for m in state['code_snippets']])
        prompt = f"""
        You are an expert Static Analysis Bug Hunter. Inspect the code segments below for anti-patterns, circular dependencies, leaking scopes, or dead elements related to: "{state['user_query']}"
        
        {snippets_str}
        """
        try:
            res = self._call_llm_with_retry(contents=prompt)
            finding = f"Static Audit Report:\n{res.text}"
        except Exception as exc:
            if not self._is_rate_limit_error(exc):
                raise
            finding = self._fallback_findings(state, "Static Audit Report")

        return {"analysis_findings": state.get("analysis_findings", []) + [finding]}

    def answer_synthesizer(self, state: RepoState) -> Dict[str, Any]:
        """Node Final: Combines collective multi-agent findings into an engineering response."""
        print("🚀 [Synthesis Node] Aggregating multi-agent findings into final streaming context...")
        
        collected_findings = "\n\n".join(state.get("analysis_findings", []))
        primary_code = state["code_snippets"][0]["snippet"] if state["code_snippets"] else "No direct context mapped."
        
        system_instructions = (
            "You are CodeIntel Core Agentic, an enterprise-grade multi-agent repository analytics layer.\n"
            "Synthesize the provided analytical data and code segments into a comprehensive, high-fidelity engineering answer.\n"
            "Reference exact file entities, cross-cluster graph connections, and maintain absolute technical accuracy."
        )

        user_prompt = f"""
        Repository Target Base: {state.get('repo_url', 'Unknown')}
        Primary Target Component: {state.get('target_file', 'Unknown')}
        
        ----------------------------------------------------------------------
        CRITICAL CODE EXTRACT:
        {primary_code}
        ----------------------------------------------------------------------
        
        COLLECTED INTELLIGENCE FROM SPECIALIZED SUBSYSTEM AGENTS:
        {collected_findings}
        
        ----------------------------------------------------------------------
        USER QUESTION: {state['user_query']}
        
        Synthesize the final technical engineering response:
        """
        
        try:
            res = self._call_llm_with_retry(
                contents=user_prompt,
                system_instruction=system_instructions, 
                temperature=0.2
            )
            return {"final_answer": res.text}
        except Exception as e:
            if self._is_rate_limit_error(e):
                return {"final_answer": self._quota_fallback_answer(state)}

            print("Primary model issue during synthesis. Attempting fallback model...")
            try:
                res = self._call_llm_with_retry(
                    contents=user_prompt,
                    system_instruction=system_instructions,
                    temperature=0.2,
                    model_override=self.fallback_model
                )
                return {"final_answer": f"[Failover Active] {res.text}"}
            except Exception as fallback_exc:
                if self._is_rate_limit_error(fallback_exc):
                    return {"final_answer": self._quota_fallback_answer(state)}
                raise

    # =====================================================================
    # 4. CONDITIONAL ROUTING MANAGEMENT (THE GRAPH EDGES)
    # =====================================================================
    def _router_edge(self, state: RepoState) -> str:
        """Determines the specific routing track based on classified intent."""
        return state["query_type"]

    def _compile_agentic_workflow(self):
        """Constructs and compiles the asynchronous state processing graph topology."""
        workflow = StateGraph(RepoState)

        # Register Workflow Nodes
        workflow.add_node("query_classifier", self.query_classifier)
        workflow.add_node("retrieval_planner", self.retrieval_planner)
        workflow.add_node("code_agent", self.code_agent)
        workflow.add_node("graph_agent", self.graph_agent)
        workflow.add_node("documentation_agent", self.documentation_agent)
        workflow.add_node("bug_hunter_agent", self.bug_hunter_agent)
        workflow.add_node("answer_synthesizer", self.answer_synthesizer)

        # Set Workflow Entry Point
        workflow.set_entry_point("query_classifier")

        # Intent Vector Ingestion Transition
        workflow.add_edge("query_classifier", "retrieval_planner")

        # Set Conditional Branch Routes
        workflow.add_conditional_edges(
            "retrieval_planner",
            self._router_edge,
            {
                "code": "code_agent",
                "architecture": "graph_agent",
                "documentation": "documentation_agent",
                "bug_hunt": "bug_hunter_agent"
            }
        )

        # Map all analytical engines back to convergence synthesis step
        workflow.add_edge("code_agent", "answer_synthesizer")
        workflow.add_edge("graph_agent", "answer_synthesizer")
        workflow.add_edge("documentation_agent", "answer_synthesizer")
        workflow.add_edge("bug_hunter_agent", "answer_synthesizer")

        # Terminate pipeline
        workflow.add_edge("answer_synthesizer", END)

        return workflow.compile()

    def execute_query(self, user_question: str, repository_id: str = None) -> str:
        """Synchronous runner interface using compiled LangGraph workflow."""
        initial_state: RepoState = {
            "user_query": user_question,
            "query_type": "code",
            "target_file": "",
            "repository_id": repository_id or "",
            "repo_url": "",
            "code_snippets": [],
            "graph_paths": [],
            "analysis_findings": [],
            "final_answer": ""
        }
        
        final_output = self.graph.invoke(initial_state)
        return final_output.get("final_answer", "❌ Execution failed to synthesize final answer.")

    async def stream_agentic_tokens(self, user_query: str, repository_id: str = None):
        """
        Async generator to stream the multi-agent reasoning process 
        and the final LLM token output directly to the frontend.
        """
        yield "🧠 Initiating CodeIntel Agentic Matrix...\n\n"
        await asyncio.sleep(0.1)

        initial_state: RepoState = {
            "user_query": user_query,
            "query_type": "code",
            "target_file": "",
            "repository_id": repository_id or "",
            "repo_url": "",
            "code_snippets": [],
            "graph_paths": [],
            "analysis_findings": [],
            "final_answer": ""
        }

        # 1. Phase 1: Classification
        yield "🔍 Classifying intent and structural routes...\n"
        try:
            q_type_res = self.query_classifier(initial_state)
            initial_state.update(q_type_res)
            yield f"↳ Route established: Layer '{initial_state['query_type'].upper()}' activated.\n\n"
        except Exception as e:
            yield f"❌ Classification Layer Error: {str(e)}\n"
            return
        await asyncio.sleep(0.1)

        # 2. Phase 2: Retrieval
        yield "🗺️ Querying Vector & Graph databases for context...\n"
        try:
            retrieval_res = self.retrieval_planner(initial_state)
            initial_state.update(retrieval_res)
        except Exception as e:
            yield f"❌ Backend Agent Engine Exception: {str(e)}\n"
            return
        await asyncio.sleep(0.1)

        # 3. Phase 3: Specialized Agent Analysis
        q_type = initial_state["query_type"]
        yield f"⚙️ Engaging localized '{q_type}' expert agent...\n"
        
        try:
            if q_type == "code":
                agent_res = self.code_agent(initial_state)
            elif q_type == "architecture":
                agent_res = self.graph_agent(initial_state)
            elif q_type == "documentation":
                agent_res = self.documentation_agent(initial_state)
            else:
                agent_res = self.bug_hunter_agent(initial_state)
            
            initial_state.update(agent_res)
        except Exception as e:
            yield f"❌ Expert Node Execution Failure: {str(e)}\n"
            return
        await asyncio.sleep(0.1)

        yield "\n🚀 Multi-agent synthesis complete. Generating response:\n---\n\n"
        await asyncio.sleep(0.2)

        # 4. Phase 4: Final Streaming Synthesis
        collected_findings = "\n\n".join(initial_state.get("analysis_findings", []))
        primary_code = initial_state["code_snippets"][0]["snippet"] if initial_state.get("code_snippets") else "No direct context mapped."
        
        system_instructions = (
            "You are CodeIntel Core Agentic, an enterprise-grade multi-agent repository analytics layer.\n"
            "Synthesize the provided analytical data and code segments into a comprehensive, high-fidelity engineering answer.\n"
            "Reference exact file entities, cross-cluster graph connections, and maintain absolute technical accuracy."
        )

        user_prompt = f"""
        Repository Target Base: {initial_state.get('repo_url', 'Unknown')}
        Primary Target Component: {initial_state.get('target_file', 'Unknown')}
        
        ----------------------------------------------------------------------
        CRITICAL CODE EXTRACT:
        {primary_code}
        ----------------------------------------------------------------------
        
        COLLECTED INTELLIGENCE FROM SPECIALIZED SUBSYSTEM AGENTS:
        {collected_findings}
        
        ----------------------------------------------------------------------
        USER QUESTION: {initial_state['user_query']}
        
        Synthesize the final technical engineering response:
        """
        
        try:
            response_stream = self._call_llm_with_retry(
                contents=user_prompt,
                system_instruction=system_instructions,
                temperature=0.2,
                is_stream=True
            )
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            if self._is_rate_limit_error(e):
                yield "\n\n" + self._quota_fallback_answer(initial_state)
            else:
                yield f"\n\nSynthesis Error: {str(e)}"


# =====================================================================
# 5. BACKWARD COMPATIBILITY LAYERS
# =====================================================================
class CodeIntelAgent:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.orchestrator = CodeIntelAgenticPlatform(model_name=model_name)
        
    def answer_with_context(self, user_query: str, repository_id: str = None) -> str:
        """Forward tracking properties directly into execution engines safely."""
        return self.orchestrator.execute_query(user_query, repository_id=repository_id)

if __name__ == "__main__":
    platform = CodeIntelAgenticPlatform()
    test_question = "Find dead code or circular paths in our tracking layer components."
    print("🤖 Running CodeIntel Agentic Simulation Task...")
    result = platform.execute_query(test_question)
    print("\n💡 === FINAL AGENTIC LAYER RESPONSE ===")
    print(result)
