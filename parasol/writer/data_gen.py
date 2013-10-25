#! /usr/bin/python
# gen test data

from sklearn import datasets
from writer import outputsamplelabel

def gen_classification_data(output, sz):
    x, y = datasets.make_classification(sz)
    outputsamplelabel(output, x, y, ',')

if __name__ == '__main__':
    gen_classification_data('/home/xunzhang/xunzhang/Data/classification/0000.csv', 260)
    