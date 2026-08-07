import os
import json
from groq import Groq
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class ResponseFeedback(BaseModel):
    score: int = Field(description="Score from 0 to 10")
    technical_accuracy: str = Field(description="Summary of technical accuracy")
    key_strengths: list[str] = Field(description="List of key strengths")
    missing_points: list[str] = Field(description="List of missing concepts or points")


class InterviewEngine:
    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        # Use explicitly passed key from app.py, or fall back to local environment
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY is missing!")
            
        self.client = Groq(api_key=key)
        self.model = model

    def generate_question(self, role: str, topic: str, difficulty: str, topic_history: list) -> str:
        prompt = f"""
        You are an expert technical interviewer for a {role} position.
        Generate ONE concise, realistic technical interview question on the topic of '{topic}'.
        Difficulty level: {difficulty}.
        Previous topics covered in this session: {topic_history}.
        Return ONLY the raw question text without introductory pleasantries.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def evaluate_response(self, question: str, candidate_answer: str) -> ResponseFeedback:
        prompt = f"""
        Evaluate this technical interview answer.
        Question: {question}
        Candidate Answer: {candidate_answer}

        Provide a structured JSON output with these exact keys:
        - "score": integer from 0 to 10
        - "technical_accuracy": brief string summary of technical accuracy
        - "key_strengths": list of strings detailing key strengths
        - "missing_points": list of strings detailing missing concepts or inaccuracies
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content)
        return ResponseFeedback.model_validate(data)