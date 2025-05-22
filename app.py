from flask import Flask, render_template, request, session, send_from_directory
from modules.outline_generator import generate_outline
from modules.content_generator import generate_content_for_outline
from modules.file_saver import save_content_to_files, sanitize_filename as s_filename # Avoid conflict
from modules.manim_script_generator import generate_manim_script as generate_manim_script_func
from modules.manim_renderer import render_manim_script as render_manim_script_func, sanitize_for_directory_name # Renamed to avoid conflict
import os
import re

# Helper function from file_saver, if not imported directly
def sanitize_filename_for_app(name):
    name = re.sub(r'[^\w\s-]', '', name).strip() # Matches file_saver's sanitize_filename for course topic
    name = re.sub(r'[-\s]+', '-', name)
    return name

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management
COURSES_BASE_DIR = os.path.abspath(os.path.join(app.root_path, 'courses'))


@app.route('/')
def index():
    return render_template('index.html',
                           course_topic=session.get('course_topic'),
                           course_details=session.get('course_details'),
                           audience_level=session.get('audience_level'),
                           outline=session.get('outline'),
                           generated_content=session.get('generated_content'),
                           save_confirmation=session.get('save_confirmation'),
                           manim_scripts_generated=session.get('manim_scripts_generated'),
                           rendered_presentations_paths=session.get('rendered_presentations_paths'),
                           course_topic_sanitized=sanitize_filename_for_app(session.get('course_topic','')) if session.get('course_topic') else None,
                           manim_template_selected=session.get('manim_template_selected'))

@app.route('/submit_course_details', methods=['POST'])
def submit_course_details():
    session['course_topic'] = request.form.get('course_topic')
    session['course_details'] = request.form.get('course_details')
    session['audience_level'] = request.form.get('audience_level')
    
    outline = generate_outline(session['course_topic'], session['course_details'], session['audience_level'])
    session['outline'] = outline
    # Clear all subsequent data
    session.pop('generated_content', None) 
    session.pop('save_confirmation', None) 
    session.pop('manim_scripts_generated', None) 
    session.pop('rendered_presentations_paths', None)
    session.pop('manim_template_selected', None)
    
    return render_template('index.html',
                           course_topic=session['course_topic'],
                           course_details=session['course_details'],
                           audience_level=session['audience_level'],
                           outline=session['outline'])

@app.route('/generate_content', methods=['POST'])
def generate_content_route():
    selected_outline_items_texts = []
    i = 0
    while True:
        selected_key = f'outline_item_selected_{i}'
        text_key = f'outline_item_text_{i}'
        if text_key in request.form: 
             selected_outline_items_texts.append(request.form.get(text_key))
        else:
            break
        i += 1
    
    session['course_topic'] = request.form.get('course_topic')
    session['course_details'] = request.form.get('course_details')
    session['audience_level'] = request.form.get('audience_level')

    if selected_outline_items_texts:
        generated_content = generate_content_for_outline(selected_outline_items_texts)
        session['generated_content'] = generated_content
    else:
        session.pop('generated_content', None)
    # Clear subsequent data
    session.pop('save_confirmation', None) 
    session.pop('manim_scripts_generated', None) 
    session.pop('rendered_presentations_paths', None)
    session.pop('manim_template_selected', None)


    return render_template('index.html',
                           course_topic=session.get('course_topic'),
                           course_details=session.get('course_details'),
                           audience_level=session.get('audience_level'),
                           outline=session.get('outline'),
                           generated_content=session.get('generated_content'))

