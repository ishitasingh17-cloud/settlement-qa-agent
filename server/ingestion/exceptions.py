"""
server/ingestion/exceptions.py

Structured exceptions for the data ingestion and normalization pipeline.
Follows docs/rules.md: no bare exceptions, explicit actionable error messages.
"""

from typing import List


class IngestionError(Exception):
    """Base exception for data ingestion and normalization failures."""
    pass


class DatasetNotFoundError(IngestionError):
    """Raised when a required source dataset file does not exist on disk."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"Source dataset not found: {filepath}")


class EmptyDatasetError(IngestionError):
    """Raised when a required dataset file exists but contains zero rows."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"Source dataset is empty: {filepath}")


class SchemaValidationError(IngestionError):
    """Raised when CSV header fails to include all required columns."""
    def __init__(self, filename: str, missing_columns: List[str], found_columns: List[str]):
        self.filename = filename
        self.missing_columns = missing_columns
        self.found_columns = found_columns
        super().__init__(
            f"Schema validation failed for '{filename}'. Missing required columns: {missing_columns}. Found: {found_columns}"
        )


class RowValidationError(IngestionError):
    """Raised when a specific CSV row fails type conversion or validation rules."""
    def __init__(self, filename: str, row_index: int, field_name: str, raw_value: str, reason: str):
        self.filename = filename
        self.row_index = row_index
        self.field_name = field_name
        self.raw_value = raw_value
        self.reason = reason
        super().__init__(
            f"Row validation failed in '{filename}' at line {row_index} on column '{field_name}'='{raw_value}': {reason}"
        )
