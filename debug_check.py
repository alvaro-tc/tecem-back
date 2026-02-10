import subprocess
import sys

with open('error_log.txt', 'w', encoding='utf-8') as f:
    subprocess.run(['python', 'manage.py', 'check'], stdout=f, stderr=f)
