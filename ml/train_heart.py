import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle

df = pd.read_csv("data/heart.csv")

X = df[['Age','RestingBP','Cholesterol','MaxHR']]
y = df['HeartDisease']

model = RandomForestClassifier()
model.fit(X, y)

pickle.dump(model, open("model/heart.pkl", "wb"))

print("✅ Heart model trained")