import streamlit as st

st.set_page_config(layout="wide", page_icon="https://queryhunt-game-assets.s3.us-east-1.amazonaws.com/favicon.png")

pages = [
    st.Page("home.py", title="Home"),
    st.Page("sql_mystery_game.py", title="Play"),
    st.Page("leaderboard.py", title="Leaderboard"),
    st.Page("info.py", title="About Project")
]

pg = st.navigation(pages, position="hidden")
pg.run()
