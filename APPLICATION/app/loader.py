import os
import pandas as pd
from datetime import datetime
import numpy as np

def load_raw_data(file_path):
    """Enhanced CSV loader with memory optimization for large files"""
    dtype_mapping = {
        'Agent name': 'str',
        'Profile ID': 'str',
        'Call Log ID': 'str',
        'Log Type': 'str',
        'State': 'str',
        'Call type': 'str',
        'Original campaign': 'str',
        'Current campaign': 'str',
        'Ember': 'str'
    }
    try:
        # First check file size to determine optimal loading strategy
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > 50:  # If file is larger than 50MB, use chunking
            chunks = []
            for chunk in pd.read_csv(
                file_path,
                dtype=dtype_mapping,
                parse_dates=['Log Time'],
                on_bad_lines='warn',
                chunksize=10000,
                low_memory=False
            ):
                # Clean string fields in each chunk
                for col in chunk.select_dtypes(include=['object']):
                    chunk[col] = chunk[col].astype(str).str.strip()
                chunks.append(chunk)
            
            df = pd.concat(chunks, ignore_index=True)
            
        else:
            # Load entire file for smaller files
            df = pd.read_csv(
                file_path,
                dtype=dtype_mapping,
                parse_dates=['Log Time'],
                on_bad_lines='warn',
                low_memory=False
            )
            
            # Clean all string fields
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip()
        
        # Validate we have the required columns
        required_columns = [
            'Agent name', 'Profile ID', 'Call Log ID', 'Log Time',
            'Log Type', 'State', 'Call type', 'Original campaign',
            'Current campaign', 'Ember'
        ]
        
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        return df
    
    except Exception as e:
        raise ValueError(f"CSV loading failed: {str(e)}")