import sys
import utils
import email_service
import streamlit as st
from io import StringIO
from dotenv import load_dotenv

load_dotenv()

# Capture debug logs
sys.stdout = StringIO() 
st.set_page_config(page_title="HR ∙ ATS")

def main():
    st.title("HR | ATS")
    st.markdown("---")

    st.subheader("Job Description and ATS Criteria")
    st.write("Please provide the job description and set the ATS criteria for filtering resumes.")

    description = st.text_area("Job Description:", key="input", height=150)
    min_experience = st.number_input("Minimum Years of Experience:", min_value=0, max_value=50, value=1, step=1)
    max_experience = st.number_input("Maximum Years of Experience:", min_value=0, max_value=50, value=3, step=1)
    ats_criteria = st.number_input("Enter ATS Score Criteria (difficulty level):", min_value=0, max_value=100, value=65, step=1)

    st.markdown("---")
    st.subheader("Upload Resumes")
    uploaded_files = st.file_uploader("Upload your resumes (PDF or DOCX)...", type=["pdf", "docx"], accept_multiple_files=True)

    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded successfully.")

    submit = st.button("Process Resumes")
    st.markdown("---")
    if submit:
        if not description:
            st.error("Please provide a job description before processing resumes.")
        elif not uploaded_files:
            st.error("Please upload at least one resume to proceed.")
        else:
            process_resumes(description, ats_criteria, uploaded_files, min_experience, max_experience)
            
    with st.expander("Show Debug Logs"):
        captured_output = sys.stdout.getvalue()
        st.text_area("Debug Logs", captured_output, height=150)


def process_resumes(description, ats_criteria, uploaded_files, min_experience, max_experience):
    proceed_resumes = []
    
    for uploaded_file in uploaded_files:
        pdf_content = utils.file_to_text(uploaded_file)
        if not pdf_content:
            st.warning(f"Rejected: {uploaded_file.name} (Empty or unreadable)")
            continue

        # Updated prompt to request feedback and decision
        prompt = utils.get_prompt_with_feedback(pdf_content, description, min_experience, max_experience, ats_criteria)
        ats_score, feedback = utils.get_ats_score_and_feedback(prompt=prompt, file_name=uploaded_file.name)

        if ats_score is None:
            st.error(f"Error processing {uploaded_file.name}")
            continue

        # Show result per resume on frontend
        decision_text = "✅ ACCEPTED" if ats_score >= int(ats_criteria) else "❌ REJECTED"
        decision_color = "green" if ats_score >= int(ats_criteria) else "red"

        st.markdown(f"### **{uploaded_file.name}** - <span style='color:{decision_color}'>{decision_text}</span> (ATS Score: {ats_score}%)", unsafe_allow_html=True)
        st.markdown(f"**Feedback:**\n\n{feedback}")

        if ats_score >= int(ats_criteria):
            proceed_resumes.append({
                "Name": uploaded_file.name,
                "Score": ats_score,
                "Feedback": feedback,
                "Resume": uploaded_file.name,
                "ResumeFile": uploaded_file
            })

    # Allow download of shortlisted resumes
    if len(proceed_resumes) != 0:
        zip_buffer = utils.create_zip_file(proceed_resumes)
        current_date_str = utils.get_day_month_year()
        if zip_buffer: 
            st.download_button(
                label="Download Shortlisted Resumes as ZIP",
                data=zip_buffer,
                file_name=f"shortlisted-resumes-{current_date_str}.zip",
                mime="application/zip"
            )


if __name__ == "__main__":
    main()
