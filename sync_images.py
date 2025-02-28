import os
import pandas as pd
from shutil import copyfile

# Define the source directory where images are stored
SOURCE_DIR = '/media/static/Smruti/AI-Tasks/model_investigation/dvc-experiments/bm_BS'
# Define the target directory to sync images
TARGET_DIR = 'data/bm/images'

# Create the target directory if it doesn't exist
os.makedirs(TARGET_DIR, exist_ok=True)

# Load metadata.xlsx
metadata = pd.read_excel('bm/BS_metadata.xlsx', sheet_name='train-100')

# Iterate over each file path in the 'file' column
for index, row in metadata.iterrows():
    image_path = row['file']
    source_path = os.path.join(SOURCE_DIR, image_path)
    target_path = os.path.join(TARGET_DIR, image_path)

    # Check if the image file exists
    if not os.path.exists(target_path):
        if os.path.exists(source_path):
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # Copy image to the target location
            copyfile(source_path, target_path)
            print(f"Synced: {image_path}")
        else:
            print(f"Missing: {image_path}")