# DeepSite Python

A simplified Python version of DeepSite that allows users to generate websites using AI.
This application uses [langchain-azure-ai](https://github.com/langchain-ai/langchain-azure) to access DeepSeek R1 model.

## Features

- Generate websites from natural language descriptions
- Edit HTML code with a Monaco Editor
- Preview the website in real-time
- Rate limiting for free users

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, JavaScript, TailwindCSS
- **Editor**: Monaco Editor
- **AI**: langchain-azure-ai (DeepSeek R1)

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Azure AI Foundry access

### Installation

1. Clone this repository

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows~: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on the `.env.example` file:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your Azure OpenAI API details:
```
AZURE_API_KEY=your_azure_api_key
AZURE_ENDPOINT={your endpoint}
```

### Running the Application

Run the Flask development server:

```bash
python app.py
```

The application will be available at http://localhost:5000

## Usage

1. Visit the homepage and click "Start Creating"
2. In the editor page, type a description of the website you want to create in the prompt box at the bottom
3. Wait for the AI to generate your website
4. Toggle between "Editor" and "Preview" modes to see and edit your website
5. Deploy your website when ready

## Project Structure

```
python_app/
│
├── app.py               # Main Flask application
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── README.md            # This file
│
├── static/              # Static assets
│   └── sites/           # Generated sites are stored here
│
└── templates/           # HTML templates
    ├── index.html       # Landing page
    └── editor.html      # Website editor page
```

## Comparison to Original DeepSite

This Python version simplifies the original DeepSite application by:

1. Replacing the React/TypeScript frontend with a simpler HTML/JavaScript approach
2. Using Flask instead of Express.js for the backend
3. Utilizing `langchain-azure-ai` instead of direct Hugging Face integration
