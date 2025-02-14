import requests
from tickets.models import Ticket
import os

HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct"
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

def query_huggingface(prompt):
    """Send a prompt to Hugging Face API and return the AI response."""
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    return response.json()[0]["generated_text"]

def generate_ai_answer(ticket_description):
    prompt = f"Student query: {ticket_description}\nAI response:"
    return query_huggingface(prompt)

def classify_department(ticket_description):
    prompt = f"Classify the following student query into one of the university departments: {', '.join([d[0] for d in Ticket.DEPARTMENT_CHOICES])}.\n\nQuery: {ticket_description}\n\nOutput only the department name."
    return query_huggingface(prompt)
