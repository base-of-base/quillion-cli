from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def process_templates(project_dir: str, context: dict, templates_dir: Path):
    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    for item in templates_dir.rglob("*"):
        if item.is_file():
            relative_path = item.relative_to(templates_dir)
            target_relative_path = relative_path.with_suffix("")
            target_path = Path(project_dir) / target_relative_path

            target_path.parent.mkdir(parents=True, exist_ok=True)

            template_rel_path = str(relative_path).replace("\\", "/")
            template = env.get_template(template_rel_path)
            target_path.write_text(template.render(**context))
