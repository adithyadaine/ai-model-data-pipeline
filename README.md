# Hugging Face AI Model ETL Pipeline

![Tech Stack](https://img.shields.io/badge/Tech-Airflow%2C%20Docker%2C%20PostgreSQL-blue)
![Python Version](https://img.shields.io/badge/Python-3.9%2B-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An automated ETL (Extract, Transform, Load) data pipeline that fetches the latest AI model metadata from the Hugging Face Hub, processes it, and loads it into a PostgreSQL database. The entire environment is containerized using Docker and orchestrated with Apache Airflow.

## 🚀 Features

-   **Automated Extraction**: Fetches the 50 most recently updated models from the Hugging Face Hub API.
-   **Data Transformation**: Cleans the raw data, handles missing values, and removes duplicates.
-   **Reliable Loading**: Inserts the cleaned data into a PostgreSQL database, handling conflicts for existing models.
-   **Daily Scheduling**: The pipeline is configured to run automatically every day.
-   **Containerized Environment**: Uses Docker and Docker Compose for a one-command setup, ensuring consistency across different machines.
-   **Database Management**: Includes a PgAdmin service to easily view and manage the database.

## ⚙️ Tech Stack & Architecture

-   **Orchestration**: Apache Airflow
-   **Data Source**: Hugging Face Hub API
-   **Database**: PostgreSQL
-   **Containerization**: Docker & Docker Compose
-   **Language**: Python
-   **Database UI**: PgAdmin

### Pipeline Flow

The pipeline follows a standard ETL process orchestrated by an Airflow DAG:

1.  **Extract**: A Python task calls the `huggingface_hub` library to pull the latest 50 models.
2.  **Transform**: A second Python task processes the raw data in memory, ensuring data quality and consistency.
3.  **Load**: The final Python task connects to the PostgreSQL database and uses an `INSERT ... ON CONFLICT` statement to load the data, ensuring idempotency.

## 🔧 Setup and Installation

### Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)
-   [Git](https://git-scm.com/downloads)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd AI-MODEL-DATA-PIPELINE
```

### 2. Configure Environment Variables

Create a `.env` file by copying the example template. This file will store all your sensitive credentials.

```bash
cp .env.example .env
```

Now, **open the `.env` file** and replace the placeholder values with your desired credentials for PostgreSQL, PgAdmin, and the Airflow UI.

### 3. Build and Run the Docker Containers

This command will build the custom Airflow image and start all services (Airflow, Postgres, Redis, PgAdmin) in the background.

```bash
docker-compose up --build -d
```

### 4. Configure the Airflow Connection (Manual Step)

The DAG needs to know how to connect to the PostgreSQL database.

1.  Navigate to the Airflow UI at **`http://localhost:8080`**.
2.  Log in with the username and password you set in your `.env` file (default is `airflow`/`airflow`).
3.  Go to **Admin** -> **Connections**.
4.  Click the `+` button to add a new connection.
5.  Fill in the form with the following details:
    -   **Connection Id**: `model_connection`
    -   **Connection Type**: `Postgres`
    -   **Host**: `postgres` (this is the service name from `docker-compose.yaml`)
    -   **Schema**: `airflow` (or your `POSTGRES_DB` value)
    -   **Login**: Your `POSTGRES_USER` from the `.env` file.
    -   **Password**: Your `POSTGRES_PASSWORD` from the `.env` file.
    -   **Port**: `5432`
6.  Click **Test**. You should see a "Connection successfully tested" message.
7.  Click **Save**.

## ▶️ Running the DAG

1.  In the Airflow UI, you will see the `huggingface_model_etl` DAG.
2.  Click the toggle button on the left to un-pause it.
3.  To run it immediately, click the "Play" button on the right and select "Trigger DAG".

## 📊 Verifying the Data

You can inspect the data loaded by the pipeline using PgAdmin.

1.  Navigate to PgAdmin at **`http://localhost:5050`**.
2.  Log in with the credentials you set in your `.env` file.
3.  Add a new server connection using the same Postgres host (`postgres`), user, and password from your `.env` file.
4.  Navigate to the `ai_models` table to view the data.

## 📂 Project Structure

```text
.
├── dags/
│   └── app.py              # The Airflow DAG file containing the ETL logic.
├── logs/                   # Airflow task logs (ignored by Git).
├── plugins/                # For custom Airflow plugins.
├── .env                    # Local environment variables (SECRET, ignored by Git).
├── .env.example            # Template for environment variables.
├── .gitignore              # Specifies files for Git to ignore.
├── docker-compose.yaml     # Defines and configures all services.
├── Dockerfile              # Builds the custom Airflow image.
└── requirements.txt        # Python dependencies for the project.
```