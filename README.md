# CodeEasy – Dead Code Elimination Tool

A web-based tool for optimizing C-like code by eliminating dead code using compiler techniques.

## Features

- Parses simplified C-like language (variables, assignments, if-else, loops, return)
- Converts to Three Address Code (TAC)
- Builds Control Flow Graph (CFG)
- Performs analysis: unused variables, unreachable code, live variables, redundant assignments, constant conditions
- Optimizes by removing dead code
- Generates optimized C-like code
- Web interface for input and output

## Project Structure

- `app.py`: Flask application
- `frontend/`: HTML, CSS, JS files
- `backend/`: Parser, TAC generator, CFG builder, analysis, optimizer, code generator
- `requirements.txt`: Python dependencies

## Installation

1. Ensure Python 3.8+ is installed.
2. Install dependencies: `pip install -r requirements.txt`

## Running the Application

Run the Flask app:

```bash
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

## Example

Input Code:
```
int x;
int y;
x = 5;
y = x + 1;
x = 10;
```

Optimized Output:
```
x = 5;
y = x + 1;
x = 10;
```

(Note: In this simple example, no dead code is removed, but the tool performs analysis.)

## Technologies

- Backend: Python, Flask, PLY
- Frontend: HTML, CSS, JavaScript
- Analysis: Control Flow Graph, Data Flow Analysis