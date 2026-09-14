import cupy as np
import SimpleITK as sitk
from PIL import Image
import pydicom
import io
import cv2

def read_dicom_series(dicom_paths):
    """
    Reads a DICOM series based on a folder path using SimpleITK.
    Returns a SimpleITK Image object representing the DICOM series.
    """
    # Get the list of DICOM files in the folder

    reader = sitk.ImageSeriesReader()

    # Read the DICOM series
    reader.SetFileNames(dicom_paths)
    image = reader.Execute()

    data = sitk.GetArrayFromImage(image)
    data = np.asarray(data)
    return image, data
  

def get_dicom_plane(dicom_files):

    ds = pydicom.dcmread(dicom_files[0])

    if 'ImageOrientationPatient' not in ds:
        return "Unknown (missing ImageOrientationPatient tag)" # 

    orientation = [float(x) for x in ds.ImageOrientationPatient]
    row_cosines = np.array(orientation[:3])
    col_cosines = np.array(orientation[3:])
    normal = np.cross(row_cosines, col_cosines)


    axis_labels = ['Sagittal', 'Coronal', 'Axial']
    axis_index = np.argmax(np.abs(normal))
    axis_index= np.asnumpy(axis_index)
  
    return axis_labels[axis_index]

def normalize_and_convert_to_uint8(volume, low=-100, high=300):
    """
    Normalizes a numpy volume based on the ranges -1000 and 3000 to 0 and 1,
    and then converts it to an uint8.
    Returns the normalized uint8 volume.
    """
    # Normalize the volume

    volume = np.clip((volume.astype("float32") - low) / (high - low), 0.0, 1.0)

    # Convert the volume to uint8
    volume = (volume * 255).astype(np.uint8)

    return volume
def resize(arr,resize_method,low):
        x_offset = 0
        y_offset = 0
        w_offset = 0
        h_offset = 0
        depth, height, width = arr.shape

        # Use YOLO's preprocessing
        if resize_method is None:
            return arr, (x_offset, y_offset, w_offset, h_offset)

        match resize_method:
            case "padding":
                max_dim = max(height, width)
                start_row = (max_dim - height) // 2
                end_row = start_row + height
                start_col = (max_dim - width) // 2
                end_col = start_col + width

                padded_arr = np.full((depth, max_dim, max_dim), low, dtype=arr.dtype)
                padded_arr[:, start_row:end_row, start_col:end_col] = arr
                arr = padded_arr

                x_offset = -start_col
                y_offset = -start_row
            case "cropping":
                min_dim = min(height, width)
                start_row = (height - min_dim) // 2
                end_row = start_row + min_dim
                start_col = (width - min_dim) // 2
                end_col = start_col + min_dim

                arr = arr[:, start_row:end_row, start_col:end_col]

                x_offset = start_col
                y_offset = start_row
            case "resize":
                # TODO: An x_offset, y_offset, w_offset and h_offset must be implemented for this task
                # The resizing will be automatically performed in _to_png()
                pass

        return arr, (x_offset, y_offset, w_offset, h_offset)
def extract_slices(arr,dynamic,offset,extract_method,num_slices):
    depth = arr.shape[0]

    # Compute the actual offset
    if dynamic:
        # Treat offset as a percentage
        offset = (offset / 100.0) * depth  # Offset remains a float
    else:
        offset = offset

    # Determine indices based on the method
    if extract_method == "center":
        mid_index = (depth - 1) / 2.0
        indices = (
            mid_index
            + (np.arange(num_slices) - (num_slices - 1) / 2.0) * offset
        )
    elif extract_method == "first":
        start_index = 0.0
        indices = start_index + np.arange(num_slices) * offset
    else:
        raise ValueError(
            f"Invalid method. Supported methods are 'center' and 'first'."
        )

    # Clip indices to be within [0, depth - 1]
    indices = np.clip(indices, 0, depth - 1)

    # Round indices to nearest integers
    indices_int = np.round(indices).astype(int)

    # Extract slices using the computed indices
    return np.take(arr, indices_int, axis=0)
def to_png(arr_slice, low, high,dtype,resize_method,imgsz):
        arr_slice = normalize_and_convert_to_uint8(arr_slice, low, high)
        # add 3-channel for RGB
        png = np.stack([arr_slice] * 3, axis=-1)
        png= np.asnumpy(png)
        # cv2.INTER_LANCZOS4 => slower but sometimes better
        if resize_method is not None:
            png = cv2.resize(
                png, (imgsz, imgsz), interpolation=cv2.INTER_LINEAR
            )

        return png


