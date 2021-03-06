#!/usr/bin/env python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-


# ----------------------------------------------------------------------------#
#                  OpenBCI Cyton CCA Application                              #
# ----------------------------------------------------------------------------#


import sys
import os

OpenBCI_PATH = '/Users/oskar.bedychaj/University/OpenBCI_Python'

# // Load OpenBCI_Python to $PATH variable. //
sys.path.insert(0, OpenBCI_PATH)

from sklearn.cross_decomposition import CCA
import numpy as np
import multiprocessing as mp
import openbci.cyton as bci
import scipy.signal as sig
import time
#import matplotlib.pyplot as plt
from time import gmtime, strftime
import csv


class CcaLive(object):
    """CCA Application for SSVEP detection.

    Parameters
    ----------
    sampling_rate : integer
        Sampling rate of device. Default 256 or 250 (for OpenBCI_Ganglion).
    connect : bool
        Connect to device immediately after object initialization.
    port : string
        MAC Address of a device.
    test_session : bool
        Whether to keep real time processing of packets.
    gui : bool
        GUI Mode on/off

    """
    def __init__(self, sampling_rate=250, connect=True, port='', channels=[],
    path='', test_session=True, electrodes=2, time_run=10, mode=1, save=False):

        self.CHANNELS = channels
        self.PATH = path

        self.bci_port = port
        self.connect = connect

        self.electrodes = electrodes
        self.time_run = time_run
        self.mode = mode
        self.save_to_file = save

        self.reference_signals = []

        self.__fs = 1./sampling_rate
        self.__t = np.arange(0.0, 1.0, self.__fs)

        self.test_session = test_session

        self.board = bci.OpenBCICyton(port=self.bci_port)
        self.board.print_register_settings()
        self.sampling_rate = int(self.board.getSampleRate())

        print ("================================")
        print ("  OpenBCI Cyton CCA Application ")
        print ("================================")

        self.streaming = mp.Event()
        self.terminate = mp.Event()

    def initialize(self):
        self.prcs = mp.Process(target=self.split,
                               args=(self.reference_signals,))
        self.prcs.daemon = True
        self.prcs.start()

    def add_stimuli(self, hz):
        '''Add stimuli to generate artificial signal'''

        self.hz = hz
        self.reference_signals.append(SignalReference(self.hz, self.__t, self.mode))
        print ("Stimuli of {} hz added!".format(self.hz))

    def decission(self):
        status = input("Press Enter to start... ")

        if self.connect:
            self.initialize()

        # Compensate for packet correlation
        time.sleep(self.time_run+1)
        print("".join(["=" for x in range(32)]))
        print("END OF TRIAL")
        print("".join(["=" for x in range(32)]))
        self.prcs.terminate()
        #self.terminate.clear()


        if self.terminate.is_set():
            self.prcs.terminate()
            self.terminate.clear()


    def split(self, ref_signals):

        self.ref = ref_signals

        def handle_sample(sample):
            ''' Save samples into table; single process '''

            self.correlation.acquire_data(sample.channel_data[:self.electrodes])

            # Set termination
            if self.terminate.is_set():
                self.streaming.clear()
                self.board.stop()


        # Board connection #

        self.correlation = CrossCorrelation(self.sampling_rate,
                                            self.electrodes,
                                            self.ref,
                                            self.save_to_file)

        self.board.start_streaming(handle_sample)
        self.board.disconnect()

class SignalReference(object):
    """ Reference signal generator"""
    def __init__(self, hz, t, mode):
        if mode == 1:
            multiplier = 2
        elif mode == 2:
            multiplier = 0.5
        else:
            print ("Incorrect mode!")

        self.hz = hz

        self.reference = np.zeros(shape=(len(t), 4))

        self.reference[:, 0] = np.array([np.sin(2*np.pi*i*self.hz) for i in t]) # sin
        self.reference[:, 1] = np.array([np.cos(2*np.pi*i*self.hz) for i in t]) # cos
        self.reference[:, 2] = np.array([np.sin(2*np.pi*i*self.hz*multiplier) for i in t]) #
        self.reference[:, 3] = np.array([np.cos(2*np.pi*i*self.hz*multiplier) for i in t]) # 

