import logging
import sys
import os
from logging.handlers import RotatingFileHandler


class OneLineExceptionFormatter(logging.Formatter):
    """Format exceptions on a single line for cleaner logs."""

    def formatException(self, exc_info):
        result = super().formatException(exc_info)
        return repr(result)

    def format(self, record):
        result = super().format(record)
        if record.exc_text:
            result = result.replace("\n", " | ")
        return result


def init_logger(
    log_level=logging.INFO,
    log_file="logs/cli.log",
    file_size=2 * 1024 * 1024,
    file_count=2,
    shell_output=True,
    log_file_mode="a",
    log_format="%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s",
    print_log_init=False,
):
    """
    Initialize logger with rotating file handler and optional stdout output.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file
        file_size: Max size per log file in bytes
        file_count: Number of backup files to keep
        shell_output: Whether to also output to stdout
        log_file_mode: File mode ('a' for append, 'w' for overwrite)
        log_format: Log message format string
        print_log_init: Whether to print initialization message

    Returns:
        Configured logger instance
    """
    try:
        main_logger = logging.getLogger()
        main_logger.setLevel(log_level)
        log_formatter = OneLineExceptionFormatter(log_format)

    except Exception as e:
        print(f"Exception when format logger: {e}")
        return None

    # Create log directory if needed
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        if print_log_init:
            print(f"Log directory: {log_dir}")

    try:
        # Clear existing handlers to prevent duplicates
        main_logger.handlers = []
        main_logger.propagate = False

        # Add rotating file handler
        log_rotate_handler = RotatingFileHandler(
            log_file,
            mode=log_file_mode,
            maxBytes=file_size,
            backupCount=file_count,
            encoding="utf-8",
            delay=0,
        )
        log_rotate_handler.setFormatter(log_formatter)
        log_rotate_handler.setLevel(log_level)
        main_logger.addHandler(log_rotate_handler)

    except Exception as e:
        print(f"Exception when creating file handler: {e}")

    try:
        # Add stdout handler if requested
        if shell_output:
            stream_log_handler = logging.StreamHandler(stream=sys.stdout)
            stream_log_handler.setFormatter(log_formatter)
            stream_log_handler.setLevel(log_level)
            main_logger.addHandler(stream_log_handler)

    except Exception as e:
        print(f"Exception when creating stdout handler: {e}")

    if print_log_init:
        print(f"Logging initialized: level={log_level}, file={os.path.abspath(log_file)}")

    return main_logger


class LogManager:
    """
    Manages component logger levels with smart hierarchy handling.

    Provides:
    - Curated registry of primary components for UI controls
    - Smart auto-adjustment of root logger when needed
    - Discovery of all active loggers for advanced debugging
    """

    # Primary components to expose in UI (curated list)
    PRIMARY_COMPONENTS = {
        "prompt": {
            "default": logging.INFO,
            "description": "Application logs (config, prompts, etc.)",
            "loggers": ["app.prompt"]
        },
        "http": {
            "default": logging.WARNING,
            "description": "HTTP request/response logs",
            "loggers": ["openai", "httpx", "httpcore"]
        },
        "langchain": {
            "default": logging.WARNING,
            "description": "LangChain internal processing",
            "loggers": ["langchain"]
        },
        "orchestrator": {
            "default": logging.INFO,
            "description": "Orchestrator planning and execution",
            "loggers": ["orchestrator"]
        },
        "mcp": {
            "default": logging.INFO,
            "description": "MCP server communication",
            "loggers": ["mcp"]
        }
    }

    # Third-party libraries to silence by default
    NOISY_DEFAULTS = {
        "asyncio": logging.WARNING,
        "urllib3": logging.WARNING,
        "httpcore.connection": logging.WARNING,
        "httpcore.http11": logging.WARNING,
        "markdown_it": logging.WARNING,
    }

    def __init__(self, root_logger=None):
        """
        Initialize LogManager.

        Args:
            root_logger: Root logger instance (defaults to logging.getLogger())
        """
        self.root_logger = root_logger or logging.getLogger()
        self._component_loggers = {}

        # Apply defaults for primary components
        for component, config in self.PRIMARY_COMPONENTS.items():
            for logger_name in config["loggers"]:
                logger = logging.getLogger(logger_name)
                logger.setLevel(config["default"])
                if component not in self._component_loggers:
                    self._component_loggers[component] = []
                self._component_loggers[component].append(logger)

        # Silence noisy libraries
        for logger_name, level in self.NOISY_DEFAULTS.items():
            logging.getLogger(logger_name).setLevel(level)

    def set_level(self, component, level):
        """
        Set log level for a component with smart root adjustment.

        If the target level is lower than root level, automatically adjusts
        root to allow messages through.

        Args:
            component: Component name (e.g., "prompt", "http", "langchain", "all")
            level: Logging level (logging.DEBUG, INFO, WARNING, ERROR)

        Returns:
            tuple: (success: bool, message: str) for UI display
        """
        level_name = logging.getLevelName(level)

        # Handle "all" pseudo-component
        if component == "all":
            components_to_set = list(self.PRIMARY_COMPONENTS.keys())
        elif component in self.PRIMARY_COMPONENTS:
            components_to_set = [component]
        else:
            return False, f"Unknown component: {component}"

        # Check if we need to lower root level
        root_adjusted = False
        if self.root_logger.level > level:
            self.root_logger.setLevel(level)
            root_adjusted = True

        # Set levels for all loggers in the component(s)
        for comp in components_to_set:
            if comp in self._component_loggers:
                for logger in self._component_loggers[comp]:
                    logger.setLevel(level)

        # Build success message
        if component == "all":
            msg = f"All components set to {level_name}"
        else:
            msg = f"{component.capitalize()} logs set to {level_name}"

        if root_adjusted:
            msg += f"\n(Root level auto-adjusted to {level_name})"

        return True, msg

    def get_ui_components(self):
        """
        Get primary components for UI controls.

        Returns:
            dict: Component name -> {default, description}
        """
        return {
            name: {
                "default": config["default"],
                "description": config["description"]
            }
            for name, config in self.PRIMARY_COMPONENTS.items()
        }

    def get_all_loggers(self):
        """
        Get all active loggers (for advanced debugging).

        Returns:
            list: Logger names currently active in the system
        """
        return sorted(logging.root.manager.loggerDict.keys())

    def get_status(self):
        """
        Get current log levels for all components.

        Returns:
            dict: {
                "root": level_name,
                "components": {component: level_name}
            }
        """
        status = {
            "root": logging.getLevelName(self.root_logger.level),
            "components": {}
        }

        for component, loggers in self._component_loggers.items():
            # Get level from first logger in the group
            if loggers:
                status["components"][component] = logging.getLevelName(loggers[0].level)

        return status
