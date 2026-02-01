# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Sheets tools for agent use.

These tools enable agents to connect, read, write, and create
Google Sheets spreadsheets based on user requirements.
"""

from typing import Any

# Tool context type - uses Any since ToolContext is internal to ADK
ToolContextType = Any


def _get_sheets_service(tool_context: ToolContextType):
    """Get GoogleSheetsService from tool context.
    
    The service should be initialized with credentials from the user's
    Supabase session and stored in the tool context or session state.
    """
    # Lazy import to avoid circular dependencies
    from app.integrations.google.sheets import GoogleSheetsService
    from app.integrations.google.client import get_google_credentials
    
    # Get provider_token from session state (set during auth)
    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")
    
    if not provider_token:
        raise ValueError(
            "Google authentication required. Please connect your Google account "
            "to access spreadsheet features."
        )
    
    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleSheetsService(credentials)


def list_connected_spreadsheets(
    tool_context: ToolContextType,
    max_results: int = 20,
) -> dict[str, Any]:
    """List the user's Google Sheets spreadsheets.
    
    Use this to show the user what spreadsheets they can connect to.
    
    Args:
        tool_context: Agent tool context with credentials.
        max_results: Maximum number of spreadsheets to return.
        
    Returns:
        Dict containing list of spreadsheets with id, name, url, and sheet tabs.
    """
    try:
        service = _get_sheets_service(tool_context)
        spreadsheets = service.list_spreadsheets(max_results)
        
        return {
            "status": "success",
            "count": len(spreadsheets),
            "spreadsheets": [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "sheets": s.sheets,
                }
                for s in spreadsheets
            ],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to list spreadsheets: {e}"}


def connect_spreadsheet(
    tool_context: ToolContextType,
    spreadsheet_id: str,
) -> dict[str, Any]:
    """Connect to an existing Google Sheets spreadsheet.
    
    Use this after listing spreadsheets to select one for data operations.
    Stores the connection in session state for subsequent operations.
    
    Args:
        tool_context: Agent tool context.
        spreadsheet_id: The ID of the spreadsheet to connect.
        
    Returns:
        Dict with spreadsheet details and confirmation.
    """
    try:
        service = _get_sheets_service(tool_context)
        info = service.get_spreadsheet(spreadsheet_id)
        
        # Store connection in session state
        tool_context.state["connected_spreadsheet_id"] = info.id
        tool_context.state["connected_spreadsheet_name"] = info.name
        
        return {
            "status": "success",
            "message": f"Connected to '{info.name}'",
            "spreadsheet": {
                "id": info.id,
                "name": info.name,
                "url": info.url,
                "sheets": info.sheets,
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to connect: {e}"}


def read_sheet_data(
    tool_context: ToolContextType,
    range_notation: str,
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """Read data from a Google Sheets range.
    
    Args:
        tool_context: Agent tool context.
        range_notation: A1 notation (e.g., "Sheet1!A1:D10" or "A1:D10").
        spreadsheet_id: Optional spreadsheet ID. Uses connected spreadsheet if not provided.
        
    Returns:
        Dict with data values, headers, and row count.
    """
    try:
        service = _get_sheets_service(tool_context)
        
        # Use connected spreadsheet if not specified
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")
        
        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected. Use connect_spreadsheet first.",
            }
        
        data = service.read_range(spreadsheet_id, range_notation)
        
        # Parse headers and data rows
        headers = data.values[0] if data.values else []
        rows = data.values[1:] if len(data.values) > 1 else []
        
        return {
            "status": "success",
            "range": data.range,
            "headers": headers,
            "rows": rows,
            "row_count": data.row_count,
            "column_count": data.column_count,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to read data: {e}"}


def write_sheet_data(
    tool_context: ToolContextType,
    range_notation: str,
    values: list[list[Any]],
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """Write data to a Google Sheets range.
    
    Args:
        tool_context: Agent tool context.
        range_notation: A1 notation for where to write (e.g., "Sheet1!A1").
        values: 2D list of values to write.
        spreadsheet_id: Optional spreadsheet ID. Uses connected spreadsheet if not provided.
        
    Returns:
        Dict with update confirmation.
    """
    try:
        service = _get_sheets_service(tool_context)
        
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")
        
        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected. Use connect_spreadsheet first.",
            }
        
        result = service.write_range(spreadsheet_id, range_notation, values)
        
        return {
            "status": "success",
            "message": f"Updated {result.get('updatedCells', 0)} cells",
            "updated_range": result.get("updatedRange"),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write data: {e}"}


def append_sheet_rows(
    tool_context: ToolContextType,
    rows: list[list[Any]],
    sheet_name: str = "Sheet1",
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """Append rows to the end of a sheet.
    
    Use this to add new data entries without overwriting existing data.
    
    Args:
        tool_context: Agent tool context.
        rows: List of rows to append (each row is a list of values).
        sheet_name: Name of the sheet tab.
        spreadsheet_id: Optional spreadsheet ID.
        
    Returns:
        Dict with append confirmation.
    """
    try:
        service = _get_sheets_service(tool_context)
        
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")
        
        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected. Use connect_spreadsheet first.",
            }
        
        result = service.append_rows(spreadsheet_id, f"{sheet_name}!A:Z", rows)
        
        updates = result.get("updates", {})
        return {
            "status": "success",
            "message": f"Appended {updates.get('updatedRows', len(rows))} rows",
            "updated_range": updates.get("updatedRange"),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to append rows: {e}"}


def create_custom_spreadsheet(
    tool_context: ToolContextType,
    title: str,
    purpose: str,
    columns: list[str],
    sheet_name: str = "Data",
    initial_data: list[list[Any]] | None = None,
) -> dict[str, Any]:
    """Create a new custom spreadsheet based on user requirements.
    
    Use this when the user wants to track something new. Design the columns
    based on what they want to track (sales, inventory, expenses, KPIs, time, etc.)
    
    Args:
        tool_context: Agent tool context.
        title: Title for the spreadsheet.
        purpose: Description of what this spreadsheet is for.
        columns: List of column headers (e.g., ["Date", "Product", "Quantity", "Revenue"]).
        sheet_name: Name for the main data sheet.
        initial_data: Optional initial data rows.
        
    Returns:
        Dict with created spreadsheet details.
    """
    try:
        service = _get_sheets_service(tool_context)
        
        sheets_config = [
            {
                "title": sheet_name,
                "headers": columns,
                "data": initial_data or [],
            }
        ]
        
        info = service.create_spreadsheet(title, sheets_config)
        
        # Store as connected spreadsheet
        tool_context.state["connected_spreadsheet_id"] = info.id
        tool_context.state["connected_spreadsheet_name"] = info.name
        
        return {
            "status": "success",
            "message": f"Created spreadsheet '{info.name}' for {purpose}",
            "spreadsheet": {
                "id": info.id,
                "name": info.name,
                "url": info.url,
                "sheets": info.sheets,
                "columns": columns,
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create spreadsheet: {e}"}


def add_sheet_columns(
    tool_context: ToolContextType,
    new_columns: list[str],
    sheet_name: str = "Sheet1",
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """Add new columns to an existing sheet.
    
    Use this when the user wants to track additional data points.
    
    Args:
        tool_context: Agent tool context.
        new_columns: List of new column headers to add.
        sheet_name: Name of the sheet tab.
        spreadsheet_id: Optional spreadsheet ID.
        
    Returns:
        Dict with update confirmation.
    """
    try:
        service = _get_sheets_service(tool_context)
        
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")
        
        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected.",
            }
        
        # Read existing headers to find next column
        existing = service.read_range(spreadsheet_id, f"{sheet_name}!1:1")
        existing_headers = existing.values[0] if existing.values else []
        
        # Calculate next column letter
        next_col_index = len(existing_headers)
        next_col_letter = _get_column_letter(next_col_index)
        
        # Write new headers
        service.write_range(
            spreadsheet_id,
            f"{sheet_name}!{next_col_letter}1",
            [new_columns],
        )
        
        all_columns = existing_headers + new_columns
        
        return {
            "status": "success",
            "message": f"Added {len(new_columns)} columns: {', '.join(new_columns)}",
            "all_columns": all_columns,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to add columns: {e}"}


def _get_column_letter(index: int) -> str:
    """Convert 0-based column index to Excel-style letter (A, B, ..., Z, AA, AB, ...)."""
    result = ""
    while index >= 0:
        result = chr(65 + (index % 26)) + result
        index = index // 26 - 1
    return result


# Export all tools for agent use
GOOGLE_SHEETS_TOOLS = [
    list_connected_spreadsheets,
    connect_spreadsheet,
    read_sheet_data,
    write_sheet_data,
    append_sheet_rows,
    create_custom_spreadsheet,
    add_sheet_columns,
]
