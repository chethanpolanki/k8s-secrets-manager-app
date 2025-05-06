import os
import csv
import base64
import yaml
import json
from flask import Flask, request, redirect, url_for, render_template_string, Response, flash, get_flashed_messages

app = Flask(__name__)
app.secret_key = 'super secret key' # Needed for flashing messages

# Directory to store environment CSV files
envs_dir = 'envs'
if not os.path.exists(envs_dir):
    os.makedirs(envs_dir)

# --- Helper Functions ---

def get_envs():
    """Lists all environment CSV files (without .csv extension) in the envs directory."""
    # Ensure envs_dir exists before listing
    if not os.path.exists(envs_dir):
        return []
    return [f[:-4] for f in os.listdir(envs_dir) if f.endswith('.csv')]

def get_secrets(env):
    """Reads secrets from the CSV file for a given environment."""
    path = os.path.join(envs_dir, f"{env}.csv")
    if not os.path.exists(path):
        return []
    secrets_list = []
    try:
        with open(path, newline='', encoding='utf-8') as csvfile:
            # Use DictReader, but handle potential empty files gracefully
            try:
                reader = csv.DictReader(csvfile)
                secrets_list = list(reader)
            except csv.Error:
                # Handle cases where the file might be empty or corrupted
                pass # Return empty list if reading fails
    except Exception as e:
        print(f"Error reading CSV for env {env}: {e}")
        flash(f"Error reading secrets for environment '{env}': {e}", 'error')
        return [] # Return empty list on error
    return secrets_list


def save_secret(env, key, encoded_value):
    """Saves or updates a secret in the CSV file for a given environment."""
    path = os.path.join(envs_dir, f"{env}.csv")
    entries = get_secrets(env)
    updated = False
    # Ensure the key is a string before comparison
    key = str(key)
    for row in entries:
        # Ensure row and row.get('key') are not None before comparison
        if row and str(row.get('key')) == key:
            row['value'] = encoded_value
            updated = True
            break
    if not updated:
        entries.append({'key': key, 'value': encoded_value})

    # Ensure the directory exists before writing
    if not os.path.exists(envs_dir):
        os.makedirs(envs_dir)

    try:
        # Write the updated entries back to the CSV
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['key', 'value']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header only if the file was empty or didn't have one
            # A simple check for file size can indicate if it's empty
            # Also check if entries is empty or the first entry doesn't have a 'key'
            write_header = True
            if os.path.exists(path):
                if os.stat(path).st_size > 0:
                    write_header = False # File is not empty, assume header exists
                elif entries and 'key' in entries[0]:
                     write_header = True # File is empty but we have data, write header

            if write_header:
                 writer.writeheader()

            # Only write rows if there are actual data rows with a 'key'
            if entries and ('key' in entries[0]):
                 writer.writerows(entries)
    except Exception as e:
         print(f"Error writing CSV for env {env}: {e}")
         flash(f"Error saving secrets for environment '{env}': {e}", 'error')
         pass # Continue execution but log the error


