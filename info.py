import streamlit as st

st.markdown("""
# QueryHunt - SQL Murder Mystery Game 🕵️‍♂️

**QueryHunt** is an interactive SQL game that combines the excitement of a murder mystery with the power of AI. Inspired by the original [SQL Murder Mystery](https://mystery.knightlab.com/), this project challenges players to solve a unique case by running SQL queries against AI-generated data. Built as a hackathon project for [AWS Game Builder Challenge](https://awsdevchallenge.devpost.com/) , QueryHunt uses multiple AWS services, such as Bedrock, RSD and S3.

## Features

- **Engaging Gameplay:** Players use SQL queries to explore data and identify the murderer in a dynamically generated story.
- **AI-Powered Hints:** An AI assistant provides hints based on previous queries to guide players toward the correct solution.
- **Cutting-Edge Tech Stack:** The game leverages Claude 3.5 Sonnet through AWS Bedrock, Llama-Index and Streamlit to deliver a smooth and modern experience.
- **Scalable and Unique:** Each game session is unique, with new stories and data generated every time, ensuring a fresh challenge for every player.

## How It Works

1. **Story Generation:** The AI generates a unique murder mystery story and populates the database with relevant data.
2. **Data Exploration:** Players explore the data by running SQL queries to piece together the clues and identify the murderer.
3. **Hints System:** The AI can offer hints based on the player’s query history, helping them narrow down the suspects.
4. **Victory:** The game ends when the player correctly identifies the murderer.

## Get In Touch

If you want to learn more, contribute, or just say hi, you can connect with me on:

- [![GitHub](https://img.shields.io/badge/GitHub-000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/arsentievalex/aws-queryhunt)
- [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/oleksandr-arsentiev-5554b3168/)
- [![Twitter](https://img.shields.io/badge/X-1DA1F2?style=for-the-badge&logo=x&logoColor=white)](https://x.com/alexarsentiev)

""")
