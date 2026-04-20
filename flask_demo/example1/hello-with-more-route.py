from flask import Flask

# Initialize a Flask app
app = Flask(__name__)

# Define a simple route function
@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/niceday')
def nice():
    return "It's a nice day!"

# Run the app
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)