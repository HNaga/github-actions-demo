import streamlit as st
import config # Import the new config file
from modules.llm_integration import (
    generate_course_outline, 
    generate_chapter_content, 
    generate_voiceover_script, 
    generate_html_slides
)
from modules.tts_module import generate_audio_gtts # Import for Step 5
import os
import io # Ensure io is fully available, BytesIO was specifically imported before
import zipfile # Import for Step 6

# --- Application Configuration ---
WORKFLOW_STEPS = [
    "Course Definition", 
    "Outline Generation", 
    "Content Generation", 
    "Slides Generation", 
    "Voiceover Generation", 
    "Review & Download"
]

# --- Initialize Session State ---
def initialize_session_state():
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'tts_engine': config.DEFAULT_TTS_ENGINE,
            'openai_api_key': config.DEFAULT_OPENAI_API_KEY,
            'elevenlabs_api_key': config.DEFAULT_ELEVENLABS_API_KEY,
            'google_cloud_tts_api_key': config.DEFAULT_GOOGLE_CLOUD_TTS_API_KEY,
        }
    
    if 'current_step_index' not in st.session_state:
        st.session_state.current_step_index = 0
        st.session_state.course_topic = ""
        st.session_state.course_details = ""
        st.session_state.audience_level = "Beginner" # Default
        st.session_state.outline = [] # List of dicts: {"id": int, "title": str, "edited_title": str, "content": str, "voiceover_script": str, "html_slides": str, "audio_bytes": None, "audio_filename": None}
        st.session_state.completed_steps = [False] * len(WORKFLOW_STEPS) 
        st.session_state.next_outline_item_id = 0 
        st.session_state.downloadable_zip = None # For Step 6
        st.session_state.zip_filename = "" # For Step 6

initialize_session_state()


# --- Sidebar for Settings ---
st.sidebar.header("⚙️ Application Settings")

# TTS Engine Selection
# The widget's value will be directly available via st.session_state.tts_engine_select
# Encapsulate settings UI in a function for clarity
def display_settings_sidebar():
    st.sidebar.selectbox(
        "TTS Engine",
        options=config.AVAILABLE_TTS_ENGINES,
        key="tts_engine_select", 
        index=config.AVAILABLE_TTS_ENGINES.index(st.session_state.settings.get('tts_engine', config.DEFAULT_TTS_ENGINE))
    )
    st.sidebar.text_input(
        "OpenAI API Key", 
        type="password", 
        key="openai_api_key_input",
        value=st.session_state.settings.get('openai_api_key', '')
    )
    st.sidebar.text_input(
        "ElevenLabs API Key", 
        type="password", 
        key="elevenlabs_api_key_input",
        value=st.session_state.settings.get('elevenlabs_api_key', '')
    )
    st.sidebar.text_input(
        "Google Cloud TTS API Key", 
        type="password", 
        key="google_cloud_tts_api_key_input",
        value=st.session_state.settings.get('google_cloud_tts_api_key', '')
    )

    if st.sidebar.button("Apply Settings"):
        st.session_state.settings['tts_engine'] = st.session_state.tts_engine_select
        st.session_state.settings['openai_api_key'] = st.session_state.openai_api_key_input
        st.session_state.settings['elevenlabs_api_key'] = st.session_state.elevenlabs_api_key_input
        st.session_state.settings['google_cloud_tts_api_key'] = st.session_state.google_cloud_tts_api_key_input
        st.sidebar.success("Settings applied!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Current Effective Settings:")
    st.sidebar.write(f"TTS Engine: `{st.session_state.settings['tts_engine']}`")
    st.sidebar.write(f"OpenAI Key: `{'Set' if st.session_state.settings.get('openai_api_key') else 'Not Set'}`")
    st.sidebar.write(f"ElevenLabs Key: `{'Set' if st.session_state.settings.get('elevenlabs_api_key') else 'Not Set'}`")
    st.sidebar.write(f"Google Cloud TTS Key: `{'Set' if st.session_state.settings.get('google_cloud_tts_api_key') else 'Not Set'}`")

display_settings_sidebar()


