import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image, ImageFile
from io import BytesIO
import os
ImageFile.LOAD_TRUNCATED_IMAGES = True


conn = sqlite3.connect("orchestrait.db")
cursor = conn.cursor()
query =f"SELECT * FROM deid"
df = pd.read_sql_query(query, conn)
conn.close()


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

set_dark_mode()

def decode_png_bytes(png_blob):
    try:
        return Image.open(BytesIO(png_blob)).convert("L")
    except Exception:
        return None


if "row_index" not in st.session_state:
    st.session_state.row_index = 0

row = df.iloc[st.session_state.row_index]

st.write(f"## CT Series: BLINDED  ({st.session_state.row_index + 1}/{len(df)})")


# Decode and display two images
img1 = decode_png_bytes(row["plane"])
img2 = decode_png_bytes(row["deid_plane"])

if img1 is None or img2 is None: 
    st.warning(f"Skipping row {st.session_state.row_index + 1} (image decode failed)")
    st.session_state.row_index += 1
    st.rerun()
    

col1, col2 = st.columns(2)
with col1:
    st.image(img1.transpose(Image.FLIP_TOP_BOTTOM), caption="Original ", use_container_width=False)
with col2:
    st.image(img2.transpose(Image.FLIP_TOP_BOTTOM), caption="Head Anonymization ", use_container_width=False) 


answers = {}
for label in ["Head_Anonymization"]:
    answers[label] = st.radio(
        "Please rate (1 = Head still there, 5 = Head remove completely )",
        [5, 4, 3, 2, 1],   # 5→1 Likert scale
        format_func=lambda x: f"{x}",
        horizontal=True,
        key=f"{label}_{st.session_state.row_index}"
    )

if st.button("Next"):
    save_row = {
        "series": row["series"],
        "choice": answers["Head_Anonymization"]  # This will be 1–5
    }

    save_df = pd.DataFrame([save_row])
    write_header = not os.path.exists("head_anonymization_review.csv")
    save_df.to_csv("head_anonymization_review.csv", mode="a", index=False, header=write_header)

    if st.session_state.row_index < len(df) - 1:
        st.session_state.row_index += 1
        st.rerun()
    else:
        st.success("Completed!")
