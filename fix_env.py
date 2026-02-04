import os

def fix_env():
    env_path = ".env"
    if not os.path.exists(env_path):
        print("No .env file found")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    env_map = {}
    clean_lines = []
    
    for line in lines:
        if "=" in line:
            key, val = line.strip().split("=", 1)
            env_map[key] = val
            # Filter out the potentially bad lines I added
            if key not in ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]:
                clean_lines.append(line)
        else:
            clean_lines.append(line)

    # Add them back with correct values
    if "SUPABASE_URL" in env_map:
        clean_lines.append(f"\nNEXT_PUBLIC_SUPABASE_URL={env_map['SUPABASE_URL']}\n")
    if "SUPABASE_ANON_KEY" in env_map:
        clean_lines.append(f"NEXT_PUBLIC_SUPABASE_ANON_KEY={env_map['SUPABASE_ANON_KEY']}\n")

    with open(env_path, "w") as f:
        f.writelines(clean_lines)
    
    print("Fixed .env file")

if __name__ == "__main__":
    fix_env()
