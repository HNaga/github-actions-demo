import os
import re

def to_pascal_case(text):
    """Converts a string to PascalCase."""
    return ''.join(word.capitalize() for word in re.split(r'[\s_-]+', text))

# --- Manim Slide Template Definitions ---

def template_simple_title_content(scene_class_name, chapter_title, chapter_content):
    """
    Template: Title at top, content block below.
    Content is truncated for display.
    """
    content_lines = chapter_content.splitlines()
    display_content = "\\n".join([line.replace('"', '\\"').replace("'", "\\'")[:70] for line in content_lines[:4]]) # Max 4 lines, 70 chars

    script_string = f"""from manim import *

class {scene_class_name}(Scene):
    def construct(self):
        title = Text("{chapter_title}", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        if "{display_content}".strip():
            content_mobject = Text("{display_content}", font_size=24, line_spacing=0.8)
            content_mobject.next_to(title, DOWN, buff=0.5)
            self.play(FadeIn(content_mobject, shift=UP))
            self.wait(3)
            self.play(FadeOut(title), FadeOut(content_mobject))
        else:
            self.wait(3) # Wait if no content, then fade title
            self.play(FadeOut(title))
        self.wait(1)
"""
    return script_string

def template_title_with_bullet_points(scene_class_name, chapter_title, chapter_content):
    """
    Template: Title at top, content formatted as bullet points.
    Uses first few lines of content as bullet points.
    """
    content_lines = chapter_content.splitlines()
    bullet_points = [line.replace('"', '\\"').replace("'", "\\'")[:60] for line in content_lines if line.strip() and not line.startswith("#")] # Max 60 chars per bullet
    
    # Limit to 5 bullet points for simplicity
    bullet_points = bullet_points[:5]

    # Manim's BulletedList requires items as strings
    bullet_items_str = ", ".join([f'"{bp}"' for bp in bullet_points]) if bullet_points else ""

    script_string = f"""from manim import *

class {scene_class_name}(Scene):
    def construct(self):
        title = Text("{chapter_title}", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        if [{bullet_items_str}]: # Check if there are any bullet points
            bullets = BulletedList({bullet_items_str}, font_size=28, line_spacing=0.7)
            bullets.next_to(title, DOWN, buff=0.5).align_to(title, LEFT)
            self.play(Write(bullets))
            self.wait(3)
            self.play(FadeOut(title), FadeOut(bullets))
        else:
            self.wait(3) # Wait if no content, then fade title
            self.play(FadeOut(title))
        self.wait(1)
"""
    return script_string

def template_two_column(scene_class_name, chapter_title, chapter_content):
    """
    Template: Title at top, content split into two conceptual columns.
    Splits content lines approximately in half for two columns.
    """
    content_lines = [line.replace('"', '\\"').replace("'", "\\'")[:50] for line in chapter_content.splitlines() if line.strip()] # Max 50 chars per line
    
    mid_point = (len(content_lines) + 1) // 2
    col1_lines = content_lines[:mid_point]
    col2_lines = content_lines[mid_point:]

    # Limit to 3 lines per column for simplicity
    col1_display = "\\n".join(col1_lines[:3])
    col2_display = "\\n".join(col2_lines[:3])

    script_string = f"""from manim import *

class {scene_class_name}(Scene):
    def construct(self):
        title = Text("{chapter_title}", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        col1_text_str = "{col1_display}"
        col2_text_str = "{col2_display}"
        
        elements_to_fade = [title]

        if col1_text_str.strip():
            col1_mobject = Text(col1_text_str, font_size=22, line_spacing=0.7)
            col1_mobject.next_to(title, DOWN, buff=0.5).to_edge(LEFT, buff=0.5)
            self.play(FadeIn(col1_mobject, shift=UP))
            elements_to_fade.append(col1_mobject)
            self.wait(1.5)

        if col2_text_str.strip():
            col2_mobject = Text(col2_text_str, font_size=22, line_spacing=0.7)
            if 'col1_mobject' in locals(): # if col1 exists, position next to it
                col2_mobject.next_to(col1_mobject, RIGHT, buff=0.75, aligned_edge=UP)
            else: # if col1 does not exist, position relative to title and centered
                col2_mobject.next_to(title, DOWN, buff=0.5).to_edge(RIGHT, buff=0.5)
            self.play(FadeIn(col2_mobject, shift=UP))
            elements_to_fade.append(col2_mobject)
            self.wait(1.5)
        
        if len(elements_to_fade) == 1: # Only title exists
            self.wait(3) # Wait if no content
            
        self.play(*[FadeOut(el) for el in elements_to_fade])
        self.wait(1)
"""
    return script_string

