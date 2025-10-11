def format_app_name(project_name: str) -> str:
    words = project_name.split("_")
    capitalized_words = [word.capitalize() for word in words if word]
    return " ".join(capitalized_words)
