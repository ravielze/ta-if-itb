from utils import printd, timings
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from pmdarima.arima import auto_arima
from configuration import OFFSET_TRESHOLD_RETRAIN

# Enum
MODEL_RETRAINED = 0
MODEL_UPDATED = 1

class PredictComponentFactory:

    def __init__(self, data, components, treshold):
        assert type(components) == list and len(components) > 0
        assert type(treshold) == float and treshold > 0.01
        assert type(data) == pd.DataFrame
        self.components = components
        self.data = data
        self.treshold = treshold

    def build(self):
        columns = set(self.data.columns.tolist())
        result = []
        for c in self.components:
            assert c in columns
            result.append(PredictComponent(c, self.data[c], self.treshold))
        return result

class PredictComponent:

    def __init__(self, name, data, treshold=0.7):
        self.name = name
        self.is_trained = False
        self.data = data.copy()
        self.calculate_readiness()
        self.treshold = treshold
        self.train()
    
    def calculate_readiness(self):
        self.mean = self.data.mean()
        self.std = self.data.std()
        self.enough_data = self.std > 0
    
    def predict(self, step):
        if (not self.enough_data):
            printd(f"({self.name}) Not enough data to predict")
            return None
        return self.trained_model.forecast(steps=step)
    
    def forecast(self, second):
        if (not self.enough_data):
            now = pd.Timestamp.now().to_period('S')
            return (str(now+second), self.mean)
        p = self.trained_model.forecast(steps=second)
        i = p.index[-1]
        if type(i) is int:
            i = pd.Timestamp.now().to_period('S') + second
        return (str(i), p.iloc[-1])
    
    def train(self):
        if (not self.enough_data):
            printd(f"({self.name}) Failed to train. Not enough data. STD: {self.std}. Mean: {self.mean}.")
            return
        traintiming = timings()
        self.automodel = auto_arima(self.data, trace=False, suppress_warnings=True, maxiter=10000, max_p=25, max_q=25, max_P=25, max_Q=25, stepwise=False, approximation=False)
        self.order = self.automodel.order
        self.model = ARIMA(self.data, order=self.order)
        self.trained_model = self.model.fit()
        printd(f"({self.name}) Training time: {traintiming()}ms")
        self.next_retrain = int(len(self.data) * self.treshold) + OFFSET_TRESHOLD_RETRAIN
        self.is_trained = True
    
    def update(self, new_data):
        self.next_retrain = self.next_retrain - len(new_data)
        new_data_copied = new_data.copy()
        self.data = pd.concat([self.data, new_data_copied])
        self.calculate_readiness()
        if self.next_retrain < 0 or not self.is_trained:
            self.train()
            return MODEL_RETRAINED
        else:
            updatetiming = timings()
            self.model.update(new_data_copied)
            printd(f"({self.name}) Update time: {updatetiming()}ms, Next Retrain: {self.next_retrain}")
            return MODEL_UPDATED
    
    def last_index(self):
        return self.trained_model.nobs
    
    def __str__(self):
        if (not self.is_trained):
            return f"ARIMA ({self.name}) Not Trained"
        return f"ARIMA ({self.name}) {self.order}"