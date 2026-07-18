'''
Paramètres du bot LinkedIn - Hu Chenwei
'''

import os
from pathlib import Path

# Dossiers
logs_folder_path = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "auto_job_apply")
file_name = os.path.join(logs_folder_path, "job_details.txt")
failed_file_name = os.path.join(logs_folder_path, "failed_jobs.txt")
generated_resume_path = os.path.join(os.path.join(logs_folder_path, "..", "generated_resumes"))

# Comportement
close_tabs = True
follow_companies = False
run_non_stop = False
alternate_sortby = True
cycle_date_posted = True
stop_date_cycle_at_24hr = True

# Intervalles de clics
min_delay = 1.5
max_delay = 4.5
type_min_delay = 0.05
type_max_delay = 0.15

# Modes
keep_screen_awake = False
run_in_background = False
stealth_mode = True
safe_mode = False
disable_extensions = True
max_applications = 30
daily_limit = 50

# Resume generator (CV is a designed image, skip)
use_resume_generator = False
use_cover_letter_generator = True

# Log
log_level = "INFO"
