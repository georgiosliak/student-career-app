from fastapi import FastAPI 
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import FileResponse 
from pydantic import BaseModel 
from collections import Counter 
from dotenv import load_dotenv 
from fpdf import FPDF 
import requests 
import os 
import json 
import uuid 
 
load_dotenv() 
 
app = FastAPI(title="School Career Guidance Platform") 
 
app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 
 
app.mount("/static", StaticFiles(directory="static"), name="static") 
 
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") 
DATA_FILE = "data.json" 
 
if not os.path.exists(DATA_FILE): 
    with open(DATA_FILE, "w") as f: 
        json.dump([], f) 
 
 
class SkillsInput(BaseModel): 
    selections: list[str] 
    student_name: str 
 
 
skill_map = { 
    "Λύνω μαθηματικά προβλήματα": "Αναλυτική σκέψη", 
    "Βοηθάω άλλους": "Κοινωνική νοημοσύνη", 
    "Δημιουργώ πράγματα": "Δημιουργικότητα", 
    "Οργανώνω ομάδες": "Ηγεσία", 
    "Διαβάζω πολύ": "Γλωσσικές δεξιότητες", 
    "Παίζω παιχνίδια στρατηγικής": "Στρατηγική σκέψη", 
} 
 
career_map = { 
    "Αναλυτική σκέψη": ["Μηχανικός", "Πληροφορική", "Στατιστική"], 
    "Κοινωνική νοημοσύνη": ["Ψυχολογία", "Εκπαίδευση", "Κοινωνική εργασία"], 
    "Δημιουργικότητα": ["Σχεδιασμός", "Τέχνη", "Διαφήμιση"], 
    "Ηγεσία": ["Διοίκηση", "Project Management"], 
    "Γλωσσικές δεξιότητες": ["Επικοινωνία", "Δημοσιογραφία", "Συγγραφή"], 
    "Στρατηγική σκέψη": ["Οικονομία", "Πολιτική", "Στρατηγική ανάλυση"], 
} 
 
 
@app.post("/analyze") 
def analyze(input: SkillsInput): 
 
    skill_counter = Counter() 
 
    for selection in input.selections: 
        skill = skill_map.get(selection) 
        if skill: 
            skill_counter[skill] += 1 
 
    total = sum(skill_counter.values()) 
 
    percentages = { 
        k: round((v / total) * 100, 1) 
        for k, v in skill_counter.items() 
    } if total > 0 else {} 
 
    prompt = f""" 
    Μαθητής: {input.student_name} 
    Δεξιότητες: {percentages} 
 
    Δώσε επαγγελματικό προσανατολισμό 
    για μαθητή Γυμνασίου ή Λυκείου. 
    """ 
 
    response = requests.post( 
        "https://openrouter.ai/api/v1/chat/completions", 
        headers={ 
            "Authorization": f"Bearer {OPENROUTER_API_KEY}", 
            "Content-Type": "application/json" 
        }, 
        json={ 
            "model": "mistralai/mistral-7b-instruct", 
            "messages": [{"role": "user", "content": prompt}] 
        } 
    ) 
 
    ai_text = response.json()["choices"][0]["message"]["content"] 
 
    student_id = str(uuid.uuid4()) 
 
    record = { 
        "id": student_id, 
        "name": input.student_name, 
        "skills": percentages, 
        "analysis": ai_text 
    } 
 
    with open(DATA_FILE, "r+") as f: 
        data = json.load(f) 
        data.append(record) 
        f.seek(0) 
        json.dump(data, f, indent=2) 
 
    return record 
 
 
@app.get("/export-pdf/{student_id}") 
def export_pdf(student_id: str): 
 
    with open(DATA_FILE, "r") as f: 
        data = json.load(f) 
 
    student = next((s for s in data if s["id"] == student_id), None) 
 
    if not student: 
        return {"error": "Student not found"} 
 
    pdf = FPDF() 
    pdf.add_page() 
 
    pdf.set_font("Arial", "B", 16) 
    pdf.cell(0, 10, "Αναφορά Επαγγελματικού Προσανατολισμού", ln=True) 
 
    pdf.set_font("Arial", "", 12) 
    pdf.ln(5) 
    pdf.cell(0, 10, f"Μαθητής: {student['name']}", ln=True) 
    pdf.ln(5) 
 
    for skill, percent in student["skills"].items(): 
        pdf.multi_cell(0, 8, f"{skill}: {percent}%") 
 
    pdf.ln(5) 
    pdf.multi_cell(0, 8, "Ανάλυση AI:") 
    pdf.ln(3) 
    pdf.multi_cell(0, 8, student["analysis"]) 
 
    filename = f"{student_id}.pdf" 
    pdf.output(filename) 
 
    return FileResponse(filename, media_type="application/pdf", filename="report.pdf")