# --- Main Area ---
st.title("🎙️ AI Course Generator 🎙️")

# --- Global Progress Stepper ---
# The radio button's value will be the selected step name. We need to find its index.
# Using a callback to update current_step_index when the radio button changes.
def update_step_from_stepper():
    try:
        st.session_state.current_step_index = WORKFLOW_STEPS.index(st.session_state.workflow_stepper)
    except ValueError: # Should not happen if options are from WORKFLOW_STEPS
        st.session_state.current_step_index = 0

selected_step_name = st.radio(
    "Current Stage:", 
    options=WORKFLOW_STEPS, 
    index=st.session_state.current_step_index, 
    horizontal=True, 
    key="workflow_stepper",
    on_change=update_step_from_stepper 
    # Note: Direct interaction with radio to navigate might be tricky if steps have prerequisites.
    # For now, this allows direct navigation. Later, we might disable future steps
    # or use Next/Prev buttons.
)

st.markdown("---") # Visual separator

# --- UI for Current Step ---
current_step_name = WORKFLOW_STEPS[st.session_state.current_step_index]

if current_step_name == "Course Definition":
    st.header("Step 1: Define Your Course")
    
    # Use st.session_state directly for widget values to ensure they persist
    # Input widgets will automatically update the session state attributes due to their 'key'
    st.text_input(
        "Course Topic", 
        key="course_topic", # Direct binding to st.session_state.course_topic
        placeholder="e.g., Introduction to Python Programming"
    )
    st.text_area(
        "Course Details/Goals", 
        key="course_details", # Direct binding
        height=150, 
        placeholder="e.g., Learn basic Python syntax, data types, and control flow..."
    )
    
    audience_options = ["Beginner", "Intermediate", "Advanced"]
    # Ensure audience_level is initialized correctly before selectbox uses it
    if 'audience_level' not in st.session_state or st.session_state.audience_level not in audience_options:
        st.session_state.audience_level = audience_options[0] 
        
    st.selectbox(
        "Target Audience", 
        options=audience_options, 
        key="audience_level" # Direct binding
    )

    if st.button("Save & Proceed to Outline Generation", key="save_course_definition"):
        if not st.session_state.course_topic or not st.session_state.course_details:
            st.error("Please provide both Course Topic and Course Details.")
        else:
            # Values are already up-to-date in st.session_state due to direct key binding
            st.session_state.completed_steps[0] = True
            if st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1:
                st.session_state.current_step_index += 1
            st.success("Course definition saved!")
            st.experimental_rerun() # Rerun to reflect the new step and update stepper

elif current_step_name == "Outline Generation":
    st.header("Step 2: Outline Generation")

    if st.button("Generate Course Outline", key="generate_outline_button"):
        if not st.session_state.course_topic: # Basic check
            st.error("Please define the course topic in Step 1 first.")
        else:
            with st.spinner("Generating outline..."):
                generated_outline_list = generate_course_outline(
                    st.session_state.course_topic, 
                    st.session_state.course_details, 
                    st.session_state.audience_level
                )
                st.session_state.outline = [] # Clear previous outline
                for i, title in enumerate(generated_outline_list):
                    st.session_state.outline.append({
                        "id": st.session_state.next_outline_item_id, 
                        "title": title, 
                        "edited_title": title
                    })
                    st.session_state.next_outline_item_id += 1
                st.session_state.completed_steps[1] = True
            st.success("Outline generated successfully!")

    if st.session_state.outline:
        st.subheader("Generated Outline (Editable)")
        
        # Create a list of items to iterate over, to allow safe deletion
        items_to_display = list(st.session_state.outline)

        for i, item in enumerate(items_to_display):
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                new_title = st.text_input(
                    label=f"Chapter {i+1}", 
                    value=item['edited_title'], 
                    key=f"outline_item_edit_{item['id']}" # Unique key for editing
                )
                # Update immediately if changed - Streamlit's text_input updates session_state on enter/blur
                # Find the item in original list and update
                for outline_item in st.session_state.outline:
                    if outline_item['id'] == item['id']:
                        outline_item['edited_title'] = st.session_state[f"outline_item_edit_{item['id']}"] # Use the key of the text_input
                        break
            with col2:
                st.markdown("<br/>", unsafe_allow_html=True) # Align button a bit
                if st.button(f"❌", key=f"delete_outline_{item['id']}"):
                    st.session_state.outline = [o for o in st.session_state.outline if o['id'] != item['id']]
                    st.experimental_rerun()

        if st.button("Add New Chapter", key="add_chapter"):
            new_id = st.session_state.next_outline_item_id
            st.session_state.outline.append({
                "id": new_id,
                "title": "New Chapter (Edit Me)",
                "edited_title": "New Chapter (Edit Me)",
                "content": "", 
                "voiceover_script": "",
                "html_slides": "",
                "audio_bytes": None, # Initialize audio_bytes
                "audio_filename": None # Initialize audio_filename
            })
            st.session_state.next_outline_item_id += 1
            st.experimental_rerun()
        
    # Navigation
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("<< Back to Course Definition", key="back_to_def_outline"): 
            if st.session_state.current_step_index > 0:
                st.session_state.current_step_index -= 1
                st.experimental_rerun()
    with col_nav2:
        if st.button("Proceed to Content Generation >>", key="to_content_gen_outline"): 
            if not st.session_state.outline:
                st.error("Please generate an outline first.")
            elif st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1:
                st.session_state.completed_steps[1] = True 
                st.session_state.current_step_index += 1
                st.experimental_rerun()