def reorient_to_axial(image):
    """
    Reorients CT image from any orientation to standard axial orientation.
    """
    # LPS = Left-Posterior-Superior (standard axial orientation)
    return sitk.DICOMOrient(image, 'LPS')

def preprocess(dicom_paths,axis,n,num_slices,low,high,dynamic,offset,extract_method,resize_method,dtype,imgsz,percentage=None,plane="Axial"):
        """Preprocess and transcode the incoming data to prepare it for inference.
        The code is from orchestrait
        This step is handled in a separate process.
        Beware that compute intensive tasks may slow down the webserver and are better located on the inference server.
        But if you do not expect high load, this method might be the easiest way to implement preprocessing.

        Args:
            dicom: The path to a DICOM file.

        Returns:
            Any: Do whatever you think is best.
        """

        try:
            def get_z_position(dcm_file):
                    ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
                    return float(ds.ImagePositionPatient[2])
            
            ct_path_sorted = sorted(dicom_paths, key=get_z_position)
            reader = sitk.ImageSeriesReader()
            reader.SetFileNames(ct_path_sorted)  # Use sorted list
            img = reader.Execute()
        except:
            reader = sitk.ImageSeriesReader()
            reader.SetFileNames(dicom_paths)
            img = reader.Execute()

        if plane != 'Axial':
            img = reorient_to_axial(img)
        arr = sitk.GetArrayFromImage(img).astype(np.float32)
        arr = np.asarray(arr)
        if percentage:
            num_to_remove = int(arr.shape[0] * percentage)
            arr = arr[arr.shape[0]-num_to_remove:]
        # Fix DICOM array can have shape (0, ...)
        if arr.shape[0] == 0:
            arr = np.squeeze(arr)
        arr = np.moveaxis(arr, axis, 0)

        low = low if low else np.min(arr)
        high = high if high else np.max(arr)

        match len(arr.shape):
            case 2:
                if n > 1:
                    arr = np.stack([arr] * num_slices, axis=0)
            case 3:
                arr = extract_slices(arr,dynamic,offset,extract_method,num_slices)
            case _:
                raise ValueError(f"Array with shape {arr.shape} is not supported.")

        arr, offsets = resize(arr,resize_method,low)  # TODO implement offsets
        arr_slice = create_gallery(arr,n,num_slices)
        png = to_png(arr_slice, low, high,dtype,resize_method,imgsz)

        return png


def letterbox_resize(img, target_size=(640, 640), color=114):
    """
    Automatically scale image up or down to fit target size using letterbox padding.
    
    Args:
        img (np.ndarray): Input image (HWC)
        target_size (tuple): Target size (width, height)
        color (tuple): Padding color
    
    Returns:
        img_resized (np.ndarray): Padded & resized image
    """
    original_h, original_w = img.shape
  
    target_w, target_h = target_size

    # Calculate scaling ratio
    scale = min(target_w / original_w, target_h / original_h)

    # Compute new image size
    new_w = int(round(original_w * scale))
    new_h = int(round(original_h * scale))

    # Resize and pad
    img = np.asnumpy(img)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    resized = np.asarray(resized)


    img_padded = np.full((target_h, target_w), color, dtype=img.dtype)

    # Compute padding offsets (centered)
    top = (target_h - new_h) // 2
    left = (target_w - new_w) // 2

    # Fill the resized image into the padded canvas
    img_padded[top:top+new_h, left:left+new_w] = resized

    return img_padded # cupy array
def dicoms4yolo_topo(topo_file_path):
    
    try:
        
        topo_image, topo_data = read_dicom_series(topo_file_path)
        img = normalize_and_convert_to_uint8(topo_data[0],-1000,3000) 
        img_padded = letterbox_resize(img)
        png = np.stack([img_padded] * 3, axis=-1) #(640,640,3)        
        return png, topo_image
    except:
        return None, None
        
def nii4yolo_topo(topo_file_path):
    
    try:
        
        topo_image = sitk.ReadImage(topo_file_path)
        topo_data =  sitk.GetArrayFromImage(topo_image)
        img = normalize_and_convert_to_uint8(topo_data[0],-1000,3000)
        img_padded = letterbox_resize(img)
        png = np.stack([img_padded] * 3, axis=-1) #(640,640,3)        
        return png, topo_image
    except:
        return None, None

def create_gallery(arr,n,num_slices):
        depth = arr.shape[0]
        if depth < num_slices:
            # print(
            #     f"Input array depth ({depth}) is less than the expected number of slices ({num_slices}). "
            #     f"Duplicating the first slice {num_slices} times to meet the required depth."
            # )
            arr = np.stack([arr[0, :, :]] * num_slices, axis=0)
        rows = [
            np.hstack(arr[i * n : (i + 1) * n, :, :]) for i in range(n)
        ]
        return np.vstack(rows)
    