@app.route('/save_content', methods=['POST'])
def save_content_route():
    course_topic = session.get('course_topic')
    generated_content = session.get('generated_content')
    # Clear subsequent data
    session.pop('manim_scripts_generated', None) 
    session.pop('rendered_presentations_paths', None)
    session.pop('manim_template_selected', None)


    if not course_topic or not generated_content:
        session['save_confirmation'] = {"message": "Error: Course topic or content missing."}
    else:
        # Update generated_content from textareas before saving
        updated_content = {}
        for chapter_title_key in generated_content.keys(): # Use original keys to find corresponding textareas
            # Ensure chapter_title_key is sanitized consistently with how textarea names are generated in HTML
            # The HTML uses: chapter|replace(' ', '_')|replace('-', '_')|replace('.', '_')|replace(':', '_')
            # s_filename from file_saver is: re.sub(r'[^\w\s-]', '', name).strip(); re.sub(r'[-\s]+', '-', name)
            # This is not the same. We need a consistent sanitization for textarea names.
            # Let's assume the HTML part `{{ chapter|replace(' ', '_')|replace('-', '_')|replace('.', '_')|replace(':', '_') }}` is what we need to match.
            
            # For simplicity, let's make s_filename in app.py match the template's textarea naming more closely for this specific purpose.
            # This is a bit of a hack. A better solution would be a dedicated sanitizer for HTML element names/ids.
            
            # Correct approach: use a consistent key. The generated_content keys are the original chapter titles.
            # HTML form names should be generated from these original titles in a reversible or consistently reproducible way.
            # The current HTML filter `chapter|replace(' ', '_')|replace('-', '_')|replace('.', '_')|replace(':', '_')` is one way.
            # Let's try to replicate that sanitization here for lookup.
            
            sanitized_key_for_form = chapter_title_key.replace(' ', '_').replace('-', '_').replace('.', '_').replace(':', '_')
            textarea_name = f"content_{sanitized_key_for_form}"
            
            updated_content[chapter_title_key] = request.form.get(textarea_name, generated_content[chapter_title_key])
        session['generated_content'] = updated_content # Update session with edited content

        save_result = save_content_to_files(course_topic, updated_content)
        session['save_confirmation'] = save_result

    return render_template('index.html',
                           course_topic=session.get('course_topic'),
                           course_details=session.get('course_details'),
                           audience_level=session.get('audience_level'),
                           outline=session.get('outline'),
                           generated_content=session.get('generated_content'),
                           save_confirmation=session.get('save_confirmation'))

@app.route('/generate_slides', methods=['POST'])
def generate_slides_route():
    course_topic = session.get('course_topic')
    save_confirmation = session.get('save_confirmation')
    selected_template = request.form.get('manim_template', 'SimpleTitleContent') # Get selected template
    session['manim_template_selected'] = selected_template # Store in session for sticky selection

    session.pop('rendered_presentations_paths', None) # Clear subsequent data

    if not course_topic or not save_confirmation or 'file_paths' not in save_confirmation:
        session['manim_scripts_generated'] = {"error": "Course topic or saved content files missing."}
    else:
        course_base_dir = save_confirmation.get('course_directory', 'courses/' + sanitize_filename_for_app(course_topic))
        manim_scripts_dir = os.path.join(course_base_dir, "manim_scripts")
        os.makedirs(manim_scripts_dir, exist_ok=True)
        
        generated_script_info = []
        for md_file_path in save_confirmation['file_paths']:
            chapter_filename = os.path.basename(md_file_path)
            chapter_title = os.path.splitext(chapter_filename)[0].replace('_', ' ').replace('-', ' ')
            sanitized_chapter_for_script = sanitize_filename_for_app(chapter_title) 
            script_filename = f"{sanitized_chapter_for_script}_{selected_template}_manim.py" # Add template to filename
            output_script_path = os.path.join(manim_scripts_dir, script_filename)
            
            # Pass the selected_template to the script generator
            result = generate_manim_script_func(chapter_title, md_file_path, output_script_path, template_name=selected_template)
            generated_script_info.append(result)
        
        session['manim_scripts_generated'] = {"scripts": generated_script_info, "directory": manim_scripts_dir, "course_base_dir": course_base_dir}

    return render_template('index.html',
                           course_topic=session.get('course_topic'),
                           course_details=session.get('course_details'),
                           audience_level=session.get('audience_level'),
                           outline=session.get('outline'),
                           generated_content=session.get('generated_content'),
                           save_confirmation=session.get('save_confirmation'),
                           manim_scripts_generated=session.get('manim_scripts_generated'),
                           manim_template_selected=session.get('manim_template_selected'))