elif current_step_name == "Content Generation":
    st.header("Step 3: Content & Voiceover Script Generation")

    if not st.session_state.outline:
        st.warning("No outline available. Please generate an outline in Step 2.")
    else:
        if st.button("Generate All Chapter Content & Scripts", key="generate_all_content_button"):
            all_content_generated = True
            for i, item in enumerate(st.session_state.outline):
                with st.spinner(f"Generating content for: {item['edited_title']}... (Chapter {i+1}/{len(st.session_state.outline)})"):
                    try:
                        content = generate_chapter_content(
                            item['edited_title'], 
                            st.session_state.course_topic, 
                            st.session_state.course_details, 
                            st.session_state.audience_level
                        )
                        script = generate_voiceover_script(content)
                        item['content'] = content
                        item['voiceover_script'] = script
                    except Exception as e:
                        st.error(f"Error generating content for '{item['edited_title']}': {e}")
                        item['content'] = item.get('content', "") 
                        item['voiceover_script'] = item.get('voiceover_script', "")
                        all_content_generated = False
            
            if all_content_generated:
                st.session_state.completed_steps[2] = True
                st.success("All chapter content and voiceover scripts generated!")
            else:
                st.warning("Some content or scripts could not be generated. Please review errors.")

        st.subheader("Review and Edit Content & Scripts")
        for i, item in enumerate(st.session_state.outline):
            with st.expander(f"Chapter: {item['edited_title']}", expanded=False):
                st.markdown("#### Chapter Content:")
                content_key = f"content_edit_{item['id']}"
                if content_key not in st.session_state:
                    st.session_state[content_key] = item.get('content', '')
                st.text_area(
                    "Edit Content", 
                    value=st.session_state[content_key], 
                    height=300, 
                    key=content_key, 
                    on_change=lambda item_id=item['id'], key=content_key: setattr(next(i for i in st.session_state.outline if i['id'] == item_id), 'content', st.session_state[key])
                )
                st.markdown("#### Voiceover Script:")
                script_key = f"script_edit_{item['id']}"
                if script_key not in st.session_state:
                    st.session_state[script_key] = item.get('voiceover_script', '')
                st.text_area(
                    "Edit Script", 
                    value=st.session_state[script_key], 
                    height=150, 
                    key=script_key,
                    on_change=lambda item_id=item['id'], key=script_key: setattr(next(i for i in st.session_state.outline if i['id'] == item_id), 'voiceover_script', st.session_state[key])
                )
    # Navigation
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("<< Back to Outline Generation", key="back_to_outline_content"): 
            if st.session_state.current_step_index > 0:
                st.session_state.current_step_index -= 1
                st.experimental_rerun()
    with col_nav2:
        if st.button("Proceed to Slides Generation >>", key="to_slides_gen_content"): 
            all_content_present = all(item.get('content') for item in st.session_state.outline)
            if not all_content_present and st.session_state.outline: 
                 st.warning("Not all chapters have content. Proceeding anyway.")
            if st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1:
                st.session_state.completed_steps[2] = True 
                st.session_state.current_step_index += 1
                st.experimental_rerun()

