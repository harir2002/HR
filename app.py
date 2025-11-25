"""
AI-Powered Resume Analysis System
Complete 2-Agent Workflow Implementation
"""
import streamlit as st
import os
import pandas as pd
from datetime import datetime
import json
from dotenv import load_dotenv
import logging

# Try to import PDF/DOCX libraries (all optional)
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

load_dotenv()

# Show warnings for missing libraries
if not HAS_PYPDF2 and not HAS_PDFPLUMBER:
    st.error("❌ No PDF library installed! Install with: pip install PyPDF2")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(page_title="AI Resume Analysis System", layout="wide", page_icon="🤖")

# Create directories
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data/results", exist_ok=True)

# Import modules
from crew_setup import run_complete_analysis

# No database - results stored in session only
USE_CHROMADB = False


def extract_text_from_file(uploaded_file):
    """Extract text from PDF/DOCX/TXT files"""
    try:
        if uploaded_file.type == "application/pdf":
            # Try PyPDF2 first
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
                if text.strip():
                    return text, True, None
            except:
                pass
            
            # Fallback to pdfplumber
            try:
                uploaded_file.seek(0)
                with pdfplumber.open(uploaded_file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                if text.strip():
                    return text, True, None
            except:
                pass
            
            return "", False, "Could not extract text from PDF"
        
        elif "wordprocessingml" in uploaded_file.type or uploaded_file.name.endswith(".docx"):
            try:
                doc = Document(uploaded_file)
                text = "\n".join([para.text for para in doc.paragraphs])
                if text.strip():
                    return text, True, None
                return "", False, "DOCX file is empty"
            except Exception as e:
                return "", False, f"Error reading DOCX: {str(e)}"
        
        else:  # Text file
            try:
                text = uploaded_file.getvalue().decode("utf-8")
                if text.strip():
                    return text, True, None
                return "", False, "Text file is empty"
            except Exception as e:
                return "", False, f"Error reading text file: {str(e)}"
    
    except Exception as e:
        return "", False, f"Unexpected error: {str(e)}"


# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

# No database - use session state only
if 'all_results' not in st.session_state:
    st.session_state.all_results = []

# App title
st.title("🤖 AI-Powered Resume Analysis System")
st.markdown("**CrewAI Multi-Agent Workflow** | Agent 1: Resume Parser → Agent 2: Insight Extractor")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Job Requirements")
    job_title = st.text_input("Job Title", value=os.getenv("JOB_TITLE", "Senior Python Developer"))
    required_skills = st.text_area(
        "Technical Skills (comma-separated)",
        value=os.getenv("REQUIRED_SKILLS", "Python, Django, AWS")
    )
    st.write("**Required Experience (years)**")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        min_experience = st.number_input(
            "Min",
            min_value=0,
            max_value=30,
            value=0,
            key="min_exp"
        )
    with col_exp2:
        max_experience = st.number_input(
            "Max",
            min_value=0,
            max_value=30,
            value=3,
            key="max_exp"
        )
    
    # Create experience range string
    required_experience = f"{min_experience} to {max_experience}"
    nice_to_have = st.text_area(
        "Mandatory Skills",
        value="Docker, Kubernetes, Redis"
    )
    
    shortlist_threshold = st.slider(
        "Shortlist Threshold Score",
        0, 100, 70,
        help="Candidates above this score will be shortlisted"
    )
    
    st.divider()
    
    # Statistics
    st.subheader("📊 Statistics")
    total = len(st.session_state.all_results)
    shortlisted = sum(1 for r in st.session_state.all_results if r.get("shortlisted", False))
    avg_score = sum(r.get("confidence_score", 0) for r in st.session_state.all_results) / max(total, 1) if total > 0 else 0
    
    st.metric("Total Analyzed", total)
    st.metric("Shortlisted", shortlisted)
    st.metric("Avg Score", f"{round(avg_score, 1)}%")

# Main tabs
tab1, tab2, tab3 = st.tabs([
    "📝 Analyze Resume",
    "👥 All Candidates",
    "✅ Shortlisted"
])

# TAB 1: ANALYZE RESUME
with tab1:
    st.header("Step 1: Upload Resumes")
    
    uploaded_files = st.file_uploader(
        "Upload Resumes (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Upload multiple resumes for bulk AI analysis (up to 100 files)"
    )
    
    if uploaded_files:
        st.info(f"📊 **{len(uploaded_files)} resume(s) selected**")
    
    if uploaded_files:
        if st.button("🚀 Analyze All Resumes", type="primary", use_container_width=True):
            # Bulk processing
            total_files = len(uploaded_files)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful = 0
            failed = 0
            failed_files = []
            
            for idx, uploaded_file in enumerate(uploaded_files):
                result = None
                status_text.text(f"Processing {idx + 1}/{total_files}: {uploaded_file.name}")
                
                # Extract text
                resume_text, success, error = extract_text_from_file(uploaded_file)
                
                if not success:
                    st.error(f"❌ {uploaded_file.name}: {error}")
                    failed += 1
                    failed_files.append(f"{uploaded_file.name} - {error}")
                    progress_bar.progress((idx + 1) / total_files)
                    continue
                
                st.info(f"✅ Extracted {len(resume_text)} characters from {uploaded_file.name}")
                
                # Run 2-agent workflow
                with st.spinner(f"🤖 Analyzing {uploaded_file.name}..."):
                    job_requirements = {
                        "job_title": job_title,
                        "required_skills": required_skills,
                        "required_experience_years": required_experience,
                        "min_experience": min_experience,
                        "max_experience": max_experience,
                        "nice_to_have": nice_to_have
                    }
                    
                    try:
                        result = run_complete_analysis(resume_text, job_requirements)
                    except Exception as e:
                        st.error(f"❌ {uploaded_file.name}: Analysis error - {str(e)}")
                        failed += 1
                        failed_files.append(f"{uploaded_file.name} - Analysis error: {str(e)}")
                        progress_bar.progress((idx + 1) / total_files)
                        continue
                
                if result and result.get("status") == "success":
                    logger.info("✅ Analysis completed successfully")
                    
                    parsed = result["parsed_resume"]
                    analysis = result["analysis"]
                    
                    logger.info(f"Parsed candidate: {parsed.get('name', 'Unknown')}")
                    logger.info(f"Skills extracted: {len(parsed.get('skills', []))} skills")
                    logger.info(f"Skills: {parsed.get('skills', [])}")
                    logger.info(f"Confidence score: {analysis.get('confidence_score', 0)}%")
                    logger.info(f"Strengths: {analysis.get('key_strengths', [])}")
                    logger.info(f"Gaps: {analysis.get('gaps', [])}")
                    
                    # Save to session state with FULL data
                    st.session_state.all_results.append({
                        "name": parsed.get("name", "Unknown"),
                        "email": parsed.get("email", ""),
                        "phone": parsed.get("phone", "N/A"),
                        "experience_years": parsed.get("experience_years", 0),
                        "skills": parsed.get("skills", []),
                        "confidence_score": analysis.get("confidence_score", 0),
                        "shortlisted": analysis.get("confidence_score", 0) >= shortlist_threshold,
                        "key_strengths": analysis.get("key_strengths", []),
                        "gaps": analysis.get("gaps", []),
                        "recommendation": analysis.get("recommendation", "N/A"),
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "resume_file": uploaded_file.name
                    })
                    
                    # Store last analysis
                    st.session_state.current_analysis = {
                        "parsed": parsed,
                        "analysis": analysis,
                        "resume_name": uploaded_file.name
                    }
                    
                    successful += 1
                    st.success(f"✅ {uploaded_file.name} - Analysis complete!")
                    logger.info("✅ ANALYSIS COMPLETE!")
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                    st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    logger.error(f"❌ Analysis failed: {error_msg}")
                    failed += 1
                    failed_files.append(f"{uploaded_file.name} - {error_msg}")
                
                # Update progress
                progress_bar.progress((idx + 1) / total_files)
            
            # Final summary
            progress_bar.progress(1.0)
            status_text.success(f"✅ Bulk processing complete!")
            
            if successful > 0:
                st.success(f"""
                **Processing Summary:**
                - ✅ Successful: {successful}
                - ❌ Failed: {failed}
                - 📊 Total: {total_files}
                """)
            
            if failed > 0:
                st.error(f"**Failed Resumes ({failed}):**")
                for failed_file in failed_files:
                    st.write(f"• {failed_file}")
            
            logger.info("=" * 80)
            logger.info(f"BULK PROCESSING COMPLETE: {successful} successful, {failed} failed")
            logger.info("=" * 80)
    
    # Display ALL results after bulk processing - FULL DETAILED VIEW FOR EACH
    if st.session_state.all_results:
        st.divider()
        st.header("📊 All Candidates Analysis Results")
        
        # Show job requirements summary at top
        with st.container(border=True):
            st.subheader("📋 Job Requirements")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Job Title:** {job_title}")
                st.write(f"**Required Experience:** {required_experience} years")
            with col2:
                st.write(f"**Technical Skills:** {required_skills}")
            with col3:
                st.write(f"**Mandatory Skills:** {nice_to_have}")
        
        st.divider()
        
        # Sort by score
        sorted_results = sorted(st.session_state.all_results, key=lambda x: x.get("confidence_score", 0), reverse=True)
        
        # Display each candidate with full details
        for idx, result in enumerate(sorted_results):
            score = result.get("confidence_score", 0)
            
            # Color coding
            if score >= 80:
                emoji = "🟢"
                level = "Excellent"
            elif score >= 60:
                emoji = "🟡"
                level = "Good"
            elif score >= 40:
                emoji = "🟠"
                level = "Moderate"
            else:
                emoji = "🔴"
                level = "Poor"
            
            # Header for each candidate
            if idx == 0:
                st.markdown(f"## 🏆 Candidate #{idx + 1} - BEST MATCH")
            else:
                st.markdown(f"## Candidate #{idx + 1}")
            
            with st.container(border=True):
                # Top metrics row
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence Score", f"{score}%")
                    st.caption(f"{emoji} {level}")
                with col2:
                    shortlisted = result.get("shortlisted", False)
                    st.metric("Shortlisted", "✅ Yes" if shortlisted else "❌ No")
                with col3:
                    recommendation = result.get("recommendation", "N/A")
                    st.metric("Recommendation", recommendation[:30] + "..." if len(recommendation) > 30 else recommendation)
                
                st.divider()
                
                # Detailed information
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.subheader("👤 Candidate Information")
                    st.write(f"**Name:** {result.get('name', 'Unknown')}")
                    st.write(f"**Email:** {result.get('email', 'N/A')}")
                    st.write(f"**Phone:** {result.get('phone', 'N/A')}")
                    st.write(f"**Experience:** {result.get('experience_years', 0)} years")
                    
                    st.write("")
                    st.write("**Skills:**")
                    skills = result.get('skills', [])
                    if skills:
                        st.write(", ".join(skills))
                    else:
                        st.write("No skills extracted")
                
                with col_right:
                    st.subheader("💡 Key Insights")
                    
                    st.write("**Strengths:**")
                    for strength in result.get("key_strengths", []):
                        st.write(f"✅ {strength}")
                    
                    st.write("")
                    st.write("**Gaps:**")
                    for gap in result.get("gaps", []):
                        st.write(f"⚠️ {gap}")
            
            st.divider()
    
    # Display single result (for backward compatibility)
    elif st.session_state.current_analysis:
        st.divider()
        st.header("📊 Analysis Results")
        
        parsed = st.session_state.current_analysis["parsed"]
        analysis = st.session_state.current_analysis["analysis"]
        
        # Score display
        score = analysis.get("confidence_score", 0)
        if score >= 80:
            color = "🟢"
            level = "Excellent"
        elif score >= 60:
            color = "🟡"
            level = "Good"
        elif score >= 40:
            color = "🟠"
            level = "Moderate"
        else:
            color = "🔴"
            level = "Poor"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Confidence Score", f"{score}%", level)
        with col2:
            shortlisted = score >= shortlist_threshold
            st.metric("Shortlisted", "✅ Yes" if shortlisted else "❌ No")
        with col3:
            st.metric("Recommendation", analysis.get("recommendation", "N/A")[:20])
        
        st.divider()
        
        # Candidate info
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Candidate Information")
            st.write(f"**Name:** {parsed.get('name', 'Unknown')}")
            st.write(f"**Email:** {parsed.get('email', 'N/A')}")
            st.write(f"**Phone:** {parsed.get('phone', 'N/A')}")
            st.write(f"**Experience:** {parsed.get('experience_years', 0)} years")
            
            st.write("**Skills:**")
            skills = parsed.get('skills', [])
            if skills:
                st.write(", ".join(skills[:10]))
            else:
                st.write("No skills extracted")
        
        with col2:
            st.subheader("💡 Key Insights")
            
            st.write("**Strengths:**")
            for strength in analysis.get("key_strengths", []):
                st.write(f"✅ {strength}")
            
            st.write("**Gaps:**")
            for gap in analysis.get("gaps", []):
                st.write(f"⚠️ {gap}")

# TAB 2: ALL CANDIDATES
with tab2:
    st.header("👥 All Analyzed Candidates")
    
    if st.session_state.all_results:
        df = pd.DataFrame(st.session_state.all_results)
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            min_score = st.slider("Minimum Score", 0, 100, 0)
        with col2:
            show_shortlisted = st.checkbox("Show only shortlisted")
        
        # Apply filters
        filtered_df = df[df["confidence_score"] >= min_score]
        if show_shortlisted:
            filtered_df = filtered_df[filtered_df["shortlisted"] == True]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # Download
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv"
        )
    else:
        st.info("No candidates analyzed yet. Upload resumes in the 'Analyze Resume' tab.")

# TAB 3: SHORTLISTED
with tab3:
    st.header("✅ Shortlisted Candidates")
    
    shortlisted = [r for r in st.session_state.all_results if r.get("shortlisted", False)]
    
    if shortlisted:
        df = pd.DataFrame(shortlisted)
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Shortlisted",
            csv,
            f"shortlisted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv"
        )
    else:
        st.info("No candidates shortlisted yet.")



# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🤖 Powered by 2 AI Agents + Groq Llama 3.3 70B | Session-based Storage</p>
</div>
""", unsafe_allow_html=True)
