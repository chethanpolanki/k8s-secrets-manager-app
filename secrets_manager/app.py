import os
import csv
import base64
import yaml
import json
import sys # Import sys to potentially find gunicorn
from flask import Flask, request, redirect, url_for, render_template, Response, flash, get_flashed_messages, jsonify

# Get the absolute path of the directory containing this script (app.py)
basedir = os.path.abspath(os.path.dirname(__file__))
# Construct the path to the templates folder, which is one level up from basedir
template_dir = os.path.join(basedir, '..', 'templates')
# Construct the path to the static folder, which is one level up from basedir
static_dir = os.path.join(basedir, '..', 'static')


# Initialize the Flask application, specifying the template and static folders
app = Flask(__name__,
            template_folder=template_dir,
            static_folder=static_dir)

# Replace with a strong, randomly generated key in production
app.secret_key = os.environ.get('SECRET_KEY', 'a_default_super_secret_key_change_me')

# Directory to store environment CSV files (relative to the project root)
# We can keep this relative as the app will be run from the project root
envs_dir = 'envs'
if not os.path.exists(envs_dir):
    os.makedirs(envs_dir)

# --- Helper Functions ---

def get_envs():
    """Lists all environment CSV files (without .csv extension) in the envs directory."""
    # Ensure envs_dir exists before listing
    if not os.path.exists(envs_dir):
        return []
    try:
        return [f[:-4] for f in os.listdir(envs_dir) if f.endswith('.csv')]
    except Exception as e:
        print(f"Error listing environments: {e}")
        flash(f"Error listing environments: {e}", 'error')
        return []


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

            # Determine if header needs to be written
            write_header = True
            if os.path.exists(path):
                if os.stat(path).st_size > 0:
                    # File has content, check if it has a header row
                    with open(path, 'r', newline='', encoding='utf-8') as f_check:
                        reader_check = csv.reader(f_check)
                        try:
                            first_row = next(reader_check)
                            # Check if the first row matches the expected fieldnames
                            if first_row == fieldnames:
                                write_header = False # Header already exists
                        except StopIteration:
                            pass # File is empty, header needed
                        except Exception:
                            # If there's an error reading the first row,
                            # assume header might be missing or file is malformed, write header
                            pass

            if write_header:
                 writer.writeheader()

            # Only write rows if there are actual data rows with a 'key'
            # Filter out potential empty or malformed rows before writing
            valid_entries = [row for row in entries if row and 'key' in row]
            if valid_entries:
                 writer.writerows(valid_entries)
    except Exception as e:
         print(f"Error writing CSV for env {env}: {e}")
         flash(f"Error saving secrets for environment '{env}': {e}", 'error')
         pass # Continue execution but log the error


def delete_secret_from_csv(env, key):
    """Deletes a secret with the given key from the CSV file for an environment."""
    path = os.path.join(envs_dir, f"{env}.csv")
    entries = get_secrets(env)
    initial_count = len(entries)
    # Ensure key is a string for comparison
    key_str = str(key)
    # Filter out the entry with the matching key
    updated_entries = [row for row in entries if row and str(row.get('key')) != key_str]
    deleted_count = initial_count - len(updated_entries)

    if deleted_count > 0:
        try:
            # Write the remaining entries back to the CSV
            with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['key', 'value']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Always write header if there are entries remaining, or if the file was non-empty initially
                write_header = True
                if not updated_entries and initial_count == 0:
                    write_header = False # File was empty and remains empty
                elif updated_entries:
                    # Check if the file was empty initially but now has entries, or if it had a header
                    if initial_count == 0 or (initial_count > 0 and 'key' in entries[0]):
                        write_header = True # Write header if adding first entry or if header existed
                    else:
                         write_header = False # Header likely didn't exist or file was malformed
                elif initial_count > 0: # File was not empty, but now is after deletion
                     # Check if the file had a header initially
                     with open(path, 'r', newline='', encoding='utf-8') as f_check:
                        reader_check = csv.reader(f_check)
                        try:
                            first_row = next(reader_check)
                            if first_row == fieldnames:
                                write_header = True # Header existed, write it even if file is empty
                        except StopIteration:
                            pass # File is empty, no header needed
                        except Exception:
                            pass # Assume header needed on error


                if write_header:
                     writer.writeheader()

                if updated_entries:
                     writer.writerows(updated_entries)

            return deleted_count # Return number of deleted items (should be 1 if found)
        except Exception as e:
            print(f"Error writing CSV after deleting secret for env {env}: {e}")
            flash(f"Error saving changes after deleting secret '{key}' in '{env}': {e}", 'error')
            return 0 # Indicate deletion failed due to save error
    else:
        # Key not found
        return 0


# --- Flask Routes ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main index page."""
    envs = get_envs()
    selected_env = request.args.get('env') if 'env' in request.args else None
    # Pass flashed messages to the template (handled in base.html)
    return render_template('index.html', envs=envs, selected_env=selected_env)


@app.route('/select_env', methods=['POST'])
def select_env():
    """Handles the creation of a new environment."""
    env = request.form['env_name'].strip().lower()
    if not env:
        flash('Environment name cannot be empty.', 'warning')
        return redirect(url_for('index'))

    # Basic validation for environment name
    if not env.replace('-', '').replace('_', '').isalnum():
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
    redirect_to = request.form.get('redirect_to', 'index') # Get redirect target

    if not env:
         flash('Environment not specified for adding secret.', 'warning')
         if redirect_to == 'show_all':
             # If trying to add from show_all but env is missing, go to index
             return redirect(url_for('index'))
         return redirect(url_for('index'))

    if not key:
        flash('Secret key cannot be empty.', 'warning')
        if redirect_to == 'show_all':
            return redirect(url_for('show_all', env=env))
        return redirect(url_for('index', env=env))

    try:
        # Base64 encode the value
        encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
        save_secret(env, key, encoded)
        flash(f"Secret '{key}' added/updated successfully in '{env}'.", 'success')
    except Exception as e:
        print(f"Error encoding or saving secret: {e}")
        flash(f"Error adding/updating secret '{key}': {e}", 'error')

    # Redirect based on the 'redirect_to' hidden input
    if redirect_to == 'show_all':
        return redirect(url_for('show_all', env=env))
    else:
        return redirect(url_for('index', env=env))