elif current_step_name == "Slides Generation":
    st.header("Step 4: HTML Slides Generation")

    if not st.session_state.outline:
        st.warning("No outline available. Please generate an outline (Step 2) and content (Step 3) first.")
    else:
        if st.button("Generate HTML Slides for All Chapters", key="generate_all_slides_button"):
            all_slides_generated = True
            for i, item in enumerate(st.session_state.outline):
                if item.get('content'):
                    with st.spinner(f"Generating HTML slides for: {item['edited_title']}... (Chapter {i+1}/{len(st.session_state.outline)})"):
                        try:
                            html_output = generate_html_slides(item['edited_title'], item['content'])
                            item['html_slides'] = html_output
                        except Exception as e:
                            st.error(f"Error generating slides for '{item['edited_title']}': {e}")
                            item['html_slides'] = "<p>Error generating slides.</p>"
                            all_slides_generated = False
                else:
                    item['html_slides'] = "<p>Content not available to generate slides.</p>"
            
            if all_slides_generated:
                st.session_state.completed_steps[3] = True 
                st.success("HTML slides generated for all chapters!")
            else:
                st.warning("Some slides could not be generated or content was missing. Please review.")


        st.subheader("Review Generated HTML Slides")
        for i, item in enumerate(st.session_state.outline):
            with st.expander(f"Slides for: {item['edited_title']}", expanded=False):
                st.subheader("Generated HTML Slides:")
                if item.get('html_slides'):
                    st.markdown(item['html_slides'], unsafe_allow_html=True)
                    html_edit_key = f"html_edit_{item['id']}"
                    if html_edit_key not in st.session_state: 
                        st.session_state[html_edit_key] = item.get('html_slides', '')
                    st.text_area(
                        "Edit HTML (Advanced)", 
                        value=st.session_state[html_edit_key], 
                        height=200, 
                        key=html_edit_key,
                        on_change=lambda item_id=item['id'], key=html_edit_key: setattr(next(i for i in st.session_state.outline if i['id'] == item_id), 'html_slides', st.session_state[key])
                    )
                else:
                    st.warning("Slides not generated yet for this chapter.")
    
    # Navigation
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("<< Back to Content Generation", key="back_to_content_slides"): 
            if st.session_state.current_step_index > 0:
                st.session_state.current_step_index -= 1
                st.experimental_rerun()
    with col_nav2:
        if st.button("Proceed to Voiceover Generation >>", key="to_voiceover_gen_slides"): 
            all_slides_present = all(item.get('html_slides') and not item.get('html_slides', '').startswith("<p>Content not available") and not item.get('html_slides', '').startswith("<p>Error generating slides") for item in st.session_state.outline)
            if not all_slides_present and st.session_state.outline:
                 st.warning("Not all chapters have successfully generated slides. Proceeding anyway.")

            if st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1:
                st.session_state.completed_steps[3] = True 
                st.session_state.current_step_index += 1
                st.experimental_rerun()

