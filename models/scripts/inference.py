from ultralytics import YOLO
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm
import shutil


if __name__ == '__main__':
    test_pngs = Path('data/test')
   
    # Orchestrate
    model = YOLO("runs/classify/orchestrate/weights/best.pt")
    images = sorted(list(test_pngs.rglob('*.png')))
    save_loc = Path('failed')
    save_loc.mkdir(exist_ok=True, parents=True)

    df_dict = {
        'path': [],
        'actual': [],
        'predicted': [],
        'probability': []
    }
    for img in tqdm(images, colour='green', desc='Classifying images'):
        results = model(str(img))  
        df_dict['path'].append(str(Path(*Path(img).parts[-2:])))
        df_dict['actual'].append(img.parts[-2])
        for result in results:
            
            probs = result.probs
            max_probs = max(probs.data)
            prob_idx = (probs.data == max_probs).nonzero().squeeze()

            df_dict['predicted'].append(result.names[prob_idx.item()])
            df_dict['probability'].append(probs.data.cpu().numpy().tolist())

        if df_dict['actual'][-1] != df_dict['predicted'][-1]:
            shutil.copy2(str(img), f"{save_loc}/{img.stem}_{df_dict['actual'][-1]}_{df_dict['predicted'][-1]}.png")


    df = pd.DataFrame(df_dict)
    df['score'] = np.where(df.actual == df.predicted, 1, 0)
    df.to_csv("inference.csv",index=False)
