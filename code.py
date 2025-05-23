import wifi
import json
import ssl
import adafruit_requests
import board
import pwmio
import time
from adafruit_connection_manager import get_radio_socketpool
from adafruit_httpserver import Server, Request, Response
from adafruit_motor import servo

# Create motor PWM output
pwm0 = pwmio.PWMOut(board.GP16, frequency=50)
servo_0 = servo.Servo(pwm0, min_pulse=870, max_pulse=2370)

pwm1 = pwmio.PWMOut(board.GP17, frequency=50)
servo_1 = servo.Servo(pwm1, min_pulse=870, max_pulse=2370)

pwm2 = pwmio.PWMOut(board.GP18, frequency=50)
servo_2 = servo.Servo(pwm2, min_pulse=870, max_pulse=2370)

pwm3 = pwmio.PWMOut(board.GP19, frequency=50)
servo_3 = servo.Servo(pwm3, min_pulse=870, max_pulse=2370)

pwm4 = pwmio.PWMOut(board.GP20, frequency=50)
servo_4 = servo.Servo(pwm4, min_pulse=870, max_pulse=2370)

pwm5 = pwmio.PWMOut(board.GP21, frequency=50)
servo_5 = servo.Servo(pwm5, min_pulse=870, max_pulse=2370)

pwm6 = pwmio.PWMOut(board.GP15, frequency=50)
servo_6 = servo.Servo(pwm6, min_pulse=870, max_pulse=2370)

pwm7 = pwmio.PWMOut(board.GP14, frequency=50)
servo_7 = servo.Servo(pwm7, min_pulse=870, max_pulse=2370)

angle = -5

servo_list = [servo_0, servo_1, servo_2, servo_3, servo_4, servo_5, servo_6, servo_7]


def move_motor(motor):
    """
    Move the motor connected to GP16 to a specific position.

    Args:
        motor: the motor class to move
    """
    motor.angle = 0

    angles = 180

    for i in range(angles):
        motor.angle = i
        time.sleep(0.01)

    for i in reversed(range(angles)):
        motor.angle = i
        time.sleep(0.01)

    motor.angle = 0


def move_motor_based_on_notebook(notebook_idx):
    """
    Move the motor based on the notebook index that was returned.

    Args:
        notebook_idx (int): The index of the notebook
    """
    print(f"Notebook index: {notebook_idx}")

    motor = servo_list[int(notebook_idx)]

    move_motor(motor)

    return notebook_idx


pool = get_radio_socketpool(wifi.radio)
server = Server(pool, "/static", debug=True)
session = adafruit_requests.Session(pool, ssl.create_default_context())

# Sample JSON data of notebooks
notebooks_data = json.dumps([
    {
        "name": "Machine Learning Basics",
        "idx": "0",
        "contents": ["gradient descent", "classification", "perceptron", "ROC Curves", "nonlinear layers", "GNNs",
                     "Logistic Regression", "reinforcement learning", "ensemble learning", "gradient boosting"]
    },
    {
        "name": "Econ and Computation",
        "idx": "1",
        "contents": ["game theory", "nash equilibrium", "correlated equilibrium", "p2p systems", "cryptoecon",
                     "peer prediction", "kidney problem", "bitcoin", "combinatorial auctions", "bidding languages"]
    },
    {
        "name": "Empty Notebook",
        "idx": "2",
        "contents": []
    },
    {
        "name": "Empty Notebook",
        "idx": "3",
        "contents": []
    },
    {
        "name": "Empty Notebook",
        "idx": "4",
        "contents": []
    },
    {
        "name": "Suffolk Summer",
        "idx": "5",
        "contents": ["maze problem", "pathfinding", "aws", "ec2", "lambda functions", "construction", "python"]
    },
    {
        "name": "Empty Notebook",
        "idx": "6",
        "contents": []
    },
    {
        "name": "Suffolk School Year",
        "idx": "7",
        "contents": ["software development", "testing", "pytest", "pull requests", "github"]
    }
])


def search_notebooks_with_ollama(query):
    """
    Search for the most relevant notebook using Ollama API.
    """
    try:
        # Ollama API endpoint - adjust the URL to your local Ollama instance
        url = "http://136.167.238.48:11434/api/generate"

        # Prepare the notebooks data
        notebooks = json.loads(notebooks_data)

        # Create a prompt for the model without using indent
        prompt = f"""
        I have these notebooks with their contents:
        {json.dumps(notebooks)}

        A user is searching for: "{query}"

        Which notebook is most relevant to this search query? Use the name and contents to inform your answer. Return only a JSON with the format:
        {{
          "idx": "the notebook id",
          "name": "the notebook name",
          "reason": "brief explanation of why this matches"
        }}
        """

        # Create payload for Ollama API
        payload = {
            "model": "bevingta/physcomp",  # Your specific Ollama model
            "prompt": prompt,
            "stream": False
        }

        # Make the API call
        response = session.post(url, json=payload)

        print("Response: ", response)

        if response.status_code == 200:
            result = response.json()

            # Extract the generated text from the response
            llm_output = result.get('response', '')

            # Parse the JSON from the LLM output
            try:
                # Look for JSON-like content between curly braces
                start_idx = llm_output.find('{')
                end_idx = llm_output.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = llm_output[start_idx:end_idx]
                    match_data = json.loads(json_str)

                    # Add match score for consistency with UI
                    if 'match_score' not in match_data:
                        match_data['match_score'] = 5  # LLM matches get high score

                    # Move the motor based on notebook index
                    notebook_idx = match_data.get('idx', 'none')
                    move_motor_based_on_notebook(notebook_idx)

                    return match_data
            except Exception as json_error:
                print(f"Error parsing LLM output: {json_error}")

        # Fallback to basic search if API call or parsing fails
        return search_notebooks_basic(query)

    except Exception as e:
        print(f"Ollama API error: {e}")
        # Fallback to basic search
        return search_notebooks_basic(query)


