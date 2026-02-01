# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Sheets service for spreadsheet operations.

Provides high-level operations for creating, reading, writing,
and managing Google Sheets spreadsheets.
"""

from typing import Any
from dataclasses import dataclass

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

from app.integrations.google.client import get_sheets_service, get_drive_service


@dataclass
class SpreadsheetInfo:
    """Information about a Google Sheets spreadsheet."""
    id: str
    name: str
    url: str
    sheets: list[str]


@dataclass
class SheetData:
    """Data from a spreadsheet range."""
    range: str
    values: list[list[Any]]
    row_count: int
    column_count: int


class GoogleSheetsService:
    """Service for Google Sheets operations.
    
    Provides methods for:
    - Listing user's spreadsheets
    - Creating new spreadsheets
    - Reading data ranges
    - Writing data to cells
    - Managing sheet structure
    """
    
    def __init__(self, credentials: Credentials):
        """Initialize with Google OAuth credentials.
        
        Args:
            credentials: Google OAuth credentials from Supabase session.
        """
        self.credentials = credentials
        self._sheets_service: Resource | None = None
        self._drive_service: Resource | None = None
    
    @property
    def sheets(self) -> Resource:
        """Lazy-load Sheets API service."""
        if self._sheets_service is None:
            self._sheets_service = get_sheets_service(self.credentials)
        return self._sheets_service
    
    @property
    def drive(self) -> Resource:
        """Lazy-load Drive API service."""
        if self._drive_service is None:
            self._drive_service = get_drive_service(self.credentials)
        return self._drive_service
    
    def list_spreadsheets(self, max_results: int = 50) -> list[SpreadsheetInfo]:
        """List user's Google Sheets spreadsheets.
        
        Args:
            max_results: Maximum number of spreadsheets to return.
            
        Returns:
            List of SpreadsheetInfo objects.
        """
        results = self.drive.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=max_results,
            fields="files(id, name, webViewLink)",
        ).execute()
        
        spreadsheets = []
        for file in results.get("files", []):
            # Get sheet names for each spreadsheet
            try:
                sheet_metadata = self.sheets.spreadsheets().get(
                    spreadsheetId=file["id"],
                    fields="sheets.properties.title"
                ).execute()
                sheet_names = [
                    s["properties"]["title"] 
                    for s in sheet_metadata.get("sheets", [])
                ]
            except Exception:
                sheet_names = []
            
            spreadsheets.append(SpreadsheetInfo(
                id=file["id"],
                name=file["name"],
                url=file.get("webViewLink", ""),
                sheets=sheet_names,
            ))
        
        return spreadsheets
    
    def get_spreadsheet(self, spreadsheet_id: str) -> SpreadsheetInfo:
        """Get information about a specific spreadsheet.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            
        Returns:
            SpreadsheetInfo object.
        """
        metadata = self.sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="spreadsheetId,properties.title,spreadsheetUrl,sheets.properties.title"
        ).execute()
        
        return SpreadsheetInfo(
            id=metadata["spreadsheetId"],
            name=metadata["properties"]["title"],
            url=metadata.get("spreadsheetUrl", ""),
            sheets=[s["properties"]["title"] for s in metadata.get("sheets", [])],
        )
    
    def read_range(
        self, 
        spreadsheet_id: str, 
        range_notation: str,
    ) -> SheetData:
        """Read data from a spreadsheet range.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            range_notation: A1 notation (e.g., "Sheet1!A1:D10").
            
        Returns:
            SheetData with values and metadata.
        """
        result = self.sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
        ).execute()
        
        values = result.get("values", [])
        row_count = len(values)
        column_count = max(len(row) for row in values) if values else 0
        
        return SheetData(
            range=result.get("range", range_notation),
            values=values,
            row_count=row_count,
            column_count=column_count,
        )
    
    def write_range(
        self,
        spreadsheet_id: str,
        range_notation: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Write data to a spreadsheet range.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            range_notation: A1 notation (e.g., "Sheet1!A1").
            values: 2D list of values to write.
            value_input_option: How to interpret input ("RAW" or "USER_ENTERED").
            
        Returns:
            API response with update details.
        """
        body = {"values": values}
        
        result = self.sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption=value_input_option,
            body=body,
        ).execute()
        
        return result
    
    def append_rows(
        self,
        spreadsheet_id: str,
        range_notation: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Append rows to the end of a spreadsheet range.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            range_notation: A1 notation for the table range.
            values: 2D list of rows to append.
            value_input_option: How to interpret input.
            
        Returns:
            API response with append details.
        """
        body = {"values": values}
        
        result = self.sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption=value_input_option,
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        
        return result
    
    def create_spreadsheet(
        self,
        title: str,
        sheets: list[dict[str, Any]] | None = None,
    ) -> SpreadsheetInfo:
        """Create a new spreadsheet.
        
        Args:
            title: Title for the new spreadsheet.
            sheets: Optional list of sheet configurations. Each dict can have:
                - title: Sheet name
                - headers: List of column headers
                - data: Initial data rows
                
        Returns:
            SpreadsheetInfo for the created spreadsheet.
        """
        # Build spreadsheet request
        spreadsheet_body: dict[str, Any] = {
            "properties": {"title": title},
        }
        
        if sheets:
            spreadsheet_body["sheets"] = [
                {"properties": {"title": sheet.get("title", f"Sheet{i+1}")}}
                for i, sheet in enumerate(sheets)
            ]
        
        # Create the spreadsheet
        result = self.sheets.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = result["spreadsheetId"]
        
        # Add headers and initial data to each sheet
        if sheets:
            for i, sheet in enumerate(sheets):
                sheet_title = sheet.get("title", f"Sheet{i+1}")
                
                # Write headers
                if "headers" in sheet:
                    self.write_range(
                        spreadsheet_id,
                        f"{sheet_title}!A1",
                        [sheet["headers"]],
                    )
                
                # Write initial data
                if "data" in sheet and sheet["data"]:
                    start_row = 2 if "headers" in sheet else 1
                    self.write_range(
                        spreadsheet_id,
                        f"{sheet_title}!A{start_row}",
                        sheet["data"],
                    )
        
        return self.get_spreadsheet(spreadsheet_id)
    
    def add_sheet(
        self,
        spreadsheet_id: str,
        title: str,
        headers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new sheet tab to an existing spreadsheet.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            title: Name for the new sheet.
            headers: Optional column headers.
            
        Returns:
            API response with new sheet details.
        """
        requests = [{
            "addSheet": {
                "properties": {"title": title}
            }
        }]
        
        result = self.sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()
        
        # Add headers if provided
        if headers:
            self.write_range(spreadsheet_id, f"{title}!A1", [headers])
        
        return result
