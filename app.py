import streamlit as st
import os
from PIL import Image
from google import genai

# 1. Title & API Key Setup
st.set_page_config(page_title="Gemma 4 Multimodal Copilot", layout="wide")
st.title("⚡ Gemma 4 Multimodal Vision & Code Copilot")

api_key = st.sidebar.text_input("Google AI Studio API Key", type="password") or os.environ.get("GEMMA_API_KEY")

if not api_key:
    st.warning("Please enter your API Key in the sidebar to start!")
    st.stop()

client = genai.Client(api_key=api_key)

# 2. UI Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Input Context")
    
    # Vision Input: Code / Error Screenshot
    uploaded_image = st.file_uploader("Upload Code / UI Screenshot", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Context", use_container_width=True)
        
    # Text/Voice Simulation Input (Since API handles text + vision natively)
    voice_note_text = st.text_area(
        "Voice Instruction (Type what you'd say or paste a transcript)",
        value="Hey Gemma, this component breaks on empty data arrays. Look at the screenshot and fix the infinite loop bug."
    )

with col2:
    st.subheader("2. Gemma 4 Real-time Analysis")
    
    if st.button("🚀 Analyze with Gemma 4", type="primary", use_container_width=True):
        if not uploaded_image:
            st.error("Please upload a code screenshot!")
        else:
            with st.spinner("Gemma 4 is processing native visual and text tokens..."):
                contents = []
                
                # Append Vision Token Payload
                img = Image.open(uploaded_image)
                contents.append(img)
                
                # Prompt Instructions + Voice Note Text
                prompt = (
                    f"You are an expert developer copilot. The user provided this voice instruction: '{voice_note_text}'. "
                    "Analyze the visual code screenshot, identify the bug, explain the fix clearly, "
                    "and output the corrected code block using Gemma 4's code reasoning capabilities."
                )
                contents.append(prompt)

                try:
                    # Query Gemma 4 Model Endpoint (31B Dense multimodal model)
                    response = client.models.generate_content(
                        model='gemma-4-31b-it',
                        contents=contents,
                    )
                    
                    st.success("Analysis Complete!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"Error during execution: {e}")