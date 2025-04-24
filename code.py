import wifi
import json
import ssl
import adafruit_requests
from adafruit_connection_manager import get_radio_socketpool
from adafruit_httpserver import Server, Request, Response
from helpers.base_response import return_a_response

pool = get_radio_socketpool(wifi.radio)
server = Server(pool, "/static", debug=True)
session = adafruit_requests.Session(pool, ssl.create_default_context())

# Sample JSON data of notebooks
notebooks_data = json.dumps([
    {
        "name": "Machine Learning Basics",
        "idx": "ml001",
        "contents": ["supervised learning", "regression", "classification", "model evaluation"]
    },
    {
        "name": "Deep Learning",
        "idx": "dl002",
        "contents": ["neural networks", "backpropagation", "activation functions", "deep architectures"]
    },
    {
        "name": "Reinforcement Learning",
        "idx": "rl003",
        "contents": ["Q-learning", "policy gradients", "reward systems", "exploration vs exploitation"]
    },
    {
        "name": "Natural Language Processing",
        "idx": "nlp004",
        "contents": ["tokenization", "word embeddings", "transformers", "BERT models"]
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

        Which notebook is most relevant to this search query? Return only a JSON with the format:
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
        return {
            "name": best_match["name"],
            "idx": best_match["idx"],
            "match_score": best_score,
            "reason": "Found by basic search algorithm"
        }
    else:
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
    # Get the response from the function
    response_text = return_a_response()

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

        <hr>
        <p>Server test response: """ + response_text + """</p>
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


server.serve_forever(str(wifi.radio.ipv4_address))
