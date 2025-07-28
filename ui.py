import streamlit as st
import io
import os
import glob

# --- Library Specific Imports ---
from docx import Document
from resume_extractor import extract_resume_text
from resume_enhancer import extract_resume_details, build_placeholder_mapping, populate_pptx_with_resume
from resume_saver import create_docx_from_enhanced, create_txt_from_text, pptx_to_pdf, pptx_to_jpg

def is_valid_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == b"%PDF"
    except Exception:
        return False

def handle_resume_upload(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    temp_path = f"temp_resume.{ext}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    if ext == "pdf" and not is_valid_pdf(temp_path):
        st.error("Uploaded file is not a valid PDF.")
        resume_text = None
    else:
        try:
            resume_text = extract_resume_text(temp_path)
        except Exception as e:
            st.error(f"Resume extraction failed: {e}")
            resume_text = None
    if os.path.exists(temp_path):
        os.remove(temp_path)
    return resume_text

# --- Configuration ---
AI_MODELS = ["GPT-4", "Claude 3", "Gemini"]

# --- Streamlit UI Layout ---
st.set_page_config(
    page_title="AI Resume Optimizer",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Resume Optimizer")
st.markdown("""
    Upload your resume, paste a Job Description, select an AI model, and let our
    system tailor your resume for the specific role!
""")

# --- Sidebar for AI Model Selection ---
st.sidebar.header("AI Model Settings")
selected_ai_model = st.sidebar.selectbox(
    "Select AI Model for Optimization",
    AI_MODELS,
    index=0,
    help="Choose the AI model to use for tailoring your resume based on the Job Description."
)
st.sidebar.markdown("---")
st.sidebar.info("""
    **Note:** File handling uses in-memory objects for uploads and downloads.
""")

# --- Session State Initialization ---
if 'original_resume_text' not in st.session_state:
    st.session_state.original_resume_text = None
if 'processed_resume_text' not in st.session_state:
    st.session_state.processed_resume_text = None
if 'jd_input_text' not in st.session_state:
    st.session_state.jd_input_text = ""

# --- 1. Resume Input ---
st.header("1. Upload Your Resume")
uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "txt"],
    help="Supported formats: PDF, DOCX, TXT."
)

def handle_resume_upload(uploaded_file):
    temp_path = f"temp_resume.{uploaded_file.name.split('.')[-1]}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    resume_text = extract_resume_text(temp_path)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    return resume_text

if uploaded_file is not None:
    resume_text = handle_resume_upload(uploaded_file)
    if resume_text:
        st.session_state.original_resume_text = resume_text
        st.success("Resume uploaded and text extracted!")
    else:
        st.session_state.original_resume_text = None
        st.error("Could not extract text from the uploaded file or unsupported format.")

# --- 2. Job Description Input ---
st.header("2. Provide Job Description (JD)")

# List available JDs from dummy_jds folder
dummy_jds_folder = "dummy_jds"
jd_files = [f for f in os.listdir(dummy_jds_folder) if f.endswith(".txt")]
jd_options = ["(Paste your own JD)"] + jd_files

selected_jd_file = st.selectbox(
    "Or select a Job Description from examples",
    jd_options,
    help="Choose a sample JD from the dummy_jds folder or paste your own below."
)

if selected_jd_file != "(Paste your own JD)":
    with open(os.path.join(dummy_jds_folder, selected_jd_file), "r", encoding="utf-8") as f:
        jd_text = f.read()
    st.session_state.jd_input_text = jd_text
else:
    jd_text = st.session_state.jd_input_text

st.session_state.jd_input_text = st.text_area(
    "Paste the Job Description here",
    value=st.session_state.jd_input_text,
    height=300,
    placeholder="e.g., 'We are looking for a highly motivated software engineer with experience in Python, AWS, and machine learning...'"
)

