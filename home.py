import streamlit as st
from streamlit.components.v1 import html

# read content from index.html
with open('index.html', 'r') as file:
    html_content = file.read()

html(html_content, height=600)