elif current_step_name == "Voiceover Generation":
    st.header("Step 5: Voiceover Generation")

    if not st.session_state.outline:
        st.warning("No outline available. Please complete previous steps first.")
    else:
        if st.button("Generate Voiceovers for All Chapters (using gTTS)", key="generate_all_voiceovers_button"):
            # Sanitizing course topic for directory name
            course_title_sanitized = "".join(c if c.isalnum() else "_" for c in st.session_state.course_topic)
            # Note: The instruction to create audio_output_dir and save files is commented out
            # as we are storing bytes directly in session state for st.audio.
            # audio_output_dir = os.path.join("outputs", course_title_sanitized, "audio")
            # os.makedirs(audio_output_dir, exist_ok=True)
            
            all_audio_generated = True
            for i, item in enumerate(st.session_state.outline):
                if item.get('voiceover_script'):
                    with st.spinner(f"Generating voiceover for: {item['edited_title']}... (Chapter {i+1}/{len(st.session_state.outline)})"):
                        try:
                            audio_data = generate_audio_gtts(item['voiceover_script'])
                            if audio_data:
                                item['audio_bytes'] = audio_data
                                item['audio_filename'] = f"{''.join(c if c.isalnum() else '_' for c in item['edited_title'])}.mp3"
                                # output_path = os.path.join(audio_output_dir, item['audio_filename'])
                                # with open(output_path, 'wb') as f:
                                #     f.write(audio_data)
                                # item['audio_path'] = output_path # If we were saving to file
                            else:
                                item['audio_bytes'] = None
                                st.error(f"Failed to generate audio for {item['edited_title']}")
                                all_audio_generated = False
                        except Exception as e:
                            st.error(f"Exception generating audio for '{item['edited_title']}': {e}")
                            item['audio_bytes'] = None
                            all_audio_generated = False
                else:
                    item['audio_bytes'] = None
                    st.warning(f"No voiceover script for {item['edited_title']} to generate audio.")
                    # all_audio_generated = False # Decide if missing script is a failure for "all generated" status
            
            if all_audio_generated:
                st.session_state.completed_steps[4] = True # Index 4 for Voiceover Generation
                st.success("Voiceovers generated for all chapters!")
            else:
                st.warning("Some voiceovers could not be generated or scripts were missing.")

        st.subheader("Listen to Generated Voiceovers")
        if not st.session_state.outline: # Should be caught by outer if, but good practice
            st.info("Generate outline first.")
        else:
            for i, item in enumerate(st.session_state.outline):
                with st.expander(f"Voiceover for: {item['edited_title']}", expanded=False):
                    if item.get('audio_bytes'):
                        st.audio(item['audio_bytes'], format="audio/mp3")
                    else:
                        st.warning("Voiceover not generated yet or failed for this chapter.")
    
    # Navigation
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("<< Back to Slides Generation", key="back_to_slides_voiceover"): 
            if st.session_state.current_step_index > 0:
                st.session_state.current_step_index -= 1
                st.experimental_rerun()
    with col_nav2:
        if st.button("Proceed to Review & Download >>", key="to_review_voiceover"): 
            all_audio_present = all(item.get('audio_bytes') for item in st.session_state.outline)
            if not all_audio_present and st.session_state.outline:
                 st.warning("Not all chapters have successfully generated voiceovers. Proceeding anyway.")

            if st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1:
                st.session_state.completed_steps[4] = True 
                st.session_state.current_step_index += 1
                st.experimental_rerun()

