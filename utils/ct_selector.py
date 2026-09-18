import cupy as cp
import torch
from .labels import body_organ_labels,body_region_labels,foreign_metall_labels
from .preprocessing import is_ct,get_slice_thickness,store_imagebase64,get_dicom_plane
from .mapping import print_bounds
from .helper import inference_device

def is_image_axial(x1plane,x2plane, threshold= 100):
    """
    Check if the image is axial based on plane coordinate difference
    """
    return cp.abs(x1plane - x2plane) >= threshold

def is_valid_modality(modality):
    """
    Check if the modality is one of the expected types
    """
    
    return modality in ("CT", "PT")



def bbox_filter_by_range(bboxes, lower, upper, device=None):
    """
    Filter bounding boxes that lie within a given vertical range, and compute the percentage of overlap.

    Parameters:
        bboxes: torch.Tensor of shape (N, 4) with boxes [x1, y1, x2, y2]
        lower: scalar int or tensor (Y lower bound)
        upper: scalar int or tensor (Y upper bound)
        device: optional torch device; defaults to ``ORCHESTRATE_DEVICE``

    Returns:
        mask: torch.BoolTensor of shape (N,) - whether each bbox intersects the range
        percentages: torch.FloatTensor of shape (N,) - percent of height within range (0 to 1)
    """
    bboxes = bboxes.to(device or inference_device())
    

    y1 = bboxes[:, 1]
    y2 = bboxes[:, 3]
    height = y2 - y1
   
    lower_tensor = torch.full_like(y1, lower)
    upper_tensor = torch.full_like(y2, upper)

    inter_top = torch.max(lower_tensor, y1)
    inter_bottom = torch.min(upper_tensor, y2)
 

    inter_height = torch.clamp(inter_bottom - inter_top, min=0)
  
    EPSILON = 1e-4
    percentages = inter_height / height.clamp(min=EPSILON)
 
    mask = inter_height > 0
    filtered_percentages = percentages[mask]

    return mask.to("cpu"), filtered_percentages 

def process_ct_scan(
    ct_study,
    topo_series_uid,
    seriesID,
    ct_path,
    topo,
    body_regions_bounding_box,
    body_regions_class,
    result_fmd,
    result_organs,
    result_organs_bbox,
    modality
):
    """
    Process a single CT scan: extract anatomical and modality data,
    determine plane orientation, and apply bounding box filters.
    """
    
    try:
        if modality == "PT":
            plane_result = "Axial" 
        else:
            plane_result = get_dicom_plane(ct_path)
    except:
        return {
            "measures": "dicom error",
            "fmd": "dicom error",
            "landmarks": "dicom error",
            "plane": "Missing ImageOrientationPatient tag in DICOM header",
            "bottom": None,
            "top": None,
            "region_percentage": "dicom error",
            "organ_percentage":"dicom error",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }
        
    try:
        top,bottom = print_bounds(ct_study,topo_series_uid,seriesID)
        if plane_result != "Axial":
            # Non-axial images are skipped from region analysis
            return {
                "measures": "not axial image",
                "fmd": "not axial image",
                "landmarks": "not axial image",
                "plane": plane_result,
                "bottom": bottom,
                "top": top,
                "region_percentage": "not axial image",
                "organ_percentage":"not axial image",
                "plane1":None,
                "plane2":None,
                "plane3":None
            }

        lower, upper = min(bottom, top), max(bottom, top)

        region_mask,region_percentage = bbox_filter_by_range(body_regions_bounding_box, lower, upper)
        filtered_regions = body_regions_class[region_mask].int().tolist()
        region_labels = [body_region_labels[i] for i in filtered_regions]
       
    except:
        return {
            "measures": "dicom error",
            "fmd": "dicom error",
            "landmarks": "dicom error",
            "plane": "no regions for this scans",
            "bottom": None,
            "top": None,
            "region_percentage": "dicom error",
            "organ_percentage":"dicom error",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }
    try:
        organ_mask,organ_percentage = bbox_filter_by_range(result_organs_bbox, lower, upper)
        filtered_organs = result_organs[organ_mask].int().tolist()
        organ_labels = [body_organ_labels[i] for i in filtered_organs]
      
    except:
        return {
            "measures": "dicom error",
            "fmd": "dicom error",
            "landmarks": "dicom error",
            "plane": "no landmarks for this scans",
            "bottom": None,
            "top": None,
            "region_percentage": "dicom error",
            "organ_percentage":"dicom error",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }
    try:
        plane1,plane2,plane3 = store_imagebase64(ct_path)

        # Foreign metal detections
        if result_fmd == "no detections":
            fmd_labels = "no detections"
        else:
            fmd_mask,_ = bbox_filter_by_range(result_fmd["bounding_box"], lower, upper)
            filtered_fmd = result_fmd["class"][fmd_mask].int().tolist()
            fmd_labels = [
                foreign_metall_labels[i] if i < len(foreign_metall_labels) else f"foreign_metal_class_{i}"
                for i in filtered_fmd
            ]
        
        return {
            "measures": region_labels,
            "fmd": fmd_labels,
            "landmarks": organ_labels,
            "plane": plane_result,
            "bottom": bottom,
            "top": top,
            "region_percentage": region_percentage,
            "organ_percentage":organ_percentage,
            "plane1":plane1,
            "plane2":plane2,
            "plane3":plane3
        }

    except Exception as e:
        return {
            "measures": "dicom error",
            "fmd": "dicom error",
            "landmarks": "dicom error",
            "plane": f"Exception Error for image storage: {e}",
            "bottom": None,
            "top": None,
            "region_percentage": "dicom error",
            "organ_percentage":"dicom error",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }

