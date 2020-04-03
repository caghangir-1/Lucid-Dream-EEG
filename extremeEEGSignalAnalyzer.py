# -*- coding: utf-8 -*-
"""
Created on Wed Apr  1 13:06:35 2020

@author: Cagatay Demirel
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import hilbert, savgol_filter, butter, hamming, lfilter, filtfilt, resample, welch, argrelextrema
from scipy.signal import lfilter, hamming, savgol_filter, hilbert, fftconvolve, butter, iirnotch, freqz, firwin, iirfilter
from struct import unpack
import os
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn import linear_model, svm, neighbors
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, cross_val_predict
from sklearn.metrics import confusion_matrix
from sklearn.neighbors import NearestNeighbors
from sklearn.neural_network import MLPClassifier
from scipy.stats import kurtosis, skew
import random
import itertools
import pickle
import librosa
from scipy.fftpack import fft
import pywt
import mne
import csv

def envelopeCreator(timeSignal, degree, fs):
    absoluteSignal = np.abs(hilbert(timeSignal))
    intervalLength = int(fs / 40 + 1) 
    amplitude_envelopeFiltered = savgol_filter(absoluteSignal, intervalLength, degree)
    return amplitude_envelopeFiltered  

def butter_bandpass(lowcut, highcut, fs, order=3): # 3 ten sonra lfilter NaN degerler vermeye basliyor
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band', analog=False)
#    b, a = iirfilter(5, [low, high], rs=60, rp=60, btype='band', analog=False, ftype='cheby1')
    return b, a
    
def butter_lowpass(cutoff, fs, order=3):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

# band-pass filter between two frequency     
def butter_bandpass_filter(data, lowcut, highcut, fs, order=3):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
#    y = lfilter(b, a, data)
    y = filtfilt(b, a, data)
    return y

def butter_lowpass_filter(data, cutoff, fs, order=3):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y

def FFT(signal, Fs):
    nFFT = len(signal) / 2
    nFFT = int(nFFT)
    #Hamming Window
    w = np.hamming(len(signal))
    #FFT
    X = abs(fft(signal * w))                                  # get fft magnitude
    X = X[0:nFFT]                                    # normalize fft
    X = X / len(X)
    
    fIndexes = (Fs / (2*nFFT)) * np.r_[0:nFFT] # [1,9] 9peet üretti
    
    return X, fIndexes
    
def hpssFilter(data):
    data = librosa.effects.hpss(data.astype("float64"), margin=(1.0,5.0))    
    return data

def binPower(signal, Band, Fs):
    nFFT = len(signal) / 2
    nFFT = int(nFFT)
    #Hamming Window
    w = np.hamming(len(signal))
    #FFT
    X = abs(fft(signal * w))                                  # get fft magnitude
    X = X[0:nFFT]                                    # normalize fft
    X = X / len(X)
    
    power = np.zeros(len(Band) - 1)
    for freq_index in range(0, len(Band) - 1):
        freq = Band[freq_index]
        nextFreq = Band[freq_index + 1]
        beginInd = int(np.floor(freq * len(signal) / Fs))
        endInd = int(np.floor(nextFreq * len(signal) / Fs))
        power[freq_index] = sum(X[beginInd:endInd])
    power_ratio = power / sum(power)
    return power, power_ratio

def pfd(X, D=None):
    """Compute Petrosian Fractal Dimension of a time series from either two
    cases below:
        1. X, the time series of type list (default)
        2. D, the first order differential sequence of X (if D is provided,
           recommended to speed up)
    In case 1, D is computed using Numpy's difference function.
    To speed up, it is recommended to compute D before calling this function
    because D may also be used by other functions whereas computing it here
    again will slow down.
    """
    if D is None:
        D = np.diff(X)
        D = D.tolist()
    N_delta = 0  # number of sign changes in derivative of the signal
    for i in range(1, len(D)):
        if D[i] * D[i - 1] < 0:
            N_delta += 1
    n = len(X)
    return np.log10(n) / (np.log10(n) + np.log10(n / n + 0.4 * N_delta))
    
def hfd(X, Kmax):
    """ Compute Hjorth Fractal Dimension of a time series X, kmax
     is an HFD parameter
    """
    L = []
    x = []
    N = len(X)
    for k in range(1, Kmax):
        Lk = []
        for m in range(0, k):
            Lmk = 0
            for i in range(1, int(np.floor((N - m) / k))):
                Lmk += abs(X[m + i * k] - X[m + i * k - k])
            Lmk = Lmk * (N - 1) / np.floor((N - m) / float(k)) / k
            Lk.append(Lmk)
        L.append(np.log(np.mean(Lk)))
        x.append([np.log(float(1) / k), 1])

    (p, r1, r2, s) = np.linalg.lstsq(x, L)
    return p[0]

def hjorth(X, D=None):
    """ Compute Hjorth mobility and complexity of a time series from either two
    cases below:
        1. X, the time series of type list (default)
        2. D, a first order differential sequence of X (if D is provided,
           recommended to speed up)
    In case 1, D is computed using Numpy's Difference function.
    Notes
    -----
    To speed up, it is recommended to compute D before calling this function
    because D may also be used by other functions whereas computing it here
    again will slow down.
    Parameters
    ----------
    X
        list
        a time series
    D
        list
        first order differential sequence of a time series
    Returns
    -------
    As indicated in return line
    Hjorth mobility and complexity
    """

    if D is None:
        D = np.diff(X)
        D = D.tolist()

    D.insert(0, X[0])  # pad the first difference
    D = np.array(D)

    n = len(X)

    M2 = float(sum(D ** 2)) / n
    TP = sum(np.array(X) ** 2)
    M4 = 0
    for i in range(1, len(D)):
        M4 += (D[i] - D[i - 1]) ** 2
    M4 = M4 / n

    return np.sqrt(M2 / TP), np.sqrt(float(M4) * TP / M2 / M2)  # Hjorth Mobility and Complexity

def hurst(X):
    """ Compute the Hurst exponent of X. If the output H=0.5,the behavior
    of the time-series is similar to random walk. If H<0.5, the time-series
    cover less "distance" than a random walk, vice verse.
    Parameters
    ----------
    X
        list
        a time series
    Returns
    -------
    H
        float
        Hurst exponent
    Notes
    --------
    Author of this function is Xin Liu
    Examples
    --------
    >>> import pyeeg
    >>> from numpy.random import randn
    >>> a = randn(4096)
    >>> pyeeg.hurst(a)
    0.5057444
    """
    X = np.array(X)
    N = X.size
    T = np.arange(1, N + 1)
    Y = np.cumsum(X)
    Ave_T = Y / T

    S_T = np.zeros(N)
    R_T = np.zeros(N)

    for i in range(N):
        S_T[i] = np.std(X[:i + 1])
        X_T = Y - T * Ave_T[i]
        R_T[i] = np.ptp(X_T[:i + 1])

    R_S = R_T / S_T
    R_S = np.log(R_S)[1:]
    n = np.log(T)[1:]
    A = np.column_stack((n, np.ones(n.size)))
    [m, c] = np.linalg.lstsq(A, R_S)[0]
    H = m
    return H
    
def dfa(X, Ave=None, L=None):
    """Compute Detrended Fluctuation Analysis from a time series X and length of
    boxes L.
    The first step to compute DFA is to integrate the signal. Let original
    series be X= [x(1), x(2), ..., x(N)].
    The integrated signal Y = [y(1), y(2), ..., y(N)] is obtained as follows
    y(k) = \sum_{i=1}^{k}{x(i)-Ave} where Ave is the mean of X.
    The second step is to partition/slice/segment the integrated sequence Y
    into boxes. At least two boxes are needed for computing DFA. Box sizes are
    specified by the L argument of this function. By default, it is from 1/5 of
    signal length to one (x-5)-th of the signal length, where x is the nearest
    power of 2 from the length of the signal, i.e., 1/16, 1/32, 1/64, 1/128,
    ...
    In each box, a linear least square fitting is employed on data in the box.
    Denote the series on fitted line as Yn. Its k-th elements, yn(k),
    corresponds to y(k).
    For fitting in each box, there is a residue, the sum of squares of all
    offsets, difference between actual points and points on fitted line.
    F(n) denotes the square root of average total residue in all boxes when box
    length is n, thus
    Total_Residue = \sum_{k=1}^{N}{(y(k)-yn(k))}
    F(n) = \sqrt(Total_Residue/N)
    The computing to F(n) is carried out for every box length n. Therefore, a
    relationship between n and F(n) can be obtained. In general, F(n) increases
    when n increases.
    Finally, the relationship between F(n) and n is analyzed. A least square
    fitting is performed between log(F(n)) and log(n). The slope of the fitting
    line is the DFA value, denoted as Alpha. To white noise, Alpha should be
    0.5. Higher level of signal complexity is related to higher Alpha.
    Parameters
    ----------
    X:
        1-D Python list or numpy array
        a time series
    Ave:
        integer, optional
        The average value of the time series
    L:
        1-D Python list of integers
        A list of box size, integers in ascending order
    Returns
    -------
    Alpha:
        integer
        the result of DFA analysis, thus the slope of fitting line of log(F(n))
        vs. log(n). where n is the
    Examples
    --------
    >>> import pyeeg
    >>> from numpy.random import randn
    >>> print(pyeeg.dfa(randn(4096)))
    0.490035110345
    Reference
    ---------
    Peng C-K, Havlin S, Stanley HE, Goldberger AL. Quantification of scaling
    exponents and crossover phenomena in nonstationary heartbeat time series.
    _Chaos_ 1995;5:82-87
    Notes
    -----
    This value depends on the box sizes very much. When the input is a white
    noise, this value should be 0.5. But, some choices on box sizes can lead to
    the value lower or higher than 0.5, e.g. 0.38 or 0.58.
    Based on many test, I set the box sizes from 1/5 of    signal length to one
    (x-5)-th of the signal length, where x is the nearest power of 2 from the
    length of the signal, i.e., 1/16, 1/32, 1/64, 1/128, ...
    You may generate a list of box sizes and pass in such a list as a
    parameter.
    """

    X = np.array(X)

    if Ave is None:
        Ave = np.mean(X)

    Y = np.cumsum(X)
    Y -= Ave

    if L is None:
        L = np.floor(len(X) * 1 / (2 ** np.array(list(range(4, int(np.log2(len(X))) - 4)))))

    F = np.zeros(len(L))  # F(n) of different given box length n

    for i in range(0, len(L)):
        n = int(L[i])                        # for each box length L[i]
        if n == 0:
            print("time series is too short while the box length is too big")
            print("abort")
            exit()
        for j in range(0, len(X), n):  # for each box
            if j + n < len(X):
                c = list(range(j, j + n))
                # coordinates of time in the box
                c = np.vstack([c, np.ones(n)]).T
                # the value of data in the box
                y = Y[j:j + n]
                # add residue in this box
                F[i] += np.linalg.lstsq(c, y)[1]
        F[i] /= ((len(X) / n) * n)
    F = np.sqrt(F)

    Alpha = np.linalg.lstsq(np.vstack([np.log(L), np.ones(len(L))]).T, np.log(F))[0][0]

    return Alpha

def statisticalFeatures(signal):
    ''' Statisctical features'''
    kurt     = kurtosis(signal, fisher = False)
    skewness = skew(signal)
    mean     = np.mean(signal)
    median   = np.median(signal)
    std      = np.std(signal)
    ''' Coefficient of variation '''
    coeff_var = std / mean
    
    allData = np.array([kurt, skewness, mean, median, std, coeff_var])
    return allData

def waveletDecomposition(signal):
    ''' Wavelet Decomposition ''' 
    cA,cD=pywt.dwt(signal,'coif1')
    # cA_values.append(cA)
    
    cA_mean = np.mean(cA)
    cA_std = np.std(cA)
    cA_Energy = np.sum(np.square(cA))
    cD_mean = np.mean(cD)
    cD_std = np.std(cD)
    cD_Energy = np.sum(np.square(cD))
    Entropy_D = np.sum(np.square(cD) * np.log(np.square(cD)))
    Entropy_A = np.sum(np.square(cA) * np.log(np.square(cA)))
    
    allData = np.array([cA_mean, cA_std, cA_Energy, cD_mean, cD_std, Entropy_D, Entropy_A])
    return allData

def firstSecondDiff_MeanMax(signal):
    ''' First and second difference mean and max '''
    sum1  = 0.0
    sum2  = 0.0
    Max1  = 0.0
    Max2  = 0.0
    first_diff = np.zeros(len(signal)-1)
    
    for j in range(len(signal)-1):
            sum1     += abs(signal[j+1]-signal[j])
            first_diff[j] = abs(signal[j+1]-signal[j])
            
            if first_diff[j] > Max1: 
                Max1 = first_diff[j] # fi
                
    for j in range(len(signal)-2):
            sum2 += abs(first_diff[j+1]-first_diff[j])
            if abs(first_diff[j+1]-first_diff[j]) > Max2 :
            	Max2 = first_diff[j+1]-first_diff[j] 
                
    diff_mean1 = sum1 / (len(signal)-1)
    diff_mean2 = sum2 / (len(signal)-2) 
    diff_max1  = Max1
    diff_max2  = Max2
    
    allData = np.array([diff_mean1, diff_mean2, diff_max1, diff_max2])
    return allData

def variance_and_meanof_vertex_and_vertex_slope(signal):
    ''' Variance and Mean of Vertex to Vertex Slope '''
    t_max   = argrelextrema(signal, np.greater)[0]
    amp_max = signal[t_max]
    t_min   = argrelextrema(signal, np.less)[0]
    amp_min = signal[t_min]
    tt      = np.concatenate((t_max,t_min),axis=0)
    if len(tt)>0:
        tt.sort() #sort on the basis of time
        h=0
        amp = np.zeros(len(tt))
        res = np.zeros(len(tt)-1)
        
        for l in range(len(tt)):
                amp[l] = signal[tt[l]]
                
        out = np.zeros(len(amp)-1)     
         
        for j in range(len(amp)-1):
            out[j] = amp[j+1]-amp[j]
        amp_diff = out
        
        out = np.zeros(len(tt)-1)  
        
        for j in range(len(tt)-1):
            out[j] = tt[j+1]-tt[j]
        tt_diff = out
        
        for q in range(len(amp_diff)):
                res[q] = amp_diff[q]/tt_diff[q] #calculating slope        
        
        slope_mean = np.mean(res) 
        slope_var  = np.var(res)   
    else:
        slope_var, slope_mean = 0, 0
        
    allData = np.array([slope_mean, slope_var])
    return allData

'''============================================ EDF Reading & Decomposing ==========================================='''
def EDFDecomposer(multipleFolders, writing_directory):
    
    os.chdir(writing_directory) #write everything into that directory
    
    if(len(multipleFolders) == 1):
        multipleFolders = multipleFolders, #change string into tuple
    open('meta_edf_decomposition.csv', 'w', newline='')
    file_overall = open("meta_edf_decomposition_overall.txt","w") 
    
    #====== Initial Definitions ======
    allFs = list()
    all_datachannels_all_folders = list()
    common_channels_all_folders = list()
    allLengthHours = list()
    allInfo = list()
    overallAmountofEDFs = 0    
    #====== Initial Definitions ======

    for folder_path in multipleFolders:
        files = list()
        for file in os.listdir(folder_path):
            if file.endswith(".edf"):
                files.append(file)
        
        #===== Definitions =====
        dataChannels = list()
        dataSamplingRates = list()
        lengthSeconds = list()
        count = len(files)
        dataInfos = list()
        tempList = list()
        #===== Definitions =====
        
        overallAmountofEDFs += count
        
        #======= Read EDF File =============
        for i in range(count):
            data = mne.io.read_raw_edf(folder_path + '/' + files[i])
            # dataSets.append(data)
            dataInfo = data.info
            dataInfos.append(dataInfo)
            dataChannels.append(dataInfo['ch_names'])
            dataSamplingRates.append(dataInfo['sfreq'])
            lengthSeconds.append(len(list(data[0])[0].flatten()) / dataInfo['sfreq'])
            
            allFs.append(dataInfo['sfreq'])
            # allDataChannels.append(dataInfo['ch_names'])
        #======= Read EDF File =============
        
        lengthMinutes, lengthHours = list(), list()
        for i in range(count):
            lengthMinutes.append(lengthSeconds[i] / 60)
            lengthHours.append(lengthMinutes[i] / 60)
            allLengthHours.append(lengthMinutes[i] / 60)
            
        #====== Add items to list =======
        tempList.append(dataInfo)
        tempList.append(dataChannels)
        tempList.append(dataSamplingRates)
        tempList.append(lengthHours)
        
        allInfo.append(tempList)
        #====== Add items to list =======
            
        '''===== Write information to a CSV file =========='''
        folder_name = folder_path.split('/')[-1]
        row_list = [[folder_name, 'File ID', 'Channel Size', 'Channels', 'Fs', 'Length(minutes)', 'Length(hours)']]
        for i in range(count):
            row_list.append(['', files[i].split('.edf')[0], str(len(dataChannels[i])), dataChannels[i], str(dataSamplingRates[i]), \
                            str(round(lengthMinutes[i],2)), str(round(lengthHours[i],2))])
            
        with open('meta_edf_decomposition.csv', 'a+', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(row_list)    
        
        with open('meta_edf_decomposition.csv', 'a+', newline='') as file:
            writer = csv.writer(file, escapechar='/', quoting=csv.QUOTE_NONE)
            writer.writerow('')
            writer.writerow('')
        '''===== Write information to a CSV file =========='''
         
        '''============ Calculation of statistics for each folder ==============='''
        amountofEDF = count
        minHours, maxHours = round(min(lengthHours),2), round(max(lengthHours),2)
        varietyOfFs, counts = np.unique(dataSamplingRates, return_counts=True)
        most_used_Fs_of_folder = varietyOfFs[np.argmax(counts)] 
        
        #===== All Data Channels Appending ====
        alldatachannels_one_folder = list()
        for dataChannels_one_file in dataChannels:
            for channel in dataChannels_one_file:
                alldatachannels_one_folder.append(channel)
                all_datachannels_all_folders.append(channel)
        #===== All Data Channels Appending ====
        
        unique_channels_one_folder = np.unique(alldatachannels_one_folder)
        
        #===== Common channel finding for a folder =====
        if(len(dataChannels) >= 2):
            common_channels_one_folder=list(set(dataChannels[0]).intersection(dataChannels[1]))
            for i in range(1, len(dataChannels)-1):
                common_channels_one_folder=list(set(common_channels_one_folder).intersection(dataChannels[i+1]))
            common_channels_all_folders.append(common_channels_one_folder) #it is already string array
        
        else:
            common_channels_one_folder = dataChannels[0] #it is list and to string array by [0]
            common_channels_all_folders.append(common_channels_one_folder) 
            
        #===== Common channel finding for a folder =====
        
        '''============ Calculation of statistics for each folder==============='''                
        #===== Write Overall Information of single folder to a text file ========
        file_overall.write(folder_name + ' :\n')
        file_overall.write('Amount of EDF files : ' + str(amountofEDF) + '\n')
        file_overall.write('Minimum length of EDF files : ' + str(minHours) + ' hours\n')
        file_overall.write('Maximum length of EDF files : ' + str(maxHours) + ' hours\n')
        file_overall.write('Fs variations :' + str(varietyOfFs) + ' Hz\n')
        file_overall.write('Most Used Fs :' + str(most_used_Fs_of_folder) + ' Hz\n')
        file_overall.write('Unique channels :' + str(unique_channels_one_folder) + '\n')
        file_overall.write('Common channels :' + str(common_channels_one_folder) + '\n')
        file_overall.write('Common channel amount :' + str(len(common_channels_one_folder)) + '\n')
        file_overall.write('\n') #gap     
        file_overall.write('****************************************') #gap for next folder
        file_overall.write('\n') #gap for next folder    
        #===== Write Overall Information of single folder to a text file ========

    '''======= Write Overall Information of whole folder to a text file ========='''    
    
    #=============== Overall Statistics ===============
    overall_unique_dataChannels = np.unique(all_datachannels_all_folders)
    unique_Fs_of_all_folders, counts = np.unique(allFs, return_counts=True)
    most_used_Fs_of_all_folders = unique_Fs_of_all_folders[np.argmax(counts)]   
    #===== Common channel finding for a folder =====

    if(len(common_channels_all_folders) >= 2):
        overall_common_channels_all_folders=list(set(common_channels_all_folders[0]).\
                                                 intersection(common_channels_all_folders[1]))
        for i in range(1, len(common_channels_all_folders)-1):
            overall_common_channels_all_folders=list(set(overall_common_channels_all_folders).\
                                                     intersection(common_channels_all_folders[i+1]))
                
        # overall_common_channels_all_folders = common_channels_all_folders #it is already string array
    else:
        overall_common_channels_all_folders = common_channels_all_folders[0]  #it is list and to string array by [0]
    #===== Common channel finding for a folder =====
    
    #=============== Overall Statistics ===============
    
    file_overall.write('Overall :\n')
    file_overall.write('Amount of EDF files :' + str(overallAmountofEDFs) + '\n')
    file_overall.write('Minimum length of whole EDF files ' + str(round(min(allLengthHours),2)) + ' hours\n')
    file_overall.write('Maximum Length of whole EDF files ' + str(round(max(allLengthHours),2)) + ' hours\n')
    file_overall.write('Total Fs variations :' + str(unique_Fs_of_all_folders) + ' Hz\n')
    file_overall.write('Most Used Fs :' + str(most_used_Fs_of_all_folders) + ' Hz\n')
    file_overall.write('Unique channels :' + str(overall_unique_dataChannels) + '\n')
    file_overall.write('Common channels :' + str(overall_common_channels_all_folders) + '\n')
    file_overall.write('Common channel amount :' + str(len(overall_common_channels_all_folders)) + '\n')
    
    '''======= Write Overall Information of whole folder to a text file ========='''
    
    file_overall.close() #finalize
    
    return allInfo, overall_unique_dataChannels, common_channels_all_folders, overall_common_channels_all_folders
'''============================================ EDF Reading & Decomposing ==========================================='''

#================================================================================================================================    
    
def RecvData(socket, requestedSize):
    returnStream = ''
    while len(returnStream) < requestedSize:
        databytes = socket.recv(requestedSize - len(returnStream))
        if databytes == '':
            raise (RuntimeError, "connection broken")
        returnStream += databytes
 
    return returnStream 
    
def SplitString(raw):
    stringlist = []
    s = ""
    for i in range(len(raw)):
        if raw[i] != '\x00':
            s = s + raw[i]
        else:
            stringlist.append(s)
            s = ""

    return stringlist

    # read from tcpip socket
def GetProperties(rawdata):

    # Extract numerical data
    (channelCount, samplingInterval) = unpack('<Ld', rawdata[:12])

    # Extract resolutions
    resolutions = []
    for c in range(channelCount):
        index = 12 + c * 8
        restuple = unpack('<d', rawdata[index:index+8])
        resolutions.append(restuple[0])

    # Extract channel names
    channelNames = SplitString(rawdata[12 + 8 * channelCount:])

    return (channelCount, samplingInterval, resolutions, channelNames)
    
def GetData(rawdata, channelCount):

    # Extract numerical data
    (block, points, markerCount) = unpack('<LLL', rawdata[:12])

    # Extract eeg data as array of floats
    data = []
    for i in range(points * channelCount):
        index = 12 + 4 * i
        value = unpack('<f', rawdata[index:index+4])
        data.append(value[0])

    # Extract markers
    markers = []
    index = 12 + 4 * points * channelCount
    for m in range(markerCount):
        markersize = unpack('<L', rawdata[index:index+4])

        ma = Marker()
        (ma.position, ma.points, ma.channel) = unpack('<LLl', rawdata[index+4:index+16])
        typedesc = SplitString(rawdata[index+16:index+markersize[0]])
        ma.type = typedesc[0]
        ma.description = typedesc[1]

        markers.append(ma)
        index = index + markersize[0]

    return (block, points, markerCount, data, markers)

def distinguishData(oneBigSignal, channelCount, resolutions):
    i = 0
    sampleCount = 0  
    chunkAmount = 1
    dataSeparated = np.zeros((channelCount, int(len(oneBigSignal)/channelCount)))#
    while 1:
        for j in range(0,channelCount):
            dataSeparated[j,sampleCount:sampleCount+chunkAmount] = [k * resolutions[0] for k in oneBigSignal[i:i+chunkAmount]]
            i = i + chunkAmount
        sampleCount = sampleCount + chunkAmount   
        if(i >= len(oneBigSignal)):
            break
    return dataSeparated

def envelopeCreator(timeSignal, degree, Fs):
    absoluteSignal = np.abs(hilbert(timeSignal))
    intervalLength = int(Fs / 10 + 1) 
    amplitude_envelopeFiltered = savgol_filter(absoluteSignal, intervalLength, degree)
    return amplitude_envelopeFiltered
    
def notchFilter(data, Fs, f0, Q):
    w0 = f0/(Fs/2)
    b, a = iirnotch(w0, Q)
    y = filtfilt(b, a, data)
#    bp_stop_Hz = np.array([49.0, 51.0])
#    b, a = butter(2,bp_stop_Hz/(Fs / 2.0), 'bandstop')
#    w, h = freqz(b, a)
    return y

def eegFilteringOfflineEyeClosed(data, channelCount, stimulusLog, sampFreq, lowPass, highPass, deletionWindowAmount, order=3):
    dataSeparatedFilt = np.zeros((channelCount, len(data[0,:])))   
    for i in range(0,channelCount):    
        tempData = notchFilter(data[i], sampFreq, 50, 30)
        dataSeparatedFilt[i] = butter_bandpass_filter(tempData, lowPass, highPass, sampFreq, order)
    
    dataSeparatedFilt2 = dataSeparatedFilt[:,2500:]
   
    eegSignals = ([],[],[],[])
    for i in range(0, channelCount):
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
 
    count = 0
    for i in range(0, len(stimulusLog)):
        for j in range(0, channelCount):
             if(count+300 > len(dataSeparatedFilt2[0,:])):
                 break
             eegSignals[j][stimulusLog[i]-1].append(dataSeparatedFilt2[j,count:count+300])
        count += 200
        
#    eegSignals = eegSignalDeletion(eegSignals, channelCount, deletionWindowAmount)

    return eegSignals

def eegFilteringOnlineEyeClose(data, channelCount, sampFreq, lowPass, highPass, correctionMs, order=3):
    correctionWindowAmount = int(correctionMs / 2)
    dataSeparatedFilt = np.zeros((channelCount, len(data[0,:])))
    for i in range(0,channelCount):    
        tempData = notchFilter(data[i], sampFreq, 50, 30)
        tempData = butter_bandpass_filter(data[i], lowPass, highPass, sampFreq, order)
        dataSeparatedFilt[i] = tempData - np.mean(tempData[0:correctionWindowAmount])
    return dataSeparatedFilt

def eegFilteringOnlineEyeOpen(data, channelCount, sampFreq, lowPass, highPass, correctionMs, order=3):
    correctionWindowAmount = int(correctionMs / 2)
    dataSeparatedFilt = np.zeros((channelCount, len(data[0,:])))
    for i in range(0,channelCount):    
#        tempData = notchFilter(data[i], sampFreq, 50, 30)
        tempData = butter_bandpass_filter(data[i], lowPass, highPass, sampFreq, order)
        dataSeparatedFilt[i] = tempData - np.mean(tempData[0:correctionWindowAmount])
    return dataSeparatedFilt

def eegFilteringOfflineEyeOpen(data, channelCount, sampFreq, lowPass, highPass, peakAmp, stimulusLog, deletionWindowAmount, 
                               order=3):
    dataSeparatedFilt = np.zeros((channelCount, len(data[0,:])))   
    for i in range(0,channelCount):    
        tempData = notchFilter(data[i], sampFreq, 50, 30)
        dataSeparatedFilt[i] = butter_bandpass_filter(tempData, lowPass, highPass, sampFreq, order)
    
    dataSeparatedFilt2 = dataSeparatedFilt[:,2500:]
    
    eegSignals = ([],[],[],[])
    for i in range(0, channelCount):
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
        eegSignals[i].append([])
    
    count = 0
    detectedBlinks = 0
    for i in range(0, len(stimulusLog)):
        if(count+300 > len(dataSeparatedFilt2[0,:])):
            break
        tempFp1Signal = dataSeparatedFilt2[0,count:count+300]
        if(np.max(tempFp1Signal) < 40000):            
            for j in range(0, channelCount):           
                eegSignals[j][stimulusLog[i]-1].append(dataSeparatedFilt2[j,count:count+300])
        else:
            detectedBlinks += 1
        count += 200        
        
#    eegSignals = eegSignalDeletion(eegSignals, channelCount, deletionWindowAmount)

    
    return eegSignals, dataSeparatedFilt2, detectedBlinks

#def eegSegmentedDataOfflineEyeClose(eegSignals)

def eegSignalDeletion(eegSignals, channelCount, deletionWindowAmount):
    for i in range(0, channelCount):
        for j in range(5):
            for k in range(deletionWindowAmount):
                del eegSignals[i][j][-1] 
    return eegSignals

def baselineCorrection(eegSignals, channelCount, correctionMs):
    correctionWindowAmount = int(correctionMs / 2)
    for i in range(channelCount):
        for j in range(3):
            for k in range(len(eegSignals[i][j])):
                eegSignals[i][j][k] = eegSignals[i][j][k] - np.mean(eegSignals[i][j][k][0:correctionWindowAmount])
    return eegSignals

def p300Creation(eegSignals, channelCount, windowMilliSecond):  
    windowSize = int(windowMilliSecond / 2)              
    p300Signals = np.zeros((5*channelCount, windowSize))
    stdWindows = np.zeros((channelCount * 5, windowSize))
    for i in range(channelCount):
        for j in range(5):        
            p300Signals[5*i+j] = np.mean(eegSignals[i][j], axis=0)  
            stdWindows[5*i+j] = np.std(eegSignals[i][j], axis=0)
    return p300Signals, stdWindows

def dataSeparationFromRAW(data, channelCount, resolutions):
    i = 0
    sampleCount = 0  
    chunkAmount = 1
    dataSeparated = np.zeros((channelCount, int(len(data)/channelCount)))
    while 1:
        for j in range(0,channelCount):
            dataSeparated[j,sampleCount:sampleCount+chunkAmount] = [k * resolutions[0] for k in data[i:i+chunkAmount]]
            i = i + chunkAmount
        sampleCount = sampleCount + chunkAmount   
        if(i >= len(data)):
            break
    return dataSeparated

def segmentedEEGSignalsP300(eegSignals, channelCount, setDirectory, expNo):
    os.chdir(setDirectory)
    windowMilliSecond = 600
    windowSize = windowMilliSecond / 2              
    stimulusAmount = 3    
    
    foundStimulus = np.zeros((channelCount))
    strings = ['Fp1', 'Fz', 'Cz', 'Pz']
    for i in range(channelCount):
        p300Signals = np.zeros((3, windowSize))
        for j in range(stimulusAmount):    
            p300Signals[j] = np.mean(eegSignals[i][j], axis=0)        
        foundStimulus[i] = P300FinderAlgorithmSTD(p300Signals)
         
        xAxis = np.arange(0, 599, 2)
        plt.figure()
        for j in range(stimulusAmount):
            plt.plot(xAxis, p300Signals[j], label=[j])
            plt.ylabel('Amplitude [uV]', fontsize=20)
            plt.xlabel('Time [Ms]', fontsize=20)
            plt.legend(loc='upper right', fontsize=10)
            plt.title(strings[i] + ' Location, Found Stimulus :' + str(foundStimulus[i]))
            plt.show()
        plt.savefig(strings[i] + '_experiment_eegSegmentedWindowsFiltered' + str(expNo), bbox_inches='tight', 
        pad_inches=0, dpi=200)
        plt.close()
        
    return foundStimulus

def plotP300(p300Signals, channelCount, setDirectory, expNo):
    os.chdir(setDirectory)
    strings = ['Fp1', 'Fz', 'Cz', 'Pz']       
    xAxis = np.arange(0, 599, 2)
    for i in range(channelCount):
        plt.figure()
        for j in range(5): 
            plt.plot(xAxis, p300Signals[5*i+j], label=[j])
            plt.ylabel('Amplitude [uV]', fontsize=20)
            plt.xlabel('Time [Ms]', fontsize=20)
            plt.legend(loc='upper right', fontsize=10)
            plt.title(strings[i] + ' Location')
            plt.show()
        plt.savefig(strings[i] + '_deney_JustStimuluses' + str(expNo), bbox_inches='tight', 
        pad_inches=0, dpi=200)
        plt.close()
        
def plotP300TargetNonTargetFrequent(p300Signals, channelCount, setDirectory, expNo, stimulusNo):
    os.chdir(setDirectory)
    strings = ['Fp1', 'Fz', 'Cz', 'Pz']       
    xAxis = np.arange(0, 599, 2)
    if(stimulusNo==0):
        nontarget = np.array([1,2])
    elif(stimulusNo==1):
        nontarget = np.array([0,2])
    else:
        nontarget = np.array([0,1])
        
    frequent = np.array([3,4])
    
    targetNontargetFreq = np.zeros((3,300))
    label = ['Target','Nontarget','Frequent']
    for i in range(channelCount):
        plt.figure()
        targetNontargetFreq[0] = p300Signals[5*i+stimulusNo]
        targetNontargetFreq[1] = np.mean([p300Signals[nontarget[0]], p300Signals[nontarget[1]]], axis=0)
        targetNontargetFreq[2] = np.mean([p300Signals[frequent[0]], p300Signals[frequent[1]]], axis=0)
        for j in range(3): 
            plt.plot(xAxis, targetNontargetFreq[j], label=label[j])
            plt.ylabel('Amplitude [uV]', fontsize=20)
            plt.xlabel('Time [Ms]', fontsize=20)
            plt.legend(loc='upper right', fontsize=10)
            plt.title(strings[i] + ' Location')
            plt.show()
        plt.savefig(strings[i] + '_tarNontarFrequent_deney' + str(expNo), bbox_inches='tight', 
        pad_inches=0, dpi=200)
        plt.close()        
        
def plotP300WithStds(p300Signals, stdWindows, channelCount, setDirectory, targetStimulus):
    os.chdir(setDirectory)
    strings = ['Fp1', 'Fp2', 'Fz', 'Cz', 'Pz', 'P4', 'P3']      
    xAxis = np.arange(0, 599, 2)
    linestyle = '--'
    for i in range(channelCount):
        plt.figure()
        plt.plot(xAxis, p300Signals[3*i+targetStimulus], linewidth = 4, label=['Target Stimulus'])
        plt.plot(xAxis, p300Signals[3*i+targetStimulus] + stdWindows[3*i+targetStimulus], color = 'black', linestyle = linestyle,
                 label=['P300+Std'], linewidth = 0.7)
        plt.plot(xAxis, p300Signals[3*i+targetStimulus] - stdWindows[3*i+targetStimulus], color = 'black', linestyle = linestyle,
                 label=['P300-Std'], linewidth = 0.7)
        plt.ylabel('Amplitude [uV]', fontsize=20)
        plt.xlabel('Time [Ms]', fontsize=20)
        plt.legend(loc='upper left', fontsize=5)
        plt.title(strings[i] + ' Location with Standart Deviations')
        plt.show()
        plt.savefig(strings[i] + '_experiment3_p300_WithStds', bbox_inches='tight', 
        pad_inches=0, dpi=200)
        plt.close()

def plotP300Stds(stdWindows, setDirectory, targetStimulus, channelCount):
    os.chdir(setDirectory)
    xAxis = np.arange(0, 599, 2)
    strings = ['Fp1', 'Fp2', 'Fz', 'Cz', 'Pz', 'P4', 'P3']      
    for i in range(channelCount):
        plt.plot(xAxis, stdWindows[3*i+targetStimulus])
        plt.ylabel('Amplitude [uV]', fontsize=20)
        plt.xlabel('Time [Sample]', fontsize=20)
        plt.title("Standart Deviation of " + strings[i] + " Windows") 
        plt.show()
        plt.savefig(strings[i] + '_experiment3_stdofWindows', bbox_inches='tight', 
        pad_inches=0, dpi=200)
        plt.close()
        
def P300FinderAlgorithmPeak(p300Signals):
    peaks = np.max(np.abs(p300Signals), axis=1) #P300 finding algorithm
    stimulus = np.argmax(peaks)
    return stimulus

def P300FinderAlgorithmSTD(p300Signals):
    stds = np.std(p300Signals, axis=1)    
    stimulus = np.argmax(stds)    
    return stimulus
    
def P300FinderAlgorithmTotEnergy(p300Signals):
    totens = np.sum(np.abs(p300Signals), axis=1)
    stimulus = np.argmax(totens)    
    return stimulus

def P300TravellerFinder(p300Signals, intervalLength):
    stimulus = P300FinderAlgorithmPeak(p300Signals)
    
    index = np.argmax(p300Signals[stimulus])
    positive_interval, negative_interval = intervalLength, intervalLength
    if(index + intervalLength > 300):
       positive_interval = 300 - index
    if(index - intervalLength < 0):
        negative_interval = index
    
    newP300 = np.zeros((3, positive_interval + negative_interval))
    for i in range(len(p300Signals)):
        newP300[i] = p300Signals[i,index - negative_interval: index + positive_interval]
    
    finalStimulus = P300FinderAlgorithmSTD(newP300)
    return finalStimulus
#=========================================== Trains ========================================================================
#===========================================================================================================================
def allTypeofTrainsetCreator_forAllBrainChannels(eegSignals, stimulusLogs, downSamplingSize, lastNStimulus, label):
    eegSignals_channel0, eegSignals_channel1, eegSignals_channel2, eegSignals_channel3 = list(), list(), list(), list()
    for i in range(len(eegSignals)):
        eegSignals_channel0.append(eegSignals[i][0])
        eegSignals_channel1.append(eegSignals[i][1])
        eegSignals_channel2.append(eegSignals[i][2])
        eegSignals_channel3.append(eegSignals[i][3])
        
    trainsXY_channel0 = allTypeofTrainsetCreator(eegSignals_channel0, stimulusLogs, downSamplingSize, lastNStimulus, label)     
    trainsXY_channel1 = allTypeofTrainsetCreator(eegSignals_channel1, stimulusLogs, downSamplingSize, lastNStimulus, label) 
    trainsXY_channel2 = allTypeofTrainsetCreator(eegSignals_channel2, stimulusLogs, downSamplingSize, lastNStimulus, label) 
    trainsXY_channel3 = allTypeofTrainsetCreator(eegSignals_channel3, stimulusLogs, downSamplingSize, lastNStimulus, label)     
    return trainsXY_channel0, trainsXY_channel1, trainsXY_channel2, trainsXY_channel3    
    

def allTypeofTrainsetCreator(eegSignals, stimulusLogs, downSamplingSize, lastNStimulus, label):
    trainX0All, trainX1All, trainX2All, trainX3All, trainY0All, trainY1All, trainY2All, trainY3All = [],[],[],[],[],[],[],[]
    random.seed(312)
    for i in range(len(eegSignals)):
        temp_eegSignals = eegSignals[i]
        stimulusLog = stimulusLogs[i]
        trainX0, trainY0 = P300SKLDADownSampledTrainsetCreator(temp_eegSignals, downSamplingSize, label[i])    
        trainX1, trainY1 = P300SKLDAOddballParadigmDownsampledTrainsetCreator(temp_eegSignals, lastNStimulus, stimulusLog, downSamplingSize, label[i])
        trainX2, trainY2 = P300SKLDATrainsetCreator(temp_eegSignals, label[i])
        trainX3, trainY3 = P300SKLDAOddballParadigmTrain(temp_eegSignals, stimulusLog, lastNStimulus, label[i])
        
        if(i==0):
            trainX0All, trainX1All, trainX2All, trainX3All = trainX0, trainX1, trainX2, trainX3
            trainY0All, trainY1All, trainY2All, trainY3All = trainY0, trainY1, trainY2, trainY3
        else:
            trainX0All = np.append(trainX0All, trainX0, axis=0)
            trainX1All = np.append(trainX1All, trainX1, axis=0)
            trainX2All = np.append(trainX2All, trainX2, axis=0)
            trainX3All = np.append(trainX3All, trainX3, axis=0)

            trainY0All = np.append(trainY0All, trainY0, axis=0)
            trainY1All = np.append(trainY1All, trainY1, axis=0)
            trainY2All = np.append(trainY2All, trainY2, axis=0)
            trainY3All = np.append(trainY3All, trainY3, axis=0)
        
    trainsXY = ((trainX0All,trainY0All),(trainX1All,trainY1All),(trainX2All,trainY2All),(trainX3All,trainY3All))
    return trainsXY

def allTypeofModelCreator_andCrossValidationAccuracyFinder(trainsXY, typeOfClf, randFrstEstimators, ann_layer1, ann_layer2, brainChannel, plotConf, directorySaveModel, modelFilename):
    scores = np.zeros((2))
    models = list()
    confMats = list()
    j=0
    class_names = ['Non-target Stimulus', 'Target Stimulus']
    for i in range(1): #only take 1. and 3. algorithm
#        if(i==0):
#            j=1
#        else:
        j=3
        trainsXYTemp = trainsXY[j]
        #========= Classifiers ==================
        clf = LinearDiscriminantAnalysis(n_components=None, priors=None, shrinkage='auto',
                                     solver='lsqr', store_covariance=False, tol=0.0001) 
        rndfrst = RandomForestClassifier(n_estimators=randFrstEstimators, criterion='gini', max_depth=None, min_samples_split=2, 
                                     min_samples_leaf=1, min_weight_fraction_leaf=0.0, max_features='auto', 
                                     max_leaf_nodes=None, bootstrap=True, oob_score=False, n_jobs=1, random_state=None, 
                                     verbose=0, warm_start=False, class_weight=None)
        lineardisc = linear_model.SGDClassifier(alpha=0.0001, average=False, class_weight=None, epsilon=0.1,
                                            eta0=0.0, fit_intercept=True, l1_ratio=0.15,
                                            learning_rate='optimal', loss='hinge', n_iter=5, n_jobs=1,
                                            penalty='l2', power_t=0.5, random_state=None, shuffle=True,
                                            verbose=0, warm_start=False)
        svmModel = svm.SVC()
        nbrs = neighbors.KNeighborsClassifier(10, weights='distance')
        
        mlp = MLPClassifier(activation='relu', alpha=1e-05, batch_size='auto',
        beta_1=0.9, beta_2=0.999, early_stopping=False,
        epsilon=1e-08, hidden_layer_sizes=(ann_layer1,ann_layer2), learning_rate='constant',
        learning_rate_init=0.001, max_iter=200, momentum=0.9,
        nesterovs_momentum=True, power_t=0.5, random_state=1, shuffle=True,
        solver='adam', tol=0.0001, validation_fraction=0.1, verbose=False,
        warm_start=False)
        #==========Train==========================
        random.seed(312)
        if(typeOfClf == 0):
            scores[i] = np.mean(cross_val_score(clf, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            y_pred = cross_val_predict(clf,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = clf.fit(trainsXYTemp[0],trainsXYTemp[1])
        elif(typeOfClf == 1):
            scores[i] = np.mean(cross_val_score(rndfrst, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            print(i)
            y_pred = cross_val_predict(rndfrst,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = rndfrst.fit(trainsXYTemp[0],trainsXYTemp[1])
        elif(typeOfClf == 2):
            scores[i] = np.mean(cross_val_score(lineardisc, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            y_pred = cross_val_predict(lineardisc,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = lineardisc.fit(trainsXYTemp[0],trainsXYTemp[1])
        elif(typeOfClf == 3):
            scores[i] = np.mean(cross_val_score(svmModel, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            y_pred = cross_val_predict(svmModel,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = svmModel.fit(trainsXYTemp[0],trainsXYTemp[1])
        elif(typeOfClf == 4):
            scores[i] = np.mean(cross_val_score(nbrs, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            y_pred = cross_val_predict(nbrs,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = nbrs.fit(trainsXYTemp[0],trainsXYTemp[1])
        elif(typeOfClf == 5):
            scores[i] = np.mean(cross_val_score(mlp, trainsXYTemp[0], trainsXYTemp[1].astype("int"), cv=10))
            y_pred = cross_val_predict(mlp,trainsXYTemp[0] ,trainsXYTemp[1].astype("int"), cv=10)
            model = mlp.fit(trainsXYTemp[0],trainsXYTemp[1])
        models.append(model)
        #========== Save Model =====================
        os.chdir(directorySaveModel)
        # save the model to disk
        pickle.dump(model, open(modelFilename, 'wb'))
        #======== Confusion Matrix==============
        confMat = confusion_matrix(trainsXYTemp[1].astype("int"),y_pred)
        if(plotConf == 1):
            confMats.append(confMat)
            plt.figure()
            plot_confusion_matrix(confMat, classes=class_names, title= (brainChannel + ' Confusion matrix'))   
    
    return models, scores, confMats
#============================================= Sub-Train Methods ===================================================================
def P300SKLDADownSampledTrainsetCreator(eegSignals, downSamplingSize, targetStimulus):
    ratio = downSamplingSize / 500
    size = int(300 * ratio)
    
    p300Candidates = np.empty(shape=[0,size])
    trainY = np.empty(shape=[0,1])
    for i in range(3):
        for j in range(len(eegSignals[i])):
            if(i==targetStimulus):
                p300Candidates = np.row_stack((p300Candidates, resample(eegSignals[i][j], size)))
                trainY = np.row_stack((trainY,1))
            else:
                if(random.random() > 0.5):
                    p300Candidates = np.row_stack((p300Candidates, resample(eegSignals[i][j], size)))
                    trainY = np.row_stack((trainY,0))

    return p300Candidates, trainY.astype("int").flatten()
    
def P300SKLDAOddballParadigmDownsampledTrainsetCreator(eegSignals, lastNStimulus, stimulusLog, downSamplingSize, targetStimulus):
    stimulusAmount = 3 # 3 amount of stimulus
    windowMilliSecond = 600
    windowSize = int(windowMilliSecond / 2)   
    ratio = downSamplingSize / 500
    size = int(windowSize * ratio)     
    stimulusAmounts = np.zeros((stimulusAmount)).astype("int")
    
    for i in range(len(stimulusLog)):
        stimulusTemp = stimulusLog[i] - 1
        if(stimulusAmounts[0] >= lastNStimulus and stimulusAmounts[1] >= lastNStimulus and stimulusAmounts[2] >= lastNStimulus):
            break
        else:
            if(stimulusTemp < 3):
                stimulusAmounts[stimulusTemp] += 1
    
    p300Candidates = np.empty(shape=[0,size])
    trainY = np.empty(shape=[0,1])
    for i in range(stimulusAmount):
        for j in range(stimulusAmounts[i]-lastNStimulus, len(eegSignals[i])-lastNStimulus):
            tempP300 = np.mean(eegSignals[i][j:j+lastNStimulus], axis=0)
            tempP300 = resample(tempP300, size)
            if(i==targetStimulus):
                p300Candidates = np.row_stack((p300Candidates, tempP300))
                trainY = np.row_stack((trainY,1))
            else:
                if(random.random() > 0.5):
                    p300Candidates = np.row_stack((p300Candidates, tempP300))
                    trainY = np.row_stack((trainY,0))
            
    return p300Candidates, trainY.astype("int").flatten()

def P300SKLDATrainsetCreator(eegSignals, targetStimulus):
    p300Candidates = np.empty(shape=[0,300])
    trainY = np.empty(shape=[0,1])
    for i in range(3):
        for j in range(len(eegSignals[i])):
            if(i==targetStimulus):
                p300Candidates = np.row_stack((p300Candidates, eegSignals[i][j]))
                trainY = np.row_stack((trainY,1))
            else:
                if(random.random() > 0.5):
                    p300Candidates = np.row_stack((p300Candidates, eegSignals[i][j]))
                    trainY = np.row_stack((trainY,0))   

    return p300Candidates, trainY.astype("int").flatten()
    
def P300SKLDAOddballParadigmTrain(eegSignals, stimulusLog, lastNStimulus, targetStimulus):
    stimulusAmount = 3 # 5 amount of stimulus
    stimulusAmounts = np.zeros((stimulusAmount)).astype("int")      
    
    for i in range(len(stimulusLog)):
        stimulusTemp = stimulusLog[i] - 1
        if(stimulusAmounts[0] >= lastNStimulus and stimulusAmounts[1] >= lastNStimulus and stimulusAmounts[2] >= lastNStimulus):
            break
        else:
            if(stimulusTemp < 3):
                stimulusAmounts[stimulusTemp] += 1
    
    p300Candidates = np.empty(shape=[0,300])
    trainY = np.empty(shape=[0,1])
    for i in range(stimulusAmount):
        for j in range(stimulusAmounts[i]-lastNStimulus, len(eegSignals[i])-lastNStimulus):
            tempP300 = np.mean(eegSignals[i][j:j+lastNStimulus], axis=0)
            if(i==targetStimulus):
                p300Candidates = np.row_stack((p300Candidates, tempP300))
                trainY = np.row_stack((trainY,1))
            else:
                if(random.random() > 0.5):
                    trainY = np.row_stack((trainY,0))   
                    p300Candidates = np.row_stack((p300Candidates, tempP300))
            
    return p300Candidates, trainY.astype("int").flatten()
#==================================================== Tests =======================================================================
def P300SKLDADownSampledTest(model, instantEEGSignal, downSamplingSize):
    ratio = downSamplingSize / 500
    size = int(300 * ratio)     
    foundStimuluses = np.zeros((3))
    
    for i in range(3):
        tempX = resample(instantEEGSignal[i], size).reshape(1,-1)        
        foundStimuluses[i] = model.predict(tempX)
        
    foundStimulus = np.argmax(foundStimuluses)
    return foundStimulus

def P300SLDAOddballParadigmTest(model, lastNEEGSignals, ifANN):
    foundStimuluses = np.zeros((3))
    targetProbs = np.zeros((3))
    
    if(ifANN == 1):
        for i in range(3):
            p300Signals = np.mean(lastNEEGSignals[i], axis=0).reshape(1,-1)
            tempProbs = model.predict_proba(p300Signals)
            targetProbs[i] = tempProbs[0,1]            
        foundStimulus = np.argmax(targetProbs)   
    else:    
        for i in range(3):
            p300Signals = np.mean(lastNEEGSignals[i], axis=0).reshape(1,-1)
            foundStimuluses[i] = model.predict(p300Signals)        
        foundStimulus = np.argmax(foundStimuluses)
        
    return foundStimulus
 
def P300SKLDAOddballParadigmDownsampledTest(model, lastNEEGSignals, downSamplingSize, ifANN):
    ratio = downSamplingSize / 500
    size = int(300 * ratio)     
    foundStimuluses = np.zeros((3,2))
    targetProbs = np.zeros((3))
    
    if(ifANN == 1):
        for i in range(3):
            p300Signals = np.mean(lastNEEGSignals[i], axis=0)
            p300SignalDownSampled = resample(p300Signals, size).reshape(1,-1)
            tempProbs = model.predict_proba(p300SignalDownSampled)
            targetProbs[i] = tempProbs[0,1]            
        foundStimulus = np.argmax(targetProbs)   
    else:
         for i in range(3):
            p300Signals = np.mean(lastNEEGSignals[i], axis=0)
            p300SignalDownSampled = resample(p300Signals, size).reshape(1,-1)
            foundStimuluses[i] = model.predict(p300SignalDownSampled)
         foundStimulus = np.argmax(foundStimuluses)   
         
    return foundStimulus
    
def P300SKLDATest(model, instantEEGSignal):
    foundStimuluses = np.zeros((3))
    
    for i in range(3):
        foundStimuluses[i] = model.predict(instantEEGSignal[i].reshape(1,-1))
        
    foundStimulus = np.argmax(foundStimuluses)
    return foundStimulus
#===================================================================================================================================
def P300RealTimeAnalyzer(eegSignals, channelCount, string):
    windowMilliSecond = 600
    stimulusAmount = len(eegSignals)
    windowSize = int(windowMilliSecond / 2)              
    p300Signals = np.zeros((stimulusAmount, windowSize))

    for i in range(stimulusAmount):        
        p300Signals[i] = np.mean(eegSignals[i], axis=0)  
        
    stimulusStd = P300FinderAlgorithmSTD(p300Signals)
    stimulusPeak = P300FinderAlgorithmPeak(p300Signals)
    stimulusTotEn = P300FinderAlgorithmTotEnergy(p300Signals)
    stimulusTraveller = P300TravellerFinder(p300Signals, 50)
    #===Plotting Realtime P300 ============
#    string = 'Fz'
#    xAxis = np.arange(0, 599, 2)
#    plt.cla()
#    for i in range(stimulusAmount): 
#        plt.plot(xAxis, p300Signals[i], label=[i])
#        plt.ylabel('Amplitude [uV]', fontsize=20)
#        plt.xlabel('Time [Ms]', fontsize=20)
#        plt.legend(loc='upper right', fontsize=10)
#        plt.title(string + ' Location, Found Stimulus :' + str(stimulus))
#        plt.show()
#    plt.pause(.005)
    
    return stimulusStd, stimulusPeak, stimulusTotEn, stimulusTraveller   

def onflineP300Finder(eegSignals, stimulusAmount, stimulusLog, travallerIntervalLength):
    windowAmount = 0
    for i in range(stimulusAmount):
        windowAmount += len(eegSignals[i])
     
    windowMilliSecond = 600    
    windowSize = int(windowMilliSecond / 2)              
    p300Signals = np.zeros((3, windowSize))    
    
    foundStimulusLogStd = []
    foundStimulusLogPeak = []
    foundStimulusLogTotEn = []
    foundStimulusLogTraveller = []  
    
    tempEEGWindows = np.zeros((stimulusAmount,300))
    stCounts = np.zeros((3)).astype("int")
    for i in range(len(stimulusLog)):
        print(i)
        tempEEGWindows[stimulusLog[i]-1] += eegSignals[stimulusLog[i] - 1][stCounts[stimulusLog[i] - 1]]
        stCounts[stimulusLog[i] - 1] += 1            
        p300Signals[stimulusLog[i]-1] = tempEEGWindows[stimulusLog[i]-1] / (i+1)
            
        stimulusStd = P300FinderAlgorithmSTD(p300Signals)
        stimulusPeak = P300FinderAlgorithmPeak(p300Signals)
        stimulusTotEn = P300FinderAlgorithmTotEnergy(p300Signals)
        stimulusTraveller = P300TravellerFinder(p300Signals, travallerIntervalLength)    
        
        foundStimulusLogStd.append(stimulusStd)
        foundStimulusLogPeak.append(stimulusPeak)
        foundStimulusLogTotEn.append(stimulusTotEn)
        foundStimulusLogTraveller.append(stimulusTraveller)  
                
        totStimAmounts = np.zeros((4,stimulusAmount))
        for j in range(stimulusAmount):
            totStimAmounts[0][j] = foundStimulusLogStd.count(j)
        for j in range(stimulusAmount):
            totStimAmounts[1][j] = foundStimulusLogPeak.count(j)
        for j in range(stimulusAmount):
            totStimAmounts[2][j] = foundStimulusLogTotEn.count(j)
        for j in range(stimulusAmount):
            totStimAmounts[3][j] = foundStimulusLogTraveller.count(j)
        
        
    return foundStimulusLogStd, foundStimulusLogPeak, foundStimulusLogTotEn, foundStimulusLogTraveller, totStimAmounts

def brainwaveFinder(eegSignal, Fs, density=True):
#    p300Signal = np.mean(eegSignals, axis=0)
    # eegSignal = notchFilter(eegSignal, Fs, 50, 30)
    
    if(density==False):
        deltaSignal = butter_bandpass_filter(eegSignal, 0.5, 3, 500, order=3)
        thetaSignal = butter_bandpass_filter(eegSignal, 3, 8, Fs, order=3)
        alphaSignal = butter_bandpass_filter(eegSignal, 8, 12, Fs, order=3)
        betaSignal = butter_bandpass_filter(eegSignal, 12, 38, Fs, order=3)
        gammaSignal = butter_bandpass_filter(eegSignal, 38, 48, Fs, order=3)
        
        deltaSignalEnergy = np.sum(deltaSignal**2)
        thetaSignalEnergy = np.sum(thetaSignal**2)
        alphaSignalEnergy = np.sum(alphaSignal**2)
        betaSignalEnergy = np.sum(betaSignal**2)
        gammaSignalEnergy = np.sum(gammaSignal**2)
        
        allEnergies = np.array([deltaSignalEnergy, thetaSignalEnergy, alphaSignalEnergy, betaSignalEnergy, gammaSignalEnergy])
        
        return allEnergies
        
    else:
        deltaSignal = butter_bandpass_filter(eegSignal, 0.5, 3, 500, order=3)
        thetaSignal = butter_bandpass_filter(eegSignal, 3, 8, Fs, order=3)
        lowalphaSignal = butter_bandpass_filter(eegSignal, 8, 10, Fs, order=3)
        highalphaSignal = butter_bandpass_filter(eegSignal, 10, 12, Fs, order=3)
        lowbetaSignal = butter_bandpass_filter(eegSignal, 12, 16, Fs, order=3)
        betaSignal = butter_bandpass_filter(eegSignal, 16, 20, Fs, order=3)
        highbetaSignal = butter_bandpass_filter(eegSignal, 20, 30, Fs, order=3)
        sigmaslowSignal = butter_bandpass_filter(eegSignal, 12, 14, Fs, order=3)
        sigmasfastSignal = butter_bandpass_filter(eegSignal, 14, 16, Fs, order=3)
        lowgammaSignal = butter_bandpass_filter(eegSignal, 30, 40, Fs, order=3)
        highgammaSignal = butter_bandpass_filter(eegSignal, 40, 48, Fs, order=3)
    
        deltaSignalEnergy = np.sum(deltaSignal**2)
        thetaSignalEnergy = np.sum(thetaSignal**2)
        lowalphaSignalEnergy = np.sum(lowalphaSignal**2)
        highalphaSignalEnergy = np.sum(highalphaSignal**2)
        lowbetaSignalEnergy = np.sum(lowbetaSignal**2)
        betaSignalEnergy = np.sum(betaSignal**2)
        highbetaSignalEnergy = np.sum(highbetaSignal**2)
        sigmaslowSignalSignalEnergy = np.sum(sigmaslowSignal**2)
        sigmasfastSignalEnergy = np.sum(sigmasfastSignal**2)
        lowgammaSignalEnergy = np.sum(lowgammaSignal**2)
        highgammaSignalEnergy = np.sum(highgammaSignal**2)
        
        allEnergies = np.array([deltaSignalEnergy, thetaSignalEnergy, lowalphaSignalEnergy, highalphaSignalEnergy, \
                                lowbetaSignalEnergy, betaSignalEnergy, highbetaSignalEnergy, sigmaslowSignalSignalEnergy, \
                                sigmasfastSignalEnergy, lowgammaSignalEnergy, highgammaSignalEnergy])
        
        return allEnergies

def welchMaxPowerofBrainwaves(eegSignal, Fs, freqBandsIndexes, Nfft = 2 ** 15, window='hann', density=True):
    '''Apply Welch to see the dominant Max power in each freq band''' 
    ff, Psd = welch(x=eegSignal, fs=Fs, window=window, nperseg=512, nfft=Nfft)
   
    if(density==False):
        Pow_max_Total = np.max(Psd[np.arange(freqBandsIndexes['Delta'][0], freqBandsIndexes['Gamma'][-1]+1)])
        Pow_max_Delta = np.max(Psd[freqBandsIndexes['Delta']])
        Pow_max_Theta = np.max(Psd[freqBandsIndexes['Theta']])
        Pow_max_Alpha = np.max(Psd[freqBandsIndexes['Alpha']])
        Pow_max_Beta = np.max(Psd[freqBandsIndexes['Beta']])
        Pow_max_Gamma = np.max(Psd[freqBandsIndexes['Gamma']])
        
        allWelchPowers = np.array([Pow_max_Total, Pow_max_Delta, Pow_max_Theta, Pow_max_Alpha, \
                                   Pow_max_Beta, Pow_max_Gamma])
        return allWelchPowers
            
    else:
        Pow_max_Total = np.max(Psd[np.arange(freqBandsIndexes['Delta'][0], freqBandsIndexes['Beta'][-1]+1)])
        Pow_max_Delta = np.max(Psd[freqBandsIndexes['Delta']])
        Pow_max_Theta = np.max(Psd[freqBandsIndexes['Theta']])
        Pow_max_Lowalpha = np.max(Psd[freqBandsIndexes['LowAlpha']])
        Pow_max_Highalpha = np.max(Psd[freqBandsIndexes['HighAlpha']])
        Pow_max_LowBeta = np.max(Psd[freqBandsIndexes['LowBeta']])
        Pow_max_Beta = np.max(Psd[freqBandsIndexes['Beta']])
        Pow_max_HighBeta = np.max(Psd[freqBandsIndexes['HighBeta']])
        Pow_max_SigmaSlow = np.max(Psd[freqBandsIndexes['Sigma_slow']])
        Pow_max_SigmaFast = np.max(Psd[freqBandsIndexes['Sigma_fast']])
        Pow_max_LowGamma = np.max(Psd[freqBandsIndexes['LowGamma']])
        Pow_max_HighGamma = np.max(Psd[freqBandsIndexes['HighGamma']])
        
        allWelchPowers = np.array([Pow_max_Total, Pow_max_Delta, Pow_max_Lowalpha, Pow_max_Highalpha, \
                                   Pow_max_LowBeta, Pow_max_Beta, Pow_max_HighBeta, Pow_max_SigmaSlow, \
                                   Pow_max_SigmaFast, Pow_max_LowGamma, Pow_max_HighGamma])
        return allWelchPowers
  
def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    
#==================================== Area 51 ======================================================
#    ratio = 20 / 500
#    size = int(300 * ratio)     
#    targetProbs = np.zeros((3))
#    for i in range(3):
#        p300Signals = np.mean(tempBigWindow[i], axis=0)
#        p300SignalDownSampled = resample(p300Signals, size).reshape(1,-1)
#        tempProbs = models1[0].predict_proba(p300SignalDownSampled)
#        foundStimuluses[i,0] = np.max(tempProbs)
#        foundStimuluses[i,1] = np.argmax(tempProbs)
#        
#    foundStimulus = foundStimuluses[np.argmax(foundStimuluses[:,0]),1]

# for i in range(3):
#     p300Signals = np.mean(tempBigWindow[i], axis=0)
#     p300SignalDownSampled = resample(p300Signals, size).reshape(1,-1)
#     foundStimuluses[i] = models2[0].predict(p300SignalDownSampled)
# foundStimulus = np.argmax(foundStimuluses)   
#      for i in range(3):
#            p300Signals = np.mean(tempBigWindow[i], axis=0).reshape(1,-1)
#            tempProbs = loaded_model.predict_proba(p300Signals)
#            targetProbs[i] = tempProbs[0,1]            
#      foundStimulus = np.argmax(targetProbs)   
#     foundStimuluses = np.zeros((3))
#     for i in range(3):
#            p300Signals = np.mean(tempBigWindow[i], axis=0).reshape(1,-1)
#            foundStimuluses[i] = models3[1].predict(p300Signals)        
#     foundStimulus = np.argmax(foundStimuluses)