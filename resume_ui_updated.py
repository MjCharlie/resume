
import streamlit as st
import io
import os
import glob

# --- Library Specific Imports ---
from docx import Document
from resume_extractor import extract_resume_text
from resume_enhancer import extract_resume_details, build_placeholder_mapping, populate_pptx_with_resume
from resume_saver import create_docx_from_enhanced, create_txt_from_text, pptx_to_pdf, pptx_to_jpg

# --- Config ---
st.set_page_config(page_title="AI Resume Optimizer", page_icon="📄", layout="wide")

# --- Custom Tech Theme Styling ---
custom_css = """
<style>
    body {
        background-color: #0f1117;
        color: #f1f1f1;
    }
    .main {
        padding: 2rem;
        background: linear-gradient(to bottom right, #1a1a2e, #16213e);
        border-radius: 12px;
        box-shadow: 0 0 20px rgba(0,0,0,0.4);
    }
    h1, h2, h3 {
        color: #45f3ff;
    }
    .stButton button {
        background-color: #00adb5;
        color: white;
        border: None;
        padding: 0.5rem 1.5rem;
        border-radius: 8px;
    }
    .stTextArea textarea {
        background-color: #222831;
        color: #eeeeee;
        border-radius: 10px;
    }
    .stDownloadButton button {
        background-color: #393e46;
        color: #eeeeee;
        border-radius: 6px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Logo and Title ---
st.image("image.png", width=100)  # Place your logo file in same directory
st.title("🤖 AI Resume Optimizer")
st.markdown("""
Upload your resume, paste a Job Description, select an AI model, and let our
system tailor your resume for the specific role!
""")

# --- AI Model Selection (converted to top row) ---
# AI_MODELS = ["GPT-4", "Claude 3", "Gemini"]
# selected_ai_model = st.selectbox(
#     "Select AI Model for Optimization:",
#     AI_MODELS,
#     index=0
# )

# st.info("Note: File handling uses in-memory objects for uploads and downloads.")

# --- Session State Initialization ---
if 'original_resume_text' not in st.session_state:
    st.session_state.original_resume_text = None
if 'processed_resume_text' not in st.session_state:
    st.session_state.processed_resume_text = None
if 'jd_input_text' not in st.session_state:
    st.session_state.jd_input_text = ""

# --- 1. Upload Resume ---
st.header("1. Upload Your Resume")
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

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

if uploaded_file:
    resume_text = handle_resume_upload(uploaded_file)
    if resume_text:
        st.session_state.original_resume_text = resume_text
        st.success("Resume uploaded and text extracted!")
    else:
        st.session_state.original_resume_text = None
        st.error("Could not extract text or unsupported format.")

# --- 2. JD Input ---
st.header("2. Provide Job Description (JD)")

dummy_jds_folder = "dummy_jds"
jd_files = [f for f in os.listdir(dummy_jds_folder) if f.endswith(".txt")]
jd_options = ["(Paste your own JD)"] + jd_files

selected_jd_file = st.selectbox("Or select from example JDs:", jd_options)

if selected_jd_file != "(Paste your own JD)":
    with open(os.path.join(dummy_jds_folder, selected_jd_file), "r", encoding="utf-8") as f:
        jd_text = f.read()
    st.session_state.jd_input_text = jd_text
else:
    jd_text = st.session_state.jd_input_text

st.session_state.jd_input_text = st.text_area(
    "Paste the Job Description here",
    value=st.session_state.jd_input_text,
    height=300
)

# --- 3. Optimize ---
st.header("3. Optimize Resume")
if st.button("🚀 Process Resume"):
    if st.session_state.original_resume_text and st.session_state.jd_input_text:
        with st.spinner("Optimizing using Gemini..."):
            enhanced = extract_resume_details(
                st.session_state.original_resume_text,
                st.session_state.jd_input_text
            )
            combined_text = ""
            for section, content in enhanced.items():
                combined_text += f"\n--- {section} ---\n{content}\n"
            st.session_state.processed_resume_text = combined_text.strip()

            template_path = os.path.abspath("CG_Resume_Template 1.pptx")
            output_pptx_path = os.path.abspath("CG_Resume_Filled.pptx")
            placeholder_mapping = build_placeholder_mapping(enhanced)
            populate_pptx_with_resume(template_path, output_pptx_path, placeholder_mapping)
            st.session_state.output_pptx_path = output_pptx_path

            output_pdf_path = os.path.abspath("optimized_resume.pdf")
            output_jpg_dir = os.path.abspath("output_images")
            pptx_to_pdf(output_pptx_path, output_pdf_path)
            pptx_to_jpg(output_pptx_path, output_jpg_dir, base_name="optimized_resume")

        if st.session_state.processed_resume_text:
            st.balloons()
            st.success("Optimization complete!")
    else:
        st.warning("Please upload resume and JD before processing.")

# --- 4. Preview ---
st.header("4. Resume Preview")
if st.session_state.processed_resume_text:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Resume")
        st.text_area("Original", st.session_state.original_resume_text, height=400, disabled=True)
    with col2:
        st.subheader("Optimized Resume")
        st.text_area("Optimized", st.session_state.processed_resume_text, height=400, disabled=True)

# --- 5. Download ---
st.header("5. Download Optimized Resume")
if st.session_state.processed_resume_text:
    docx_buffer = create_docx_from_enhanced(enhanced)
    txt_data = create_txt_from_text(st.session_state.processed_resume_text)

    st.download_button("📄 Download DOCX", docx_buffer, "optimized_resume.docx")
    st.download_button("📝 Download TXT", txt_data, "optimized_resume.txt")

    if os.path.exists(st.session_state.output_pptx_path):
        with open(st.session_state.output_pptx_path, "rb") as f:
            st.download_button("🎨 Download PPTX", f.read(), "optimized_resume.pptx")

    output_pdf_path = "optimized_resume.pdf"
    if os.path.exists(output_pdf_path):
        with open(output_pdf_path, "rb") as f:
            st.download_button("📄 Download PDF", f.read(), "optimized_resume.pdf")

    jpg_dir = os.path.join("output_images", "slides_images")
    jpg_files = sorted(glob.glob(os.path.join(jpg_dir, "*.jpg")))
    if jpg_files:
        with open(jpg_files[0], "rb") as f:
            st.download_button("🖼️ Download Slide JPG", f.read(), "optimized_resume_slide1.jpg")
