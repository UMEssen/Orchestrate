import streamlit as st
import pandas as pd
import pydicom
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import os
import sqlite3

st.set_page_config(layout="wide", page_title="CT Series Viewer")

@st.cache_data
def load_csv(csv_path: str) -> pd.DataFrame:
    """Load the CSV containing study and series information."""
    return pd.read_csv(csv_path)

@st.cache_data
def load_dicom_series(series_folder: str, series_instance_uid: str) -> tuple:
    """
    Load all DICOM files from a series folder matching the series instance UID.
    Returns tuple of (images_array, slice_locations, pixel_spacing, slice_thickness)
    """
    dicom_files = []
    series_path = Path(series_folder)
    
    # Find all .dcm files and filter by SeriesInstanceUID
    for file in series_path.rglob("*.dcm"):
        try:
            dcm = pydicom.dcmread(str(file))
            # Only include files matching the target SeriesInstanceUID
            if hasattr(dcm, 'SeriesInstanceUID') and dcm.SeriesInstanceUID == series_instance_uid:
                dicom_files.append(dcm)
        except Exception as e:
            st.warning(f"Could not read {file}: {e}")
    
    if not dicom_files:
        return None, None, None, None
    
    # Sort by Instance Number or Slice Location
    try:
        dicom_files.sort(key=lambda x: int(x.InstanceNumber))
    except:
        try:
            dicom_files.sort(key=lambda x: float(x.SliceLocation))
        except:
            st.warning("Could not sort slices properly")
    
    # Extract pixel arrays
    images = []
    slice_locations = []
    
    for dcm in dicom_files:
        img = dcm.pixel_array
        
        # Apply rescale slope and intercept if available
        if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
            img = img * dcm.RescaleSlope + dcm.RescaleIntercept
        
        images.append(img)
        
        if hasattr(dcm, 'SliceLocation'):
            slice_locations.append(dcm.SliceLocation)
        else:
            slice_locations.append(len(slice_locations))
    
 
    images_array = images
    
    # Get pixel spacing for aspect ratio
    pixel_spacing = None
    if hasattr(dicom_files[0], 'PixelSpacing'):
        pixel_spacing = dicom_files[0].PixelSpacing
    
    # Get slice thickness or spacing between slices
    slice_thickness = None
    if hasattr(dicom_files[0], 'SliceThickness'):
        slice_thickness = dicom_files[0].SliceThickness
    elif len(slice_locations) > 1:
        # Calculate from slice locations
        slice_thickness = abs(slice_locations[1] - slice_locations[0])
    
    return images_array, slice_locations, pixel_spacing, slice_thickness

def display_ct_slice(image: np.ndarray, slice_num: int, total_slices: int, 
                     window_center: int = 40, window_width: int = 400, aspect_ratio: float = 1.0):
    """Display a single CT slice with windowing and proper aspect ratio."""
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Apply window/level
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    
    windowed_image = np.clip(image, img_min, img_max)
    
    ax.imshow(windowed_image, cmap='gray', vmin=img_min, vmax=img_max, aspect=aspect_ratio)
    ax.axis('off')
    ax.set_title(f"Slice {slice_num + 1} / {total_slices}", fontsize=14, pad=10)
    
    plt.tight_layout()
    return fig

