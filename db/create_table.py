import sqlite3
from utils.config import METADATA_DB, OUTPUT_DB, ensure_runtime_directories

def create_table_candidate():
    ensure_runtime_directories()
    conn = sqlite3.connect(OUTPUT_DB)
    cursor = conn.cursor()

    # main table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidate (
        studies TEXT,
        series TEXT,
        modalities TEXT,
        thicknesses TEXT,
        planes TEXT,
        topo_body_part TEXT,
        series_regions TEXT,
        series_landmarks TEXT,
        ct_series_kernel TEXT,
        ct_series_contrast TEXT,
        ct_series_brain_contrast TEXT,
        ct_series_foreign_metal TEXT,
        plane1 BLOB,
        plane2 BLOB,
        plane3 BLOB,
        PRIMARY KEY (studies, series)
    );
    """)

    # subtable for body regions percentage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rapid (
        studies TEXT,
        body_parts TEXT,
        body_regions TEXT,
        body_organs TEXT
    )
    """)

    # subtable for body regions percentage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        studies TEXT,
        series TEXT,
        body_regions TEXT,
        percentage TEXT,
        FOREIGN KEY (studies, series) REFERENCES orchestrait(studies, series)
    )
    """)

    # subtable for body landmarks percentage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS landmarks (
        studies TEXT,
        series TEXT,
        body_organs TEXT,
        percentage TEXT,
        FOREIGN KEY (studies, series) REFERENCES orchestrait(studies, series)
    )
    """)

    # add error table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        studies TEXT,
        series TEXT,
        error_message TEXT,
        UNIQUE (studies, series)  
    )
    """)

    #add table for head deid
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deid (
        studies TEXT,
        series TEXT,
        deid_plane BLOB,
        plane BLOB,
        head_position TEXT,
        num_head_slices TEXT,
        PRIMARY KEY (studies, series)
    );
    """)

    conn.commit()
    conn.close()
    #print("Database and table created successfully.")


def create_table_preprocessing():
    ensure_runtime_directories()
    conn = sqlite3.connect(METADATA_DB)
    cursor = conn.cursor()

    # main table because each study must has a topogram
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topogram (
        studies TEXT PRIMARY KEY ,
        series TEXT,
        series_descriptions TEXT,
        filepath LONGTEXT
        
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dicom_recevier (
        studies TEXT,
        series TEXT,
        series_descriptions TEXT,
        filepath LONGTEXT,
        FOREIGN KEY (studies) REFERENCES topogram(studies)
       
    );
    """)

    # document table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        studies TEXT,
        series TEXT,
        series_descriptions TEXT,
        FOREIGN KEY (studies) REFERENCES topogram(studies)
      
    );
    """)

    conn.commit()
    conn.close()
    #print("Database and table created successfully.")
