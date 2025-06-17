import os
import re
import pandas as pd
from shutil import copyfile
from datetime import datetime
from packaging.version import parse as parse_version  # <-- Handles semver correctly
import yaml

# Load YAML config
with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# Dynamic access from config
DERMOSCOPIC_BASE = CONFIG["source_roots"]["dermoscopic"]
CLINICAL_BASE = CONFIG["source_roots"]["clinical"]
MAIN_BASE = CONFIG["source_roots"]["base"]
TARGET_FOLDER = CONFIG["target_roots"]
CLINICAL_CLASSES = set(CONFIG["clinical_classes"])
LABEL_COLUMN_BY_CLASS = CONFIG.get("label_columns", {})
TRAIN_DATA_ROOT = CONFIG["metadata_dir"]

LOG_PATH = os.path.join(CONFIG["log_file_dir"], 'description_'+ str(datetime.now().strftime('%d-%m-%Y_%H.%M.%S'))+'.log')         

# Map class to the correct column that determines the label folder
LABEL_COLUMN_BY_CLASS = {
    "bm": "Folder",
    "multi": "Class",
    "mnm": "Folder",
    "cm": "Folder"
    # Default is 'Folder'
}

def get_label_column(class_name):
    return LABEL_COLUMN_BY_CLASS.get(class_name, "Folder")

def get_source_base(class_name):
    clinical_classes = {"cm"}
    return MAIN_BASE if class_name in clinical_classes else DERMOSCOPIC_BASE

def get_target_base():
    return TARGET_FOLDER

def sync_images_from_sheet(class_name, sheet ,df, label_column, source_base, target_destination):
    synced, missing = 0, 0

    for _, row in df.iterrows():
        try:
            hash_val = str(row['hash value']).strip()
            folder = str(row[label_column]).strip()
        except KeyError as e:
            print(f"⚠️ Missing expected column: {e}")
            continue

        source_path = os.path.join(source_base, hash_val)
        if class_name in {"cm"}:
            source_path = os.path.join(CLINICAL_BASE,hash_val) if folder in {"clinic"} else os.path.join(DERMOSCOPIC_BASE,hash_val)
        else:
            source_path = os.path.join(source_base, hash_val)
        target_path = os.path.join(target_destination, class_name, sheet ,"photos", folder, hash_val)
        if not os.path.exists(target_path):
            if os.path.exists(source_path):
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                copyfile(source_path, target_path)
                synced += 1
                print(f"✅ Synced: {folder}/{hash_val}")
            else:
                missing += 1
                print(source_path)
                print(f"❌ Missing: {folder}/{hash_val}")

    return synced, missing

def sync_images(class_name, metadata_file):
    metadata_path = os.path.join(TRAIN_DATA_ROOT, class_name, metadata_file)
    source_base = get_source_base(class_name)
    label_column = get_label_column(class_name)

    target_destination = get_target_base()

    try:
        xls = pd.ExcelFile(metadata_path)
        
        sheet_names = xls.sheet_names
    except Exception as e:
        print(f"⚠️ Failed to read Excel file: {e}")
        return []

    print(f"\n🔄 Syncing '{class_name}' using column '{label_column}' from sheets: {sheet_names}")
    class_log_entries = []

    for sheet in sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet)
        except Exception as e:
            print(f"⚠️ Skipping sheet '{sheet}' due to error: {e}")
            continue

        synced, missing = sync_images_from_sheet(class_name, sheet ,df, label_column, source_base, target_destination)
        class_log_entries.append(f"{class_name}:{sheet} → {synced} synced, {missing} missing")

    return class_log_entries

def find_latest_metadata_file(class_dir):
    """
    Returns the filename of the latest metadata file for a given class.
    Matches filenames like: metadata_training_bm_2.1.0.xlsx
    """
    metadata_versions = []
    for fname in os.listdir(class_dir):
        match = re.match(r"metadata_training_(\w+)_([\d\.]+)\.xlsx", fname) or re.match(r"metadata_training_(\w+)_with_hash_value_([\d\.]+)\.xlsx", fname)
        if match:
            class_name = match.group(1)
            version_str = match.group(2)
            try:
                version = parse_version(version_str)
                metadata_versions.append((fname, version))
            except Exception:
                continue

    if not metadata_versions:
        return None

    # Sort by version (descending), return the highest
    metadata_versions.sort(key=lambda x: x[1], reverse=True)
    return metadata_versions[0][0]

def sync_all():
    if not os.path.exists(CONFIG["log_file_dir"]):
        os.makedirs(CONFIG["log_file_dir"])

    all_entries = []

    for class_name in os.listdir(TRAIN_DATA_ROOT):
        class_dir = os.path.join(TRAIN_DATA_ROOT, class_name)
        if not os.path.isdir(class_dir):
            continue

        latest_file = find_latest_metadata_file(class_dir)
        if latest_file:
            entries = sync_images(class_name, latest_file)
            all_entries.extend(entries)
        else:
            print(f"⚠️ No metadata files found for class '{class_name}'")

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as log_file:
        log_file.write(f"\n{datetime.now()} Sync Summary\n")
        for entry in all_entries:
            log_file.write(f"{entry}\n")
        log_file.write("------\n")

    print("\n📋 Sync Summary")
    print("\n".join(all_entries))

if __name__ == "__main__":
    sync_all()