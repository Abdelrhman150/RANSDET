# RanDetect
## Machine Learning-Based Early Ransomware Detection and File Recovery System

RanDetect is an intelligent cybersecurity system designed to detect ransomware attacks at an early stage by analyzing suspicious file and process behaviors.

Instead of relying on known ransomware signatures, RanDetect focuses on identifying ransomware-like encryption behavior such as mass file modification, abnormal write activity, entropy increase, and large-scale content changes.

The system combines behavioral monitoring, machine learning classification, and protected file versioning to reduce data loss and enable automatic recovery of affected files.

---

## Project Overview

Ransomware attacks usually follow a common pattern:

1. Accessing a large number of files
2. Encrypting or modifying their contents
3. Replacing the original files
4. Preventing users from accessing their data

RanDetect aims to interrupt this process by detecting abnormal encryption behavior before the attack spreads.

The main workflow:

```
File & Process Monitoring
          |
          v
Feature Extraction
          |
          v
Machine Learning Detection
          |
          v
Risk Evaluation
          |
          v
Alert + File Recovery
```

---

# Key Features

## Real-Time Behavior Monitoring

RanDetect analyzes system activity and collects information about:

- File read/write operations
- File modification frequency
- File rename activity
- Directory access patterns
- Process behavior

---

## Ransomware Behavior Analysis

The system extracts multiple indicators associated with ransomware activity:

- Number of files modified
- Files modified per second
- Content change ratio
- Entropy variation before and after modification
- Randomness increase in file content
- File access distribution
- Extension changes

These features help distinguish malicious encryption from normal bulk operations.

---

## Machine Learning Detection

RanDetect uses machine learning models to classify system behavior.

Current models:

- Random Forest
- XGBoost

The model learns patterns of:

- Normal user activity
- Benign bulk operations
- Suspicious encryption behavior

The goal is to detect ransomware behavior rather than identify a specific ransomware family.

---

## File Recovery System

To minimize damage, RanDetect maintains protected file versions.

When suspicious activity is detected:

```
Detection
    |
    v
Identify affected files
    |
    v
Stop malicious activity
    |
    v
Restore last safe versions
```

The recovery system helps restore files without depending on decrypting the ransomware encryption.

---

# Feature Engineering

RanDetect uses behavioral and file-based features.

Examples:

| Feature | Description |
|---|---|
| files_read | Number of accessed files |
| files_written | Number of modified files |
| modification_rate | Files changed per second |
| entropy_before | File randomness before modification |
| entropy_after | File randomness after modification |
| entropy_difference | Change in randomness |
| content_change_ratio | Percentage of changed data |
| rename_count | Number of renamed files |
| directory_count | Number of affected directories |
| compression_ratio | File compressibility change |

---

# Dataset Generation

The project uses both public datasets and custom-generated data.

The custom dataset includes:

### Normal Activity

Examples:

- File editing
- Copying files
- Compression
- Backup operations
- Batch processing

### Encryption Simulation

Controlled encryption scenarios using different:

- Algorithms
- File types
- File sizes
- Encryption speeds
- Number of affected files

This helps the model learn general encryption behavior instead of memorizing a specific ransomware pattern.

---

# Project Architecture

```
                 Windows System

                       |
                       v

             Monitoring Agent

                       |
                       v

             Feature Extraction

                       |
                       v

             ML Detection Model

                       |
          -------------------------
          |                       |
          v                       v

       Normal              Suspicious

                              |
                              v

                    Alert & Recovery
```

---

# Technologies Used

## Machine Learning

- Python
- Pandas
- NumPy
- Scikit-learn
- XGBoost
- SHAP

## Backend

- FastAPI
- SQLite

## System Monitoring

- Windows APIs
- ETW (Event Tracing for Windows)

## Storage

- Protected Version Storage
- File Metadata Database

---

# Evaluation Metrics

The system is evaluated using:

- Precision
- Recall
- F1-score
- False Positive Rate
- Detection Time
- Recovery Rate

Important measurements:

## Time To Detect (TTD)

The time required to identify ransomware behavior after the attack starts.

## Files Lost Before Detection

The number of files affected before the system responds.

## Recovery Rate

The percentage of successfully restored files.

---

# Future Improvements

Future versions may include:

- Windows File System Minifilter integration
- Advanced copy-on-write protection
- Real ransomware family testing
- Deep learning sequence models
- Multi-device monitoring dashboard
- Cloud-based threat intelligence integration

---

# Research Question

Can machine learning detect ransomware-like mass encryption behavior early enough to reduce data loss and automatically recover affected files?

---

# Disclaimer

RanDetect is developed for cybersecurity research and educational purposes in controlled environments.
