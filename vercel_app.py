# Vercel serverless function handler
from kartshart.wsgi import application

# Vercel expects an 'app' or 'handler' variable
app = application
