# Kubernetes Secret Manager (Local Tool)

This is a simple, local web-based application built with Flask to help you manage Kubernetes secrets outside of your cluster. It allows you to organize secrets by environment, handle Base64 encoding/decoding, and import/export secrets in a format compatible with Kubernetes YAML.

**⚠️ IMPORTANT SECURITY WARNING ⚠️**

This tool is designed for **local secret management** and **should not be exposed publicly**. The secret data is stored in plain text CSV files in the `envs` directory relative to where the application is run.

**DO NOT** commit the `envs` directory or any files containing your actual secret values to Git or any version control system. The `.gitignore` file provided with this repository is configured to prevent this, but always double-check.

## Why use this tool?

Managing secrets directly in YAML files can be cumbersome, especially with Base64 encoding. This tool provides a user-friendly interface to:

* **Organize:** Keep secrets for different environments (like `uat`, `prod`) separate.
* **Simplify Encoding:** Automatically handles Base64 encoding when adding/updating secrets and decoding when viewing them.
* **Import/Export:** Easily get secrets into and out of a format compatible with Kubernetes Secret `data:` blocks.
* **Bulk Update:** Paste the `data:` block from an existing Kubernetes Secret YAML to quickly populate or update an environment.

## Installation

You can install this package directly from the GitHub repository using `pip` or `uv`.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/chethanpolanki/k8s-secrets-manager-app.git
    cd k8s-secrets-manager-app
    ```

2.  **Install dependencies using uv (recommended) or pip:**

    Using `uv`:
    ```bash
    uv sync
    ```

    Using `pip`:
    ```bash
    pip install .
    ```
    *(The `.` tells pip to install the package from the current directory)*

    Alternatively, you can install directly from GitHub without cloning the repo first:

    Using `uv`:
    ```bash
    uv pip install git+https://github.com/chethanpolanki/k8s-secrets-manager-app.git
    ```

    Using `pip`:
    ```bash
    pip install git+https://github.com/chethanpolanki/k8s-secrets-manager-app.git
    ```

## Usage

1.  **Run the application:**
    If you installed using `uv sync` or `pip install .` from the cloned repo:
    ```bash
    # Make sure you are in the root directory of the cloned repo
    k8s-secret-manager
    ```
    If you installed directly from GitHub using `uv pip install git+...` or `pip install git+...`:
    ```bash
    # You can run this from any terminal after installation
    k8s-secret-manager
    ```

2.  **Access the web interface:** Open your web browser and go to `http://127.0.0.1:5000/`.

3.  **Manage Environments:**
    * Use the "Add Environment" form to create new environments (e.g., `uat`, `prod`). This will create a corresponding `.csv` file in the `envs` directory.
    * Use the "Select Environment" dropdown to switch between environments.

4.  **Add/Update Secrets:**
    * Select an environment.
    * Use the "Add/Update Single Secret" form to add a new key-value pair or update an existing one. The value will be automatically Base64 encoded.

5.  **View Secrets:**
    * Use the "Show Key" form to view the decoded value of a specific secret.
    * Click "Edit All" to see a table of all secrets in the current environment with their decoded values, and edit them in bulk.

6.  **Export Secrets:**
    * Click the "Export (.yaml data block)" button to download a plain text file containing the `data:` block for the current environment, with keys and Base64 encoded values, ready to be pasted into a Kubernetes Secret YAML file.

7.  **Bulk Paste from Kubernetes:**
    * Select an environment.
    * Paste the `data:` block from the output of `kubectl get secret YOUR_SECRET_NAME -o yaml` into the "Bulk Paste from Kubernetes" textarea.
    * Click "Parse & Review". The application will decode the values and show them to you.
    * Review the secrets. If they look correct, click "Confirm Import" to add/update these secrets in your selected environment's CSV file.

## Development

If you want to modify the code:

1.  Clone the repository.
2.  Navigate to the repository directory.
3.  Install dependencies using `uv sync` or `pip install -e .` (the `-e` flag installs in editable mode).
4.  Run the application using `python -m secrets_manager.main` or simply `k8s-secret-manager` if installed in editable mode.

## Contributing

Feel free to open issues or submit pull requests if you have suggestions or improvements.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/chethanpolanki/k8s-secrets-manager-app/blob/main/LICENSE) file for details.