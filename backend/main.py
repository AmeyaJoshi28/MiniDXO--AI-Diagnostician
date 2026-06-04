from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents import ResearcherAgent, OrchestratorAgent, InterviewerAgent

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agents
res = ResearcherAgent()
orch = OrchestratorAgent()
inter = InterviewerAgent()

class ChatInput(BaseModel):
    message: str

@app.post("/reset")
async def reset_session():
    """Resets the agent states for a new patient."""
    global orch, res, inter
    res = ResearcherAgent()
    orch = OrchestratorAgent()
    inter = InterviewerAgent()
    return {"status": "Agent memory cleared"}

@app.post("/chat")
async def handle_chat(data: ChatInput):
    # 1. Fetch relevant medical data based on input
    evidence = res.fetch_evidence(data.message)
    
    # 2. Update the confidence bars (beliefs)
    status = orch.update_beliefs(evidence, data.message)
    
    # 3. Get next question or final diagnosis
    reply, why, force_finish = inter.generate_question(orch.beliefs, res.db, orch.history, orch.asked_questions)

    if status == "DIAGNOSE" or force_finish:
        top_name = max(orch.beliefs, key=orch.beliefs.get)
        disease_entry = next((item for item in res.db.values() if item["name"] == top_name), None)

        # Extract NIH source text if available, else use a fallback
        nih_summary = disease_entry["text"] if disease_entry else "No additional reference data available."
        nih_source  = disease_entry["source"] if disease_entry else "Unknown"

        # PROMPT: Full clinical summary with NIH context + remedies
        prompt = (
            f"SYSTEM: You are a Medical Diagnostic AI providing a clinical summary.\n\n"
            f"PATIENT SYMPTOM HISTORY: {orch.history}\n\n"
            f"LIKELY CONDITION: {top_name}\n\n"
            f"NIH REFERENCE SUMMARY: {nih_summary}\n"
            f"SOURCE: {nih_source}\n\n"
            f"TASK: Using the patient history and NIH reference above, produce a clinical summary in HTML.\n\n"
            f"STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS (use these exact HTML tags):\n"
            f"<h3>Diagnostic Summary: [Condition Name]</h3>\n"
            f"<p><strong>Condition:</strong> Briefly describe what {top_name} is.</p>\n"
            f"<p><strong>Why your symptoms match:</strong> Explain which reported symptoms align with {top_name}, referencing the NIH summary.</p>\n"
            f"<p><strong>Confidence:</strong> State the AI confidence level and what it means.</p>\n"
            f"<p><strong>Common Medical Treatments:</strong> List standard medical treatments a doctor may prescribe.</p>\n"
            f"<p><strong>Home Remedies & Lifestyle Tips:</strong> List safe, practical home remedies and lifestyle changes that can help manage symptoms.</p>\n"
            f"<p><strong>When to See a Doctor:</strong> Describe warning signs that require immediate medical attention.</p>\n"
            f"<p><strong>Source:</strong> {nih_source}</p>\n"
            f"<p><em>Disclaimer: This is an AI-generated preliminary assessment, not a professional medical diagnosis. Please consult a qualified doctor before taking any action.</em></p>\n\n"
            f"RULES:\n"
            f"- Output ONLY the HTML above. No markdown, no asterisks, no backticks.\n"
            f"- Keep each section concise — 2 to 4 sentences or bullet points using <ul><li> tags.\n"
            f"- Home remedies must be safe, general, and non-prescriptive (e.g. rest, hydration, warm compress).\n"
            f"- Do NOT invent symptoms the patient did not mention."
        )

        diagnosis_text = inter.ask_gemini(prompt)
        reply = diagnosis_text 
        current_reasoning = f"Confidence threshold met for {top_name}."
    else:
        current_reasoning = f"{orch.monologue}<br/><strong>Step:</strong> {why}"

    return {
        "reply": reply, 
        "reasoning": current_reasoning, 
        "confidence": orch.beliefs
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
