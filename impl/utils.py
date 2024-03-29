import time
from configuration import DEBUG, STREAM_FILE_PATH, MODEL_FILE_PATH, TIMEZONE, SAVE_MODEL, COMPONENTS
import pandas as pd
import numpy as np
import json
import pickle
import re

def save_model(model):
    if (not SAVE_MODEL):
        return
    with open(MODEL_FILE_PATH, 'wb') as file:
        pickle.dump(model, file)

def load_model():
    result = None
    with open(MODEL_FILE_PATH, 'rb') as file:
        result = pickle.load(file)
    printd(f"Loaded model from '{MODEL_FILE_PATH}'.")
    return result

def timings(precision=3):
    start = time.time()
    def end():
        return round((time.time()-start)*1000,precision)
    return end

def printd(*args):
    if DEBUG:
        print(*args)

def read_from_file():
    readingtime = timings()
    with open(STREAM_FILE_PATH, 'r') as file:
        lines = file.readlines()
        if lines:
            result = []
            for line in lines:
                data = json.loads(line)
                result.append(data)
            with open(STREAM_FILE_PATH, 'w') as file:
                file.write('')
            #     pass
            for i in range(len(result)):
                #result[i] = to_vector(result[i][NODE_NAME])
                result[i] = to_vector(result[i])
            printd("Reading data from file took", readingtime(), "ms")
            return result
    printd("Reading data from file took", readingtime(), "ms")
    return []

def to_vector(stats_data):
    result = [stats_data["timestamp"], stats_data["write_load"]]
    order = ["index", "get", "query", "fetch", "scroll", "suggest", "bulk", "flush", "refresh"]
    for o in order:
        total = stats_data["delta_total"][o]
        time = stats_data["delta_time"][o]
        if total > 0:
            val = time/total
        else:
            val = 0
        result.append(val)
    result.append(stats_data["cpu"]["percent"])
    result.append(stats_data["cpu"]["load_avg_1m"])
    result.append(stats_data["cpu"]["load_avg_5m"])
    result.append(stats_data["cpu"]["load_avg_15m"])
    result.append(stats_data["mem"]["used_percent"])
    return np.asarray(result)

def create_dataframe(data):
    df = pd.DataFrame(data, columns=COMPONENTS)
    df['Time'] = pd.to_datetime(df['Time'], unit='ms')
    df['Time'] = df['Time'].dt.round('S')
    df['Time'] = pd.to_datetime(df['Time']).dt.tz_localize('UTC')
    df['Time'] = df['Time'].dt.tz_convert(TIMEZONE)
    df.set_index('Time', inplace=True)
    df.index = pd.DatetimeIndex(df.index).to_period('S')
    df.dropna(inplace=True)
    #print(df.to_string())
    #print(df.columns.tolist())
    return df

def extract_number_from_string(string):
    pattern = r'(\d+)'
    result = re.findall(pattern, string)
    if result:
        return int(result[0])
    else:
        return None