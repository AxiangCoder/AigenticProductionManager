from . import SafeLiteLlm
from dotenv import load_dotenv
import os
load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")
# MODEL = "gemini-2.5-flash"
MODEL = SafeLiteLlm(model=MODEL_NAME)