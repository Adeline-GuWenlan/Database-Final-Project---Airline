from flask import Flask

# Initialize a Flask app
app = Flask(__name__)

# Define a simple route function
@app.route('/')
def hello():
    return 'Hello World!'

# Run the app
if __name__ == '__main__':
    app.run('127.0.0.1', 5000)
