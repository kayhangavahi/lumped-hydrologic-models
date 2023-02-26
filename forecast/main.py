# -*- coding: utf-8 -*-
"""
Created on Tue Dec 27 14:04:19 2022

@author: kgavahi
"""

import pandas as pd
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.utils import shuffle
import copy
def MSE(X,Y):
	return np.mean((X-Y)**2)**.5
def CORREL(X,Y):
	X_bar = np.nanmean(X)
	Y_bar = np.nanmean(Y)
    
	numerator = np.nansum((X - X_bar) * (Y - Y_bar))
	denominator = np.nansum((X - X_bar)**2)**0.5 * np.nansum((Y - Y_bar)**2)**0.5
	r = numerator / denominator	
	return r
def KGE(x,y):
	r = CORREL(x,y)
	t1 = (r-1)**2
	t2 = (np.nanstd(x)/np.nanstd(y)-1)**2
	t3 = (np.nanmean(x)/np.nanmean(y)-1)**2
	return 1 - (t1+t2+t3)**0.5
def make_dataset(df):
    n_train = len(df)
    n_input = n_train - (input_width + shift) + 1
    
    print('n_input', n_input)
    
    X = np.zeros([n_input, input_width, df.shape[1]])
    #X = np.zeros([n_input, input_width, 2])
    y = np.zeros([n_input, label_width, 1])
    for i in range(n_input):
    
        if i==0:
            print(np.arange(n_input)[i:i+input_width])
            print(np.arange(n_input)[i+input_width+(shift-label_width):i+input_width+shift])
    
        X[i, :, :] = df.iloc[i:i+input_width, :]
        #X[i, :, :] = df.iloc[i:i+input_width, :2]
        
        
        
        y[i, :, 0] = df.iloc[i+input_width+(shift-label_width):i+input_width+shift, -1]
        
    
    ind = np.isnan(np.sum(np.sum(y, axis=1), axis=1))

        
    y = y[~ind]
    X = X[~ind]

    ind = np.isnan(np.sum(np.sum(X, axis=1), axis=1))
        
    y = y[~ind]
    X = X[~ind]


    print(y.shape)
    print(X.shape)        
    
    
    
    return X, y



watershed = '08066500'
data = pd.read_csv(f"GalvestonBay/{watershed}.txt", delimiter=',', header=None)
data.columns = ['year','month','day','flow','PET','rain1','rain2','rain3','rain4']


data['date'] = data['year'].astype(str) + \
    data['month'].astype(str).str.zfill(2) + \
        data['day'].astype(str).str.zfill(2)


data['time'] = pd.to_datetime(data['date'])

data.index= pd.to_datetime(data['time'])

data['daily_rain'] = data['rain1'] + data['rain2'] + data['rain3'] + data['rain4']



data = data[['PET', 'daily_rain', 'flow']]
#data = data[['flow']]



if data.shape[1]==1:
    mode = 'only flow'
else:
    mode = 'all three'

n = len(data)
train_df = data[0:int(n*0.6)]
val_df = data[int(n*0.6):int(n*0.8)]
test_df = data[int(n*0.8):]




train_df['flow'].plot(label='train')
val_df['flow'].plot(label='val')
test_df['flow'].plot(label='test')
ax = plt.gca()
ax.set_ylabel('streamflow (cms)')
ax.legend()


#### See this for Harvey:
#### https://www.weather.gov/crp/hurricane_harvey

print('max flow at row number = ', data['flow'].argmax(axis=0))
print(data.iloc[data['flow'].argmax(axis=0)])




train_mean = train_df.mean()
train_std = train_df.std()

train_df = (train_df - train_mean) / train_std
val_df = (val_df - train_mean) / train_std
test_df = (test_df - train_mean) / train_std






input_width = 20
label_width = 1
shift = 1


X_train, y_train = make_dataset(train_df)
X_val, y_val = make_dataset(val_df)
X_test, y_test = make_dataset(test_df)


X_train, y_train = shuffle(X_train, y_train, random_state=1)



