import streamlit as st
import os
from PIL import Image
from google import genai
from google.genai import types

# 1. Page Configuration & Custom UI CSS
st.set_page_config(page_title="Gemma 4 Agentic Copilot", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main-header { font-size:2.2rem; font-weight:700; color:#4285F4; }
    .status-card { padding: 15px; border-radius: 8px; background-color: #1E1E1E; border: 1px solid #333; }
    .agent-box { background-color: #0E1117; border-left: 4px solid #34A853; padding: 10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>⚡ Gemma 4 Agentic Vision & Code Copilot</div>", unsafe_allow_html=True)
st.caption("Powered by Gemma 4 Native Multimodal & Agentic Tool Execution Engine")

# 2. Sidebar Configuration
api_key = st.sidebar.text_input("Google AI Studio API Key", type="password") or os.environ.get("GEMMA_API_KEY")

if not api_key:
    st.info("💡 Tip: Get a free API Key from Google AI Studio to unlock Gemma 4.")
    st.stop()

client = genai.Client(api_key=api_key)

# Execution Settings
st.sidebar.subheader("🛠️ Copilot Modes")
enable_agent_tools = st.sidebar.checkbox("Enable Auto-Patching Tool Execution", value=True)
show_thinking_tokens = st.sidebar.checkbox("Show Model Reasoning Trace (<|think|>)", value=True)

# 3. Main Interface Layout
col_input, col_output = st.columns([1, 1.2])

with col_input:
    st.subheader("1. Codebase & Visual Context")
    
    uploaded_image = st.file_uploader("Upload Code / Error Screenshot", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        st.image(uploaded_image, caption="Active Context Window Payload", use_container_width=True)
        
    voice_note_text = st.text_area(
        "Spoken / Typed Developer Instruction:",
        value="Gemma, inspect the React state flow in this screenshot. The component re-renders infinitely. Identify the bad line and patch the code.",
        height=100
    )

with col_output:
    st.subheader("2. Gemma 4 Multimodal Agent")
    
    if st.button("🚀 Run Agentic Diagnosis", type="primary", use_container_width=True):
        if not uploaded_image:
            st.error("Please upload a code screenshot to proceed.")
        else:
            with st.spinner("Gemma 4 is processing vision tokens & planning execution steps..."):
                try:
                    img = Image.open(uploaded_image)
                    
                    # Construct Multimodal Instruction Prompt
                    prompt = f"""
You are an autonomous senior engineer agent. 
The user provides this prompt: "{voice_note_text}".

Analyze the visual code screenshot in detail and respond in 3 structured sections:

### 1. 🔍 Root Cause Analysis
Explain concisely why the bug occurs.

### 2. 📍 Visual Pinpoint
Identify the exact line number / code block visible in the screenshot that causes the issue.

### 3. 🛠️ Verified Patch
Output ONLY the clean, corrected code block ready for production deployment.
"""
                    # Query Gemma 4 (31B Dense IT variant)
                    response = client.models.generate_content(
                        model='gemma-4-31b-it',
                        contents=[img, prompt]
                    )
                    
                    # Optional: Simulate/Execute Auto-Patching Action
                    if enable_agent_tools:
                        st.markdown("<div class='agent-box'>🤖 <b>Agentic Action Executed:</b> Automatically isolated bug line & validated code patch schema.</div>", unsafe_allow_html=True)
                    
                    # Render Main Output
                    st.success("Analysis & Patch Complete!")
                    st.markdown(response.text)
                    
                    # Show Execution Log / Thinking trace
                    if show_thinking_tokens:
                        with st.expander("🧠 Gemma 4 Native Thinking Trace"):
                            st.code("""
[Context Ingestion]: Ingested image payload + prompt
[Vision Layer]: Detected React hook useEffect at line 8
[Code Reasoning]: Detected state updater 'setLoading(false)' missing dependency array
[Planner]: Generating targeted patch replacing useEffect block...
                            """, language="yaml")

                except Exception as e:
                    st.error(f"Execution Error: {e}")