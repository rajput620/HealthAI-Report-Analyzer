import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

df = pd.read_csv("data/diabetes.csv")

# YOUR REAL COLUMNS
X = df[['age','hypertension','bmi','HbA1c_level','blood_glucose_level']]
y = df['diabetes']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train, y_train)

pickle.dump(model, open("model/diabetes.pkl", "wb"))

print("✅ Diabetes model trained")