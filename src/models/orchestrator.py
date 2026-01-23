from .rapid import BodyPartPredictor,BodyRegionDetector, BodyOrganDetector, LateralBrainDetector
from .others import FremdmetallDetector
from .contrast import BrainContrastClassifier
from .process import ViewPositionClassifier
from utils.preprocessing import dicoms4yolo_topo
from utils.postprocessing import insert_db,insert_db_error,insert_db_rapid,insert_deid
from utils.ct_selector import ct_selection,ct_selection_lateral
from utils.orchestrate_abd_thx import handle_abd_thx_ct
from utils.orchestrate_other import handle_other_modality
from utils.head_anonym import defacing
from utils.DCMreceiver import preparation, run_studies
from db.create_table import create_table_candidate,create_table_preprocessing
import sqlite3
import os
import cupy as cp
from multiprocessing import Pool
from functools import partial

def rapid(topo_data,topo):
    result_regions = BodyRegionDetector(topo_data)
    result_landmarks =  BodyOrganDetector(topo_data)
    result_fmd = FremdmetallDetector(topo)
    
    if result_regions!= "no detections" and result_landmarks != "no detections":
        body_regions_bounding_box = result_regions["bounding_box"]
        body_regions_class = result_regions["class"]
 
        result_organs = result_landmarks["class"]
        result_organs_bbox = result_landmarks["bounding_box"]
    else:
        body_regions_bounding_box = None
        body_regions_class = None
        result_organs= None
        result_organs_bbox = None

    
    return body_regions_bounding_box,body_regions_class,result_organs,result_organs_bbox,result_fmd
    

