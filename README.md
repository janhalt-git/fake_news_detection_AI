# fake_news_detection_AI

This project utilizes google gemini's API.
You must create an API key at https://aistudio.google.com/api-keys in order to run this project.

## for Testing:
create virtual environment:                      in the parent folder, use the cmd ".venv\Scripts\Activate.ps1

if you come across an error run in terminal:     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
                                                 and run the previous step again

install required dependencies:                   pip install -U google-generativeai fastapi sqlmodel uvicorn trafilatura tldextract politifact

Add your API key:                                run in cmd $env:GEMINI_API_KEY="INSERT_HERE"

cmd to run the app:                              python -m uvicorn app.main:app --reload

open the server in your browser:                 http://127.0.0.1:8000/docs

click on "try it out"

example test cmds (use them in the request body):        { "url": "ANY URL THAT LEADS DIRECTLY TO AN ARTICLE" } {"text": "The president is currently 52 years old"}
