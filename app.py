import streamlit as st
import streamlit.components.v1 as components
from docx import Document
import subprocess
import os
import tempfile
import threading

# --- PAGE SETUP ---
st.set_page_config(page_title="Script Runner", page_icon="🎭", layout="centered")

# --- CORE FUNCTIONS ---
@st.cache_data(show_spinner=False)
def parse_script(file_source, practicing_character, lines_of_context):
    doc = Document(file_source)
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
def get_audio_bytes(text_to_speak, speed="+50%"):
    if not text_to_speak.strip():
        return None
        
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        temp_path = tmp.name
        
    try:
        subprocess.run([
            "edge-tts", 
            "--voice", "he-IL-AvriNeural", 
            "--rate", speed, 
            "--text", text_to_speak, 
            "--write-media", temp_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        with open(temp_path, "rb") as f:
            audio_data = f.read()
        return audio_data
        
    except Exception as e:
        print(f"Audio generation failed: {e}") 
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- STATE MANAGEMENT & CALLBACKS ---
if 'block_index' not in st.session_state:
    st.session_state.block_index = 0
if 'revealed' not in st.session_state:
    st.session_state.revealed = False

def reveal_line():
    st.session_state.revealed = True

def next_scene(total_blocks):
    if st.session_state.block_index < total_blocks - 1:
        st.session_state.block_index += 1
        st.session_state.revealed = False

def prev_scene():
    if st.session_state.block_index > 0:
        st.session_state.block_index -= 1
        st.session_state.revealed = False

def jump_to_scene():
    st.session_state.block_index = st.session_state.scene_selector - 1
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
    
    default_file = "Play.docx"
    active_file = None
    
    if uploaded_file is not None:
        active_file = uploaded_file
        st.success("Using uploaded script.")
    elif os.path.exists(default_file):
        active_file = default_file
        st.info(f"Using default script: '{default_file}'")
    
    character_name = st.text_input("Your Character's Name", value="שפיגל")
    context_size = st.slider("Context Lines to Read", min_value=1, max_value=5, value=3)
    
    st.divider()
    auto_advance = st.checkbox("🎤 Hands-Free Mode", value=True, help="Automatically turns on mic after audio finishes, and advances the scene when you stop speaking.")

# Main App Logic
if active_file and character_name:
    with st.spinner("Parsing script..."):
        blocks = parse_script(active_file, character_name, context_size)
    
    if not blocks:
        st.warning(f"Could not find any lines for '{character_name}'. Check your spelling!")
        st.stop()

    total_scenes = len(blocks)

    # --- NAVIGATION BAR ---
    st.divider()
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1.5, 1])
    
    with nav_col1:
        st.button("⏪ Previous", on_click=prev_scene, disabled=(st.session_state.block_index == 0), use_container_width=True)
        
    with nav_col2:
        scene_numbers = list(range(1, total_scenes + 1))
        st.selectbox("Jump to scene:", scene_numbers, index=st.session_state.block_index, key="scene_selector", on_change=jump_to_scene, label_visibility="collapsed")
        
    with nav_col3:
        # The JS will secretly "click" this button for you
        st.button("Next ⏩", on_click=next_scene, args=(total_scenes,), disabled=(st.session_state.block_index == total_scenes - 1), use_container_width=True)
    
    st.progress((st.session_state.block_index + 1) / total_scenes, text=f"Scene {st.session_state.block_index + 1} of {total_scenes}")
    st.divider()

    # Get the current scene data
    current_block = blocks[st.session_state.block_index]

    if current_block['jumped']:
        st.caption("... [Skipping ahead in script] ...")

    # Display Context Lines
    st.subheader("Cue (Listen):")
    context_