# --- 3. Process Button ---
st.header("3. Optimize Resume")
if st.button("🚀 Process Resume"):
    if st.session_state.original_resume_text and st.session_state.jd_input_text:
        with st.spinner("Optimizing your resume using Gemini..."):
            # Use Gemini to enhance all resume sections
            enhanced = extract_resume_details(
                st.session_state.original_resume_text,
                st.session_state.jd_input_text
            )
            # Combine all enhanced sections for preview and downloads
            combined_text = ""
            for section, content in enhanced.items():
                combined_text += f"\n--- {section} ---\n{content}\n"
            st.session_state.processed_resume_text = combined_text.strip()

            # Generate PPTX
            template_path = os.path.abspath("CG_Resume_Template 1.pptx")
            output_pptx_path = os.path.abspath("CG_Resume_Filled.pptx")
            placeholder_mapping = build_placeholder_mapping(enhanced)
            populate_pptx_with_resume(template_path, output_pptx_path, placeholder_mapping)
            st.session_state.output_pptx_path = output_pptx_path

            # --- ADD THIS: Generate PDF and JPG outputs ---
            output_pdf_path = os.path.abspath("optimized_resume.pdf")
            output_jpg_dir = os.path.abspath("output_images")
            pptx_to_pdf(output_pptx_path, output_pdf_path)
            pptx_to_jpg(output_pptx_path, output_jpg_dir, base_name="optimized_resume")
            # ----------------------------------------------

        if st.session_state.processed_resume_text:
            st.balloons()
            st.success("Optimization process completed!")
        else:
            st.error("Resume optimization failed. Please check inputs.")
    else:
        st.warning("Please upload a resume and provide a Job Description before processing.")

# --- 4. Before & After Preview ---
st.header("4. Resume Preview")
if st.session_state.processed_resume_text:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Resume Preview")
        if st.session_state.original_resume_text:
            st.text_area(
                "Original Content",
                st.session_state.original_resume_text,
                height=400,
                disabled=True,
                help="This is the text extracted from your uploaded resume."
            )
        else:
            st.info("Upload a resume to see its original content here.")
    with col2:
        st.subheader("Optimized Resume Preview")
        st.text_area(
            "Optimized Content",
            st.session_state.processed_resume_text,
            height=400,
            disabled=True,
            help="This is the resume content after AI optimization based on the JD."
        )
else:
    st.info("Upload a resume, provide a JD, and click 'Process Resume' to see the previews.")

# --- 5. Download Options ---
st.header("5. Download Optimized Resume")
if st.session_state.processed_resume_text:
    st.markdown("Download your optimized resume in various formats:")

    docx_buffer = create_docx_from_enhanced(enhanced)
    txt_data = create_txt_from_text(st.session_state.processed_resume_text)

    st.download_button(
        label="Download as DOCX 📄",
        data=docx_buffer,
        file_name="optimized_resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        help="Download the optimized resume as a Microsoft Word document (.docx)."
    )

    st.download_button(
        label="Download as TXT 📝",
        data=txt_data,
        file_name="optimized_resume.txt",
        mime="text/plain",
        help="Download the optimized resume as a plain text file (.txt)."
    )

    if st.session_state.get("output_pptx_path") and os.path.exists(st.session_state.output_pptx_path):
        with open(st.session_state.output_pptx_path, "rb") as f:
            pptx_data = f.read()
        st.download_button(
            label="Download as PPTX 🎨",
            data=pptx_data,
            file_name="optimized_resume.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            help="Download the optimized resume as a PowerPoint file (.pptx)."
        )

    output_pdf_path = "optimized_resume.pdf"
    if os.path.exists(output_pdf_path):
        with open(output_pdf_path, "rb") as f:
            pdf_data = f.read()
        st.download_button(
            label="Download as PDF 📄",
            data=pdf_data,
            file_name="optimized_resume.pdf",
            mime="application/pdf"
        )

    output_jpg_dir = "output_images"
    jpg_dir = os.path.join(output_jpg_dir, "slides_images")
    jpg_files = sorted(glob.glob(os.path.join(jpg_dir, "*.jpg")))
    if jpg_files:
        with open(jpg_files[0], "rb") as f:
            jpg_data = f.read()
        st.download_button(
            label="Download First Slide as JPG 🖼️",
            data=jpg_data,
            file_name="optimized_resume_slide1.jpg",
            mime="image/jpeg"
        )
else:
    st.info("Optimized resume will be available for download here after successful processing.")