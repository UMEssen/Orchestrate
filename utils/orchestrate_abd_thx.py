
from models.process import KernelClassifier
from models.contrast import ContrastClassifier
from utils.postprocessing import insert_db
from utils.output_format import build_db_row,build_result_dict,insert_subtable

def handle_abd_thx_ct(ct_path,ct_names,ct_measures,
                      ct_fmd,ct_study,modalities,
                      result_Topo,i,ct_landmarks,
                      planes,thicknesses,region_percentage,
                      organ_percentage,plane1,plane2,plane3):


    result_kernel = KernelClassifier(ct_path[i])
    result_contrast = ContrastClassifier(ct_path[i])
    brain_result = "Not calculate in this case"
    result = build_result_dict(
        name=ct_names[i],
        regions=ct_measures[i],
        kernel=result_kernel["result"],
        contrast=result_contrast["result"],
        brain_contrast="Not calculate in this case",
        foreign_metall=ct_fmd[i]
    )

    db_row = build_db_row(
        study_id=ct_study,
        name=ct_names[i],
        modality=str(modalities[i]),
        thickness=str(thicknesses[i]),
        plane=str(planes[i]),
        topo_result=result_Topo["result"],
        regions=str(ct_measures[i]),
        landmarks=str(ct_landmarks[i]),
        kernel=result_kernel["result"],
        contrast=result_contrast["result"],
        brain_contrast=brain_result,
        foreign_metall=str(ct_fmd[i]),
        plane1=plane1[i],
        plane2=plane2[i],
        plane3=plane3[i]
    )
    insert_db(db_row)
    insert_subtable(ct_landmarks,ct_study,ct_names,organ_percentage,ct_measures,region_percentage,i)

    return result
