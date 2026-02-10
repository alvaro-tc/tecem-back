
import os

log_files = ['error.log', 'error.txt', 'error_output.txt']

for log_file in log_files:
    if os.path.exists(log_file):
        print(f"--- Reading last 50 lines of {log_file} ---")
        try:
            with open(log_file, 'r', encoding='utf-16') as f:
                lines = f.readlines()
                print(''.join(lines[-50:]))
        except UnicodeError:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(''.join(lines[-50:]))
            except Exception as e:
                print(f"Error reading {log_file}: {e}")
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
    else:
        print(f"--- {log_file} not found ---")