def orchestrate_models(ct_study: str) -> dict:
    create_table_candidate()
    create_table_preprocessing()
    
    studyID = ct_study.split("/")[-1]
    preparation(ct_study) # save data into DB, with topogram db, dicom_recevier db 
    df_topo, df_scan = run_studies(studyID)

    for row in df_topo.itertuples():
        topo_path = row.filepath
        topo_series_uid = row.series
        
        topo_data,topo = dicoms4yolo_topo(topo_path)
        
        if topo_data is None: # candidate table only store valid topogram
            db_row = [ct_study.split("/")[-1],"all series","Topogram can not be proceed correctly"]
            insert_db_error(db_row)
            return {"image_path":ct_study,"results": "Topogram invalid"}
        
        else:
            topo_data = cp.asnumpy(topo_data)
            result_viewposition = ViewPositionClassifier(topo_data)["result"]

            result_Topo = BodyPartPredictor(topo_data)
            body_regions_bounding_box,body_regions_class,result_organs,result_organs_bbox,result_fmd = rapid(topo_data,topo)
            
            db_rapid = [ct_study.split("/")[-1],result_Topo["result"],str(body_regions_class),str(result_organs)]
            insert_db_rapid(db_rapid)

            if result_Topo["result"]=="legs":
                db_row = [ct_study.split("/")[-1],"all series","Special Case: Lower Extremities"]
                insert_db_error(db_row)
            elif result_Topo["result"]=="hands":
                db_row = [ct_study.split("/")[-1],"all series","Special Case: Upper Extremities"]
                insert_db_error(db_row)
            elif result_viewposition == "Lateral" and result_Topo["result"]=="torso":
                db_row = [ct_study.split("/")[-1],"all series","Special Case: Lateral Topogram"]
                insert_db_error(db_row)
            
            else:
                lateral_topo_brain_detect_result = LateralBrainDetector(topo_data)
                if result_viewposition == "Lateral" and lateral_topo_brain_detect_result!= "no detections" and result_Topo["result"]=="brain_neck":             
                    ct_names,modalities,planes,thicknesses,plane1,plane2,plane3,ct_path= ct_selection_lateral(df_scan)
                    ct_cohort = []
                    for i in range(len(modalities)):
                        if modalities[i] == "CT" and planes[i]=="Axial":
                            try:
                                result_braincontrast = BrainContrastClassifier(ct_path[i])
                        
                                dic = {"CT_Scans":ct_names[i],"BrainContrast":result_braincontrast["result"]}
                        
                                db_row = [studyID,ct_names[i],str(modalities[i]),str(thicknesses[i]),str(planes[i]),
                                        "Lateral_Brain","No Region for Lateral","No Landmark for Lateral",
                                        "No region for kernel","No region for contrast",
                                        result_braincontrast["result"],"No foreign metall detection for now",
                                        plane1[i],plane2[i],plane3[i]]
                                insert_db(db_row)
                            except Exception as e:
                                db_row = [ct_study.split("/")[-1],ct_names[i],str(e)]
                                insert_db_error(db_row)
                        elif planes[i]!="Axial":
                            db_row = [ct_study.split("/")[-1],ct_names[i],"Not Axial"]
                            insert_db_error(db_row)

                elif body_regions_bounding_box is None:
                    db_row = [ct_study.split("/")[-1],"all series","No detections (Body Regions detection)"]
                    insert_db_error(db_row)
                    return {"image_path":ct_study,"results": "no detect in this study"}

                else:                   
                    if result_viewposition != "Lateral" and (result_Topo["result"] == "torso" or result_Topo["result"] == "brain_neck"):
                        ct_names,ct_measures,bottoms,tops,ct_fmd,modalities,ct_landmarks,planes,thicknesses,region_percentage,organ_percentage,plane1,plane2,plane3,ct_path = ct_selection(ct_study,topo_series_uid,df_scan,body_regions_bounding_box,body_regions_class,topo,result_fmd,result_organs,result_organs_bbox)
                        #selected ct scans
                        ct_cohort = []
                        for i in range(len(ct_measures)):   
                            if modalities[i]=="CT" and planes[i]=="Axial": 
                                if ('abdominal_region' in ct_measures[i] or 'thoracic_region' in ct_measures[i] or "pericardium" in ct_measures[i]):
                                    
                                    dic = handle_abd_thx_ct(ct_path,ct_names,ct_measures,ct_fmd,studyID,modalities,result_Topo,i,ct_landmarks,planes,thicknesses,region_percentage,organ_percentage,plane1,plane2,plane3)                                
                                    ct_cohort.append(dic)
                                if 'head' in ct_measures[i]: #head deid                                
                                    try:
                                        plane_with_head,plane2_with_removal_head,head_position,num_head_slices = defacing(ct_study,ct_names[i],bottoms[i],tops[i],studyID,body_regions_bounding_box,body_regions_class)
                                        db_row = [ct_study.split("/")[-1],ct_names[i],plane2_with_removal_head,plane_with_head,str(head_position),str(num_head_slices)]
                                        insert_deid(db_row)
                                    except Exception as e:
                                        print("Exception",e)

                                else: # Wrong detections or no detections 
                                    dic = handle_other_modality(ct_names,ct_measures,ct_fmd,studyID,modalities,result_Topo,i,planes)
                                    ct_cohort.append(dic)

                            elif modalities[i]=="PT":  
                                db_row = [ct_study.split("/")[-1],ct_names[i],"PET CT"]
                                insert_db_error(db_row)
                                
                            else: # other modality e.g. False or Empty
                                dic = handle_other_modality(ct_names,ct_measures,ct_fmd,studyID,modalities,result_Topo,i,planes)
                                ct_cohort.append(dic)
                        output = {"study_path":studyID,"result": "complete"}
                        return output
                    
                    else:
                        db_row = [ct_study.split("/")[-1],"all series",result_Topo["result"]]
                        insert_db_error(db_row)
                        return {"image_path":ct_study,"results": {"body_part": result_Topo["result"]}}
        



def process_single_study(study: str, ct_studies: str) -> dict:
    """Process a single study"""
    conn = sqlite3.connect("db/metadata.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT 1 FROM topogram WHERE studies = ?", (study,))
    exists = cursor.fetchone()

    if not exists:
        try:
            path = os.path.join(ct_studies,study)

            result = orchestrate_models(os.path.join(path))
            return {"study_name":study,"result":result}
        except Exception as e:
            print(f"Error processing {study}: {e}")
            return None


def orchestrate_all_study(ct_studies: str) -> list:
    """
    Orchestrate study processing with multiprocessing
    """
    num_processes = 6
    
    create_table_candidate()
    create_table_preprocessing()
    studies = [s for s in os.listdir(ct_studies) if os.path.isdir(os.path.join(ct_studies, s))]
    
    # Create partial function with ct_studies bound
    process_func = partial(process_single_study, ct_studies=ct_studies)
    
    # Process in parallel
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_func, studies)
    
    # Filter out None results
    return [r for r in results if r is not None]