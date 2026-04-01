import streamlit as st
from docx import Document
import subprocess
import os
import tempfile

# --- PAGE SETUP ---
st.set_page_config(page_title="Script Runner", page_icon="🎭", layout="centered")

# --- CORE FUNCTIONS ---
@st.cache_data(show_spinner=False)
def parse_script(file_bytes, practicing_character, lines_of_context):
    """Reads the docx file and chunks it into 'scenes' based on your character's lines."""
    doc = Document(file_bytes)
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    char_prefixes = (f"{practicing_character}:", f"{practicing_character} :", f"{practicing_character} -")
    user_line_indices = [i for i, text in enumerate(lines) if text.startswith(char_prefixes)]
    
    if not user_line_indices:
        return []

    blocks = []
    last_played_index = -1
    
    for u_idx in user_line_indices:
        start_idx = max(last_played_index + 1, u_idx - lines_of_context)
        context_lines = lines[start_idx:u_idx]
        user_line = lines[u_idx]
        
        blocks.append({
            'context': context_lines,
            'user_line': user_line,
            'jumped': start_idx > last_played_index + 1
        })
        last_played_index = u_idx
        
    return blocks

@st.cache_data(show_spinner=False)
def get_audio_bytes(text_to_speak):
    """Generates audio using edge-tts and returns the raw bytes for the web player."""
    if not text_to_speak.strip():
        return None
        
    # Create a temporary file to save the audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        temp_path = tmp.name
        
    try:
        # Generate the audio
        subprocess.run([
            "edge-tts", 
            "--voice", "he-IL-AvriNeural", 
            "--rate", "+15%", # Slightly faster for better flow
            "--text", text_to_speak, 
            "--write-media", temp_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Read the audio bytes to send to the browser
        with open(temp_path, "rb") as f:
            audio_data = f.read()
        return audio_data
        
    except Exception as e:
        st.error(f"Audio generation failed: {e}")
        return None
    finally:
        # Clean up the file from the server
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- STATE MANAGEMENT ---
# Streamlit reruns the script on every button click, so we have to remember where we are.
if 'block_index' not in st.session_state:
    st.session_state.block_index = 0
if 'revealed' not in st.session_state:
    st.session_state.revealed = False

def reveal_line():
    st.session_state.revealed = True

def next_scene():
    st.session_state.block_index += 1
    st.session_state.revealed = False

def restart():
    st.session_state.block_index = 0
    st.session_state.revealed = False

# --- UI FRONTEND ---
st.title("🎭 Interactive Script Rehearsal")
st.markdown("Upload your script, put on your headphones, and run your lines.")

# Sidebar for controls
with st.sidebar:
    st.header("Settings")
    uploaded_file = st.file_uploader("Upload Word Script (.docx)", type=["docx"])
    character_name = st.text_input("Your Character's Name", value="שפיגל")
    context_size = st.slider("Context Lines to Read", min_value=1, max_value=5, value=3)

# Main App Logic
if uploaded_file and character_name:
    # 1. Parse the script
    with st.spinner("Parsing script..."):
        blocks = parse_script(uploaded_file, character_name, context_size)
    
    if not blocks:
        st.warning(f"Could not find any lines for '{character_name}'. Check your spelling!")
        st.stop()

    # 2. Check if we reached the end
    if st.session_state.block_index >= len(blocks):
        st.success("🎉 You've reached the end of your lines! Great job!")
        st.button("Start Over", on_click=restart)
        st.stop()

    # 3. Get the current scene data
    current_block = blocks[st.session_state.block_index]
    
    # Show progress
    st.progress((st.session_state.block_index) / len(blocks), 
                text=f"Scene {st.session_state.block_index + 1} of {len(blocks)}")

    st.divider()

    # Display a jump indicator if we skipped a large chunk of text
    if current_block['jumped']:
        st.caption("... [Skipping ahead in script] ...")

    # Display Context Lines
    st.subheader("Cue (Listen):")
    context_text = ""
    for line in current_block['context']:
        st.markdown(f"> *{line}*")
        context_text += line + " "

    # Generate and display audio player
    if context_text:
        with st.spinner("Loading audio..."):
            audio_bytes = get_audio_bytes(context_text)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    else:
        st.info("No context lines before this cue. You start the scene!")

    st.divider()

    # Display User Actions
    if not st.session_state.revealed:
        st.subheader(f"It's your turn, {character_name}!")
        st.button("🗣️ Reveal My Line", on_click=reveal_line, use_container_width=True, type="primary")
    else:
        st.subheader("Your Line:")
        st.success(f"**{current_block['user_line']}**")
        st.button("⏭️ Next Scene", on_click=next_scene, use_container_width=True)

else:
    st.info("👈 Please upload a .docx script and enter your character's name in the sidebar to begin.")