def handle_non_ct_scan(modality):
    """
    Prepare placeholder values for unsupported modalities.
    """
    return {
        "measures": f"no body regions for modality {modality}",
        "fmd": f"no fmd for modality {modality}",
        "landmarks": f"no body landmarks for modality {modality}",
        "plane": "invalid modality",
        "bottom": None,
        "top": None,
        "region_percentage": f"no body regions for modality {modality}",
        "organ_percentage":f"no body landmarks for modality {modality}",
        "plane1":None,
        "plane2":None,
        "plane3":None
    }

def ct_selection(
    ct_study,
    topo_series_uid,
    df_scan,
    body_regions_bounding_box,
    body_regions_class,
    topo,
    result_fmd,
    result_organs,
    result_organs_bbox
):
    """
    Main function to select and analyze CT scans from a study directory.
    Returns metadata and anatomical classification for each scan.
    """
    
    # Output containers
    ct_names, ct_measures, ct_fmd = [], [], []
    bottoms, tops = [], []
    modalities, ct_landmarks, planes, thicknesses = [], [], [], []
    region_percentage,organ_percentage = [],[]
    plane1s,plane2s,plane3s = [],[],[]

  
    path = []
    for row in df_scan.itertuples():
        dicom_paths = row.filepath
        seriesID = row.series
        modality = is_ct(dicom_paths)
        thickness = get_slice_thickness(dicom_paths)
        if is_valid_modality(modality):
            result = process_ct_scan(
                ct_study,
                topo_series_uid,
                seriesID,
                dicom_paths, 
                topo,
                body_regions_bounding_box,
                body_regions_class,
                result_fmd,
                result_organs,
                result_organs_bbox,
                modality
            )
        else:
            
            result = handle_non_ct_scan(modality)

        path.append(dicom_paths)
        ct_names.append(seriesID)
        modalities.append(modality)
        thicknesses.append(thickness)
        ct_measures.append(result["measures"])
        ct_fmd.append(result["fmd"])
        ct_landmarks.append(result["landmarks"])
        planes.append(result["plane"])
        bottoms.append(result["bottom"])
        tops.append(result["top"])
        region_percentage.append(result["region_percentage"])
        organ_percentage.append(result["organ_percentage"])
        plane1s.append(result["plane1"])
        plane2s.append(result["plane2"])
        plane3s.append(result["plane3"])
        
    return (
        ct_names,
        ct_measures,
        bottoms,
        tops,
        ct_fmd,
        modalities,
        ct_landmarks,
        planes,
        thicknesses,
        region_percentage,
        organ_percentage,
        plane1s,
        plane2s,
        plane3s,
        path
    )

def process_ct_scan_lateral(
    ct_path,
    modality
):
    """
    Process a single CT scan: extract anatomical and modality data,
    determine plane orientation, and apply bounding box filters.
    """

    try:
        if modality == "PT":
            plane_result = "Axial"
        else:
            plane_result = get_dicom_plane(ct_path)
    except:
        return {
            "plane": "Missing ImageOrientationPatient tag in DICOM header",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }
    try:
        plane1,plane2,plane3 = store_imagebase64(ct_path)

        return {
            "plane": plane_result,
            "plane1":plane1,
            "plane2":plane2,
            "plane3":plane3
        }

    except Exception as e:
        return {
            "plane": f"Exception Error for image storage: {e}",
            "plane1":None,
            "plane2":None,
            "plane3":None
        }

def ct_selection_lateral(
    df_scan
):
    """
    Main function to select and analyze CT scans from a study directory.
    Returns metadata and anatomical classification for each scan.
    """
    
    # Output containers
    ct_names = []
    modalities, planes, thicknesses = [], [], []
    plane1s,plane2s,plane3s = [],[],[]

  
    path = []
    for row in df_scan.itertuples():
        dicom_paths = row.filepath
        seriesID = row.series
        modality = is_ct(dicom_paths)
        plane = get_dicom_plane(dicom_paths)
        thickness = get_slice_thickness(dicom_paths)
        if is_valid_modality(modality):
            result = process_ct_scan_lateral(
                dicom_paths, 
                modality
            )
        else:
            
            result = handle_non_ct_scan(modality)

        path.append(dicom_paths)
        ct_names.append(seriesID)
        modalities.append(modality)
        thicknesses.append(thickness)
        planes.append(plane)
        plane1s.append(result["plane1"])
        plane2s.append(result["plane2"])
        plane3s.append(result["plane3"])
        
    return (
        ct_names,
        modalities,
        planes,
        thicknesses,
        plane1s,
        plane2s,
        plane3s,
        path
    )
