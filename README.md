[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aws-queryhunt-game.streamlit.app/)

# 🕵️‍♂️ QueryHunt - SQL Murder Mystery Game

**QueryHunt** is an interactive SQL game that combines the excitement of a murder mystery with the power of AI. Inspired by the original [SQL Murder Mystery](https://mystery.knightlab.com/), this project challenges players to solve a unique case by running SQL queries against AI-generated data. Built as a hackathon project for [AWS Game Builder Challenge](https://awsdevchallenge.devpost.com/)

## Architecture

<img src="https://i.postimg.cc/28y6DNs3/Architecture-diagram.png"/>

## Tech Stack

- **AWS RDS:** Stores AI-generated temporary game data, including tables for Victim, Suspects, Evidence, Alibis, and more.
- **Llama-Index:** Manages the workflow for generating and validating game data.
- **Claude 3.5 Sonnet:** Generates unique game stories, data and personalized hints for a player.
- **Streamlit:** Provides the user interface, including a custom SQL editor for running queries.
- **AWS S3** Stores game assets such as favicon, schema image and logo.
- **AWS Bedrock** Enables inference with LLM model.
- **AWS Elastic Beanstalk** Deployment and hosting. Note: currently, the app is on free Streamlit Community Cloud due to costs.

## How It Works

1. **Story Generation:** The AI generates a unique murder mystery story and populates the database with relevant data.
2. **Data Exploration:** Players explore the data by running SQL queries to piece together the clues and identify the murderer.
3. **Hints System:** The AI can offer hints based on the player’s query history, helping them narrow down the suspects.
4. **Victory:** The game ends when the player correctly identifies the murderer.

## Llama-Index Workflow

Below is representation of the Llama-Index workflow that is used to orchestrate multiple LLM calls and ingestion of temporary game data into TiDB Serverless.

<img src="https://i.postimg.cc/NMbg3db1/Llama-Index-Workflow.png"/>

## Getting Started

To set up and run QueryHunt locally:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/arsentievalex/aws-queryhunt.git

2. **Install the required packages:**
   ```bash
   cd aws-queryhunt pip install -r requirements.txt

3. **Replace the following secrets with your credentials:**
   ```bash
   st.secrets["OPENAI_API_KEY"], st.secrets["TIDB_CONNECTION_URL"], st.secrets["TIDB_USER"], st.secrets["TIDB_PASSWORD"]

4. **Run entrypoint app.py:**
   ```bash
   streamlit run app.py
