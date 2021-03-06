#!/usr/bin/env python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-

import app
import path_load
import os
from  helpers import *
#==============================================================================#
# Define global variables.
#==============================================================================#

# Port adress of OpenBCI Cyton board
# BCI_PORT = '/dev/tty.usbserial-DM00CVLC'
BCI_PORT = path_load.PortSearch().port

#==============================================================================#
# Run application
#==============================================================================#
# connect { if connect on start? }
# electrodes { number of connected electrodes to process}
# time_run { time of trial in seconds }
# mode { one of two modes }
# // mode 1
# Harmonic reference
# // mode 2
# Subharmonic reference

# Initialize app

test = app.CcaLive(
port=BCI_PORT,
connect=True,
electrodes=2,
time_run=20,
mode=1,
save=True
)

#==============================================================================#
# Initialize
#==============================================================================#

print("Number of acquired electrodes: {}".format(test.electrodes))
print("Time of trial: {}".format(test.time_run))
print("Sampling rate: {}".format(test.sampling_rate))
print("Connected on serial port: {}".format(test.bci_port))
print("Application mode: {}".format(test.mode))
if test.mode == 1:
    print ("Application mode: Harmonic reference signals")
if test.mode == 2:
    print ("Application mode: Subharmonic reference signals")
print("".join(["=" for x in range(32)]))

#==============================================================================#
# Stimuli configuration
#==============================================================================#
# Add references signal /
# Stimulus for experiment. Max amount = 4.
# ========================== #
test.add_stimuli(12)
test.add_stimuli(7)
test.add_stimuli(10)
# ========================== #
#==============================================================================#
## SUBJECT ##

SUBJ = 1

#==============================================================================#


print("".join(["=" for x in range(32)]))

print("Starting application...")
test.decission()

try:
    test.get_correlation()
except AttributeError as e:
    pass

# Make sure it's dead.
if test.prcs.is_alive():
    print("Terminating process...")
    test.prcs.terminate()
    print("Done!")

create_subject_from_file(SUBJ)