from sklearn.ensemble import RandomForestRegressor
regr = RandomForestRegressor(max_depth=100, random_state=0)
regr.fit(X_train.reshape(X_train.shape[0], input_width*X_train.shape[-1]), 
         y_train.reshape(y_train.shape[0], 1).ravel())

tf.random.set_seed(7)







MAX_EPOCHS = 50

def compile_and_fit(model, patience=2):
  early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                    patience=patience,
                                                    mode='min')

  model.compile(loss=tf.keras.losses.MeanSquaredError(),
                optimizer=tf.keras.optimizers.Adam(),
                metrics=[tf.keras.metrics.MeanAbsoluteError()])
  
  
  
  history = model.fit(X_train, y_train, epochs=MAX_EPOCHS,
                      validation_data=(X_val, y_val),
                      callbacks=[early_stopping])
  
  return history

lstm_model = tf.keras.models.Sequential([
    # Shape [batch, time, features] => [batch, time, lstm_units]
    tf.keras.layers.LSTM(10, return_sequences=False),
    # Shape => [batch, time, features]
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(units=1)
])



history = compile_and_fit(lstm_model)


y_pred =  lstm_model.predict(X_test)
y_pred_rf = regr.predict(X_test.reshape(X_test.shape[0],
                                        input_width*X_test.shape[-1]))* train_std['flow'] + train_mean['flow']


y_pred_base =  X_test[:, -1, -1] * train_std['flow'] + train_mean['flow']


y_pred = y_pred.ravel() * train_std['flow'] + train_mean['flow']
y_test = y_test.ravel() * train_std['flow'] + train_mean['flow']




print(mode)
print('test MSE RF:', MSE(y_pred_rf, y_test), 'baseline MSE:', MSE(y_pred_base, y_test))
print('test CORREL RF:', CORREL(y_pred_rf, y_test), 'baseline CORREL:', CORREL(y_pred_base, y_test))
print('test KGE RF:', KGE(y_pred_rf, y_test), 'baseline KGE:', KGE(y_pred_base, y_test))


print(mode)
print('test MSE LSTM:', MSE(y_pred, y_test), 'baseline MSE:', MSE(y_pred_base, y_test))
print('test CORREL LSTM:', CORREL(y_pred, y_test), 'baseline CORREL:', CORREL(y_pred_base, y_test))
print('test KGE LSTM:', KGE(y_pred, y_test), 'baseline KGE:', KGE(y_pred_base, y_test))




plt.figure()
n_input = len(test_df) - (input_width + shift) + 1

y_pred_df = copy.deepcopy(test_df)

test_df = test_df.rename(columns={"flow": "Obs"})
test_df['Obs'] = test_df['Obs'] * train_std['flow'] + train_mean['flow']

test_df[0+input_width+(shift-label_width):n_input+input_width+shift]['Obs'].plot(marker = '*', markersize=4)




y_pred_df.iloc[0+input_width+(shift-label_width):n_input+input_width+shift, -1] = y_pred

y_pred_df = y_pred_df.rename(columns={"flow": "LSTM"})
y_pred_df[0+input_width+(shift-label_width):n_input+input_width+shift]['LSTM'].plot(marker = '.', markersize=4)


ax = plt.gca()
ax.set_ylabel('streamflow (cms)')
ax.legend()

plt.savefig(f'{watershed}_MaxEpoch_{MAX_EPOCHS}_inWidth_{input_width}_shift_{shift}.png')



test_df['LSTM'] = y_pred_df['LSTM'] 



product_lstm = np.zeros([1388, 102])
product_base = np.zeros([1388, 102])

    


product_heaven = np.genfromtxt(f'Results_Harvey/{watershed}.txt', delimiter=',')
product_lstm[:, 0] = np.array(test_df['Obs'])
product_lstm[input_width:, 1] = y_pred

product_base[:, 0] = np.array(test_df['Obs'])
product_base[input_width:, 1] = y_pred_base


product_lstm = product_lstm[535-242:1388-3, :]
product_base = product_base[535-242:1388-3, :]