def foreign_meta_preprocessing(topo_image):
    data = sitk.GetArrayFromImage(topo_image)
    data = np.asarray(data)
    png = to_png(data[0], low=-200, high=400,dtype=np.uint8,resize_method="resize",imgsz=512)
  
    return png

def kernel_preprocessing(ct_file_path):
        n = 1
        png = preprocess(ct_file_path,axis=0,
                         n=n,num_slices=n**2,
                         low=None,high=None,
                         dynamic=False,offset=1,
                         extract_method="center",
                         resize_method=None,
                         dtype=np.uint8,imgsz=640)
        return png
   

def braincontrast_preprocessing(ct_file_path,percentage=None):
        n = 2
        png = preprocess(ct_file_path,axis=0,
                         n=n,num_slices=n**2,
                         low=None,high=None,
                         dynamic=False,offset=5,
                         extract_method="center",
                         resize_method="padding",
                         dtype=np.uint8,imgsz=640)
        return png

def plane_preprocessing(ct_file_path,axis=0,plane="Axial"):
        n = 2
        try:
            png = preprocess(ct_file_path,axis=axis,
                         n=n,num_slices=n**2,
                         low=None,high=None,
                         dynamic=False,offset=5,
                         extract_method="center",
                         resize_method="padding",
                         dtype=np.uint8,imgsz=640,plane=plane)
  
            return png
        except:
             return "error: can not load dicom"


def contrast_preprocessing(ct_file_path):
        n=2
        png = preprocess(ct_file_path,axis=0,
                         n=n,num_slices=n**2,
                         low=-200,high=400,
                         dynamic=False,offset=5,
                         extract_method="center",
                         resize_method="padding",
                         dtype=np.uint8,imgsz=640)
        return png
       

def get_slice_thickness(dicom_path):
    """
    Extracts the slice thickness from a DICOM file.
    """
    try:
        ds = pydicom.dcmread(dicom_path[0], stop_before_pixels=True)
        thickness = ds.get("SliceThickness", None) # unknown
        return thickness if thickness is not None else "SliceThickness tag not found"
    except Exception as e:
        return f"Error reading DICOM: {e}"


def is_ct(dicom_paths):

    first_file = dicom_paths[0]

    # Load DICOM metadata
    ds = pydicom.dcmread(first_file)

    # Get the Modality (e.g., 'CT', 'MR', 'PT', etc.)
    modality = ds.Modality
    
    return  modality

def encode_plane_to_base64_png(plane_uint8):
    img = Image.fromarray(plane_uint8)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def resize_plane_keep_ratio(img_u8, row_spacing, col_spacing):
    h, w = img_u8.shape
    aspect = (col_spacing / row_spacing)  # width / height physical ratio
    new_w = int(w * aspect)
    new_h = h
    return cv2.resize(img_u8, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
def store_imagebase64(ct_path):
 
    plane = get_dicom_plane(ct_path)

    def get_z_position(dcm_file):
        ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
        return float(ds.ImagePositionPatient[2])

    ct_path_sorted = sorted(ct_path, key=get_z_position)

    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(ct_path_sorted)  # Use sorted list
    img = reader.Execute()

    arr = sitk.GetArrayFromImage(img) 
    
    if plane != 'Axial':
         return None,None,None

    arr = sitk.GetArrayFromImage(img)
    z, y, x = arr.shape
    sx, sy, sz = img.GetSpacing() 
 
    arr = normalize_and_convert_to_uint8(arr)
    # Correct mid-slices (NO transpose)
    axial    = arr[z//2, :, :]
    coronal  = arr[:, y//2, :]
    sagittal = arr[:, :, x//2]

    # Apply spacing-correct aspect ratio
    axial_resized = cv2.resize(
                        axial,
                        None,
                        fx=sx/sy,
                        fy=1.0,
                        interpolation=cv2.INTER_LINEAR,
                    )
    coronal_resized = cv2.resize(
                        coronal,
                        None,
                        fx=sx/sy,
                        fy=sz/sy,
                        interpolation=cv2.INTER_LINEAR,
                    )
    sagittal_resized = cv2.resize(
                        sagittal,
                        None,
                        fx=sy/sx,
                        fy=sz/sy,
                        interpolation=cv2.INTER_LINEAR,
                    )
    
    
    b64_axial    = encode_plane_to_base64_png(axial_resized)
    b64_coronal  = encode_plane_to_base64_png(coronal_resized)
    b64_sagittal = encode_plane_to_base64_png(sagittal_resized)

    return b64_axial, b64_coronal, b64_sagittal