elif current_step_name == "Review & Download":
    st.header("Step 6: Review Presentation & Download Course Package")

    # Presentation Experience Section
    st.subheader("Review Chapter Presentations")
    
    chapters_for_review = [item['edited_title'] for item in st.session_state.outline if item.get('html_slides') and item.get('audio_bytes')]
    
    if not chapters_for_review:
        st.warning("No chapters fully ready for presentation review (missing slides or audio). Please generate slides and voiceovers in previous steps.")
    else:
        selected_chapter_title = st.selectbox("Select Chapter to Review", options=chapters_for_review, key="review_chapter_select")
        selected_chapter_item = next((item for item in st.session_state.outline if item['edited_title'] == selected_chapter_title), None)

        if selected_chapter_item:
            st.markdown("---")
            st.subheader(f"Now Viewing: {selected_chapter_item['edited_title']}")
            
            st.markdown("#### Slides:")
            st.markdown(selected_chapter_item['html_slides'], unsafe_allow_html=True)
            
            st.markdown("#### Voiceover:")
            st.audio(selected_chapter_item['audio_bytes'], format="audio/mp3")
            st.markdown("---")

    # Download Package Section
    st.subheader("Download Full Course Package")
    if st.button("Prepare and Download Course ZIP", key="prepare_download_button"):
        if not st.session_state.course_topic:
            st.error("Course topic is missing. Cannot prepare package.")
        elif not st.session_state.outline:
            st.error("No course outline available. Cannot prepare package.")
        else:
            with st.spinner("Preparing course package..."):
                course_title_sanitized = "".join(c if c.isalnum() else "_" for c in st.session_state.course_topic)
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    # Add Outline File
                    outline_content = f"# Course Outline: {st.session_state.course_topic}\n\n"
                    for i, item in enumerate(st.session_state.outline):
                        outline_content += f"{i+1}. {item['edited_title']}\n"
                    zip_file.writestr(f"{course_title_sanitized}/Course_Outline.md", outline_content)

                    # Add Chapter Files
                    for item in st.session_state.outline:
                        chapter_title_sanitized = "".join(c if c.isalnum() else "_" for c in item['edited_title'])
                        # Using item['id'] for a more stable folder name than loop index `i`
                        chapter_base_path = f"{course_title_sanitized}/Chapter_{str(item['id']).zfill(2)}_{chapter_title_sanitized}"
                        
                        if item.get('content'):
                            zip_file.writestr(f"{chapter_base_path}/Chapter_Content.md", item['content'])
                        if item.get('voiceover_script'):
                            zip_file.writestr(f"{chapter_base_path}/Voiceover_Script.txt", item['voiceover_script'])
                        if item.get('html_slides'):
                            zip_file.writestr(f"{chapter_base_path}/Slides.html", item['html_slides'])
                        if item.get('audio_bytes') and item.get('audio_filename'):
                            zip_file.writestr(f"{chapter_base_path}/{item['audio_filename']}", item['audio_bytes'])
                
                zip_buffer.seek(0)
                st.session_state.downloadable_zip = zip_buffer.getvalue()
                st.session_state.zip_filename = f"{course_title_sanitized}_Course_Package.zip"
                st.session_state.completed_steps[5] = True # Mark step as complete
                st.success("Course package prepared!")
                # No rerun needed here, download button will appear due to state change

    if st.session_state.get("downloadable_zip"):
        st.download_button(
            label="Download ZIP", 
            data=st.session_state.downloadable_zip, 
            file_name=st.session_state.zip_filename, 
            mime="application/zip",
            key="download_zip_button"
        )

    # Navigation
    if st.button("<< Back to Voiceover Generation", key="back_to_voiceover_review"): 
        if st.session_state.current_step_index > 0:
            st.session_state.current_step_index -= 1
            # Clear zip from session if user goes back
            st.session_state.downloadable_zip = None
            st.session_state.zip_filename = ""
            st.experimental_rerun()
    
    if st.button("🎉 Finish & Start Over", key="finish_start_over"):
        # Reset relevant parts of session state to start fresh
        st.session_state.current_step_index = 0
        st.session_state.course_topic = ""
        st.session_state.course_details = ""
        st.session_state.audience_level = "Beginner"
        st.session_state.outline = []
        st.session_state.completed_steps = [False] * len(WORKFLOW_STEPS)
        st.session_state.next_outline_item_id = 0
        st.session_state.downloadable_zip = None
        st.session_state.zip_filename = ""
        st.success("Workflow reset. Ready to start a new course!")
        st.experimental_rerun()


# Placeholder for other steps (should not be reached if Review & Download is the last step)
else:
    st.header(f"Placeholder for: {current_step_name}") # Should ideally not be shown if logic is correct
    st.write(f"This is step {st.session_state.current_step_index + 1} of {len(WORKFLOW_STEPS)}.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("<< Previous Step") and st.session_state.current_step_index > 0: # Generic prev
            st.session_state.current_step_index -= 1
            st.experimental_rerun()
    with col2:
        if st.button("Next Step >>") and st.session_state.current_step_index < len(WORKFLOW_STEPS) - 1: # Generic next
            st.session_state.current_step_index += 1
            st.experimental_rerun()

# Debugging: Display current session state
# st.sidebar.markdown("---")
# st.sidebar.subheader("Debug: Full Session State")
# st.sidebar.json(st.session_state)
