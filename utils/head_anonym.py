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
    metadata_confidence = 0.0
    
    # Check PatientPosition
    if hasattr(dicom_slices[0], 'PatientPosition'):
        patient_pos = dicom_slices[0].PatientPosition
        details['patient_position'] = patient_pos
        #print(f"  PatientPosition: {patient_pos}")
        
        if patient_pos in ['HFS', 'HFP']: 
            metadata_position = 'end' #Head First: head at END
            metadata_confidence = 0.9
        
        elif patient_pos in ['FFS', 'FFP']:
            metadata_position = 'start'#Feet First: head at START
            metadata_confidence = 0.9
            
        elif patient_pos.startswith('HF'):
            metadata_position = 'end' #Likely Head First
            metadata_confidence = 0.7
            
        elif patient_pos.startswith('FF'):
            metadata_position = 'start' #Likely Feet First
            metadata_confidence = 0.7
            
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
            metadata_confidence = 0.6
            
        elif metadata_position == z_position:
            metadata_confidence = min(metadata_confidence + 0.1, 1.0)
            
        else:
            metadata_confidence *= 0.8  # Reduce confidence
    
    details['metadata_position'] = metadata_position
    details['metadata_confidence'] = metadata_confidence
    
    
    # HU-based detection
    hu_position = None
    hu_confidence = 0.0
    
    # Check if data looks like raw HU
    if ct_array.min() >= 0 and ct_array.max() <= 255:
        print("⚠️ HU analysis NOT reliable on normalized data, Skipping HU analysis")

    elif ct_array.min() < -500: # data appears to be raw HU
        
        try:
            # Use the HU-based detection
            hu_position, hu_score_start, hu_score_end = detect_head_from_hu(ct_array)
            
            # Calculate confidence based on score difference
            score_diff = abs(hu_score_start - hu_score_end)
            hu_confidence = min(score_diff * 2, 1.0)  # Scale to 0-1
            
            details['hu_position'] = hu_position
            details['hu_confidence'] = hu_confidence
            details['hu_score_start'] = hu_score_start
            details['hu_score_end'] = hu_score_end
            
        except Exception as e:
            print(f"❌ HU analysis failed: {e}")
    else:
        print("⚠️Cannot perform reliable HU analysis")
    
    """
    Combining results
    """

    if metadata_position and hu_position: # Both methods are available

        if metadata_position == hu_position:
            final_position = metadata_position
            final_confidence = max(metadata_confidence, hu_confidence)
            method = 'both_agree'
        
        else: # Disagreement - use higher confidence
            if prefer_metadata and metadata_confidence >= 0.7:
                final_position = metadata_position
                final_confidence = metadata_confidence
                method = 'metadata_preferred'
           
            elif metadata_confidence > hu_confidence:
                final_position = metadata_position
                final_confidence = metadata_confidence
                method = 'metadata_higher_confidence'
            else:
                final_position = hu_position
                final_confidence = hu_confidence
                method = 'hu_higher_confidence'
    
    elif metadata_position: # Only metadata available
        final_position = metadata_position
        final_confidence = metadata_confidence
        method = 'metadata_only'
    
    elif hu_position: # Only HU analysis available
        final_position = hu_position
        final_confidence = hu_confidence
        method = 'hu_only'
      
    else:
        # Neither method worked
        raise ValueError(
            "Cannot determine head position. Please use manual_position parameter."
        )
    
    details['final_position'] = final_position
    details['final_confidence'] = final_confidence
    details['method'] = method
       
    return final_position, method, final_confidence, details


def detect_head_from_hu(ct_array, sample_size=5):

    num_slices = ct_array.shape[0]
    sample_size = min(sample_size, num_slices // 4)
    
    # Sample both ends
    start_slices = ct_array[:sample_size]
    end_slices = ct_array[-sample_size:]
    
    # Calculate scores
    start_score = calculate_head_score_simple(start_slices)
    end_score = calculate_head_score_simple(end_slices)
    
    if start_score > end_score:
        position = 'start'
    else:
        position = 'end'
    
    return position, start_score, end_score


def calculate_head_score_simple(slices):
    scores = []
    
    for slice_img in slices:
        mean_intensity = np.mean(slice_img)
        
        std_intensity = np.std(slice_img)
        
        threshold = np.percentile(slice_img, 90)
        high_intensity_ratio = np.sum(slice_img > threshold) / slice_img.size
        
        # Simple score
        score = (
            0.4 * (mean_intensity / (np.max(slice_img) + 1)) +
            0.4 * (std_intensity / (np.max(slice_img) + 1)) +
            0.2 * high_intensity_ratio
        )
        scores.append(score)
    
    return np.mean(scores)


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
       
    # Load DICOM files
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
    

    
    # Load and sort slices
    slices = []
    for filepath in dicom_files:
        ds = pydicom.dcmread(filepath)
        slices.append(ds)
    
    # Sort by slice position
    if hasattr(slices[0], 'ImagePositionPatient'):
        slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
    elif hasattr(slices[0], 'InstanceNumber'):
        slices.sort(key=lambda x: int(x.InstanceNumber))
    
    # Get spacing
    sx, sy, sz = get_spacing_from_dicom(slices)
    
    # Convert to numpy array
    ct_array = np.stack([s.pixel_array for s in slices])
    print(f"Loaded CT shape: {ct_array.shape}")
    print(f"Value range: [{ct_array.min()}, {ct_array.max()}]")
    
    # Detect head position
    
    try:
        head_position, method, confidence, details = detect_head_hybrid(
            slices, ct_array, prefer_metadata
        )
    except ValueError as e:
        print(f"\n❌ Detection failed: {e}")
        raise
    
     # Warning if low confidence
    if confidence < 0.7:
        print(f"\n⚠️  WARNING: Low confidence ({confidence:.2f})")
        print("   Recommend manual verification of results!")

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