import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib  # for saving the model


irrigation = pd.read_csv('tomate_irrigation.csv')
del irrigation['hourly_time']

class_names = {
    'OFF': 0,
    'ON': 1,
    'No adjustment': 2,
    'ALERT': 3
}
irrigation['irrigation_status'] = irrigation['irrigation_status'].map(class_names)
irrigation["ts_generation"] = pd.to_datetime(irrigation["ts_generation"])
irrigation.set_index('ts_generation')

# 1. Prepare data
X = irrigation.drop(columns=['irrigation_status', 'ts_generation', 'electrical_conductivity', 'humidity'])
y = irrigation['irrigation_status']
del irrigation['hourly_time']
# 2. Train/test split (time-ordered)
train_size = int(0.70 * len(irrigation))
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# 3. Train model
model = RandomForestClassifier(
    n_estimators=150,
    max_depth=10,
    min_samples_leaf=3,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# 4. Evaluation
print("✅ Train accuracy:", model.score(X_train, y_train))
print("✅ Test accuracy:", model.score(X_test, y_test))
print(classification_report(y_test, model.predict(X_test)))

# 5. Save model
joblib.dump(model, "random_forest_irrigation.pkl")
print("✅ Model saved as 'random_forest_irrigation.pkl'")
