import os
import pydicom
import sqlite3
import pandas as pd
from collections import defaultdict, Counter
import ast

def filter(path,dim):
    dim_counter = Counter(dim)

    majority_dim, _ = dim_counter.most_common(1)[0]

    filtered_path = []
    filtered_dim = []

    for p, d in zip(path, dim):
        if d == majority_dim:
            filtered_path.append(p)
            filtered_dim.append(d)
    return filtered_path, filtered_dim


def series_description(ds):
    desc = getattr(ds, 'SeriesDescription', '')
    if isinstance(desc, pydicom.multival.MultiValue):
        desc = ' '.join(str(v) for v in desc)
    return str(desc).lower()


def is_localizer_image_type(ds):
    """
    Checks the ImageType tag for a 'LOCALIZER' entry (case-insensitive).
    ImageType is typically multi-valued, e.g. ['ORIGINAL', 'PRIMARY', 'LOCALIZER'].
    """
    image_type = getattr(ds, 'ImageType', '')
    if isinstance(image_type, pydicom.multival.MultiValue):
        values = [str(v).lower() for v in image_type]
    else:
        values = [str(image_type).lower()]
    return any('localizer' in v for v in values)


def get_series_flag(ds):
    """
    Returns the series description if present; otherwise falls back to
    checking ImageType for a LOCALIZER flag.
    """
    desc = series_description(ds)
    if desc.strip():
        return desc
    if is_localizer_image_type(ds):
        return 'localizer'
    return desc  # stays '' if neither is available

def group_dicom_paths_by_series_with_topogram_flag(folder_path):
    series_dict = defaultdict(list)
    series_descriptions = {}
    dimensions_dict = defaultdict(list)

    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        try:
            ds = pydicom.dcmread(filepath, stop_before_pixels=True)

            series_uid = ds.SeriesInstanceUID

            series_dict[series_uid].append(filepath)

            dims = (getattr(ds, "Rows", None), getattr(ds, "Columns", None))
            dimensions_dict[series_uid].append(dims)

            if series_uid not in series_descriptions:
                series_descriptions[series_uid] = get_series_flag(ds)

        except Exception as e:
            print(f"Skipped {filename}: {e}")

    result = []
    path = []
    flags = []
    dimensions = []

    for series_uid, file_list in series_dict.items():
        result.extend([series_uid])
        path.extend([file_list])
        flags.extend([series_descriptions.get(series_uid, False)])
        dimensions.append(dimensions_dict[series_uid])

    return result, path, flags, dimensions

"""
INSERT INTO DB
"""
   
def insert_db_dcm(ls):
    conn = sqlite3.connect("db/metadata.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO dicom_recevier (studies, series,series_descriptions,filepath)
    VALUES (?, ?, ?,?)
    """, ls)

    conn.commit()
    conn.close()

def insert_db_topo(ls):
    conn = sqlite3.connect("db/metadata.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO topogram (studies, series,series_descriptions,filepath)
    VALUES (?, ?, ?, ?)
    """, ls)
    conn.commit()
    conn.close()

def insert_db_document(ls):
    conn = sqlite3.connect("db/metadata.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO documents (studies, series,series_descriptions)
    VALUES (?, ?, ?)
    """, ls)
    conn.commit()
    conn.close()

def preparation(folder):
    dicom_list,paths,flags,dims = group_dicom_paths_by_series_with_topogram_flag(folder)
    for i in range(len(dicom_list)):
        keywords = ["übersicht","summary","table","chart","proto", "befund", "doc", "report","bericht","stat","info","referenz","snapshot","smart","image","results"]
    
        # Check if any of the keywords are in the path
        if any(keyword in flags[i].lower() for keyword in keywords):

            db_row = [folder.split("/")[-1],dicom_list[i],flags[i]]
            insert_db_document(db_row)
        elif 'top' in flags[i].lower() or 'scout' in flags[i].lower() or 'localizer' in flags[i].lower() or 'surview' in flags[i].lower():

            db_row = [folder.split("/")[-1],dicom_list[i],flags[i],str(paths[i])]
            insert_db_topo(db_row)
        else:
            filtered_path,_ = filter(paths[i],dims[i])
            db_row = [folder.split("/")[-1],dicom_list[i],flags[i],str(filtered_path)]
            insert_db_dcm(db_row)

def read_from_db(db,name):
    conn = sqlite3.connect(db)
    df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
    # Close the connection
    conn.close()
    return df

def read_studies_from_db(db,name,studyID):
    conn = sqlite3.connect(db)
    query = f"SELECT * FROM {name} WHERE studies = ?"
    df = pd.read_sql_query(query, conn, params=(studyID,))
    # Close the connection
    conn.close()
    return df
    
def run_studies(studyID):
    df_topo = read_studies_from_db("db/metadata.db","topogram",studyID)
    df_topo["filepath"] = df_topo["filepath"].apply(ast.literal_eval)
    df_scan = read_studies_from_db("db/metadata.db","dicom_recevier",studyID)
    df_scan ["filepath"] = df_scan["filepath"].apply(ast.literal_eval)
    df_scan = df_scan[df_scan.studies.isin(df_topo.studies.values.tolist())]
    return  df_topo, df_scan


