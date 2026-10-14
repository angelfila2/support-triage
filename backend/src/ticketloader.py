
import pandas


def load_tickets(filepath):
    df = pandas.read_csv(filepath)
    return df