def main(candidate,region,landmark,deid):
    st.title("Orchestrate Viewer")
    st.markdown("---")
    
    # Main content
    if not os.path.exists(csv_path):
        st.error(f"CSV file not found: {csv_path}")
        st.info("Please update the `csv_path` variable in the code with the correct path.")
        return
    
    if not os.path.exists(studies_folder):
        st.error(f"Studies folder not found: {studies_folder}")
        st.info("Please update the `studies_folder` variable in the code with the correct path.")
        return
    
    # Load CSV
    try:
        df = load_csv(csv_path)
    except Exception as e:
        return
    
    # st.markdown("---")
    
    # Display series
    st.header("Toolbar")

    if 'anonymize' not in st.session_state:
        st.session_state.anonymize = False
    
    # Custom styled button using markdown
    button_text = "Text Anonymization" if not st.session_state.anonymize else "Text De-anoymization"
    
    btn_col1,  btn_col3 = st.columns([1,2])
    with btn_col1:
        st.subheader("Anonymization")
        if st.button(button_text, key="anonymize_btn", type="primary"):
            st.session_state.anonymize = not st.session_state.anonymize
            st.rerun()
    # with btn_col2:
        # Custom HTML button for baby blue
        st.markdown("""
            <style>
            .baby-blue-btn {
                background-color: #FC46AA;
                color: white;
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 0.5rem;
                font-size: 1rem;
                cursor: pointer;
                width: 34%;
                text-align: center;
                font-weight: 400;
            }
            .baby-blue-btn:hover {
                background-color: #6BB6D9;
            }
            </style>
            <button class="baby-blue-btn">Head De-anonymization</button>
        """, unsafe_allow_html=True)

        # TODO: Head De-anonymization
    with btn_col3:
        st.subheader("HU Window Settings")
        
        # Range slider for window (min, max)
        window_range = st.slider(
            "Window Range (Min - Max HU)",
            min_value=-3000,
            max_value=3000,
            value=(-200, 400),
            step=10
        )
        
        # Calculate center and width from range
        window_min = window_range[0]
        window_max = window_range[1]
        window_center = (window_min + window_max) // 2
        window_width = window_max - window_min
            
    # Apply custom CSS for pink button
    st.markdown("""
        <style>
        /* Pink color for primary button (anonymize) */
        button[kind="primary"] {
            background-color: #fa86c4 !important;
            border-color: #fa86c4 !important;
            color: white !important;
          
        }
        button[kind="primary"]:hover {
            background-color: #f76bb8 !important;
            border-color: #f76bb8 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Hardcoded column names
    folder_col = "studies"
    series_uid_col = "series"
    
    # Navigation for series
    if 'current_series_idx' not in st.session_state:
        st.session_state.current_series_idx = 0
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous", disabled=(st.session_state.current_series_idx == 0)):
            st.session_state.current_series_idx -= 1
            st.rerun()
    with col2:
        st.markdown(f"<h3 style='text-align: center;'>Series {st.session_state.current_series_idx + 1} / {len(df)}</h3>", unsafe_allow_html=True)
    with col3:
        if st.button("Next ➡️", disabled=(st.session_state.current_series_idx == len(df) - 1)):
            st.session_state.current_series_idx += 1
            st.rerun()
    
    #st.markdown("---")
    
    # Display current series
    idx = st.session_state.current_series_idx
    row = df.iloc[idx]
    
    # Get folder name and series instance UID
    folder_name = str(row[folder_col])
    series_instance_uid = str(row[series_uid_col])
    
    # Display series metadata
    col1, col2 = st.columns(2)
    with col1:
        display_folder = "BLINDED" if st.session_state.anonymize else folder_name
        st.markdown(f"<p style='font-size:14px;'><b>Study ID:</b> {display_folder}</p>", unsafe_allow_html=True)

    with col2:
        if st.session_state.anonymize:
            display_uid = "BLINDED"
        else:
            display_uid = series_instance_uid[:40] + "..." if len(series_instance_uid) > 40 else series_instance_uid

        st.markdown(f"<p style='font-size:14px;'><b>Series Instance UID:</b> {display_uid}</p>", unsafe_allow_html=True)

    study_folder_path = os.path.join(studies_folder, folder_name)
    
    if not os.path.exists(study_folder_path):
        st.error(f"Study folder not found: {study_folder_path}")
        return
    
    # Load DICOM series
    with st.spinner(f"Loading series..."):
        images, slice_locs, pixel_spacing,slice_thickness = load_dicom_series(study_folder_path, series_instance_uid)
    
    if images is None:
        st.error(f"Could not load DICOM files from: {study_folder_path}")
        return
    
    num_slices = len(images)

    
    #st.markdown("---")
    st.header("Orchestrate Outputs")
    deid = deid[deid.series==str(series_instance_uid)]
    head_anon = int(deid.num_head_slices.values.tolist()[0])
    candidate = candidate[candidate.series==str(series_instance_uid)]
    region = region[region.series==str(series_instance_uid)]
    landmark = landmark[landmark.series==str(series_instance_uid)]
    candidate = candidate[["modalities","thicknesses","ct_series_contrast","ct_series_kernel"]]
    candidate.ct_series_kernel = candidate.ct_series_kernel.apply(lambda x: "Soft" if x == "SK" else "Hard")
    candidate.ct_series_contrast = candidate.ct_series_contrast.apply(lambda x: "Native" if x == "nativ" else "Contrast Enhancement")
    candidate["Anatomical Regions"] = str(region.body_regions.values.tolist()[:-1])
    candidate["Anatomical Landmarks"] = str(landmark.body_organs.values.tolist())

    candidate2 = candidate[["Anatomical Regions","Anatomical Landmarks"]]
    candidate = candidate[["modalities","thicknesses","ct_series_contrast","ct_series_kernel"]]
    st.dataframe(candidate)
    st.dataframe(candidate2)
  
    # TOP ROW: HU Window Controls (Left) and CT Axial Viewer (Right)
    left_col, middle_col,right_col = st.columns([1,1,1.5])
    
    with left_col:
        st.subheader("Coronal View")
        if len(images) > 0 and len(images[0].shape) == 2:
            # Stack images to create 3D volume
            height = images[0].shape[0]
            mid_coronal_idx = height // 2
            
            # Extract coronal slice (same row across all axial slices)
            coronal_slice = np.array([img[mid_coronal_idx, :] for img in images])
            coronal_slice = np.flipud(coronal_slice)
            
            # Coronal: width in-plane (pixel_spacing[1]), height is slice direction (slice_thickness)
            coronal_aspect = 1.0
            if pixel_spacing is not None and slice_thickness is not None:
                coronal_aspect = slice_thickness / pixel_spacing[1]
            
            fig_cor = display_ct_slice(
                coronal_slice[head_anon:,:],
                mid_coronal_idx,
                height,
                window_center,
                window_width,
                aspect_ratio=coronal_aspect
            )
            st.pyplot(fig_cor, use_container_width=False)
            plt.close(fig_cor)
       
    with middle_col:
        st.subheader("Sagittal View")
        # Get mid sagittal slice
        if len(images) > 0 and len(images[0].shape) == 2:
            width = images[0].shape[1]
            mid_sagittal_idx = width // 2
            
            # Extract sagittal slice (same column across all axial slices)
            sagittal_slice = np.array([img[:, mid_sagittal_idx] for img in images])
            sagittal_slice = np.flipud(sagittal_slice)
       
            # Sagittal: width in-plane (pixel_spacing[0]), height is slice direction (slice_thickness)
            sagittal_aspect = 1.0
            if pixel_spacing is not None and slice_thickness is not None:
                sagittal_aspect = slice_thickness / pixel_spacing[0]
            
            fig_sag = display_ct_slice(
                sagittal_slice[head_anon:,:],
                mid_sagittal_idx,
                width,
                window_center,
                window_width,
                aspect_ratio=sagittal_aspect
            )
            st.pyplot(fig_sag, use_container_width=False)
            plt.close(fig_sag)
    with right_col:
        st.subheader("Axial View")
        
        # Slice selector
        slice_num = st.slider(
            "Axial Slice",
            0,
            num_slices - 1,
            num_slices // 2,
            key=f"slice_{idx}"
        )
        
        # Display the axial slice
        fig = display_ct_slice(
            images[slice_num],
            slice_num,
            num_slices,
            window_center,
            window_width
        )
        st.pyplot(fig, use_container_width=False)
        plt.close(fig)
        
        # Show slice location if available
        if slice_locs and slice_num < len(slice_locs):
            st.caption(f"Slice Location: {slice_locs[slice_num]:.2f} mm")
        
        
      
    st.markdown("---")

if __name__ == "__main__":
    csv_path = "path-of-target-cases"  # csv of target use cases
    studies_folder = "path-of-dicom-data"     # raw dicom data
    conn = sqlite3.connect("orchestrait.db") # orchestrate database
    cursor = conn.cursor()
    query =f"SELECT * FROM candidate"
    candidate = pd.read_sql_query(query, conn)
    query_regions =f"SELECT * FROM regions"
    region =  pd.read_sql_query(query_regions, conn)
    query_landmarks =f"SELECT * FROM landmarks"
    landmark =  pd.read_sql_query(query_landmarks, conn)
    query_deid =f"SELECT * FROM deid"
    deid =  pd.read_sql_query(query_deid, conn)
    conn.close()
    main(candidate,region,landmark,deid)
