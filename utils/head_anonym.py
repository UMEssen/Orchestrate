from utils.postprocessing import get_head_position,select_brain_ct_from_scans
from utils.preprocessing import normalize_and_convert_to_uint8,encode_plane_to_base64_png
import numpy as np
import pydicom
import os
import cv2


def detect_head_hybrid(dicom_slices, ct_array, prefer_metadata=True):
    
    details = {}
    
    # metadata detection
    metadata_position = None
    
    # Check PatientPosition
    if hasattr(dicom_slices[0], 'PatientPosition'):
        patient_pos = dicom_slices[0].PatientPosition
        details['patient_position'] = patient_pos
        #print(f"  PatientPosition: {patient_pos}")
        
        if patient_pos in ['HFS', 'HFP']: 
            metadata_position = 'end' #Head First: head at END
        
        elif patient_pos in ['FFS', 'FFP']:
            metadata_position = 'start'#Feet First: head at START
            
        elif patient_pos.startswith('HF'):
            metadata_position = 'end' #Likely Head First
            
        elif patient_pos.startswith('FF'):
            metadata_position = 'start' #Likely Feet First

            
        else:
            print(f"Unknown position code: {patient_pos}")
    else:
        print("PatientPosition: NOT FOUND")
    
    # Check ImagePositionPatient
    if hasattr(dicom_slices[0], 'ImagePositionPatient') and hasattr(dicom_slices[-1], 'ImagePositionPatient'):
        
        first_z = float(dicom_slices[0].ImagePositionPatient[2])
        last_z = float(dicom_slices[-1].ImagePositionPatient[2])
        
        details['first_z'] = first_z
        details['last_z'] = last_z
        
        if last_z > first_z:
            z_position = 'end' # Z increases: head likely at END

        else:
            z_position = 'start' # Z decreases: head likely at START
        
        # If no PatientPosition, use Z-coordinate
        if metadata_position is None:
            metadata_position = z_position
               
    details['metadata_position'] = metadata_position 
    return metadata_position, details


def get_spacing_from_dicom(dicom_slices):
    if hasattr(dicom_slices[0], 'PixelSpacing'):
        pixel_spacing = dicom_slices[0].PixelSpacing
        sx = float(pixel_spacing[1])
        sy = float(pixel_spacing[0])
    else:
        sx, sy = 1.0, 1.0
    
    if len(dicom_slices) > 1:
        if hasattr(dicom_slices[0], 'ImagePositionPatient'):
            pos1 = np.array(dicom_slices[0].ImagePositionPatient)
            pos2 = np.array(dicom_slices[1].ImagePositionPatient)
            sz = float(np.abs(pos2[2] - pos1[2]))
        elif hasattr(dicom_slices[0], 'SliceThickness'):
            sz = float(dicom_slices[0].SliceThickness)
        elif hasattr(dicom_slices[0], 'SpacingBetweenSlices'):
            sz = float(dicom_slices[0].SpacingBetweenSlices)
        else:
            sz = 1.0
    else:
        sz = 1.0
    
    return sx, sy, sz


def load_and_remove_head_hybrid(folder_path, series_uid, head_percentage=0,prefer_metadata=True):
    dicom_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True)
                if hasattr(ds, 'SeriesInstanceUID') and ds.SeriesInstanceUID == series_uid:
                    dicom_files.append(filepath)
            except:
                continue
    
    if not dicom_files:
        raise ValueError(f"No files found with Series UID: {series_uid}")
    
    slices = []
    for filepath in dicom_files:
        ds = pydicom.dcmread(filepath)
        slices.append(ds)
    
    # Sort by slice position
    if hasattr(slices[0], 'ImagePositionPatient'):
        slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
    elif hasattr(slices[0], 'InstanceNumber'):
        slices.sort(key=lambda x: int(x.InstanceNumber))
    

    sx, sy, sz = get_spacing_from_dicom(slices)
    ct_array = np.stack([s.pixel_array for s in slices])

    # Detect head position
    try:
        head_position, details = detect_head_hybrid(
            slices, ct_array, prefer_metadata
        )
    except ValueError as e:
        print(f"\n❌ Detection failed: {e}")
        raise
    
    # Remove head slices
    num_slices = ct_array.shape[0]
    num_head_slices = int(num_slices * head_percentage)
    
    print("\n" + "="*10)
    print("REMOVING HEAD SLICES")
    print("="*10)
    
    if head_position == 'start':
        removed_array = ct_array[:num_head_slices]
        remaining_array = ct_array[num_head_slices:]
        print(f"Removing FIRST {num_head_slices} slices")
    else:
        removed_array = ct_array[-num_head_slices:]
        remaining_array = ct_array[:-num_head_slices]
        print(f"Removing LAST {num_head_slices} slices")
    
    return ct_array,remaining_array, removed_array, head_position, (sx, sy, sz), num_head_slices



def defacing(ct_study,ct_names,bottoms,tops,studyID,body_regions_bounding_box,body_regions_class):

    head_y_max = get_head_position(body_regions_bounding_box, body_regions_class)
    percentage = select_brain_ct_from_scans(head_y_max, bottoms, tops)
    ct_array,remaining_array, removed, position, spacing,num_head_slices = load_and_remove_head_hybrid(
        ct_study,
        ct_names, 
        head_percentage=percentage.item(),
        prefer_metadata=True  # Trust metadata over HU when both available
    )
    ct_array= normalize_and_convert_to_uint8(ct_array,-1000,3000)
    
    # cv2.imwrite("coronal_version.png",ct_array[:, 256, :])
    remaining_array = normalize_and_convert_to_uint8(remaining_array,-1000,3000)
    # Save coronal view
    mid_slice = remaining_array.shape[1] // 2
    coronal = remaining_array[:, mid_slice, :]
    ct_coronal = ct_array[:, mid_slice, :]
    coronal_resized = cv2.resize(
                        coronal,
                        None,
                        fx=spacing[0]/spacing[1],
                        fy=spacing[-1]/spacing[1],
                        interpolation=cv2.INTER_LINEAR,
                    )
    ct_coronal_resized = cv2.resize(
                        ct_coronal,
                        None,
                        fx=spacing[0]/spacing[1],
                        fy=spacing[-1]/spacing[1],
                        interpolation=cv2.INTER_LINEAR,
                    )
    plane_without_head  = encode_plane_to_base64_png(coronal_resized)
    plane_with_head  = encode_plane_to_base64_png(ct_coronal_resized)
    # cv2.imwrite("coronal_version_remain.png",coronal)
   

    return plane_with_head,plane_without_head,position,num_head_slices