import os
import glob
import yaml
import json

def escape_sql(value):
    if value is None:
        return 'NULL'
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"
    return "'" + str(value).replace("'", "''") + "'"

def seed_workflows_sql():
    definitions_dir = "app/workflows/definitions"
    output_file = "supabase/migrations/0009_seed_workflows.sql"
    
    yaml_files = glob.glob(os.path.join(definitions_dir, "*.yaml"))
    print(f"Found {len(yaml_files)} workflow definitions")
    
    sql_statements = [
        "-- Migration: 0009_seed_workflows.sql",
        "-- Description: Seed initial workflow templates",
        "",
        "BEGIN;",
        ""
    ]
    
    for file_path in yaml_files:
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                
            name = data.get('name')
            if not name:
                print(f"Skipping {file_path}: No name found")
                continue
                
            print(f"Generating SQL for: {name}")
            
            description = data.get('description')
            category = data.get('category')
            phases = data.get('phases', [])
            
            # Use DELETE + INSERT for simple seeding
            sql = f"""
            DELETE FROM workflow_templates WHERE name = {escape_sql(name)};
            INSERT INTO workflow_templates (name, description, category, phases)
            VALUES (
                {escape_sql(name)},
                {escape_sql(description)},
                {escape_sql(category)},
                {escape_sql(phases)}
            );
            """
            sql_statements.append(sql)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    sql_statements.append("COMMIT;")
    
    with open(output_file, 'w') as f:
        f.write("\n".join(sql_statements))
        
    print(f"Generated SQL migration: {output_file}")

if __name__ == "__main__":
    seed_workflows_sql()
