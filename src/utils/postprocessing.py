
import sqlite3

def get_head_position(bbox,label):
    target_label = 0
    indices = (label == target_label).nonzero(as_tuple=True)[0]
    if len(indices)== 0:
        head_y_max = None
    else:
         head_y_max = bbox[indices][0][-1]
    return head_y_max


def select_brain_ct_from_scans(head_y_max,bottom,top):
    distance = head_y_max - min(bottom,top)
    ct_len = max(bottom,top)-min(bottom,top)
    relative_position = distance/ct_len
    return relative_position

def insert_db(ls):
    # print("begin insert")
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO candidate (studies, series, modalities, thicknesses,planes,topo_body_part, series_regions,series_landmarks,ct_series_kernel,ct_series_contrast,ct_series_brain_contrast,ct_series_foreign_metal,plane1,plane2,plane3)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)
    """, ls)

    conn.commit()
    conn.close()
    # print(f" entries inserted successfully.")

def insert_db_regions(ls):
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO regions (studies, series,body_regions,percentage)
    VALUES (?, ?, ?, ?)
    """, ls)

    conn.commit()
    conn.close()
    # print(f" entries inserted successfully.")

def insert_db_landmarks(ls):
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO landmarks (studies, series,body_organs,percentage)
    VALUES (?, ?, ?, ?)
    """, ls)

    conn.commit()
    conn.close()
    # print(f" entries inserted successfully.")

def insert_db_error(ls):
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO errors (studies, series,error_message)
    VALUES (?, ?, ?)
    """, ls)

    conn.commit()
    conn.close()
    # print(f" entries inserted successfully.")

def insert_deid(ls):
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO deid (studies, series,deid_plane,plane,head_position,num_head_slices)
    VALUES (?, ?, ?,?,?,?)
    """, ls)
    print("insert sucessful")
    conn.commit()
    conn.close()
def insert_db_rapid(ls):
    conn = sqlite3.connect("db/orchestrait.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO rapid (studies, body_parts,body_regions,body_organs)
    VALUES (?, ?, ?,?)
    """, ls)

    conn.commit()
    conn.close()
     