# --- Flask Routes ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main index page."""
    envs = get_envs()
    selected_env = request.args.get('env') if 'env' in request.args else None

    # Get flashed messages
    messages = get_flashed_messages(with_categories=True)

    # HTML template with enhanced Tailwind CSS classes and descriptions
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>K8s Secret Manager</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; }
          .flash-message { padding: 1rem; margin-bottom: 1rem; border-radius: 0.375rem; }
          .flash-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
          .flash-error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
          .flash-warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
          .flash-info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
      </head>
      <body class="bg-gray-100 text-gray-800 p-6">
        <div class="container mx-auto max-w-4xl">
          <h1 class="text-3xl font-bold text-blue-700 mb-8 text-center">Kubernetes Secret Manager</h1>

          <p class="mb-8 text-gray-700 text-center max-w-2xl mx-auto">
            This application helps you manage your Kubernetes secrets locally and securely. Organize secrets by environment, easily encode/decode values, and import/export data compatible with Kubernetes Secret YAML.
          </p>

          {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
              <div class="mb-6">
              {% for category, message in messages %}
                <div class="flash-message flash-{{ category }}">{{ message }}</div>
              {% endfor %}
              </div>
            {% endif %}
          {% endwith %}


          <div class="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 class="text-xl font-semibold text-blue-600 mb-4">Manage Environments</h2>
            <p class="text-sm text-gray-600 mb-4">Create different environments (like `uat`, `prod`, `dev`) to keep your secrets organized. Each environment's secrets are stored in a separate file.</p>

            <form action="{{ url_for('select_env') }}" method="post" class="mb-4 border-b pb-4">
              <label for="env_name" class="block text-sm font-medium text-gray-700 mb-2">Add New Environment:</label>
              <div class="flex flex-col sm:flex-row gap-4">
                  <input type="text" id="env_name" name="env_name" placeholder="e.g. uat, prod" required class="flex-grow px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                  <button type="submit" class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">Add Env</button>
              </div>
            </form>

            {% if envs %}
            <div class="flex flex-col sm:flex-row gap-4 items-center">
              <form action="{{ url_for('index') }}" method="get" class="flex flex-grow w-full sm:w-auto gap-4 items-center">
                <label for="select_env" class="block text-sm font-medium text-gray-700">Select Environment:</label>
                <select id="select_env" name="env" class="flex-grow px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                  {% for e in envs %}
                    <option value="{{ e }}" {% if e == selected_env %}selected{% endif %}>{{ e }}</option>
                  {% endfor %}
                </select>
                <button type="submit" class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">Load Env</button>
              </form>
               {% if selected_env %}
               <form action="{{ url_for('delete_env') }}" method="post" onsubmit="return confirm('Are you sure you want to delete the environment \'{{ selected_env }}\'? This cannot be undone.');">
                 <input type="hidden" name="env" value="{{ selected_env }}">
                 <button type="submit" class="px-6 py-2 bg-red-600 text-white font-semibold rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">Delete Selected Env</button>
               </form>
               {% endif %}
            </div>
            {% endif %}
          </div>

          {% if selected_env %}
          <div class="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 class="text-xl font-semibold text-blue-600 mb-4">Working with Environment: <span class="font-bold">{{ selected_env }}</span></h2>

            <form action="{{ url_for('add_secret') }}" method="post" class="mb-6 border-b pb-6">
              <input type="hidden" name="env" value="{{ selected_env }}">
              <h3 class="text-lg font-medium text-gray-700 mb-3">Add/Update Single Secret</h3>
              <p class="text-sm text-gray-600 mb-4">Add a new secret key-value pair or update an existing one. The value you enter will be automatically Base64 encoded.</p>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div>
                  <label for="key" class="block text-sm font-medium text-gray-700 mb-2">Key:</label>
                  <input type="text" id="key" name="key" placeholder="e.g. DATABASE_URL" required class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                </div>
                <div>
                  <label for="value" class="block text-sm font-medium text-gray-700 mb-2">Value:</label>
                  <input type="text" id="value" name="value" placeholder="e.g. postgres://user:pass@host:port/db" required class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                </div>
                <div>
                  <button type="submit" class="w-full px-6 py-2 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">Add/Update Secret</button>
                </div>
              </div>
            </form>

            <div class="mb-6 border-b pb-6">
              <h3 class="text-lg font-medium text-gray-700 mb-3">Actions for this Environment:</h3>
               <p class="text-sm text-gray-600 mb-4">View decoded secrets, edit all secrets in a table, or export secrets in a format suitable for Kubernetes YAML.</p>
              <div class="flex flex-wrap gap-4 items-center">
                <form action="{{ url_for('show') }}" method="get" class="flex items-center gap-4">
                  <input type="hidden" name="env" value="{{ selected_env }}">
                  <label for="show_key" class="text-sm font-medium text-gray-700">Show Decoded Value for Key:</label>
                  <input type="text" id="show_key" name="key" placeholder="e.g. API_KEY" required class="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 w-40">
                  <button type="submit" class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">Show</button>
                </form>

                <form action="{{ url_for('show_all') }}" method="get">
                  <input type="hidden" name="env" value="{{ selected_env }}">
                  <button type="submit" class="px-6 py-2 bg-yellow-600 text-white font-semibold rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2">Edit All Secrets</button>
                </form>

                <form action="{{ url_for('export_env') }}" method="get">
                  <input type="hidden" name="env" value="{{ selected_env }}">
                  <button type="submit" class="px-6 py-2 bg-purple-600 text-white font-semibold rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2">Export (.yaml data block)</button>
                </form>
              </div>
            </div>


            <form action="{{ url_for('bulk_paste') }}" method="post">
              <input type="hidden" name="env" value="{{ selected_env }}">
              <h3 class="text-lg font-medium text-gray-700 mb-3">Bulk Paste from Kubernetes Secret YAML</h3>
              <p class="text-sm text-gray-600 mb-3">
                Paste the `data:` block from a Kubernetes Secret YAML (e.g., output of `kubectl get secret YOUR_SECRET_NAME -o yaml`) here. The application will parse it, decode the Base64 values, and show them for review before you confirm adding/updating them to this environment. This is useful for migrating existing secrets or performing bulk updates.
                Example format:
              </p>
              <pre class="bg-gray-100 p-3 rounded-md text-sm mb-4 overflow-x-auto whitespace-pre-wrap"><code>data:
  MY_SECRET_KEY_1: encoded_value_1
  ANOTHER_KEY: encoded_value_2
...</code></pre>
              <textarea name="bulk" rows="8" placeholder="Paste YAML with 'data:' block here" class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 mb-4"></textarea><br>
              <button type="submit" class="px-6 py-2 bg-teal-600 text-white font-semibold rounded-md hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2">Parse & Review</button>
            </form>
          </div>
          {% endif %}
        </div>
      </body>
    </html>
    """, envs=envs, selected_env=selected_env)


@app.route('/select_env', methods=['POST'])
def select_env():
    """Handles the creation of a new environment."""
    env = request.form['env_name'].strip().lower()
    if not env:
        flash('Environment name cannot be empty.', 'warning')
        return redirect(url_for('index'))

    # Basic validation for environment name
    if not env.isalnum() and '-' not in env and '_' not in env:
         flash('Environment name must be alphanumeric and can contain hyphens or underscores.', 'warning')
         return redirect(url_for('index'))


    path = os.path.join(envs_dir, f"{env}.csv")
    # Create the CSV file if it doesn't exist, add header
    if not os.path.exists(path):
        # Ensure directory exists
        if not os.path.exists(envs_dir):
             os.makedirs(envs_dir)
        try:
            with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['key', 'value'])
                writer.writeheader()
            flash(f"Environment '{env}' created successfully.", 'success')
        except Exception as e:
            print(f"Error creating CSV for new env {env}: {e}")
            flash(f"Error creating environment '{env}': {e}", 'error')
            # Continue execution but log the error
            pass
    else:
        flash(f"Environment '{env}' already exists.", 'info')


    # Redirect to the index page with the new environment selected
    return redirect(url_for('index', env=env))


@app.route('/delete_env', methods=['POST'])
def delete_env():
    """Handles the deletion of an environment."""
    env = request.form.get('env')
    if not env:
        flash('No environment specified for deletion.', 'warning')
        return redirect(url_for('index'))

    path = os.path.join(envs_dir, f"{env}.csv")

    if os.path.exists(path):
        try:
            os.remove(path)
            flash(f"Environment '{env}' deleted successfully.", 'success')
        except Exception as e:
            print(f"Error deleting environment file {path}: {e}")
            flash(f"Error deleting environment '{env}': {e}", 'error')
    else:
        flash(f"Environment '{env}' not found.", 'warning')

    # Redirect back to the index page (without a selected environment)
    return redirect(url_for('index'))


@app.route('/add_secret', methods=['POST'])
def add_secret():
    """Handles adding or updating a single secret."""
    env = request.form['env']
    key = request.form['key'].strip()
    value = request.form['value']

    if not env:
         flash('Environment not specified for adding secret.', 'warning')
         return redirect(url_for('index'))

    if not key:
        flash('Secret key cannot be empty.', 'warning')
        return redirect(url_for('index', env=env))

    try:
        # Base64 encode the value
        encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
        save_secret(env, key, encoded)
        flash(f"Secret '{key}' added/updated successfully in '{env}'.", 'success')
    except Exception as e:
        print(f"Error encoding or saving secret: {e}")
        flash(f"Error adding/updating secret '{key}': {e}", 'error')


    # Redirect back to the index page with the environment selected
    return redirect(url_for('index', env=env))


@app.route('/show', methods=['GET'])
def show():
    """Renders a page showing the decoded value of a single secret."""
    env = request.args.get('env')
    key = request.args.get('key')

    if not env or not key:
         return render_template_string("""
         <!doctype html>
         <html lang="en">
           <head>
             <meta charset="UTF-8">
             <meta name="viewport" content="width=device-width, initial-scale=1.0">
             <title>Error</title>
             <script src="https://cdn.tailwindcss.com"></script>
             <style> body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; } </style>
           </head>
           <body class="bg-gray-100 text-gray-800 p-6">
             <div class="container mx-auto max-w-2xl">
               <h1 class="text-2xl font-bold text-red-700 mb-4">Error</h1>
               <p class="bg-red-100 text-red-800 p-4 rounded-md shadow-md">Environment or Key not specified.</p>
               <a href="{{ url_for('index') }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back Home</a>
             </div>
           </body>
         </html>
         """)


    secrets = get_secrets(env)
    decoded = None
    found = False
    # Ensure key is a string for consistent comparison
    key_str = str(key)
    for row in secrets:
        if str(row.get('key')) == key_str:
            found = True
            try:
                # Decode base64 value
                decoded = base64.b64decode(row.get('value', '')).decode('utf-8')
            except Exception:
                 decoded = '[Invalid base64 or decoding error]' # Handle potential decoding errors
            break

    # HTML template with Tailwind CSS classes
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Show Secret: {{ key }}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; }
        </style>
      </head>
      <body class="bg-gray-100 text-gray-800 p-6">
        <div class="container mx-auto max-w-2xl bg-white p-6 rounded-lg shadow-md">
          <h1 class="text-2xl font-bold text-blue-700 mb-4">Secret: <span class="font-semibold">{{ key }}</span> (<span class="font-semibold">{{ env }}</span>)</h1>
           <p class="text-sm text-gray-600 mb-4">This page shows the decoded value for the selected secret key.</p>
          {% if found %}
            <div class="bg-gray-50 p-4 rounded-md border border-gray-200">
                <strong class="text-blue-600">Decoded Value:</strong> <span class="font-mono break-all text-gray-700">{{ decoded }}</span>
            </div>
          {% else %}
            <p class="bg-yellow-100 text-yellow-800 p-4 rounded-md shadow-md"><em>No such key found or an error occurred while retrieving it.</em></p>
          {% endif %}
          <a href="{{ url_for('index', env=env) }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back to Environment Actions</a>
        </div>
      </body>
    </html>
    """, env=env, key=key, decoded=decoded, found=found)