class CrossCorrelation(object):
    """CCA class; returns correlation value for each channel """
    def __init__(self, sampling_rate, channels_num, ref_signals, save_to_file):
        self.signal_file = []
        self.packet_id = 0
        self.all_packets = 0
        self.sampling_rate = sampling_rate
        self.rs = ref_signals
        self.sampling_rate = sampling_rate
        self.channels_num = channels_num
        self.save_to_file = save_to_file
        self.signal_window = np.zeros(shape=(sampling_rate, channels_num))
        self.channels = np.zeros(shape=(len(self.rs), 3), dtype=tuple)
        self.ssvep_display = np.zeros(shape=(len(self.rs), 1), dtype=int)
        self.logging = []

    def acquire_data(self, packet):
        self.signal_window[self.packet_id] = packet
        self.signal_file.append(packet)
        self.packet_id += 1

        if self.packet_id % self.sampling_rate == 0:
            self.all_packets += 1
            filtered = self.filtering(self.signal_window)
            if self.save_to_file:
                self.save_file(filtered)
                self.save_file(self.channels)

            self.correlate(filtered)
            self.make_decission()
            self.print_results()
            self.packet_id = 0

    def save_file(self, list_file):

        if list_file.shape == (self.sampling_rate, self.channels_num):
            myFile = open('outputs/signal_filtered' + '.csv', 'a')

            with myFile:
                writer = csv.writer(myFile)
                writer.writerows(list_file)


        elif list_file.shape == (len(self.rs), 3):
            myFile = open('outputs/results' + '.csv', 'a')

            with myFile:
                writer = csv.writer(myFile)
                writer.writerows(list_file)
        else:
            pass

    def filtering(self, packet):
        """ Push single sample into the list """
        packet = np.squeeze(np.array(packet))

        # Butter bandstop filter 49-51hz
        for i in range(self.channels_num):
            signal = packet[:, i]
            lowcut = 49/(self.sampling_rate*0.5)
            highcut = 51/(self.sampling_rate*0.5)
            [b, a] = sig.butter(4, [lowcut, highcut], 'bandstop')
            packet[:, i] = sig.filtfilt(b, a, signal)

        # Butter bandpass filter 3-49hz
        for i in range(self.channels_num):
            signal = packet[:, i]
            lowcut = 6/(self.sampling_rate*0.5)
            highcut =  20/(self.sampling_rate*0.5)
            [b, a] = sig.butter(4, [lowcut, highcut], 'bandpass')
            packet[:, i] = sig.filtfilt(b, a, signal)

        return packet

    def correlate(self, signal):
        for ref in range(len(self.rs)):
            sample = signal

            cca = CCA(n_components=1)
            cca_ref = CCA(n_components=1)
            cca_all = CCA(n_components=1)

            ref_ = self.rs[ref].reference[:, [0, 1]]
            ref_2 = self.rs[ref].reference[:, [2, 3]]
            ref_all = self.rs[ref].reference[:, [0, 1, 2, 3]]

            cca.fit(sample, ref_)
            cca_ref.fit(sample, ref_2)
            cca_all.fit(sample, ref_all)

            u, v = cca.transform(sample, ref_)
            u_2, v_2 = cca_ref.transform(sample, ref_2)
            u_3, v_3 = cca_all.transform(sample, ref_all)

            corr = np.corrcoef(u.T, v.T)[0, 1]
            corr2 = np.corrcoef(u_2.T, v_2.T)[0, 1]
            corr_all = np.corrcoef(u_3.T, v_3.T)[0, 1]
            self.channels[ref] = corr, corr2, corr_all

    def make_decission(self):
        '''Simple SSVEP Classifier'''
        # TODO: Improve ERP detection.
        best_ = 0
        it_ = 0
        for ref in range(len(self.rs)):
            thereshold_01 = self.channels[ref][0] >= 0.375
            thereshold_02 = self.channels[ref][1] >= 0.22
            if thereshold_01 and thereshold_02:
                if self.channels[ref][0] >= best_:
                    best_ = self.channels[ref][0]
                    it_ = ref
                    self.ssvep_display[it_] = 1
                else:
                    self.ssvep_display[ref] = 0
            else:
                self.ssvep_display[ref] = 0

        self.logging.append(self.ssvep_display.copy())

    def print_results(self):
        ''' Prints results in terminal '''
        print("================================")
        print("Packet ID : %s " % self.all_packets)
        print("================================")
        print("Canonical Correlation:")
        for i in range(len(self.rs)):
            print("Signal {hz}: {channel_value:.3}".format(hz=(str(self.rs[i].hz) + " hz"), channel_value=
                  self.channels[i][0]))
        print("Stimuli detection: {0}".format([str(self.ssvep_display[i])
              for i in range(len(self.ssvep_display))]))
