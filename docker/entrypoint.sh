#!/bin/bash

# Start the run once job.
echo "Docker container has been started"
declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env

# setup git
cd /hurricane-agent/
git config --local --add remote.origin.fetch +refs/heads/*:refs/remotes/origin/*

# run the tensorflow server
python /hurricane-agent/download_models.py
nohup tensorflow_model_server --model_base_path=/root/forecast --rest_api_port=9000 --model_name=hurricane 2>&1 &

# run the API
nohup python /hurricane-deploy/run.py > logs.txt &

# Setup a cron schedule
echo "SHELL=/bin/bash
BASH_ENV=/container.env
0 * * * * python /hurricane-deploy/report.py hourly >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f