@app.route('/delete_secret', methods=['POST'])
def delete_secret():
    """Handles the deletion of a single secret."""
    env = request.form.get('env')
    key = request.form.get('key')

    if not env or not key:
        flash('Environment or Key not specified for deletion.', 'warning')
        # Redirect back to index, or maybe show_all if possible
        return redirect(url_for('index'))

    deleted_count = delete_secret_from_csv(env, key)

    if deleted_count > 0:
        flash(f"Secret '{key}' deleted successfully from '{env}'.", 'success')
    else:
        flash(f"Secret '{key}' not found in '{env}' or could not be deleted.", 'warning')

    # Redirect back to the show_all page for the current environment
    return redirect(url_for('show_all', env=env))


@app.route('/show', methods=['GET'])
def show():
    """Renders a page showing the decoded value of a single secret."""
    env = request.args.get('env')
    key = request.args.get('key')

    if not env or not key:
         flash('Environment or Key not specified.', 'warning')
         return redirect(url_for('index'))

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

    # Render the show.html template
    return render_template('show.html', env=env, key=key, decoded=decoded, found=found)


@app.route('/show_all', methods=['GET'])
def show_all():
    """Renders a page to show and edit all secrets for an environment."""
    env = request.args.get('env')
    if not env:
         flash('Environment not specified for showing all secrets.', 'warning')
         return redirect(url_for('index'))

    secrets = get_secrets(env)
    decoded_list = []
    for row in secrets:
        key = str(row.get('key', ''))
        encoded_val = str(row.get('value', ''))
        try:
            # Decode base64 value for display
            decoded_list.append({'key': key, 'value': base64.b64decode(encoded_val).decode('utf-8')})
        except Exception:
            # Handle potential decoding errors
            decoded_list.append({'key': key, 'value': '[Invalid base64 or decoding error]'})

    # Render the show_all.html template
    return render_template('show_all.html', env=env, decoded_list=decoded_list)


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

    # Redirect back to the show_all page for the environment
    return redirect(url_for('show_all', env=env))


@app.route('/export', methods=['GET'])
def export_env():
    """Exports secrets in a Kubernetes Secret YAML data block format."""
    env = request.args.get('env')
    if not env:
         flash('Environment not specified for export.', 'warning')
         return redirect(url_for('index'))


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
         # Render the error.html template
         return render_template('error.html', error_message=error_message, env=env)


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
         error_message = f"Error encoding data for confirmation: {e}"
         # Render the error.html template
         return render_template('error.html', error_message=error_message, env=env)


    # Render the bulk_paste_review.html template
    return render_template('bulk_paste_review.html', env=env, decoded=decoded, bulk_data_encoded_json=bulk_data_encoded_json)


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


@app.route('/search_other_envs', methods=['GET'])
def search_other_envs():
    """Searches for a key in environments other than the current one."""
    current_env = request.args.get('current_env')
    search_term = request.args.get('search_term', '').strip().lower()

    if not search_term:
        return jsonify([]) # Return empty list if no search term

    found_in_envs = []
    all_envs = get_envs()

    for env in all_envs:
        # Skip the current environment
        if env == current_env:
            continue

        secrets = get_secrets(env)
        for secret in secrets:
            key = str(secret.get('key', '')).lower()
            # Search only by key for simplicity in this endpoint
            if search_term in key:
                found_in_envs.append(env)
                break # Found in this environment, no need to check other secrets in it

    # Return unique environment names
    return jsonify(list(set(found_in_envs)))

# --- New function to run the server ---
def run_server():
    """Runs the application using Gunicorn."""
    # This function will be the entry point for the script
    # We'll use gunicorn's command line interface via subprocess or os.execv
    # A simpler way for setuptools scripts is to just point to a function
    # that starts the WSGI server. Gunicorn can be started programmatically.

    # Find the gunicorn executable in the virtual environment
    gunicorn_executable = os.path.join(sys.prefix, 'Scripts', 'gunicorn.exe') if sys.platform == "win32" else os.path.join(sys.prefix, 'bin', 'gunicorn')

    if not os.path.exists(gunicorn_executable):
        print("Error: gunicorn executable not found in the virtual environment.")
        print("Please ensure gunicorn is installed (uv add gunicorn or pip install gunicorn)")
        sys.exit(1)

    # Command and arguments for gunicorn
    # We pass the module path 'secrets_manager.app'
    # Gunicorn will find the 'app' object within that module
    command = [
        gunicorn_executable,
        '--workers', '3', # Number of worker processes
        '--bind', '127.0.0.1:5000', # Bind to localhost on port 5000
        'secrets_manager.app:app' # Module:app object
    ]

    print(f"Starting Gunicorn server with command: {' '.join(command)}")
    # Replace the current process with the gunicorn process
    os.execv(gunicorn_executable, command)


if __name__ == '__main__':
    # This block is typically for running the development server directly
    # If running via the entry point script, run_server() is called instead
    # For development, you might still want app.run(debug=True)
    # But for the entry point script, we want Gunicorn
    print("Running Flask development server (use 'k8s-secret-manager' for production-like server)")
    app.run(debug=True)

