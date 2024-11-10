import dotenv
import importlib
from pathlib import Path
from shroud.slack.slack import start_app

dotenv.load_dotenv()

def import_modules_from_directory(directory):
    for path in directory.glob("*.py"):
        if path.name != "__init__.py":
            module_name = f"shroud.slack.handlers.{path.stem}"
            importlib.import_module(module_name)

def main():
    handlers_directory = Path(__file__).parent / 'slack' / 'handlers'
    import_modules_from_directory(handlers_directory)
    start_app()

if __name__ == "__main__":
    main()