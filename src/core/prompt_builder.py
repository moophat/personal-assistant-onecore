import logging
from jinja2 import Environment, FileSystemLoader, Template
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds prompts from Jinja2 templates with hot reload support."""

    def __init__(self, template_path: str):
        self.template_path = Path(template_path)
        self.template: Optional[Template] = None
        self.last_mtime: Optional[float] = None
        self.env = Environment(loader=FileSystemLoader(self.template_path.parent))

        # User message template path
        self.user_template_path = self.template_path.parent / "user_prompt.jinja"
        self.user_template: Optional[Template] = None
        self.user_last_mtime: Optional[float] = None

    def load(self) -> Template:
        """Load template from file."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        self.template = self.env.get_template(self.template_path.name)
        self.last_mtime = self.template_path.stat().st_mtime
        return self.template

    def check_and_reload(self) -> tuple[bool, Optional[Template]]:
        """
        Check if template file has been modified and reload if necessary.

        Returns:
            Tuple of (was_reloaded: bool, template: Optional[Template])
        """
        if not self.template_path.exists():
            return False, self.template

        current_mtime = self.template_path.stat().st_mtime

        # First load or file has been modified
        if self.last_mtime is None or current_mtime > self.last_mtime:
            try:
                template = self.load()
                return True, template
            except Exception as e:
                logger.error(f"Error reloading template: {e}")
                return False, self.template

        return False, self.template

    def render(self, **variables: Any) -> str:
        """
        Render template with provided variables.

        Args:
            **variables: Variables to pass to the template

        Returns:
            Rendered template string
        """
        if self.template is None:
            self.load()

        return self.template.render(**variables)

    def get_template(self) -> Template:
        """Get current template."""
        if self.template is None:
            self.load()
        return self.template

    def load_user_template(self) -> Optional[Template]:
        """Load user template from file if it exists."""
        if not self.user_template_path.exists():
            return None

        self.user_template = self.env.get_template(self.user_template_path.name)
        self.user_last_mtime = self.user_template_path.stat().st_mtime
        return self.user_template

    def check_and_reload_user_template(self) -> bool:
        """Check if user template file has been modified and reload if necessary."""
        if not self.user_template_path.exists():
            return False

        current_mtime = self.user_template_path.stat().st_mtime

        if self.user_last_mtime is None or current_mtime > self.user_last_mtime:
            try:
                self.load_user_template()
                return True
            except Exception as e:
                logger.error(f"Error reloading user template: {e}")
                return False

        return False

    def render_user(self, **variables: Any) -> str:
        """
        Render user message with template if it exists, otherwise return raw user_input.

        Args:
            **variables: Variables to pass to the template (must include user_input)

        Returns:
            Rendered user message string
        """
        # Check for hot reload
        self.check_and_reload_user_template()

        # If no template exists, return raw user input
        if self.user_template is None:
            self.load_user_template()

        if self.user_template is None:
            return variables.get("user_input", "")

        return self.user_template.render(**variables)
