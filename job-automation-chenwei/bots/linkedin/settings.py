'''
Paramètres du bot LinkedIn - Hu Chenwei
'''

close_tabs = True
follow_companies = False
run_non_stop = False
alternate_sortby = True
cycle_date_posted = True
stop_date_cycle_at_24hr = True

# Click intervals (en secondes, aléatoires)
min_delay = 1.5
max_delay = 4.5
type_min_delay = 0.05
type_max_delay = 0.15

# Keep screen awake?
keep_screen_awake = False

# Run in background (no browser window)?
run_in_background = True  # WSL headless, Xvfb gère l'affichage

# Stealth mode (evade bot detection)?
stealth_mode = True

# Maximum number of applications per run
max_applications = 30

# Skip resume generation (CV is a designed image, not regeneratable)
use_resume_generator = False

# Generate cover letters instead
use_cover_letter_generator = True

# Daily limit (0 = no limit)
daily_limit = 50

# Log level
log_level = "INFO"

# Use custom Chrome profile with LinkedIn session cookies (skip MFA)
safe_mode = False
profile_dir = "/home/user/.auto-job-apply-profile-linkedin"
