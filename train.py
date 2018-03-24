import cv2
import numpy as np
import tensorflow as tf
import csv
from keras.models import Sequential
from keras.layers import Flatten, Dense, Lambda
from keras.layers.convolutional import Convolution2D
from keras.layers.pooling import MaxPooling2D

lines = []
with open('../data/driving_log.csv') as csvfile:
	reader = csv.reader(csvfile)
	has_header = csv.Sniffer().has_header(csvfile.read(1024))
	csvfile.seek(0) #rewind
	if has_header:
		next(reader)
	for line in reader:
		lines.append(line)

images= []
measurements = []
for line in lines:
	source_path = line[0]
	filename = source_path.split('/')[-1]
	current_path = './data/IMG/' + filename
	image = cv2.imread(current_path)
	images.append(image)
	measurement = float(line[3])
	measurements.append(measurement)

X_train = np.array(images)
y_train = np.array(measurements)
print(X_train.shape)
print(y_train.shape)
#model
'''
model = Sequential()
model.add(Lambda(lambda x: (x-128)/128, input_shape = (160,320,3)))
model.add(Convolution2D(6,5,5, activation='relu'))
model.add(MaxPooling2D())
model.add(Convolution2D(6,5,5, activation='relu'))
model.add(MaxPooling2D())
model.add(Convolution2D(6,5,5, activation='relu'))
model.add(MaxPooling2D())
model.add(Dense(120))
model.add(Dense(84))
model.add(Dense(1))

#train
model.compile(loss='mse', optimizer='adam')
model.fit(X_train, y_train, validation_split= 0.3, shuffle=True, nb_epoch = 5 )

model.save('model.h5')
'''
