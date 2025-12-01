import pandas as pd
import numpy as np
from sklearn.metrics import f1_score, classification_report
from scipy import stats
def bootstrap_f1_ci(y_true, y_pred, average='weighted', n_bootstrap=1000, confidence=0.95):
    bootstrap_scores = []
    n_samples = len(y_true)
    
    for _ in range(n_bootstrap):

        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        y_true_boot = [y_true[i] for i in indices]
        y_pred_boot = [y_pred[i] for i in indices]
        
        score = f1_score(y_true_boot, y_pred_boot, average=average)
        bootstrap_scores.append(score)
    
    # Calculate confidence interval
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_scores, (alpha/2) * 100)
    upper = np.percentile(bootstrap_scores, (1 - alpha/2) * 100)
    
    return np.array(bootstrap_scores), lower, upper

if __name__ == "__main__":

    df = pd.read_csv("inference.csv")

    y_pred = df.predicted.values.tolist()
    y_true = df.actual.values.tolist()

    f1_original = f1_score(y_true, y_pred, average='weighted')
    bootstrap_scores, ci_lower, ci_upper = bootstrap_f1_ci(y_true, y_pred, average='weighted')
    
    print("="*10+"Evaluation"+ "="*10)
    print(f"F1-score: {f1_original:.3f}")
