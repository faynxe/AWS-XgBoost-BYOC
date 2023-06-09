from __future__ import print_function

import io
import json
import os
import pickle
import signal
import sys
import traceback
import xgboost as xgb
import flask
import pandas as pd
import numpy as np
import shap

#All training, model, hyperparameter type artifacts are within this prefix
#for a general structure visit following link: 
prefix = "/opt/ml/"
model_path = os.path.join(prefix, "model")

def _get_full_model_paths(model_dir):
    for data_file in os.listdir(model_dir):
        full_model_path = os.path.join(model_dir, data_file)
        if os.path.isfile(full_model_path):
            if data_file.startswith("."):
                logging.warning(
                    f"Ignoring dotfile '{full_model_path}' found in model directory"
                    " - please exclude dotfiles from model archives"
                )
            else:
                yield full_model_path


                
class ScoringService(object):
    model = None  # Where we keep the model when it's loaded

    @classmethod
    def get_model(rgrs):
        """Get the model object for this instance, loading it if it's not already loaded."""
        full_model_paths = list(_get_full_model_paths(model_path))
        if rgrs.model == None:
            with open(os.path.join(model_path, str(full_model_paths[0])), "rb") as inp:
                rgrs.model = pickle.load(inp)
        return rgrs.model

    @classmethod
    def predict(rgrs, input):
        """For the input, do the predictions and return them.
        Args:
            input (a pandas dataframe): The data on which to do the predictions. There will be
                one prediction per row in the dataframe"""
        rf = rgrs.get_model()
        return rf.predict(input)


# The flask app for serving predictions
app = flask.Flask(__name__)


@app.route("/ping", methods=["GET"])
def ping():
    """Determine if the container is working and healthy. In this sample container, we declare
    it healthy if we can load the model successfully."""
    health = ScoringService.get_model() is not None  # You can insert a health check here

    status = 200 if health else 404
    return flask.Response(response="\n", status=status, mimetype="application/json")


@app.route("/invocations", methods=["POST"])
def transformation():
    
    data = None

    # Convert from CSV to pandas
    if flask.request.content_type == "text/csv":
        data = flask.request.data.decode("utf-8")
        s = io.StringIO(data)
        data = pd.read_csv(s, header=None)
    else:
        return flask.Response(
            response="This predictor only supports CSV data", status=415, mimetype="text/plain"
        )

    print("Invoked with {} records".format(data.shape[0]))

    # Do the prediction
    print(data)
    data= xgb.DMatrix(data)
    predictions = ScoringService.predict(data)

    # Convert from numpy back to CSV
    out = io.StringIO()
    pd.DataFrame({"results": predictions}).to_csv(out, header=False, index=False)
    result = out.getvalue()
    
    
    return flask.Response(response=result, status=200, mimetype="text/csv")
