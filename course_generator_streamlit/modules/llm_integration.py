# modules/llm_integration.py
import time # To simulate delay

def generate_course_outline(topic: str, details: str, audience: str) -> list[str]:
    """Generates a course outline based on the topic, details, and audience."""
    time.sleep(2) # Simulate LLM processing time
    return [
        f"Introduction to {topic}",
        f"Core Concepts of {topic}",
        f"Advanced Topics in {topic} for {audience}s",
        "Practical Applications",
        "Conclusion and Further Learning"
    ]

def generate_chapter_content(chapter_title: str, topic: str, details: str, audience: str) -> str:
    """Generates content for a specific chapter."""
    time.sleep(3) # Simulate LLM processing time
    return f"""
    ## {chapter_title}

    This chapter delves into the specifics of {chapter_title}, building upon the general knowledge of {topic}.
    We will explore various facets relevant to {audience} learners.

    Key points:
    - Point 1 related to {chapter_title}
    - Point 2 related to {chapter_title}
    - Point 3 tailored for {audience}s.

    {details}
    """

def generate_voiceover_script(chapter_content: str) -> str:
    """Generates a voiceover script from chapter content."""
    time.sleep(1)
    # Simple script: just use the first few lines of content
    script_lines = chapter_content.strip().split('\\n')[:5]
    return "\\n".join(script_lines) + "\\n\\nEnd of voiceover for this section."

def generate_html_slides(chapter_title: str, chapter_content: str) -> str:
    """Generates HTML slide content for a chapter."""
    time.sleep(2)
    # Remove markdown headers for slide content
    content_lines = [line for line in chapter_content.strip().split('\\n') if not line.startswith('#')]
    slide_points_html = "".join([f"<li>{line}</li>" for line in content_lines if line.strip() and not line.startswith("Key points:") and not line.startswith("- Point")])
    
    key_points_section = chapter_content.split("Key points:")[-1] if "Key points:" in chapter_content else ""
    key_points_html = "".join([f"<li>{line.replace('- ','')}</li>" for line in key_points_section.split('\\n') if line.strip().startswith('-')])


    return f"""
    <div style="border: 1px solid #ddd; padding: 20px; margin-bottom: 20px;">
        <h2>Slide 1: {chapter_title}</h2>
        <p>This is the main title slide for {chapter_title}.</p>
    </div>
    <div style="border: 1px solid #ddd; padding: 20px; margin-bottom: 20px;">
        <h3>Slide 2: Overview</h3>
        <ul>
            {slide_points_html if slide_points_html else "<li>No specific overview points generated.</li>"}
        </ul>
    </div>
    <div style="border: 1px solid #ddd; padding: 20px; margin-bottom: 20px;">
        <h3>Slide 3: Key Points</h3>
        <ul>
            {key_points_html if key_points_html else "<li>No key points generated.</li>"}
        </ul>
    </div>
    <div style="border: 1px solid #ddd; padding: 20px;">
        <h3>Slide 4: Conclusion</h3>
        <p>End of slides for {chapter_title}.</p>
    </div>
    """
