from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from collections import Counter
from fpdf import FPDF
import os
import json
import uuid

app = FastAPI(title="School Career Guidance Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

class SkillsInput(BaseModel):
    selections: list[str]
    student_name: str
    grade_level: str = "Γυμνάσιο"  # Προαιρετικό: "Γυμνάσιο" ή "Λύκειο"

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

activity_suggestions = {
    "Αναλυτική σκέψη": ["Μαθηματικοί γρίφοι", "Προγραμματιστικά projects", "Πειράματα φυσικής"],
    "Κοινωνική νοημοσύνη": ["Εθελοντισμός", "Ομαδικά project", "Συμμετοχή σε εκπαιδευτικές ομάδες"],
    "Δημιουργικότητα": ["Ζωγραφική/σχεδιασμός", "Δημιουργία ιστοριών", "Μικρά καλλιτεχνικά projects"],
    "Ηγεσία": ["Οργάνωση σχολικών ομάδων", "Διαχείριση project", "Σχολική εκπροσώπηση"],
    "Γλωσσικές δεξιότητες": ["Συγγραφή άρθρων", "Δημοσιογραφία μαθητικού περιοδικού", "Ανάγνωση βιβλίων"],
    "Στρατηγική σκέψη": ["Παιχνίδια στρατηγικής", "Οικονομικά simulations", "Σχολική πολιτική ανάλυση"],
}

@app.post("/analyze")
def analyze(input: SkillsInput):

    skill_counter = Counter()
    for sel in input.selections:
        skill = skill_map.get(sel)
        if skill:
            skill_counter[skill] += 1

    total = sum(skill_counter.values())
    percentages = {k: round(v/total*100,1) for k,v in skill_counter.items()} if total>0 else {}

    if not percentages:
        return {
            "id":"no-skills",
            "name":input.student_name,
            "skills":{},
            "analysis":"Δεν επιλέχθηκαν δεξιότητες."
        }

    top_skills = [k for k,_ in skill_counter.most_common(2)]
    suggested_careers = []
    activities = []
    for skill in top_skills:
        suggested_careers.extend(career_map.get(skill, []))
        activities.extend(activity_suggestions.get(skill, []))

    suggested_careers = list(dict.fromkeys(suggested_careers))
    activities = list(dict.fromkeys(activities))

    if len(top_skills)==1:
        skills_text = top_skills[0]
    else:
        skills_text = " και ".join(top_skills)

    # Δημιουργία φυσικού, φιλικού κειμένου με bullets
    analysis_text = (
        f"Ο/Η μαθητής/μαθήτρια {input.student_name} δείχνει ιδιαίτερη κλίση στις δεξιότητες: {skills_text}.\n\n"
        f"Προτεινόμενοι τομείς ενδιαφέροντος:\n- " + "\n- ".join(suggested_careers) + "\n\n"
        f"Στο {input.grade_level}, μπορείτε να εξερευνήσετε τις παρακάτω δραστηριότητες για να ενισχύσετε αυτές τις δεξιότητες:\n- "
        + "\n- ".join(activities) + "\n\n"
        "Συνιστάται να συμμετέχετε σε ομαδικές δραστηριότητες, projects και μικρές προκλήσεις που σχετίζονται με τα ενδιαφέροντά σας."
    )

    student_id = str(uuid.uuid4())
    record = {
        "id": student_id,
        "name": input.student_name,
        "skills": percentages,
        "analysis": analysis_text
    }

    with open(DATA_FILE,"r+") as f:
        data_file = json.load(f)
        data_file.append(record)
        f.seek(0)
        json.dump(data_file, f, indent=2)

    return record

@app.get("/export-pdf/{student_id}")
def export_pdf(student_id:str):
    with open(DATA_FILE,"r") as f:
        data=json.load(f)
    student=next((s for s in data if s["id"]==student_id),None)
    if not student:
        return {"error":"Student not found"}

    pdf=FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Αναφορά Επαγγελματικού Προσανατολισμού",ln=True)
    pdf.set_font("Arial","",12)
    pdf.ln(5)
    pdf.cell(0,10,f"Μαθητής: {student['name']}",ln=True)
    pdf.ln(5)
    for skill,percent in student["skills"].items():
        pdf.multi_cell(0,8,f"{skill}: {percent}%")
    pdf.ln(5)
    pdf.multi_cell(0,8,"Ανάλυση:")
    pdf.ln(3)
    pdf.multi_cell(0,8,student["analysis"])
    filename=f"{student_id}.pdf"
    pdf.output(filename)
    return FileResponse(filename,media_type="application/pdf",filename="report.pdf")
