def generate_content_for_outline(selected_outline_items):
    """
    Generates placeholder content for each selected outline item.
    """
    content = {}
    for item in selected_outline_items:
        content[item] = f"This is the placeholder content for the chapter: {item}."
    return content
