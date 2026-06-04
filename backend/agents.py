import json
import re
import google.generativeai as genai


API_KEY = "YOUR_GEMINI_KEY"
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-2.5-flash-lite')

class ResearcherAgent:
    def __init__(self):
        try:
            with open("medical_data.json", "r", encoding="utf-8") as f:
                self.db = json.load(f)
        except Exception:
            self.db = {}

    def fetch_evidence(self, user_input):
        user_words = set(re.findall(r'\w+', user_input.lower()))
        matches = []
        # Stop words to prevent 'Body Weight' from hijacking the search
        stop_words = {"i", "have", "a", "the", "and", "is", "it", "yes", "no", "not", "body", "weight"}
        filtered_input = user_words - stop_words

        for key, data in self.db.items():
            keywords = [k.lower() for k in data.get("keywords", [])]
            matched_keywords = [word for word in filtered_input if any(word in kw for kw in keywords)]
            if matched_keywords:
                # Score multiplier: specific symptoms weigh more than general ones
                score = len(matched_keywords) * 2.5
                matches.append({"id": key, "name": data["name"], "text": data["text"], "source": data["source"], "score": score})
        return sorted(matches, key=lambda x: x["score"], reverse=True)[:3]

class OrchestratorAgent:
    def __init__(self):
        self.beliefs = {}
        self.monologue = ""
        self.history = []
        self.asked_questions = []

    def update_beliefs(self, evidence, user_input):
        clean_input = user_input.lower().strip()
        self.history.append(clean_input)

        for item in evidence:
            current = self.beliefs.get(item["name"], 0.0)
            
            # Logic: If user confirms a specific symptom
            if any(confirm in clean_input for confirm in ["yes", "yeah", "i have", "stiff", "true"]):
                self.beliefs[item["name"]] = min(current + 0.35, 0.98)
            # Logic: If user denies
            elif any(neg in clean_input for neg in ["no", "not", "never", "don't"]):
                self.beliefs[item["name"]] = max(current - 0.45, 0.0)
            else:
                self.beliefs[item["name"]] = min(current + 0.1, 0.95)
        
        if not self.beliefs:
            self.monologue = "Awaiting initial symptoms..."
            return "CONTINUE"
        
        sorted_beliefs = sorted(self.beliefs.items(), key=lambda x: x[1], reverse=True)
        top_name, top_score = sorted_beliefs[0]
        
        # Threshold for Gemini 3 diagnosis
        if top_score >= 0.88:
            return "DIAGNOSE"
        
        self.monologue = f"Evaluating potential {top_name} ({int(top_score*100)}%)..."
        return "CONTINUE"

class InterviewerAgent:
    def ask_gemini(self, prompt):
        try:
            # Gemini 3 often includes 'thoughts' in the response; we grab the text content
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini 3 Error: {e}")
            return None

    def generate_question(self, beliefs, db, history, asked_questions):
        if not beliefs:
            return "Hello. Please describe your symptoms so I can begin an assessment.", "Awaiting input", False
        
        sorted_beliefs = sorted(beliefs.items(), key=lambda x: x[1], reverse=True)
        for name, score in sorted_beliefs:
            disease_id = next((k for k, v in db.items() if v["name"] == name), None)
            if disease_id:
                keywords = db[disease_id].get("keywords", [])
                available = [kw for kw in keywords if kw.lower() not in asked_questions and kw.lower() not in ["weight", "body"]]
                
                if available:
                    target_kw = available[0].lower()
                    asked_questions.append(target_kw)
                    
                    # PROMPT: Utilizing Gemini 3's better instruction following
                    prompt = (
                        f"SYSTEM: You are a medical interviewer exploring the possibility of {name}.\n"
                        f"CONTEXT: User mentions so far: {history}.\n"
                        f"TASK: Ask a brief, natural question to see if they have '{target_kw}'.\n"
                        f"RULE: Do NOT mention the disease name yet. Just ask about the symptom."
                    )
                    return self.ask_gemini(prompt), f"Investigating {target_kw}", False
        
        return "I have sufficient data for an initial assessment.", "Analysis complete", True
