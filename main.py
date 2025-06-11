from hh.api import findResumes
from utils.excel_writer import append_resumes_to_excel
import os
import truststore

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

if __name__ == "__main__":
    result = findResumes(
        ("1С", "everywhere", "any", "all_time"),
        debug=False,
        access_token=ACCESS_TOKEN
    )

    append_resumes_to_excel(result, filename="resumes.xlsx")