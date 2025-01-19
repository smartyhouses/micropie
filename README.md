[![Logo](https://patx.github.io/micropie/logo2.png)](https://patx.github.io/micropie)

## **Introduction**

**MicroPie** is a lightweight Python web framework that makes building web applications simple and efficient. It includes features such as routing, session management, and Jinja2 template rendering.

### **Key Features**
- 🚀 **Easy Setup:** Minimal configuration required.
- 🔄 **Routing:** Maps URLs to functions automatically.
- 🔐 **Sessions:** Simple session management using cookies.
- 🎨 **Templates:** Jinja2 for dynamic HTML pages.
- ⚡ **Fast & Lightweight:** No unnecessary dependencies. WSGI support.

## **Installation**

Install MicroPie with:

```bash
pip install micropie
```

## **Getting Started**

Create a basic MicroPie app in `server.py`:

```python
from MicroPie import Server

class MyApp(Server):
    def index(self, name="Guest"):
        return f"Hello, {name}!"

MyApp().run()
```

Run the server:

```bash
python server.py
```

Visit your app at [http://127.0.0.1:8080](http://127.0.0.1:8080).

## **Core Features**

### **1. Routing**

Define methods to handle URLs:

```python
class MyApp(Server):
    def hello(self):
        return "Hello, world!"
```

**Access:**
- Basic route: [http://127.0.0.1:8080/hello](http://127.0.0.1:8080/hello)

### **2. Handling GET Requests**

MicroPie allows passing data using query strings (`?key=value`) and URL path segments.

#### **Query Parameters**

You can pass query parameters via the URL, which will be automatically mapped to method arguments:

```python
class MyApp(Server):
    def greet(self, name="Guest"):
        return f"Hello, {name}!"
```

**Access:**
- Using query parameters: [http://127.0.0.1:8080/greet?name=Alice](http://127.0.0.1:8080/greet?name=Alice)
  - This will return: `Hello, Alice!`
- Using URL path segments: [http://127.0.0.1:8080/greet](http://127.0.0.1:8080/greet)
  - This will return: `Hello, Guest!`

#### **Path Parameters (Dynamic Routing)**

You can also pass parameters directly in the URL path instead of query strings:

```python
class MyApp(Server):
    def greet(self, name):
        return f"Hello, {name}!"
```

**Access:**
- Using path parameters: [http://127.0.0.1:8080/greet/Alice](http://127.0.0.1:8080/greet/Alice)
  - This will return: `Hello, Alice!`
- Another example: [http://127.0.0.1:8080/greet/John](http://127.0.0.1:8080/greet/John)
  - This will return: `Hello, John!`

#### **Using Both Query and Path Parameters Together**

```python
class MyApp(Server):
    def profile(self, user_id):
        age = self.query_params.get('age', ['Unknown'])[0]
        return f"User ID: {user_id}, Age: {age}"
```

**Access:**
- [http://127.0.0.1:8080/profile/123?age=25](http://127.0.0.1:8080/profile/123?age=25)
  - Returns: `User ID: 123, Age: 25`
- [http://127.0.0.1:8080/profile/456](http://127.0.0.1:8080/profile/456)
  - Returns: `User ID: 456, Age: Unknown`

### **3. Handling POST Requests**

MicroPie supports handling form data submitted via HTTP POST requests. Form data is automatically mapped to method arguments.

#### **Example 1: Handling Form Submission with Default Values**

```python
class MyApp(Server):
    def submit(self, username="Anonymous"):
        return f"Form submitted by: {username}"
```

#### **Example 2: Accessing Raw POST Data**

```python
class MyApp(Server):
    def submit(self):
        username = self.body_params.get('username', ['Anonymous'])[0]
        return f"Submitted by: {username}"
```

#### **Example 3: Handling Multiple POST Parameters**

```python
class MyApp(Server):
    def register(self):
        username = self.body_params.get('username', ['Guest'])[0]
        email = self.body_params.get('email', ['No Email'])[0]
        return f"Registered {username} with email {email}"
```

### 4. **Session Cleanup**
Sessions expire after 8 hours but can be manually cleaned:

```python
class MyApp(Server):
    def cleanup_sessions(self):
        super().cleanup_sessions()
```

### 5. **WSGI Support**
MicroPie includes built-in WSGI support via the wsgi_app() method, allowing you to deploy your applications with WSGI-compatible servers like Gunicorn.

#### **Example**
Create a file named app.py:
```python
from MicroPie import Server

class MyApp(Server):
    def index(self):
        return "Hello, WSGI World!"

app = MyApp()
wsgi_application = app.wsgi_app
```

Run `app.py` with:
```bash
gunicorn app:wsgi_application
```

#### Why Use WSGI?
WSGI (Web Server Gateway Interface) is the standard Python interface between web servers and web applications. Deploying with a WSGI server like Gunicorn provides benefits such as:
- Better Performance: Multi-threaded and multi-process capabilities.
- Scalability: Easily handle multiple requests concurrently.
- Production Readiness: Designed for high-load environments.


## **API Reference**

### Class: Server

#### run(host='127.0.0.1', port=8080)
Starts the HTTP server with the specified host and port.

#### get_session(request_handler)
Retrieves or creates a session for the current request. Sessions are managed via cookies.

#### cleanup_sessions()
Removes expired sessions that have surpassed the timeout period.

#### redirect(location)
Returns a 302 redirect response to the specified URL.

#### render_template(name, **args)
Renders a Jinja2 template with provided context variables.

#### validate_request(method)
Validates incoming requests for both GET and POST methods based on query and body parameters.

#### wsgi_app(environ, start_response)
- Parses incoming HTTP requests and routes them to appropriate handler methods.
- Handles both GET and POST requests.
- Provides response headers and status codes.

## **Examples**
[See the examples folder!](https://github.com/patx/micropie/tree/main/examples)

## **Feature Comparison: MicroPie, Flask, CherryPy, and Bottle**

| Feature             | MicroPie  | Flask     | CherryPy  | Bottle     | Django     |
|--------------------|-----------|-----------|-----------|------------|-------------|
| **Ease of Use**     | Very Easy  | Easy      | Easy      | Easy       | Moderate  |
| **Routing**         | Automatic | Manual    | Manual    | Manual     | Automatic  |
| **Template Engine** | Jinja2     | Jinja2    | None      | SimpleTpl  | Django Templating |
| **Session Handling**| Built-in  | Extension | Built-in  | Plugin     | Built-in   |
| **Request Handling**| Simple    | Flexible  | Advanced  | Simple     | Advanced   |
| **Performance**     | High*     | High      | Moderate  | High       | Moderate   |
| **Scalability**     | Low       | Moderate  | High      | Low        | High       |
| **Built-in Server** | Yes       | No        | Yes       | Yes        | Yes        |
| **WSGI Support**    | Yes       | Yes       | Yes       | Yes        | Yes        |
| **Database Support**| No        | Extension | Plugin    | Plugin     | Built-in   |
| **Middleware**      | Limited   | Extension | Plugin    | Limited    | Extensive  |
| **Plugin Support**  | Limited   | Extensive | Rich      | Limited    | Extensive  |
| **Community Support**| Small    | Large     | Moderate  | Moderate   | Very Large |
| **Deployment**      | Simple    | Moderate  | Moderate  | Simple     | Complex    |

*Note that while MicroPie is high-performing for lightweight applications, it may not scale well for complex, high-traffic web applications due to the lack of advanced features such as asynchronous request handling and database connection pooling, which are found in frameworks like Django and Flask.

## **Have Suggestions or Feedback?**
Please submit your ideas or report any issues via our [GitHub repo](https://github.com/patx/micropie/issues).

