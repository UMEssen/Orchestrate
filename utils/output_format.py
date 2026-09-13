from utils.postprocessing import insert_db_landmarks,insert_db_regions

def build_result_dict(name, regions, kernel, contrast, brain_contrast, foreign_metall):
    return {
        "CT_Scans": name,
        "Regions": regions,
        "Kernel": kernel,
        "Contrast": contrast,
        "BrainContrast": brain_contrast,
        "Foreign_metall": foreign_metall,
    }

def build_db_row(study_id, name, modality, thickness, plane, topo_result, regions,
                 landmarks, kernel, contrast, brain_contrast, foreign_metall,plane1,plane2,plane3):

    return [
        study_id,
        name,
        modality,
        thickness,
        plane,
        topo_result,
        regions,
        landmarks,
        kernel,
        contrast,
        brain_contrast,
        foreign_metall,
        plane1,
        plane2,
        plane3
    ]

def insert_subtable(ct_landmarks,ct_study,ct_names,organ_percentage,ct_measures,region_percentage,i):
    for p in range(len(ct_landmarks[i])):
        db_organ_row = [
            ct_study,
            ct_names[i],
            ct_landmarks[i][p],
            str(round(organ_percentage[i][p].item(), 2))
        ]
        insert_db_landmarks(db_organ_row)
    
    for p in range(len(ct_measures[i])):
        db_region_row = [
            ct_study,
            ct_names[i],
            ct_measures[i][p],
            str(round(region_percentage[i][p].item(),2))
        ]
        insert_db_regions(db_region_row)