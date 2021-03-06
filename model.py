#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4:

import cv2
import numpy as np
import tensorflow as tf
import csv
import os
import sklearn
from keras.models import Sequential
from keras.layers import Flatten, Dense, Lambda, Cropping2D, Dropout, Conv2D
from keras.layers.pooling import MaxPooling2D
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from math import floor

# Data augmentation functions definitions
def do_nothing(image,angle):
    return image, angle

def grayscale(image, angle):
    gray = cv2.cvtColor(np.copy(image), cv2.COLOR_RGB2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB), angle

def mirror(image, angle): 
    return np.fliplr(np.copy(image)), -angle

def random_brightness(image, angle):
    image1 = cv2.cvtColor(np.copy(image),cv2.COLOR_RGB2HSV)
    random_bright = 0.8 + 0.4*(2*np.random.uniform()-1.0)    
    image1[:,:,2] = image1[:,:,2]*random_bright
    image1 = cv2.cvtColor(image1,cv2.COLOR_HSV2RGB)
    return image1, angle

def random_translation(img, angle):
    tx_range,ty_range = 64,64
    rows,cols,ch = img.shape
    p=10 #pad the image (reflect the boundary)
    tr_x = tx_range*np.random.uniform()-tx_range/2 #random number between -tx_range and +tx_range
    tr_y = ty_range*np.random.uniform()-ty_range/2
    Trans_M = np.float32([[1,0,tr_x],[0,1,tr_y]])
    wrap = cv2.copyMakeBorder(img,p,p,p,p,0) #pads image with 10px uniform border
    img = cv2.warpAffine(wrap,Trans_M,(cols,rows))
    
    new_angle = angle + tr_x * 3.75e-4
    return img, new_angle 

#refactor the pandas csv data : takes the data read by pandas, returns a list of dictionaries, each dictionary containing path and angle for a training image, with the list of methods yet unapplied
def make_reference_list(methods_index, data, offset=0.2):
    paths= data.values[:,np.array([0,1,2])].reshape(-1) #flattened list containing center, left, right images paths
    angles = np.array([[center, left, right] for center, left, right in zip(data.values[:,3], data.values[:,3]+offset, data.values[:,3]-offset)]).reshape(-1) #flattened list of corresponding angles
    return [{'path':'../data/IMG/'+path.split('/')[-1], 'angle': angle, 'methods': methods_index} for path,angle in zip(paths,angles)]

#picks a specific element of the array, returns the element and the updated numpy array
def pick(numpy_array,index):
    return numpy_array[index], np.delete(numpy_array, index)

# the logic for making batches
def batch_generator(training_data_reference, methods_list, batch_size = 32):
    #define a list of transformations for each image in the data
    restart_flag = False
    while True:
        
        
        if restart_flag : 
            for data_point in training_data_reference:
                data_point['methods'] = np.array(range(len(methods_list)))
            restart_flag = False
        #methods = methods_list
        print('This should be the beginning of a new epoch...')
        num_samples = len(training_data_reference)

        while True:

            for offset in range(0, num_samples, batch_size):

                # get the next batch images
                batch_samples = training_data_reference[offset:offset+batch_size]
                X_batch, y_batch = np.empty((batch_size, 160 ,320, 3), dtype = np.uint8), np.empty(batch_size)

                #for each image in batch...
                for idx in range(len(batch_samples)):                 

                    #pick the method and refresh the data reference
                    image_path = batch_samples[idx]['path']
                    image = cv2.imread(image_path)
                    angle = batch_samples[idx]['angle']
                    num_methods_left = len(batch_samples[idx]['methods'])

                    #apply a random method and remove it from the list of methods for that datapoint
                    try:
                        random_int = np.random.randint(num_methods_left)
                        method_index,training_data_reference[offset+idx]['methods'] = pick(batch_samples[idx]['methods'], random_int)
                        method = methods[method_index]
                    except ValueError as e: 
                        #method = do_nothing
                        restart_flag = True
                        break
                    # get image and angle from calling selected method
                    X_batch[idx], y_batch[idx] = method(image,angle)

                if restart_flag: 
                    break
                yield X_batch, y_batch
            
            if restart_flag: 
                break

#variables and parameters for training : (tune the model here) 

data_file = '../data/driving_log.csv'
data = pd.read_csv(data_file, header= None, names = ['center', 'left', 'right', 'steering_angle', 'x','y','z'])

#list all the possible augmentation methods here
methods = [grayscale, mirror, random_brightness,do_nothing]
#methods = [grayscale, mirror, random_brightness,random_translation,do_nothing]

methods_index = np.array(range(len(methods)))

left_right_images_offset = 1.2/10 #angle offset for left and right images in radians
training_data_reference = shuffle(make_reference_list(methods_index,data,offset=left_right_images_offset))

train_samples, validation_samples = train_test_split(training_data_reference, test_size= 0.2)

bs = 32
#train_generator,train_generator_copy  = tee(batch_generator(train_samples , methods ,batch_size=bs))
train_generator = batch_generator(train_samples, methods, batch_size=bs) 
validation_generator = batch_generator(validation_samples ,methods ,  batch_size=bs)

#X_sample,_ = next(train_generator_copy)
#row, col, ch =  X_sample[0].shape
row, col, ch = 160, 320, 3 
#model
model = Sequential()
model.add(Cropping2D(cropping = ((70,25),(0,0)),input_shape=(row,col,ch)))
model.add(Lambda(lambda x: (x-128)/128))
model.add(Conv2D(24, (5, 5), padding="same", activation="elu", strides=(2, 2)))
model.add(Conv2D(36, (5, 5), padding="same", activation="elu", strides=(2, 2)))
model.add(Conv2D(48, (5, 5), padding="same", activation="elu", strides=(2, 2)))
model.add(Dropout(0.5))
model.add(Conv2D(64, (3, 3), padding="same", activation="elu"))
model.add(Conv2D(64, (3, 3), padding="same", activation="elu"))
model.add(Dropout(0.5))
model.add(Flatten())
model.add(Dense(120))
model.add(Dense(84))
model.add(Dense(1))

from keras.utils import plot_model
plot_model(model, to_file='model.png')

#train
model.compile(loss='mse', optimizer='adam')
batches_per_epoch = int(floor(len(train_samples)*len(methods)/bs))
validation_batches_per_epoch = int(floor(len(validation_samples)*len(methods)/bs)) 
history_object = model.fit_generator(train_generator, steps_per_epoch=batches_per_epoch, 
validation_data=validation_generator, validation_steps=validation_batches_per_epoch, epochs=10, verbose = 1)

#save
model.save('../model.h5')


#This is to display training / validation losses
### print the keys contained in the history object
print(history_object.history.keys())
fig= plt.figure()
### plot the training and validation loss for each epoch
plt.plot(history_object.history['loss'])
plt.plot(history_object.history['val_loss'])
plt.title('model mean squared error loss')
plt.ylabel('mean squared error loss')
plt.xlabel('epoch')
plt.legend(['training set', 'validation set'], loc='upper right')
#plt.show()
plt.savefig('../loss.png')