def search_notebooks_basic(query):
    """
    Basic search function as fallback.
    """
    query = query.lower()
    notebooks = json.loads(notebooks_data)
    best_match = None
    best_score = 0

    for notebook in notebooks:
        # Check if query matches the notebook name
        if query in notebook["name"].lower():
            score = 3  # Higher weight for name matches
            if score > best_score:
                best_score = score
                best_match = notebook

        # Check if query matches any content item
        for item in notebook["contents"]:
            if query in item.lower():
                score = 2  # Lower weight for content matches
                if score > best_score:
                    best_score = score
                    best_match = notebook

    # If no direct match, find partial matches
    if best_match is None:
        for notebook in notebooks:
            # Check for partial matches in name
            name_words = notebook["name"].lower().split()
            for word in name_words:
                if query in word or word in query:
                    score = 1  # Even lower weight for partial matches
                    if score > best_score:
                        best_score = score
                        best_match = notebook

            # Check for partial matches in contents
            for item in notebook["contents"]:
                item_words = item.lower().split()
                for word in item_words:
                    if query in word or word in query:
                        score = 0.5
                        if score > best_score:
                            best_score = score
                            best_match = notebook

    if best_match:
        result = {
            "name": best_match["name"],
            "idx": best_match["idx"],
            "match_score": best_score,
            "reason": "Found by basic search algorithm"
        }

        # Move the motor based on notebook index
        notebook_idx = best_match["idx"]
        move_motor_based_on_notebook(notebook_idx)

        return result
    else:
        # No match found - move motor to 0% position
        move_motor_based_on_notebook("none")
        return {"name": "No matching notebook found", "idx": "none", "match_score": 0, "reason": "No matches found"}


@server.route("/")
def base(request: Request):
    """
    Serve a default static plain text message.
    """
    return Response(request, "Hello from the CircuitPython HTTP Server!")


@server.route("/html")
def html_page(request: Request):
    """
    Serve an HTML page with search functionality.
    """

    # Create HTML with search form
    html = """<!DOCTYPE html>
    <html>
    <head>
        <title>Notebook Search</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            form { margin: 20px 0; }
            input[type="text"] { padding: 8px; width: 70%; }
            button { padding: 8px 16px; }
            #result { margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
            .loading { display: none; margin-top: 10px; color: #666; }
        </style>
        <script>
            function searchNotebooks() {
                const query = document.getElementById('search-query').value;

                if (!query) {
                    alert('Please enter a search term');
                    return false;
                }

                // Show loading indicator
                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').innerHTML = '';

                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(data => {
                        // Hide loading indicator
                        document.getElementById('loading').style.display = 'none';

                        const resultDiv = document.getElementById('result');
                        resultDiv.innerHTML = `
                            <h3>Search Result:</h3>
                            <p><strong>Notebook:</strong> ${data.name}</p>
                            <p><strong>Index:</strong> ${data.idx}</p>
                            <p><strong>Match Score:</strong> ${data.match_score}</p>
                            ${data.reason ? `<p><strong>Reason:</strong> ${data.reason}</p>` : ''}
                        `;
                    })
                    .catch(error => {
                        // Hide loading indicator
                        document.getElementById('loading').style.display = 'none';

                        console.error('Error:', error);
                        document.getElementById('result').innerHTML = '<p>Error processing your request</p>';
                    });

                return false; // Prevent form submission
            }
        </script>
    </head>
    <body>
        <h1>Notebook Search</h1>
        <p>Enter a topic to find the most relevant notebook:</p>

        <form onsubmit="return searchNotebooks()">
            <input type="text" id="search-query" placeholder="e.g., reinforcement learning">
            <button type="submit">Search</button>
        </form>

        <div id="loading" class="loading">Searching notebooks with AI... this may take a few seconds</div>

        <div id="result">
            <p>Search results will appear here</p>
        </div>
    </body>
    </html>
    """

    return Response(request, html, content_type="text/html")


@server.route("/api/search")
def search_api(request: Request):
    """
    API endpoint for searching notebooks.
    """
    # Get the query parameter
    query = request.query_params.get("q", "")

    # Search notebooks using Ollama
    try:
        result = search_notebooks_with_ollama(query)
    except Exception as e:
        print(f"Search error: {e}")
        # Fallback to basic search
        result = search_notebooks_basic(query)

    # Return JSON response
    return Response(request, json.dumps(result), content_type="application/json")


@server.route("/api/call-function")
def call_function(request: Request):
    """
    API route that calls the function and returns its result.
    """
    response_text = return_a_response()
    return Response(request, response_text)


@server.route("/api/motor")
def motor_api(request: Request):
    """
    API endpoint for directly controlling the motor.
    """
    # Get the position parameter (0-100%)
    position = int(request.query_params.get("position", "50"))
    position = max(0, min(100, position))  # Ensure position is between 0-100

    # Get the duration parameter (seconds)
    duration = float(request.query_params.get("duration", "1.0"))
    duration = max(0.1, min(5.0, duration))  # Reasonable limits on duration

    # Move the motor
    move_motor(position, duration)


    # Return JSON response
    result = {"success": True, "position": position, "duration": duration}
    return Response(request, json.dumps(result), content_type="application/json")


server.serve_forever(str(wifi.radio.ipv4_address))
