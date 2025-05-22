import subprocess
import os
import shutil
import re

def sanitize_for_directory_name(name):
    """
    Sanitizes a string to be suitable for a directory name.
    Removes or replaces characters that are problematic in directory names.
    """
    name = re.sub(r'[^\w\s-]', '', name).strip() # Remove non-alphanumeric (excluding spaces, hyphens)
    name = re.sub(r'[-\s]+', '_', name) # Replace spaces and hyphens with underscores
    return name

def render_manim_script(script_path, scene_name, course_media_output_dir):
    """
    Renders a Manim script and moves the output to a specified course media directory.
    script_path: Path to the .py Manim script.
    scene_name: The name of the scene class to render.
    course_media_output_dir: Base directory for this course's rendered outputs.
    """
    if not os.path.exists(script_path):
        return {"error": f"Script file not found: {script_path}"}

    script_dir = os.path.dirname(script_path)
    original_media_dir = os.path.join(script_dir, "media") # Default Manim output relative to script

    # Define where the final output for this specific scene should go
    scene_specific_output_dir = os.path.join(course_media_output_dir, sanitize_for_directory_name(scene_name))
    os.makedirs(scene_specific_output_dir, exist_ok=True)

    # Manim command
    # Using -ql for low quality. Output is typically media/videos/<script_name_no_ext>/<quality>/<scene_name>.mp4
    # We let Manim run from the script's directory.
    command = [
        "manim",
        "-ql", # Low quality for faster rendering
        script_path,
        scene_name,
    ]

    try:
        # Run Manim from the script's directory to ensure correct relative path resolution by Manim
        process = subprocess.run(command, capture_output=True, text=True, cwd=script_dir, check=True)
        
        # Determine the expected output path from Manim
        # Manim outputs to: <script_dir>/media/videos/<script_filename_no_ext>/<quality>/<scene_name>.mp4
        script_filename_no_ext = os.path.splitext(os.path.basename(script_path))[0]
        # Manim scene names are case-sensitive.
        # The output directory for scene name might be PascalCase or as is, depending on Manim version/config.
        # Let's assume it's the same as scene_name for now.
        
        # Common output structure: media/videos/script_name/1080p60/SceneName.mp4 or 480p15 for -ql
        # We need to find the actual generated file. Let's search for .mp4 in media/videos/<script_name_no_ext>/<quality>/
        # The quality subdirectory can be '480p15' for -ql, '720p30', '1080p60' for -p, etc.
        
        expected_manim_output_video_subpath_template = os.path.join("videos", script_filename_no_ext) # e.g., videos/IntroductionToPython_manim
        
        # Search for the .mp4 file as Manim's exact output path can be tricky
        found_video_path = None
        manim_media_dir_for_script = os.path.join(original_media_dir, "videos", script_filename_no_ext)

        for quality_dir in os.listdir(manim_media_dir_for_script): # e.g., 480p15, 1080p60
            potential_path = os.path.join(manim_media_dir_for_script, quality_dir, f"{scene_name}.mp4")
            if os.path.exists(potential_path):
                found_video_path = potential_path
                break
        
        if not found_video_path:
            # Try a common alternative if scene name in path is lowercased by some Manim versions
            # (Though usually it's PascalCase as the class name)
             if os.path.exists(os.path.join(manim_media_dir_for_script, quality_dir, f"{scene_name.lower()}.mp4")):
                found_video_path = os.path.join(manim_media_dir_for_script, quality_dir, f"{scene_name.lower()}.mp4")

        if not found_video_path:
            return {"error": f"Manim output video for scene '{scene_name}' not found after rendering. Stdout: {process.stdout} Stderr: {process.stderr}", "stdout": process.stdout, "stderr": process.stderr}

        # Move the found video file to the scene_specific_output_dir
        final_video_path = os.path.join(scene_specific_output_dir, os.path.basename(found_video_path))
        shutil.move(found_video_path, final_video_path)

        # Clean up: remove the original media directory created by Manim if it's empty or only contains empty dirs
        try:
            # Remove the specific scene's output folder (e.g., media/videos/script_name/480p15/SceneName.mp4's parent quality dir)
            # This is a bit aggressive; better to remove the whole 'media' dir for that script if all scenes are processed.
            # For now, let's leave the broader media directory as other scenes from same script might exist.
            # If script_dir/media is empty, we can remove it.
            if os.path.exists(original_media_dir) and not os.listdir(original_media_dir):
                 shutil.rmtree(original_media_dir)
            elif os.path.exists(os.path.dirname(found_video_path)) and not os.listdir(os.path.dirname(found_video_path)): # remove quality dir
                 os.rmdir(os.path.dirname(found_video_path))
            if os.path.exists(os.path.dirname(os.path.dirname(found_video_path))) and not os.listdir(os.path.dirname(os.path.dirname(found_video_path))): # remove script_filename_no_ext dir
                 os.rmdir(os.path.dirname(os.path.dirname(found_video_path)))


        except OSError as e:
            # Log this, but don't fail the whole process because of cleanup issue
            print(f"Warning: Could not clean up Manim media directory {original_media_dir}: {e}")


        return {"video_path": final_video_path, "stdout": process.stdout}

    except subprocess.CalledProcessError as e:
        return {"error": f"Manim execution failed with code {e.returncode}", "stdout": e.stdout, "stderr": e.stderr, "script_path": script_path, "scene_name": scene_name}
    except FileNotFoundError: # For the subprocess.run command itself
        return {"error": "Manim command not found. Is Manim installed and in PATH?"}
    except Exception as e:
        return {"error": f"An unexpected error occurred during rendering: {e}"}

if __name__ == '__main__':
    # For direct testing of this module
    # Setup a dummy Manim script
    test_script_dir = "test_manim_files"
    os.makedirs(test_script_dir, exist_ok=True)
    test_script_path = os.path.join(test_script_dir, "test_scene_manim.py")
    
    with open(test_script_path, "w") as f:
        f.write("""from manim import *
class MyTestScene(Scene):
    def construct(self):
        text = Text("Hello Manim!")
        self.play(Write(text))
        self.wait(1)
""")

    # Define course media output directory for test
    test_course_output_dir = "test_course_media_output"
    os.makedirs(test_course_output_dir, exist_ok=True)

    print(f"Attempting to render: {test_script_path}, Scene: MyTestScene")
    result = render_manim_script(test_script_path, "MyTestScene", test_course_output_dir)

    if "error" in result:
        print(f"Error rendering Manim script: {result['error']}")
        if "stdout" in result: print(f"STDOUT: {result['stdout']}")
        if "stderr" in result: print(f"STDERR: {result['stderr']}")
    else:
        print(f"Manim script rendered successfully!")
        print(f"Video path: {result['video_path']}")
        print(f"STDOUT: {result['stdout']}")

    # Clean up (optional)
    # shutil.rmtree(test_script_dir)
    # shutil.rmtree(test_course_output_dir)
    # Manim might create media directory in test_script_dir, also clean that if needed
    # default_manim_media_output = os.path.join(test_script_dir, "media")
    # if os.path.exists(default_manim_media_output):
    # shutil.rmtree(default_manim_media_output)
