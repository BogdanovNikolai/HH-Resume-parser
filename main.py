import app
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    app.app.run(host='0.0.0.0', port=5000, debug=True)