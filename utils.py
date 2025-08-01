import os
import io
import pdfplumber
import docx
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def file_to_text(file):
    """
    Convert PDF or DOCX to text.
    """
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        return pdf_to_text(file)
    elif filename.endswith(".docx"):
        return docx_to_text(file)
    else:
        return None

def pdf_to_text(file):
    """
    Extract text from PDF using pdfplumber.
    """
    text = ''
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def docx_to_text(file):
    """
    Extract text from a DOCX file using python-docx.
    """
    text = ''
    document = docx.Document(file)
    for para in document.paragraphs:
        text += para.text + "\n"
    return text.strip()

def get_prompt_with_feedback(resume_text, description, min_experience, max_experience):
    """
    Build prompt with feedback instructions for Gemini.
    """
    return f"""
    You are an ATS (Applicant Tracking System) evaluator. 
    Compare the candidate's resume with the job description. 
    Provide:
      1. ATS percentage match (just the number, no % symbol)
      2. A one-line feedback on why the resume was accepted or rejected.
    
    Consider:
      - Skills match
      - Years of experience must be between {min_experience} and {max_experience}
      - Education and tools
    
    If resume is empty or irrelevant, give 0 as score and clear feedback.

    Job Description:
    {description}

    Resume:
    {resume_text}

    Output format (exactly):
    SCORE: <number>
    FEEDBACK: <short feedback sentence>
    """

def get_ats_score_and_feedback(prompt, file_name=None, retries=3):
    """
    Call Gemini API and parse ATS score and feedback.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = model.generate_content(prompt)
            if not response or not response.text:
                return 0, "No response from AI model."

            text = response.text.strip()
            score, feedback = parse_score_feedback(text)

            return score, feedback
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            attempt += 1

    return 0, "Error in AI evaluation."

def parse_score_feedback(output_text):
    """
    Parse output text of Gemini into score and feedback.
    """
    lines = output_text.split("\n")
    score = 0
    feedback = "No feedback provided."
    for line in lines:
        if line.lower().startswith("score"):
            try:
                score = int(line.split(":")[1].strip())
            except:
                score = 0
        if line.lower().startswith("feedback"):
            feedback = line.split(":", 1)[1].strip()

    return score, feedback

def create_zip_file(resumes):
    """
    Create a zip file from shortlisted resumes.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for res in resumes:
            res["file"].seek(0)
            zipf.writestr(res["name"], res["file"].read())
    zip_buffer.seek(0)
    return zip_buffer
