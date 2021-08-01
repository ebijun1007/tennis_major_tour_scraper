import os
import glob
import pandas as pd

path = "./data/"

all_files = glob.glob(os.path.join(path, "*.csv"))
df_from_each_file = (pd.read_csv(f, sep=',') for f in all_files)
df_merged = pd.concat(df_from_each_file, ignore_index=True).replace("-", "")
df_merged.to_csv("merged.csv", index=False)
