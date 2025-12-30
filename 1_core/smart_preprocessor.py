#!/usr/bin/env python3
"""
Optimized Smart Preprocessor for JSW Energy Report
Uses single-pass reading and efficient data extraction.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
import uuid
import sys
import os
import re
from tqdm import tqdm

# Add parent dir to path to find ingestion_pipeline
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
from ingestion_pipeline import Document

class JSWEnergyPreprocessor:
    """High-performance preprocessor for JSW Energy Excel files"""
    
    def __init__(self):
        # Keywords that indicate a sheet contains monthly data
        self.month_keywords = [
            'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
            'JUL', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC'
        ]
        self.skip_sheets = ['Dashboard', 'DATA SHEET', 'Sheet1', 'Environment']
    
    def is_monthly_sheet(self, sheet_name: str) -> bool:
        """Heuristic to detect if a sheet contains monthly data"""
        name_upper = sheet_name.upper()
        if any(keyword in name_upper for keyword in self.month_keywords):
            if not any(skip in name_upper for skip in [s.upper() for s in self.skip_sheets]):
                return True
        return False

    def get_date_aliases(self, date_val: str, is_month: bool = False) -> List[str]:
        """Generate common aliases for a date/month for search robustness"""
        aliases = [date_val]
        try:
            if is_month:
                # Expecting 'JAN', 'FEB', etc. or '%Y-%m'
                # Attempt to parse as month
                month_names = {
                    'JAN': '01', 'JANUARY': '01',
                    'FEB': '02', 'FEBRUARY': '02',
                    'MAR': '03', 'MARCH': '03',
                    'APR': '04', 'APRIL': '04',
                    'MAY': '05',
                    'JUN': '06', 'JUNE': '06',
                    'JUL': '07', 'JULY': '07',
                    'AUG': '08', 'AUGUST': '08',
                    'SEPT': '09', 'SEP': '09', 'SEPTEMBER': '09',
                    'OCT': '10', 'OCTOBER': '10',
                    'NOV': '11', 'NOVEMBER': '11',
                    'DEC': '12', 'DECEMBER': '12'
                }
                
                m_upper = date_val.upper()
                m_num = ""
                if m_upper in month_names:
                    m_num = month_names[m_upper]
                elif '-' in date_val: # e.g. 2024-12
                    m_num = date_val.split('-')[1]
                
                if m_num:
                    # Add numeric variations
                    aliases.extend([m_num, m_num.lstrip('0')])
                    # Add all name variations for this number
                    for name, num in month_names.items():
                        if num == m_num:
                            aliases.append(name)
            else:
                # Expecting 'YYYY-MM-DD'
                dt = datetime.strptime(date_val, '%Y-%m-%d')
                aliases.append(dt.strftime('%d/%m/%y'))
                aliases.append(dt.strftime('%d-%m-%Y'))
                aliases.append(str(dt.month))
                aliases.append(dt.strftime('%b').upper())
                aliases.append(dt.strftime('%B').upper())
        except:
            pass
        return list(set(aliases))

    def _parse_sheet_context(self, sheet_name: str) -> Dict[str, str]:
        """Extract Year and Month from sheet name (e.g., 'JUL-24' -> {month: 07, year: 2024})"""
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
            'JUL': '07', 'AUG': '08', 'SEP': '09', 'SEPT': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        name_upper = sheet_name.upper()
        context = {"month": None, "year": None}
        
        # Try to find month
        for m_name, m_num in month_map.items():
            if m_name in name_upper:
                context["month"] = m_num
                break
        
        # Try to find year (2-digit or 4-digit)
        year_match = re.search(r'\b(20\d{2}|\d{2})\b', name_upper)
        if year_match:
            year = year_match.group(1)
            context["year"] = f"20{year}" if len(year) == 2 else year
            
        return context

    def attempt_date_parse(self, d, sheet_context=None) -> str:
        """Strictly parse date strings, Excel serials, and numeric days."""
        if isinstance(d, (pd.Timestamp, datetime)):
            return d.strftime('%Y-%m-%d')
            
        s = str(d).strip().replace(' 00:00:00', '')
        if not s or s.lower() == 'nan':
            return None

        # 1. Handle Excel Serial Dates (e.g., 45000+)
        if s.isdigit() and len(s) >= 5:
            try:
                val = int(s)
                if 40000 < val < 60000: # Valid range for roughly 2010s-2060s
                    dt = datetime(1899, 12, 30) + pd.Timedelta(days=val)
                    return dt.strftime('%Y-%m-%d')
            except: pass

        # 2. Handle Numeric Days (1-31) with Sheet Context
        if s.isdigit() and 1 <= int(s) <= 31:
            if sheet_context and sheet_context.get("month") and sheet_context.get("year"):
                try:
                    day = s.zfill(2)
                    return f"{sheet_context['year']}-{sheet_context['month']}-{day}"
                except: pass
            return s # Return as is if no context, but likely a day number

        # 3. Try common patterns
        try:
            for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%b-%y', '%B-%y', '%d-%b-%y']:
                try:
                    return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
                except: continue
        except: pass
        
        # 4. Final strict numeric check: 
        # If it's a number (int or float), it MUST be between 1 and 31 (inclusive)
        # to be considered a "Day" header. Otherwise, REJECT.
        try:
            num_val = float(s)
            if 1 <= num_val <= 31:
                return str(int(num_val)) # Return as cleaned day number
            return None # Reject other numbers (103, 246885, etc.)
        except ValueError:
            # Not a number (e.g., "SL NO"), REJECT as date
            # We used to return the string as is, but that caused issues like "Difference.14" 
            # being treated as a date. 
            return None

    def process_file(self, file_path_or_obj) -> List[Document]:
        """Process JSW Energy Excel with optimized single-pass reading"""
        
        print("\n" + "="*60)
        print("OPTIMIZED JSW ENERGY PREPROCESSOR")
        print("="*60)
        
        is_file_obj = not isinstance(file_path_or_obj, str)
        if not is_file_obj and not os.path.exists(file_path_or_obj):
            print(f"Error: File not found: {file_path_or_obj}")
            return []

        documents = []
        file_id = str(uuid.uuid4())
        file_name = getattr(file_path_or_obj, 'name', 'Uploaded_File') if is_file_obj else os.path.basename(file_path_or_obj)
        
        all_feeders = {}  # feeder_key -> {name, swb, readings, last_diff}
        daily_totals = {}  # date -> total_consumption
        monthly_totals = {}  # month -> total_consumption
        
        try:
            print(f"Loading Excel: {file_name}...")
            # Use pd.ExcelFile for single-pass zip extraction
            xl = pd.ExcelFile(file_path_or_obj)
            print(f"📄 All sheets in file: {xl.sheet_names}")
            
            # Improved sheet detection
            sheets_to_process = []
            for s in xl.sheet_names:
                if self.is_monthly_sheet(s):
                    sheets_to_process.append(s)
            
            if not sheets_to_process:
                print(f"Warning: No monthly sheets found matching keywords: {self.month_keywords}")
                # Try a broader search: any sheet that isn't in skip_sheets and has some keywords or just isn't empty
                for s in xl.sheet_names:
                    s_upper = s.upper()
                    if not any(skip.upper() in s_upper for skip in self.skip_sheets):
                        sheets_to_process.append(s)
                
                if sheets_to_process:
                    print(f"Fallback: Processing non-skipped sheets: {sheets_to_process}")
                else:
                    # Last resort: process everything except explicit skip_sheets
                    sheets_to_process = [s for s in xl.sheet_names if s not in self.skip_sheets]
                    print(f"Emergency Fallback: Processing all available sheets: {sheets_to_process}")

            if not sheets_to_process:
                print("Error: No sheets available for processing after all filters.")
                return []

            print(f"🔍 Found {len(sheets_to_process)} sheets to process: {sheets_to_process}")
            
            for sheet_name in tqdm(sheets_to_process, desc="Processing sheets"):
                try:
                    # Read the sheet, try to find the real header
                    df_full = xl.parse(sheet_name, header=None)
                    if df_full.empty:
                        continue
                    
                    # Find header row by looking for 'Feeder', 'Panel', 'Description' or 'Tag'
                    header_row_idx = 0
                    for row_idx, row in df_full.head(30).iterrows(): # Scan deeper
                        row_str = " ".join(str(val).upper() for val in row if pd.notna(val))
                        if any(k in row_str for k in ['FEEDER', 'PANEL', 'DESCRIPTION', 'TAG', 'PARTICULAR']):
                            header_row_idx = row_idx
                            break
                    
                    df = xl.parse(sheet_name, header=header_row_idx)
                    
                    if df.empty or len(df.columns) < 2:
                        continue
                    
                    sheet_context = self._parse_sheet_context(sheet_name)
                    print(f"  📄 Context for '{sheet_name}': {sheet_context}")

                    # Identify columns
                    feeder_col = None
                    swb_col = None
                    
                    for col in df.columns:
                        col_str = str(col).upper()
                        if any(k in col_str for k in ['FEEDER', 'PANEL', 'DESCRIPTION', 'TAG', 'PARTICULAR']):
                            feeder_col = col
                        elif any(k in col_str for k in ['SWB', 'SWITCH', 'LOCATION', 'AREA', 'SOURCE']):
                            swb_col = col
                            
                    if feeder_col is None:
                        # Only take first col if it's not a date
                        first_col = df.columns[0]
                        if not self.attempt_date_parse(first_col, sheet_context):
                            feeder_col = first_col
                            
                    if swb_col is None and len(df.columns) > 1:
                        # Only take second col if it's not a date
                        second_col = df.columns[1]
                        if not self.attempt_date_parse(second_col, sheet_context):
                            swb_col = second_col
                    
                    # Efficiently find date columns and differentiate between Reading and Consumption
                    reading_cols = []
                    consumption_cols = []
                    
                    for i, col in enumerate(df.columns):
                        col_str = str(col).lower()
                        # Skip if it's the feeder or swb column
                        if col == feeder_col or col == swb_col:
                            continue
                        
                        # Check if column name itself is a date or "Consumption" keyword
                        is_consumption = any(k in col_str for k in ['diff', 'cons', 'unit', 'kwh', 'energy', 'net'])
                        
                        # Validate Date Header strictly
                        parsed_date = self.attempt_date_parse(col, sheet_context)
                        
                        if is_consumption:
                            consumption_cols.append((i, col))
                        elif parsed_date:
                            reading_cols.append((i, col, parsed_date))
                        # else:
                        #    print(f"      DEBUG: Column '{col}' NOT a date (parsed={parsed_date})")
                    
                    if not consumption_cols and not reading_cols:
                        print(f"Warning: No data columns found in sheet {sheet_name}. Columns: {list(df.columns)}")
                        continue

                    print(f"  🔍 Sheet '{sheet_name}': Identified {len(reading_cols)} Readings and {len(consumption_cols)} Consumption (Diff) columns.")

                    # --- ROW CLASSIFICATION LOGIC ---
                    sheet_daily_feeder_sums = {} # date -> sum
                    sheet_daily_incomer_sums = {} # date -> sum
                    sheet_daily_total_rows = {} # date -> val
                    
                    for idx, row in df.iterrows():
                        feeder_raw = str(row[feeder_col]).strip() if pd.notna(row[feeder_col]) else ""
                        swb = str(row[swb_col]).strip() if swb_col and pd.notna(row[swb_col]) else sheet_name
                        
                        if not feeder_raw or any(x in feeder_raw.upper() for x in ['SL NO', 'REMARK']):
                            continue
                        
                        feeder_upper = feeder_raw.upper()
                        # KEYWORD SCAN: Identify if this row is a summary or main source
                        row_type = 'feeder' # Default
                        
                        # Broaden keywords for generic industrial use
                        total_keywords = ['TOTAL', 'GRAND TOTAL', 'NET CONSUMPTION', 'PLANT TOTAL', 'TOTAL PLANT']
                        source_keywords = ['I/C', 'INCOMER', 'MAIN', 'BUS COUPLER', 'SOURCE', 'FEED', 'INPUT']
                        
                        if any(x in feeder_upper for x in total_keywords):
                            row_type = 'total'
                        elif any(x in feeder_upper for x in source_keywords):
                            # Only categorize as incomer/source if it doesn't also look like a total
                            row_type = 'incomer'
                        # Decide whether to skip the row
                        # Generally skip technical/summary rows, BUT allow 'total' and 'incomer' rows
                        should_process = True
                        if any(x in feeder_upper for x in ['SWITCH BOARD', 'TOTAL']):
                            if row_type == 'feeder': # It's just a random "Total" row we don't recognize
                                should_process = False
                        
                        # Allow "FEEDER 1", "FEEDER 2" etc, but skip if it's JUST the word "FEEDER" or "FEEDERS"
                        if feeder_upper in ['FEEDER', 'FEEDERS', 'SL NO', 'REMARK']:
                            should_process = False

                        if not should_process:
                             continue
                        
                        # Avoid 'Unknown' if possible
                        if swb.upper() == 'UNKNOWN' or not swb:
                            swb = sheet_name
                        
                        feeder_key = f"{feeder_raw} ({swb})"
                        if feeder_key not in all_feeders:
                            all_feeders[feeder_key] = {
                                'name': feeder_raw, 
                                'swb': swb, 
                                'readings': {}, 
                                'last_diff': 0,
                                "is_main_source": row_type == 'incomer', # Generic hierarchy flag
                                "is_total_row": row_type == 'total',
                                "row_type": row_type,
                                "context_tags": [feeder_raw] + ([swb] if swb else []), # Basic tags for CSV/Excel
                                "created_at": datetime.now().strftime("%Y-%m-%d"), # Fallback to today but format correctly
                                "trusted": True,
                                "doc_type": "industrial_data",
                            }
                        
                        # Combine consumption_cols into items if processing as consumption
                        if consumption_cols:
                            items_to_process = []
                            # Logic: If consumption_cols matches reading_cols count, map them 1-to-1
                            if len(consumption_cols) == len(reading_cols):
                                for i in range(len(consumption_cols)):
                                    c_idx, col_name = consumption_cols[i]
                                    r_idx, r_name, r_date = reading_cols[i]
                                    items_to_process.append((c_idx, col_name, r_date))
                            else:
                                # Fallback to spatial proximity
                                for c_idx, col_name in consumption_cols:
                                    # Try parsing the header itself first (e.g., "01-07-2024 Diff")
                                    d_str = self.attempt_date_parse(col_name, sheet_context)
                                    
                                    # If not found, look for the nearest previous reading date (Standard JSW interleaved format)
                                    if not d_str:
                                        for r_idx, r_name, r_date in reversed(reading_cols):
                                            if r_idx < c_idx:
                                                d_str = r_date
                                                break
                                                
                                    # Fallback: nearest subsequent (rare)
                                    if not d_str:
                                        for r_idx, r_name, r_date in reading_cols:
                                            if r_idx > c_idx:
                                                d_str = r_date
                                                break
                                    
                                    if d_str:
                                        items_to_process.append((c_idx, col_name, d_str))
                        else:
                            items_to_process = reading_cols

                        # Process identified data columns
                        last_reading_val = None
                        feeder_readings = {}

                        for item in items_to_process:
                            col_idx, raw_date_header, date_str = item
                            
                            # If date_str is not a valid date or numeric day, try to find the nearest previous reading date
                            if not date_str or (not re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)) and not (str(date_str).isdigit() and 1 <= int(date_str) <= 31)):
                                # This handles "Difference.14" etc. 
                                # We look for the date in reading_cols that matches the index pattern if possible,
                                # but for now, we simply skip columns that aren't clearly dates to avoid bad data.
                                continue

                            raw_val = row.iloc[col_idx]
                            
                            # Update last_reading_val even if raw_val is NaN to maintain delta chain
                            current_val = None
                            try:
                                if pd.notna(raw_val):
                                    current_val = float(raw_val)
                                    if current_val < 0 or current_val > 100000000:
                                        current_val = None
                            except: pass
                            
                            consumption_val = 0
                            if consumption_cols:
                                if current_val is not None:
                                    consumption_val = current_val
                            else:
                                if current_val is not None and last_reading_val is not None:
                                    delta = current_val - last_reading_val
                                    if 0 <= delta < 1000000:
                                        consumption_val = delta
                                # Always update last_reading_val if we have a current_val
                                if current_val is not None:
                                    last_reading_val = current_val
                            
                            if consumption_val > 0:
                                feeder_readings[date_str] = consumption_val
                                
                                # Accurate Aggregation logic (Once per reading!):
                                if row_type == 'total':
                                    sheet_daily_total_rows[date_str] = max(sheet_daily_total_rows.get(date_str, 0), consumption_val)
                                elif row_type == 'incomer':
                                    sheet_daily_incomer_sums[date_str] = sheet_daily_incomer_sums.get(date_str, 0) + consumption_val
                                else:
                                    sheet_daily_feeder_sums[date_str] = sheet_daily_feeder_sums.get(date_str, 0) + consumption_val

                        # Accumulate readings for the feeder document
                        if row_type != 'total': # Don't create feeder docs for "Total" rows
                            all_feeders[feeder_key]['readings'].update(feeder_readings)
                
                    # --- HIERARCHICAL PLANT TOTAL AGGREGATION ---
                    # For this sheet, we now decide what the real "Daily Total" is
                    all_dates = set(list(sheet_daily_total_rows.keys()) + list(sheet_daily_incomer_sums.keys()) + list(sheet_daily_feeder_sums.keys()))
                    
                    sheet_total_cons = 0
                    if not all_dates:
                        print(f"    ⚠️ No data extracted from sheet {sheet_name}")
                    
                    for d_str in sorted(all_dates):
                        # Priority: 1. Total Row, 2. Incomer Sum, 3. Feeder Sum
                        final_daily_val = 0
                        method = ""
                        
                        # ONLY use total_row if it actually HAS a value for this date
                        if d_str in sheet_daily_total_rows and sheet_daily_total_rows[d_str] > 0:
                            final_daily_val = sheet_daily_total_rows[d_str]
                            method = "total_row"
                        elif d_str in sheet_daily_incomer_sums and sheet_daily_incomer_sums[d_str] > 0:
                            final_daily_val = sheet_daily_incomer_sums[d_str]
                            method = "incomer_sum"
                        else:
                            final_daily_val = sheet_daily_feeder_sums.get(d_str, 0)
                            method = "feeder_sum"
                        
                        if final_daily_val > 0:
                            daily_totals[d_str] = daily_totals.get(d_str, 0) + final_daily_val
                            sheet_total_cons += final_daily_val
                        
                    monthly_totals[sheet_name] = sheet_total_cons

                except Exception as e:
                    import traceback
                    print(f"\nWarning: Error in sheet {sheet_name}: {e}")
                    # traceback.print_exc()
            
        except Exception as e:
            import traceback
            print(f"\nError: Global processing error: {e}")
            traceback.print_exc()
            return []

        # Create structured documents efficiently
        feeder_docs_count = 0
        for feeder_key, data in all_feeders.items():
            if not data['readings']: continue
            if data.get('is_total_row'): continue # Skip total rows in individual feeder docs
            
            readings = list(data['readings'].values())
            avg = np.mean(readings)
            total = np.sum(readings)
            
            # IMPORTANT: For industrial_data rows, we should tag them with the specific date of the reading
            # to enable temporal filtering in RAG.
            first_date = min(data['readings'].keys()) if data['readings'] else datetime.now().strftime("%Y-%m-%d")
            last_date = max(data['readings'].keys()) if data['readings'] else datetime.now().strftime("%Y-%m-%d")
            
            # Update created_at to the most representative date (e.g., start of the month/period)
            data_metadata = data.copy()
            data_metadata['created_at'] = first_date 
            data_metadata['data_date_start'] = first_date
            data_metadata['data_date_end'] = last_date
            
            prefix = "[INCOMER] " if data.get('is_incomer') else ""
            content = (
                f"{prefix}Feeder: {feeder_key} | Location: {data['swb']} | "
                f"Avg daily: {avg:.1f} KWH | Total: {total:.1f} KWH | "
                f"Period: {first_date} to {last_date}"
            )
            
            documents.append(Document(
                doc_id=f"row_{uuid.uuid4().hex[:8]}",
                file_id=file_id,
                file_name=file_name,
                doc_type="industrial_data",
                content=content,
                metadata=data_metadata
            ))
            
            documents.append(Document(
                doc_id=str(uuid.uuid4()), file_id=file_id, file_name=file_name,
                doc_type="feeder_data", content=content,
                metadata={
                    "feeder": data['name'], 
                    "location": data['swb'], 
                    "total": float(total),
                    "is_incomer": data.get('is_incomer', False)
                }
            ))
            feeder_docs_count += 1
        
        print(f"📝 Created {feeder_docs_count} actual feeder summaries.")
        
        print(f"📅 Creating {len(daily_totals)} daily summaries...")
        for date, total in sorted(daily_totals.items()):
            documents.append(Document(
                doc_id=str(uuid.uuid4()), file_id=file_id, file_name=file_name,
                doc_type="daily_total", content=f"Date: {date} | Total Plant Cons: {total:,.1f} KWH",
                metadata={"date": date, "total": float(total), "aliases": self.get_date_aliases(date)}
            ))
            
        print(f"🗓️ Creating {len(monthly_totals)} monthly summaries...")
        for month, total in monthly_totals.items():
            documents.append(Document(
                doc_id=str(uuid.uuid4()), file_id=file_id, file_name=file_name,
                doc_type="monthly_total", content=f"Month: {month} | Total Plant Cons: {total:,.1f} KWH",
                metadata={"month": month, "total": float(total), "aliases": self.get_date_aliases(month, is_month=True)}
            ))
            
        # Global Summary
        total_all_time = sum(monthly_totals.values())
        if total_all_time > 0:
            # Calculate Peaks
            peak_day = max(daily_totals.items(), key=lambda x: x[1]) if daily_totals else ("N/A", 0)
            peak_month = max(monthly_totals.items(), key=lambda x: x[1]) if monthly_totals else ("N/A", 0)
            
            monthly_breakdown = "\n".join([f"- {m}: {t:,.1f} KWH" for m, t in monthly_totals.items()])
            
            summary_content = (
                f"TOTAL ALL-TIME PLANT CONSUMPTION: {total_all_time:,.1f} KWH\n"
                f"Period Coverage: {len(monthly_totals)} months\n"
                f"Monthly Breakdown:\n{monthly_breakdown}\n\n"
                f"PEAK STATISTICS:\n"
                f"- Highest Cons. Day: {peak_day[0]} with {peak_day[1]:,.1f} KWH\n"
                f"- Highest Cons. Month: {peak_month[0]} with {peak_month[1]:,.1f} KWH"
            )
            
            documents.append(Document(
                doc_id=str(uuid.uuid4()), file_id=file_id, file_name=file_name,
                doc_type="plant_summary",
                content=summary_content,
                metadata={
                    "total": float(total_all_time), 
                    "months": list(monthly_totals.keys()),
                    "peak_day": peak_day[0],
                    "peak_day_val": float(peak_day[1]),
                    "peak_month": peak_month[0]
                }
            ))
        else:
            print("Warning: Total all-time consumption is zero. Skipping plant_summary document.")
        
        print(f"\nSUCCESS: Created {len(documents)} structured documents.")
        return documents

if __name__ == "__main__":
    p = JSWEnergyPreprocessor()
    # Test path from original script
    test_file = "../4_data/Energy Consumption Daily Report MHS Ele - Copy.xlsx"
    if os.path.exists(test_file):
        docs = p.process_file(test_file)
        print(f"Ingested {len(docs)} documents.")