@app.route('/show_all', methods=['GET'])
def show_all():
    """Renders a page to show and edit all secrets for an environment."""
    env = request.args.get('env')
    if not env:
         return render_template_string("""
         <!doctype html>
         <html lang="en">
           <head>
             <meta charset="UTF-8">
             <meta name="viewport" content="width=device-width, initial-scale=1.0">
             <title>Error</title>
             <script src="https://cdn.tailwindcss.com"></script>
             <style> body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; } </style>
           </head>
           <body class="bg-gray-100 text-gray-800 p-6">
             <div class="container mx-auto max-w-2xl">
               <h1 class="text-2xl font-bold text-red-700 mb-4">Error</h1>
               <p class="bg-red-100 text-red-800 p-4 rounded-md shadow-md">Environment not specified for showing all secrets.</p>
               <a href="{{ url_for('index') }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back Home</a>
             </div>
           </body>
         </html>
         """)


    secrets = get_secrets(env)
    decoded_list = []
    for row in secrets:
        key = str(row.get('key', ''))
        encoded_val = str(row.get('value', ''))
        try:
            # Decode base64 value for display
            decoded_list.append((key, base64.b64decode(encoded_val).decode('utf-8')))
        except Exception:
            # Handle potential decoding errors
            decoded_list.append((key, '[Invalid base64 or decoding error]'))

    # HTML template with Tailwind CSS classes
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edit All Secrets: {{ env }}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; }
        </style>
      </head>
      <body class="bg-gray-100 text-gray-800 p-6">
        <div class="container mx-auto max-w-4xl bg-white p-6 rounded-lg shadow-md">
          <h1 class="text-2xl font-bold text-blue-700 mb-4">Edit All Secrets (<span class="font-semibold">{{ env }}</span>)</h1>
          <p class="text-sm text-gray-600 mb-4">Edit the decoded values for all secrets in this environment. Click "Update All" to save your changes (values will be re-encoded).</p>
          <form action="{{ url_for('update_all') }}" method="post">
            <input type="hidden" name="env" value="{{ env }}">
            {% if decoded_list %}
            <table class="min-w-full divide-y divide-gray-200 mb-6 border border-gray-200 rounded-md overflow-hidden">
              <thead class="bg-gray-50">
                <tr>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Key</th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
              {% for key, val in decoded_list %}
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ key }}</td>
                  <td class="px-6 py-4 text-sm text-gray-500">
                    <input type="hidden" name="keys" value="{{ key }}">
                    <input type="text" name="values" value="{{ val }}" class="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm">
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
            {% else %}
             <p class="bg-yellow-100 text-yellow-800 p-4 rounded-md shadow-md mb-6">No secrets found in this environment yet.</p>
            {% endif %}
            <div class="flex gap-4">
              <button type="submit" class="px-6 py-2 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">Update All</button>
              <button type="button" onclick="window.location='{{ url_for('index', env=env) }}'" class="px-6 py-2 bg-red-600 text-white font-semibold rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">Cancel</button>
            </div>
          </form>
        </div>
      </body>
    </html>
    """, env=env, decoded_list=decoded_list)


@app.route('/update_all', methods=['POST'])
def update_all():
    """Handles updating all secrets from the edit all page."""
    env = request.form['env']
    keys = request.form.getlist('keys')
    values = request.form.getlist('values')

    if not env:
         flash('Environment not specified for updating secrets.', 'warning')
         return redirect(url_for('index'))

    # Iterate through the submitted keys and values
    updated_count = 0
    for key, val in zip(keys, values):
        try:
            # Base64 encode the new value before saving
            encoded = base64.b64encode(val.encode('utf-8')).decode('utf-8')
            save_secret(env, key, encoded)
            updated_count += 1
        except Exception as e:
            print(f"Error encoding or saving secret for key {key}: {e}")
            flash(f"Error updating secret '{key}': {e}", 'error')
            # Continue processing other secrets, but consider logging or user feedback

    if updated_count > 0:
        flash(f"Successfully updated {updated_count} secret(s) in '{env}'.", 'success')

    # Redirect back to the index page with the environment selected
    return redirect(url_for('index', env=env))


@app.route('/export', methods=['GET'])
def export_env():
    """Exports secrets in a Kubernetes Secret YAML data block format."""
    env = request.args.get('env')
    if not env:
         return render_template_string("""
         <!doctype html>
         <html lang="en">
           <head>
             <meta charset="UTF-8">
             <meta name="viewport" content="width=device-width, initial-scale=1.0">
             <title>Error</title>
             <script src="https://cdn.tailwindcss.com"></script>
             <style> body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; } </style>
           </head>
           <body class="bg-gray-100 text-gray-800 p-6">
             <div class="container mx-auto max-w-2xl">
               <h1 class="text-2xl font-bold text-red-700 mb-4">Error</h1>
               <p class="bg-red-100 text-red-800 p-4 rounded-md shadow-md">Environment not specified for export.</p>
               <a href="{{ url_for('index') }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back Home</a>
             </div>
           </body>
         </html>
         """)


    secrets = get_secrets(env)
    # Export in a format similar to kubectl get secret -o yaml data block
    lines = ['data:']
    if not secrets:
        # Add a comment if no secrets are present
        lines.append('  # No secrets defined for this environment')

    for row in secrets:
        # Ensure key and value are treated as strings for the YAML export format
        key = str(row.get('key', ''))
        encoded_value = str(row.get('value', ''))
        # Use YAML-like indentation
        lines.append(f"  {key}: {encoded_value}")
    content = '\n'.join(lines)

    # Return as a plain text response with a .yaml filename
    return Response(
        content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename={env}_secrets.yaml'
        }
    )


@app.route('/bulk_paste', methods=['POST'])
def bulk_paste():
    """Parses pasted Kubernetes Secret YAML data block for review."""
    env = request.form['env']
    bulk_text = request.form['bulk']

    if not env:
         flash('Environment not specified for bulk paste.', 'warning')
         return redirect(url_for('index'))

    parsed_data = {}
    error_message = None

    try:
        # Attempt to parse the pasted text as YAML
        parsed = yaml.safe_load(bulk_text)

        # Check if parsed result is a dictionary and contains a 'data' key which is also a dictionary
        if isinstance(parsed, dict) and 'data' in parsed and isinstance(parsed['data'], dict):
             parsed_data = parsed['data']
        else:
             error_message = "Error: Could not find a 'data' block or it's not in the expected dictionary format."

    except yaml.YAMLError as e:
        error_message = f"Error parsing YAML: {e}"
    except Exception as e:
         error_message = f"An unexpected error occurred during parsing: {e}"

    # If there was a parsing error, display it
    if error_message:
         return render_template_string("""
         <!doctype html>
         <html lang="en">
           <head>
             <meta charset="UTF-8">
             <meta name="viewport" content="width=device-width, initial-scale=1.0">
             <title>Bulk Import Error</title>
             <script src="https://cdn.tailwindcss.com"></script>
             <style> body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; } </style>
           </head>
           <body class="bg-gray-100 text-gray-800 p-6">
             <div class="container mx-auto max-w-2xl bg-white p-6 rounded-lg shadow-md">
               <h1 class="text-2xl font-bold text-red-700 mb-4">Bulk Import Error</h1>
               <p class="text-sm text-gray-600 mb-4">There was an issue parsing the YAML you provided.</p>
               <p class="bg-red-100 text-red-800 p-4 rounded-md shadow-md">{{ error_message }}</p>
               <a href="{{ url_for('index', env=env) }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back to Environment Actions</a>
             </div>
           </body>
         </html>
         """, error_message=error_message, env=env)


    decoded = {}
    # Ensure keys from yaml are treated as strings
    for key, val in parsed_data.items():
        key_str = str(key)
        if isinstance(val, str):
            try:
                # Decode base64 value for review
                decoded[key_str] = base64.b64decode(val).decode('utf-8')
            except Exception:
                # Handle invalid base64 for review
                decoded[key_str] = '[Invalid base64]'
        else:
             # Handle non-string values in the data block for review
             decoded[key_str] = f'[Non-string value: {type(val).__name__}]'

    # Store the original base64 encoded data dictionary for confirmation
    # This prevents issues if decoding/re-encoding happens in the review step
    try:
        bulk_data_encoded_json = base64.b64encode(json.dumps(parsed_data).encode('utf-8')).decode('utf-8')
    except Exception as e:
         return f"<p>Error encoding data for confirmation: {e}</p><a href=\"{url_for('index', env=env)}\">Back</a>"


    # HTML template with Tailwind CSS classes for review page
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Review Bulk Import: {{ env }}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; }
        </style>
      </head>
      <body class="bg-gray-100 text-gray-800 p-6">
        <div class="container mx-auto max-w-4xl bg-white p-6 rounded-lg shadow-md">
          <h1 class="text-2xl font-bold text-blue-700 mb-4">Review Bulk Import (<span class="font-semibold">{{ env }}</span>)</h1>
          {% if decoded %}
            <p class="mb-4 text-gray-700">Review the secrets below. Confirming will add or update these secrets in your <code>{{ env }}.csv</code> file. Existing keys will be overwritten.</p>
            <ul class="bg-gray-50 p-6 rounded-lg shadow-inner mb-6 divide-y divide-gray-200 border border-gray-200">
            {% for key, val in decoded.items() %}
              <li class="py-3">
                <strong class="text-blue-600">{{ key }}</strong>: <span class="font-mono break-all text-gray-700">{{ val }}</span>
              </li>
            {% endfor %}
            </ul>
            <form action="{{ url_for('bulk_confirm') }}" method="post" class="flex flex-col sm:flex-row gap-4">
              <input type="hidden" name="env" value="{{ env }}">
              <input type="hidden" name="bulk_data_encoded_json" value="{{ bulk_data_encoded_json }}">
              <button type="submit" class="px-6 py-2 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">Confirm Import</button>
              <button type="button" onclick="window.location='{{ url_for('index', env=env) }}'" class="px-6 py-2 bg-red-600 text-white font-semibold rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">Cancel</button>
            </form>
          {% else %}
            <p class="bg-yellow-100 text-yellow-800 p-4 rounded-md shadow-md">No valid secrets found under the <code>data:</code> block or failed to process the input.</p>
            <a href="{{ url_for('index', env=env) }}" class="inline-block mt-6 px-6 py-2 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">Back to Environment Actions</a>
          {% endif %}
        </div>
      </body>
    </html>
    """, env=env, decoded=decoded, bulk_data_encoded_json=bulk_data_encoded_json)


