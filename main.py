import app
import os
from dotenv import load_dotenv
from postgres_client import postgres_client

load_dotenv()

if __name__ == "__main__":
    postgres_client.create_tables()
    print("All good man")
    
    app.app.run(host='0.0.0.0', port=5000, debug=False)