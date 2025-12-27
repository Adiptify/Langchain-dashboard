import pandas as pd
from typing import Dict, Any, List
import json
import sqlite3
import re

from config import METADATA_DB_PATH
from utils import logger

class AgentTools:
    """
    A collection of safe tools (e.g., pandas operations, calculator) that the agent
    can execute to answer queries or retrieve specific data.
    These tools operate on the ingested data and its metadata.
    """
    def execute_pandas_operation(self, operation: str, metric: str, equipment_terms: List[str], 
                                date_range: tuple = None, context_rows: List[Dict] = None) -> Dict[str, Any]:
        """
        Execute specific pandas operations based on SLM-extracted parameters.
        This is the enhanced version that works with SLM router results.
        """
        try:
            if not context_rows:
                return {"error": "No context rows provided", "value": None}
            
            # Extract numeric values from context rows
            numeric_values = []
            column_used = None
            
            for row in context_rows:
                content = row.get('content', '')
                metadata = row.get('metadata', {})
                
                # Look for metric-related columns
                # Map common energy metrics to content patterns
                energy_patterns = ['energy', 'consumption', 'kwh', 'kwh', 'power', 'mwh']
                metric_found = False
                
                if metric:
                    # Check if metric or related terms are in content
                    for pattern in energy_patterns:
                        if pattern in content.lower() or metric.lower() in content.lower():
                            metric_found = True
                            break
                
                if metric_found:
                    # Extract numeric values from content
                    numbers = re.findall(r'(\d+(?:\.\d+)?)', content)
                    for num in numbers:
                        try:
                            val = float(num)
                            # Filter reasonable energy values (10-1000000)
                            if 10 <= val <= 1000000:
                                numeric_values.append(val)
                                if not column_used:
                                    column_used = metric
                        except ValueError:
                            continue
                
                # Also check metadata for numeric fields
                if isinstance(metadata, dict):
                    numeric_fields = metadata.get('numeric_fields', [])
                    for field in numeric_fields:
                        if metric.lower() in field.lower() or 'energy' in field.lower() or 'consumption' in field.lower():
                            # Try to extract value from content
                            pattern = rf"{field}:\s*(\d+(?:\.\d+)?)"
                            match = re.search(pattern, content, re.IGNORECASE)
                            if match:
                                try:
                                    numeric_values.append(float(match.group(1)))
                                    column_used = field
                                except ValueError:
                                    continue
            
            if not numeric_values:
                return {"error": f"No numeric values found for metric '{metric}'", "value": None}
            
            # Perform operation
            if operation.lower() in ['avg', 'average', 'mean']:
                result_value = sum(numeric_values) / len(numeric_values)
            elif operation.lower() in ['sum', 'total']:
                result_value = sum(numeric_values)
            elif operation.lower() == 'max':
                result_value = max(numeric_values)
            elif operation.lower() == 'min':
                result_value = min(numeric_values)
            elif operation.lower() == 'count':
                result_value = len(numeric_values)
            else:
                result_value = sum(numeric_values) / len(numeric_values)  # Default to average
            
            return {
                "value": result_value,
                "operation": operation,
                "metric": metric,
                "column_used": column_used,
                "count": len(numeric_values),
                "equipment_terms": equipment_terms,
                "matched_rows": len(context_rows)
            }
            
        except Exception as e:
            logger.error(f"Pandas operation failed: {e}")
            return {"error": str(e), "value": None}

    def __init__(self):
        logger.info("AgentTools initialized.")

    def _get_dataframe_from_file_id(self, file_id: str) -> pd.DataFrame:
        """
        Retrieves all row-level documents for a given file_id and reconstructs a DataFrame.
        This is a simplified approach; for very large files, a more efficient data loading
        or query mechanism would be needed.
        """
        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT content, metadata FROM documents WHERE file_id = ? AND doc_type = 'row'", (file_id,))
        rows = cursor.fetchall()
        conn.close()

        data = []
        for content_str, metadata_str in rows:
            metadata = json.loads(metadata_str)
            # Assuming the original row data (or a parseable version) is in metadata
            # For now, we'll try to reconstruct from 'content' if it's JSON-like, or a simpler approach
            # A better approach would be to store the original row dict directly in metadata.
            # For demonstration, let's assume metadata["original_row_data"] exists or try parsing content.
            
            # This part needs adjustment based on how original row data is stored.
            # For now, let's assume pandas tools will operate on already retrieved, structured content.
            # This method is more for demonstrating the *intent* to get data for a tool.
        logger.warning(f"_get_dataframe_from_file_id is a placeholder. Actual DataFrame reconstruction for tools needs original row data in metadata.")
        return pd.DataFrame() # Return empty for now, as full reconstruction from SLM summary is not direct

    def execute_pandas_query(self, file_id: str, query_instruction: str) -> Dict[str, Any]:
        """
        Executes a pandas-like query or analysis on data associated with a file_id.
        This function should be carefully designed to be safe (e.g., prevent arbitrary code execution).
        For demonstration, this will be a simulated pandas operation.
        """
        logger.info(f"Executing pandas query for file_id: {file_id} with instruction: {query_instruction}")
        
        # In a real system, this would parse query_instruction into safe pandas operations.
        # For now, let's simulate a simple aggregation based on keywords in query_instruction.

        conn = sqlite3.connect(METADATA_DB_PATH)
        cursor = conn.cursor()
        
        # Retrieve all row documents for the file_id
        cursor.execute("SELECT content, metadata FROM documents WHERE file_id = ? AND doc_type = 'row'", (file_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"result": "No data found for the specified file_id.", "type": "text"}

        # Attempt to extract numeric_fields from metadata for aggregation
        all_numeric_data = []
        for _, metadata_str in rows:
            metadata = json.loads(metadata_str)
            if "numeric_fields" in metadata:
                all_numeric_data.append(metadata["numeric_fields"])

        if not all_numeric_data:
            return {"result": "No numeric data available for calculations in this file.", "type": "text"}

        # Convert to a pandas DataFrame for aggregation
        df = pd.DataFrame(all_numeric_data).fillna(0) # Fill NaN with 0 for aggregation

        # Simple keyword-based aggregation
        result_value = "N/A"
        result_type = "text"

        lower_instruction = query_instruction.lower()

        # Define keywords for energy consumption related columns
        energy_keywords = ["energy", "consumption", "reading", "diffrence", "kwh", "mwh"]

        if "sum" in lower_instruction or "total" in lower_instruction:
            target_col = None
            # Prioritize columns that match specific keywords or are explicitly mentioned
            for col in df.columns:
                if any(keyword in col.lower() for keyword in energy_keywords) and (col.lower() in lower_instruction or "all" in lower_instruction or "total" in lower_instruction):
                    target_col = col
                    break
                elif col.lower() in lower_instruction:
                    target_col = col
                    break
            
            if target_col and target_col in df.columns:
                sum_val = df[target_col].sum()
                result_value = f"The total for {target_col.replace('_', ' ')} is {sum_val:.2f}"
                result_type = "natural_language"
            else: # If no specific column mentioned or matched, sum all relevant numeric columns
                relevant_sums = {}
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in energy_keywords):
                        relevant_sums[col] = df[col].sum()

                if relevant_sums:
                    result_value = f"Total sums for relevant energy consumption columns: {json.dumps(relevant_sums, indent=2)}"
                    result_type = "json"
                else:
                    # Fallback if no specific or relevant columns are found
                    total_sums = {col: df[col].sum() for col in df.columns}
                    result_value = f"Total sums for all numeric columns: {json.dumps(total_sums, indent=2)}"
                    result_type = "json"

        elif "average" in lower_instruction or "mean" in lower_instruction:
            target_col = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in energy_keywords) and (col.lower() in lower_instruction or "all" in lower_instruction or "mean" in lower_instruction):
                    target_col = col
                    break
                elif col.lower() in lower_instruction:
                    target_col = col
                    break

            if target_col and target_col in df.columns:
                mean_val = df[target_col].mean()
                result_value = f"The average for {target_col.replace('_', ' ')} is {mean_val:.2f}"
                result_type = "natural_language"
            else:
                relevant_means = {}
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in energy_keywords):
                        relevant_means[col] = df[col].mean()
                    
                if relevant_means:
                    result_value = f"Average values for relevant energy consumption columns: {json.dumps(relevant_means, indent=2)}"
                    result_type = "json"
                else:
                    avg_means = {col: df[col].mean() for col in df.columns}
                    result_value = f"Average values for all numeric columns: {json.dumps(avg_means, indent=2)}"
                    result_type = "json"

        elif "max" in lower_instruction or "highest" in lower_instruction:
            target_col = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in energy_keywords) and (col.lower() in lower_instruction or "all" in lower_instruction or "max" in lower_instruction):
                    target_col = col
                    break
                elif col.lower() in lower_instruction:
                    target_col = col
                    break

            if target_col and target_col in df.columns:
                max_val = df[target_col].max()
                result_value = f"The maximum for {target_col.replace('_', ' ')} is {max_val:.2f}"
                result_type = "natural_language"
            else:
                relevant_maxes = {}
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in energy_keywords):
                        relevant_maxes[col] = df[col].max()

                if relevant_maxes:
                    result_value = f"Maximum values for relevant energy consumption columns: {json.dumps(relevant_maxes, indent=2)}"
                    result_type = "json"
                else:
                    max_vals = {col: df[col].max() for col in df.columns}
                    result_value = f"Maximum values for all numeric columns: {json.dumps(max_vals, indent=2)}"
                    result_type = "json"

        elif "min" in lower_instruction or "lowest" in lower_instruction:
            target_col = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in energy_keywords) and (col.lower() in lower_instruction or "all" in lower_instruction or "min" in lower_instruction):
                    target_col = col
                    break
                elif col.lower() in lower_instruction:
                    target_col = col
                    break

            if target_col and target_col in df.columns:
                min_val = df[target_col].min()
                result_value = f"The minimum for {target_col.replace('_', ' ')} is {min_val:.2f}"
                result_type = "natural_language"
            else:
                relevant_mins = {}
                for col in df.columns:
                    if any(keyword in col.lower() for keyword in energy_keywords):
                        relevant_mins[col] = df[col].min()

                if relevant_mins:
                    result_value = f"Minimum values for relevant energy consumption columns: {json.dumps(relevant_mins, indent=2)}"
                    result_type = "json"
                else:
                    min_vals = {col: df[col].min() for col in df.columns}
                    result_value = f"Minimum values for all numeric columns: {json.dumps(min_vals, indent=2)}"
                    result_type = "json"
        
        # Add more complex pandas operations here

        return {"result": result_value, "type": result_type, "provenance": f"Aggregated data from file_id: {file_id}"}

# Example Usage (for testing/demonstration)
if __name__ == "__main__":
    # For real testing, you'd need to have data ingested into metadata.db
    # and have a valid file_id.
    # Create a dummy metadata.db and add some data for testing if not present.

    # This part needs to be improved for actual testing without a full ingestion first.
    # For now, assuming a metadata.db exists with some data.
    print("To test AgentTools, please ensure you have run ingestion and have a valid file_id.")
    print("Example: tool_output = agent_tools.execute_pandas_query('your_file_id', 'sum of energy_consumption')")
