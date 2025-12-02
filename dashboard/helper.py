import streamlit as st
from PIL import Image, ImageFile
from io import BytesIO
ImageFile.LOAD_TRUNCATED_IMAGES = True

def set_dark_mode():
    st.markdown("""
    <style>

    /* App background */
    .stApp {
        background-color: black !important;
    }

    /* Apply text color to ALL normal text */
    html, body, [class*="css"] {
        color: #f2d8d8 !important;
        background-color: #1a1a1a !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #f2d8d8 !important;
    }

    /* Radio label text */
    span[role="radio"] label {
        color: #fc8181 !important;
        font-weight: 600 !important;
    }

    /* Radio bullet accent */
    input[type="radio"] {
        accent-color: #fc8181 !important;
    }

    /* Streamlit widgets general text */
    label, .stMarkdown, .stText, .stDataFrame, .stCheckbox, p, div, span {
        color: #f2d8d8 !important;
    }

    /* Buttons */
    div.stButton > button {
        background-color: black !important;
        color: #f2d8d8 !important;
        border-radius: 6px !important;
        border: 1px solid #f2d8d8 !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
    }

    div.stButton > button:hover {
        background-color: #f2d8d8 !important;
        border-color: #1a202c !important;
        color: #9ca0a6 !important;
    }

    </style>
    """, unsafe_allow_html=True)

def dark_table(df):
    styled = (
        df.style
        .hide(axis="index")  
        .set_properties(**{
            "color": "#f2d8d8",
            "background-color": "black",
            "border-color": "#f2d8d8"
        })
        .set_table_styles([
            {"selector": "th", "props": "color: #f2d8d8; background-color: black; border: 1px solid #f2d8d8;"},
            {"selector": "td", "props": "border: 1px solid #f2d8d8;"},
            {"selector": "table", "props": "border-collapse: collapse;"},
        ])
    )

    st.markdown(styled.to_html(), unsafe_allow_html=True)

def dark_table_T(df):
    styled = (
        df.style
        .hide(axis="index")    
        .hide(axis="columns") 
        .set_properties(**{
            "color": "#f2d8d8",
            "background-color": "black",
            "border-color": "#f2d8d8"
        })
        .set_table_styles([
            {"selector": "th", "props": "color: #f2d8d8; background-color: black; border: 1px solid #f2d8d8;"},
            {"selector": "td", "props": "border: 1px solid #f2d8d8;"},
            {"selector": "table", "props": "border-collapse: collapse;"},
        ])
    )

    st.markdown(styled.to_html(), unsafe_allow_html=True)

def decode_png_bytes(png_blob):
    try:
        return Image.open(BytesIO(png_blob)).convert("L")
    except Exception:
        return None
