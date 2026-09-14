import os
import numpy as np
import pydicom
from collections import defaultdict

def letterbox_params(orig_w, orig_h, target_w, target_h):
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(round(orig_w * scale))

    new_h = int(round(orig_h * scale))
    left  = (target_w - new_w) // 2
    top   = (target_h - new_h) // 2
    return scale, left, top, new_w, new_h

def map_range_native_to_png(i0_native, i1_native, j0_native, j1_native,
                            orig_w, orig_h, target_l=640):
    """Map native coordinates to letterboxed PNG coordinates."""
    scale, left, top, _, _ = letterbox_params(orig_w, orig_h, target_l, target_l)

    # y
    j0_png = int(j0_native * scale) + top
    j1_png = int(j1_native * scale) + top

    # x
    i0_png = int(i0_native * scale) + left
    i1_png = int(i1_native * scale) + left

    # clamp
    j0_png = max(0, min(target_l - 1, j0_png))
    j1_png = max(0, min(target_l - 1, j1_png))
    i0_png = max(0, min(target_l - 1, i0_png))
    i1_png = max(0, min(target_l - 1, i1_png))

    return i0_png, i1_png, j0_png, j1_png

def build_affine(datasets):
    """Build 4x4 affine matrix from DICOM series."""
    if not datasets:
        raise ValueError("Empty series")
    

    ds_with_ipp = [d for d in datasets if hasattr(d, "ImagePositionPatient")]
    
    if not ds_with_ipp:
        raise ValueError("No ImagePositionPatient found")
  
    ds0 = ds_with_ipp[0]
   
    iop = np.asarray(ds0.ImageOrientationPatient, dtype=float)
    row_vec = iop[0:3]  # row direction
    col_vec = iop[3:6]  # column direction
    slice_vec = np.cross(row_vec, col_vec)  # slice normal
   

    if hasattr(ds0, "PixelSpacing") and len(ds0.PixelSpacing) == 2:
        # print("yes")
        dy, dx = map(float, ds0.PixelSpacing)
    else:
        dy, dx = 1.0, 1.0
    
    # sort slices along normal direction
    positions = np.array([np.array(d.ImagePositionPatient, dtype=float) 
                         for d in ds_with_ipp])
    projections = positions @ slice_vec
    sort_order = np.argsort(projections)
    sorted_positions = positions[sort_order]
    sorted_projections = projections[sort_order]

    # slice spacing
    if len(sorted_projections) > 1: # we need at least two slice to calculate the spacing
        gaps = np.abs(np.diff(sorted_projections))
        dz = float(np.median(gaps[gaps > 1e-6])) if gaps[gaps > 1e-6].size else 1.0
    else:
        slice_thickness = getattr(ds0, "SliceThickness", None)
        dz = float(slice_thickness) if slice_thickness is not None else 1.0
        # print("dz",dz)

    affine = np.eye(4)
    affine[0:3, 0] = row_vec * dx
    affine[0:3, 1] = col_vec * dy
    affine[0:3, 2] = slice_vec * dz
    affine[0:3, 3] = sorted_positions[0]
    
    return affine, sort_order, (row_vec, col_vec, dx, dy, sorted_positions)


def load_series(folder):
    """Load all DICOM series from folder."""
    series_map = defaultdict(list)
    for root, _, files in os.walk(folder):
        for f in files:
            try:
                ds = pydicom.dcmread(os.path.join(root, f), force=True)
                if hasattr(ds, "SeriesInstanceUID"):
                    series_map[ds.SeriesInstanceUID].append(ds)
            except:
                pass

    return series_map


def print_bounds(folder, uid_A, uid_B):
    """
    - Topogram y_max (maximum y across all slices)
    - Topogram y_min (minimum y across all slices)
    - Series y_max (maximum y across all slices)
    - Series y_min (minimum y across all slices)
    """

    series_map = load_series(folder)
    if uid_A not in series_map or uid_B not in series_map:
        raise ValueError("Series UIDs not found")
    
    series_A = series_map[uid_A]
    series_B = series_map[uid_B]
    #print(f"Total number of ct slices {len(series_A)}")

   
    affine_A, order_A, (row_A, col_A, dx_A, dy_A, pos_A) = build_affine(series_A)
    affine_B, order_B, (row_B, col_B, dx_B, dy_B, pos_B) = build_affine(series_B)
    
    ds_A = series_A[order_A[0]]
    h_A, w_A = int(ds_A.Rows), int(ds_A.Columns)
    ds_B = series_B[order_B[0]]
    h_B, w_B = int(ds_B.Rows), int(ds_B.Columns)
    
    # bounds for Series A
    y_A_values = []
    for slice_idx in range(len(series_A)):
        corners = np.array([
            [0, 0, slice_idx],
            [w_A - 1, 0, slice_idx],
            [w_A - 1, h_A - 1, slice_idx],
            [0, h_A - 1, slice_idx],
        ])
        
        corners_hom = np.c_[corners, np.ones(len(corners))]
        phys = (affine_A @ corners_hom.T).T[:, :3]
        y = phys @ col_A
        y_A_values.extend(y)
    
    # bounds for Series B (project into A's coordinate system)
    y_B_values = []
    for slice_idx in range(len(series_B)):
        corners = np.array([
            [0, 0, slice_idx],
            [w_B - 1, 0, slice_idx],
            [w_B - 1, h_B - 1, slice_idx],
            [0, h_B - 1, slice_idx],
        ])
        
        corners_hom = np.c_[corners, np.ones(len(corners))]
        phys = (affine_B @ corners_hom.T).T[:, :3]
        y = phys @ col_A
        y_B_values.extend(y)
    
 
    y_A_max_mm = np.max(y_A_values)
    y_A_min_mm = np.min(y_A_values)
    y_B_max_mm = np.max(y_B_values)
    y_B_min_mm = np.min(y_B_values)
    
    y_A_max_px = y_A_max_mm / dy_A
    y_A_min_px = y_A_min_mm / dy_A
    y_B_max_px = y_B_max_mm / dy_A
    y_B_min_px = y_B_min_mm / dy_A

    topo_max_px = y_A_max_px - y_A_min_px
    topo_min_px = 0
    series_max_px = y_B_max_px - y_A_min_px 
    series_min_px = y_B_min_px - y_A_min_px if y_A_min_px < y_B_min_px else 0

    _, _, series_min_px_png, series_max_px_png = map_range_native_to_png(
        0, 0, series_min_px, series_max_px,
        orig_w=512, orig_h=512
    )
    
    return series_min_px_png, series_max_px_png