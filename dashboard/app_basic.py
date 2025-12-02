import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image, ImageFile
from helper import set_dark_mode, dark_table_T,dark_table,decode_png_bytes
ImageFile.LOAD_TRUNCATED_IMAGES = True


# Load database
conn = sqlite3.connect("orchestrait.db")
cursor = conn.cursor()
query =f"SELECT * FROM candidate"
df = pd.read_sql_query(query, conn)
query_regions =f"SELECT * FROM regions"
region =  pd.read_sql_query(query_regions, conn)
query_landmarks =f"SELECT * FROM landmarks"
landmark =  pd.read_sql_query(query_landmarks, conn)
conn.close()


set_dark_mode()


if "row_index" not in st.session_state:
    st.session_state.row_index = 0

row = df.iloc[st.session_state.row_index]
st.write(f"## Series: BLINDED  ({st.session_state.row_index + 1}/{len(df)})")


# Decode and display two images
img1 = decode_png_bytes(row["plane1"])
img2 = decode_png_bytes(row["plane2"])
img3 = decode_png_bytes(row["plane3"])

if img1 is None or img2 is None or img3 is None:
    st.warning(f"Skipping row {st.session_state.row_index + 1} (image decode failed)")
    st.session_state.row_index += 1
    st.rerun()
    
col1, col2 ,col3 = st.columns(3)
with col1:
    st.image(img1, caption="Axial ", use_container_width=False)
with col2:
    st.image(img2.transpose(Image.FLIP_TOP_BOTTOM), caption="Coronal", use_container_width=False)
with col3:
    st.image(img3.transpose(Image.FLIP_TOP_BOTTOM), caption="Sagittal", use_container_width=False)


st.write(f"### Orchestrate Results")
data = [
    { "Thickness":row["thicknesses"],
      "Kernel": row["ct_series_kernel"],
      "Body Contrast": row["ct_series_contrast"],
      "Brain Contrast": row["ct_series_brain_contrast"]
    }
]
data_df = pd.DataFrame(data)  # removes index + header
dark_table(data_df)



st.write(f"### Body Regions Results")
region_result = region[region["series"]== row["series"]]
region_result_T = region_result[["body_regions","percentage"]].T.reset_index()

dark_table_T(region_result_T)



st.write(f"### Body Landmarks Results")
landmark_result = landmark.loc[landmark["series"] == row["series"]]
dark_table_T(landmark_result[["body_organs","percentage"]].T.reset_index())



if st.button("Next"):
    
    if st.session_state.row_index < len(df) - 1:
        st.session_state.row_index += 1
        st.rerun()
    else:
        st.success("End")