@app.route('/render_presentations', methods=['POST'])
def render_presentations_route():
    manim_scripts_info = session.get('manim_scripts_generated')
    course_topic = session.get('course_topic') 

    if not manim_scripts_info or 'scripts' not in manim_scripts_info or not course_topic:
        session['rendered_presentations_paths'] = {"error": "Manim script details or course topic not found in session."}
    else:
        course_base_dir = manim_scripts_info.get('course_base_dir')
        if not course_base_dir:
            save_conf = session.get('save_confirmation')
            if save_conf and 'course_directory' in save_conf: # This is an absolute path from file_saver
                course_base_dir = save_conf['course_directory']
            else: 
                # Construct path relative to app.root_path/courses if all else fails
                course_base_dir = os.path.join(COURSES_BASE_DIR, sanitize_filename_for_app(course_topic))
        
        # Ensure course_media_output_dir is an absolute path for send_from_directory
        # The render_manim_script_func expects an absolute path for course_media_output_dir
        # and it creates 'rendered_presentations' inside it.
        # So, course_media_output_dir for rendering should be: os.path.join(course_base_dir, "rendered_presentations")
        # And this is what's stored in session['rendered_presentations_paths']['output_directory']

        # For serving, we need path relative to COURSES_BASE_DIR.
        # session['rendered_presentations_paths']['output_directory'] should already be absolute.
        # Let's ensure it for clarity.
        course_media_output_dir_abs = os.path.join(course_base_dir, "rendered_presentations")
        os.makedirs(course_media_output_dir_abs, exist_ok=True)


        render_results = []
        for script_detail in manim_scripts_info['scripts']:
            if 'script_path' in script_detail and 'scene_name' in script_detail:
                script_path = script_detail['script_path'] # This should be absolute or resolvable by Manim
                scene_name = script_detail['scene_name']
                
                render_result = render_manim_script_func(script_path, scene_name, course_media_output_dir_abs)
                render_results.append(render_result)
            elif 'error' in script_detail:
                render_results.append({"error": f"Skipping render due to script generation error: {script_detail['error']}"})
            else:
                render_results.append({"error": "Invalid script detail."})
        
        session['rendered_presentations_paths'] = {"results": render_results, "output_directory_abs": course_media_output_dir_abs}

    return render_template('index.html',
                           course_topic=session.get('course_topic'),
                           course_details=session.get('course_details'),
                           audience_level=session.get('audience_level'),
                           outline=session.get('outline'),
                           generated_content=session.get('generated_content'),
                           save_confirmation=session.get('save_confirmation'),
                           manim_scripts_generated=session.get('manim_scripts_generated'),
                           rendered_presentations_paths=session.get('rendered_presentations_paths'),
                           course_topic_sanitized=sanitize_filename_for_app(session.get('course_topic','')) if session.get('course_topic') else None)

# New route to serve videos
@app.route('/serve_video/<path:course_name_sanitized>/<path:scene_dir_name>/<path:filename>')
def serve_video(course_name_sanitized, scene_dir_name, filename):
    # course_name_sanitized is from sanitize_filename_for_app (allows hyphens)
    # scene_dir_name is from sanitize_for_directory_name (uses underscores)
    # Construct path relative to COURSES_BASE_DIR
    # Video path structure: COURSES_BASE_DIR/course_name_sanitized/rendered_presentations/scene_dir_name/filename.mp4
    directory = os.path.join(COURSES_BASE_DIR, course_name_sanitized, "rendered_presentations", scene_dir_name)
    try:
        return send_from_directory(directory, filename, as_attachment=False)
    except FileNotFoundError:
        from flask import abort
        abort(404, description="Video file not found.")


if __name__ == '__main__':
    # Ensure COURSES_BASE_DIR exists when running directly (though file_saver and renderer should create subdirs)
    if not os.path.exists(COURSES_BASE_DIR):
        os.makedirs(COURSES_BASE_DIR)
    app.run(debug=True)
