import os
import shutil
import pdfplumber
import google.generativeai as genai
import time
from google.api_core.exceptions import ResourceExhausted

# Directories
resume_dir = './resumes'
shortlist_dir = './short-listed-resumes'

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

os.makedirs(shortlist_dir, exist_ok=True)

# Extract text from PDF
def pdf_to_text(pdf_path):
    text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# Build the full path of a PDF
def get_pdf_path(resume_dir, resume_file):
    return os.path.join(resume_dir, resume_file)

# Prompt to get ATS percentage and feedback
def get_prompt(text, description):
    return f"""
    You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding of ATS functionality, be strict on key responsibilities and requirements but be flexible on the rest. 
    Evaluate the given resume against the provided job description and provide the following output:

    1. A single number (percentage match without the % symbol) on the first line.
    2. On the next lines, provide detailed feedback explaining:
       - Which skills/experience match well
       - Which skills/experience are missing
       - Suggestions for improvement

    Job Description:
    {description}

    Resume:
    {text}
    """

# Get ATS percentage and feedback
def get_ats_feedback(prompt, retries=5, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            response = model.generate_content(prompt)
            if response and response.text:
                lines = response.text.strip().split("\n", 1)
                score = lines[0].strip()
                feedback = lines[1].strip() if len(lines) > 1 else "No feedback provided."
                return score, feedback
            return None, None
        except ResourceExhausted:
            print(f"API quota exhausted. Waiting for {delay} seconds before retrying...")
            time.sleep(delay)
            attempt += 1
    print("Exceeded maximum retries. Skipping this resume.")
    return None, None

# Get resumes from directory
def get_resume_dir():
    try:
        return os.listdir(resume_dir)
    except Exception:
        return None

def main():
    # Take job description as input
    print("Please paste the job description below (Press Enter twice to finish):")
    description_lines = []
    while True:
        line = input()
        if line == "":
            break
        description_lines.append(line)
    description = "\n".join(description_lines)

    # Get resumes
    resume_files = get_resume_dir()
    if not resume_files or len(resume_files) == 0:
        print("No resumes found :(")
        return

    # Process each resume
    for resume_file in resume_files:
        if resume_file.lower().endswith('.pdf'):
            pdf_path = get_pdf_path(resume_dir, resume_file)
            print(f'Processing {pdf_path}...')

            text = pdf_to_text(pdf_path)
            prompt = get_prompt(text, description)
            score, feedback = get_ats_feedback(prompt)
            
            if score is None:
                continue

            try:
                ats_percentage = int(score)

                if ats_percentage > 90:
                    shutil.move(pdf_path, shortlist_dir)
                    print(f'{pdf_path}: ✅ Passed the ATS percentage criteria with {ats_percentage}%')
                else:
                    print(f'{pdf_path}: ❌ Did not meet the ATS percentage criteria ({ats_percentage}%)')

                # Print feedback
                print("\n----- FEEDBACK -----")
                print(feedback)
                print("--------------------\n")

                # Save feedback to a text file
                feedback_filename = os.path.splitext(resume_file)[0] + "_feedback.txt"
                feedback_path = os.path.join(shortlist_dir if ats_percentage > 90 else resume_dir, feedback_filename)
                with open(feedback_path, "w", encoding="utf-8") as f:
                    f.write(f"ATS Score: {ats_percentage}%\n\n")
                    f.write(feedback)

            except Exception:
                print(f'{pdf_path}: Invalid ATS response from model')

if __name__ == "__main__":
    main()
