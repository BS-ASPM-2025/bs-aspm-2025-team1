import os
from fastapi.templating import Jinja2Templates

# להגיע לשורש הפרויקט: src/web -> src -> (root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))