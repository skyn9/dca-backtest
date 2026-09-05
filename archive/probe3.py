import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import fetch, pandas as pd, json
df = fetch.csindex("H00300")
print("H00300 rows", len(df))
print(df.head(3).to_string()); print(df.tail(3).to_string())
print("date nulls:", df['date'].isna().sum(), " min:", df['date'].min(), " max:", df['date'].max())
print("按年计数:"); print(df.groupby(df['date'].dt.year).size().to_string())