# --- Main Script Generation Function ---

MANIM_TEMPLATES = {
    "SimpleTitleContent": template_simple_title_content,
    "TitleWithBulletPoints": template_title_with_bullet_points,
    "TwoColumn": template_two_column,
}

def generate_manim_script(chapter_title, chapter_content_file_path, output_script_path, template_name="SimpleTitleContent"):
    """
    Generates a Manim script for a given chapter using a specified template.
    """
    try:
        with open(chapter_content_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Content file not found: {chapter_content_file_path}"}
    except Exception as e:
        return {"error": f"Error reading content file: {e}"}

    scene_class_name = f"{to_pascal_case(chapter_title)}Scene"

    template_function = MANIM_TEMPLATES.get(template_name)
    if not template_function:
        return {"error": f"Invalid template name: {template_name}. Available templates: {list(MANIM_TEMPLATES.keys())}"}

    # Generate script content using the chosen template
    # Sanitize chapter_title and content for embedding in script string
    safe_chapter_title = chapter_title.replace('"', '\\"').replace("'", "\\'")
    # Content is passed as is, template functions should handle sanitization if they embed it directly
    
    script_content = template_function(scene_class_name, safe_chapter_title, content)

    try:
        os.makedirs(os.path.dirname(output_script_path), exist_ok=True)
        with open(output_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        return {"script_path": output_script_path, "scene_name": scene_class_name}
    except Exception as e:
        return {"error": f"Error writing Manim script: {e}"}

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    test_content_dir = "test_course_content"
    os.makedirs(test_content_dir, exist_ok=True)
    test_md_path = os.path.join(test_content_dir, "01-Introduction_to_Python.md")
    with open(test_md_path, "w") as f:
        f.write("This is the first line of content for our Python intro.\\nAnd this is the second line.\\nFollowed by a third one to see how it looks.")

    test_output_scripts_dir = "test_manim_scripts"
    os.makedirs(test_output_scripts_dir, exist_ok=True)
    test_script_path = os.path.join(test_output_scripts_dir, "IntroductionToPython_manim.py")
    
    result = generate_manim_script("Introduction to Python", test_md_path, test_script_path)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Manim script generated: {result['script_path']}")
        print(f"Scene name: {result['scene_name']}")
        # To run this (ensure Manim is installed and in PATH):
        # manim -pql {result['script_path']} {result['scene_name']}
    
    # Clean up test files
    # os.remove(test_md_path)
    # os.rmdir(test_content_dir)
    # os.remove(test_script_path)
    # os.rmdir(test_output_scripts_dir)
"""
# Added a main block for testing, will remove if it causes issues with the execution environment
# or keep it if it's fine. For now, it helps in development.
# The actual file saving part of the subtask will use this module without running the main block.
# The functions to_pascal_case is added to help with scene naming.
# Added error handling for file operations.
# Content for Manim scene is simplified (first 3 lines, 50 chars each).
# Added FadeOut animations for cleanup.
# Ensured content_mobject is only referenced if created.
# Positioned title and content more explicitly.
# Added a check for empty content_text_str before creating Text mobject.
# Made directories for output script path if they don't exist.
