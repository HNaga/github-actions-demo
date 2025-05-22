import os
import re

def sanitize_filename(name):
    """
    Sanitizes a string to be used as a filename.
    Removes or replaces characters that are not allowed in filenames.
    """
    name = re.sub(r'[^\w\s-]', '', name).strip() # Remove non-alphanumeric (excluding spaces, hyphens)
    name = re.sub(r'[-\s]+', '-', name) # Replace spaces and hyphens with a single hyphen
    return name

def save_content_to_files(course_topic, generated_content):
    """
    Saves the generated content for a course into Markdown files.
    """
    base_dir = "courses"
    sanitized_topic = sanitize_filename(course_topic)
    course_dir = os.path.join(base_dir, sanitized_topic)

    if not os.path.exists(course_dir):
        os.makedirs(course_dir)

    saved_files = []
    for chapter_title, content in generated_content.items():
        sanitized_chapter_title = sanitize_filename(chapter_title)
        file_name = f"{sanitized_chapter_title}.md"
        file_path = os.path.join(course_dir, file_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        saved_files.append(file_path)
    
    return {"message": f"Content saved to '{course_dir}'", "file_paths": saved_files, "course_directory": course_dir}
