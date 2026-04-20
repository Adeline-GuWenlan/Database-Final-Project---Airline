from flask import Flask, render_template

# Initialize a Flask app
app = Flask(__name__)

# Define a simple route function
@app.route('/')
def hello():
    return render_template('hello.html')

# Run the app
if __name__ == '__main__':
    app.run('127.0.0.1', 5000)
