#!/bin/bash
#SBATCH --job-name=chill
#SBATCH --account=climreg
#SBATCH --partition=io
#SBATCH --qos=io
#SBATCH --time=03:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=1
#SBATCH --array=0
#SBATCH --output=/p/tmp/fallah/kerman/chill_%a.log
cd /p/tmp/fallah/kerman
F=1951; L=2025                      # one job: the io QOS takes one array task per account
~/mambaforge/bin/python kerman_chill.py /p/tmp/fallah/kerman/parts/chill.npz $F $L
