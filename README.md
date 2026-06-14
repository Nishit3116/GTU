# GTU PYQ Downloader & Merger

Terminal application for downloading GTU Previous Year Question Papers and merging them into a single PDF in the required session order.

The current order is winter-first by year: `W2026, S2026, W2025, S2025, W2024, S2024, W2023, S2023, W2022, S2022, W2021, S2021`.

## Project Overview

GTU Personal Analyser is a modular academic intelligence platform built around GTU Previous Year Question Papers. Starting from automated PYQ ingestion and validation, it extracts question text (with optional OCR), applies NLP-driven topic extraction and tagging, and builds a structured question bank. The platform provides analytics to identify weak topics, frequently asked questions, and difficulty patterns, and can generate personalized study plans based on historical paper patterns and user progress. v1 focuses on reliable paper discovery, download, and merge capabilities with local-first privacy; future releases will add web dashboards, AI-driven summarization, and study-planner features.

## Features

- Prompts for a GTU subject code from the terminal
- Searches GTU papers in the exact required session order
- Skips missing papers without stopping the workflow
- Validates existing PDFs before reusing them
- Retries transient download failures
- Merges valid PDFs with `PdfReader` and `PdfWriter` from `pypdf`
- Writes a professional summary and a log file for troubleshooting

## Installation

Clone the repository from GitHub:

```bash
git clone [https://github.com/YOUR_USERNAME/gtu-pyq-downloader.git]
(https://github.com/Nishit3116/GTU.git)
cd gtu-pyq-downloader
```

Install dependencies:

```bash
python -m pip install -e .
```

## Usage

Run the application:

```bash
gtu-pyq
```

Or run directly:

```bash
python -m gtu_pyq_downloader
```

Then enter the GTU subject code when prompted:

```
Enter Subject Code: 3170719
```

The app will download all available papers and merge them into a single PDF.

## Output

Downloaded PDFs are stored in:

```text
downloads/{subject_code}/
```

Merged PDF name:

```text
PYQ ({subject_code}).pdf
```

## Future Extensions

The package layout is intentionally modular so additional modules can be added later for:

- Automatic Syllabus Downloader
- Mid Paper Downloader
- AI Topic Extraction
- Gemini Integration
- OCR
- Streamlit/Web Dashboard
- Database Storage
- AI Study Planner
- Academic Intelligence Platform
