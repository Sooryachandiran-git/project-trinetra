import os
import csv
from io import StringIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from influxdb_client import InfluxDBClient
import logging

logger = logging.getLogger("HistoryAPI")
router = APIRouter()

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "trinetra-research-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "trinetra")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "trinetra_raw")

def get_query_api():
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        # Using synchronous query API
        return client, client.query_api()
    except Exception as e:
        logger.error(f"Failed to connect to InfluxDB for queries: {e}")
        raise HTTPException(status_code=503, detail="InfluxDB not reachable")

@router.get("/history/telemetry")
def get_telemetry_history(topology_id: Optional[str] = None, minutes: int = 60, ied_id: Optional[str] = None):
    """
    Fetch the last N minutes of grid telemetry. 
    Can be filtered by topology_id and ied_id.
    """
    client, query_api = get_query_api()
    
    # Base query
    query = f'from(bucket: "{INFLUX_BUCKET}")\n  |> range(start: -{minutes}m)\n  |> filter(fn: (r) => r["_measurement"] == "grid_telemetry")'
    if topology_id:
        query += f'\n  |> filter(fn: (r) => r["topology_id"] == "{topology_id}")'
    if ied_id:
        query += f'\n  |> filter(fn: (r) => r["ied_id"] == "{ied_id}")'
        
    # Pivot fields into columns and sort chronologically
    query += '\n  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")\n  |> sort(columns: ["_time"], desc: false)'
    
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        results = []
        for table in tables:
            for record in table.records:
                # Sanitize the output: drop influx specific columns starting with _
                row = {k: v for k, v in record.values.items() if not k.startswith('_') or k == '_time'}
                row['timestamp'] = record.values.get('_time').isoformat() if record.values.get('_time') else None
                results.append(row)
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Error querying telemetry history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()

@router.get("/history/alarms")
def get_alarm_history(topology_id: Optional[str] = None, hours: int = 24):
    """
    Fetch the last N hours of discrete events (attack_events, operator_actions)
    Formatted for the Control Room Alarm Historian table.
    """
    client, query_api = get_query_api()
    
    # We query attack_events and operator_actions and combine them.
    # InfluxDB flux can combine them using or in filter, or we can just fetch all and aggregate.
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r["_measurement"] == "attack_events" or r["_measurement"] == "operator_actions")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
    '''
    
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        results = []
        for table in tables:
            for record in table.records:
                vals = record.values
                timestamp = vals.get('_time')
                measurement = vals.get('_measurement')
                
                # Normalize schema into a generic "alarm log" format for frontend
                entry = {
                    "id": f"{measurement}_{timestamp.timestamp() if timestamp else 0}",
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "type": measurement,
                    "ied_id": vals.get("target_ied", "unknown"),
                }
                
                if measurement == "attack_events":
                    evt = vals.get("event")
                    atype = vals.get("attack_type")
                    entry["severity"] = "CRITICAL"
                    entry["description"] = f"Attack {evt}: {atype} via {vals.get('attack_source_ip', 'unknown')}"
                    entry["details"] = vals.get("attack_params", "")
                
                elif measurement == "operator_actions":
                    action = vals.get("action_type")
                    res = vals.get("action_result")
                    entry["severity"] = "WARNING" if res != "success" else "INFO"
                    entry["description"] = f"Operator Action: {action} ({res})"
                    entry["details"] = f"Response time: {vals.get('response_time_ms', 0)}ms"
                
                results.append(entry)
                
        # Final sort by time desc
        results.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        logger.error(f"Error querying alarm history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()

@router.get("/history/export/{topology_id}")
def export_dataset(topology_id: str):
    """
    Exports the complete ML dataset (grid_telemetry) for a specific topology_id as a CSV file.
    This fulfills the research requirement for reproducible ML dataset generation.
    """
    client, query_api = get_query_api()
    
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: 0)
      |> filter(fn: (r) => r["_measurement"] == "grid_telemetry" and r["topology_id"] == "{topology_id}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: false)
    '''
    
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        
        if not tables:
            raise HTTPException(status_code=404, detail=f"No data found for topology_id: {topology_id}")
            
        # We need a unified set of headers.
        # Since fields can technically be sparse (though DataWriter writes them cleanly),
        # we dynamically collect all keys first.
        all_records = []
        header_set = set(['timestamp', 'topology_id', 'ied_id', 'breaker_id', 'grid_state', 'attack_type', 'attack_target'])
        
        for table in tables:
            for record in table.records:
                row = {k: v for k, v in record.values.items() if not k.startswith('_') or k == '_time'}
                row['timestamp'] = record.values.get('_time').isoformat() if record.values.get('_time') else ''
                # Drop InfluxDB specifics
                row.pop('result', None)
                row.pop('table', None)
                row.pop('_start', None)
                row.pop('_stop', None)
                row.pop('_time', None)
                row.pop('_measurement', None)
                
                header_set.update(row.keys())
                all_records.append(row)
                
        headers = sorted(list(header_set))
        # ensure timestamp is first
        if 'timestamp' in headers:
            headers.remove('timestamp')
            headers.insert(0, 'timestamp')
            
        # Write to CSV in memory
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_records)
        
        output.seek(0)
        
        filename = f"trinetra_dataset_{topology_id}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting dataset: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()
