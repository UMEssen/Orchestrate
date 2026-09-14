from utils.output_format import build_db_row,build_result_dict
from utils.postprocessing import insert_db_error, insert_db
def handle_other_modality(ct_names,ct_measures,ct_fmd,ct_study,modalities,result_Topo,i,planes):
   
    modality = modalities[i]
    result = build_result_dict(
        name=ct_names[i],
        regions=ct_measures[i],
        kernel=f"no kernel classification for this modality ({modality})",
        contrast=f"no contrast classification for this modality ({modality})",
        brain_contrast=f"no brain contrast classification for this modality ({modality})",
        foreign_metall=ct_fmd[i]
    )

    if "No DICOM series" in modality:
        db_row = [ct_study,ct_names[i],modality]
        insert_db_error(db_row)

    elif modality == "document":
        db_row = build_db_row(
        study_id=ct_study,
        name=ct_names[i],
        modality=str(modality),
        thickness="no thickness info",
        plane=str(planes[i]),
        topo_result=result_Topo["result"],
        regions="no body regions detections",
        landmarks="no landmarks detections",
        kernel=result["Kernel"],
        contrast=result["Contrast"],
        brain_contrast=result["BrainContrast"],
        foreign_metall=str(ct_fmd[i]),
        plane1=None,
        plane2=None,
        plane3=None
        )
        insert_db(db_row)

    elif planes[i] in ["coronal","sagittal",'lws_bws_hws']:
        db_row = [ct_study,ct_names[i],f"{planes[i]} image, not usable"]
        insert_db_error(db_row)
    elif planes[i] == "axial" and ct_measures[i] == "not axial image":
        db_row = [ct_study,ct_names[i],f"image range not usable"]
        insert_db_error(db_row)
    elif len(ct_measures[i]) == 0:
        db_row = [ct_study,ct_names[i],f"This ct scans did not cover any detected body regions"]
        insert_db_error(db_row)
    else:
        db_row = [ct_study,ct_names[i],str(planes[i])]
        insert_db_error(db_row)

    return result