@app.route('/bulk_confirm', methods=['POST'])
def bulk_confirm():
    """Confirms the bulk import and saves the secrets."""
    env = request.form['env']
    bulk_data_encoded_json = request.form['bulk_data_encoded_json']

    if not env:
         flash('Environment not specified for confirming bulk import.', 'warning')
         return redirect(url_for('index'))

    try:
        # Decode the original base64 encoded data dictionary (which was JSON)
        data = json.loads(base64.b64decode(bulk_data_encoded_json).decode('utf-8'))
    except Exception:
        flash("Error decoding bulk data for confirmation.", 'error')
        return redirect(url_for('index', env=env))

    # Iterate through the keys and original encoded values from the parsed YAML
    imported_count = 0
    skipped_count = 0
    for key, val in data.items():
         # Ensure key is string and val is string before saving
        if isinstance(val, str):
             try:
                 save_secret(env, str(key), val)
                 imported_count += 1
             except Exception as e:
                 print(f"Error saving secret for key '{key}' during bulk_confirm: {e}")
                 flash(f"Error saving secret '{key}' during bulk import: {e}", 'error')
                 # Continue but count as skipped due to save error
                 skipped_count += 1
        else:
             print(f"Warning: Skipping non-string value for key '{key}' during bulk_confirm.")
             flash(f"Skipped key '{key}' with non-string value during bulk import.", 'warning')
             skipped_count += 1

    if imported_count > 0:
        flash(f"Successfully imported/updated {imported_count} secret(s) in '{env}'.", 'success')
    if skipped_count > 0:
         flash(f"Skipped {skipped_count} key(s) due to errors or non-string values.", 'warning')


    # Redirect back to the index page with the environment selected
    return redirect(url_for('index', env=env))


if __name__ == '__main__':
    # Run the Flask development server
    # In a production environment, use a production-ready WSGI server
    app.run(debug=True) # Set debug=False for production
